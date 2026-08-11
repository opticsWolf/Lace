# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.

import sys
import logging
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QAction, QActionGroup, QIcon
from PySide6.QtWidgets import QApplication, QMainWindow, QTextEdit, QLabel, QStyle, QMenu, QFileDialog

from pathlib import Path

# Adjust these imports if your docking framework is in a subfolder
from lace import (
    DockManager, DockWidget, DockWidgetArea, DockThemeBridge, 
    apply_dock_theme, DockWidgetFeature, DockFlags, get_icon_provider,
    ThemeManager, SideBarFocusBehavior, InsertionOrder, TabBadgePosition,
    DockMenuBarStyler
)

logging.basicConfig(level=logging.DEBUG)


# ── RESIZE DEBUGGING ───────────────────────────────────────────────
# Resize tracing is emitted at DEBUG level – adjust the logger to see it.
logger = logging.getLogger(__name__)


def _dbg(tag, *parts):
    logger.debug("[RESIZE][%s] %s", tag, "  ".join(str(p) for p in parts))


class DebugTextEdit(QTextEdit):
    """QTextEdit that logs its own geometry and its parent-chain sizes
    on every resize event."""

    def resizeEvent(self, event):
        super().resizeEvent(event)
        chain = []
        p = self.parent()
        while p is not None:
            chain.append(f"{type(p).__name__}:{p.width()}x{p.height()}")
            p = p.parent()
        _dbg("textbox", f"textbox={self.width()}x{self.height()}", " <- ".join(chain))


# ── DockFlags metadata for menu generation ───────────────────────────

DOCK_FLAGS_INFO = [
    (DockFlags.opaque_splitter_resize, 
     "Opaque Splitter Resize",
     "Splitters instantly resize content instead of showing a rubber band."),
    
    (DockFlags.opaque_undocking,
     "Opaque Undocking",
     "Widgets instantly follow the cursor when torn off."),
    
    (DockFlags.always_show_tabs,
     "Always Show Tabs",
     "Tabs are always shown, even if there is only one widget in the area."),
    
    (DockFlags.show_tab_close_button,
     "Show Tab Close Button",
     "Tabs display their own close button."),
    
    (DockFlags.active_tab_has_close_button,
     "Active Tab Has Close Button",
     "Only the currently active tab displays a close button."),
    
    (DockFlags.dock_area_has_close_button,
     "Dock Area Has Close Button",
     "The dock area title bar displays a close button."),
    
    (DockFlags.dock_area_close_button_closes_tab,
     "Close Button Closes Tab",
     "Clicking the dock area close button closes the active tab, not the whole area."),
    
    (DockFlags.dock_area_has_undock_button,
     "Dock Area Has Undock Button",
     "The dock area title bar displays an undock button."),
    
    (DockFlags.dock_area_has_pin_button,
     "Dock Area Has Pin Button",
     "The dock area title bar displays a pin button."),
    
    (DockFlags.dock_area_has_maximize_button,
     "Dock Area Has Maximize Button",
     "The dock area title bar displays a maximize/restore button."),
    
    (DockFlags.sidebar_area_has_maximize_button,
     "Sidebar Area Has Maximize Button",
     "The sidebar title bar displays a maximize/restore button when an overlay panel is open."),
    
    (DockFlags.dock_area_has_tabs_menu_button,
     "Dock Area Has Tabs Menu",
     "The dock area title bar displays a menu button listing all tabs."),
    
    (DockFlags.middle_mouse_button_closes_tab,
     "Middle Click Closes Tab",
     "Clicking a tab with the middle mouse button closes it."),
    
    (DockFlags.floatable_tabs,
     "Floatable Tabs",
     "Tabs can be dragged out to float in their own window."),
    
    (DockFlags.pinnable_tabs,
     "Pinnable Tabs",
     "Tabs can be pinned into sidebar."),
    
    (DockFlags.hide_disabled_title_bar_icons,
     "Hide Disabled Title Bar Icons",
     "Hides disabled icons in the title bar instead of showing them grayed out."),
    
    (DockFlags.custom_tab_icons,
     "Custom Tab Icons",
     "Use custom icons via user config instead of widget defaults."),
    
    (DockFlags.chromeless_float,
     "Chromeless Float",
     "Floating container windows are created without native OS title bars or borders (FramelessWindowHint)."),
]


class DemoMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dock Feature & Flags Testbed")
        self.resize(1200, 800)

        # Resolve the path to your icon directory
        base_path = Path(__file__).resolve().parent          # demos/
        icon_dir = base_path.parent / "lace" / "resources" / "lace_icons"  # repo root

        # Initialize the provider singleton
        try:
            get_icon_provider(icon_dir)
        except Exception as e:
            logging.error(f"Failed to load icons: {e}")

        # Set application icon with absolute path so floating/detached windows inherit it
        icon_path = base_path / "icon.ico"
        if icon_path.exists():
            app_icon = QIcon(str(icon_path.resolve()))
            if not app_icon.isNull() and not app_icon.pixmap(16, 16).isNull():
                QApplication.instance().setWindowIcon(app_icon)
                self.setWindowIcon(app_icon)
        if self.windowIcon().isNull():
            standard_icon = self.style().standardIcon(QStyle.SP_TitleBarMenuButton)
            self.setWindowIcon(standard_icon)
            QApplication.instance().setWindowIcon(standard_icon)

        self.theme_bridge = DockThemeBridge()
        self.theme_manager = ThemeManager(QApplication.instance())
        self.theme_manager.auto_mode_enabled = False  # Start disabled so default theme shows until user toggles auto

        # 1. Initialize the DockManager
        self.dock_manager = DockManager(self)
        self.setCentralWidget(getattr(self.dock_manager, '_root', None) or self.dock_manager)
        
        # 2. Build the UI Components
        self.create_dock_widgets()
        
        # 3. Create Menus
        self.create_view_menu()
        self.create_theme_menu()
        self.create_flags_menu()
        self.create_sidebar_menu()

        # Remove Fusion's 1px bottom border from the menu bar and pin its
        # background to the sidebar colour; re-applied on every theme
        # switch by DockMenuBarStyler.
        self._menu_bar_styler = DockMenuBarStyler(self.menuBar(), parent=self)

        # 4. Apply initial theme
        apply_dock_theme("cyberpunk_neon")

    def changeEvent(self, event):
        # Whenever Windows changes themes, a PaletteChange event is broadcasted
        if event.type() == QEvent.Type.PaletteChange and hasattr(self, "theme_manager"):
            self.theme_manager.sync_theme()
        super().changeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        _dbg("window", f"window={self.width()}x{self.height()}")
        sw = getattr(self, "standard_widget", None)
        if sw is not None:
            sa = sw._scroll_area
            sa_str = f"{sa.width()}x{sa.height()}" if sa is not None else "N/A"
            _dbg("window",
                 f"dockwidget={sw.width()}x{sw.height()}",
                 f"scrollarea={sa_str}",
                 f"textbox={sw._widget.width()}x{sw._widget.height()}")

    def create_dock_widgets(self):
        """Creates widgets with specific feature constraints for testing."""
        
        # --- Empty Sidebars (to test Pin functionality) ---
        if hasattr(self.dock_manager, 'sidebar_manager'):
            self.dock_manager.sidebar_manager.add_sidebar(DockWidgetArea.right)
            self.dock_manager.sidebar_manager.add_sidebar(DockWidgetArea.left)

        # --- 1. Standard Widget (All Features) ---
        standard_widget = DockWidget("Standard Editor", self)
        standard_widget.set_default_icon_name("dock")
        standard_widget.set_custom_icon_name("pin")
        standard_content = DebugTextEdit()
        standard_content.setPlaceholderText("I can be moved, closed, and floated.")
        standard_widget.set_widget(standard_content)
        standard_widget.set_features(DockWidgetFeature.all_features)
        self.dock_manager.add_dock_widget(DockWidgetArea.center, standard_widget)
        self.standard_widget = standard_widget
        self.standard_content = standard_content

        # --- 2. Unclosable Widget ---
        unclosable_widget = DockWidget("Unclosable Logger", self)
        unclosable_widget.set_default_icon_name("tab_list")
        unclosable_widget.set_custom_icon_name("float")
        unclosable_content = QTextEdit()
        unclosable_content.setReadOnly(True)
        unclosable_content.setText("FEATURE TEST:\nI cannot be closed via tab or title bar.\n\nTry grouping me with the Standard Editor!")
        unclosable_widget.set_widget(unclosable_content)
        unclosable_widget.set_features(DockWidgetFeature.movable | DockWidgetFeature.floatable | DockWidgetFeature.pinnable)
        self.dock_manager.add_dock_widget(DockWidgetArea.bottom, unclosable_widget)

        # --- 3. Unfloatable Widget ---
        unfloatable_widget = DockWidget("Unfloatable Tool", self)
        unfloatable_widget.set_default_icon_name("pin")
        unfloatable_widget.set_custom_icon_name("unpin")
        unfloatable_content = QLabel("FEATURE TEST:\nI can be closed, but I cannot be detached into a floating window.\n\nNotice the Detach icon is disabled.")
        unfloatable_content.setAlignment(Qt.AlignCenter)
        unfloatable_widget.set_widget(unfloatable_content)
        unfloatable_widget.set_features(DockWidgetFeature.movable | DockWidgetFeature.closable | DockWidgetFeature.pinnable)
        self.dock_manager.add_dock_widget(DockWidgetArea.right, unfloatable_widget)

        # --- 3b. Immovable Widget ---
        immovable_widget = DockWidget("Immovable Tool", self)
        immovable_content = QLabel("FEATURE TEST:\nI can be closed, floated, or pinned, but I CANNOT be moved/dragged between dock areas.")
        immovable_content.setAlignment(Qt.AlignCenter)
        immovable_widget.set_widget(immovable_content)
        immovable_widget.set_features(DockWidgetFeature.closable | DockWidgetFeature.floatable | DockWidgetFeature.pinnable)
        self.dock_manager.add_dock_widget(DockWidgetArea.top, immovable_widget)

        # --- 4. Locked Widget (No Features) ---
        locked_widget = DockWidget("Locked Panel", self)
        locked_content = QLabel("FEATURE TEST:\nI have 'no_features'.\n\nI am permanently stuck here.")
        locked_content.setAlignment(Qt.AlignCenter)
        locked_widget.set_widget(locked_content)
        locked_widget.set_features(DockWidgetFeature.no_features)
        self.dock_manager.add_dock_widget(DockWidgetArea.left, locked_widget)

        # --- 5. Unpinnable Widget ---
        unpinnable_widget = DockWidget("Unpinnable Data", self)
        unpinnable_content = QTextEdit()
        unpinnable_content.setReadOnly(True)
        unpinnable_content.setText("FEATURE TEST:\nI can be moved, closed, and floated, but I CANNOT be pinned to the sidebar.\n\nNotice the Pin icon is disabled in my title bar and context menu.")
        unpinnable_widget.set_widget(unpinnable_content)
        unpinnable_widget.set_features(DockWidgetFeature.closable | DockWidgetFeature.movable | DockWidgetFeature.floatable)
        self.dock_manager.add_dock_widget(DockWidgetArea.center, unpinnable_widget)

        # --- 6. Locked Sidebar Tool (Permanently Locked in Sidebar) ---
        locked_sidebar_widget = DockWidget("Locked Sidebar Tool", self)
        locked_sidebar_content = QLabel("FEATURE TEST:\nI am permanently locked to this sidebar.\n\nI am not draggable/floatable and cannot be unpinned.")
        locked_sidebar_content.setAlignment(Qt.AlignCenter)
        locked_sidebar_widget.set_widget(locked_sidebar_content)
        locked_sidebar_widget.set_features(DockWidgetFeature.closable)
        self.dock_manager.add_sidebar_widget(DockWidgetArea.left, locked_sidebar_widget)

        # --- 7. Right Locked Panel (Neither floatable, closable, nor unpinnable) ---
        right_locked_widget = DockWidget("Right Locked Panel", self)
        right_locked_content = QLabel("FEATURE TEST:\nI am in the right sidebar.\n\nI am neither floatable, closable, nor unpinnable.")
        right_locked_content.setAlignment(Qt.AlignCenter)
        right_locked_widget.set_widget(right_locked_content)
        right_locked_widget.set_features(DockWidgetFeature.movable)
        self.dock_manager.add_sidebar_widget(DockWidgetArea.right, right_locked_widget)

        # --- 8. Right Pinnable Tool (Not floatable, but pinnable/unpinnable and closable) ---
        right_pinnable_widget = DockWidget("Right Pinnable Tool", self)
        right_pinnable_content = QLabel("FEATURE TEST:\nI am in the right sidebar.\n\nI am not floatable, but I am pinnable/unpinnable and closable.")
        right_pinnable_content.setAlignment(Qt.AlignCenter)
        right_pinnable_widget.set_widget(right_pinnable_content)
        right_pinnable_widget.set_features(DockWidgetFeature.closable | DockWidgetFeature.movable | DockWidgetFeature.pinnable)
        self.dock_manager.add_sidebar_widget(DockWidgetArea.right, right_pinnable_widget)
        # --- 9. Locked Area Demonstration ---
        locked_a = DockWidget("Design Item A", self)
        a_content = QLabel("Design Canvas A\n\nI am locked permanently to the 'DesignArea' dock area.\nI cannot be floated or pinned.")
        a_content.setAlignment(Qt.AlignCenter)
        locked_a.set_widget(a_content)
        locked_a.set_features(DockWidgetFeature.all_features)
        
        self.dock_manager.add_dock_widget(DockWidgetArea.bottom, locked_a)
        
        design_area = locked_a.dock_area_widget()
        if design_area:
            design_area.locked_name = "DesignArea"
            
        locked_a.locked_to_area = "DesignArea"
        
        locked_b = DockWidget("Design Item B", self)
        b_content = QLabel("Design Canvas B\n\nI am also locked permanently to the 'DesignArea' dock area.\nI cannot be floated or pinned.")
        b_content.setAlignment(Qt.AlignCenter)
        locked_b.set_widget(b_content)
        locked_b.set_features(DockWidgetFeature.all_features)
        locked_b.locked_to_area = "DesignArea"
        
        if design_area:
            design_area.add_dock_widget(locked_b)

        # Initialize demonstration badges on sidebar widgets to showcase TabBadgePosition
        if hasattr(self.dock_manager, 'sidebar_manager'):
            sm = self.dock_manager.sidebar_manager
            sm.update_badge(locked_sidebar_widget, 3)
            sm.update_badge(right_locked_widget, 12)
            sm.update_badge(right_pinnable_widget, 99)

    def create_view_menu(self):
        menubar = self.menuBar()
        view_menu = self.dock_manager.view_menu
        view_menu.setTitle("View")
        menubar.addMenu(view_menu)

        view_menu.addSeparator()
        order_menu = view_menu.addMenu("Insertion Order")
        order_group = QActionGroup(self)
        order_group.setExclusive(True)

        spelling_act = order_menu.addAction("By Spelling (Alphabetical)")
        spelling_act.setCheckable(True)
        spelling_act.setChecked(self.dock_manager.menu_insertion_order == InsertionOrder.by_spelling)
        def on_spelling_toggled(checked):
            if checked:
                self.dock_manager.menu_insertion_order = InsertionOrder.by_spelling
        spelling_act.triggered.connect(on_spelling_toggled)
        order_group.addAction(spelling_act)

        insertion_act = order_menu.addAction("By Insertion (Chronological)")
        insertion_act.setCheckable(True)
        insertion_act.setChecked(self.dock_manager.menu_insertion_order == InsertionOrder.by_insertion)
        def on_insertion_toggled(checked):
            if checked:
                self.dock_manager.menu_insertion_order = InsertionOrder.by_insertion
        insertion_act.triggered.connect(on_insertion_toggled)
        order_group.addAction(insertion_act)

    def create_theme_menu(self):
        menubar = self.menuBar()
        theme_menu = menubar.addMenu("Themes")

        def add_theme_action(name, theme_key):
            action = QAction(name, self)
            def on_theme_triggered():
                if hasattr(self, "theme_manager"):
                    self.theme_manager.auto_mode_enabled = False
                    if hasattr(self, "_auto_theme_action"):
                        self._auto_theme_action.setChecked(False)
                apply_dock_theme(theme_key)
            action.triggered.connect(on_theme_triggered)
            theme_menu.addAction(action)

        add_theme_action("Default", "default")
        add_theme_action("Dark", "dark")
        add_theme_action("Light", "light")
        add_theme_action("Midnight", "midnight")
        add_theme_action("Monokai", "monokai")
        add_theme_action("Neutral", "neutral")
        add_theme_action("Nordic", "nordic")
        add_theme_action("Warm", "warm")
        add_theme_action("Tokyo Night", "tokyo_night")
        add_theme_action("Catppuccin", "catppuccin")
        add_theme_action("Dracula", "dracula")
        add_theme_action("Solarized Dark", "solarized_dark")
        add_theme_action("Solarized Light", "solarized_light")
        add_theme_action("Cyberpunk Neon", "cyberpunk_neon")
        add_theme_action("Cyberpunk Edge", "cyberpunk_edge")

        theme_menu.addSeparator()
        self._auto_theme_action = QAction("Auto Theme (OS Sync)", self, checkable=True)
        self._auto_theme_action.setChecked(self.theme_manager.auto_mode_enabled)
        def on_auto_toggled(checked):
            self.theme_manager.auto_mode_enabled = checked
            if checked:
                self.theme_manager.sync_theme(force=True)
        self._auto_theme_action.toggled.connect(on_auto_toggled)
        theme_menu.addAction(self._auto_theme_action)

        def setup_override_menu(title, is_dark_target):
            menu = theme_menu.addMenu(title)
            group = QActionGroup(self)
            group.setExclusive(True)

            current_target = self.theme_manager.user_dark_theme if is_dark_target else self.theme_manager.user_light_theme

            themes_list = [
                ("Default", "default"),
                ("Dark", "dark"),
                ("Light", "light"),
                ("Midnight", "midnight"),
                ("Monokai", "monokai"),
                ("Neutral", "neutral"),
                ("Nordic", "nordic"),
                ("Warm", "warm"),
                ("Tokyo Night", "tokyo_night"),
                ("Catppuccin", "catppuccin"),
                ("Dracula", "dracula"),
                ("Solarized Dark", "solarized_dark"),
                ("Solarized Light", "solarized_light"),
                ("Cyberpunk Neon", "cyberpunk_neon"),
                ("Cyberpunk Edge", "cyberpunk_edge"),
            ]

            for name, key in themes_list:
                act = QAction(name, self, checkable=True)
                act._theme_key = key
                group.addAction(act)
                if current_target == key:
                    act.setChecked(True)

                def on_selected(checked=False, k=key):
                    if is_dark_target:
                        self.theme_manager.user_dark_theme = k
                    else:
                        self.theme_manager.user_light_theme = k
                    if self.theme_manager.auto_mode_enabled:
                        if self.theme_manager.is_windows_dark_mode() == is_dark_target:
                            self.theme_manager.sync_theme(force=True)
                act.triggered.connect(on_selected)
                menu.addAction(act)

            menu.addSeparator()
            custom_act = QAction("Custom QSS File...", self, checkable=True)
            custom_act._theme_key = "custom_qss"
            group.addAction(custom_act)
            if current_target not in [k for _, k in themes_list]:
                custom_act.setChecked(True)

            def on_custom_selected(checked=False):
                path, _ = QFileDialog.getOpenFileName(
                    self, f"Select QSS File for {'Dark' if is_dark_target else 'Light'} Theme",
                    "", "Stylesheet Files (*.qss *.css);;All Files (*)"
                )
                if path:
                    if is_dark_target:
                        self.theme_manager.user_dark_theme = path
                    else:
                        self.theme_manager.user_light_theme = path
                    custom_act.setChecked(True)
                    if self.theme_manager.auto_mode_enabled:
                        if self.theme_manager.is_windows_dark_mode() == is_dark_target:
                            self.theme_manager.sync_theme(force=True)
                else:
                    curr = self.theme_manager.user_dark_theme if is_dark_target else self.theme_manager.user_light_theme
                    for a in group.actions():
                        if getattr(a, "_theme_key", None) == curr:
                            a.setChecked(True)
                            break
            custom_act.triggered.connect(on_custom_selected)
            menu.addAction(custom_act)
            return menu

        setup_override_menu("Set Light Mode Theme", is_dark_target=False)
        setup_override_menu("Set Dark Mode Theme", is_dark_target=True)

    def create_flags_menu(self):
        """Menu to dynamically toggle DockManager configuration flags."""
        menubar = self.menuBar()
        flags_menu = menubar.addMenu("Global Flags")
        flags_menu.setToolTipsVisible(True)
        
        self._flag_actions = {}

        # Group: Splitter & Drag behavior
        flags_menu.addSection("Drag && Resize")
        self._add_flag_action(flags_menu, DockFlags.opaque_splitter_resize)
        self._add_flag_action(flags_menu, DockFlags.opaque_undocking)
        self._add_flag_action(flags_menu, DockFlags.chromeless_float)
        
        # Group: Tab behavior
        flags_menu.addSection("Tabs")
        self._add_flag_action(flags_menu, DockFlags.always_show_tabs)
        self._add_flag_action(flags_menu, DockFlags.show_tab_close_button)
        self._add_flag_action(flags_menu, DockFlags.active_tab_has_close_button)
        self._add_flag_action(flags_menu, DockFlags.middle_mouse_button_closes_tab)
        self._add_flag_action(flags_menu, DockFlags.floatable_tabs)
        self._add_flag_action(flags_menu, DockFlags.pinnable_tabs)
        self._add_flag_action(flags_menu, DockFlags.custom_tab_icons)
        
        # Group: Title bar buttons
        flags_menu.addSection("Title Bar")
        self._add_flag_action(flags_menu, DockFlags.dock_area_has_close_button)
        self._add_flag_action(flags_menu, DockFlags.dock_area_close_button_closes_tab)
        self._add_flag_action(flags_menu, DockFlags.dock_area_has_undock_button)
        self._add_flag_action(flags_menu, DockFlags.dock_area_has_pin_button)
        self._add_flag_action(flags_menu, DockFlags.dock_area_has_maximize_button)
        self._add_flag_action(flags_menu, DockFlags.sidebar_area_has_maximize_button)
        self._add_flag_action(flags_menu, DockFlags.dock_area_has_tabs_menu_button)
        self._add_flag_action(flags_menu, DockFlags.hide_disabled_title_bar_icons)
        
        # Presets submenu
        flags_menu.addSeparator()
        presets_menu = flags_menu.addMenu("Presets")
        
        default_action = presets_menu.addAction("Default Config")
        default_action.triggered.connect(self._apply_default_config)
        
        minimal_action = presets_menu.addAction("Minimal (No Buttons)")
        minimal_action.triggered.connect(self._apply_minimal_config)
        
        full_action = presets_menu.addAction("Full (All Buttons)")
        full_action.triggered.connect(self._apply_full_config)

    def create_sidebar_menu(self):
        """Menu to dynamically configure sidebar overlay behaviors like focus transfer."""
        menubar = self.menuBar()
        sidebar_menu = menubar.addMenu("Sidebar")
        
        focus_group = QActionGroup(self)
        focus_group.setExclusive(True)
        
        sidebar_menu.addSection("Focus Mode")
        
        modes = [
            ("Take Focus && Restore (Default)", SideBarFocusBehavior.take_focus_and_restore, "Sidebar steals focus on open and returns focus to previous card on close."),
            ("Take Focus Only", SideBarFocusBehavior.take_focus_only, "Sidebar steals focus on open without restoring focus on close."),
            ("No Focus Transfer", SideBarFocusBehavior.no_focus_transfer, "Sidebar does not steal focus when sliding out or in.")
        ]
        
        for text, behavior, tooltip in modes:
            action = sidebar_menu.addAction(text)
            action.setCheckable(True)
            action.setToolTip(tooltip)
            if behavior == self.dock_manager.sidebar_focus_behavior:
                action.setChecked(True)
            focus_group.addAction(action)
            
            action.triggered.connect(
                lambda checked=False, b=behavior: setattr(self.dock_manager, "sidebar_focus_behavior", b)
            )

        badge_group = QActionGroup(self)
        badge_group.setExclusive(True)
        
        sidebar_menu.addSection("Badge Position")
        badge_positions = [
            ("Top Right (Default)", TabBadgePosition.top_right, "Position badge counter at top-right corner of tab button."),
            ("Top Left", TabBadgePosition.top_left, "Position badge counter at top-left corner of tab button."),
            ("Bottom Right", TabBadgePosition.bottom_right, "Position badge counter at bottom-right corner of tab button."),
            ("Bottom Left", TabBadgePosition.bottom_left, "Position badge counter at bottom-left corner of tab button.")
        ]
        
        for text, pos, tooltip in badge_positions:
            action = sidebar_menu.addAction(text)
            action.setCheckable(True)
            action.setToolTip(tooltip)
            if pos == getattr(self.dock_manager, "tab_badge_position", TabBadgePosition.top_right):
                action.setChecked(True)
            badge_group.addAction(action)
            
            action.triggered.connect(
                lambda checked=False, p=pos: setattr(self.dock_manager, "tab_badge_position", p)
            )

        sidebar_menu.addSection("Badge Controls")
        
        def set_demo_badges(count: int):
            sm = getattr(self.dock_manager, "sidebar_manager", None)
            if sm:
                for dw in sm._pinned.keys():
                    sm.update_badge(dw, count)
                    
        action_badges_3 = sidebar_menu.addAction("Set All Badges to 3")
        action_badges_3.triggered.connect(lambda: set_demo_badges(3))
        
        action_badges_99 = sidebar_menu.addAction("Set All Badges to 99")
        action_badges_99.triggered.connect(lambda: set_demo_badges(99))
        
        action_badges_excl = sidebar_menu.addAction("Set All Badges to '!'")
        action_badges_excl.triggered.connect(lambda: set_demo_badges("!"))
        
        action_badges_quest = sidebar_menu.addAction("Set All Badges to '?'")
        action_badges_quest.triggered.connect(lambda: set_demo_badges("?"))
        
        action_badges_0 = sidebar_menu.addAction("Clear All Badges")
        action_badges_0.triggered.connect(lambda: set_demo_badges(0))

    def _add_flag_action(self, menu: QMenu, flag: DockFlags):
        """Add a checkable action for a DockFlag."""
        info = next((f for f in DOCK_FLAGS_INFO if f[0] == flag), None)
        if info is None:
            return
        
        flag_enum, label, tooltip = info
        
        action = QAction(label, self)
        action.setCheckable(True)
        action.setChecked(flag in self.dock_manager.config_flags)
        action.setToolTip(tooltip)
        action.setData(flag)
        action.toggled.connect(lambda checked, f=flag: self._on_flag_toggled(f, checked))
        
        menu.addAction(action)
        self._flag_actions[flag] = action

    def _on_flag_toggled(self, flag: DockFlags, checked: bool):
        """Handle flag toggle from menu."""
        if checked:
            self.dock_manager.config_flags |= flag
        else:
            self.dock_manager.config_flags &= ~flag
        
        self._refresh_all_areas()

    def _refresh_all_areas(self):
        """Force UI updates on all existing areas to reflect the new flags."""
        from lace.dock_splitter import DockSplitter
        opaque_resize = DockFlags.opaque_splitter_resize in self.dock_manager.config_flags
        for container in self.dock_manager.dock_containers():
            for splitter in container.findChildren(DockSplitter):
                splitter.setOpaqueResize(opaque_resize)
            for area in container.opened_dock_areas():
                area._update_title_bar_button_states()
                if hasattr(area._title_bar, 'update_pin_button_visibility'):
                    area._title_bar.update_pin_button_visibility()
                # Force tabs to re-evaluate close buttons
                for i in range(area._tab_bar().count()):
                    tab = area._tab_bar().tab(i)
                    tab.set_active_tab(tab.is_active_tab())

    def _sync_flag_actions(self):
        """Sync all menu checkboxes with current flags."""
        current = self.dock_manager.config_flags
        for flag, action in self._flag_actions.items():
            action.blockSignals(True)
            action.setChecked(flag in current)
            action.blockSignals(False)

    def _apply_default_config(self):
        """Apply the default configuration."""
        self.dock_manager.config_flags = DockFlags.default_config
        self._sync_flag_actions()
        self._refresh_all_areas()

    def _apply_minimal_config(self):
        """Apply minimal config - no title bar buttons."""
        self.dock_manager.config_flags = (
            DockFlags.opaque_splitter_resize |
            DockFlags.opaque_undocking |
            DockFlags.always_show_tabs
        )
        self._sync_flag_actions()
        self._refresh_all_areas()

    def _apply_full_config(self):
        """Apply full config - all buttons visible."""
        self.dock_manager.config_flags = (
            DockFlags.opaque_splitter_resize |
            DockFlags.opaque_undocking |
            DockFlags.always_show_tabs |
            DockFlags.show_tab_close_button |
            DockFlags.active_tab_has_close_button |
            DockFlags.dock_area_has_close_button |
            DockFlags.dock_area_has_undock_button |
            DockFlags.dock_area_has_pin_button |
            DockFlags.dock_area_has_maximize_button |
            DockFlags.sidebar_area_has_maximize_button |
            DockFlags.dock_area_has_tabs_menu_button |
            DockFlags.middle_mouse_button_closes_tab |
            DockFlags.floatable_tabs |
            DockFlags.pinnable_tabs |
            DockFlags.chromeless_float
        )
        self._sync_flag_actions()
        self._refresh_all_areas()


if __name__ == '__main__':
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion") 
    window = DemoMainWindow()
    window.show()
    sys.exit(app.exec())
