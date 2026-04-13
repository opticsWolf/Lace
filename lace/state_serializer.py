# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0

Enhanced Layout Serializer with comprehensive state tracking for:
- All dock containers (main + floating)
- Dock areas and their widgets
- Floating window positions and sizes
- Sidebar pinned widgets and overlay states
- Widget states (docked, floating, pinned, closed)
"""

import logging
import json
from typing import TYPE_CHECKING, Dict, Any, List, Optional

from .enums import DockFlags, WidgetState
from .dock_container_widget import DockContainerWidget
from .floating_dock_container import FloatingDockContainer

if TYPE_CHECKING:
    from .dock_manager import DockManager
    from .dock_widget import DockWidget

logger = logging.getLogger(__name__)


class LayoutSerializer:
    """
    Dedicated serializer for saving and restoring the DockManager's layout state.
    
    State Structure:
    {
        "type": "QtAdvancedDockingSystem",
        "version": <int>,
        "containers": [...],           # Main + floating containers
        "sidebars": {...},             # Sidebar pinned widgets & sizes
        "widget_states": {...},        # Per-widget state info
        "floating_geometries": {...},  # Floating window positions
    }
    """

    def __init__(self, manager: 'DockManager'):
        self._manager = manager

    # ─────────────────────────────────────────────────────────────────────
    #  Public API
    # ─────────────────────────────────────────────────────────────────────

    def save_state(self, version: int = 0) -> str:
        """
        Serializes the entire dock layout into a JSON string.
        Includes containers, sidebars, widget states, and floating geometries.
        """
        state_dict = {
            "type": "QtAdvancedDockingSystem",
            "version": version,
            "containers": [],
            "sidebars": {},
            "widget_states": {},
            "floating_geometries": {},
        }
        
        # 1. Save all containers (main + floating)
        containers = self._manager.dock_containers()
        for container in containers:
            if container is self._manager:
                container_state = DockContainerWidget.save_state(container)
            else:
                container_state = container.save_state()
            state_dict["containers"].append(container_state)
        
        # 2. Save floating window geometries separately for easy access
        state_dict["floating_geometries"] = self._save_floating_geometries()
        
        # 3. Save sidebar state if sidebar manager exists
        state_dict["sidebars"] = self._save_sidebar_state()
        
        # 4. Save comprehensive widget states
        state_dict["widget_states"] = self._save_widget_states()
        
        return json.dumps(state_dict)

    def save_state_formatted(self, version: int = 0) -> str:
        """Save state with pretty formatting for debugging."""
        state_json = self.save_state(version)
        return json.dumps(json.loads(state_json), indent=2)

    def check_format(self, state_json: str, version: int) -> bool:
        """Validates if the provided JSON matches the expected version."""
        try:
            data = json.loads(state_json)
            if data.get("type") != "QtAdvancedDockingSystem":
                return False
            return data.get("version") == version
        except (json.JSONDecodeError, TypeError):
            return False

    def restore_state(self, state_json: str, version: int) -> bool:
        """
        Parses the JSON state and rebuilds the dock layout.
        
        Restoration order:
        1. Pre-cleanup (hide floaters, mark widgets dirty)
        2. Restore containers (main + floating with geometries)
        3. Cleanup orphaned floating widgets
        4. Restore widget open/closed states
        5. Restore sidebar pinned widgets
        6. Restore active tabs and emit UI events
        """
        if not self.check_format(state_json, version):
            logger.error('LayoutSerializer: JSON format error or version mismatch!')
            return False

        try:
            state_dict = json.loads(state_json)
        except json.JSONDecodeError as e:
            logger.error(f'LayoutSerializer: JSON decode error: {e}')
            return False

        # Pre-restore cleanup
        self._hide_floating_widgets()
        self._mark_dock_widgets_dirty()
        
        # Close sidebar overlay before restoration
        self._close_sidebar_overlay()

        # 1. Restore containers
        containers_data = state_dict.get("containers", [])
        result = True
        
        for index, container_data in enumerate(containers_data):
            if not self._restore_container(index, container_data, testing=False):
                logger.error(f'LayoutSerializer: Failed restoring container at index {index}')
                result = False
                break

        # 2. Restore floating window geometries
        floating_geometries = state_dict.get("floating_geometries", {})
        self._restore_floating_geometries(floating_geometries)

        # 3. Cleanup orphaned floating widgets
        self._cleanup_orphaned_floating_widgets(expected_count=len(containers_data))

        # 4. Restore widget states (open/closed)
        self._restore_dock_widgets_open_state()
        
        # 5. Restore sidebar state (pinned widgets)
        sidebar_state = state_dict.get("sidebars", {})
        self._restore_sidebar_state(sidebar_state)

        # 6. Final UI updates
        self._restore_dock_areas_indices()
        self._emit_top_level_events()
        
        return result

    # ─────────────────────────────────────────────────────────────────────
    #  Save Helpers
    # ─────────────────────────────────────────────────────────────────────

    def _save_floating_geometries(self) -> Dict[str, Dict[str, int]]:
        """Save geometry of all floating containers."""
        geometries = {}
        for i, floating_widget in enumerate(self._manager.floating_widgets()):
            geo = floating_widget.geometry()
            geometries[f"floating_{i}"] = {
                "x": geo.x(),
                "y": geo.y(),
                "width": geo.width(),
                "height": geo.height(),
                "is_maximized": floating_widget.isMaximized(),
            }
        return geometries

    def _save_sidebar_state(self) -> Dict[str, Any]:
        """Save sidebar manager state if available."""
        if not hasattr(self._manager, 'sidebar_manager') or not self._manager.sidebar_manager:
            return {}
        
        try:
            return self._manager.sidebar_manager.save_state()
        except Exception as e:
            logger.warning(f"Failed to save sidebar state: {e}")
            return {}

    def _save_widget_states(self) -> Dict[str, Dict[str, Any]]:
        """
        Save comprehensive state for each dock widget.
        Captures: closed, widget_state, container, dock_area, tab_index
        """
        states = {}
        for name, dock_widget in self._manager.dock_widgets_map().items():
            widget_state = {
                "closed": dock_widget.is_closed(),
                "state": self._widget_state_to_str(dock_widget.widget_state()),
            }
            
            # Track location
            dock_area = dock_widget.dock_area_widget()
            if dock_area:
                container = dock_area.dock_container()
                widget_state["container_index"] = self._get_container_index(container)
                widget_state["in_dock_area"] = True
            else:
                widget_state["in_dock_area"] = False
            
            # Check if pinned to sidebar
            if hasattr(self._manager, 'sidebar_manager') and self._manager.sidebar_manager:
                if self._manager.sidebar_manager.is_pinned(dock_widget):
                    widget_state["pinned"] = True
            
            states[name] = widget_state
        
        return states

    def _widget_state_to_str(self, state: WidgetState) -> str:
        """Convert WidgetState enum to string."""
        return state.name if hasattr(state, 'name') else str(state)

    def _get_container_index(self, container) -> int:
        """Get index of container in the dock_containers list."""
        containers = self._manager.dock_containers()
        try:
            return containers.index(container)
        except ValueError:
            return -1

    # ─────────────────────────────────────────────────────────────────────
    #  Restore Helpers
    # ─────────────────────────────────────────────────────────────────────

    def _restore_container(self, index: int, container_data: Dict[str, Any], testing: bool) -> bool:
        """Routes the dict data to the appropriate container for restoration."""
        containers = self._manager.dock_containers()
        
        # If the JSON dictates more containers than we have, create a new floating one
        if index >= len(containers):
            if testing:
                return True
            floating_widget = FloatingDockContainer(dock_manager=self._manager)
            return floating_widget.restore_state(container_data, testing)
        
        # Otherwise, restore into the existing container
        container = containers[index]
        if container.is_floating():
            return container.floating_widget().restore_state(container_data, testing)
        else:
            return DockContainerWidget.restore_state(container, container_data, testing)

    def _restore_floating_geometries(self, geometries: Dict[str, Dict[str, int]]):
        """Restore floating window positions and sizes."""
        floating_widgets = self._manager.floating_widgets()
        
        for i, floating_widget in enumerate(floating_widgets):
            key = f"floating_{i}"
            if key not in geometries:
                continue
            
            geo = geometries[key]
            try:
                floating_widget.setGeometry(
                    geo.get("x", 100),
                    geo.get("y", 100),
                    geo.get("width", 400),
                    geo.get("height", 300)
                )
                if geo.get("is_maximized", False):
                    floating_widget.showMaximized()
            except Exception as e:
                logger.warning(f"Failed to restore floating geometry {key}: {e}")

    def _restore_sidebar_state(self, sidebar_state: Dict[str, Any]):
        """Restore sidebar pinned widgets and settings."""
        if not sidebar_state:
            return
        
        if not hasattr(self._manager, 'sidebar_manager') or not self._manager.sidebar_manager:
            logger.debug("No sidebar manager available for state restoration")
            return
        
        try:
            self._manager.sidebar_manager.restore_state(sidebar_state)
        except Exception as e:
            logger.warning(f"Failed to restore sidebar state: {e}")

    def _close_sidebar_overlay(self):
        """Close sidebar overlay before restoration."""
        if hasattr(self._manager, 'sidebar_manager') and self._manager.sidebar_manager:
            try:
                self._manager.sidebar_manager.close_overlay()
            except Exception:
                pass

    def _cleanup_orphaned_floating_widgets(self, expected_count: int):
        """Removes floating widgets that were not part of the restored state."""
        floating_widgets = self._manager.floating_widgets()
        
        # The first container is always the DockManager itself (index 0).
        # Any floating widgets start at index 1 conceptually.
        floating_widget_index = max(0, expected_count - 1)
        delete_count = len(floating_widgets) - floating_widget_index

        for i in range(delete_count):
            try:
                to_remove = floating_widgets[floating_widget_index + i]
                self._manager.remove_dock_container(to_remove.dock_container())
                to_remove.deleteLater()
            except Exception as e:
                logger.warning(f"Failed to cleanup orphaned floating widget: {e}")

    def _restore_dock_widgets_open_state(self):
        """Ensures widgets that were closed in the saved state are hidden, and open ones are shown."""
        for dock_widget in self._manager.dock_widgets_map().values():
            if dock_widget.property("dirty"):
                dock_widget.flag_as_unassigned()
            else:
                dock_widget.toggle_view_internal(not dock_widget.property("closed"))

    def _restore_dock_areas_indices(self):
        """Restores the active tab for each dock area."""
        for dock_container in self._manager.dock_containers():
            for i in range(dock_container.dock_area_count()):
                dock_area = dock_container.dock_area(i)
                dock_widget_name = dock_area.property("currentDockWidget")
                
                dock_widget = None
                if dock_widget_name:
                    dock_widget = self._manager.find_dock_widget(dock_widget_name)

                if not dock_widget or dock_widget.is_closed():
                    index = dock_area.index_of_first_open_dock_widget()
                    if index >= 0:
                        dock_area.set_current_index(index)
                else:
                    dock_area.internal_set_current_dock_widget(dock_widget)

    def _emit_top_level_events(self):
        """Triggers UI updates for toolbars and title bars based on their nested states."""
        for dock_container in self._manager.dock_containers():
            top_level_dock_widget = dock_container.top_level_dock_widget()
            if top_level_dock_widget is not None:
                top_level_dock_widget.emit_top_level_changed(True)
            else:
                for i in range(dock_container.dock_area_count()):
                    dock_area = dock_container.dock_area(i)
                    for dock_widget in dock_area.dock_widgets():
                        dock_widget.emit_top_level_changed(False)

    def _hide_floating_widgets(self):
        """Hide all floating widgets before restoration."""
        for floating_widget in self._manager.floating_widgets():
            floating_widget.hide()

    def _mark_dock_widgets_dirty(self):
        """Flags all current widgets so we know which ones weren't found in the restored state."""
        for dock_widget in self._manager.dock_widgets_map().values():
            dock_widget.setProperty("dirty", True)
