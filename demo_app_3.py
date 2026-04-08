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
        QLabel, QWidget, QStyle,
)

# Adjust these imports if your docking framework is in a subfolder
from lace import (
    DockManager, DockWidget, DockWidgetArea, DockThemeBridge, 
    apply_dock_theme, DockWidgetFeature, DockFlags
)

logging.basicConfig(level=logging.DEBUG)


class DemoMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Dock Feature & Flags Testbed")
        self.resize(1200, 800)

        if self.windowIcon().isNull():
            standard_icon = self.style().standardIcon(QStyle.SP_TitleBarMenuButton)
            self.setWindowIcon(standard_icon)

        self.theme_bridge = DockThemeBridge()

        # 1. Initialize the DockManager
        self.dock_manager = DockManager(self)
        self.setCentralWidget(self.dock_manager)
        
        # Enable the Pin Button flag by default for the demo
        self.dock_manager.config_flags |= DockFlags.title_bar_has_pin_button

        # 2. Build the UI Components
        self.create_dock_widgets()
        
        # 3. Create Menus
        self.create_theme_menu()
        self.create_flags_menu()

        # 4. Apply initial theme
        apply_dock_theme("dark")

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
        # Default is already all_features, but let's be explicit
        standard_widget.set_features(DockWidgetFeature.all_features)
        self.dock_manager.add_dock_widget(DockWidgetArea.center, standard_widget)

        # --- 2. Unclosable Widget ---
        unclosable_widget = DockWidget("Unclosable Logger", self)
        unclosable_content = QTextEdit()
        unclosable_content.setReadOnly(True)
        unclosable_content.setText("FEATURE TEST:\nI cannot be closed via tab or title bar.\n\nTry grouping me with the Standard Editor!")
        unclosable_widget.set_widget(unclosable_content)
        # Missing the closable flag
        unclosable_widget.set_features(DockWidgetFeature.movable | DockWidgetFeature.floatable | DockWidgetFeature.pinnable)
        self.dock_manager.add_dock_widget(DockWidgetArea.bottom, unclosable_widget)

        # --- 3. Unfloatable Widget ---
        unfloatable_widget = DockWidget("Unfloatable Tool", self)
        unfloatable_content = QLabel("FEATURE TEST:\nI can be closed, but I cannot be detached into a floating window.\n\nNotice the Detach icon is disabled.")
        unfloatable_content.setAlignment(Qt.AlignCenter)
        unfloatable_widget.set_widget(unfloatable_content)
        # Missing the floatable flag
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
        
        # Exclude pinnable
        unpinnable_widget.set_features(DockWidgetFeature.closable | DockWidgetFeature.movable | DockWidgetFeature.floatable)
        self.dock_manager.add_dock_widget(DockWidgetArea.center, unpinnable_widget)

    def create_theme_menu(self):
        menubar = self.menuBar()
        theme_menu = menubar.addMenu("Themes")

        def add_theme_action(name, theme_key):
            action = QAction(name, self)
            action.triggered.connect(lambda: apply_dock_theme(theme_key))
            theme_menu.addAction(action)

        add_theme_action("Dark (Default)", "dark")
        add_theme_action("Light", "light")

    def create_flags_menu(self):
        """Menu to dynamically toggle DockManager configuration flags."""
        menubar = self.menuBar()
        flags_menu = menubar.addMenu("Global Flags")

        # Helper to bind a menu checkbox to a specific DockFlag
        def add_flag_toggle(name, flag: DockFlags):
            action = QAction(name, self)
            action.setCheckable(True)
            # Check if the flag is currently active in the manager
            action.setChecked(flag in self.dock_manager.config_flags)
            
            def on_toggled(checked):
                if checked:
                    self.dock_manager.config_flags |= flag
                else:
                    self.dock_manager.config_flags &= ~flag
                
                # Force UI updates on all existing areas to reflect the new flags
                for container in self.dock_manager.dock_containers():
                    for area in container.opened_dock_areas():
                        area._update_title_bar_button_states()
                        if hasattr(area._title_bar, 'update_pin_button_visibility'):
                            area._title_bar.update_pin_button_visibility()
                        # Force tabs to re-evaluate close buttons
                        for i in range(area._tab_bar().count()):
                            tab = area._tab_bar().tab(i)
                            tab.set_active_tab(tab.is_active_tab())
                            
            action.toggled.connect(on_toggled)
            flags_menu.addAction(action)

        add_flag_toggle("Active Tab has Close Button", DockFlags.active_tab_has_close_button)
        add_flag_toggle("Area Close Button Closes Active Tab", DockFlags.dock_area_close_button_closes_tab)
        add_flag_toggle("Title Bar has Pin Button", DockFlags.title_bar_has_pin_button)
        add_flag_toggle("Opaque Splitter Resize", DockFlags.opaque_splitter_resize)


if __name__ == '__main__':
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion") 
    window = DemoMainWindow()
    window.show()
    sys.exit(app.exec())