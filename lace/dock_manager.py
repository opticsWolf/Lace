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

from PySide6.QtCore import QObject, Signal, QPoint, QRect
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
from .layout_serializer import LayoutSerializer, LayoutError, LayoutPersistenceManager
from .dock_style_manager import get_dock_style_manager
from .dock_theme_bridge import DockThemeBridge
from ._trace import trace

logger = logging.getLogger(__name__)


class DockManager(QObject):
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
        super().__init__(parent)

        # 1. Initialize Styles (Grab the singleton so children can use it)
        self.style_manager = get_dock_style_manager()

        # 2. Flattened Internal State
        self._floating_widgets: List[FloatingDockContainer] = []
        self._containers: List['DockContainerWidget'] = []
        self._dock_widgets_map: Dict[str, 'DockWidget'] = {}
        self._perspectives: Dict[str, str] = {}  # Now stores JSON strings instead of QByteArray
        
        self._config_flags = DockFlags.default_config
        self._is_restoring_state = False

        # 3. Root Container (Composition over Inheritance)
        self._root = DockContainerWidget(self, parent)
        
        self._view_menu_groups: Dict[str, QMenu] = {}
        self._view_menu = QMenu("Show View", self._root)
        self._menu_insertion_order = InsertionOrder.by_spelling

        # 4. Global Event Bus (Phase 5)
        self.signals = DockSignals()
        self.signals.request_overlay_show.connect(self._handle_request_overlay_show)
        self.signals.request_overlay_hide.connect(self._handle_request_overlay_hide)
        self.signals.floating_widget_dropped.connect(self._handle_floating_widget_dropped)

        # 5. Overlays
        self._dock_area_overlay = DockOverlay(self._root, OverlayMode.dock_area)
        self._container_overlay = DockOverlay(self._root, OverlayMode.container)

        # 6. Base Layout Setup
        if isinstance(parent, QMainWindow):
            parent.setCentralWidget(self._root)

        # 7. Modular Sub-systems (Phase 3 & 4)
        self._serializer = LayoutSerializer(self)
        self._persistence = LayoutPersistenceManager(pathlib.Path.cwd())
        self.sidebar_manager = SidebarManager(self)

        # 8. Theme Bridge — pushes QPalette to the root container tree so
        #    standard Qt children (spinboxes, combos, tree-views) inside
        #    dock panels match the active dock theme automatically.
        self._theme_bridge = DockThemeBridge(target=self._root, style_name="", parent=self)

        if isinstance(parent, QMainWindow):
            self.sidebar_manager.setup_shortcuts(parent)

    # ─────────────────────────────────────────────────────────────────────
    #  FACADE API: Core Docking
    # ─────────────────────────────────────────────────────────────────────

    def add_dock_widget(self, area: DockWidgetArea, dock_widget: 'DockWidget', 
                        target_area: 'DockAreaWidget' = None) -> 'DockAreaWidget':
        trace("manager.add_dock_widget", area=getattr(area, 'name', str(area)), widget=dock_widget.objectName())
        dock_widget.set_dock_manager(self)
        self._dock_widgets_map[dock_widget.objectName()] = dock_widget
        return self._root.add_dock_widget(area, dock_widget, target_area)

    def remove_dock_widget(self, widget: 'DockWidget'):
        trace("manager.remove_dock_widget", widget=widget.objectName())
        self._dock_widgets_map.pop(widget.objectName(), None)
        self._root.remove_dock_widget(widget)

    def find_dock_widget(self, object_name: str) -> Optional['DockWidget']:
        return self._dock_widgets_map.get(object_name)

    def dock_widgets_map(self) -> Dict[str, 'DockWidget']:
        return self._dock_widgets_map

    # ─────────────────────────────────────────────────────────────────────
    #  FACADE API: Sidebars
    # ─────────────────────────────────────────────────────────────────────

    def add_sidebar_widget(self, area: DockWidgetArea, dock_widget: 'DockWidget'):
        """Clean API to pin a widget directly to the auto-hide sidebar."""
        dock_widget.set_dock_manager(self)
        self._dock_widgets_map[dock_widget.objectName()] = dock_widget
        sidebar = self.sidebar_manager.add_sidebar(area)
        self.sidebar_manager.pin_widget(dock_widget, sidebar)

    def _add_sidebar_to_layout(self, sidebar: QWidget, area: DockWidgetArea):
        """Places the sidebar at the correct edge of the main grid layout."""
        layout = self._root.layout()
        
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
        return self._serializer.serialize(version)

    def restore_state(self, state_json: str, version: int = 0) -> bool:
        """Restores the layout and sidebars from a JSON string."""
        if self._is_restoring_state:
            return False

        is_hidden = self._root.isHidden()
        if not is_hidden:
            self._root.hide()

        try:
            self._is_restoring_state = True
            self.restoring_state.emit()
            # deserialize() raises LayoutError subclasses on failure instead
            # of returning a bool, so translate that into the legacy contract.
            self._serializer.deserialize(state_json, version)
            success = True
        except LayoutError:
            logger.exception("DockManager: layout restore failed")
            success = False
        finally:
            self._is_restoring_state = False

        if success:
            self.state_restored.emit()
        
        if not is_hidden:
            self._root.show()

        return success

    def is_restoring_state(self) -> bool:
        return self._is_restoring_state

    def save_layout_to_file(self, filename: str, version: int = 0) -> None:
        """Atomically writes the current layout to ``filename`` (JSON)."""
        self._persistence.save_layout(self._serializer, filename, version)

    def load_layout_from_file(self, filename: str, version: int = 0) -> None:
        """Loads and applies a layout previously written with
        :meth:`save_layout_to_file`."""
        self._persistence.load_layout(self._serializer, filename, version)

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
        if self._config_flags == flags:
            return
        self._config_flags = flags
        self.notify_config_flags_changed()

    def set_config_flags(self, flags: DockFlags):
        self.config_flags = flags

    def notify_config_flags_changed(self):
        for container in self.dock_containers():
            for dock_area in container.opened_dock_areas():
                dock_area.update_title_bar_visibility()
                if dock_area._title_bar:
                    dock_area._title_bar.update_button_states()
                    tab_bar = dock_area._title_bar.tab_bar()
                    if tab_bar:
                        tab_bar._update_tab_bar_visibility()
                        for i in range(tab_bar.count()):
                            tab = tab_bar.tab(i)
                            if tab:
                                tab.update_close_button_visibility()

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
            if len(self._containers) > 0:
                trace("manager.register_container", container=dock_container.objectName() or dock_container.__class__.__name__)
            self._containers.append(dock_container)

    def remove_dock_container(self, dock_container: DockContainerWidget):
        if dock_container is not getattr(self, '_root', None) and dock_container in self._containers:
            trace("manager.remove_container", container=dock_container.objectName() or dock_container.__class__.__name__)
            self._containers.remove(dock_container)

    def dock_containers(self) -> List[DockContainerWidget]:
        # Clean up dead references before returning
        self._containers = [c for c in self._containers if _is_widget_alive(c)]
        return list(self._containers)

    @property
    def view_menu(self) -> QMenu:
        return self._view_menu

    # ─────────────────────────────────────────────────────────────────────
    #  Delegated Root Container Surface (Composition Facade)
    # ─────────────────────────────────────────────────────────────────────

    def dock_manager(self) -> 'DockManager':
        return self

    def root_container(self) -> DockContainerWidget:
        return self._root

    def add_dock_area(self, dock_area_widget: 'DockAreaWidget',
                      area: DockWidgetArea = DockWidgetArea.invalid,
                      target_dock_area: 'DockAreaWidget' = None):
        return self._root.add_dock_area(dock_area_widget, area, target_dock_area)

    def remove_dock_area(self, area: 'DockAreaWidget'):
        self._root.remove_dock_area(area)

    def dock_area(self, index: int) -> 'DockAreaWidget':
        return self._root.dock_area(index)

    def dock_area_count(self) -> int:
        return self._root.dock_area_count()

    def opened_dock_areas(self) -> list:
        return self._root.opened_dock_areas()

    def dock_area_at(self, global_pos: QPoint) -> 'DockAreaWidget':
        return self._root.dock_area_at(global_pos)

    def is_floating(self) -> bool:
        return self._root.is_floating()

    def top_level_dock_area(self) -> 'DockAreaWidget':
        return self._root.top_level_dock_area()

    def top_level_dock_widget(self) -> 'DockWidget':
        return self._root.top_level_dock_widget()

    def has_top_level_dock_widget(self) -> bool:
        return self._root.has_top_level_dock_widget()

    def dock_widgets(self) -> list:
        return self._root.dock_widgets()

    def features(self) -> DockFlags:
        return self._root.features()

    def floating_widget(self) -> Optional['FloatingDockContainer']:
        return self._root.floating_widget()

    def close_other_areas(self, keep_open_area: 'DockAreaWidget'):
        self._root.close_other_areas(keep_open_area)

    def refresh_style(self):
        self._root.refresh_style()

    def dump_layout(self):
        self._root.dump_layout()

    def root_splitter(self):
        return self._root.root_splitter()

    def last_added_dock_area_widget(self, area: DockWidgetArea) -> 'DockAreaWidget':
        return self._root.last_added_dock_area_widget(area)

    def z_order_index(self) -> int:
        return self._root.z_order_index()

    def is_in_front_of(self, other: 'DockContainerWidget') -> bool:
        return self._root.is_in_front_of(other)

    def drop_floating_widget(self, floating_widget: 'FloatingDockContainer', target_pos: QPoint):
        self._root.drop_floating_widget(floating_widget, target_pos)

    def _drop_into_container(self, floating_widget: 'FloatingDockContainer', area: DockWidgetArea):
        self._root._drop_into_container(floating_widget, area)

    def _drop_into_section(self, floating_widget: 'FloatingDockContainer', area: 'DockAreaWidget', drop_area: DockWidgetArea):
        self._root._drop_into_section(floating_widget, area, drop_area)

    def _drop_into_center_of_section(self, floating_widget: 'FloatingDockContainer', area: 'DockAreaWidget'):
        self._root._drop_into_center_of_section(floating_widget, area)

    # ─────────────────────────────────────────────────────────────────────
    #  Delegated QWidget Surface (for compatibility with existing callers)
    # ─────────────────────────────────────────────────────────────────────

    def layout(self):
        return self._root.layout()

    def rect(self) -> QRect:
        return self._root.rect()

    def size(self):
        return self._root.size()

    def geometry(self) -> QRect:
        return self._root.geometry()

    def width(self) -> int:
        return self._root.width()

    def height(self) -> int:
        return self._root.height()

    def window(self):
        return self._root.window()

    def mapToGlobal(self, pos: QPoint) -> QPoint:
        return self._root.mapToGlobal(pos)

    def mapFromGlobal(self, pos: QPoint) -> QPoint:
        return self._root.mapFromGlobal(pos)

    def isHidden(self) -> bool:
        return self._root.isHidden()

    def isVisible(self) -> bool:
        return self._root.isVisible()

    def show(self):
        self._root.show()

    def hide(self):
        self._root.hide()

    def update(self):
        self._root.update()

    def setFocus(self):
        self._root.setFocus()


def _is_widget_alive(widget: QWidget) -> bool:
    """Helper to check if a C++ Qt object has been deleted."""
    try:
        widget.isVisible()
        return True
    except RuntimeError:
        return False