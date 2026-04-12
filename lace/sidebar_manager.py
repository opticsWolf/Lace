# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0

Enhanced VS Code-style auto-hide sidebars with animations, context menus,
resizable panels, and advanced interactions.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional, Dict

from PySide6.QtCore import QObject, Signal, QTimer, QPoint, QEvent, QSize, QRect, Qt
from PySide6.QtGui import QKeySequence, QShortcut, QCursor
from PySide6.QtWidgets import QApplication, QMainWindow

from .enums import DockWidgetArea, WidgetState
from .dock_context_menu import find_closest_dock_area
from .sidebar_state import SidebarStateManager, SidebarState
from .sidebar_tab import VerticalTabButton
from .sidebar_container import SideBarContainer
from .sidebar_tab_bar import SideTabBar

if TYPE_CHECKING:
    from .dock_widget import DockWidget
    from .dock_manager import DockManager

logger = logging.getLogger(__name__)

_HIDE_DELAY_MS = 400


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
            shortcut = QShortcut(QKeySequence(key), window)
            shortcut.activated.connect(callback)
            self._shortcuts[key] = shortcut


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
        self._overlay = SideBarContainer(dock_manager)
        
        # Connect overlay signals
        self._overlay.pin_back_requested.connect(self._on_overlay_pin_back)
        self._overlay.drag_unpin_requested.connect(self._on_drag_unpin)
        self._overlay.close_requested.connect(self.close_overlay)
        self._overlay.resize_finished.connect(self._on_resize_finished)
        
        self._pinned: Dict['DockWidget', SideTabBar] = {}
        self._active_button: Optional[VerticalTabButton] = None
        self._last_active_area: Optional[DockWidgetArea] = None
        
        self._hide_timer = QTimer()
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(_HIDE_DELAY_MS)
        self._hide_timer.timeout.connect(self._on_hide_timeout)
        
        # --- NEW: Switch Debouncer ---
        self._switch_timer = QTimer()
        self._switch_timer.setSingleShot(True)
        self._switch_timer.setInterval(150) # Matches animation duration
        self._switch_timer.timeout.connect(self._process_pending_switch)
        self._pending_button: Optional[VerticalTabButton] = None
        
        self._state_manager = SidebarStateManager()
        self._keyboard = SidebarKeyboardHandler(self)
        
        qapp = QApplication.instance()
        if qapp:
            self._click_filter = ClickOutsideFilter(self, parent=self)
            qapp.installEventFilter(self._click_filter)
    
    def setup_shortcuts(self, window: QMainWindow):
        self._keyboard.register_shortcuts(window)
        self._keyboard.toggle_sidebar.connect(self.toggle_sidebar)
        self._keyboard.focus_sidebar.connect(self.focus_sidebar)
        self._keyboard.close_current.connect(self.close_overlay)
    
    def add_sidebar(self, area: DockWidgetArea) -> SideTabBar:
        if area in self._sidebars:
            return self._sidebars[area]
        
        bar = SideTabBar(area, self._dock_manager)
        self._dock_manager._add_sidebar_to_layout(bar, area)
        
        bar.tab_clicked.connect(self._on_tab_clicked)
        bar.tab_hover_enter.connect(self._on_tab_hover_enter)
        bar.tab_hover_leave.connect(self._on_tab_hover_leave)
        bar.tab_drag_started.connect(self._on_tab_drag_started)
        bar.sidebar_activated.connect(self._on_sidebar_activated)
        
        self._sidebars[area] = bar
        state = self._state_manager.load_state(area)
        self._overlay._size_hint = QSize(state.width, state.height)
        
        return bar
    
    # def pin_widget(self, dock_widget: 'DockWidget', 
    #                sidebar: Optional[SideTabBar] = None,
    #                area: Optional[DockWidgetArea] = None):
    #     if dock_widget in self._pinned:
    #         return
        
    #     if sidebar is None:
    #         if area is None:
    #             area = DockWidgetArea.left
    #         sidebar = self._sidebars.get(area)
    #         if not sidebar:
    #             return
        
    #     dock_area = dock_widget.dock_area_widget()
    #     if dock_area is not None:
    #         dock_area.remove_dock_widget(dock_widget)
        
    #     # FIX: Protect the tab from being destroyed if the old area was deleted
    #     tab_widget = getattr(dock_widget, 'tab_widget', lambda: None)()
    #     if tab_widget is not None:
    #         try:
    #             tab_widget.setParent(None)
    #         except RuntimeError:
    #             pass
        
    #     dock_widget.set_dock_area(None)
    #     sidebar.add_tab(dock_widget)
    #     dock_widget.hide()
    #     self._pinned[dock_widget] = sidebar
    #     self.update_badge(dock_widget, 0)

    def pin_widget(self, dock_widget: 'DockWidget', 
                   sidebar: Optional['SideTabBar'] = None,
                   area: Optional[DockWidgetArea] = None):
        
        # 1. Intelligent Area Detection based on closest screen edge
        if area is None and sidebar is None:
            # Use the parent dock area if available for more stable geometry
            dock_area = dock_widget.dock_area_widget()
            if dock_area is not None:
                widget_center_global = dock_area.mapToGlobal(dock_area.rect().center())
            else:
                widget_center_global = dock_widget.mapToGlobal(dock_widget.rect().center())
                
            center_in_manager = self._dock_manager.mapFromGlobal(widget_center_global)
            
            manager_rect = self._dock_manager.rect()
            # Fallback to main window geometry if the manager hasn't been fully laid out yet
            if manager_rect.width() <= 10:
                manager_rect = self._dock_manager.window().rect()
            
            # Calculate distance to valid sidebar edges.
            # abs() prevents negative distances from hijacking the min() check
            # if coordinates drift out of bounds during layout passes.
            dist_left = abs(center_in_manager.x())
            dist_right = abs(manager_rect.width() - center_in_manager.x())
            dist_bottom = abs(manager_rect.height() - center_in_manager.y())
            
            # Assign to the edge with the shortest absolute distance
            min_dist = min(dist_left, dist_right, dist_bottom)
            if min_dist == dist_left:
                area = DockWidgetArea.left
            elif min_dist == dist_bottom:
                area = DockWidgetArea.bottom
            else:
                area = DockWidgetArea.right
                
        # 2. Ensure sidebar exists for the target area
        if sidebar is None:
            if area not in self._sidebars:
                self.add_sidebar(area)
            sidebar = self._sidebars[area]
            
        # 3. Detach from current dock area
        dock_area = dock_widget.dock_area_widget()
        if dock_area is not None:
            dock_area.remove_dock_widget(dock_widget)
        
        tab_widget = getattr(dock_widget, 'tab_widget', lambda: None)()
        if tab_widget is not None:
            try:
                tab_widget.setParent(None)
            except RuntimeError:
                pass
        
        dock_widget.set_dock_area(None)
        
        # 4. Hide the widget to prevent (0,0) layout ghosting
        dock_widget.hide() 
        dock_widget.set_widget_state(WidgetState.pinned_hidden) # <-- NEW STAT
        
        # 5. Add to the correct sidebar
        sidebar.add_tab(dock_widget)
        self._pinned[dock_widget] = sidebar
        self.update_badge(dock_widget, 0)
    
    def unpin_widget(self, dock_widget: 'DockWidget', 
                     area: Optional[DockWidgetArea] = None):
        if dock_widget not in self._pinned:
            return
        
        sidebar = self._pinned.pop(dock_widget)

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

        if overlay_visible:
            # Synchronously detach from the overlay to prevent the delayed 
            # animation cleanup from ripping the widget out of its new home
            self._overlay._current_widgets.remove(dock_widget)
            dock_widget.hide() # FIX: Hide before setting parent to None
            dock_widget.setParent(None)
            if not self._overlay._current_widgets:
                self._overlay.hide_widget(animate=True)
            self._uncheck_all()
            self._active_button = None
        
        sidebar.remove_tab(dock_widget)
        dock_widget.set_dock_area(None)
        
        # FIX: Protect the tab from being destroyed
        tab_widget = getattr(dock_widget, 'tab_widget', lambda: None)()
        if tab_widget is not None:
            try:
                tab_widget.setParent(None)
            except RuntimeError:
                pass
        
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
        
        dock_widget.set_widget_state(WidgetState.docked) # <-- RESTORE STATE
        
        # Capture the new area created by the manager
        new_area = self._dock_manager.add_dock_widget(target_area, dock_widget)
        
        # Explicitly show the area and the widget
        if new_area:
            new_area.show()
        
        dock_widget.show()
        dock_widget.toggle_view(True)
        
    
    def unpin_widget_floating(self, dock_widget: 'DockWidget'):
        if dock_widget not in self._pinned:
            return
        
        sidebar = self._pinned.pop(dock_widget)
        
        is_visible = self._overlay.isVisible() and dock_widget in self._overlay._current_widgets
        
        if is_visible:
            # Capture geometry before hiding the overlay
            size = self._overlay.size()
            origin = self._overlay.mapToGlobal(QPoint(0, 0))
            
            self._overlay._current_widgets.remove(dock_widget)
            dock_widget.setParent(None)
            if not self._overlay._current_widgets:
                self._overlay.hide_widget(animate=True)
            self._uncheck_all()
            self._active_button = None
        else:
            state = self._state_manager.load_state(sidebar.area)
            size = QSize(state.width, state.height)
            origin = QCursor.pos() - QPoint(10, 10)
        
        sidebar.remove_tab(dock_widget)
        dock_widget.hide()
        dock_widget.set_dock_area(None)

        # FIX: Protect the tab from being destroyed
        tab_widget = getattr(dock_widget, 'tab_widget', lambda: None)()
        if tab_widget is not None:
            try:
                tab_widget.setParent(None)
            except RuntimeError:
                pass
        
        from .floating_dock_container import FloatingDockContainer
        dock_widget.set_dock_manager(self._dock_manager)
        floating = FloatingDockContainer(
            dock_widget=dock_widget, dock_manager=self._dock_manager)
        
        # FIX: Check if the user is actively holding the mouse button down
        is_dragging = bool(QApplication.mouseButtons() & Qt.LeftButton)
        
        if is_dragging:
            # Mirror start_dragging logic: attach dynamically to the cursor
            local_offset = QPoint(size.width() // 2, 10)
            if is_visible:
                local_offset = QCursor.pos() - origin
            
            # Pass floating as the mouse handler so it safely claims the mouse grab
            floating.start_dragging(local_offset, size, floating)
            
            # Install a global tracker to continuously update position/overlays
            FloatingDragTracker(floating, floating)
        else:
            # Mirror detached window context-menu logic
            floating.resize(size)
            if is_visible:
                floating.move(origin + QPoint(10, 10))
            else:
                floating.move(origin)
            floating.show()
    
    def move_widget_to_area(self, dock_widget: 'DockWidget', new_area: DockWidgetArea):
        if dock_widget not in self._pinned:
            return
        
        old_sidebar = self._pinned[dock_widget]
        new_sidebar = self._sidebars.get(new_area)
        
        if not new_sidebar or old_sidebar == new_sidebar:
            return
        
        old_sidebar.remove_tab(dock_widget)
        new_sidebar.add_tab(dock_widget)
        self._pinned[dock_widget] = new_sidebar
        
        if self._overlay.isVisible() and dock_widget in self._overlay._current_widgets:
            self._overlay.show_widget(dock_widget, new_area, animate=False)
    
    def update_badge(self, dock_widget: 'DockWidget', count: int):
        if dock_widget in self._pinned:
            btn = self._pinned[dock_widget].button_for(dock_widget)
            if btn:
                btn.set_badge(count)
    
    def toggle_sidebar(self, area: DockWidgetArea):
        sidebar = self._sidebars.get(area)
        if not sidebar:
            return
        
        if self._overlay.isVisible() and self._overlay._area == area:
            self.close_overlay()
            self.sidebar_toggled.emit(area, False)
        else:
            if sidebar.tab_count() > 0:
                buttons = sidebar._buttons
                if self._last_active_area == area and self._active_button in buttons:
                    self._show_for_button(self._active_button)
                else:
                    self._show_for_button(buttons[0])
                self.sidebar_toggled.emit(area, True)
    
    def focus_sidebar(self, area: DockWidgetArea):
        self.toggle_sidebar(area)
    
    def close_overlay(self):
        """Safely closes the overlay and stops pending animations."""
        #self._switch_timer.stop()
        #self._pending_button = None
        
        if self._overlay.isVisible():
            # Update state of the currently shown widget back to hidden
            if self._active_button:
                dw = self._active_button.property("_dock_widget")
                if dw:
                    dw.set_widget_state(WidgetState.pinned_hidden) # <-- NEW STATE

            self._overlay.hide_widget()
            self._uncheck_all()
            self._active_button = None
    
    def _on_tab_hover_enter(self, button: VerticalTabButton):
        if not self._auto_show_on_hover or self._keep_open:
            return
        self._hide_timer.stop()

        # If hovering over the already active tab, do nothing
        if self._active_button is button and self._overlay.isVisible():
            self._switch_timer.stop()
            self._pending_button = None
            return

        # Visually update
        self._uncheck_all()
        button.setChecked(True)
        
        # Queue the switch
        self._pending_button = button
        
        if self._overlay.isVisible() and self._animations_enabled:
            self._switch_timer.start()
        else:
            self._process_pending_switch()
    
    def _on_tab_hover_leave(self, button: VerticalTabButton):
        if not self._auto_show_on_hover or self._keep_open:
            return
        self._hide_timer.start()
    
    def _process_pending_switch(self):
        """Executes the tab switch only after the mouse settles."""
        button = self._pending_button
        if not button:
            return
        self._pending_button = None

        dock_widget = button.property("_dock_widget")
        if not dock_widget:
            return

        area = self._pinned[dock_widget].area

        # CRITICAL FIX: Only force an instant hide if switching to a completely 
        # different screen edge (e.g., Left Sidebar -> Bottom Panel). 
        # Otherwise, let the overlay swap the content internally!
        if self._overlay.isVisible() and self._last_active_area and self._last_active_area != area:
            self._overlay.hide_widget(animate=False)

        self._show_for_button(button)
    
    def _on_hide_timeout(self):
        if self._keep_open or self._overlay.underMouse():
            return
        self.close_overlay()
    
    # def _on_tab_clicked(self, button: VerticalTabButton):
    #     if self._auto_show_on_hover:
    #         if self._active_button is button and self._overlay.isVisible():
    #             self.close_overlay()
    #         return
        
    #     if self._active_button is button and self._overlay.isVisible():
    #         self.close_overlay()
    #     else:
    #         self._show_for_button(button)
    
    def _on_tab_clicked(self, button: VerticalTabButton):
        # 1. If clicking the already open tab, close it.
        if self._active_button is button and self._overlay.isVisible():
            self._switch_timer.stop()
            self._pending_button = None
            self.close_overlay()
            return

        # 2. Visually update immediately for snappy UI feel
        self._uncheck_all()
        button.setChecked(True)
        
        # 3. Queue the switch
        self._pending_button = button
        
        if self._overlay.isVisible() and self._animations_enabled:
            self._switch_timer.start() # Wait for mouse to settle
        else:
            self._process_pending_switch() # Execute immediately
    
    def _show_for_button(self, button: VerticalTabButton):
        dock_widget = button.property("_dock_widget")
        if dock_widget is None:
            return
        
        area = self._pinned[dock_widget].area
        
        # --- FIX: Load size per dock widget ---
        state = self._state_manager.load_state(dock_widget.objectName())
        if state.width <= 0:  # Fallback to the general area size if it's the first time
            state = self._state_manager.load_state(area)
            
        size = QSize(state.width, state.height)
        
        self._uncheck_all()
        button.setChecked(True)
        self._active_button = button
        self._last_active_area = area
        
        # Respect the animation toggle
        self._overlay.show_widget(dock_widget, area, size=size, animate=self._animations_enabled)
        dock_widget.set_widget_state(WidgetState.pinned_shown) # <-- NEW STATE
    
        # --- FIX: ENFORCE Z-ORDERING ---
        # Explicitly raise all sidebars to the top of the rendering stack
        # so the overlay animates smoothly *underneath* the buttons.
        for bar in self._sidebars.values():
            bar.raise_()
    
    def _uncheck_all(self):
        for bar in self._sidebars.values():
            bar.uncheck_all()
    
    def _on_overlay_pin_back(self, dock_widget: 'DockWidget'):
        self.unpin_widget(dock_widget)
    
    def _on_drag_unpin(self, dock_widget: 'DockWidget'):
        self.unpin_widget_floating(dock_widget)
    
    def _on_resize_finished(self):
        # Save the size specifically for the active dock widget, not just the area
        if self._active_button:
            dock_widget = self._active_button.property("_dock_widget")
            if dock_widget:
                state = SidebarState(
                    width=self._overlay.width(),
                    height=self._overlay.height()
                )
                self._state_manager.save_state(dock_widget.objectName(), state)
    
    def _on_tab_drag_started(self, button: VerticalTabButton):
        dock_widget = button.property("_dock_widget")
        if dock_widget:
            # Check if mouse is still over the sidebar rect (likely internal reorder)
            sidebar = self._pinned.get(dock_widget)
            if sidebar:
                global_pos = QCursor.pos()
                if sidebar.rect().contains(sidebar.mapFromGlobal(global_pos)):
                    # Allow SideTabBar to handle reordering without making it float immediately
                    return
            self.unpin_widget_floating(dock_widget)
    
    def _on_sidebar_activated(self):
        self._hide_timer.stop()
    
    def pin_to_closest_sidebar(self, dock_widget: 'DockWidget'):
        if not self._sidebars:
            logger.warning('pin_to_closest_sidebar: no sidebars registered')
            return

        dock_area = dock_widget.dock_area_widget()
        main_widget = self._dock_manager

        if dock_area is not None and main_widget is not None:
            try:
                area_center = dock_area.mapToGlobal(dock_area.rect().center())
                # FIX: Convert manager rect to global coordinates so both
                # sides of the distance calculation use the same frame.
                main_top_left = main_widget.mapToGlobal(QPoint(0, 0))
                main_rect = QRect(main_top_left, main_widget.size())

                edge_distances = {
                    DockWidgetArea.left:   abs(area_center.x() - main_rect.left()),
                    DockWidgetArea.right:  abs(area_center.x() - main_rect.right()),
                    DockWidgetArea.top:    abs(area_center.y() - main_rect.top()),
                    DockWidgetArea.bottom: abs(area_center.y() - main_rect.bottom()),
                }

                available = {a: d for a, d in edge_distances.items() if a in self._sidebars}
                closest_area = min(available, key=available.get)
            except Exception:
                closest_area = next(iter(self._sidebars))
        else:
            closest_area = next(iter(self._sidebars))

        self.pin_widget(dock_widget, area=closest_area)

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
    def has_sidebars(self) -> bool:
        return len(self._sidebars) > 0


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