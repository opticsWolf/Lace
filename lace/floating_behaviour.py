# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2019 Ken Lauer
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace, adapted from qtpydocking.
# Original code Copyright (c) 2019 Ken Lauer (BSD-3-Clause).
# Modifications Copyright (c) 2026 opticsWolf (Apache-2.0).

"""Behaviour shared by both floating dock container implementations.

Lace ships two of them — one on a native OS window frame, one on a frameless
window with a custom title bar — and they used to be two 1000+ line classes
with the same name, ~900 lines of which were duplicated verbatim. Every drag,
drop, resize or lifecycle fix had to land twice, and when one of them didn't,
the two window modes silently diverged.

What differs between them is window chrome: construction, the native-vs-synthetic
drag lifecycle, window flags, and how each installs its event filters. What does
not differ is everything downstream of that — the drag state machine, drop-overlay
tracking, chromeless resize, title bookkeeping and state persistence. That is
what lives here.

Subclasses supply::

    __init__, event, eventFilter, moveEvent, changeEvent, start_floating,
    update_window_flags_from_config, _do_restore_geometry,
    _end_swallowed_release, _install_permanent_filter, _remove_permanent_filter

and may override :meth:`FloatingContainerBehaviour._on_dock_areas_changed`.

The mixin must come **before** the Qt base in the MRO::

    class FloatingDockContainer(FloatingContainerBehaviour, QWidget, DockStyled)

It overrides closeEvent/resizeEvent/hideEvent/deleteLater, which QWidget also
defines; listed after QWidget, Qt's versions would win and none of this would
run. It defines no ``__init__``, so ``super().__init__(parent)`` in a subclass
still reaches the Qt base.
"""


import logging
import sys
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QCloseEvent, QCursor, QHideEvent, QPainterPath, QPalette, QRegion
from PySide6.QtWidgets import QApplication, QWidget

from lace.dock_container_state import restore_container_state
from lace.dock_theme import DockStyleCategory
from lace.enums import DockFlags, DockWidgetArea, DockWidgetFeature, DragState

if TYPE_CHECKING:
    from lace.dock_container_widget import DockContainerWidget
    from lace.dock_widget import DockWidget

logger = logging.getLogger(__name__)

# Resize handle thickness in pixels. Visual layout is NOT affected —
# we only use this for hit-testing, never as a layout inset.
_RESIZE_BORDER = 8

# Internal edge mask used by the non-Windows fallback.
_EDGE_NONE = 0
_EDGE_LEFT = 1 << 0
_EDGE_RIGHT = 1 << 1
_EDGE_TOP = 1 << 2
_EDGE_BOTTOM = 1 << 3

# Win32 window-style constants for the taskbar opt-in. Named here rather than
# imported so the mixin stays free of a pywin32 dependency on every platform.
_GWL_EXSTYLE = -20
_WS_EX_APPWINDOW = 0x00040000


class FloatingContainerBehaviour:
    """Window-chrome-independent behaviour of a floating dock container."""

    def _on_dock_areas_changed(self) -> None:
        """Hook: the set of dock areas in this float changed.

        Runs before the title bookkeeping in
        :meth:`on_dock_areas_added_or_removed`. The frameless container uses
        it to re-evaluate its custom close button, which the native one gets
        from the OS for free.
        """

    def __repr__(self):
        return f'<FloatingDockContainer container={self._dock_container}>'

    def _wants_taskbar_button(self) -> bool:
        """Whether this float should carry its own taskbar button."""
        return self._test_config_flag(DockFlags.floating_taskbar_button)

    def _apply_taskbar_presence(self) -> None:
        """Add or remove this float's taskbar button. Windows only.

        Floats are parented to the root container so they stack above the main
        window, and Qt hands a parented top-level its parent's HWND as the
        Win32 *owner*. Windows keeps an owned window out of the taskbar and out
        of Alt-Tab, so a minimized float would be unreachable — which is why
        the minimize button only appears with this flag set.
        ``WS_EX_APPWINDOW`` overrides the rule for one window without giving up
        the parenting.

        Call this after anything that recreates the native handle
        (``setWindowFlags``): the new handle does not inherit the ex-style.
        """
        if sys.platform != "win32":
            return
        if not self._wants_taskbar_button() and self.windowHandle() is None:
            # Nothing to clear, and no reason to force a native handle into
            # existence early just to prove it.
            return
        try:
            import ctypes

            hwnd = int(self.winId())
            if not hwnd:
                return
            user32 = ctypes.windll.user32
            user32.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]
            user32.GetWindowLongW.restype = ctypes.c_long
            user32.SetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int,
                                              ctypes.c_long]
            user32.SetWindowLongW.restype = ctypes.c_long

            handle = ctypes.c_void_p(hwnd)
            current = user32.GetWindowLongW(handle, _GWL_EXSTYLE)
            if self._wants_taskbar_button():
                wanted = current | _WS_EX_APPWINDOW
            else:
                wanted = current & ~_WS_EX_APPWINDOW
            if wanted == current:
                return
            user32.SetWindowLongW(handle, _GWL_EXSTYLE, wanted)
            # The shell reads the ex-style when the window is next shown, so an
            # already-visible float needs a cycle for the button to appear or
            # go away. Before the first show() there is nothing to cycle.
            if self.isVisible():
                self.hide()
                self.show()
        except Exception:
            logger.debug("Taskbar presence update unavailable", exc_info=True)

    def _activate_window(self):
        """Bring this floating window to the front and give it focus."""
        logger.debug(f"[FDC._activate_window] START. "
                     f"Active Window: {QApplication.activeWindow()}, "
                     f"Mouse Grabber: {QWidget.mouseGrabber()}")
        try:
            self.raise_()
            self.activateWindow()
            if self._dock_container:
                self._dock_container.setFocus()
            logger.debug(f"[FDC._activate_window] Done. "
                         f"Active Window: {QApplication.activeWindow()}")
        except RuntimeError:
            logger.debug("[FDC._activate_window] Window was deleted before activation.")

    def _apply_resize(self, global_pos: QPoint) -> None:
        """Apply the in-progress resize to this container's geometry."""
        delta = global_pos - self._resize_press_pos
        geom = QRect(self._resize_press_geom)
        min_size = self.minimumSizeHint().expandedTo(self.minimumSize())
        min_w = max(min_size.width(), 24)
        min_h = max(min_size.height(), 24)
        max_size = self.maximumSize()

        edge = self._resize_dir

        # Horizontal
        if edge & _EDGE_LEFT:
            new_right = geom.right()
            new_left = geom.left() + delta.x()
            if new_right - new_left + 1 < min_w:
                new_left = new_right - min_w + 1
            if new_right - new_left + 1 > max_size.width():
                new_left = new_right - max_size.width() + 1
            geom.setLeft(new_left)
        elif edge & _EDGE_RIGHT:
            new_right = geom.right() + delta.x()
            if new_right - geom.left() + 1 < min_w:
                new_right = geom.left() + min_w - 1
            if new_right - geom.left() + 1 > max_size.width():
                new_right = geom.left() + max_size.width() - 1
            geom.setRight(new_right)

        # Vertical
        if edge & _EDGE_TOP:
            new_bottom = geom.bottom()
            new_top = geom.top() + delta.y()
            if new_bottom - new_top + 1 < min_h:
                new_top = new_bottom - min_h + 1
            if new_bottom - new_top + 1 > max_size.height():
                new_top = new_bottom - max_size.height() + 1
            geom.setTop(new_top)
        elif edge & _EDGE_BOTTOM:
            new_bottom = geom.bottom() + delta.y()
            if new_bottom - geom.top() + 1 < min_h:
                new_bottom = geom.top() + min_h - 1
            if new_bottom - geom.top() + 1 > max_size.height():
                new_bottom = geom.top() + max_size.height() - 1
            geom.setBottom(new_bottom)

        self.setGeometry(geom)

    def _child_has_grab_mouse(self) -> bool:
        """Return True if any descendant currently has the mouse grab.

        This prevents us from stealing the cursor while the user is
        interacting with an inner widget (e.g. scrollbar thumb drag).
        """
        app = QApplication.instance()
        if app is None:
            return False
        grabber = QWidget.mouseGrabber()
        if grabber is None:
            return False
        if grabber is self:
            return False
        return self._is_our_widget(grabber)

    def _clear_synthetic_release_flag(self):
        self._ignore_synthetic_release = False

    @staticmethod
    def _cursor_for_edge(edge: int) -> Optional[Qt.CursorShape]:
        """Map an edge bitmask to a Qt cursor shape (or None for client area)."""
        if edge == _EDGE_NONE:
            return None
        # Corner combinations
        if edge & _EDGE_TOP and edge & _EDGE_LEFT:
            return Qt.SizeFDiagCursor
        if edge & _EDGE_TOP and edge & _EDGE_RIGHT:
            return Qt.SizeBDiagCursor
        if edge & _EDGE_BOTTOM and edge & _EDGE_LEFT:
            return Qt.SizeBDiagCursor
        if edge & _EDGE_BOTTOM and edge & _EDGE_RIGHT:
            return Qt.SizeFDiagCursor
        # Pure edges
        if edge & (_EDGE_LEFT | _EDGE_RIGHT):
            return Qt.SizeHorCursor
        if edge & (_EDGE_TOP | _EDGE_BOTTOM):
            return Qt.SizeVerCursor
        return None

    def _destroyed(self, *args):
        self._remove_permanent_filter()
        dock_container = self._dock_container
        self._dock_container = None
        if dock_container is not None:
            self._dock_manager.remove_dock_container(dock_container)
            self._dock_manager.remove_floating_widget(self)

    def _end_programmatic_drag(self):
        """Deferred cleanup for programmatic drags (path A/C)."""
        logger.debug("[FDC._end_programmatic_drag] START")
        logger.debug("[FDC._end_programmatic_drag] END")
        self._finalize_drag()

    def _finalize_drag(self):
        """Attempt to drop into a container, or survive as an independent window."""
        logger.debug(f"[FDC._finalize_drag] START. "
                     f"Drop container: {self._drop_container}, "
                     f"Active Window: {QApplication.activeWindow()}")

        self._set_state(DragState.inactive)

        if not self._drop_container or not self._is_movable():
            logger.debug("[FDC._finalize_drag] No drop container or not movable — surviving as independent window.")
            if self._dock_manager:
                self._dock_manager.container_overlay().hide_overlay()
                self._dock_manager.dock_area_overlay().hide_overlay()
            self._activate_window()
            return

        dock_area_overlay = self._dock_manager.dock_area_overlay()
        container_overlay = self._dock_manager.container_overlay()

        dropped = False
        if any(overlay.drop_area_under_cursor() != DockWidgetArea.invalid
               for overlay in (dock_area_overlay, container_overlay)):

            overlay = container_overlay
            if not overlay.drop_overlay_rect().isValid():
                overlay = dock_area_overlay

            rect = overlay.drop_overlay_rect()
            if not rect.isValid():
                logger.debug("[FDC._finalize_drag] Invalid overlay rect.")
            else:
                frame_width = (self.frameSize().width() - self.rect().width()) // 2
                title_bar_height = int(
                    self.frameSize().height() - self.rect().height() - frame_width)
                top_left = overlay.mapToGlobal(rect.topLeft())
                top_left.setY(top_left.y() + title_bar_height)
                geom = QRect(top_left,
                             QSize(rect.width(), rect.height() - title_bar_height))
                self.setGeometry(geom)

            logger.debug(f"[FDC._finalize_drag] Dropping into {self._drop_container}")
            self._drop_container.drop_floating_widget(self, QCursor.pos())
            dropped = True

        # Always hide overlays and clear the reference
        if self._dock_manager:
            self._dock_manager.container_overlay().hide_overlay()
            self._dock_manager.dock_area_overlay().hide_overlay()
        self._drop_container = None

        if not dropped:
            logger.debug("[FDC._finalize_drag] Drop zone invalid — surviving as independent window.")
            self._activate_window()

    def _handle_resize_event(self, obj: QObject, event: QEvent) -> bool:
        """Process hover / press / move / release for fallback resizing."""
        if not self._chromeless:
            return False
        if not self._is_our_widget(obj):
            return False

        etype = event.type()

        # --- Hover: update cursor shape ----------------------------------
        if etype == QEvent.MouseMove:
            mouse_evt = event  # type: QMouseEvent
            if not self._is_resizing:
                # Use global position mapped to container coordinates so the
                # cursor stays correct even when the mouse is over a child.
                local = self.mapFromGlobal(mouse_evt.globalPosition().toPoint()) \
                    if hasattr(mouse_evt, "globalPosition") \
                    else self.mapFromGlobal(mouse_evt.globalPos())
                edge = self._hit_test_edges(local)
                cursor_shape = self._cursor_for_edge(edge)
                # Only override cursor when the mouse is in the resize band
                # AND no child widget is currently grabbing the mouse.
                if cursor_shape is not None and not self._child_has_grab_mouse():
                    self._resize_active_widget = obj if isinstance(obj, QWidget) else None
                    if isinstance(obj, QWidget):
                        obj.setCursor(cursor_shape)
                    return False  # don't consume — let child widgets paint
                else:
                    if isinstance(obj, QWidget) and obj.cursor().shape() in (
                        Qt.SizeHorCursor, Qt.SizeVerCursor, Qt.SizeFDiagCursor, Qt.SizeBDiagCursor
                    ):
                        obj.unsetCursor()
                    return False
            else:
                # Active resize — handle below in the move branch.
                pass

        # --- Begin resize ------------------------------------------------
        if etype == QEvent.MouseButtonPress:
            mouse_evt = event  # type: QMouseEvent
            if mouse_evt.button() != Qt.LeftButton:
                return False
            # Decide whether press is in a resize band — use the *target*
            # widget's coordinates mapped back to the container.
            target = obj
            if not isinstance(target, QWidget):
                return False
            global_pos = (mouse_evt.globalPosition().toPoint()
                          if hasattr(mouse_evt, "globalPosition")
                          else mouse_evt.globalPos())
            local = self.mapFromGlobal(global_pos)
            edge = self._hit_test_edges(local)
            if edge == _EDGE_NONE:
                return False
            # Begin resizing.
            self._is_resizing = True
            self._resize_dir = edge
            self._resize_press_pos = global_pos
            self._resize_press_geom = QRect(self.pos(), self.size())
            self._resize_active_widget = target
            # Grab the mouse so we keep receiving moves even if the cursor
            # leaves the original target widget.
            target.grabMouse(self._cursor_for_edge(edge) or Qt.ArrowCursor)
            return True

        # --- Continue resize ---------------------------------------------
        if etype == QEvent.MouseMove and self._is_resizing:
            mouse_evt = event  # type: QMouseEvent
            global_pos = (mouse_evt.globalPosition().toPoint()
                          if hasattr(mouse_evt, "globalPosition")
                          else mouse_evt.globalPos())
            self._apply_resize(global_pos)
            return True

        # --- End resize --------------------------------------------------
        if etype == QEvent.MouseButtonRelease and self._is_resizing:
            mouse_evt = event  # type: QMouseEvent
            if mouse_evt.button() != Qt.LeftButton:
                return False
            target = self._resize_active_widget
            self._is_resizing = False
            self._resize_dir = _EDGE_NONE
            self._resize_active_widget = None
            if isinstance(target, QWidget):
                try:
                    target.releaseMouse()
                except RuntimeError:
                    pass
            # Refresh cursor for the current hover position.
            if isinstance(target, QWidget):
                edge = self._hit_test_edges(self.mapFromGlobal(QCursor.pos()))
                cursor_shape = self._cursor_for_edge(edge)
                if cursor_shape:
                    target.setCursor(cursor_shape)
                else:
                    target.unsetCursor()
            return True

        return False

    def _hit_test_edges(self, local_pos: QPoint) -> int:
        """Return a bitmask of `_EDGE_*` flags for *local_pos*.

        Coordinates are relative to this container's top-left. The handle
        band is `_RESIZE_BORDER` pixels wide.
        """
        rect = self.rect()
        if not rect.contains(local_pos):
            return _EDGE_NONE

        flags = _EDGE_NONE
        if local_pos.x() <= _RESIZE_BORDER:
            flags |= _EDGE_LEFT
        elif local_pos.x() >= rect.width() - _RESIZE_BORDER:
            flags |= _EDGE_RIGHT
        if local_pos.y() <= _RESIZE_BORDER:
            flags |= _EDGE_TOP
        elif local_pos.y() >= rect.height() - _RESIZE_BORDER:
            flags |= _EDGE_BOTTOM
        return flags

    def _is_movable(self) -> bool:
        if not self._dock_container:
            return False
        try:
            top_area = self._dock_container.top_level_dock_area()
            if top_area is not None:
                return top_area.movable
            for area in self._dock_container.opened_dock_areas():
                if not area.movable:
                    return False
            return True
        except RuntimeError:
            return False

    def _is_our_widget(self, obj: QObject) -> bool:
        """Return True if *obj* is this container or a descendant of it."""
        if obj is self:
            return True
        if isinstance(obj, QWidget):
            return self.isAncestorOf(obj)
        return False

    def _set_state(self, state_id: DragState):
        self._dragging_state = state_id
        if state_id == DragState.floating_widget:
            opaque = self._test_config_flag(DockFlags.opaque_undocking)
            self.setWindowOpacity(1.0 if opaque else 0.6)
        elif state_id == DragState.inactive:
            self.setWindowOpacity(1.0)

    def _set_window_title(self, text: str):
        self.setWindowTitle(text)

    def _test_config_flag(self, flag: DockFlags) -> bool:
        if self._dock_manager:
            return flag in self._dock_manager.config_flags
        return False

    def _update_chromeless_mask(self):
        """Set a rounded QRegion mask so the corners outside the painted
        border become transparent.  Only called for chromeless floats."""
        r = self._corner_radius
        if r <= 0 or self.width() <= 0 or self.height() <= 0:
            self.clearMask()
            return
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), r, r)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def _update_drop_overlays(self, global_pos: QPoint):
        if not self.isVisible() or not self._dock_manager or not self._is_movable():
            return

        top_container = None
        for container_widget in self._dock_manager.dock_containers():
            try:
                if not container_widget.isVisible():
                    continue
                if self._dock_container is container_widget:
                    continue

                mapped_pos = container_widget.mapFromGlobal(global_pos)
                if container_widget.rect().contains(mapped_pos):
                    if not top_container or container_widget.is_in_front_of(top_container):
                        top_container = container_widget
            except RuntimeError:
                # Safely ignore containers that were deleted in C++
                pass

        self._drop_container = top_container
        container_overlay = self._dock_manager.container_overlay()
        dock_area_overlay = self._dock_manager.dock_area_overlay()
        if not top_container:
            logger.debug('update_drop_overlays: No top container')
            container_overlay.hide_overlay()
            dock_area_overlay.hide_overlay()
            return

        logger.debug('update_drop_overlays: top container=%s name=%s',
                     self._drop_container, self._drop_container.objectName())

        visible_dock_areas = top_container.visible_dock_area_count()
        container_overlay.set_allowed_areas(
            DockWidgetArea.outer_dock_areas
            if visible_dock_areas > 1
            else DockWidgetArea.all_dock_areas
        )

        container_area = container_overlay.show_overlay(top_container)
        container_overlay.enable_drop_preview(container_area != DockWidgetArea.invalid)
        dock_area = top_container.dock_area_at(global_pos)

        if dock_area and dock_area.isVisible() and visible_dock_areas > 0:
            dock_area_overlay.enable_drop_preview(True)
            dock_area_overlay.set_allowed_areas(
                DockWidgetArea.no_area
                if visible_dock_areas == 1
                else DockWidgetArea.all_dock_areas)
            area = dock_area_overlay.show_overlay(dock_area)

            if (area == DockWidgetArea.center and
                    container_area != DockWidgetArea.invalid):
                dock_area_overlay.enable_drop_preview(False)
                container_overlay.enable_drop_preview(True)
            else:
                container_overlay.enable_drop_preview(DockWidgetArea.invalid == area)
        else:
            dock_area_overlay.hide_overlay()

    def closeEvent(self, event: QCloseEvent):
        logger.debug('FloatingDockContainer closeEvent')
        self._remove_permanent_filter()
        self._set_state(DragState.inactive)
        if not self.is_closable():
            event.ignore()
            return
            
        # Move aggressive layout cleanup from hideEvent to closeEvent
        # This prevents frameless opacity changes from accidentally destroying widgets
        if self._dock_container:
            for dock_area in self._dock_container.opened_dock_areas():
                for dock_widget in dock_area.opened_dock_widgets():
                    dock_widget.toggle_view(False)
                    
        super().closeEvent(event)

    def deleteLater(self):
        self._remove_permanent_filter()
        self._destroyed()
        super().deleteLater()

    def dock_container(self) -> 'DockContainerWidget':
        return self._dock_container

    def hideEvent(self, event: QHideEvent):
        super().hideEvent(event)

    def init_floating_geometry(self, drag_start_mouse_pos: QPoint, size: QSize):
        self.start_floating(drag_start_mouse_pos, size, DragState.inactive)

    def move_floating(self):
        border_size = (self.frameSize().width() - self.size().width()) / 2
        move_to_pos = QCursor.pos() - self._drag_start_mouse_position - QPoint(int(border_size), 0)
        self.move(move_to_pos)

    def on_dock_area_current_changed(self, index: int):
        """Updates the floating window title when the active tab in the area changes."""
        try:
            if self._single_dock_area:
                widget = self._single_dock_area.current_dock_widget()
                if widget:
                    self._set_window_title(widget.windowTitle())
        except (RuntimeError, AttributeError):
            # Safe guard if the widget or area is being destroyed
            pass

    def refresh_style(self):
        core_styles = self._style_mgr.get_all(DockStyleCategory.CORE)
        bg_color = core_styles.get("canvas_bg")

        if bg_color:
            pal = self.palette()
            pal.setColor(QPalette.ColorRole.Window, bg_color)
            self.setPalette(pal)

        if not self._chromeless:
            self.setAutoFillBackground(True)
            self.setBackgroundRole(QPalette.ColorRole.Window)

        self._corner_radius = float(core_styles.get("corner_radius", 0))
        if self._chromeless:
            self._update_chromeless_mask()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._chromeless:
            self._update_chromeless_mask()

    def restore_state(self, state: dict, testing: bool, assigned: dict = None) -> bool:
        if not restore_container_state(self._dock_container, state, testing, assigned):
            return False
        self.on_dock_areas_added_or_removed()
        return True

    def start_dragging(self, drag_start_mouse_pos: QPoint, size: QSize,
                       mouse_event_handler: QWidget = None):
        self.start_floating(drag_start_mouse_pos, size,
                            DragState.floating_widget, mouse_event_handler)

    def update_window_title(self):
        try:
            top_level_dock_area = self._dock_container.top_level_dock_area()
            if top_level_dock_area is not None:
                widget = top_level_dock_area.current_dock_widget()
                title = widget.windowTitle() if widget else QApplication.applicationDisplayName()
            else:
                title = QApplication.applicationDisplayName()
        except RuntimeError:
            title = QApplication.applicationDisplayName()
        self._set_window_title(title)

    def on_dock_areas_added_or_removed(self):
        """Updates window title and forces title-bar button synchronization."""
        logger.debug('FloatingDockContainer.onDockAreasAddedOrRemoved()')

        self._on_dock_areas_changed()

        # --- FIX: Synchronize all title bars in this floating window ---
        # This ensures the Pin/Unpin icon flips immediately upon floating.
        try:
            for area in self._dock_container.opened_dock_areas():
                area._update_title_bar_button_states()
        except (RuntimeError, AttributeError):
            pass

        # Existing title management logic
        try:
            top_level_dock_area = self._dock_container.top_level_dock_area()
            dock_areas = self._dock_container.opened_dock_areas()
        except RuntimeError:
            return

        target_area = top_level_dock_area if top_level_dock_area else (dock_areas[0] if dock_areas else None)

        try:
            is_different = self._single_dock_area != target_area
        except RuntimeError:
            is_different = True

        if is_different:
            if self._single_dock_area:
                try:
                    self._single_dock_area.current_changed.disconnect(self.on_dock_area_current_changed)
                except (RuntimeError, TypeError):
                    pass
            self._single_dock_area = target_area
            if self._single_dock_area:
                try:
                    self._single_dock_area.current_changed.connect(self.on_dock_area_current_changed)
                except (RuntimeError, TypeError):
                    pass

        try:
            if self._single_dock_area:
                widget = self._single_dock_area.current_dock_widget()
                title = widget.windowTitle() if widget else QApplication.applicationDisplayName()
            else:
                title = QApplication.applicationDisplayName()
        except RuntimeError:
            title = QApplication.applicationDisplayName()
            
        self._set_window_title(title)

    def is_closable(self) -> bool:
        if self._dock_container is None:
            return True
        return DockWidgetFeature.closable in self._dock_container.features()

    def has_top_level_dock_widget(self) -> bool:
        if self._dock_container is None:
            return False
        return self._dock_container.has_top_level_dock_widget()

    def top_level_dock_widget(self) -> Optional['DockWidget']:
        if self._dock_container is None:
            return None
        return self._dock_container.top_level_dock_widget()

    def dock_widgets(self) -> list:
        if self._dock_container is None:
            return []
        return self._dock_container.dock_widgets()
