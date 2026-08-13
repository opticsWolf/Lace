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

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QCursor, QPalette, QMoveEvent
from PySide6.QtWidgets import QApplication, QBoxLayout, QWidget

from lace.enums import DockFlags, DragState, DockWidgetArea, WidgetState
from lace.dock_container_widget import DockContainerWidget

from lace.dock_styled import DockStyled
from lace.dock_theme import DockStyleCategory
from lace.floating_behaviour import FloatingContainerBehaviour, _EDGE_NONE

if TYPE_CHECKING:
    from lace import DockAreaWidget, DockWidget, DockManager

logger = logging.getLogger(__name__)

_z_order_counter = 0


class FloatingDockContainer(FloatingContainerBehaviour, QWidget, DockStyled):
    """Floating dock container on a native OS window frame.

    The behaviour mixin comes first: it overrides closeEvent, resizeEvent,
    hideEvent and deleteLater, which QWidget also defines, so listing it after
    QWidget would let Qt's versions win. See :mod:`lace.floating_behaviour`.
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

        super().__init__(dock_manager.root_container())
        
        self._dragging_state = DragState.inactive
        self._drag_start_mouse_position = QPoint()
        self._drop_container: DockContainerWidget = None
        self._single_dock_area: 'DockAreaWidget' = None
        self._mouse_event_handler: QWidget = None
        self._dock_container: DockContainerWidget = None
        self._pending_restore_geometry: Optional['QRect'] = None
        global _z_order_counter
        _z_order_counter += 1
        self._z_order_index = _z_order_counter
        self._dock_manager = dock_manager
        
        # Apply the dedicated floating-window icon if configured (see
        # DockManager.set_floating_window_icon), else fall back to the
        # application icon and finally the root window icon.
        floating_icon = dock_manager.resolve_floating_window_icon()
        if not floating_icon.isNull() and not floating_icon.pixmap(16, 16).isNull():
            self.setWindowIcon(floating_icon)
            if QApplication.instance() and QApplication.instance().windowIcon().isNull():
                QApplication.instance().setWindowIcon(floating_icon)

        dock_container = DockContainerWidget(dock_manager, self)
        self._dock_container = dock_container
        dock_container.destroyed.connect(self._destroyed)
        dock_container.dock_areas_added.connect(self.on_dock_areas_added_or_removed)
        self._chromeless = self._test_config_flag(DockFlags.chromeless_float)
        self._corner_radius = 0.0
        flags = Qt.Window | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint
        if self._chromeless:
            flags |= Qt.FramelessWindowHint
        self.setWindowFlags(flags)
        if self._chromeless:
            self.setAttribute(Qt.WA_TranslucentBackground)
        
        layout = QBoxLayout(QBoxLayout.TopToBottom)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

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

        # --- Resizing state (cross-platform) ---------------------------------
        self._is_resizing = False
        self._resize_dir = _EDGE_NONE
        self._resize_press_pos = QPoint()        # Global press position
        self._resize_press_geom = QRect()        # Geometry at press time
        self._resize_active_widget: Optional[QWidget] = None  # widget under cursor

        # Permanent event-filter tracking — only meaningful on non-Windows.
        self._permanent_filter_installed = False

        # Install permanent filter when chromeless.
        if self._chromeless:
            self._install_permanent_filter()
        
    def _install_permanent_filter(self) -> None:
        """Install self as a permanent application-level event filter.

        Used only on non-Windows platforms to provide chromeless resize
        behavior without altering the widget layout.
        """
        if self._permanent_filter_installed:
            return
        app = QApplication.instance()
        if app is not None:
            app.installEventFilter(self)
            self._permanent_filter_installed = True

    def _remove_permanent_filter(self) -> None:
        """Remove the permanent application-level event filter if installed."""
        if not self._permanent_filter_installed:
            return
        app = QApplication.instance()
        if app is not None:
            try:
                app.removeEventFilter(self)
            except RuntimeError:
                pass
        self._permanent_filter_installed = False
        # Reset transient resize state — but never tear down a live drag.
        self._is_resizing = False
        self._resize_dir = _EDGE_NONE
        self._resize_active_widget = None

    def _end_swallowed_release(self):
        """Finish a drag whose release was swallowed by the synthetic-release
        guard.  The button is already up, so this is the real release — reset
        the state machine and finalize exactly like the normal release path,
        so no stale mouse grab / drag state / app filter survives to eat the
        next click (e.g. the first press of a double-click elsewhere)."""
        self._set_state(DragState.inactive)
        if self._mouse_event_handler is not None:
            try:
                self._mouse_event_handler.releaseMouse()
            except RuntimeError:
                pass
            self._mouse_event_handler = None
        app = QApplication.instance()
        if app is not None and not self._permanent_filter_installed:
            app.removeEventFilter(self)
        QTimer.singleShot(0, self._finalize_drag)

    # ─────────────────────────────────────────────────────────────────────
    #  Window flags / native frame
    # ─────────────────────────────────────────────────────────────────────

    def update_window_flags_from_config(self):
        self._chromeless = self._test_config_flag(DockFlags.chromeless_float)
        flags = Qt.Window | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint
        if self._chromeless:
            flags |= Qt.FramelessWindowHint
        if self.windowFlags() != flags:
            # Save client-area geometry so content size is preserved across
            # the flag change (setWindowFlags destroys/recreates the native
            # window frame, resetting geometry).
            saved_geometry = self.geometry()
            was_visible = self.isVisible()
            self.setWindowFlags(flags)
            # Sync translucent background with chromeless state.
            self.setAttribute(Qt.WA_TranslucentBackground, self._chromeless)
            if was_visible:
                self.show()
            # Restore the saved client-area geometry and force a full repaint.
            QTimer.singleShot(0, self._do_restore_geometry)
            self._pending_restore_geometry = saved_geometry
        else:
            self._pending_restore_geometry = None

        # Sync permanent event-filter state with the chromeless flag.
        if self._chromeless:
            self._install_permanent_filter()
        else:
            self._remove_permanent_filter()

    def _do_restore_geometry(self):
        """Restore saved client-area geometry after setWindowFlags (deferred)."""
        geom = getattr(self, '_pending_restore_geometry', None)
        if geom is None:
            return
        self._pending_restore_geometry = None
        self.setGeometry(geom)

        # setWindowFlags() destroys and recreates the native window handle, and
        # the new one does not carry the DWM dark-mode attribute. Re-push the
        # palette and re-set that attribute for this window; deferred so the
        # handle is fully registered with DWM first.
        #
        # There used to be a qapp.setStyle(qapp.style().objectName()) here as
        # well, which re-polished every widget in the process. DockThemeBridge
        # already owns style application (it applies Fusion to the target), so
        # the window does not need to re-style the application to fix its own
        # frame.
        if not self._chromeless:
            QTimer.singleShot(0, self._apply_dock_palette_to_window)

        # Re-apply the chromeless rounded-corner mask so corners render
        # correctly after the flag change (resizeEvent won't fire since
        # geometry is restored to the same value).
        if self._chromeless:
            self._update_chromeless_mask()
        else:
            self.clearMask()
        # Force a full redraw of the window and its children.
        self.repaint()

    def _apply_dock_palette_to_window(self) -> None:
        """Re-push the dock theme palette onto this window's new native handle.

        After setWindowFlags() the recreated handle does not inherit the DWM
        dark-mode attribute, so the title bar comes back light on a dark theme.

        This used to be forced with ``qapp.setPalette()`` plus a toggle of the
        global ``QStyleHints.colorScheme`` (to the opposite scheme and back,
        because setting the current one is a no-op). Both are process-wide: the
        palette call re-polished every widget in the application, and the
        toggle emitted ``colorSchemeChanged`` twice, once with the *wrong*
        scheme — enough to make an application using
        ``ThemeManager.install_listener()`` flip to its light theme and back.
        Toggling one dock flag visibly strobed the whole UI.
        """
        palette = self.palette()
        try:
            from lace.dock_theme import resolve_dock_colors, build_dock_palette
            palette = build_dock_palette(is_panel=False, colors=resolve_dock_colors())
            self.setPalette(palette)
        except Exception:
            logger.debug("Dock theme unavailable; keeping the current palette",
                         exc_info=True)

        is_dark = palette.color(QPalette.ColorRole.Window).lightness() < 128
        self._apply_dwm_dark_frame(is_dark)

    def _apply_dwm_dark_frame(self, is_dark: bool) -> None:
        """Set the immersive dark-mode frame attribute on *this* window only."""
        if sys.platform != "win32":
            handle = self.windowHandle()
            if handle is not None:
                handle.requestUpdate()
            return

        try:
            import ctypes

            hwnd = int(self.winId())
            if not hwnd:
                return
            value = ctypes.c_int(1 if is_dark else 0)
            # DWMWA_USE_IMMERSIVE_DARK_MODE: 20 since Windows 10 build 19041,
            # 19 on the earlier builds that supported it at all.
            for attribute in (20, 19):
                if ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    ctypes.c_void_p(hwnd), ctypes.c_int(attribute),
                    ctypes.byref(value), ctypes.sizeof(value)
                ) == 0:
                    return
            logger.debug("DWM rejected the dark-frame attribute for this window")
        except Exception:
            logger.debug("DWM dark-frame update unavailable", exc_info=True)

    # ─────────────────────────────────────────────────────────────────────
    #  Drag entry point
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

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
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
                # A release that arrives while the synthetic-release guard is
                # armed.  If the button is already up this is the REAL release
                # (the spurious one produced by the grabMouse handoff during
                # window mapping arrives while the button is still held).
                # Finish the drag through the normal path so the float never
                # keeps a stale mouse grab / drag state that would eat the
                # next click — e.g. the first press of a double-click on the
                # main window title bar ("stale" double-click-to-maximize).
                if QApplication.mouseButtons() == Qt.NoButton:
                    logger.debug("[FDC] Swallowed release with button up — "
                                 "real release, finalizing drag")
                    self._end_swallowed_release()
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

                QTimer.singleShot(0, self._end_programmatic_drag)
                return False

        return super().eventFilter(watched, event)
