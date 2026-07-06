# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0

dock_container_state — per-container layout (de)serialization
=============================================================

The recursive splitter/dock-area tree save & restore for a single
``DockContainerWidget``.  Extracted from the container itself to keep that
class focused on layout management; the functions take the container as their
first argument and are exposed on it via thin ``save_state`` / ``restore_state``
delegates.
"""

import logging
from typing import Optional, Tuple

from PySide6.QtCore import Qt, QByteArray
from PySide6.QtWidgets import QSplitter, QWidget

from .dock_area_widget import DockAreaWidget

logger = logging.getLogger(__name__)


def save_container_state(c) -> dict:
    """Phase 2: Modernized dict-based state saving."""
    logger.debug('DockContainerWidget.saveState isFloating %s', c.is_floating())
    state = {
        "type": "Container",
        "floating": c.is_floating(),
        "geometry": "",
        "root_splitter": _save_child_nodes_state(c, c._root_splitter),
    }
    if c.is_floating():
        floating_widget = c.floating_widget()
        geometry = floating_widget.saveGeometry()
        state["geometry"] = geometry.toHex(ord(' ')).data().decode()
    return state


def _save_child_nodes_state(c, widget: QWidget) -> dict:
    if isinstance(widget, QSplitter):
        splitter = widget
        orientation = "-" if splitter.orientation() == Qt.Horizontal else "|"
        return {
            "type": "Splitter",
            "orientation": orientation,
            "count": splitter.count(),
            "sizes": splitter.sizes(),
            "children": [_save_child_nodes_state(c, splitter.widget(i))
                         for i in range(splitter.count())],
        }
    elif isinstance(widget, DockAreaWidget):
        return widget.save_state()
    return {}


def restore_container_state(c, state: dict, testing: bool = False) -> bool:
    """Phase 2: Use dict for state deserialization instead of stream."""
    is_floating = state.get("floating", False)
    logger.debug('Restore DockContainerWidget Floating %s', is_floating)

    if not testing:
        c._visible_dock_area_count = -1
        c._dock_areas.clear()
        c._last_added_area_cache.clear()

    if is_floating:
        logger.debug('Restore floating widget')
        geometry_string = state.get("geometry", "")
        if not geometry_string:
            return False

        geometry = QByteArray.fromHex(geometry_string.encode())
        if geometry.isEmpty():
            return False

        if not testing:
            floating_widget = c.floating_widget()
            floating_widget.restoreGeometry(geometry)

    root_splitter_state = state.get("root_splitter", {})
    res, new_root_splitter = _restore_child_nodes(c, root_splitter_state, testing)
    if not res:
        return False

    if testing:
        return True

    if not new_root_splitter:
        new_root_splitter = c._new_splitter(Qt.Horizontal)

    c._layout.replaceWidget(c._root_splitter, new_root_splitter)
    old_root = c._root_splitter
    c._root_splitter = new_root_splitter
    old_root.deleteLater()
    return True


def _restore_child_nodes(c, state: dict, testing: bool) -> Tuple[bool, Optional[QWidget]]:
    node_type = state.get("type")
    if node_type == "Splitter":
        return _restore_splitter(c, state, testing)
    elif node_type == "Area":
        return _restore_dock_area(c, state, testing)
    return True, None


def _restore_splitter(c, state: dict, testing: bool) -> Tuple[bool, Optional[QWidget]]:
    orientation_str = state.get("orientation", "-")
    orientation = Qt.Horizontal if orientation_str == "-" else Qt.Vertical

    widget_count = state.get("count", 0)
    if not widget_count:
        return False, None

    logger.debug('Restore NodeSplitter Orientation: %s  WidgetCount: %s', orientation, widget_count)

    splitter = None if testing else c._new_splitter(orientation)
    visible = False
    sizes = state.get("sizes", [])

    for child_state in state.get("children", []):
        result, child_node = _restore_child_nodes(c, child_state, testing)
        if not result:
            return False, None

        if splitter is not None and child_node is not None:
            logger.debug('ChildNode isVisible %s isVisibleTo %s',
                         child_node.isVisible(), child_node.isVisibleTo(splitter))
            splitter.addWidget(child_node)
            visible |= child_node.isVisibleTo(splitter)

    if len(sizes) != widget_count:
        return False, None

    if testing:
        splitter = None
    else:
        if not splitter.count():
            splitter.deleteLater()
            splitter = None
        else:
            splitter.setSizes(sizes)
            splitter.setVisible(visible)

    return True, splitter


def _restore_dock_area(c, state: dict, testing: bool) -> Tuple[bool, Optional[QWidget]]:
    tabs = state.get("tabs", 0)
    current_dock_widget = state.get("current", "")
    logger.debug('Restore NodeDockArea Tabs: %s current: %s', tabs, current_dock_widget)

    dock_area = None
    if not testing:
        dock_area = DockAreaWidget(c._dock_manager, c)

    for widget_state in state.get("widgets", []):
        if widget_state.get("type") != "Widget":
            continue

        object_name = widget_state.get("name")
        if not object_name:
            return False, None

        closed = widget_state.get("closed", False)
        dock_widget = c._dock_manager.find_dock_widget(object_name)

        if dock_widget and dock_area:
            logger.debug('Dock Widget found - parent %s', dock_widget.parent())
            dock_area.hide()
            dock_area.add_dock_widget(dock_widget)
            dock_widget.set_toggle_view_action_checked(not closed)
            dock_widget.set_closed_state(closed)
            dock_widget.setProperty("closed", closed)
            dock_widget.setProperty("dirty", False)

    if testing:
        return True, None

    if not dock_area.dock_widgets_count():
        dock_area.deleteLater()
        dock_area = None
    else:
        dock_area.setProperty("currentDockWidget", current_dock_widget)
        c._append_dock_areas(dock_area)

    return True, dock_area
