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
from typing import TYPE_CHECKING, List, Dict, Tuple, Optional

from PySide6.QtCore import (QByteArray, QEvent, QPoint, Qt, Signal)
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QFrame, QGridLayout, QSplitter, QWidget

from .util import (find_parent, hide_empty_parent_splitters,
                   emit_top_level_event_for_widget, find_child, find_children)
from .enums import (DockWidgetArea, DockWidgetFeature, TitleBarButton,
                    DockFlags, DockInsertParam)
from .dock_splitter import DockSplitter
from .dock_area_widget import DockAreaWidget
from .dock_style_manager import get_dock_style_manager
from .dock_theme import DockStyleCategory

if TYPE_CHECKING:
    from . import DockManager, DockWidget, FloatingDockContainer

logger = logging.getLogger(__name__)

_z_order_counter = 0


def dock_area_insert_parameters(area: DockWidgetArea) -> DockInsertParam:
    if area == DockWidgetArea.top:
        return DockInsertParam(Qt.Vertical, False)
    if area == DockWidgetArea.right:
        return DockInsertParam(Qt.Horizontal, True)
    if area in (DockWidgetArea.center, DockWidgetArea.bottom):
        return DockInsertParam(Qt.Vertical, True)
    if area == DockWidgetArea.left:
        return DockInsertParam(Qt.Horizontal, False)
    return DockInsertParam(Qt.Vertical, False)


def insert_widget_into_splitter(splitter: QSplitter, widget: QWidget, append: bool):
    if append:
        return splitter.addWidget(widget)
    return splitter.insertWidget(0, widget)


def replace_splitter_widget(splitter: QSplitter, from_: QWidget, to: QWidget):
    index = splitter.indexOf(from_)
    from_.setParent(None)
    logger.debug('replace splitter widget %d %s -> %s', index, from_, to)
    splitter.insertWidget(index, to)


class DockContainerWidget(QFrame):
    dock_areas_added = Signal()
    dock_areas_removed = Signal()
    dock_area_view_toggled = Signal(DockAreaWidget, bool)

    def __init__(self, dock_manager: 'DockManager', parent: QWidget):
        super().__init__(parent)
        
        # Flattened private properties
        self._dock_manager = dock_manager
        self._z_order_index = 0
        self._dock_areas: List[DockAreaWidget] = []
        self._layout = QGridLayout()
        self._root_splitter: DockSplitter = None
        self._is_floating = self.floating_widget() is not None
        self._last_added_area_cache: Dict[DockWidgetArea, DockAreaWidget] = {}
        self._visible_dock_area_count = -1
        self._top_level_dock_area: DockAreaWidget = None

        # --- ADDED: Style Manager Integration ---
        self._style_mgr = get_dock_style_manager()
        self._style_mgr.register(self, DockStyleCategory.CORE)
        self.refresh_style()

        self._layout.setContentsMargins(0, 1, 0, 1)
        self._layout.setSpacing(0)
        self.setLayout(self._layout)

        # Enable palette-driven background so CORE.canvas_bg paints
        # behind splitters and dock-area gaps when the theme changes.
        self.setAutoFillBackground(True)
        self.setBackgroundRole(QPalette.ColorRole.Window)

        if dock_manager is not self:
            self._dock_manager.register_dock_container(self)
            self.create_root_splitter()

    def __repr__(self):
        return f'<{self.__class__.__name__} is_floating={self._is_floating}>'

    def deleteLater(self):
        if self._dock_manager:
            self._dock_manager.remove_dock_container(self)
        super().deleteLater()

    def event(self, e: QEvent) -> bool:
        result = super().event(e)
        global _z_order_counter
        if e.type() == QEvent.WindowActivate:
            _z_order_counter += 1
            self._z_order_index = _z_order_counter
        elif e.type() == QEvent.Show and not self._z_order_index:
            _z_order_counter += 1
            self._z_order_index = _z_order_counter
        return result

    def root_splitter(self) -> QSplitter:
        return self._root_splitter

    def create_root_splitter(self):
        """
        Create and position the root splitter in the center of the grid layout.
        
        This method ensures the main dock area (root splitter) is centered within 
        the widget's QGridLayout, allowing sidebars to form a perimeter around it. 
        The central cell (row 1, column 1) will absorb extra space as needed.
        
        The root splitter is placed at grid position (1, 1), and stretch factors
        are set for row 1 and column 1 to ensure proper expansion behavior.
        
        This method should be called only once during initialization.
        """
        if self._root_splitter:
            return
            
        self._root_splitter = self._new_splitter(Qt.Horizontal)
        
        # Place the root splitter in the center (Row 1, Column 1) of the grid
        self._layout.addWidget(self._root_splitter, 1, 1)
        
        # Ensure the center area absorbs all extra stretch space
        self._layout.setRowStretch(1, 1)
        self._layout.setColumnStretch(1, 1)

    def _dock_widget_into_container(self, area: DockWidgetArea, dockwidget: 'DockWidget') -> DockAreaWidget:
        new_dock_area = DockAreaWidget(self._dock_manager, self)
        new_dock_area.add_dock_widget(dockwidget)
        self._add_dock_area(new_dock_area, area)
        new_dock_area.update_title_bar_visibility()
        self._last_added_area_cache[area] = new_dock_area
        return new_dock_area

    def _dock_widget_into_dock_area(self, area: DockWidgetArea, dock_widget: 'DockWidget',
                                    target_dock_area: DockAreaWidget) -> DockAreaWidget:
        if area == DockWidgetArea.center:
            target_dock_area.add_dock_widget(dock_widget)
            return target_dock_area

        new_dock_area = DockAreaWidget(self._dock_manager, self)
        new_dock_area.add_dock_widget(dock_widget)

        insert_param = dock_area_insert_parameters(area)
        target_area_splitter = find_parent(QSplitter, target_dock_area)
        index = target_area_splitter.indexOf(target_dock_area)
        if target_area_splitter.orientation() == insert_param.orientation:
            logger.debug('TargetAreaSplitter.orientation() == insert_orientation')
            target_area_splitter.insertWidget(index + insert_param.insert_offset, new_dock_area)
        else:
            logger.debug('TargetAreaSplitter.orientation() != insert_orientation')
            new_splitter = self._new_splitter(insert_param.orientation)
            new_splitter.addWidget(target_dock_area)
            insert_widget_into_splitter(new_splitter, new_dock_area, insert_param.append)
            target_area_splitter.insertWidget(index, new_splitter)

        self._append_dock_areas(new_dock_area)
        self._emit_dock_areas_added()
        return new_dock_area

    def _add_dock_area(self, new_dock_area: DockAreaWidget, area: DockWidgetArea):
        insert_param = dock_area_insert_parameters(area)

        if len(self._dock_areas) <= 1:
            self._root_splitter.setOrientation(insert_param.orientation)

        splitter = self._root_splitter
        if splitter.orientation() == insert_param.orientation:
            insert_widget_into_splitter(splitter, new_dock_area, insert_param.append)
        else:
            new_splitter = self._new_splitter(insert_param.orientation)
            if insert_param.append:
                self._layout.replaceWidget(splitter, new_splitter)
                new_splitter.addWidget(splitter)
                new_splitter.addWidget(new_dock_area)
            else:
                new_splitter.addWidget(new_dock_area)
                self._layout.replaceWidget(splitter, new_splitter)
                new_splitter.addWidget(splitter)

            self._root_splitter = new_splitter

        self._append_dock_areas(new_dock_area)
        new_dock_area.update_title_bar_visibility()
        
        #--- FIX START ---
        #Ensure the root splitter is visible now that it has content
        if not self._root_splitter.isVisible():
            self._root_splitter.show()
        #--- FIX END ---
        
        self._emit_dock_areas_added()
        new_dock_area.destroyed.connect(self.remove_dock_area)

    def drop_floating_widget(self, floating_widget: 'FloatingDockContainer', target_pos: QPoint):
        logger.debug('DockContainerWidget.dropFloatingWidget')
        dock_area = self.dock_area_at(target_pos)
        drop_area = DockWidgetArea.invalid
        container_drop_area = self._dock_manager.container_overlay().drop_area_under_cursor()
        floating_top_level_dock_widget = floating_widget.top_level_dock_widget()
        top_level_dock_widget = self.top_level_dock_widget()

        if dock_area is not None:
            drop_overlay = self._dock_manager.dock_area_overlay()
            drop_overlay.set_allowed_areas(DockWidgetArea.all_dock_areas)
            drop_area = drop_overlay.show_overlay(dock_area)
            if (container_drop_area not in (DockWidgetArea.invalid, drop_area)):
                drop_area = DockWidgetArea.invalid

            if drop_area != DockWidgetArea.invalid:
                logger.debug('Dock Area Drop Content: %s', drop_area)
                self._drop_into_section(floating_widget, dock_area, drop_area)

        if DockWidgetArea.invalid == drop_area:
            drop_area = container_drop_area
            logger.debug('Container Drop Content: %s', drop_area)
            if drop_area != DockWidgetArea.invalid:
                self._drop_into_container(floating_widget, drop_area)

        if top_level_dock_widget is not None:
            top_level_dock_widget.emit_top_level_changed(False)

        if floating_top_level_dock_widget is not None:
            floating_top_level_dock_widget.emit_top_level_changed(False)

        # Removed the conflicting OS FOCUS TRANSFER LOGIC here.
        # The floating window's 100ms deferred _claim_focus_safely() now handles it natively.

    def _drop_into_container(self, floating_widget: 'FloatingDockContainer', area: DockWidgetArea):
        insert_param = dock_area_insert_parameters(area)
        floating_dock_container = floating_widget.dock_container()

        new_dock_areas = find_children(
            floating_dock_container, DockAreaWidget, '', Qt.FindChildrenRecursively)

        single_dropped_dock_widget = floating_dock_container.top_level_dock_widget()
        single_dock_widget = self.top_level_dock_widget()
        splitter = self._root_splitter
        
        if len(self._dock_areas) <= 1:
            splitter.setOrientation(insert_param.orientation)
        elif splitter.orientation() != insert_param.orientation:
            new_splitter = self._new_splitter(insert_param.orientation)
            self._layout.replaceWidget(splitter, new_splitter)
            new_splitter.addWidget(splitter)
            splitter = new_splitter

        floating_splitter = floating_dock_container.root_splitter()
        if floating_splitter.count() == 1:
            insert_widget_into_splitter(splitter, floating_splitter.widget(0), insert_param.append)
        elif floating_splitter.orientation() == insert_param.orientation:
            while floating_splitter.count():
                insert_widget_into_splitter(splitter, floating_splitter.widget(0), insert_param.append)
        else:
            insert_widget_into_splitter(splitter, floating_splitter, insert_param.append)

        self._root_splitter = splitter
        self._add_dock_areas_to_list(new_dock_areas)
        floating_widget.deleteLater()

        emit_top_level_event_for_widget(single_dropped_dock_widget, False)
        emit_top_level_event_for_widget(single_dock_widget, False)

        if not splitter.isVisible():
            splitter.show()

        self.dump_layout()

    def _drop_into_section(self, floating_widget: 'FloatingDockContainer',
                           target_area: DockAreaWidget, area: DockWidgetArea):
        if area == DockWidgetArea.center:
            self._drop_into_center_of_section(floating_widget, target_area)
            return

        insert_param = dock_area_insert_parameters(area)

        new_dock_areas = find_children(
            floating_widget.dock_container(), DockAreaWidget, '', Qt.FindChildrenRecursively)

        target_area_splitter = find_parent(QSplitter, target_area)

        if not target_area_splitter:
            splitter = self._new_splitter(insert_param.orientation)
            self._layout.replaceWidget(target_area, splitter)
            splitter.addWidget(target_area)
            target_area_splitter = splitter

        area_index = target_area_splitter.indexOf(target_area)

        floating_splitter = find_child(
            floating_widget.dock_container(), QWidget, '', Qt.FindDirectChildrenOnly)

        if target_area_splitter.orientation() == insert_param.orientation:
            sizes = target_area_splitter.sizes()
            target_area_size = (target_area.width()
                                if insert_param.orientation == Qt.Horizontal
                                else target_area.height())
            adjust_splitter_sizes = True
            if (floating_splitter.orientation() != insert_param.orientation
                    and floating_splitter.count() > 1):
                target_area_splitter.insertWidget(
                    area_index + insert_param.insert_offset,
                    floating_splitter)
            else:
                adjust_splitter_sizes = (floating_splitter.count() == 1)
                insert_index = area_index + insert_param.insert_offset
                while floating_splitter.count():
                    insert_index += 1
                    target_area_splitter.insertWidget(insert_index,
                                                      floating_splitter.widget(0))

            if adjust_splitter_sizes:
                size = (target_area_size - target_area_splitter.handleWidth()) / 2
                sizes[area_index] = size
                sizes.insert(area_index, size)
                target_area_splitter.setSizes(sizes)

        else:
            new_splitter = self._new_splitter(insert_param.orientation)
            target_area_size = (target_area.width()
                                if insert_param.orientation == Qt.Horizontal
                                else target_area.height())
            adjust_splitter_sizes = True
            if (floating_splitter.orientation() != insert_param.orientation) and floating_splitter.count() > 1:
                new_splitter.addWidget(floating_splitter)
            else:
                adjust_splitter_sizes = (floating_splitter.count() == 1)
                while floating_splitter.count():
                    new_splitter.addWidget(floating_splitter.widget(0))

            sizes = target_area_splitter.sizes()
            insert_widget_into_splitter(new_splitter, target_area, not insert_param.append)
            if adjust_splitter_sizes:
                size = target_area_size / 2
                new_splitter.setSizes((size, size))

            target_area_splitter.insertWidget(area_index, new_splitter)
            target_area_splitter.setSizes(sizes)

        logger.debug('Deleting floating_widget %s', floating_widget)
        floating_widget.deleteLater()
        self._add_dock_areas_to_list(new_dock_areas)
        self.dump_layout()

    def _drop_into_center_of_section(self, floating_widget: 'FloatingDockContainer',
                                     target_area: DockAreaWidget):
        floating_container = floating_widget.dock_container()
        new_dock_widgets = floating_container.dock_widgets()
        top_level_dock_area = floating_container.top_level_dock_area()
        new_current_index = -1

        if top_level_dock_area is not None:
            new_current_index = top_level_dock_area.current_index()

        for i, dock_widget in enumerate(new_dock_widgets):
            target_area.insert_dock_widget(i, dock_widget, False)

            if new_current_index < 0 and not dock_widget.is_closed():
                new_current_index = i

        target_area.set_current_index(new_current_index)
        floating_widget.deleteLater()
        target_area.update_title_bar_visibility()

    def add_dock_area(self, dock_area_widget: DockAreaWidget,
                      area: DockWidgetArea = DockWidgetArea.center):
        container = dock_area_widget.dock_container()
        if container and container is not self:
            container.remove_dock_area(dock_area_widget)
        self._add_dock_area(dock_area_widget, area)

    def _add_dock_areas_to_list(self, new_dock_areas: list):
        count_before = len(self._dock_areas)
        new_area_count = len(new_dock_areas)
        self._append_dock_areas(*new_dock_areas)

        for dock_area in new_dock_areas:
            undock = dock_area.title_bar_button(TitleBarButton.undock)
            undock.setVisible(True)
            close = dock_area.title_bar_button(TitleBarButton.close)
            close.setVisible(True)

        if count_before == 1:
            self._dock_areas[0].update_title_bar_visibility()
        if new_area_count == 1:
            self._dock_areas[-1].update_title_bar_visibility()

        self._emit_dock_areas_added()

    def _append_dock_areas(self, *new_dock_areas):
        self._dock_areas.extend(new_dock_areas)
        for dock_area in new_dock_areas:
            dock_area.view_toggled.connect(self._on_dock_area_view_toggled)

    def remove_dock_area(self, area: DockAreaWidget):
        def emit_and_exit():
            top_level_widget = self.top_level_dock_widget()
            emit_top_level_event_for_widget(top_level_widget, True)
            self.dump_layout()
            self._emit_dock_areas_removed()
    
        logger.debug('DockContainerWidget.removeDockArea')
        
        # Guard: destroyed signal may pass partially-destroyed QWidget
        if not isinstance(area, DockAreaWidget):
            logger.debug('remove_dock_area called with non-DockAreaWidget: %s (likely from destroyed signal)', type(area).__name__)
            return
            
        if area not in self._dock_areas:
            # This can happen legitimately if area was already removed explicitly
            # and then destroyed signal fires later
            logger.debug('Area %s not found in DockContainerWidget %s (already removed?)', area, self)
            return
    
        # Disconnect destroyed signal to prevent double-removal
        try:
            area.destroyed.disconnect(self.remove_dock_area)
        except RuntimeError:
            pass  # Already disconnected
    
        area.view_toggled.disconnect(self._on_dock_area_view_toggled)
        self._dock_areas.remove(area)
        splitter = find_parent(DockSplitter, area)

        logger.debug('area setParent %s None', area)
        area.setParent(None)
        hide_empty_parent_splitters(splitter)

        for _area, _widget in self._last_added_area_cache.items():
            if _widget is splitter:
                self._last_added_area_cache[_area] = None

        if splitter.count() > 1:
            return emit_and_exit()

        if splitter is self._root_splitter:
            logger.debug('Removed from RootSplitter')

            if not splitter.count():
                splitter.hide()
                return emit_and_exit()

            child_splitter = splitter.widget(0)

            if not isinstance(child_splitter, QSplitter):
                return emit_and_exit()

            logger.debug('child_splitter setParent %s None', child_splitter)
            child_splitter.setParent(None)
            self._layout.replaceWidget(splitter, child_splitter)
            self._root_splitter = child_splitter

            logger.debug('RootSplitter replaced by child splitter')

        elif splitter.count() == 1:
            logger.debug('Replacing splitter with content')
            parent_splitter = find_parent(QSplitter, splitter)
            sizes = parent_splitter.sizes()
            widget = splitter.widget(0)
            logger.debug('widget setParent to dock container %s %s', widget, self)
            widget.setParent(self)
            replace_splitter_widget(parent_splitter, splitter, widget)
            parent_splitter.setSizes(sizes)

        splitter.deleteLater()
        splitter = None

        return emit_and_exit()

    def save_state(self) -> dict:
        """Phase 2: Modernized dict-based state saving."""
        logger.debug('DockContainerWidget.saveState isFloating %s', self.is_floating())
        state = {
            "type": "Container",
            "floating": self.is_floating(),
            "geometry": "",
            "root_splitter": self._save_child_nodes_state(self._root_splitter)
        }
        if self.is_floating():
            floating_widget = self.floating_widget()
            geometry = floating_widget.saveGeometry()
            state["geometry"] = geometry.toHex(ord(' ')).data().decode()
        return state

    def _save_child_nodes_state(self, widget: QWidget) -> dict:
        if isinstance(widget, QSplitter):
            splitter = widget
            orientation = "-" if splitter.orientation() == Qt.Horizontal else "|"
            return {
                "type": "Splitter",
                "orientation": orientation,
                "count": splitter.count(),
                "sizes": splitter.sizes(),
                "children": [self._save_child_nodes_state(splitter.widget(i)) for i in range(splitter.count())]
            }
        elif isinstance(widget, DockAreaWidget):
            return widget.save_state()
        return {}

    def restore_state(self, state: dict, testing: bool = False) -> bool:
        """Phase 2: Use dict for state deserialization instead of stream."""
        is_floating = state.get("floating", False)
        logger.debug('Restore DockContainerWidget Floating %s', is_floating)

        if not testing:
            self._visible_dock_area_count = -1
            self._dock_areas.clear()
            self._last_added_area_cache.clear()

        if is_floating:
            logger.debug('Restore floating widget')
            geometry_string = state.get("geometry", "")
            if not geometry_string:
                return False

            geometry = QByteArray.fromHex(geometry_string.encode())
            if geometry.isEmpty():
                return False

            if not testing:
                floating_widget = self.floating_widget()
                floating_widget.restoreGeometry(geometry)

        root_splitter_state = state.get("root_splitter", {})
        res, new_root_splitter = self._restore_child_nodes(root_splitter_state, testing)
        if not res:
            return False

        if testing:
            return True

        if not new_root_splitter:
            new_root_splitter = self._new_splitter(Qt.Horizontal)

        self._layout.replaceWidget(self._root_splitter, new_root_splitter)
        old_root = self._root_splitter
        self._root_splitter = new_root_splitter
        old_root.deleteLater()
        return True

    def _restore_child_nodes(self, state: dict, testing: bool) -> Tuple[bool, Optional[QWidget]]:
        node_type = state.get("type")
        if node_type == "Splitter":
            return self._restore_splitter(state, testing)
        elif node_type == "Area":
            return self._restore_dock_area(state, testing)
        return True, None

    def _restore_splitter(self, state: dict, testing: bool) -> Tuple[bool, Optional[QWidget]]:
        orientation_str = state.get("orientation", "-")
        orientation = Qt.Horizontal if orientation_str == "-" else Qt.Vertical
        
        widget_count = state.get("count", 0)
        if not widget_count:
            return False, None

        logger.debug('Restore NodeSplitter Orientation: %s  WidgetCount: %s', orientation, widget_count)

        splitter = None if testing else self._new_splitter(orientation)
        visible = False
        sizes = state.get("sizes", [])

        for child_state in state.get("children", []):
            result, child_node = self._restore_child_nodes(child_state, testing)
            if not result:
                return False, None
            
            if splitter is not None and child_node is not None:
                logger.debug('ChildNode isVisible %s isVisibleTo %s', child_node.isVisible(), child_node.isVisibleTo(splitter))
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

    def _restore_dock_area(self, state: dict, testing: bool) -> Tuple[bool, Optional[QWidget]]:
        tabs = state.get("tabs", 0)
        current_dock_widget = state.get("current", "")
        logger.debug('Restore NodeDockArea Tabs: %s current: %s', tabs, current_dock_widget)
        
        dock_area = None
        if not testing:
            dock_area = DockAreaWidget(self._dock_manager, self)

        for widget_state in state.get("widgets", []):
            if widget_state.get("type") != "Widget":
                continue
            
            object_name = widget_state.get("name")
            if not object_name:
                return False, None
            
            closed = widget_state.get("closed", False)
            dock_widget = self._dock_manager.find_dock_widget(object_name)
            
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
            self._append_dock_areas(dock_area)

        return True, dock_area

    def last_added_dock_area_widget(self, area: DockWidgetArea) -> DockAreaWidget:
        return self._last_added_area_cache.get(area, None)

    def has_top_level_dock_widget(self) -> bool:
        if not self.is_floating():
            return False
        dock_areas = self.opened_dock_areas()
        if len(dock_areas) != 1:
            return False
        return dock_areas[0].open_dock_widgets_count() == 1

    def top_level_dock_widget(self) -> 'DockWidget':
        top_level_dock_area = self.top_level_dock_area()
        if not top_level_dock_area:
            return None
        dock_widgets = top_level_dock_area.opened_dock_widgets()
        if len(dock_widgets) != 1:
            return None
        return dock_widgets[0]

    def top_level_dock_area(self) -> DockAreaWidget:
        if not self.is_floating():
            return None
        dock_areas = self.opened_dock_areas()
        if len(dock_areas) != 1:
            return None
        return dock_areas[0]

    def dock_widgets(self) -> list:
        return [widget
                for dock_area in self._dock_areas
                for widget in dock_area.dock_widgets()]

    def add_dock_widget(self, area: DockWidgetArea, dockwidget: 'DockWidget',
                        dock_area_widget: DockAreaWidget = None) -> DockAreaWidget:
        old_dock_area = dockwidget.dock_area_widget()
        if old_dock_area is not None:
            old_dock_area.remove_dock_widget(dockwidget)

        dockwidget.set_dock_manager(self._dock_manager)
        if dock_area_widget is not None:
            return self._dock_widget_into_dock_area(area, dockwidget, dock_area_widget)
        return self._dock_widget_into_container(area, dockwidget)

    def remove_dock_widget(self, widget: 'DockWidget'):
        area = widget.dock_area_widget()
        if area is not None:
            area.remove_dock_widget(widget)

    def z_order_index(self) -> int:
        return self._z_order_index

    def is_in_front_of(self, other: 'DockContainerWidget') -> bool:
        return self.z_order_index() > other.z_order_index()

    def dock_area_at(self, global_pos: QPoint) -> DockAreaWidget:
        for dock_area in self._dock_areas:
            pos = dock_area.mapFromGlobal(global_pos)
            if dock_area.isVisible() and dock_area.rect().contains(pos):
                return dock_area
        return None

    def dock_area(self, index: int) -> DockAreaWidget:
        try:
            return self._dock_areas[index]
        except IndexError:
            return None

    def opened_dock_areas(self) -> list:
        return [dock_area for dock_area in self._dock_areas if not dock_area.isHidden()]

    def dock_area_count(self) -> int:
        return len(self._dock_areas)

    def visible_dock_area_count(self) -> int:
        if self._visible_dock_area_count > -1:
            return self._visible_dock_area_count

        self._visible_dock_area_count = sum(1 for dock_area in self._dock_areas if not dock_area.isHidden())
        return self._visible_dock_area_count

    def _on_visible_dock_area_count_changed(self):
        top_level_dock_area = self.top_level_dock_area()

        if top_level_dock_area is not None:
            self._top_level_dock_area = top_level_dock_area
            is_solo_floating = self.is_floating()

            # Undock button: hide when already solo-floating (can't undock further).
            top_level_dock_area.title_bar_button(
                TitleBarButton.undock).setVisible(not is_solo_floating)

            # Close button: respect the active widget's closable feature
            # instead of blanket-hiding it for all solo-floating areas.
            if is_solo_floating:
                widget = top_level_dock_area.current_dock_widget()
                can_close = bool(
                    widget and DockWidgetFeature.closable in widget.features()
                ) if widget else top_level_dock_area.closable
                top_level_dock_area.title_bar_button(
                    TitleBarButton.close).setVisible(can_close)
            else:
                top_level_dock_area.title_bar_button(
                    TitleBarButton.close).setVisible(True)

        elif self._top_level_dock_area:
            self._top_level_dock_area.title_bar_button(
                TitleBarButton.undock).setVisible(True)
            self._top_level_dock_area.title_bar_button(
                TitleBarButton.close).setVisible(True)
            self._top_level_dock_area = None

    def _emit_dock_areas_removed(self):
            self._visible_dock_area_count = -1  # Force cache invalidation
            self._on_visible_dock_area_count_changed()
            self.dock_areas_removed.emit()

    def _emit_dock_areas_added(self):
        self._visible_dock_area_count = -1  # Force cache invalidation
        self._on_visible_dock_area_count_changed()
        self.dock_areas_added.emit()

    def _new_splitter(self, orientation: Qt.Orientation, parent: QWidget = None) -> DockSplitter:
        splitter = DockSplitter(orientation, parent)
        opaque_resize = DockFlags.opaque_splitter_resize in self._dock_manager.config_flags
        splitter.setOpaqueResize(opaque_resize)
        splitter.setChildrenCollapsible(False)
        return splitter

    def _on_dock_area_view_toggled(self, visible: bool):
        try:
            dock_area = self.sender()
        except RuntimeError:
            logger.exception('dock area view toggled error')
            return

        # Invalidate the cache instead of incrementally updating it.
        # This prevents double-counting since toggle_view() triggers 
        # setVisible() before this signal is even emitted.
        self._visible_dock_area_count = -1

        self._on_visible_dock_area_count_changed()
        self.dock_area_view_toggled.emit(dock_area, visible)

    def is_floating(self) -> bool:
        return self._is_floating

    def _dump_recursive(self, level: int, widget: QWidget):
        indent = ' ' * level * 4
        if isinstance(widget, QSplitter):
            splitter = widget
            logger.debug(
                "%sSplitter %s v: %s c: %s",
                indent,
                ('|' if splitter.orientation() == Qt.Vertical else '--'),
                (' ' if splitter.isHidden() else 'v'),
                splitter.count()
            )

            for i in range(splitter.count()):
                self._dump_recursive(level + 1, splitter.widget(i))
        elif isinstance(widget, DockAreaWidget):
            dock_area = widget
            logger.debug('%sDockArea', indent)
            logger.debug('%s%s %s DockArea', indent,
                         ' ' if dock_area.isHidden() else 'v',
                         ' ' if dock_area.open_dock_widgets_count() > 0 else 'c')

            indent = ' ' * (level + 1) * 4
            for i, dock_widget in enumerate(dock_area.dock_widgets()):
                logger.debug('%s%s%s%s %s', indent,
                             '*' if i == dock_area.current_index() else ' ',
                             ' ' if i == dock_widget.isHidden() else 'v',
                             'c' if i == dock_widget.is_closed() else ' ',
                             dock_widget.windowTitle())

    def dump_layout(self):
        if not logger.isEnabledFor(logging.DEBUG):
            return
        logger.debug("--------------------------")
        self._dump_recursive(0, self._root_splitter)
        logger.debug("--------------------------\n\n")

    def features(self) -> DockWidgetFeature:
        features = DockWidgetFeature.all_features
        for dock_area in self._dock_areas:
            features &= dock_area.features()
        return features

    def floating_widget(self) -> 'FloatingDockContainer':
        from .floating_dock_container import FloatingDockContainer
        return find_parent(FloatingDockContainer, self)

    def close_other_areas(self, keep_open_area: DockAreaWidget):
        for dock_area in self._dock_areas:
            if dock_area != keep_open_area and DockWidgetFeature.closable in dock_area.features():
                dock_area.close_area()

    def refresh_style(self):
        """Fetches the latest core styles and applies them to the layout."""
        styles = self._style_mgr.get_all(DockStyleCategory.CORE)
        
        # Apply theme-driven margins and spacing instead of hardcoded (0, 1, 0, 1)
        margin = styles.get("margin", 0)
        padding = styles.get("padding", 0)
        
        self._layout.setContentsMargins(margin, margin, margin, margin)
        self._layout.setSpacing(padding)
        
        # Optional: You can also set a background color here if floating containers 
        # need a specific background behind the splitters.

    def on_style_changed(self, category: DockStyleCategory, changes: dict):
        """Callback triggered by DockStyleManager when the theme switches."""
        self.refresh_style()
