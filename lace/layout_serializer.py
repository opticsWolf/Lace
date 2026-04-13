# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0

Enhanced Layout Serialization and Persistence System
"""

import os
import time
import tempfile
import logging
import json
import uuid
import errno
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Any, List

from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QRect

from .enums import DockFlags, WidgetState
from .dock_container_widget import DockContainerWidget
from .floating_dock_container import FloatingDockContainer

if TYPE_CHECKING:
    from .dock_manager import DockManager
    from .dock_widget import DockWidget

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
#  Exceptions
# ─────────────────────────────────────────────────────────────────────

class LayoutError(Exception):
    """Base exception for layout operations."""
    pass

class LayoutIOError(LayoutError):
    """Raised when disk I/O fails during safe write/read operations."""
    pass

class InvalidFormatError(LayoutError):
    """Raised when the layout JSON schema is corrupt or version mismatched."""
    pass

class RestoreFailureError(LayoutError):
    """Raised when the layout fails pre-validation or structural reconstruction."""
    pass


# ─────────────────────────────────────────────────────────────────────
#  Persistence Layer
# ─────────────────────────────────────────────────────────────────────

class LayoutPersistenceManager:
    """
    Dedicated manager for handling layout file operations.
    Ensures leak-free, atomic file writes with exhaustive OS error handling.
    """

    def __init__(self, base_dir: Path | str):
        self._base_dir = Path(base_dir).resolve()

    def set_default_path(self, path: Path | str) -> None:
        self._base_dir = Path(path).resolve()
        logger.debug(f"LayoutPersistenceManager: Base directory set to {self._base_dir}")

    def save_layout(self, serializer: 'LayoutSerializer', filename: str, version: int = 0, formatted: bool = True) -> None:
        filepath = self._base_dir / filename
        if filepath.suffix != '.json':
            filepath = filepath.with_suffix('.json')

        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.exception(f"LayoutPersistenceManager: Failed to create target directory {filepath.parent}")
            raise LayoutIOError(f"Directory creation failed: {e}") from e

        state_json = serializer.serialize(version=version, formatted=formatted)
        
        fd, temp_file_str = tempfile.mkstemp(dir=filepath.parent, prefix="layout_tmp_", suffix=".json", text=True)
        temp_path = Path(temp_file_str)

        try:
            f = os.fdopen(fd, 'w', encoding='utf-8')
            with f:
                f.write(state_json)
                f.flush()
                os.fsync(fd)

            self._safe_replace(temp_path, filepath)
            logger.info(f"LayoutPersistenceManager: Successfully saved layout atomically to {filepath}")
            
        except OSError as e:
            logger.exception(f"LayoutPersistenceManager: OS write failed for {filepath}")
            if e.errno == errno.ENOSPC:
                raise LayoutIOError("Disk full: Cannot save layout data.") from e
            raise LayoutIOError(f"Failed to safely write layout to disk: {e}") from e
        except Exception as e:
            logger.exception(f"LayoutPersistenceManager: Unexpected failure saving {filepath}")
            raise LayoutIOError(f"Critical write failure: {e}") from e
        finally:
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError as e:
                    logger.warning(f"LayoutPersistenceManager: Failed to unlink temporary file {temp_path}: {e}")

    def _safe_replace(self, src: Path, dst: Path, max_retries: int = 4, base_delay: float = 0.1) -> None:
        """Cross-platform file replacement handling locking delays."""
        for attempt in range(max_retries):
            try:
                os.replace(src, dst)
                return
            except OSError as e:
                if e.errno in (errno.EACCES, errno.EPERM, errno.EBUSY):
                    if attempt == max_retries - 1:
                        raise LayoutIOError(f"File locked, atomic replace failed after {max_retries} attempts.") from e
                    time.sleep(base_delay * (2 ** attempt))
                else:
                    raise

    def load_layout(self, serializer: 'LayoutSerializer', filename: str, target_version: int = 0) -> None:
        filepath = self._base_dir / filename
        if filepath.suffix != '.json':
            filepath = filepath.with_suffix('.json')

        if not filepath.exists():
            raise LayoutIOError(f"Layout file not found at {filepath}")

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                state_json = f.read()
        except OSError as e:
            logger.exception(f"LayoutPersistenceManager: Disk I/O error reading from {filepath}")
            raise LayoutIOError(f"Failed to read layout file: {e}") from e

        serializer.deserialize(state_json, target_version)


# ─────────────────────────────────────────────────────────────────────
#  State Extractor (View -> Data)
# ─────────────────────────────────────────────────────────────────────

class LayoutStateBuilder:
    """
    Pure data-extractor. Strictly read-only.
    Never mutates Qt objects or sets dynamic properties during serialization.
    """
    
    SYSTEM_TYPE: str = "QtAdvancedDockingSystem"

    def __init__(self, manager: 'DockManager'):
        self._manager = manager
        self._transient_id_map: Dict[Any, str] = {}

    def build_state_dict(self, version: int) -> Dict[str, Any]:
        self._transient_id_map.clear()
        
        state_dict = {
            "type": self.SYSTEM_TYPE,
            "version": version,
            "containers": [],
            "sidebars": self._save_sidebar_state(),
            "container_geometries": {},
            # widget_states built last as it depends on the id map
        }
        
        for container in self._manager.dock_containers():
            is_main = (container is self._manager)
            # Generate a transient linking ID solely for this JSON document
            cid = "main" if is_main else str(uuid.uuid4())
            self._transient_id_map[container] = cid
            
            c_state = DockContainerWidget.save_state(container) if is_main else container.save_state()
            state_dict["containers"].append({
                "id": cid,
                "is_main": is_main,
                "data": c_state
            })
            
        state_dict["container_geometries"] = self._save_container_geometries()
        state_dict["widget_states"] = self._save_widget_states()
            
        return state_dict

    def _save_container_geometries(self) -> Dict[str, Dict[str, Any]]:
        geometries = {}
        for container in self._manager.dock_containers():
            if container.is_floating():
                cid = self._transient_id_map[container]
                geo = container.floating_widget().geometry()
                geometries[cid] = {
                    "x": geo.x(),
                    "y": geo.y(),
                    "width": geo.width(),
                    "height": geo.height(),
                    "is_maximized": container.floating_widget().isMaximized(),
                }
        return geometries

    def _save_sidebar_state(self) -> Dict[str, Any]:
        if not hasattr(self._manager, 'sidebar_manager') or not self._manager.sidebar_manager:
            return {}
        try:
            return self._manager.sidebar_manager.save_state()
        except Exception as e:
            logger.warning(f"LayoutStateBuilder: Failed to save sidebar state: {e}")
            return {}

    def _save_widget_states(self) -> Dict[str, Dict[str, Any]]:
        states = {}
        for name, dock_widget in self._manager.dock_widgets_map().items():
            widget_state = {
                "closed": dock_widget.is_closed(),
                "state": dock_widget.widget_state().name if hasattr(dock_widget.widget_state(), 'name') else str(dock_widget.widget_state()),
            }
            
            dock_area = dock_widget.dock_area_widget()
            if dock_area:
                container = dock_area.dock_container()
                widget_state["container_id"] = self._transient_id_map.get(container, "unknown")
                widget_state["in_dock_area"] = True
                try:
                    widget_state["tab_index"] = dock_area.dock_widgets().index(dock_widget)
                except ValueError:
                    widget_state["tab_index"] = -1
            else:
                widget_state["in_dock_area"] = False
                widget_state["tab_index"] = -1
            
            if hasattr(self._manager, 'sidebar_manager') and self._manager.sidebar_manager:
                if self._manager.sidebar_manager.is_pinned(dock_widget):
                    widget_state["pinned"] = True
            
            states[name] = widget_state
            
        return states


# ─────────────────────────────────────────────────────────────────────
#  Layout Engine (Data -> View)
# ─────────────────────────────────────────────────────────────────────

class LayoutEngine:
    """Consumes a pre-validated dictionary and mutates the UI state."""

    def __init__(self, manager: 'DockManager'):
        self._manager = manager

    def apply_state(self, state_dict: Dict[str, Any]) -> None:
        """Applies state ONLY after deep reality validation."""
        self._validate_can_restore(state_dict)

        self._hide_floating_widgets()
        self._mark_dock_widgets_dirty()
        self._close_sidebar_overlay()

        # Existing floating widgets are treated as an anonymous reusable pool to prevent UI flicker
        floating_pool = list(self._manager.floating_widgets())
        to_maximize = []
        
        for c_info in state_dict["containers"]:
            cid = c_info.get("id")
            c_data = c_info.get("data", {})
            
            if c_info.get("is_main"):
                DockContainerWidget.restore_state(self._manager, c_data, testing=False)
            else:
                fw = floating_pool.pop() if floating_pool else FloatingDockContainer(dock_manager=self._manager)
                fw.restore_state(c_data, testing=False)
                
                # Link geometry immediately via the transient ID
                geo = state_dict.get("container_geometries", {}).get(cid)
                if geo:
                    self._apply_container_geometry(fw, geo)
                    if geo.get("is_maximized", False):
                        to_maximize.append(fw)

        # Cleanup unused pool windows
        for orphan_fw in floating_pool:
            self._manager.remove_dock_container(orphan_fw.dock_container())
            orphan_fw.deleteLater()

        self._restore_dock_widgets_open_state()
        self._restore_sidebar_state(state_dict.get("sidebars", {}))
        self._restore_dock_areas_indices(state_dict.get("widget_states", {}))
        self._emit_top_level_events()

        # Apply deferred visibility states to prevent mid-restoration UI flicker
        for fw in to_maximize:
            fw.showMaximized()

    def _validate_can_restore(self, state_dict: Dict[str, Any]) -> None:
        """
        Validates the state tree against reality BEFORE any mutations occur.
        Ensures atomic-like safety by refusing to apply corrupted payloads.
        """
        required_keys = {"type", "version", "containers", "widget_states"}
        if not required_keys.issubset(state_dict.keys()):
            raise InvalidFormatError(f"Missing required root keys. Found: {state_dict.keys()}")

        if not isinstance(state_dict["containers"], list):
            raise InvalidFormatError("'containers' must be a list structure.")

        # 1. Validate Geometries Bounds
        geometries = state_dict.get("container_geometries", {})
        for cid, geo in geometries.items():
            if not isinstance(geo, dict):
                raise InvalidFormatError(f"Geometry for {cid} must be a dict.")
            for key in ("x", "y", "width", "height"):
                if key not in geo or not isinstance(geo[key], (int, float)):
                    raise InvalidFormatError(f"Invalid or missing geometry key '{key}' for container {cid}.")
            if geo["width"] <= 0 or geo["height"] <= 0:
                raise InvalidFormatError(f"Geometry dimensions for {cid} must be positive integers.")
            if geo["width"] > 32000 or geo["height"] > 32000:
                raise InvalidFormatError(f"Geometry dimensions for {cid} exceed maximum reasonable Qt rendering bounds.")

        # 2. Validate Widgets Reality Check
        available_widgets = set(self._manager.dock_widgets_map().keys())
        saved_widgets = set(state_dict["widget_states"].keys())
        missing = saved_widgets - available_widgets

        if missing:
            logger.warning(f"Layout references missing widgets: {missing}. Safely ignoring them.")
            for m in missing:
                del state_dict["widget_states"][m]

    def _apply_container_geometry(self, fw: 'FloatingDockContainer', geo: Dict[str, Any]) -> None:
        """
        Applies geometry data, validating against actual active screens.
        Safely rescues off-screen windows (e.g. unplugged multi-monitor).
        """
        x = int(geo.get("x", 100))
        y = int(geo.get("y", 100))
        w = max(50, int(geo.get("width", 400)))
        h = max(50, int(geo.get("height", 300)))

        target_rect = QRect(x, y, w, h)
        is_on_screen = False

        # Cross-reference target geometry with all currently active monitors
        screens = QGuiApplication.screens()
        for screen in screens:
            screen_geo = screen.availableGeometry()
            if screen_geo.intersects(target_rect):
                is_on_screen = True
                
                # Prevent window from being vastly larger than the display it's currently on
                w = min(w, screen_geo.width())
                h = min(h, screen_geo.height())
                target_rect.setWidth(w)
                target_rect.setHeight(h)
                break

        # If the window would spawn entirely off-screen (monitor was unplugged),
        # relocate it to the center of the primary screen to rescue it.
        if not is_on_screen and screens:
            primary_screen = QGuiApplication.primaryScreen()
            if primary_screen:
                avail_geo = primary_screen.availableGeometry()
                w = min(w, avail_geo.width())
                h = min(h, avail_geo.height())
                x = avail_geo.x() + (avail_geo.width() - w) // 2
                y = avail_geo.y() + (avail_geo.height() - h) // 2

        try:
            fw.setGeometry(x, y, w, h)
        except Exception as e:
            logger.warning(f"Failed to apply geometry: {e}")

    def _mark_dock_widgets_dirty(self) -> None:
        for dock_widget in self._manager.dock_widgets_map().values():
            dock_widget.setProperty("_lace_unassigned_marker", True)

    def _restore_dock_widgets_open_state(self) -> None:
        for dock_widget in self._manager.dock_widgets_map().values():
            if dock_widget.property("_lace_unassigned_marker"):
                dock_widget.flag_as_unassigned()
            else:
                dock_widget.toggle_view_internal(not dock_widget.property("closed"))
            dock_widget.setProperty("_lace_unassigned_marker", None)

    def _restore_sidebar_state(self, sidebar_state: Dict[str, Any]) -> None:
        if not sidebar_state or not hasattr(self._manager, 'sidebar_manager') or not self._manager.sidebar_manager:
            return
        try:
            self._manager.sidebar_manager.restore_state(sidebar_state)
        except Exception as e:
            logger.warning(f"Failed to restore sidebar state: {e}")

    def _close_sidebar_overlay(self) -> None:
        if hasattr(self._manager, 'sidebar_manager') and self._manager.sidebar_manager:
            try:
                self._manager.sidebar_manager.close_overlay()
            except Exception:
                pass

    def _restore_dock_areas_indices(self, widget_states: Dict[str, Dict[str, Any]]) -> None:
        for dock_container in self._manager.dock_containers():
            for i in range(dock_container.dock_area_count()):
                dock_area = dock_container.dock_area(i)
                dock_widget_name = dock_area.property("currentDockWidget")
                
                dock_widget = self._manager.find_dock_widget(dock_widget_name) if dock_widget_name else None

                if not dock_widget or dock_widget.is_closed():
                    index = dock_area.index_of_first_open_dock_widget()
                    if index >= 0:
                        dock_area.set_current_index(index)
                else:
                    dock_area.internal_set_current_dock_widget(dock_widget)

    def _emit_top_level_events(self) -> None:
        for dock_container in self._manager.dock_containers():
            top_level_dock_widget = dock_container.top_level_dock_widget()
            if top_level_dock_widget is not None:
                top_level_dock_widget.emit_top_level_changed(True)
            else:
                for i in range(dock_container.dock_area_count()):
                    dock_area = dock_container.dock_area(i)
                    for dock_widget in dock_area.dock_widgets():
                        dock_widget.emit_top_level_changed(False)

    def _hide_floating_widgets(self) -> None:
        for floating_widget in self._manager.floating_widgets():
            floating_widget.hide()


# ─────────────────────────────────────────────────────────────────────
#  Main API Facade
# ─────────────────────────────────────────────────────────────────────

class LayoutSerializer:
    """
    Facade coordinating state builders and layout engines.
    Exposes pure string <-> UI logic and enforces strict version checking.
    """
    
    SYSTEM_TYPE: str = LayoutStateBuilder.SYSTEM_TYPE

    def __init__(self, manager: 'DockManager'):
        self._manager = manager
        self._builder = LayoutStateBuilder(manager)
        self._engine = LayoutEngine(manager)

    def serialize(self, version: int = 0, formatted: bool = False) -> str:
        """Extracts the dock layout into a JSON string safely."""
        state_dict = self._builder.build_state_dict(version)
        indent = 2 if formatted else None
        return json.dumps(state_dict, indent=indent)

    def deserialize(self, state_json: str, target_version: int) -> None:
        """Parses JSON state, validates versions, and applies it to the UI."""
        try:
            state_dict = json.loads(state_json)
        except json.JSONDecodeError as e:
            raise InvalidFormatError(f"Invalid JSON data: {e}") from e

        if state_dict.get("type") != self.SYSTEM_TYPE:
            raise InvalidFormatError(f"Invalid system type. Expected {self.SYSTEM_TYPE}.")

        file_version = state_dict.get("version", 0)
        if file_version != target_version:
            raise InvalidFormatError(
                f"Layout version mismatch. File is v{file_version}, expected v{target_version}. "
                "Schema migrations are unsupported to guarantee state integrity."
            )

        self._engine.apply_state(state_dict)