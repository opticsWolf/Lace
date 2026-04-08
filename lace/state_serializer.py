# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0
"""

import logging
import json
from typing import TYPE_CHECKING, Dict, Any

from .enums import DockFlags
from .dock_container_widget import DockContainerWidget
from .floating_dock_container import FloatingDockContainer

if TYPE_CHECKING:
    from .dock_manager import DockManager

logger = logging.getLogger(__name__)


class LayoutSerializer:
    """
    Dedicated serializer for saving and restoring the DockManager's layout state.
    Utilizes standard JSON for easy debugging, persistence, and cross-compatibility.
    """

    def __init__(self, manager: 'DockManager'):
        self._manager = manager

    def save_state(self, version: int = 0) -> str:
        """
        Serializes the entire dock layout into a JSON string.
        Child widgets (Containers, Areas, Splitters) now return dicts via `save_state()`.
        """
        state_dict = {
            "type": "QtAdvancedDockingSystem",
            "version": version,
            "containers": []
        }
        
        containers = self._manager.dock_containers()
        
        for container in containers:
            if container is self._manager:
                # The DockManager is the root DockContainerWidget
                # We call the class method directly to avoid recursive loops
                container_state = DockContainerWidget.save_state(container)
            else:
                container_state = container.save_state()
            
            state_dict["containers"].append(container_state)

        # Apply formatting if configured
        #indent = 2 if DockFlags.xml_auto_formatting in self._manager.config_flags else None
        # We can optionally compress the string here if needed, but standard 
        # string returns are usually preferred for JSON workflows.
        return json.dumps(state_dict)#, indent=indent)

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
        """Parses the JSON state and rebuilds the dock layout."""
        if not self.check_format(state_json, version):
            logger.error('LayoutSerializer: JSON format error or version mismatch!')
            return False

        try:
            state_dict = json.loads(state_json)
        except json.JSONDecodeError:
            return False

        # Pre-restore cleanup
        self._hide_floating_widgets()
        self._mark_dock_widgets_dirty()

        # The actual restoration
        containers_data = state_dict.get("containers", [])
        result = True
        
        for index, container_data in enumerate(containers_data):
            result = self._restore_container(index, container_data, testing=False)
            if not result:
                logger.error(f'LayoutSerializer: Failed restoring container at index {index}')
                break

        # Cleanup floating widgets that existed previously but aren't in the new state
        self._cleanup_orphaned_floating_widgets(expected_count=len(containers_data))

        # Post-restore UI updates
        self._restore_dock_widgets_open_state()
        self._restore_dock_areas_indices()
        self._emit_top_level_events()
        
        return result

    # ─────────────────────────────────────────────────────────────────────
    #  Internal Restoration Lifecycle Methods
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

    def _cleanup_orphaned_floating_widgets(self, expected_count: int):
        """Removes floating widgets that were not part of the restored state."""
        floating_widgets = self._manager.floating_widgets()
        
        # The first container is always the DockManager itself (index 0).
        # Any floating widgets start at index 1 conceptually.
        floating_widget_index = max(0, expected_count - 1)
        delete_count = len(floating_widgets) - floating_widget_index

        for i in range(delete_count):
            to_remove = floating_widgets[floating_widget_index + i]
            self._manager.remove_dock_container(to_remove.dock_container())
            to_remove.deleteLater()

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
        for floating_widget in self._manager.floating_widgets():
            floating_widget.hide()

    def _mark_dock_widgets_dirty(self):
        """Flags all current widgets so we know which ones weren't found in the restored state."""
        for dock_widget in self._manager.dock_widgets_map().values():
            dock_widget.setProperty("dirty", True)