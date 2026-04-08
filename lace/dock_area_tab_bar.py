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

from typing import TYPE_CHECKING, Optional
import logging

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, Signal
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QBoxLayout, QFrame, QScrollArea, QSizePolicy, QWidget

from .util import start_drag_distance
from .enums import DragState, DockWidgetArea
from .dock_widget_tab import DockWidgetTab
from .floating_dock_container import FloatingDockContainer
from .dock_style_manager import get_dock_style_manager
from .dock_theme import DockStyleCategory

if TYPE_CHECKING:
    from . import DockAreaWidget

logger = logging.getLogger(__name__)


class DockAreaTabBar(QScrollArea):
    current_changing = Signal(int)
    current_changed = Signal(int)
    tab_bar_clicked = Signal(int)
    tab_close_requested = Signal(int)
    tab_closed = Signal(int)
    tab_opened = Signal(int)
    tab_moved = Signal(int, int)
    removing_tab = Signal(int)
    tab_inserted = Signal(int)

    def __init__(self, parent: 'DockAreaWidget'):
        super().__init__(parent)

        # Flattened private properties
        self._dock_area = parent
        self._drag_start_mouse_pos = QPoint()
        self._floating_widget: Optional['FloatingDockContainer'] = None
        self._tabs_container_widget: QWidget = None
        self._tabs_layout: QBoxLayout = None
        self._current_index = -1

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Ignored)
        self.setFrameStyle(QFrame.NoFrame)
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._tabs_container_widget = QWidget()
        self._tabs_container_widget.setObjectName("tabsContainerWidget")
        self.setWidget(self._tabs_container_widget)

        self._tabs_layout = QBoxLayout(QBoxLayout.LeftToRight)
        self._tabs_layout.setContentsMargins(0, 0, 0, 0)
        self._tabs_layout.setSpacing(0)
        self._tabs_layout.addStretch(1)
        self._tabs_container_widget.setLayout(self._tabs_layout)

        # --- ADDED: Style Manager Integration ---
        self._style_mgr = get_dock_style_manager()
        self._style_mgr.register(self, DockStyleCategory.TAB)
        self.refresh_style()

    def _update_tabs(self):
        for i in range(self.count()):
            tab_widget = self.tab(i)
            if not tab_widget:
                continue

            if i == self._current_index:
                tab_widget.show()
                tab_widget.set_active_tab(True)
                self.ensureWidgetVisible(tab_widget)
            else:
                tab_widget.set_active_tab(False)

    def _connect_tab_signals(self, tab: DockWidgetTab):
        tab.clicked.connect(self.on_tab_clicked)
        tab.close_requested.connect(self.on_tab_close_requested)
        tab.close_other_tabs_requested.connect(self.on_close_other_tabs_requested)
        tab.moved.connect(self.on_tab_widget_moved)

    def _disconnect_tab_signals(self, tab: DockWidgetTab):
        tab.clicked.disconnect(self.on_tab_clicked)
        tab.close_requested.disconnect(self.on_tab_close_requested)
        tab.close_other_tabs_requested.disconnect(self.on_close_other_tabs_requested)
        tab.moved.disconnect(self.on_tab_widget_moved)

    def on_tab_clicked(self):
        tab = self.sender()
        if not tab or not isinstance(tab, DockWidgetTab):
            return

        index = self._tabs_layout.indexOf(tab)
        if index < 0:
            return

        self.set_current_index(index)
        self.tab_bar_clicked.emit(index)

    def on_tab_close_requested(self):
        tab = self.sender()
        index = self._tabs_layout.indexOf(tab)
        self.close_tab(index)

    def on_close_other_tabs_requested(self):
        sender = self.sender()

        for i in range(self.count()):
            tab = self.tab(i)
            if tab.is_closable() and not tab.isHidden() and tab != sender:
                self.close_tab(i)

    def on_tab_widget_moved(self, global_pos: QPoint):
        moving_tab = self.sender()
        if not moving_tab or not isinstance(moving_tab, DockWidgetTab):
            return

        from_index = self._tabs_layout.indexOf(moving_tab)
        mouse_pos = self.mapFromGlobal(global_pos)
        to_index = -1

        for i in range(self.count()):
            drop_tab = self.tab(i)
            if (drop_tab == moving_tab or not drop_tab.isVisibleTo(self) or
                    not drop_tab.geometry().contains(mouse_pos)):
                continue

            to_index = self._tabs_layout.indexOf(drop_tab)
            if to_index == from_index:
                to_index = -1
                continue
            elif to_index < 0:
                to_index = 0
            break

        if to_index < 0:
            if mouse_pos.x() > self.tab(self.count() - 1).geometry().right():
                logger.debug('after all tabs')
                to_index = self.count() - 1
            else:
                to_index = from_index

        self._tabs_layout.removeWidget(moving_tab)
        self._tabs_layout.insertWidget(to_index, moving_tab)
        if to_index >= 0:
            logger.debug('tabMoved from %s to %s', from_index, to_index)
            self.tab_moved.emit(from_index, to_index)
            self.set_current_index(to_index)

    def make_area_floating(self, global_pos: QPoint, drag_state):
        dock_area = self._dock_area
        if dock_area is None:
            return
        manager = dock_area.dock_manager()
        if not manager:
            return
    
        from .floating_dock_container import FloatingDockContainer
    
        # Capture before constructor detaches the area from the layout.
        size = dock_area.size()
        dock_origin = dock_area.mapToGlobal(QPoint(0, 0))
    
        floating_container = FloatingDockContainer(dock_area=dock_area)
    
        if drag_state == DragState.floating_widget and hasattr(floating_container, 'start_dragging'):
            floating_container.start_dragging(global_pos, size, None)
        else:
            # Place the window exactly where the dock was, shifted slightly
            # so the user can see it has detached.
            floating_container.move(dock_origin + QPoint(10, 10))
            floating_container.resize(size)
    
        floating_container.show()

    def wheelEvent(self, event: QWheelEvent):
        event.accept()
        direction = event.angleDelta().y()
        horizontal_bar = self.horizontalScrollBar()
        delta = (20 if direction < 0 else -20)
        horizontal_bar.setValue(self.horizontalScrollBar().value() + delta)

    # --- REPLACED: Simplified mouse event handlers ---
    def mousePressEvent(self, ev: QMouseEvent):
        """
        Handle mouse press events.
        
        Ignores left-button presses to allow parent (DockAreaTitleBar) 
        to handle dragging. Other buttons are handled by the parent class.

        Args:
            ev (QMouseEvent): The mouse event.
        """
        # Let the parent (DockAreaTitleBar) handle left clicks for dragging
        if ev.button() == Qt.LeftButton:
            ev.ignore()
            return
        super().mousePressEvent(ev)

    def mouseReleaseEvent(self, ev: QMouseEvent):
        """
        Handle mouse release events.

        Ignores left-button releases to allow parent (DockAreaTitleBar) 
        to handle dragging. Other buttons are handled by the parent class.

        Args:
            ev (QMouseEvent): The mouse event.
        """
        if ev.button() == Qt.LeftButton:
            ev.ignore()
            return
        super().mouseReleaseEvent(ev)

    def mouseMoveEvent(self, ev: QMouseEvent):
        """
        Handle mouse move events.

        Ignores left-button moves to allow parent (DockAreaTitleBar) 
        to handle dragging. Other movements are handled by the parent class.

        Args:
            ev (QMouseEvent): The mouse event.
        """
        # Ignore move events so they bubble up to the title bar's drag logic
        if ev.buttons() & Qt.LeftButton:
            ev.ignore()
            return
        super().mouseMoveEvent(ev)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """
        Handle mouse double-click events.

        Ignores left-button double clicks to allow parent (DockAreaTitleBar) 
        to handle floating. Other buttons are handled by the parent class.

        Args:
            event (QMouseEvent): The mouse event.
        """
        if event.button() == Qt.LeftButton:
            event.ignore()
            return
        super().mouseDoubleClickEvent(event)

    # --- REMOVED: start_floating and make_area_floating methods ---
    
    def insert_tab(self, index: int, tab: 'DockWidgetTab'):
        self._tabs_layout.insertWidget(index, tab)
        self._connect_tab_signals(tab)
        tab.installEventFilter(self)
        self.tab_inserted.emit(index)
        
        if index <= self._current_index:
            self.set_current_index(self._current_index + 1)

    def remove_tab(self, tab: 'DockWidgetTab'):
        if not self.count():
            return

        logger.debug('DockAreaTabBar.removeTab')
        new_current_index = self.current_index()
        remove_index = self._tabs_layout.indexOf(tab)
        if self.count() == 1:
            new_current_index = -1

        if new_current_index > remove_index:
            new_current_index -= 1
        elif new_current_index == remove_index:
            new_current_index = -1

            for i in range(remove_index + 1, self.count()):
                if self.tab(i).isVisibleTo(self):
                    new_current_index = i - 1
                    break

            if new_current_index < 0:
                for i in range(remove_index - 1, -1, -1):
                    if self.tab(i).isVisibleTo(self):
                        new_current_index = i
                        break

        self.removing_tab.emit(remove_index)
        self._tabs_layout.removeWidget(tab)
        self._disconnect_tab_signals(tab)

        tab.removeEventFilter(self)
        logger.debug('NewCurrentIndex %s', new_current_index)

        if new_current_index != self._current_index:
            self.set_current_index(new_current_index)
        else:
            self._update_tabs()

    def count(self) -> int:
        return self._tabs_layout.count() - 1

    def current_index(self) -> int:
        return self._current_index

    def current_tab(self) -> Optional['DockWidgetTab']:
        if self._current_index < 0:
            return None
        return self._tabs_layout.itemAt(self._current_index).widget()

    def tab(self, index: int) -> Optional['DockWidgetTab']:
        if index >= self.count() or index < 0:
            return None
        return self._tabs_layout.itemAt(index).widget()

    def eventFilter(self, tab: QObject, event: QEvent) -> bool:
        result = super().eventFilter(tab, event)
        if isinstance(tab, DockWidgetTab):
            if event.type() == QEvent.Hide:
                self.tab_closed.emit(self._tabs_layout.indexOf(tab))
            elif event.type() == QEvent.Show:
                self.tab_opened.emit(self._tabs_layout.indexOf(tab))
        return result

    def is_tab_open(self, index: int) -> bool:
        if index < 0 or index >= self.count():
            return False
        return not self.tab(index).isHidden()

    def set_current_index(self, index: int):
        if index == self._current_index:
            return
        if index < -1 or index > (self.count() - 1):
            logger.warning('Invalid index %s', index)
            return

        self.current_changing.emit(index)
        self._current_index = index
        self._update_tabs()
        self.current_changed.emit(index)

    def close_tab(self, index: int):
        if index < 0 or index >= self.count():
            return

        tab = self.tab(index)
        if tab.isHidden():
            return

        self.tab_close_requested.emit(index)
        tab.hide()

    def refresh_style(self):
        styles = self._style_mgr.get_all(DockStyleCategory.TAB)
        
        # Update spacing between individual tabs
        self._tabs_layout.setSpacing(styles.get("margin", 0))
        
        # Update background behind the tabs
        bg_color = styles.get("bg_normal").name()
        self.setStyleSheet(f"""
            DockAreaTabBar {{
                background-color: {bg_color};
                border: none;
            }}
            QWidget#tabsContainerWidget {{
                background-color: {bg_color};
            }}
        """)

    def on_style_changed(self, category: DockStyleCategory, changes: dict):
        self.refresh_style()

