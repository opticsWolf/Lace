# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2019 Ken Lauer
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace, adapted from qtpydocking.
# Original code Copyright (c) 2019 Ken Lauer (BSD-3-Clause).
# Modifications Copyright (c) 2026 opticsWolf (Apache-2.0).


import logging
from typing import TYPE_CHECKING, List, Dict, Optional

from PySide6.QtCore import (QEvent, QPoint, Qt, Signal)
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QFrame, QGridLayout, QSplitter, QWidget

from lace.util import (find_parent, hide_empty_parent_splitters,
                   emit_top_level_event_for_widget, find_child, find_children,
                   is_window_maximized, toggle_window_maximized,
                   dump_layout as _dump_layout)
from lace.enums import (DockWidgetArea, DockWidgetFeature, TitleBarButton,
                    DockFlags, DockInsertParam)
from lace.dock_splitter import DockSplitter
from lace.dock_area_widget import DockAreaWidget
from lace.dock_styled import DockStyled
from lace.dock_theme import DockStyleCategory
from lace._trace import trace

if TYPE_CHECKING:
    from lace import DockManager, DockWidget, FloatingDockContainer

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


class DropController:
    """Manages resolving and executing drag-and-drop operations for a DockContainerWidget."""
    def __init__(self, container: 'DockContainerWidget'):
        self._c = container

    def drop_floating_widget(self, floating_widget: 'FloatingDockContainer', target_pos: QPoint):
        logger.debug('DockContainerWidget.dropFloatingWidget')
        dock_area = self._c.dock_area_at(target_pos)
        drop_area = DockWidgetArea.invalid
        container_drop_area = self._c._dock_manager.container_overlay().drop_area_under_cursor()
        floating_top_level_dock_widget = floating_widget.top_level_dock_widget()
        top_level_dock_widget = self._c.top_level_dock_widget()

        if dock_area is not None:
            drop_overlay = self._c._dock_manager.dock_area_overlay()
            drop_overlay.set_allowed_areas(DockWidgetArea.all_dock_areas)
            drop_area = drop_overlay.show_overlay(dock_area)
            if (container_drop_area not in (DockWidgetArea.invalid, drop_area)):
                drop_area = DockWidgetArea.invalid

            if drop_area != DockWidgetArea.invalid:
                logger.debug('Dock Area Drop Content: %s', drop_area)
                trace("drop.resolve", target_area=dock_area.objectName() or dock_area.__class__.__name__, floating=floating_widget.objectName() or "floating", into=getattr(drop_area, 'name', str(drop_area)))
                self._drop_into_section(floating_widget, dock_area, drop_area)

        if DockWidgetArea.invalid == drop_area:
            drop_area = container_drop_area
            logger.debug('Container Drop Content: %s', drop_area)
            if drop_area != DockWidgetArea.invalid:
                trace("drop.resolve", target_area="container", floating=floating_widget.objectName() or "floating", into=getattr(drop_area, 'name', str(drop_area)))
                self._drop_into_container(floating_widget, drop_area)

        if top_level_dock_widget is not None:
            top_level_dock_widget.emit_top_level_changed(False)

        if floating_top_level_dock_widget is not None:
            floating_top_level_dock_widget.emit_top_level_changed(False)

    def _drop_into_container(self, floating_widget: 'FloatingDockContainer', area: DockWidgetArea):
        insert_param = dock_area_insert_parameters(area)
        floating_dock_container = floating_widget.dock_container()

        new_dock_areas = find_children(
            floating_dock_container, DockAreaWidget, '', Qt.FindChildrenRecursively)

        single_dropped_dock_widget = floating_dock_container.top_level_dock_widget()
        single_dock_widget = self._c.top_level_dock_widget()
        splitter = self._c._root_splitter
        trace("drop.insert", splitter=splitter.objectName() or "root_splitter", index="container")
        
        if len(self._c._dock_areas) <= 1:
            splitter.setOrientation(insert_param.orientation)
        elif splitter.orientation() != insert_param.orientation:
            new_splitter = self._c._new_splitter(insert_param.orientation)
            self._c._layout.replaceWidget(splitter, new_splitter)
            new_splitter.addWidget(splitter)
            splitter = new_splitter

        floating_splitter = floating_dock_container.root_splitter()
        if floating_splitter.count() == 1:
            insert_widget_into_splitter(splitter, floating_splitter.widget(0), insert_param.append)
        elif floating_splitter.orientation() == insert_param.orientation:
            # Extract children one-by-one, preserving their order.
            # When prepending, insert at incrementing indices so earlier
            # children stay before later ones (insertWidget(0) in a loop
            # would reverse the order).
            insert_idx = 0
            while floating_splitter.count():
                if insert_param.append:
                    splitter.addWidget(floating_splitter.widget(0))
                else:
                    splitter.insertWidget(insert_idx, floating_splitter.widget(0))
                    insert_idx += 1
        else:
            insert_widget_into_splitter(splitter, floating_splitter, insert_param.append)

        self._c._root_splitter = splitter
        self._c._add_dock_areas_to_list(new_dock_areas)
        floating_widget.deleteLater()

        emit_top_level_event_for_widget(single_dropped_dock_widget, False)
        emit_top_level_event_for_widget(single_dock_widget, False)

        if not splitter.isVisible():
            splitter.show()

        self._c.dump_layout()

    def _resolve_section_insertion(self, target_area: DockAreaWidget, insert_param: DockInsertParam) -> tuple[QSplitter, int]:
        target_area_splitter = find_parent(QSplitter, target_area)

        if not target_area_splitter:
            splitter = self._c._new_splitter(insert_param.orientation)
            self._c._layout.replaceWidget(target_area, splitter)
            splitter.addWidget(target_area)
            target_area_splitter = splitter

        area_index = target_area_splitter.indexOf(target_area)
        return target_area_splitter, area_index

    def _insert_into_section_splitter(self, target_area_splitter: QSplitter, area_index: int,
                                      target_area: DockAreaWidget, floating_splitter: QWidget, insert_param: DockInsertParam):
        if target_area_splitter.orientation() == insert_param.orientation:
            sizes = target_area_splitter.sizes()
            target_area_size = (target_area.width()
                                if insert_param.orientation == Qt.Horizontal
                                else target_area.height())
            child_count = floating_splitter.count()
            if (floating_splitter.orientation() != insert_param.orientation
                    and child_count > 1):
                # Insert the whole floating splitter as one widget.
                target_area_splitter.insertWidget(
                    area_index + insert_param.insert_offset,
                    floating_splitter)
                child_count = 1  # counts as a single inserted widget
            else:
                # Extract children one-by-one, preserving order.
                insert_index = area_index + insert_param.insert_offset
                while floating_splitter.count():
                    target_area_splitter.insertWidget(insert_index,
                                                      floating_splitter.widget(0))
                    insert_index += 1

            # Split target_area's size among itself + inserted children.
            total = child_count + 1
            share = (target_area_size - target_area_splitter.handleWidth() * (total - 1)) / total
            for _ in range(child_count):
                sizes.insert(area_index, share)
            sizes[area_index + child_count] = share
            target_area_splitter.setSizes(sizes)

        else:
            new_splitter = self._c._new_splitter(insert_param.orientation)
            target_area_size = (target_area.width()
                                if insert_param.orientation == Qt.Horizontal
                                else target_area.height())
            child_count = floating_splitter.count()
            if (floating_splitter.orientation() != insert_param.orientation) and child_count > 1:
                new_splitter.addWidget(floating_splitter)
            else:
                while floating_splitter.count():
                    new_splitter.addWidget(floating_splitter.widget(0))

            sizes = target_area_splitter.sizes()
            insert_widget_into_splitter(new_splitter, target_area, not insert_param.append)
            # Equal split: target_area vs. new_splitter content.
            size = target_area_size / 2
            new_splitter.setSizes((size, size))

            target_area_splitter.insertWidget(area_index, new_splitter)
            target_area_splitter.setSizes(sizes)

    def _drop_into_section(self, floating_widget: 'FloatingDockContainer',
                           target_area: DockAreaWidget, area: DockWidgetArea):
        if area == DockWidgetArea.center:
            self._drop_into_center_of_section(floating_widget, target_area)
            return

        insert_param = dock_area_insert_parameters(area)

        new_dock_areas = find_children(
            floating_widget.dock_container(), DockAreaWidget, '', Qt.FindChildrenRecursively)

        target_area_splitter, area_index = self._resolve_section_insertion(target_area, insert_param)
        trace("drop.insert", splitter=target_area_splitter.objectName() or "section_splitter", index=area_index)

        floating_splitter = find_child(
            floating_widget.dock_container(), QWidget, '', Qt.FindDirectChildrenOnly)

        self._insert_into_section_splitter(target_area_splitter, area_index, target_area, floating_splitter, insert_param)

        logger.debug('Deleting floating_widget %s', floating_widget)
        floating_widget.deleteLater()
        self._c._add_dock_areas_to_list(new_dock_areas)
        self._c.dump_layout()

    def _drop_into_center_of_section(self, floating_widget: 'FloatingDockContainer',
                                     target_area: DockAreaWidget):
        trace("drop.insert", splitter=target_area.objectName() or "center_area", index="center")
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
        target_area.ensure_title_bar_visible()


class DockContainerWidget(QFrame, DockStyled):
    STYLE_CATEGORIES = (DockStyleCategory.CORE,)
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
        self._drop_controller = DropController(self)
        self._maximized_dock_area: DockAreaWidget = None
        self._pre_maximize_splitter_sizes: dict = None  # {id(splitter): sizes_list}
        # DockSplitterHandle junction detection reads this on every hover-move;
        # None means "rebuild from findChildren".  Cleared wherever the area
        # layout changes, which is where handles are created and destroyed.
        self._handle_cache: Optional[list] = None

        # --- ADDED: Style Manager Integration ---
        self._init_dock_style()

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
        new_dock_area.ensure_title_bar_visible()
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
        new_dock_area.ensure_title_bar_visible()
        
        #--- FIX START ---
        #Ensure the root splitter is visible now that it has content
        if not self._root_splitter.isVisible():
            self._root_splitter.show()
        #--- FIX END ---
        
        self._emit_dock_areas_added()
        new_dock_area.destroyed.connect(self.remove_dock_area)

    def drop_floating_widget(self, floating_widget: 'FloatingDockContainer', target_pos: QPoint):
        self._drop_controller.drop_floating_widget(floating_widget, target_pos)

    def _drop_into_container(self, floating_widget: 'FloatingDockContainer', area: DockWidgetArea):
        self._drop_controller._drop_into_container(floating_widget, area)

    def _drop_into_section(self, floating_widget: 'FloatingDockContainer',
                           target_area: DockAreaWidget, area: DockWidgetArea):
        self._drop_controller._drop_into_section(floating_widget, target_area, area)

    def _drop_into_center_of_section(self, floating_widget: 'FloatingDockContainer',
                                     target_area: DockAreaWidget):
        self._drop_controller._drop_into_center_of_section(floating_widget, target_area)

    def add_dock_area(self, dock_area_widget: DockAreaWidget,
                      area: DockWidgetArea = DockWidgetArea.center):
        trace("manager.add_dock_area", area=getattr(area, 'name', str(area)), dock_area=dock_area_widget.objectName() or dock_area_widget.__class__.__name__)
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
            if undock:
                undock.setVisible(True)
            close = dock_area.title_bar_button(TitleBarButton.close)
            if close:
                close.setVisible(True)
            pin = dock_area.title_bar_button(TitleBarButton.pin)
            if pin:
                dock_area._update_title_bar_button_states()

        if count_before == 1:
            self._dock_areas[0].ensure_title_bar_visible()
        if new_area_count == 1:
            self._dock_areas[-1].ensure_title_bar_visible()

        self._emit_dock_areas_added()

    def _append_dock_areas(self, *new_dock_areas):
        self._dock_areas.extend(new_dock_areas)
        for dock_area in new_dock_areas:
            dock_area.view_toggled.connect(self._on_dock_area_view_toggled)

    def remove_dock_area(self, area: DockAreaWidget):
        trace("manager.remove_dock_area", dock_area=area.objectName() or area.__class__.__name__)
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

        # ── Restore maximized state if the removed area was the maximized one ──
        if area is self._maximized_dock_area:
            for sibling in self._dock_areas:
                if sibling.opened_dock_widgets():
                    sibling.setVisible(True)
            self._maximized_dock_area = None
            self._pre_maximize_splitter_sizes = None
            self._visible_dock_area_count = -1
            for dock_area in self._dock_areas:
                dock_area._update_title_bar_button_states()

        splitter = find_parent(DockSplitter, area)

        logger.debug('area setParent %s None', area)
        area.setParent(None)
        hide_empty_parent_splitters(splitter)

        # Drop the cached reference to the area we just removed, or
        # last_added_dock_area_widget() hands back a deleted C++ object.
        for _area, _widget in self._last_added_area_cache.items():
            if _widget is area:
                self._last_added_area_cache[_area] = None

        if splitter is None:
            # The area was not inside a DockSplitter — nothing left to collapse.
            return emit_and_exit()

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

                # Pin button: respect the active widget's pinnable feature & sidebar availability
                pin_button = top_level_dock_area.title_bar_button(TitleBarButton.pin)
                if pin_button:
                    mgr = top_level_dock_area.dock_manager()
                    has_sidebars = mgr and hasattr(mgr, 'sidebar_manager') and mgr.sidebar_manager.has_sidebars
                    can_pin = bool(
                        widget and DockWidgetFeature.pinnable in widget.features()
                    ) if widget else top_level_dock_area.pinnable
                    show_pin = can_pin and has_sidebars and mgr and (DockFlags.dock_area_has_pin_button in mgr.config_flags)
                    pin_button.setVisible(show_pin)
                    pin_button.setEnabled(can_pin)
            else:
                top_level_dock_area.title_bar_button(
                    TitleBarButton.close).setVisible(True)
                pin_button = top_level_dock_area.title_bar_button(TitleBarButton.pin)
                if pin_button:
                    top_level_dock_area._update_title_bar_button_states()

        elif self._top_level_dock_area:
            self._top_level_dock_area.title_bar_button(
                TitleBarButton.undock).setVisible(True)
            self._top_level_dock_area.title_bar_button(
                TitleBarButton.close).setVisible(True)
            pin_button = self._top_level_dock_area.title_bar_button(TitleBarButton.pin)
            if pin_button:
                self._top_level_dock_area._update_title_bar_button_states()
            self._top_level_dock_area = None

    def _emit_dock_areas_removed(self):
            self._visible_dock_area_count = -1  # Force cache invalidation
            self._handle_cache = None
            self._on_visible_dock_area_count_changed()
            self.dock_areas_removed.emit()

    def _emit_dock_areas_added(self):
        self._visible_dock_area_count = -1  # Force cache invalidation
        self._handle_cache = None
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
        if visible and hasattr(self, '_dock_manager') and self._dock_manager and hasattr(self._dock_manager, 'sidebar_manager'):
            self._dock_manager.sidebar_manager.raise_overlays()

    def is_floating(self) -> bool:
        return self._is_floating

    def dump_layout(self):
        _dump_layout(self)

    def features(self) -> DockWidgetFeature:
        features = DockWidgetFeature.all_features
        for dock_area in self._dock_areas:
            features &= dock_area.features()
        return features

    def floating_widget(self):
        from lace.util import find_floating_dock_container
        return find_floating_dock_container(self)

    def close_other_areas(self, keep_open_area: DockAreaWidget):
        self._restore_maximized_area()
        for dock_area in list(self.opened_dock_areas()):
            if dock_area != keep_open_area:
                dock_area.close_area()

    def is_area_maximized(self, area: DockAreaWidget) -> bool:
        """Return True if area is the currently-maximized dock area."""
        if self._maximized_dock_area is not None and self._maximized_dock_area is area:
            return True
        # Floating window with a single dock area uses OS maximize;
        # _maximized_dock_area is not set in that path.
        floating = self.floating_widget()
        if (floating and self.visible_dock_area_count() == 1
                and is_window_maximized(floating)):
            return True
        return False

    def _maximize_splitter(self, splitter: QSplitter, area: DockAreaWidget) -> bool:
        """Recursively zero out sibling splitters/areas and give all space to *area*.

        Returns True if *area* is a direct child of *splitter*.
        """
        def collapse(widget):
            """Take every pane of a losing subtree down to zero.

            setSizes([0]) only reached the *first* pane: Qt applies as many
            values as it is given and leaves the rest at their current size,
            so a sibling splitter with two panes kept one of them on screen.
            """
            if isinstance(widget, QSplitter):
                widget.setSizes([0] * max(1, widget.count()))
            elif isinstance(widget, DockAreaWidget):
                widget.setVisible(False)

        count = splitter.count()
        for i in range(count):
            child = splitter.widget(i)
            if isinstance(child, QSplitter):
                if self._maximize_splitter(child, area):
                    # This subtree contains the maximized area — zero out
                    # all other children of this splitter.
                    for j in range(count):
                        if j != i:
                            collapse(splitter.widget(j))
                    # Give the winning child all available space.
                    sizes = list(splitter.sizes())
                    sizes[i] = sum(sizes)
                    splitter.setSizes(sizes)
                    return True
                # Subtree does not contain area — zero it out.
                collapse(child)
            elif isinstance(child, DockAreaWidget) and child is area:
                # Found the maximized area at this level — give all space to it
                # and hide all other dock areas at this level.
                for j in range(count):
                    if j != i:
                        sib = splitter.widget(j)
                        if isinstance(sib, DockAreaWidget):
                            sib.setVisible(False)
                sizes = [0] * count
                sizes[i] = sum(splitter.sizes())
                splitter.setSizes(sizes)
                return True
        return False

    def _collect_splitter_sizes(self, splitter: QSplitter) -> None:
        """Recursively collect all splitter sizes into _pre_maximize_splitter_sizes."""
        if self._pre_maximize_splitter_sizes is None:
            self._pre_maximize_splitter_sizes = {}
        self._pre_maximize_splitter_sizes[id(splitter)] = list(splitter.sizes())
        for i in range(splitter.count()):
            child = splitter.widget(i)
            if isinstance(child, QSplitter):
                self._collect_splitter_sizes(child)

    def toggle_maximize_dock_area(self, area: DockAreaWidget):
        """Maximize or restore a dock area inside this container.

        - For a solo dock area in a floating window: delegates to OS
          showMaximized() / showNormal().
        - For multiple dock areas (main window or multi-dock float):
          hides sibling areas so the target fills 100%, then restores
          them with their original splitter sizes on un-maximize.
        """
        if self._maximized_dock_area is area:
            # ── Restore ──────────────────────────────────────────────
            self._restore_maximized_area()
            return

        # If another area was maximized, restore it first
        if self._maximized_dock_area is not None:
            self._restore_maximized_area()

        # ── Floating: single dock area → OS maximize ─────────────
        floating = self.floating_widget()
        if floating and self.visible_dock_area_count() == 1:
            # Same toggle the frameless title bar uses: isMaximized() alone is
            # not enough to decide, and showNormal() alone is not enough to
            # undo. See lace.util / docs/FRAMELESS_WINDOW_STATE.md.
            toggle_window_maximized(floating)
            # Update button state for the floating case
            area._update_title_bar_button_states()
            return

        # ── Multi-dock: hide siblings & redistribute sizes ───────────
        if self._root_splitter is None:
            return

        # Save ALL splitter sizes (root + nested) for later restore
        self._pre_maximize_splitter_sizes = {}
        self._collect_splitter_sizes(self._root_splitter)
        self._maximized_dock_area = area

        for dock_area in self._dock_areas:
            if dock_area is not area:
                dock_area.setVisible(False)

        # Give all available space to the maximized area so its
        # children resize immediately (Qt splitters don't auto-redistribute).
        # The maximized area may be nested inside splitters, so we
        # recursively zero out sibling splitters/areas and give the
        # maximized area's parent splitter all available space.
        self._maximize_splitter(self._root_splitter, area)

        # Invalidate visible count cache and update button states
        self._visible_dock_area_count = -1
        for dock_area in self._dock_areas:
            dock_area._update_title_bar_button_states()

    def _restore_maximized_area(self):
        """Internal: restore all hidden sibling areas from a maximize."""
        if self._maximized_dock_area is None:
            return

        self._maximized_dock_area = None

        for dock_area in self._dock_areas:
            if dock_area.opened_dock_widgets():
                dock_area.setVisible(True)

        # Restore original splitter proportions (all splitters, not just root)
        if self._pre_maximize_splitter_sizes and self._root_splitter:
            for sp in self._all_splitters():
                sid = id(sp)
                if sid in self._pre_maximize_splitter_sizes:
                    sp.setSizes(self._pre_maximize_splitter_sizes[sid])
        self._pre_maximize_splitter_sizes = None

        # Invalidate visible count cache and update button states
        self._visible_dock_area_count = -1
        for dock_area in self._dock_areas:
            dock_area._update_title_bar_button_states()

    def _all_splitters(self):
        """Yield all splitters under the root splitter."""
        if self._root_splitter is None:
            return
        yield self._root_splitter
        stack = [self._root_splitter]
        while stack:
            sp = stack.pop()
            for i in range(sp.count()):
                child = sp.widget(i)
                if isinstance(child, QSplitter):
                    yield child
                    stack.append(child)

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

