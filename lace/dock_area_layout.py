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
from typing import List, Optional, TYPE_CHECKING

from PySide6.QtCore import QRect
from PySide6.QtWidgets import QBoxLayout, QWidget

if TYPE_CHECKING:
    from .dock_widget import DockWidget

logger = logging.getLogger(__name__)


class DockAreaLayout:
    """
    A custom layout wrapper that acts similarly to a QStackedLayout, but operates 
    within a standard QBoxLayout. It ensures only one DockWidget is visible in the 
    content area at a time.
    """

    def __init__(self, parent_layout: QBoxLayout):
        self._parent_layout = parent_layout
        self._widgets: List[QWidget] = []
        self._current_index: int = -1
        self._current_widget: Optional[QWidget] = None

    def count(self) -> int:
        """Returns the number of widgets managed by this layout."""
        return len(self._widgets)

    def insert_widget(self, index: int, widget: QWidget):
        """Inserts a widget at the given index and updates visibility."""
        logger.debug('%s setParent None', widget)
        widget.setParent(None)
        
        if index < 0:
            index = len(self._widgets)

        self._widgets.insert(index, widget)
        
        if self._current_index < 0:
            self.set_current_index(index)
        elif index <= self._current_index:
            self._current_index += 1

    def remove_widget(self, widget: QWidget):
        """Removes the widget from the layout."""
        if self.current_widget() == widget:
            layout_item = self._parent_layout.takeAt(1)
            if layout_item:
                removed_widget = layout_item.widget()
                logger.debug('%s setParent None', removed_widget)
                removed_widget.setParent(None)

            self._current_widget = None
            self._current_index = -1

        if widget in self._widgets:
            self._widgets.remove(widget)

    def current_widget(self) -> Optional[QWidget]:
        """Returns the currently visible widget."""
        return self._current_widget

    def set_current_index(self, index: int):
        """Swaps the visible widget to the one at the given index."""
        prev = self.current_widget()
        next_ = self.widget(index)
        
        if not next_ or (next_ is prev and not self._current_widget):
            return

        reenable_updates = False
        parent = self._parent_layout.parentWidget()
        if parent and parent.updatesEnabled():
            reenable_updates = True
            parent.setUpdatesEnabled(False)

        layout_item = self._parent_layout.takeAt(1)
        if layout_item:
            widget = layout_item.widget()
            logger.debug('%s setParent None', widget)
            widget.setParent(None)

        self._parent_layout.addWidget(next_)
        if prev:
            prev.hide()

        self._current_index = index
        self._current_widget = next_
        
        if reenable_updates:
            parent.setUpdatesEnabled(True)

    def current_index(self) -> int:
        """Returns the index of the currently visible widget."""
        return self._current_index

    def is_empty(self) -> bool:
        """Checks if the layout has no widgets."""
        return len(self._widgets) == 0

    def index_of(self, widget: QWidget) -> int:
        """Returns the index of the given widget, or ValueError if not found."""
        return self._widgets.index(widget)

    def widget(self, index: int) -> Optional[QWidget]:
        """Safely retrieves the widget at the given index."""
        try:
            return self._widgets[index]
        except IndexError:
            return None

    def geometry(self) -> QRect:
        """Returns the geometry of the currently visible widget."""
        if not self._widgets or self._current_widget is None:
            return QRect()
        return self._current_widget.geometry()