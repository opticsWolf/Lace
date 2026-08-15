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
from PySide6.QtGui import QColor, QCursor, QMoveEvent
from PySide6.QtWidgets import QApplication, QBoxLayout, QWidget

from lace.enums import DockFlags, DragState, DockWidgetArea, WidgetState
from lace.dock_container_widget import DockContainerWidget

from lace.dock_styled import DockStyled
from lace.dock_theme import DockStyleCategory
from lace.floating_behaviour import FloatingContainerBehaviour, _EDGE_NONE
from lace.frameless_window import FramelessLaceWindow, _resolve_title_bar
from lace.frameless_titlebar import FramelessTitleBarStyler
from lace.util import (is_window_maximized, pre_snap_geometry, restore_window,
                       start_drag_distance)

if TYPE_CHECKING:
    from lace import DockAreaWidget, DockWidget, DockManager

logger = logging.getLogger(__name__)

_z_order_counter = 0


class FramelessFloatingDockContainer(FloatingContainerBehaviour,
                                     FramelessLaceWindow, DockStyled):
    """Floating dock container backed by a frameless window.

    Inherits from :class:`FramelessLaceWindow` (PySideSix-Frameless-Window)
    so floating windows always get the custom title bar, cross-platform
    resize borders (WM_NCHITTEST / LinuxMoveResize / native macOS handling)
    and DWM shadow instead of a native OS title bar.  The custom title bar
    is themed through :class:`FramelessTitleBarStyler`.

    Everything that does not depend on the window chrome — the drag state
    machine, drop-overlay tracking, title bookkeeping, state persistence —
    lives in :class:`~lace.floating_behaviour.FloatingContainerBehaviour`,
    which the native-frame container shares. The mixin comes first in the
    MRO because it overrides methods the Qt base also defines.
    """
    STYLE_CATEGORIES = (DockStyleCategory.CORE,)

    # Every attribute eventFilter reads, defaulted at class level so the
    # filter is safe on a half-built object.
    #
    # qframelesswindow's Linux base installs this window as an
    # *application-wide* event filter from inside its own __init__
    # (LinuxFramelessWindowBase._initFrameless), i.e. from our super().__init__()
    # below -- long before __init__ assigns these. Everything after that line
    # pumps events (setWindowFlags recreates the native handle, the container
    # and title bar are built, the styler runs), so eventFilter *will* be
    # called in that window. An AttributeError raised there does not stay
    # local: it propagates out through Qt's event dispatch, aborts this
    # constructor, and leaves an orphan C++ widget installed as an app filter
    # for the rest of the process -- after which every widget creation in the
    # program fails with "QMainWindow returned NULL without setting an
    # exception". Only Linux installs that filter, which is why the fault
    # never appeared on Windows.
    _permanent_filter_installed = False
    _frameless_drag_filter = False
    _os_move_active = False
    _titlebar_drag_start = None
    _dragging_state = DragState.inactive
    _ignore_synthetic_release = False

    def __init__(self, *, dock_area: 'DockAreaWidget' = None,
                 dock_widget: 'DockWidget' = None,
                 dock_manager: 'DockManager' = None,
                 title_bar=None):
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
        # Close-button disabled state: remembered normal icon colour and the
        # system close hover/pressed colours (so they can be restored when the
        # float becomes closable again), plus the sets of dock areas and dock
        # widgets whose membership/feature/view signals we are following.
        self._close_btn_normal_color = None
        self._close_btn_system_hover = None
        self._feature_synced_widgets = set()
        self._area_synced_areas = set()
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
        dock_container.dock_areas_removed.connect(self.on_dock_areas_added_or_removed)
        self._chromeless = self._test_config_flag(DockFlags.chromeless_float)
        self._corner_radius = 0.0

        # ── Frameless window setup ─────────────────────────────────────────
        # Floating containers are parented widgets, so promote this to a real
        # top-level frameless window first (the frameless base only ORs
        # Qt.FramelessWindowHint into the existing flags).
        self.setWindowFlags(self._window_flags())
        # setWindowFlags() (re)creates the native window handle — re-apply the
        # DWM shadow / animation registered by the frameless base.
        updater = getattr(self, "updateFrameless", None)
        if updater is not None:
            try:
                updater()
            except Exception:
                pass
        # ...and the taskbar ex-style, which the new handle does not inherit.
        self._apply_taskbar_presence()

        # Swap in a custom title bar if the DockManager (or constructor
        # argument) requests one; otherwise use the standard Lace title bar.
        # The standard bar shows the window icon and title text like the main
        # window, and its synchronous double-click-to-maximize avoids the
        # async SC_MAXIMIZE bug in qframelesswindow on Windows.
        self.setTitleBar(self._create_title_bar(title_bar))
        # StandardTitleBar only refreshes its icon label on windowIconChanged,
        # and the icon was already set before the swap — push it explicitly so
        # the floating window shows the app icon.
        icon_setter = getattr(self.titleBar, "setIcon", None)
        if icon_setter is not None:
            icon_setter(self.windowIcon())
        self._sync_minimize_button()
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
        # normal icon colour) on every theme change, so refresh the remembered
        # normal colour and re-apply our disabled state after each styler pass.
        self._titlebar_styler._after_refresh = self._after_styler_refresh

        # Sync the title-bar close button with the float's closability now
        # that the dock areas / widgets are in place.  _after_styler_refresh
        # re-captures the themed normal colour (overwriting any colour
        # captured by dock-area signals that fired before the styler ran) and
        # then applies the disabled state if needed.
        self._after_styler_refresh()

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

    def _create_title_bar(self, title_bar):
        """Resolve the title-bar descriptor for this floating container.

        The descriptor may come from the explicit *title_bar* argument, the
        owning :class:`.dock_manager.DockManager` (via its
        ``floating_title_bar`` attribute), or fall back to the standard Lace
        title bar.
        """
        if title_bar is None:
            manager = getattr(self, '_dock_manager', None)
            if manager is not None:
                title_bar = getattr(manager, 'floating_title_bar', None)
        return _resolve_title_bar(title_bar, self)

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

    # ─────────────────────────────────────────────────────────────────────
    #  Window flags / frameless chrome
    # ─────────────────────────────────────────────────────────────────────

    def _window_flags(self) -> Qt.WindowType:
        """The window flags this float wants, given the current config.

        The frameless variant always keeps Qt.FramelessWindowHint (the base
        class sets it); the native OS title bar never returns. The minimize
        hint follows the taskbar flag — see :meth:`_sync_minimize_button`.
        """
        flags = (Qt.Window | Qt.FramelessWindowHint |
                 Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        if self._wants_taskbar_button():
            flags |= Qt.WindowMinimizeButtonHint
        return flags

    def _sync_minimize_button(self) -> None:
        """Show the title bar's minimize button only if the float can come back.

        qframelesswindow builds a minimize button into every title bar and
        wires it to showMinimized(), and its addWindowAnimation() ORs
        WS_MINIMIZEBOX onto the handle, so minimizing works whether or not the
        window has anywhere to minimize *to*. Without a taskbar button it has
        nowhere — the float vanishes and is not in Alt-Tab either.

        Hiding the button also widens the draggable region: qframelesswindow's
        _isDragRegion() measures only the visible buttons.
        """
        min_button = getattr(self.titleBar, "minBtn", None)
        if min_button is not None:
            min_button.setVisible(self._wants_taskbar_button())

    def update_window_flags_from_config(self):
        self._chromeless = self._test_config_flag(DockFlags.chromeless_float)
        flags = self._window_flags()
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
            # Set the taskbar ex-style while the window is still hidden, so the
            # show() below is what the shell sees.
            self._apply_taskbar_presence()
            if was_visible:
                self.show()
            # Restore the saved client-area geometry and force a full repaint.
            QTimer.singleShot(0, self._do_restore_geometry)
            self._pending_restore_geometry = saved_geometry
        else:
            self.setAttribute(Qt.WA_TranslucentBackground, self._chromeless)
            self._pending_restore_geometry = None
            self._apply_taskbar_presence()

        # The custom title bar follows the chromeless flag: chromeless floats
        # are bare surfaces without any title bar.
        tb = getattr(self, "titleBar", None)
        if tb is not None:
            if self._chromeless:
                tb.hide()
            else:
                tb.show()
                tb.raise_()
            self._sync_minimize_button()

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

            # Arm the guard against the OS synthetic release that can be
            # produced when a NEW window is mapped during the drag.  Only
            # needed for not-yet-visible floats: an already-visible float
            # (re-drag of a floating window) does not map, so a real quick
            # release must never be swallowed (a swallowed release leaves a
            # stale mouse grab that steals the next click anywhere — e.g. the
            # main window title bar — breaking double-click-to-maximize).
            if not self.isVisible():
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
            # If the OS move loop consumed the release, the float can be left
            # stuck in a drag state.  A focus/activation change with no button
            # held means the user has finished interacting elsewhere; end any
            # stale drag before it can jump on the next move.
            if (self._dragging_state != DragState.inactive
                    and QApplication.mouseButtons() == Qt.NoButton):
                logger.debug('[FDC] ActivationChange with no button held — canceling stale drag')
                self._cancel_stale_drag()
        if event.type() == QEvent.WindowStateChange and self._dock_container:
            # Update maximize/restore icon when the OS window state changes
            for dock_area in self._dock_container.opened_dock_areas():
                dock_area._update_title_bar_button_states()

    def moveEvent(self, event: QMoveEvent):
        super().moveEvent(event)
        state = getattr(self, '_dragging_state', DragState.inactive)
        # Ultimate stuck-state safety net: a drag with no button held is stale
        # (e.g. the OS move loop swallowed the release).  Cancel it before any
        # further moves cause a phantom jump or drop.
        if state != DragState.inactive and QApplication.mouseButtons() == Qt.NoButton:
            logger.debug('[FDC] moveEvent with no button held — canceling stale drag')
            self._cancel_stale_drag()
            return
        if state == DragState.mouse_pressed:
            self._set_state(DragState.floating_widget)
            self._update_drop_overlays(QCursor.pos())
        elif state == DragState.floating_widget:
            self._update_drop_overlays(QCursor.pos())

    def event(self, e: QEvent) -> bool:
        """Handle native (OS) non-client events for the frameless variant.

        The frameless container uses a custom title-bar widget and drives
        dock-drag via :meth:`_handle_titlebar_drag` / :meth:`eventFilter`.  Non-
        client events therefore come from the OS resize borders (WM_NCHITTEST
        edges), not from a native title bar.  We must NOT start a dock drag on
        ``NonClientAreaMouseButtonPress`` here — that would arm the drag state
        machine for a resize border click and can leave the float stuck in a
        drag state, causing a subsequent click elsewhere to finalize and drop
        the float into another container (or move it off-screen).

        We keep the release/dblclick/resize safety nets so a stray release can
        always clear a stuck state.
        """
        state = getattr(self, '_dragging_state', DragState.inactive)
        etype = e.type()
        if etype == QEvent.NonClientAreaMouseButtonPress:
            # Never start a dock drag from a resize border.  If a stale drag is
            # still armed (e.g. the OS move loop consumed its release), cancel
            # it now rather than letting it persist.
            if state != DragState.inactive:
                logger.debug('[FDC] NonClientAreaMouseButtonPress with stale drag state %s — canceling', state)
                self._cancel_stale_drag()
        elif state == DragState.mouse_pressed:
            if etype == QEvent.NonClientAreaMouseButtonDblClick:
                logger.debug('FloatingWidget.event QEvent.NonClientAreaMouseButtonDblClick')
                self._set_state(DragState.inactive)
            elif etype == QEvent.Resize:
                if not self.isMaximized():
                    self._set_state(DragState.inactive)
            elif etype == QEvent.NonClientAreaMouseButtonRelease:
                # Safety net so non-drag clicks don't leave window stuck in mouse_pressed.
                logger.debug('FloatingWidget.event QEvent.NonClientAreaMouseButtonRelease')
                self._set_state(DragState.inactive)
        elif state == DragState.floating_widget:
            if etype == QEvent.NonClientAreaMouseButtonRelease:
                logger.debug('FloatingWidget.event QEvent.NonClientAreaMouseButtonRelease')
                self._set_state(DragState.inactive)
                QTimer.singleShot(0, self._finalize_drag)

        return super().event(e)

        # REMOVED: toggle_view(False) loop
        # Recreating the frameless window (e.g. via setWindowOpacity during drops) 
        # triggers QHideEvent. Closing widgets here incorrectly ripped them from the layout!

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        # --- Frameless title-bar drag (custom mode) ------------------------
        # self.titleBar is safe this early: the frameless base assigns it just
        # before it installs this object as an app-wide filter (see the
        # class-level defaults above for what "this early" means here).
        if watched is self.titleBar:
            if self._handle_titlebar_drag(watched, event):
                return True

        # --- Permanent path: chromeless resize on macOS / Linux --------------
        if self._permanent_filter_installed:
            if self._handle_resize_event(watched, event):
                return True

        # --- Existing drag / float handling goes here ------------------------
        # A new press starting elsewhere while a drag is still armed means the
        # previous drag's release was consumed (e.g. by the OS move loop) and
        # never reached the state machine.  Without this, the new interaction's
        # release would be mistaken for the drag's release and finalize the
        # drag into whatever container the cursor happens to be over — e.g.
        # clicking a dock widget in another floating window would drop this float
        # into it and delete it ("vanishing").  End the stale drag at the press
        # instead, and let the press reach its real target.
        #
        # Don't cancel if the press is on this float's own title bar:
        # _handle_titlebar_drag already manages that press (it cancels any stale
        # drag and re-arms the state machine itself), so cancelling here would
        # undo the press it just armed on Windows.
        if (event.type() == QEvent.MouseButtonPress
                and self._dragging_state != DragState.inactive
                and watched is not self.titleBar):
            self._cancel_stale_drag()
            return False

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
                self._frameless_drag_filter = False
                # This is the path an OS-move drag ends on when the modal
                # loop swallowed the title bar's own release, so it owes the
                # same cleanup _handle_titlebar_drag's release branch does.
                self._os_move_active = False

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
        self._titlebar_drag_start = None
        self._os_move_active = False
        self._remove_frameless_drag_filter()
        # Also remove the transient app filter installed by start_floating()
        # (tab / dock-area title-bar drags); removeEventFilter on a filter
        # that is not installed is a no-op, so this is safe to always call.
        if not self._permanent_filter_installed:
            app = QApplication.instance()
            if app is not None:
                app.removeEventFilter(self)
        QTimer.singleShot(0, self._finalize_drag)

    def _cancel_stale_drag(self):
        """End a drag whose release was consumed (e.g. by the OS move loop)
        without dropping into a container.

        Called when a new mouse press starts while a drag is still armed, so
        the new interaction's release can never be mistaken for the drag's
        release and trigger a phantom drop.
        """
        self._set_state(DragState.inactive)
        if self._mouse_event_handler is not None:
            try:
                self._mouse_event_handler.releaseMouse()
            except RuntimeError:
                pass
            self._mouse_event_handler = None
        self._titlebar_drag_start = None
        self._os_move_active = False
        self._remove_frameless_drag_filter()
        if self._drop_container is not None:
            self._drop_container = None
            if self._dock_manager:
                self._dock_manager.container_overlay().hide_overlay()
                self._dock_manager.dock_area_overlay().hide_overlay()

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
            # A previous drag may still be armed (its release was consumed by
            # the OS move loop) — end it cleanly before starting a new drag so
            # stale drop-overlay state cannot linger.
            if self._dragging_state != DragState.inactive:
                self._cancel_stale_drag()
            # A new press means no OS move loop of ours is still running.
            # Asserting that here rather than trusting the previous drag to
            # have cleared it: the loop swallows the release that would have,
            # and the app-filter path that ends the drag instead reset only
            # the drag state. A leaked True made every later move skip the
            # drag-start branch below and get consumed, so the float could
            # never be dragged again — including after an Aero snap, which is
            # how the loop usually ends.
            self._os_move_active = False
            self._titlebar_drag_start = event.position().toPoint()
            self._drag_start_mouse_position = event.position().toPoint()
            self._set_state(DragState.mouse_pressed)
            # Catch the OS-delivered release anywhere (title bar, content
            # or outside the window) and route it through the state machine.
            app = QApplication.instance()
            if app is not None and not self._frameless_drag_filter:
                app.installEventFilter(self)
                self._frameless_drag_filter = True
            # On Windows the qframeless title bar starts its native OS move
            # loop on mouse move, not on press.  If we consume the press (and
            # start the move loop) here, the title bar never sees the press
            # and its double-click-to-maximize shortcut breaks: Qt generates
            # MouseButtonDblClick only from the press sequence it observes on
            # the widget, and the OS move loop swallows the release, leaving a
            # stale drag whose grab eats the next click elsewhere (e.g. the
            # main window title bar).  Arm the drag state, but let the press
            # reach the title bar on Windows; the first move beyond the drag
            # threshold below starts the real drag.  On other platforms the
            # title bar starts the move on press, so we must take control of
            # the press ourselves.
            if sys.platform == "win32":
                return False
            try:
                from qframelesswindow.utils import startSystemMove
                # Here the press starts the move, so the rip-out has to
                # happen here rather than at the drag threshold.
                self._restore_under_cursor(event.globalPosition().toPoint())
                startSystemMove(self, event.globalPosition().toPoint())
                self._os_move_active = True
            except Exception:
                # OS move loop unavailable — the move branch below falls
                # back to a manual grabMouse + move_floating drag.
                self._os_move_active = False
            return True

        if etype == QEvent.MouseButtonDblClick:
            # A double-click on the draggable part of the title bar must
            # toggle maximization, not arm a drag.  Cancel any pending
            # press/drag so the title bar's own mouseDoubleClickEvent is the
            # only behaviour.
            if self._dragging_state != DragState.inactive:
                self._cancel_stale_drag()
            return False

        if etype == QEvent.MouseMove:
            if state == DragState.mouse_pressed:
                start = getattr(self, "_titlebar_drag_start", None)
                # On non-Windows the press already started the OS move loop
                # (_os_move_active), so a (stale) move must not re-enter it;
                # on Windows the loop starts here, past the drag threshold.
                if start is not None and not self._os_move_active:
                    dist = (event.position().toPoint() - start).manhattanLength()
                    if dist >= start_drag_distance():
                        self._titlebar_drag_start = None
                        self._drag_start_mouse_position = start
                        self._set_state(DragState.floating_widget)
                        # A maximized window has to come loose before anyone
                        # tries to move it — the OS will not move it, and the
                        # gesture is meant to un-maximize.
                        self._restore_under_cursor(
                            event.globalPosition().toPoint())
                        try:
                            from qframelesswindow.utils import startSystemMove
                            startSystemMove(self, event.globalPosition().toPoint())
                            self._os_move_active = True
                        except Exception:
                            # OS move loop unavailable — manual fallback drag.
                            self._os_move_active = False
                            self._mouse_event_handler = self.titleBar
                            self.titleBar.grabMouse()
                            self.move_floating()
                        return True
                # Sub-threshold move: consume it so the title bar cannot start
                # its own native move on a tiny wiggle.
                return True
            if state == DragState.floating_widget:
                # If the OS move loop was used, the OS already moved the window.
                # Manually re-positioning here with stale local coordinates would
                # make the float jump to the wrong place.
                if not self._os_move_active:
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
                # Always remove the transient app filter here — the drag is
                # over.  If it was a real drag we still finalize below, but the
                # filter must not outlive this interaction.
                self._remove_frameless_drag_filter()
                if was_dragging:
                    QTimer.singleShot(0, self._finalize_drag)
                self._titlebar_drag_start = None
                self._os_move_active = False
                return True
            return False

        return False

    def _restore_under_cursor(self, global_pos: QPoint) -> None:
        """Un-maximize or un-snap, grab kept where it is, before an OS move.

        Windows gives native frames this for free: dragging a maximized or
        Aero-snapped window by its caption pulls it loose under the pointer.
        That lives in the ``WM_NCLBUTTONDOWN`` / ``HTCAPTION`` path, which a
        client-area title bar never receives — and qframelesswindow's move is
        ``WM_SYSCOMMAND SC_MOVE``, which Windows refuses outright for either
        state. So nothing restored the window, and nothing moved it either.

        A snap is not a maximize — ``showCmd`` stays ``SW_NORMAL`` — so it
        needs its own question, and its own source for the pre-snap size:
        Qt's ``normalGeometry()`` has been overwritten with the snapped rect
        by then, while Windows still has the original in
        ``rcNormalPosition``. Un-snapping is then just a geometry change.

        The window is placed so the cursor keeps the same fraction across
        the title bar; grab a maximized float near its right edge and it
        comes loose near its right edge, rather than jumping so its corner
        lands under the pointer.
        """
        local = self.mapFromGlobal(global_pos)
        fraction = min(1.0, max(0.0, local.x() / max(1, self.width())))

        if is_window_maximized(self):
            # The restored size has to come from normalGeometry(), read now:
            # showNormal() does not apply the geometry before it returns (on
            # either platform), so reading size() afterwards still measures
            # the maximized window — and a plain move() then loses to Qt's
            # own deferred restore. Set the whole rect instead.
            target = QRect(self.normalGeometry())
            if target.isEmpty():
                target = QRect(self.pos(), self.size())
            restore_window(self)
        else:
            target = pre_snap_geometry(self)
            if target is None:
                return

        target.moveTo(global_pos.x() - int(fraction * target.width()),
                      global_pos.y() - local.y())
        self.setGeometry(target)
        # The manual (no OS move loop) fallback measures from this.
        self._drag_start_mouse_position = self.mapFromGlobal(global_pos)

    def _remove_frameless_drag_filter(self):
        """Remove the transient app filter installed for frameless drags."""
        if self._frameless_drag_filter:
            app = QApplication.instance()
            if app is not None and not self._permanent_filter_installed:
                app.removeEventFilter(self)
            self._frameless_drag_filter = False

    # ─────────────────────────────────────────────────────────────────────
    #  Custom title-bar close button
    # ─────────────────────────────────────────────────────────────────────

    def _on_dock_areas_changed(self) -> None:
        """The close button is ours to enable, not the window manager's.

        The native-frame container inherits the no-op: its close button
        belongs to the OS frame, which already refuses a window whose
        is_closable() says no.
        """
        self._update_close_button_state()
        self._sync_feature_signals()

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
            # Capture the true normal colour once — it is guaranteed to be
            # the themed colour because the styler's initial pass runs before
            # our first sync (and _after_styler_refresh re-captures it after
            # every theme change).  Never re-capture from the current value:
            # while disabled the current colour is our own dimmed colour.
            if self._close_btn_normal_color is None:
                self._close_btn_normal_color = QColor(close_btn._normalColor)
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

    def _after_styler_refresh(self):
        """Called after every FramelessTitleBarStyler pass (initial styling
        and theme switches).  The styler just re-applied the theme's close
        button normal colour, so refresh the remembered normal before
        re-applying our disabled state."""
        tb = getattr(self, "titleBar", None)
        close_btn = getattr(tb, "closeBtn", None)
        if close_btn is not None:
            self._close_btn_normal_color = QColor(close_btn._normalColor)
        self._update_close_button_state()

    def _sync_feature_signals(self):
        """Follow membership / feature / view signals of everything currently
        in the float so the close-button state tracks add / remove / open /
        close / feature changes without relying on a single container signal.

        Area-level: ``dock_widgets_changed`` (a widget joined/left an existing
        area) and ``view_toggled`` (the area was opened/closed).  Widget-level:
        ``features_changed`` (closable toggled) and ``view_toggled`` (a widget
        was opened/closed — ``features()`` only intersects opened widgets).

        Qt auto-disconnects when a sender or receiver is destroyed, so stale
        entries are pruned here on the next sync rather than on destruction.
        """
        try:
            container = self._dock_container
            areas = set(container._dock_areas)
            widgets = set(container.dock_widgets())
        except RuntimeError:
            return

        # Areas
        for area in list(self._area_synced_areas):
            if area not in areas:
                try:
                    area.dock_widgets_changed.disconnect(self._on_dock_widgets_changed)
                except (RuntimeError, TypeError):
                    pass
                try:
                    area.view_toggled.disconnect(self._update_close_button_state)
                except (RuntimeError, TypeError):
                    pass
                self._area_synced_areas.discard(area)
        for area in areas:
            if area not in self._area_synced_areas:
                try:
                    area.dock_widgets_changed.connect(self._on_dock_widgets_changed)
                except (RuntimeError, TypeError):
                    pass
                try:
                    area.view_toggled.connect(self._update_close_button_state)
                except (RuntimeError, TypeError):
                    pass
                self._area_synced_areas.add(area)

        # Widgets
        for w in list(self._feature_synced_widgets):
            if w not in widgets:
                for sig in (w.features_changed, w.view_toggled):
                    try:
                        sig.disconnect(self._update_close_button_state)
                    except (RuntimeError, TypeError):
                        pass
                self._feature_synced_widgets.discard(w)
        for w in widgets:
            if w not in self._feature_synced_widgets:
                for sig in (w.features_changed, w.view_toggled):
                    try:
                        sig.connect(self._update_close_button_state)
                    except (RuntimeError, TypeError):
                        pass
                self._feature_synced_widgets.add(w)

    def _on_dock_widgets_changed(self, *args):
        """A dock widget was inserted into / removed from one of our areas:
        re-check the close-button state and follow any newly added widget's
        signals."""
        self._update_close_button_state()
        self._sync_feature_signals()


#: Deprecated alias.  Both floating containers were called
#: ``FloatingDockContainer`` until 0.5.50, which made
#: ``isinstance(x, lace.FloatingDockContainer)`` quietly wrong in
#: custom-titlebar mode.  Use :func:`lace.util.is_floating_dock_container`
#: for the check, or the class by its real name.
FloatingDockContainer = FramelessFloatingDockContainer
