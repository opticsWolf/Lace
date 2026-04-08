# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2019 Ken Lauer
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0

This file is part of Lace, adapted from qtpydocking.
Original code Copyright (c) 2019 Ken Lauer (BSD-3-Clause).
Modifications Copyright (c) 2026 opticsWolf (Apache-2.0).
"""

import logging
import pathlib
from typing import Dict, List, Optional

from PySide6.QtCore import Signal
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMainWindow, QMenu, QWidget

from .enums import InsertionOrder, DockFlags, DockWidgetArea, OverlayMode
from .dock_container_widget import DockContainerWidget
from .dock_overlay import DockOverlay
from .floating_dock_container import FloatingDockContainer
from .dock_widget import DockWidget
from .dock_area_widget import DockAreaWidget

# New Modular Sub-systems
from .dock_signals import DockSignals
from .sidebar_manager import SidebarManager
from .state_serializer import LayoutSerializer
from .dock_style_manager import get_dock_style_manager
from .dock_theme_bridge import DockThemeBridge

logger = logging.getLogger(__name__)


class DockManager(DockContainerWidget):
    """
    The main Facade for the Advanced Docking System.
    Manages dock containers, floating widgets, sidebars, and state serialization.
    """
    perspective_list_changed = Signal()
    perspectives_removed = Signal()
    restoring_state = Signal()
    state_restored = Signal()
    opening_perspective = Signal(str)
    perspective_opened = Signal(str)

    def __init__(self, parent: QWidget):
        super().__init__(self, parent)

        # 1. Initialize Styles (Grab the singleton so children can use it)
        self.style_manager = get_dock_style_manager()

        # 2. Flattened Internal State
        self._floating_widgets: List[FloatingDockContainer] = []
        self._containers: List['DockContainerWidget'] = [self]
        self._dock_widgets_map: Dict[str, 'DockWidget'] = {}
        self._perspectives: Dict[str, str] = {}  # Now stores JSON strings instead of QByteArray
        
        self._view_menu_groups: Dict[str, QMenu] = {}
        self._view_menu = QMenu("Show View", self)
        self._menu_insertion_order = InsertionOrder.by_spelling
        
        self._config_flags = DockFlags.default_config
        self._is_restoring_state = False

        # 2. Global Event Bus (Phase 5)
        self.signals = DockSignals()
        self.signals.request_overlay_show.connect(self._handle_request_overlay_show)
        self.signals.request_overlay_hide.connect(self._handle_request_overlay_hide)
        self.signals.floating_widget_dropped.connect(self._handle_floating_widget_dropped)

        # 3. Overlays
        self._dock_area_overlay = DockOverlay(self, OverlayMode.dock_area)
        self._container_overlay = DockOverlay(self, OverlayMode.container)

        # 4. Base Layout Setup
        self.create_root_splitter()
        if isinstance(parent, QMainWindow):
            parent.setCentralWidget(self)

        # 5. Modular Sub-systems (Phase 3 & 4)
        self._serializer = LayoutSerializer(self)
        self.sidebar_manager = SidebarManager(self)

        # 6. Theme Bridge — pushes QPalette to this widget tree so
        #    standard Qt children (spinboxes, combos, tree-views) inside
        #    dock panels match the active dock theme automatically.
        self._theme_bridge = DockThemeBridge(target=self, style_name="", parent=self)

        if isinstance(parent, QMainWindow):
            self.sidebar_manager.setup_shortcuts(parent)

    # ─────────────────────────────────────────────────────────────────────
    #  FACADE API: Core Docking
    # ─────────────────────────────────────────────────────────────────────

    def add_dock_widget(self, area: DockWidgetArea, dock_widget: 'DockWidget', 
                        target_area: 'DockAreaWidget' = None) -> 'DockAreaWidget':
        self._dock_widgets_map[dock_widget.objectName()] = dock_widget
        return super().add_dock_widget(area, dock_widget, target_area)

    def remove_dock_widget(self, widget: 'DockWidget'):
        self._dock_widgets_map.pop(widget.objectName(), None)
        super().remove_dock_widget(widget)

    def find_dock_widget(self, object_name: str) -> Optional['DockWidget']:
        return self._dock_widgets_map.get(object_name)

    def dock_widgets_map(self) -> Dict[str, 'DockWidget']:
        return self._dock_widgets_map

    # ─────────────────────────────────────────────────────────────────────
    #  FACADE API: Sidebars
    # ─────────────────────────────────────────────────────────────────────

    def add_sidebar_widget(self, area: DockWidgetArea, dock_widget: 'DockWidget'):
        """Clean API to pin a widget directly to the auto-hide sidebar."""
        self._dock_widgets_map[dock_widget.objectName()] = dock_widget
        sidebar = self.sidebar_manager.add_sidebar(area)
        self.sidebar_manager.pin_widget(dock_widget, sidebar)

    def _add_sidebar_to_layout(self, sidebar: QWidget, area: DockWidgetArea):
        """Places the sidebar at the correct edge of the main grid layout."""
        layout = self.layout()
        
        # Ensure we have a grid layout to work with
        if hasattr(layout, 'addWidget'):
            if area == DockWidgetArea.left:
                layout.addWidget(sidebar, 1, 0)
            elif area == DockWidgetArea.right:
                layout.addWidget(sidebar, 1, 2)
            elif area == DockWidgetArea.top:
                layout.addWidget(sidebar, 0, 1)
            elif area == DockWidgetArea.bottom:
                layout.addWidget(sidebar, 2, 1)

    # ─────────────────────────────────────────────────────────────────────
    #  FACADE API: State Management (JSON)
    # ─────────────────────────────────────────────────────────────────────

    def save_state(self, version: int = 0) -> str:
        """Saves the current layout and sidebars to a JSON string."""
        return self._serializer.save_state(version)

    def restore_state(self, state_json: str, version: int = 0) -> bool:
        """Restores the layout and sidebars from a JSON string."""
        if self._is_restoring_state:
            return False

        is_hidden = self.isHidden()
        if not is_hidden:
            self.hide()

        try:
            self._is_restoring_state = True
            self.restoring_state.emit()
            success = self._serializer.restore_state(state_json, version)
        finally:
            self._is_restoring_state = False

        if success:
            self.state_restored.emit()
        
        if not is_hidden:
            self.show()

        return success

    def is_restoring_state(self) -> bool:
        return self._is_restoring_state

    # ─────────────────────────────────────────────────────────────────────
    #  FACADE API: Styling & Theming
    # ─────────────────────────────────────────────────────────────────────

    def set_theme(self, theme_name: str) -> bool:
        """
        Applies a predefined theme to the entire docking system.
        Returns True if the theme was found and applied successfully.
        """
        from .dock_style_manager import apply_dock_theme
        return apply_dock_theme(theme_name)

    # ─────────────────────────────────────────────────────────────────────
    #  Perspectives
    # ─────────────────────────────────────────────────────────────────────

    def add_perspective(self, name: str):
        self._perspectives[name] = self.save_state()
        self.perspective_list_changed.emit()

    def remove_perspective(self, name: str):
        if name in self._perspectives:
            del self._perspectives[name]
            self.perspective_list_changed.emit()

    def remove_perspectives(self, names: List[str]):
        for name in names:
            self._perspectives.pop(name, None)
        self.perspective_list_changed.emit()

    def perspective_names(self) -> List[str]:
        return list(self._perspectives.keys())

    def open_perspective(self, perspective_name: str):
        if perspective_name not in self._perspectives:
            return
        
        self.opening_perspective.emit(perspective_name)
        self.restore_state(self._perspectives[perspective_name])
        self.perspective_opened.emit(perspective_name)

    # ─────────────────────────────────────────────────────────────────────
    #  Event Handlers for Decoupled Signals
    # ─────────────────────────────────────────────────────────────────────

    def _handle_request_overlay_show(self, container: 'DockContainerWidget'):
        self._container_overlay.show_overlay(container)

    def _handle_request_overlay_hide(self):
        self._container_overlay.hide_overlay()
        self._dock_area_overlay.hide_overlay()

    def _handle_floating_widget_dropped(self, floating_widget: FloatingDockContainer, target_pos):
        self.drop_floating_widget(floating_widget, target_pos)

    # ─────────────────────────────────────────────────────────────────────
    #  Internal Accessors & Routing
    # ─────────────────────────────────────────────────────────────────────

    @property
    def config_flags(self) -> DockFlags:
        return self._config_flags

    @config_flags.setter
    def config_flags(self, flags: DockFlags):
        self._config_flags = flags

    def container_overlay(self) -> DockOverlay:
        return self._container_overlay

    def dock_area_overlay(self) -> DockOverlay:
        return self._dock_area_overlay

    def floating_widgets(self) -> List[FloatingDockContainer]:
        return self._floating_widgets

    def register_floating_widget(self, floating_widget: FloatingDockContainer):
        self._floating_widgets.append(floating_widget)

    def remove_floating_widget(self, floating_widget: FloatingDockContainer):
        if floating_widget in self._floating_widgets:
            self._floating_widgets.remove(floating_widget)

    def register_dock_container(self, dock_container: DockContainerWidget):
        if dock_container not in self._containers:
            self._containers.append(dock_container)

    def remove_dock_container(self, dock_container: DockContainerWidget):
        if self is not dock_container and dock_container in self._containers:
            self._containers.remove(dock_container)

    def dock_containers(self) -> List[DockContainerWidget]:
        # Clean up dead references before returning
        self._containers = [c for c in self._containers if _is_widget_alive(c)]
        return list(self._containers)

    @property
    def view_menu(self) -> QMenu:
        return self._view_menu


def _is_widget_alive(widget: QWidget) -> bool:
    """Helper to check if a C++ Qt object has been deleted."""
    try:
        widget.isVisible()
        return True
    except RuntimeError:
        return False