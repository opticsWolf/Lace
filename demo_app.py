# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0
"""

import sys
import logging
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
        QApplication, QMainWindow, QTextEdit,
        QLabel, QWidget, QStyle, QMenu,
)

from pathlib import Path

# Adjust these imports if your docking framework is in a subfolder
from lace import (
    DockManager, DockWidget, DockWidgetArea, DockThemeBridge, 
    apply_dock_theme, DockWidgetFeature, DockFlags, get_icon_provider
)

logging.basicConfig(level=logging.DEBUG)


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
    
    (DockFlags.drag_preview_shows_content_pixmap,
     "Drag Preview Shows Content",
     "Shows a snapshot of the widget content while dragging."),
]


class DemoMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dock Feature & Flags Testbed")
        self.resize(1200, 800)

        # Resolve the path to your icon directory
        base_path = Path(__file__).parent
        icon_dir = base_path / "lace" / "resources" / "lace_icons"

        # Initialize the provider singleton
        try:
            get_icon_provider(icon_dir)
        except Exception as e:
            logging.error(f"Failed to load icons: {e}")

        if self.windowIcon().isNull():
            standard_icon = self.style().standardIcon(QStyle.SP_TitleBarMenuButton)
            self.setWindowIcon(standard_icon)

        self.theme_bridge = DockThemeBridge()

        # 1. Initialize the DockManager
        self.dock_manager = DockManager(self)
        self.setCentralWidget(self.dock_manager)
        
        # 2. Build the UI Components
        self.create_dock_widgets()
        
        # 3. Create Menus
        self.create_theme_menu()
        self.create_flags_menu()

        # 4. Apply initial theme
        apply_dock_theme("default")

    def create_dock_widgets(self):
        """Creates widgets with specific feature constraints for testing."""
        
        # --- Empty Sidebars (to test Pin functionality) ---
        if hasattr(self.dock_manager, 'sidebar_manager'):
            self.dock_manager.sidebar_manager.add_sidebar(DockWidgetArea.right)
            self.dock_manager.sidebar_manager.add_sidebar(DockWidgetArea.left)

        # --- 1. Standard Widget (All Features) ---
        standard_widget = DockWidget("Standard Editor", self)
        standard_content = QTextEdit()
        standard_content.setPlaceholderText("I can be moved, closed, and floated.")
        standard_widget.set_widget(standard_content)
        standard_widget.set_features(DockWidgetFeature.all_features)
        self.dock_manager.add_dock_widget(DockWidgetArea.center, standard_widget)

        # --- 2. Unclosable Widget ---
        unclosable_widget = DockWidget("Unclosable Logger", self)
        unclosable_content = QTextEdit()
        unclosable_content.setReadOnly(True)
        unclosable_content.setText("FEATURE TEST:\nI cannot be closed via tab or title bar.\n\nTry grouping me with the Standard Editor!")
        unclosable_widget.set_widget(unclosable_content)
        unclosable_widget.set_features(DockWidgetFeature.movable | DockWidgetFeature.floatable | DockWidgetFeature.pinnable)
        self.dock_manager.add_dock_widget(DockWidgetArea.bottom, unclosable_widget)

        # --- 3. Unfloatable Widget ---
        unfloatable_widget = DockWidget("Unfloatable Tool", self)
        unfloatable_content = QLabel("FEATURE TEST:\nI can be closed, but I cannot be detached into a floating window.\n\nNotice the Detach icon is disabled.")
        unfloatable_content.setAlignment(Qt.AlignCenter)
        unfloatable_widget.set_widget(unfloatable_content)
        unfloatable_widget.set_features(DockWidgetFeature.movable | DockWidgetFeature.closable | DockWidgetFeature.pinnable)
        self.dock_manager.add_dock_widget(DockWidgetArea.right, unfloatable_widget)

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

    def create_theme_menu(self):
        menubar = self.menuBar()
        theme_menu = menubar.addMenu("Themes")

        def add_theme_action(name, theme_key):
            action = QAction(name, self)
            action.triggered.connect(lambda: apply_dock_theme(theme_key))
            theme_menu.addAction(action)

        add_theme_action("Default", "default")
        add_theme_action("Dark", "dark")
        add_theme_action("Light", "light")
        add_theme_action("Midnight", "midnight")
        add_theme_action("Monokai", "monokai")
        add_theme_action("Neutral", "neutral")
        add_theme_action("Nordic", "nordic")
        add_theme_action("Warm", "warm")

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
        self._add_flag_action(flags_menu, DockFlags.drag_preview_shows_content_pixmap)
        
        # Group: Tab behavior
        flags_menu.addSection("Tabs")
        self._add_flag_action(flags_menu, DockFlags.always_show_tabs)
        self._add_flag_action(flags_menu, DockFlags.show_tab_close_button)
        self._add_flag_action(flags_menu, DockFlags.active_tab_has_close_button)
        self._add_flag_action(flags_menu, DockFlags.middle_mouse_button_closes_tab)
        self._add_flag_action(flags_menu, DockFlags.floatable_tabs)
        self._add_flag_action(flags_menu, DockFlags.pinnable_tabs)
        
        # Group: Title bar buttons
        flags_menu.addSection("Title Bar")
        self._add_flag_action(flags_menu, DockFlags.dock_area_has_close_button)
        self._add_flag_action(flags_menu, DockFlags.dock_area_close_button_closes_tab)
        self._add_flag_action(flags_menu, DockFlags.dock_area_has_undock_button)
        self._add_flag_action(flags_menu, DockFlags.dock_area_has_pin_button)
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
        for container in self.dock_manager.dock_containers():
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
            DockFlags.dock_area_has_tabs_menu_button |
            DockFlags.middle_mouse_button_closes_tab |
            DockFlags.floatable_tabs |
            DockFlags.pinnable_tabs |
            DockFlags.drag_preview_shows_content_pixmap
        )
        self._sync_flag_actions()
        self._refresh_all_areas()


if __name__ == '__main__':
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion") 
    window = DemoMainWindow()
    window.show()
    sys.exit(app.exec())
