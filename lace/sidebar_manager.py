# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.

from __future__ import annotations

import logging
import warnings
from typing import TYPE_CHECKING, Optional, Dict, Any, FrozenSet, Iterable

import shiboken6
from PySide6.QtCore import QObject, Signal, QTimer, QPoint, QEvent, QSize, Qt
from PySide6.QtGui import QKeySequence, QShortcut, QCursor
from PySide6.QtWidgets import QApplication, QMainWindow

from lace.enums import DockWidgetArea, WidgetState, DockWidgetFeature, DockFlags, SideBarFocusBehavior
from lace.dock_menu import find_closest_dock_area
from lace.layout_serializer import SidebarStateManager, SidebarState
from lace.sidebar_tab import VerticalTabButton, TabBadgePosition
from lace.sidebar_container import SideBarContainer
from lace.sidebar_tab_bar import SideTabBar
from lace._trace import trace

if TYPE_CHECKING:
    from lace.dock_widget import DockWidget
    from lace.dock_manager import DockManager

logger = logging.getLogger(__name__)

_HIDE_DELAY_MS = 400

#: The sides a sidebar can run along, in the order ties are broken.
_AREA_ORDER = (DockWidgetArea.left, DockWidgetArea.bottom,
               DockWidgetArea.right, DockWidgetArea.top)
_SIDEBAR_AREAS = frozenset(_AREA_ORDER)
_OPPOSITE_AREA = {
    DockWidgetArea.left: DockWidgetArea.right,
    DockWidgetArea.right: DockWidgetArea.left,
    DockWidgetArea.top: DockWidgetArea.bottom,
    DockWidgetArea.bottom: DockWidgetArea.top,
}


class SidebarKeyboardHandler(QObject):
    """Handles keyboard shortcuts for sidebar navigation."""
    
    toggle_sidebar = Signal(DockWidgetArea)
    focus_sidebar = Signal(DockWidgetArea)
    close_current = Signal()
    
    def __init__(self, parent: QObject = None):
        super().__init__(parent)
        self._shortcuts: Dict[str, QShortcut] = {}
    
    def register_shortcuts(self, window: QMainWindow):
        """Register default VS Code-style shortcuts."""
        shortcuts = {
            #"Ctrl+B": (lambda: self.toggle_sidebar.emit(DockWidgetArea.left), "Toggle Left Sidebar"),
            #"Ctrl+J": (lambda: self.toggle_sidebar.emit(DockWidgetArea.bottom), "Toggle Bottom Panel"),
            #"Ctrl+Shift+E": (lambda: self.focus_sidebar.emit(DockWidgetArea.left), "Focus Explorer"),
            #"Ctrl+Shift+F": (lambda: self.focus_sidebar.emit(DockWidgetArea.left), "Focus Search"),
            #"Ctrl+Shift+G": (lambda: self.focus_sidebar.emit(DockWidgetArea.left), "Focus Source Control"),
            #"Ctrl+Shift+X": (lambda: self.focus_sidebar.emit(DockWidgetArea.left), "Focus Extensions"),
            "Escape": (lambda: self.close_current.emit(), "Close Sidebar"),
        }

        for key, (callback, tooltip) in shortcuts.items():
            if key in self._shortcuts:
                continue
            shortcut = QShortcut(QKeySequence(key), window)
            shortcut.activated.connect(callback)
            self._shortcuts[key] = shortcut
        # The Escape binding exists only to dismiss a hover overlay, which
        # never takes focus — but as a window-wide shortcut it would swallow
        # Esc for every focused widget (terminals, editors, dialogs) even
        # with nothing to close. Start disabled; SidebarManager syncs it on
        # overlay Show/Hide so the key belongs to the app unless an overlay
        # is actually up.
        self.set_escape_enabled(False)

    def set_escape_enabled(self, enabled: bool) -> None:
        """Enable the Escape-to-close binding only while an overlay is up."""
        shortcut = self._shortcuts.get("Escape")
        if shortcut is not None:
            try:
                shortcut.setEnabled(enabled)
            except RuntimeError:
                pass


class SidebarHoverController(QObject):
    """Manages hover timers, tab switching delays, and auto-hide timeouts for sidebars."""
    def __init__(self, manager: 'SidebarManager', parent: QObject = None):
        super().__init__(parent or manager)
        self._manager = manager
        
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(_HIDE_DELAY_MS)
        self._hide_timer.timeout.connect(self.on_hide_timeout)
        
        self._switch_timer = QTimer(self)
        self._switch_timer.setSingleShot(True)
        self._switch_timer.setInterval(150) # Matches animation duration
        self._switch_timer.timeout.connect(self.process_pending_switch)
        self._pending_button: Optional[VerticalTabButton] = None

    def on_tab_hover_enter(self, button: VerticalTabButton):
        if not self._manager._auto_show_on_hover or self._manager._keep_open:
            return
        self._hide_timer.stop()

        if self._manager._active_button is button and self._manager._overlay.isVisible():
            self._switch_timer.stop()
            self._pending_button = None
            return

        self._manager._uncheck_all()
        button.setChecked(True)
        
        self._pending_button = button
        dw = button.dock_widget()
        trace("sidebar.hover", action="enter", button=dw.objectName() if dw else "button")
        
        if self._manager._overlay.isVisible() and self._manager._animations_enabled:
            self._switch_timer.start()
        else:
            self.process_pending_switch()

    def on_tab_hover_leave(self, button: VerticalTabButton):
        if not self._manager._auto_show_on_hover or self._manager._keep_open:
            return
        dw = button.dock_widget()
        trace("sidebar.hover", action="leave", button=dw.objectName() if dw else "button")
        self._hide_timer.start()

    def process_pending_switch(self):
        button = self._pending_button
        if not button:
            return
        trace("sidebar.timer", kind="switch", fire=True)
        self._pending_button = None

        dock_widget = button.dock_widget()
        sidebar = self._manager._pinned.get(dock_widget) if dock_widget else None
        if sidebar is None:
            return      # a stale tab: its dock was unpinned meanwhile

        area = sidebar.area

        if self._manager._overlay.isVisible() and self._manager._last_active_area and self._manager._last_active_area != area:
            self._manager._overlay.hide_widget(animate=False)

        self._manager._show_for_button(button)

    def on_hide_timeout(self):
        if self._manager._keep_open or self._manager._overlay.underMouse():
            return
        trace("sidebar.timer", kind="hide", fire=True)
        self._manager.close_overlay()

    def on_tab_clicked(self, button: VerticalTabButton):
        if self._manager._active_button is button and self._manager._overlay.isVisible():
            self._switch_timer.stop()
            self._pending_button = None
            self._manager.close_overlay()
            return

        self._manager._uncheck_all()
        button.setChecked(True)
        
        self._pending_button = button
        
        if self._manager._overlay.isVisible() and self._manager._animations_enabled:
            self._switch_timer.start()
        else:
            self.process_pending_switch()

    def on_sidebar_activated(self):
        self._hide_timer.stop()


class SidebarOverlayController(QObject):
    """Manages overlay display, hiding, resizing, and detaching."""
    def __init__(self, manager: 'SidebarManager', parent: QObject = None):
        super().__init__(parent or manager)
        self._manager = manager

    def show_for_button(self, button: VerticalTabButton):
        dock_widget = button.dock_widget()
        sidebar = self._manager._pinned.get(dock_widget) if dock_widget else None
        if sidebar is None:
            return

        area = sidebar.area
        
        state = self._manager._state_manager.load_state(dock_widget.objectName())
        if state.width <= 0:
            state = self._manager._state_manager.load_state(area)
            
        size = QSize(state.width, state.height)
        
        self._manager._uncheck_all()
        button.setChecked(True)
        self._manager._active_button = button
        self._manager._last_active_area = area
        
        trace("sidebar.overlay", action="show", area=getattr(area, 'name', str(area)), size=size.width())
        self._manager._overlay.show_widget(dock_widget, area, size=size, animate=self._manager._animations_enabled)
        dock_widget.set_widget_state(WidgetState.pinned_shown)
    
        self._manager.raise_overlays()

    def close_overlay(self):
        trace("sidebar.overlay", action="hide", area="overlay", size=0)
        
        if self._manager._overlay.isVisible():
            if self._manager._active_button:
                dw = self._manager._active_button.dock_widget()
                if dw:
                    dw.set_widget_state(WidgetState.pinned_hidden)

            self._manager._overlay.hide_widget(
                animate=self._manager._animations_enabled)
            self._manager._uncheck_all()
            self._manager._active_button = None

    def detach_from_overlay(self, dock_widget: 'DockWidget', hide: bool = False):
        self._manager._overlay._current_widgets.remove(dock_widget)
        if hide:
            dock_widget.hide()
        dock_widget.setParent(None)
        if not self._manager._overlay._current_widgets:
            self._manager._overlay.hide_widget(animate=True)
        self._manager._uncheck_all()
        self._manager._active_button = None

    def on_resize_finished(self):
        trace("sidebar.overlay", action="resize", area="overlay", size=self._manager._overlay.width() if self._manager._overlay else 0)
        if self._manager._active_button:
            dock_widget = self._manager._active_button.dock_widget()
            if dock_widget:
                state = SidebarState(
                    width=self._manager._overlay.width(),
                    height=self._manager._overlay.height()
                )
                self._manager._state_manager.save_state(dock_widget.objectName(), state)


class SidebarDragController(QObject):
    """Manages tearing tabs off sidebars into floating windows and drag tracking."""
    def __init__(self, manager: 'SidebarManager', parent: QObject = None):
        super().__init__(parent or manager)
        self._manager = manager

    def on_tab_drag_started(self, button: VerticalTabButton):
        dock_widget = button.dock_widget()
        if dock_widget:
            if not (dock_widget.features() & DockWidgetFeature.movable):
                return
            if not (dock_widget.features() & DockWidgetFeature.floatable):
                return
            sidebar = self._manager._pinned.get(dock_widget)
            if sidebar:
                global_pos = QCursor.pos()
                if sidebar.rect().contains(sidebar.mapFromGlobal(global_pos)):
                    return
            self.unpin_widget_floating(dock_widget)

    def unpin_widget_floating(self, dock_widget: 'DockWidget'):
        if dock_widget not in self._manager._pinned:
            return
        if not (dock_widget.features() & DockWidgetFeature.floatable):
            return
        
        sidebar = self._manager._pinned[dock_widget]

        is_visible = self._manager._overlay.isVisible() and dock_widget in self._manager._overlay._current_widgets

        if is_visible:
            size = self._manager._overlay.size()
            origin = self._manager._overlay.mapToGlobal(QPoint(0, 0))
        else:
            state = self._manager._state_manager.load_state(sidebar.area)
            size = QSize(state.width, state.height)
            origin = QCursor.pos() - QPoint(10, 10)

        self._manager.release_widget(dock_widget)
        dock_widget.hide()
        trace("sidebar.transition", widget=dock_widget.objectName() or dock_widget.__class__.__name__, from_state="pinned", to_state="floating")

        floating_cls = self._manager._dock_manager.floating_container_class()
        dock_widget.set_dock_manager(self._manager._dock_manager)
        floating = floating_cls(
            dock_widget=dock_widget, dock_manager=self._manager._dock_manager)
        
        is_dragging = bool(QApplication.mouseButtons() & Qt.LeftButton)
        
        if is_dragging:
            local_offset = QPoint(size.width() // 2, 10)
            if is_visible:
                local_offset = QCursor.pos() - origin
            
            floating.start_dragging(local_offset, size, floating)
            FloatingDragTracker(floating, floating)
        else:
            floating.resize(size)
            if is_visible:
                floating.move(origin + QPoint(10, 10))
            else:
                floating.move(origin)
            floating.show()


class SidebarManager(QObject):
    """Full-featured VS Code-style sidebar manager."""
    
    sidebar_toggled = Signal(DockWidgetArea, bool)
    widget_unpinned = Signal(object)
    
    def __init__(self, dock_manager: 'DockManager'):
        super().__init__(dock_manager)
        self._dock_manager = dock_manager
        
        # --- TOGGLES ---
        self._auto_show_on_hover: bool = True
        self._animations_enabled: bool = True  # NEW: Master toggle for animations
        self._keep_open: bool = False
        
        self._sidebars: Dict[DockWidgetArea, SideTabBar] = {}
        self._overlay = SideBarContainer(dock_manager.root_container())
        self._overlay._dock_manager = dock_manager
        
        # Connect overlay signals
        self._overlay.pin_back_requested.connect(self._on_overlay_pin_back)
        self._overlay.drag_unpin_requested.connect(self._on_drag_unpin)
        self._overlay.close_requested.connect(self.close_overlay)
        self._overlay.resize_finished.connect(self._on_resize_finished)
        
        self._pinned: Dict['DockWidget', SideTabBar] = {}
        self._destroyed_hooks: Dict['DockWidget', Any] = {}
        self._allowed_areas: FrozenSet[DockWidgetArea] = _SIDEBAR_AREAS
        self._restoring = False
        self._pins_before: Dict['DockWidget', DockWidgetArea] = {}
        self._active_button: Optional[VerticalTabButton] = None
        self._last_active_area: Optional[DockWidgetArea] = None
        self._badge_position: TabBadgePosition = TabBadgePosition.top_right
        
        self._hover_controller = SidebarHoverController(self)
        self._overlay_controller = SidebarOverlayController(self)
        self._drag_controller = SidebarDragController(self)
        
        self._state_manager = SidebarStateManager()
        self._keyboard = SidebarKeyboardHandler(self)
        # Gate the window-wide Escape shortcut on actual overlay visibility
        # (see eventFilter): covers every show/hide path — hover, click,
        # toggle, drag-out, animation completion — with no per-call-site
        # bookkeeping to miss.
        self._overlay.installEventFilter(self)

        qapp = QApplication.instance()
        if qapp:
            self._click_filter = ClickOutsideFilter(self, parent=self)
            qapp.installEventFilter(self._click_filter)
    
    @property
    def _hide_timer(self):
        return self._hover_controller._hide_timer

    @property
    def _switch_timer(self):
        return self._hover_controller._switch_timer

    @property
    def _pending_button(self):
        return self._hover_controller._pending_button

    @_pending_button.setter
    def _pending_button(self, value):
        self._hover_controller._pending_button = value

    def setup_shortcuts(self, window: QMainWindow):
        self._keyboard.register_shortcuts(window)
        self._keyboard.toggle_sidebar.connect(self.toggle_sidebar)
        self._keyboard.focus_sidebar.connect(self.toggle_sidebar)
        self._keyboard.close_current.connect(self.close_overlay)
        # Registration starts Escape disabled; sync with reality in case an
        # overlay is somehow already up.
        self._keyboard.set_escape_enabled(self._overlay.isVisible())

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        # The Escape shortcut is window-wide (the hover overlay never takes
        # focus, so scoping it to the sidebar would break its only purpose)
        # but must not swallow Esc for focused widgets when nothing is open.
        # Syncing on Show/Hide follows the overlay's actual visibility —
        # including animation-delayed hides — whatever path showed or hid it.
        if watched is self._overlay:
            if event.type() == QEvent.Show:
                self._keyboard.set_escape_enabled(True)
            elif event.type() == QEvent.Hide:
                self._keyboard.set_escape_enabled(False)
        return False
    
    def add_sidebar(self, area: DockWidgetArea) -> SideTabBar:
        if area in self._sidebars:
            return self._sidebars[area]
        
        bar = SideTabBar(area, self._dock_manager.root_container())
        bar._dock_manager = self._dock_manager
        self._dock_manager._add_sidebar_to_layout(bar, area)
        
        bar.tab_clicked.connect(self._hover_controller.on_tab_clicked)
        bar.tab_hover_enter.connect(self._hover_controller.on_tab_hover_enter)
        bar.tab_hover_leave.connect(self._hover_controller.on_tab_hover_leave)
        bar.tab_drag_started.connect(self._drag_controller.on_tab_drag_started)
        bar.sidebar_activated.connect(self._hover_controller.on_sidebar_activated)
        
        self._sidebars[area] = bar
        state = self._state_manager.load_state(area)
        self._overlay._size_hint = QSize(state.width, state.height)
        
        return bar
    
    # ─────────────────────────────────────────────────────────────────────
    #  Which sides sidebars may use
    # ─────────────────────────────────────────────────────────────────────

    def set_sidebar_areas(self, areas: Iterable[DockWidgetArea]) -> None:
        """Allow sidebars on *areas* only, and create those sidebars.

        A dock pinned to a side that is no longer allowed moves to the
        closest allowed one. The default allows all four sides.
        """
        allowed = frozenset(DockWidgetArea(a) for a in areas) & _SIDEBAR_AREAS
        if not allowed:
            raise ValueError("set_sidebar_areas needs at least one of left, right, top, bottom")
        self._allowed_areas = allowed
        for area in sorted(allowed, key=_AREA_ORDER.index):
            self.add_sidebar(area)
        for dock_widget, sidebar in list(self._pinned.items()):
            if sidebar.area not in allowed:
                self.pin_widget(dock_widget, area=self._allowed_area(sidebar.area, dock_widget),
                                force=True)

    def sidebar_areas(self) -> FrozenSet[DockWidgetArea]:
        """The sides sidebars may use (see :meth:`set_sidebar_areas`)."""
        return self._allowed_areas

    def _usable_sidebars(self) -> Dict[DockWidgetArea, SideTabBar]:
        return {a: bar for a, bar in self._sidebars.items() if a in self._allowed_areas}

    def _allowed_area(self, area: DockWidgetArea, dock_widget: 'DockWidget') -> DockWidgetArea:
        """*area* if it is allowed, else the allowed side closest to it.

        Left and right stand in for each other; otherwise the side closest
        to the dock wins.
        """
        if area in self._allowed_areas:
            return area
        opposite = _OPPOSITE_AREA.get(area)
        if area in (DockWidgetArea.left, DockWidgetArea.right) and opposite in self._allowed_areas:
            chosen = opposite
        else:
            chosen = self._closest_area(dock_widget, self._allowed_areas)
        logger.debug("Sidebar %s is not allowed; using %s", area.name, chosen.name)
        return chosen

    def _closest_area(self, dock_widget: 'DockWidget', candidates) -> DockWidgetArea:
        """The side in *candidates* whose window edge is closest to the dock."""
        order = [a for a in _AREA_ORDER if a in candidates]
        try:
            # The dock area gives steadier geometry than the dock itself.
            dock_area = dock_widget.dock_area_widget()
            source = dock_area if dock_area is not None else dock_widget
            center = self._dock_manager.mapFromGlobal(source.mapToGlobal(source.rect().center()))
            rect = self._dock_manager.rect()
            if rect.width() <= 10:          # not laid out yet
                rect = self._dock_manager.window().rect()
            # abs(): a centre that drifted outside during a layout pass must
            # not win with a negative distance.
            distance = {
                DockWidgetArea.left: abs(center.x()),
                DockWidgetArea.right: abs(rect.width() - center.x()),
                DockWidgetArea.top: abs(center.y()),
                DockWidgetArea.bottom: abs(rect.height() - center.y()),
            }
            return min(order, key=distance.__getitem__)
        except Exception:
            return order[0]

    # ─────────────────────────────────────────────────────────────────────
    #  Pinning
    # ─────────────────────────────────────────────────────────────────────

    def pin_widget(self, dock_widget: 'DockWidget',
                   sidebar: Optional['SideTabBar'] = None,
                   area: Optional[DockWidgetArea] = None,
                   *, force: bool = False) -> bool:
        """Pin *dock_widget* to a sidebar; whether it is pinned afterwards.

        With neither *sidebar* nor *area*, the closest allowed side is used,
        or the dock stays where it is if it is pinned already. A dock without
        ``DockWidgetFeature.pinnable`` is refused unless *force* is set.
        Pinning a pinned dock to another side moves its tab.
        """
        if self._dock_manager and DockFlags.pinnable_tabs not in self._dock_manager.config_flags:
            return False
        if not force and not (dock_widget.features() & DockWidgetFeature.pinnable):
            logger.debug("pin_widget: %s is not pinnable", dock_widget.objectName())
            return False
        current = self._pinned.get(dock_widget)
        if current is not None and sidebar is None and area is None:
            return True                     # already pinned, no side asked for

        if self._dock_manager:
            dock_widget.set_dock_manager(self._dock_manager)
        if dock_widget.objectName():
            self._dock_manager._dock_widgets_map[dock_widget.objectName()] = dock_widget

        if sidebar is None:
            if area is None:
                # Left, right and bottom: a top sidebar is used only when asked for.
                auto = (self._allowed_areas - {DockWidgetArea.top}) or self._allowed_areas
                area = self._closest_area(dock_widget, auto)
            else:
                area = self._allowed_area(area, dock_widget)
            sidebar = self.add_sidebar(area)
        if current is sidebar:
            return True
        if current is not None:
            self.release_widget(dock_widget, notify=False)   # moving sides

        # Detach from the current dock area
        dock_area = dock_widget.dock_area_widget()
        if dock_area is not None:
            dock_area.remove_dock_widget(dock_widget)

        self._detach_tab_widget(dock_widget)
        dock_widget.set_dock_area(None)

        # Hidden until the overlay shows it, so it doesn't ghost at (0, 0)
        dock_widget.hide()
        dock_widget.set_widget_state(WidgetState.pinned_hidden)

        # A closed dock keeps its tab hidden until it is opened
        btn = sidebar.add_tab(dock_widget, visible=not dock_widget.is_closed())
        if btn:
            btn.set_badge_position(self._badge_position)
        self._pinned[dock_widget] = sidebar
        self._destroyed_hooks[dock_widget] = dock_widget.destroyed.connect(
            lambda *_, d=dock_widget: self._on_pinned_destroyed(d))
        dock_widget.set_toggle_view_action_checked(not dock_widget.is_closed())
        trace("sidebar.transition", widget=dock_widget.objectName() or dock_widget.__class__.__name__, from_state="docked", to_state="pinned")
        self.update_badge(dock_widget, 0)
        self._notify_pinned(dock_widget, sidebar.area)
        return True

    def release_widget(self, dock_widget: 'DockWidget', *, notify: bool = True) -> bool:
        """Take *dock_widget* out of its sidebar without docking it anywhere.

        The dock is left hidden, with no dock area, for the caller to place
        or delete. Returns whether it was pinned.
        """
        if dock_widget not in self._pinned:
            return False
        if dock_widget in self._overlay._current_widgets:
            # Synchronously, so the overlay's delayed hide can't rip the
            # widget out of wherever it goes next.
            self._detach_from_overlay(dock_widget, hide=True)
        self._forget(dock_widget)
        self._detach_tab_widget(dock_widget)
        dock_widget.set_dock_area(None)
        dock_widget.set_widget_state(WidgetState.docked)
        trace("sidebar.transition", widget=dock_widget.objectName() or dock_widget.__class__.__name__, from_state="pinned", to_state="released")
        if notify:
            self._notify_pinned(dock_widget, None)
        return True

    def _forget(self, dock_widget: 'DockWidget', dying: bool = False) -> Optional[SideTabBar]:
        """Drop the sidebar's bookkeeping for *dock_widget*: its entry, its tab
        and its ``destroyed`` hook. Doesn't touch the dock itself, and with
        *dying* not even its signals."""
        sidebar = self._pinned.pop(dock_widget, None)
        if sidebar is None:
            return None
        hook = self._destroyed_hooks.pop(dock_widget, None)
        if hook is not None:
            try:
                QObject.disconnect(hook)
            except (RuntimeError, TypeError):
                pass
        if not shiboken6.isValid(sidebar):
            return sidebar          # the window is being torn down
        button = sidebar.button_for(dock_widget)
        if button is not None:
            if self._active_button is button:
                self._active_button = None
            if self._pending_button is button:
                self._pending_button = None
        sidebar.remove_tab(dock_widget, disconnect=not dying)
        return sidebar

    def _on_pinned_destroyed(self, dock_widget: 'DockWidget') -> None:
        # Deleted while pinned, by a path that didn't release it first.
        if not shiboken6.isValid(self):
            return                  # the manager went first, at shutdown
        if shiboken6.isValid(self._overlay) and dock_widget in self._overlay._current_widgets:
            self._overlay._current_widgets.remove(dock_widget)
        self._forget(dock_widget, dying=True)

    def _notify_pinned(self, dock_widget: 'DockWidget', area: Optional[DockWidgetArea]) -> None:
        if self._restoring:
            return      # end_restore() reports the net change once per dock
        signals = getattr(self._dock_manager, "signals", None)
        if signals is not None:
            signals.dock_pinned_changed.emit(dock_widget, area)

    def pinned_widgets(self) -> Dict['DockWidget', DockWidgetArea]:
        """Every pinned dock and the side it is pinned to."""
        return {dock: bar.area for dock, bar in self._pinned.items()}

    def begin_restore(self) -> None:
        """Start a layout restore: release every pinned dock.

        The layout being restored says where each dock goes, sidebars
        included, so nothing stays pinned from before. Pin changes are
        reported by :meth:`end_restore`.
        """
        self._pins_before = self.pinned_widgets()
        self._restoring = True
        for dock_widget in list(self._pinned):
            self.release_widget(dock_widget)

    def end_restore(self) -> None:
        """Finish a restore: report each dock whose pin changed, once."""
        self._restoring = False
        before, self._pins_before = self._pins_before, {}
        after = self.pinned_widgets()
        for dock_widget in list(before) + [d for d in after if d not in before]:
            if before.get(dock_widget) != after.get(dock_widget) and shiboken6.isValid(dock_widget):
                self._notify_pinned(dock_widget, after.get(dock_widget))

    def unpin_widget(self, dock_widget: 'DockWidget',
                     area: Optional[DockWidgetArea] = None):
        """Move a pinned dock back into the dock layout.

        A pinned dock without ``DockWidgetFeature.pinnable`` is locked in its
        sidebar and stays. Only the host puts one there, with
        :meth:`DockManager.add_sidebar_widget` or by dropping the feature
        from a pinned dock; :meth:`pin_widget` refuses it.
        """
        sidebar = self._pinned.get(dock_widget)
        if sidebar is None:
            return
        if not (dock_widget.features() & DockWidgetFeature.pinnable):
            return

        # Capture the overlay geometry BEFORE we start hiding/detaching,
        # so we can determine the closest dock edge from where the panel
        # was actually visible on screen.
        overlay_visible = (
            self._overlay.isVisible()
            and dock_widget in self._overlay._current_widgets
        )
        if overlay_visible:
            overlay_center = self._overlay.mapToGlobal(
                QPoint(self._overlay.width() // 2,
                       self._overlay.height() // 2)
            )

        self.release_widget(dock_widget, notify=False)

        # Determine the closest dock edge.
        if area is not None:
            # Explicit area requested by caller — honour it.
            target_area = area
        elif overlay_visible:
            # Use the overlay's on-screen centre to find the nearest edge.
            try:
                target_area = find_closest_dock_area(
                    overlay_center, self._dock_manager)
            except Exception:
                target_area = sidebar.area
        else:
            # Overlay not visible — use the sidebar's own edge.
            target_area = sidebar.area

        # Capture the new area created by the manager
        new_area = self._dock_manager.add_dock_widget(target_area, dock_widget)

        # Explicitly show the area and the widget
        if new_area:
            new_area.show()

        dock_widget.show()
        dock_widget.toggle_view(True)
        self._notify_pinned(dock_widget, None)

    def unpin_widget_floating(self, dock_widget: 'DockWidget'):
        self._drag_controller.unpin_widget_floating(dock_widget)

    def _detach_tab_widget(self, dock_widget: 'DockWidget'):
        """Reparent the widget's tab away so it survives the widget being
        moved between the sidebar, a dock area, or a floating window."""
        tab_widget = getattr(dock_widget, 'tab_widget', lambda: None)()
        if tab_widget is not None:
            try:
                tab_widget.setParent(None)
            except RuntimeError:
                pass

    def move_widget_to_area(self, dock_widget: 'DockWidget', new_area: DockWidgetArea):
        if dock_widget not in self._pinned:
            return
        if not (dock_widget.features() & DockWidgetFeature.movable):
            return
        
        old_sidebar = self._pinned[dock_widget]
        new_sidebar = self._usable_sidebars().get(new_area)
        
        if not new_sidebar or old_sidebar == new_sidebar:
            return
        
        old_button = old_sidebar.button_for(dock_widget)
        old_sidebar.remove_tab(dock_widget)
        btn = new_sidebar.add_tab(dock_widget, visible=not dock_widget.is_closed())
        if btn:
            btn.set_badge_position(self._badge_position)
        self._pinned[dock_widget] = new_sidebar
        if self._active_button is old_button:
            self._active_button = btn
            btn.setChecked(True)
        if self._pending_button is old_button:
            self._pending_button = None

        if self._overlay.isVisible() and dock_widget in self._overlay._current_widgets:
            self._overlay.show_widget(dock_widget, new_area, animate=False)
        self._notify_pinned(dock_widget, new_area)
    
    def update_badge(self, dock_widget: 'DockWidget', value: Any):
        if dock_widget in self._pinned:
            btn = self._pinned[dock_widget].button_for(dock_widget)
            if btn:
                btn.set_badge(value)

    @property
    def badge_position(self) -> TabBadgePosition:
        return self._badge_position

    @badge_position.setter
    def badge_position(self, position: TabBadgePosition):
        self._badge_position = position
        for sidebar in self._sidebars.values():
            for btn in sidebar._buttons:
                btn.set_badge_position(position)

    def set_badge_position(self, position: TabBadgePosition):
        self.badge_position = position
    
    def toggle_sidebar(self, area: DockWidgetArea):
        sidebar = self._sidebars.get(area)
        if not sidebar:
            return
        
        if self._overlay.isVisible() and self._overlay._area == area:
            self.close_overlay()
            self.sidebar_toggled.emit(area, False)
        else:
            if sidebar.count() > 0:
                buttons = sidebar._buttons
                if self._last_active_area == area and self._active_button in buttons:
                    self._show_for_button(self._active_button)
                else:
                    self._show_for_button(buttons[0])
                self.sidebar_toggled.emit(area, True)
    
    def focus_sidebar(self, area: DockWidgetArea):
        """Deprecated alias for :meth:`toggle_sidebar`."""
        warnings.warn(
            "SidebarManager.focus_sidebar() is deprecated and will be removed; "
            "use toggle_sidebar().",
            DeprecationWarning, stacklevel=2)
        self.toggle_sidebar(area)

    def _uncheck_all(self):
        for bar in self._sidebars.values():
            bar.uncheck_all()

    def _detach_from_overlay(self, dock_widget: 'DockWidget', hide: bool = False):
        self._overlay_controller.detach_from_overlay(dock_widget, hide)

    def close_overlay(self):
        """Safely closes the overlay and stops pending animations."""
        self._overlay_controller.close_overlay()

    def _on_tab_hover_enter(self, button: VerticalTabButton):
        self._hover_controller.on_tab_hover_enter(button)

    def _on_tab_hover_leave(self, button: VerticalTabButton):
        self._hover_controller.on_tab_hover_leave(button)

    def _process_pending_switch(self):
        """Executes the tab switch only after the mouse settles."""
        self._hover_controller.process_pending_switch()

    def _on_hide_timeout(self):
        self._hover_controller.on_hide_timeout()

    def _on_tab_clicked(self, button: VerticalTabButton):
        self._hover_controller.on_tab_clicked(button)

    def _show_for_button(self, button: VerticalTabButton):
        self._overlay_controller.show_for_button(button)

    def _on_overlay_pin_back(self, dock_widget: 'DockWidget'):
        if not (dock_widget.features() & DockWidgetFeature.pinnable):
            return
        self.unpin_widget(dock_widget)
    
    def _on_drag_unpin(self, dock_widget: 'DockWidget'):
        if not (dock_widget.features() & DockWidgetFeature.floatable):
            return
        self.unpin_widget_floating(dock_widget)
    
    def _on_resize_finished(self):
        self._overlay_controller.on_resize_finished()
    
    def _on_tab_drag_started(self, button: VerticalTabButton):
        self._drag_controller.on_tab_drag_started(button)
    
    def _on_sidebar_activated(self):
        self._hover_controller.on_sidebar_activated()
    
    def pin_to_closest_sidebar(self, dock_widget: 'DockWidget'):
        if self._dock_manager and DockFlags.pinnable_tabs not in self._dock_manager.config_flags:
            return
        sidebars = self._usable_sidebars()
        if not sidebars:
            logger.warning('pin_to_closest_sidebar: no sidebars registered')
            return
        self.pin_widget(dock_widget, area=self._closest_area(dock_widget, sidebars))

    def raise_overlays(self):
        """Ensure the sidebar overlay container and tab bars stay on top in the central Z-order."""
        if hasattr(self, '_overlay') and self._overlay:
            self._overlay.raise_()
        for bar in self._sidebars.values():
            bar.raise_()

    def show_widget(self, dock_widget: 'DockWidget'):
        """Shows the sidebar overlay for a pinned dock widget and ensures its tab button is visible."""
        if dock_widget in self._pinned:
            btn = self._pinned[dock_widget].button_for(dock_widget)
            if btn:
                btn.setVisible(True)
                bar = self._pinned[dock_widget]
                if any(not b.isHidden() for b in bar._buttons):
                    bar.setVisible(True)
                root = self._dock_manager.root_container()
                if root and root.layout():
                    root.layout().activate()
                if self._restoring:
                    # A restore opens a pinned dock by showing its tab; the
                    # overlay opens only for the layout's active widget.
                    return
                self._show_for_button(btn)
        self.raise_overlays()

    def hide_widget(self, dock_widget: 'DockWidget'):
        """Hides the sidebar overlay if currently showing this widget, and hides its tab button."""
        if dock_widget in self._pinned:
            btn = self._pinned[dock_widget].button_for(dock_widget)
            if self._active_button is btn:
                self.close_overlay()
            if btn:
                btn.setVisible(False)
            dock_widget.set_widget_state(WidgetState.pinned_hidden)

    def is_pinned(self, dock_widget: 'DockWidget') -> bool:
        return dock_widget in self._pinned
    
    def set_keep_open(self, keep: bool):
        self._keep_open = keep
    
    # --- NEW TOGGLE METHODS ---
    def set_auto_show_on_hover(self, enable: bool):
        """Enable or disable opening sidebars simply by hovering."""
        self._auto_show_on_hover = enable

    def set_animations_enabled(self, enable: bool):
        """Enable or disable the slide-in / slide-out animations."""
        self._animations_enabled = enable
    
    @property
    def overlay(self) -> 'SideBarContainer':
        return self._overlay

    @property
    def focus_behavior(self) -> SideBarFocusBehavior:
        return self._overlay.focus_behavior

    @focus_behavior.setter
    def focus_behavior(self, behavior: SideBarFocusBehavior):
        self._overlay.focus_behavior = behavior

    @property
    def has_sidebars(self) -> bool:
        return bool(self._usable_sidebars())

    # ─────────────────────────────────────────────────────────────────────
    #  State Serialization
    # ─────────────────────────────────────────────────────────────────────

    def save_state(self) -> Dict[str, Any]:
        """
        Serialize the complete sidebar state for layout persistence.
        Returns a dict suitable for JSON serialization.
        """
        state = {
            "pinned_widgets": {},      # widget_name -> sidebar_area
            "overlay_sizes": {},       # widget_name -> {width, height}
            "active_widget": None,     # Currently shown widget name
            "sidebar_areas": [],       # List of active sidebar areas
            "settings": {
                "auto_show_on_hover": self._auto_show_on_hover,
                "animations_enabled": self._animations_enabled,
                "keep_open": self._keep_open,
            }
        }
        
        # Save which widgets are pinned to which sidebars
        for dock_widget, sidebar in self._pinned.items():
            widget_name = dock_widget.objectName()
            area_name = sidebar.area.name if hasattr(sidebar.area, 'name') else str(sidebar.area)
            state["pinned_widgets"][widget_name] = area_name
        
        # Save overlay sizes from state manager
        state["overlay_sizes"] = self._state_manager.export_all()
        
        # Save active widget if overlay is visible
        if self._active_button and self._overlay.isVisible():
            dock_widget = self._active_button.dock_widget()
            if dock_widget:
                state["active_widget"] = dock_widget.objectName()
        
        # Save which sidebar areas exist
        for area in self._usable_sidebars():
            area_name = area.name if hasattr(area, 'name') else str(area)
            state["sidebar_areas"].append(area_name)
        
        return state

    def restore_state(self, state: Dict[str, Any]) -> bool:
        """
        Restore sidebar state from a previously saved dict.
        Should be called AFTER containers are restored but BEFORE final UI updates.
        """
        if not state:
            return False
        
        try:
            # Close any open overlay first
            self.close_overlay()
            
            # Restore settings
            settings = state.get("settings", {})
            self._auto_show_on_hover = settings.get("auto_show_on_hover", True)
            self._animations_enabled = settings.get("animations_enabled", True)
            self._keep_open = settings.get("keep_open", False)
            
            # Restore overlay sizes
            overlay_sizes = state.get("overlay_sizes", {})
            self._state_manager.import_all(overlay_sizes)
            
            # Ensure sidebars exist for all saved areas that are allowed
            for area_name in state.get("sidebar_areas", []):
                area = self._area_from_name(area_name)
                if area in self._allowed_areas:
                    self.add_sidebar(area)
            
            # Restore pinned widgets
            pinned_data = state.get("pinned_widgets", {})
            for widget_name, area_name in pinned_data.items():
                dock_widget = self._dock_manager.find_dock_widget(widget_name)
                if dock_widget is None:
                    logger.warning(f"restore_state: widget '{widget_name}' not found")
                    continue
                
                area = self._area_from_name(area_name)
                if area is None:
                    logger.warning(f"restore_state: invalid area '{area_name}'")
                    continue
                
                # Pin the widget (this handles detaching from dock areas).
                # force: a dock locked in its sidebar (no pinnable) goes back
                # there too.
                self.pin_widget(dock_widget, area=self._allowed_area(area, dock_widget),
                                force=True)

            # Restore active widget (show overlay)
            active_name = state.get("active_widget")
            if active_name:
                dock_widget = self._dock_manager.find_dock_widget(active_name)
                if dock_widget and dock_widget in self._pinned:
                    # Deferred to avoid layout issues during restore
                    QTimer.singleShot(0, lambda d=dock_widget: self._show_pinned(d))
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore sidebar state: {e}")
            return False

    def _show_pinned(self, dock_widget: 'DockWidget') -> None:
        """Open the overlay for *dock_widget* if it is still pinned and open."""
        if not shiboken6.isValid(dock_widget) or dock_widget.is_closed():
            return
        sidebar = self._pinned.get(dock_widget)
        button = sidebar.button_for(dock_widget) if sidebar is not None else None
        if button is not None:
            self._show_for_button(button)

    def _area_from_name(self, name: str) -> Optional[DockWidgetArea]:
        """Convert area name string back to DockWidgetArea enum."""
        try:
            return DockWidgetArea[name]
        except (KeyError, TypeError):
            # Try matching by value name
            for area in DockWidgetArea:
                if area.name == name or str(area) == name:
                    return area
            return None


class ClickOutsideFilter(QObject):
    """Detect clicks outside overlay safely handling application popups."""
    def __init__(self, manager: SidebarManager, parent: QObject = None):
        super().__init__(parent)
        self._manager = manager
    
    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            overlay = self._manager._overlay
            if overlay.isVisible():
                # Prevent hiding if a menu/combobox dropdown is actively open
                if QApplication.activePopupWidget():
                    return False
                    
                global_pos = (event.globalPosition().toPoint()
                             if hasattr(event, 'globalPosition')
                             else event.globalPos())
                             
                if not self._hit_test(global_pos):
                    self._manager.close_overlay()
        return False
    
    def _hit_test(self, global_pos: QPoint) -> bool:
        overlay = self._manager._overlay
        if overlay.isVisible():
            if overlay.rect().contains(overlay.mapFromGlobal(global_pos)):
                return True
        for bar in self._manager._sidebars.values():
            if bar.isVisible():
                if bar.rect().contains(bar.mapFromGlobal(global_pos)):
                    return True
        return False


class FloatingDragTracker(QObject):
    """
    Tracks global mouse movements to drag a floating widget torn off from the sidebar.
    This ensures the dock overlays update smoothly without requiring the original
    widget to maintain an active mouse tracking loop.
    """
    def __init__(self, floating_widget, parent: QObject = None):
        super().__init__(parent)
        self._floating_widget = floating_widget
        QApplication.instance().installEventFilter(self)
    
    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseMove:
            if self._floating_widget and self._floating_widget.isVisible():
                self._floating_widget.move_floating()
        elif event.type() == QEvent.MouseButtonRelease:
            if event.button() == Qt.LeftButton:
                QApplication.instance().removeEventFilter(self)
                self.deleteLater()
        return False