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


import sys
from typing import TYPE_CHECKING, Optional
import logging

from PySide6.QtCore import (QEvent, QObject, QPoint, QRect, QRectF,
                            QSize, Qt, QTimer)
from PySide6.QtGui import (QCloseEvent, QColor, QCursor, QHideEvent, QPainterPath,
                           QPalette, QMoveEvent, QRegion, QMouseEvent)
from PySide6.QtWidgets import QApplication, QBoxLayout, QWidget

from .enums import DockFlags, DockWidgetFeature, DragState, DockWidgetArea, WidgetState
from .dock_container_widget import DockContainerWidget
from .dock_container_state import restore_container_state

from .dock_styled import DockStyled
from .dock_theme import DockStyleCategory
from .frameless_window import FramelessLaceWindow
from .frameless_titlebar import FramelessTitleBarStyler
from .util import start_drag_distance



# Resize handle thickness in pixels. Visual layout is NOT affected —
# we only use this for hit-testing, never as a layout inset.
_RESIZE_BORDER = 8

# Internal edge mask used by the non-Windows fallback.
_EDGE_NONE = 0
_EDGE_LEFT = 1 << 0
_EDGE_RIGHT = 1 << 1
_EDGE_TOP = 1 << 2
_EDGE_BOTTOM = 1 << 3

if TYPE_CHECKING:
    from . import DockAreaWidget, DockWidget, DockManager

logger = logging.getLogger(__name__)

_z_order_counter = 0


class FloatingDockContainer(FramelessLaceWindow, DockStyled):
    """Floating dock container backed by a frameless window.

    Inherits from :class:`FramelessLaceWindow` (PySideSix-Frameless-Window)
    so floating windows always get the custom title bar, cross-platform
    resize borders (WM_NCHITTEST / LinuxMoveResize / native macOS handling)
    and DWM shadow instead of a native OS title bar.  The custom title bar
    is themed through :class:`FramelessTitleBarStyler`.
    """
    STYLE_CATEGORIES = (DockStyleCategory.CORE,)
    def __init__(self, *, dock_area: 'DockAreaWidget' = None,
                 dock_widget: 'DockWidget' = None,
                 dock_manager: 'DockManager' = None):
        """Initializes the floating container and resets the state of incoming widgets."""
        if dock_manager is None:
            if dock_area is not None:
                dock_manager = dock_area.dock_manager()
            elif dock_widget is not None:
                dock_manager = dock_widget.dock_manager()

        if dock_manager is None:
            raise ValueError('Must pass in either dock_area, dock_widget, or dock_manager')

        super().__init__(getattr(dock_manager, '_root', None) or dock_manager)
        
        self._dragging_state = DragState.inactive
        self._drag_start_mouse_position = QPoint()
        self._drop_container: DockContainerWidget = None
        self._single_dock_area: 'DockAreaWidget' = None
        self._mouse_event_handler: QWidget = None
        self._dock_container: DockContainerWidget = None
        self._pending_restore_geometry: Optional['QRect'] = None
        # Close-button disabled state: remembered normal icon colour and the
        # system close hover/pressed colours (so they can be restored when the
        # float becomes closable again), plus the set of dock widgets whose
        # features_changed we are following.
        self._close_btn_normal_color = None
        self._close_btn_system_hover = None
        self._feature_synced_widgets = set()
        global _z_order_counter
        _z_order_counter += 1
        self._z_order_index = _z_order_counter
        self._dock_manager = dock_manager
        
        # Apply application icon or fallback to root main window icon
        app_icon = QApplication.instance().windowIcon()
        if (app_icon.isNull() or app_icon.pixmap(16, 16).isNull()) and getattr(dock_manager, '_root', None) and hasattr(dock_manager._root, 'windowIcon'):
            app_icon = dock_manager._root.windowIcon()
        if not app_icon.isNull() and not app_icon.pixmap(16, 16).isNull():
            self.setWindowIcon(app_icon)
            if QApplication.instance().windowIcon().isNull():
                QApplication.instance().setWindowIcon(app_icon)

        dock_container = DockContainerWidget(dock_manager, self)
        self._dock_container = dock_container
        dock_container.destroyed.connect(self._destroyed)
        dock_container.dock_areas_added.connect(self.on_dock_areas_added_or_removed)
        self._chromeless = self._test_config_flag(DockFlags.chromeless_float)
        self._corner_radius = 0.0

        # ── Frameless window setup ─────────────────────────────────────────
        # Floating containers are parented widgets, so promote this to a real
        # top-level frameless window first (the frameless base only ORs
        # Qt.FramelessWindowHint into the existing flags).
        flags = (Qt.Window | Qt.FramelessWindowHint |
                 Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        self.setWindowFlags(flags)
        # setWindowFlags() (re)creates the native window handle — re-apply the
        # DWM shadow / animation registered by the frameless base.
        updater = getattr(self, "updateFrameless", None)
        if updater is not None:
            try:
                updater()
            except Exception:
                pass

        # Swap in a StandardTitleBar so floating windows show the window icon
        # and title text like the main window.
        from qframelesswindow.titlebar import StandardTitleBar
        self.setTitleBar(StandardTitleBar(self))
        # StandardTitleBar only refreshes its icon label on windowIconChanged,
        # and the icon was already set before the swap — push it explicitly so
        # the floating window shows the app icon.
        icon_setter = getattr(self.titleBar, "setIcon", None)
        if icon_setter is not None:
            icon_setter(self.windowIcon())
        if self._chromeless:
            # chromeless_float => bare floating surface: no title bar at all.
            self.titleBar.hide()
            self.setAttribute(Qt.WA_TranslucentBackground)

        layout = QBoxLayout(QBoxLayout.TopToBottom)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        # The custom title bar is a normal layout row; the dock container
        # fills the remaining space beneath it.
        layout.addWidget(self.titleBar, 0)
        layout.addWidget(dock_container, 1)
        dock_manager.register_floating_widget(self)

        # --- FIX: Transition widgets to Floating state before adding to layout ---
        if dock_area is not None:
            # Update all widgets within the area to floating state
            for dw in dock_area.dock_widgets():
                dw.set_widget_state(WidgetState.floating)
            dock_container.add_dock_area(dock_area)
        elif dock_widget is not None:
            # Update single widget to floating state
            dock_widget.set_widget_state(WidgetState.floating)
            dock_container.add_dock_widget(DockWidgetArea.center, dock_widget)
            
        self._ignore_synthetic_release = False

        # Style Manager Integration
        self._init_dock_style()

        # Sync the title-bar close button with the float's closability now
        # that the dock areas / widgets are in place.
        self._update_close_button_state()

        # ── Frameless title-bar theme integration ──────────────────────────
        # FramelessTitleBarStyler subscribes to DockStyleManager and applies
        # the active dock-theme colours to the custom title bar (background,
        # title text, min/max/close button colours).
        self._titlebar_styler = FramelessTitleBarStyler(
            title_bar=self.titleBar, parent=self)
        # The styler re-applies theme colours (including the close button's
        # normal icon colour) on every theme change, so re-apply our
        # close-button disabled state after each styler pass.
        self._titlebar_styler._after_refresh = self._update_close_button_state

        # Sync the title-bar close button with the float's closability now
        # that the dock areas / widgets are in place (runs again after the
        # styler's initial pass via _after_refresh).
        self._update_close_button_state()

        # ── Title-bar drag → dock-drag routing ────────────────────────────
        # The qframelesswindow title bar's plain OS move loop
        # (startSystemMove / WM_SYSCOMMAND SC_MOVE) never delivers the
        # NonClientAreaMouseButtonPress events the dock-drag machinery
        # relies on, so the drop overlay would never appear and floats
        # could not be redocked when dragged by the custom title bar.
        # Route the title bar's press/move/release through
        # _handle_titlebar_drag instead: the press arms the dock-drag
        # state machine and starts the OS move loop, moveEvent feeds the
        # drop overlay, and the release (caught by a transient app filter
        # wherever it lands) finalizes through the shared path.
        self._titlebar_drag_start = QPoint()
        self._frameless_drag_filter = False
        self._os_move_active = False
        self.titleBar.installEventFilter(self)

        # --- Resizing state (cross-platform) ---------------------------------
        self._is_resizing = False
        self._resize_dir = _EDGE_NONE
        self._resize_press_pos = QPoint()        # Global press position
        self._resize_press_geom = QRect()        # Geometry at press time
        self._resize_active_widget: Optional[QWidget] = None  # widget under cursor

        # Permanent event-filter tracking — the FramelessLaceWindow base
        # already handles resize borders on every platform (WM_NCHITTEST on
        # Windows, LinuxMoveResize on Linux, native handling on macOS), so
        # the manual chromeless-resize fallback is never armed.
        self._permanent_filter_installed = False
        
    def _install_permanent_filter(self) -> None:
        """No-op: the FramelessLaceWindow base handles window resizing.

        On Windows the base answers WM_NCHITTEST with the resize hit-tests;
        on Linux/macOS it installs its own event filter / native handling.
        The manual chromeless-resize fallback is therefore never needed for
        the frameless variant.
        """
        self._permanent_filter_installed = False

    def _remove_permanent_filter(self) -> None:
        """No-op: the frameless base owns resize handling, no filter to remove."""
        self._permanent_filter_installed = False

    def _is_our_widget(self, obj: QObject) -> bool:
        """Return True if *obj* is this container or a descendant of it."""
        if obj is self:
            return True
        if isinstance(obj, QWidget):
            return self.isAncestorOf(obj)
        return False

    def __repr__(self):
        return f'<FloatingDockContainer container={self._dock_container}>'

    # ─────────────────────────────────────────────────────────────────────
    #  Drag Lifecycle
    # ─────────────────────────────────────────────────────────────────────

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

    # ─────────────────────────────────────────────────────────────────────
    #  Drop overlay tracking (shared by both drag paths via moveEvent)
    # ─────────────────────────────────────────────────────────────────────

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

    # ─────────────────────────────────────────────────────────────────────
    #  Internal helpers
    # ─────────────────────────────────────────────────────────────────────

    def update_window_flags_from_config(self):
        self._chromeless = self._test_config_flag(DockFlags.chromeless_float)
        # The frameless variant always keeps Qt.FramelessWindowHint (the base
        # class sets it); the native OS title bar never returns.
        flags = (Qt.Window | Qt.FramelessWindowHint |
                 Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        if self.windowFlags() != flags:
            # Save client-area geometry so content size is preserved across
            # the flag change (setWindowFlags destroys/recreates the native
            # window frame, resetting geometry).
            saved_geometry = self.geometry()
            was_visible = self.isVisible()
            self.setWindowFlags(flags)
            # Sync translucent background with chromeless state.
            self.setAttribute(Qt.WA_TranslucentBackground, self._chromeless)
            # setWindowFlags() recreates the native window handle — re-apply
            # the DWM shadow / animation registered by the frameless base.
            updater = getattr(self, "updateFrameless", None)
            if updater is not None:
                try:
                    updater()
                except Exception:
                    pass
            if was_visible:
                self.show()
            # Restore the saved client-area geometry and force a full repaint.
            QTimer.singleShot(0, self._do_restore_geometry)
            self._pending_restore_geometry = saved_geometry
        else:
            self.setAttribute(Qt.WA_TranslucentBackground, self._chromeless)
            self._pending_restore_geometry = None

        # The custom title bar follows the chromeless flag: chromeless floats
        # are bare surfaces without any title bar.
        tb = getattr(self, "titleBar", None)
        if tb is not None:
            if self._chromeless:
                tb.hide()
            else:
                tb.show()
                tb.raise_()

        # Sync the rounded-corner mask with the chromeless state.
        if self._chromeless:
            self._update_chromeless_mask()
        else:
            self.clearMask()

    def _do_restore_geometry(self):
        """Restore saved client-area geometry after setWindowFlags (deferred)."""
        geom = getattr(self, '_pending_restore_geometry', None)
        if geom is None:
            return
        self._pending_restore_geometry = None
        self.setGeometry(geom)

        # Re-apply the chromeless rounded-corner mask so corners render
        # correctly after the flag change (resizeEvent won't fire since
        # geometry is restored to the same value).
        if self._chromeless:
            self._update_chromeless_mask()
        else:
            self.clearMask()
        # Force a full redraw of the window and its children.
        self.repaint()

    def _test_config_flag(self, flag: DockFlags) -> bool:
        if self._dock_manager:
            return flag in self._dock_manager.config_flags
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

    def _destroyed(self, *args):
        self._remove_permanent_filter()
        dock_container = self._dock_container
        self._dock_container = None
        if dock_container is not None:
            self._dock_manager.remove_dock_container(dock_container)
            self._dock_manager.remove_floating_widget(self)

    def deleteLater(self):
        self._remove_permanent_filter()
        self._destroyed()
        super().deleteLater()

    # ─────────────────────────────────────────────────────────────────────
    #  Title / dock-area bookkeeping
    # ─────────────────────────────────────────────────────────────────────

    def on_dock_areas_added_or_removed(self):
        """Updates window title and forces title-bar button synchronization."""
        logger.debug('FloatingDockContainer.onDockAreasAddedOrRemoved()')

        # Close button enabled state follows the float's closability, which
        # depends on the dock widgets currently in the float.
        self._update_close_button_state()
        self._sync_feature_signals()
        
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

    # ─────────────────────────────────────────────────────────────────────
    #  Public drag API
    # ─────────────────────────────────────────────────────────────────────

    def start_floating(self, drag_start_mouse_pos: QPoint, size: QSize,
                       drag_state: DragState,
                       mouse_event_handler: QWidget = None):
        self.resize(size)
        self._set_state(drag_state)
        self._drag_start_mouse_position = drag_start_mouse_pos
        
        if drag_state == DragState.floating_widget:
            self._mouse_event_handler = mouse_event_handler
            
            # Arm the guard against the OS synthetic release.
            # Using 50ms buffer instead of 0 to ensure the event loop has fully processed 
            # the grabMouse handoff before we start accepting releases.
            self._ignore_synthetic_release = True
            QTimer.singleShot(50, self._clear_synthetic_release_flag)
                
        self.move_floating()
        self.show()

        if drag_state == DragState.floating_widget:
            if self._mouse_event_handler:
                self._mouse_event_handler.grabMouse()
            if not self._permanent_filter_installed:
                QApplication.instance().installEventFilter(self)

    def _clear_synthetic_release_flag(self):
        self._ignore_synthetic_release = False

    def start_dragging(self, drag_start_mouse_pos: QPoint, size: QSize,
                       mouse_event_handler: QWidget = None):
        self.start_floating(drag_start_mouse_pos, size,
                            DragState.floating_widget, mouse_event_handler)

    def init_floating_geometry(self, drag_start_mouse_pos: QPoint, size: QSize):
        self.start_floating(drag_start_mouse_pos, size, DragState.inactive)

    def move_floating(self):
        border_size = (self.frameSize().width() - self.size().width()) / 2
        move_to_pos = QCursor.pos() - self._drag_start_mouse_position - QPoint(int(border_size), 0)
        self.move(move_to_pos)

    # ─────────────────────────────────────────────────────────────────────
    #  State persistence
    # ─────────────────────────────────────────────────────────────────────

    def restore_state(self, state: dict, testing: bool) -> bool:
        if not restore_container_state(self._dock_container, state, testing):
            return False
        self.on_dock_areas_added_or_removed()
        return True

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

    # ─────────────────────────────────────────────────────────────────────
    #  Qt event overrides
    # ─────────────────────────────────────────────────────────────────────

    def changeEvent(self, event: QEvent):
        super().changeEvent(event)
        if (event.type() == QEvent.ActivationChange) and self.isActiveWindow():
            logger.debug('FloatingWidget.changeEvent QEvent.ActivationChange')
            global _z_order_counter
            _z_order_counter += 1
            self._z_order_index = _z_order_counter
        if event.type() == QEvent.WindowStateChange and self._dock_container:
            # Update maximize/restore icon when the OS window state changes
            for dock_area in self._dock_container.opened_dock_areas():
                dock_area._update_title_bar_button_states()

    def moveEvent(self, event: QMoveEvent):
        super().moveEvent(event)
        state = getattr(self, '_dragging_state', DragState.inactive)
        if state == DragState.mouse_pressed:
            self._set_state(DragState.floating_widget)
            self._update_drop_overlays(QCursor.pos())
        elif state == DragState.floating_widget:
            self._update_drop_overlays(QCursor.pos())

    def event(self, e: QEvent) -> bool:
        """Handle native (OS) title-bar drag lifecycle (path B)."""
        state = getattr(self, '_dragging_state', DragState.inactive)
        if state == DragState.inactive:
            if e.type() == QEvent.NonClientAreaMouseButtonPress:
                logger.debug('FloatingWidget.event Event.NonClientAreaMouseButtonPress %s', e.type())
                self._set_state(DragState.mouse_pressed)
        elif state == DragState.mouse_pressed:
            if e.type() == QEvent.NonClientAreaMouseButtonDblClick:
                logger.debug('FloatingWidget.event QEvent.NonClientAreaMouseButtonDblClick')
                self._set_state(DragState.inactive)
            elif e.type() == QEvent.Resize:
                if not self.isMaximized():
                    self._set_state(DragState.inactive)
            elif e.type() == QEvent.NonClientAreaMouseButtonRelease:
                # Add safety net so non-drag clicks don't leave window stuck in mouse_pressed
                self._set_state(DragState.inactive)
        elif state == DragState.floating_widget:
            if e.type() == QEvent.NonClientAreaMouseButtonRelease:
                logger.debug('FloatingWidget.event QEvent.NonClientAreaMouseButtonRelease')
                self._set_state(DragState.inactive)
                QTimer.singleShot(0, self._finalize_drag)

        return super().event(e)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._chromeless:
            self._update_chromeless_mask()

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

    def hideEvent(self, event: QHideEvent):
        super().hideEvent(event)
        # REMOVED: toggle_view(False) loop
        # Recreating the frameless window (e.g. via setWindowOpacity during drops) 
        # triggers QHideEvent. Closing widgets here incorrectly ripped them from the layout!

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

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        # --- Frameless title-bar drag (custom mode) ------------------------
        if watched is self.titleBar:
            if self._handle_titlebar_drag(watched, event):
                return True

        # --- Permanent path: chromeless resize on macOS / Linux --------------
        if self._permanent_filter_installed:
            if self._handle_resize_event(watched, event):
                return True

        # --- Existing drag / float handling goes here ------------------------
        # Dynamically clear synthetic release block upon actual mouse movement
        if event.type() == QEvent.MouseMove:
            self._ignore_synthetic_release = False
            
        if event.type() == QEvent.MouseButtonRelease:
            
            if getattr(self, '_ignore_synthetic_release', False):
                logger.debug("[FDC] Ignoring OS synthetic mouse release during window mapping.")
                return False 
                
            if self._dragging_state == DragState.floating_widget:
                self._set_state(DragState.inactive)

                if self._mouse_event_handler is not None:
                    try:
                        self._mouse_event_handler.releaseMouse()
                    except RuntimeError:
                        pass
                    self._mouse_event_handler = None
                
                # Only remove the transient drag-time event filter — never the
                # permanent chromeless-resize filter.
                if self._permanent_filter_installed:
                    # We were not using a transient filter; nothing to remove.
                    pass
                else:
                    app = QApplication.instance()
                    if app is not None:
                        app.removeEventFilter(self)
                self._frameless_drag_filter = False

                QTimer.singleShot(0, self._end_programmatic_drag)
                return False

            if (self._frameless_drag_filter
                    and self._dragging_state == DragState.mouse_pressed):
                # A click on the frameless title bar that ended without a
                # drag — the OS-delivered release may have landed on the
                # content or outside the window.  Reset the press state so
                # the float can never get stuck in mouse_pressed.
                self._set_state(DragState.inactive)
                self._titlebar_drag_start = None
                self._remove_frameless_drag_filter()
                return False

        return super().eventFilter(watched, event)

    def _handle_titlebar_drag(self, obj: QObject, event: QEvent) -> bool:
        """Drive the dock-drag machinery from the frameless title bar.

        The qframelesswindow title bar's plain OS move loop
        (``startSystemMove`` / ``WM_SYSCOMMAND SC_MOVE``) never delivers the
        ``NonClientAreaMouseButtonPress`` events the dock drag relies on —
        the drop overlay never appears and the float cannot be redocked
        when dragged by its custom title bar.

        This keeps the OS move loop (smooth dragging, Aero snap, DWM
        animation — exactly like a regular QMainWindow float) but arms the
        dock-drag state machine around it: the press sets ``mouse_pressed``
        and installs a transient app filter, the OS loop moves the window
        (moveEvent feeds the drop overlay), the app filter catches the
        OS-delivered release wherever it lands, and the drag finalizes
        through the shared path.  If the OS move loop is unavailable it
        falls back to a manual grabMouse + move_floating drag.
        """
        etype = event.type()
        state = self._dragging_state

        if etype == QEvent.MouseButtonPress:
            if event.button() != Qt.LeftButton:
                return False
            if not getattr(self.titleBar, "canDrag", lambda p: True)(
                    event.position().toPoint()):
                return False  # press on a min/max/close button
            self._titlebar_drag_start = event.position().toPoint()
            self._drag_start_mouse_position = event.position().toPoint()
            self._set_state(DragState.mouse_pressed)
            # Catch the OS-delivered release anywhere (title bar, content
            # or outside the window) and route it through the state machine.
            app = QApplication.instance()
            if app is not None and not self._frameless_drag_filter:
                app.installEventFilter(self)
                self._frameless_drag_filter = True
            try:
                from qframelesswindow.utils import startSystemMove
                startSystemMove(self, event.globalPosition().toPoint())
                self._os_move_active = True
            except Exception:
                # OS move loop unavailable — the move branch below falls
                # back to a manual grabMouse + move_floating drag.
                self._os_move_active = False
            return True

        if etype == QEvent.MouseMove:
            if state == DragState.mouse_pressed:
                start = getattr(self, "_titlebar_drag_start", None)
                if start is not None and not self._os_move_active:
                    # startSystemMove failed — manual fallback drag.
                    dist = (event.position().toPoint() - start).manhattanLength()
                    if dist >= start_drag_distance():
                        self._titlebar_drag_start = None
                        self._drag_start_mouse_position = start
                        self._mouse_event_handler = self.titleBar
                        self._set_state(DragState.floating_widget)
                        self.titleBar.grabMouse()
                        self.move_floating()
                return True
            if state == DragState.floating_widget:
                # During the OS move loop the float moves itself; this only
                # runs in the manual fallback.
                self.move_floating()
                return True
            return False

        if etype == QEvent.MouseButtonRelease:
            if state in (DragState.mouse_pressed, DragState.floating_widget):
                was_dragging = state == DragState.floating_widget
                self._set_state(DragState.inactive)
                if self._mouse_event_handler is not None:
                    try:
                        self._mouse_event_handler.releaseMouse()
                    except RuntimeError:
                        pass
                    self._mouse_event_handler = None
                if was_dragging:
                    QTimer.singleShot(0, self._finalize_drag)
                else:
                    self._remove_frameless_drag_filter()
                self._titlebar_drag_start = None
                self._os_move_active = False
                return True
            return False

        return False

    def _remove_frameless_drag_filter(self):
        """Remove the transient app filter installed for frameless drags."""
        if self._frameless_drag_filter:
            app = QApplication.instance()
            if app is not None and not self._permanent_filter_installed:
                app.removeEventFilter(self)
            self._frameless_drag_filter = False

    # ------------------------------------------------------------------
    # Non-Windows chromeless resize
    # ------------------------------------------------------------------
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

    # ── Chromeless rounded-corner mask ────────────────────────────────

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


    # ─────────────────────────────────────────────────────────────────────
    #  Public accessors
    # ─────────────────────────────────────────────────────────────────────

    def dock_container(self) -> 'DockContainerWidget':
        return self._dock_container

    def is_closable(self) -> bool:
        return DockWidgetFeature.closable in self._dock_container.features()

    def _update_close_button_state(self, *args):
        """Enable (and restore) or disable (and dim) the title-bar close
        button based on whether every dock widget in this float is closable.

        An unclosable dock widget anywhere in the float makes the whole
        window unclosable (see ``is_closable``), so the close button is
        disabled and its icon dimmed — clicking it does nothing instead of
        silently ignoring the close.

        The button is a qframelesswindow ``TitleBarButton`` with custom
        painting (no built-in disabled rendering): disabling it stops Qt from
        delivering mouse press/click events, and we restyle it like the
        standard title-bar buttons — dimmed normal icon (``button_disable_clr``
        or a translucent version of the current colour) and the theme's
        ``button_hover_bg`` highlight instead of the system close-red — so a
        hovered disabled button never glows red.  The original colours are
        remembered so the system close styling returns when the float becomes
        closable again.  ``*args`` tolerates the ``features_changed`` payload.
        """
        tb = getattr(self, "titleBar", None)
        close_btn = getattr(tb, "closeBtn", None)
        if close_btn is None:
            return
        closable = self.is_closable()
        close_btn.setEnabled(closable)
        style_mgr = getattr(self, "_style_mgr", None)

        if closable:
            # Restore the system close styling: normal icon colour, red hover
            # background, white hover/pressed icon, light-red pressed bg.
            if self._close_btn_normal_color is not None:
                close_btn._normalColor = QColor(self._close_btn_normal_color)
                self._close_btn_normal_color = None
            if self._close_btn_system_hover is not None:
                (hover_bg, hover_fg, pressed_bg, pressed_fg) = \
                    self._close_btn_system_hover
                close_btn._hoverBgColor = hover_bg
                close_btn._hoverColor = hover_fg
                close_btn._pressedBgColor = pressed_bg
                close_btn._pressedColor = pressed_fg
                self._close_btn_system_hover = None
        else:
            # Capture the true normal colour the first time — or re-capture
            # if the styler re-themed the button while it was disabled (the
            # styler runs after the first dock-area signal, so the first
            # disable may have captured the pre-theme default).
            current = QColor(close_btn._normalColor)
            if (self._close_btn_normal_color is None
                    or current != QColor(self._close_btn_normal_color)):
                self._close_btn_normal_color = current
            # Same for the system close hover/pressed colours (only captured
            # once — the styler never touches them, so they stay the
            # qframeless defaults: red bg / white icons).
            if self._close_btn_system_hover is None:
                self._close_btn_system_hover = (
                    QColor(close_btn._hoverBgColor),
                    QColor(close_btn._hoverColor),
                    QColor(close_btn._pressedBgColor),
                    QColor(close_btn._pressedColor),
                )
            disabled = None
            if style_mgr is not None:
                disabled = style_mgr.get(
                    DockStyleCategory.TITLE_BAR, "button_disable_clr", None)
            if disabled is not None:
                close_btn._normalColor = QColor(disabled)
            else:
                # Fallback: a translucent version of the normal icon colour.
                dimmed = QColor(self._close_btn_normal_color)
                dimmed.setAlpha(int(dimmed.alpha() * 0.4))
                close_btn._normalColor = dimmed

            # Hover/pressed highlight: use the standard title-bar button
            # highlight (theme button_hover_bg + button_color) exactly like
            # the min/max buttons, never the system close-red.
            if style_mgr is not None:
                btn_col = style_mgr.get(
                    DockStyleCategory.TITLE_BAR, "button_color")
                btn_hover = style_mgr.get(
                    DockStyleCategory.TITLE_BAR, "button_hover_bg")
                if btn_col:
                    close_btn._hoverColor = QColor(btn_col)
                    close_btn._pressedColor = QColor(btn_col)
                if btn_hover:
                    close_btn._hoverBgColor = QColor(btn_hover)
                    pressed_bg = QColor(btn_hover)
                    pressed_bg.setAlpha(
                        min(255, int(pressed_bg.alpha() * 1.5)))
                    close_btn._pressedBgColor = pressed_bg
        close_btn.update()

    def _sync_feature_signals(self):
        """Follow each contained dock widget's ``features_changed`` signal so
        toggling closable at runtime updates the close button immediately."""
        try:
            widgets = set(self._dock_container.dock_widgets())
        except RuntimeError:
            return
        for w in widgets:
            if w in self._feature_synced_widgets:
                continue
            try:
                w.features_changed.connect(self._update_close_button_state)
            except (RuntimeError, TypeError):
                pass
            self._feature_synced_widgets.add(w)

    def has_top_level_dock_widget(self) -> bool:
        return self._dock_container.has_top_level_dock_widget()

    def top_level_dock_widget(self) -> 'DockWidget':
        return self._dock_container.top_level_dock_widget()

    def dock_widgets(self) -> list:
        return self._dock_container.dock_widgets()