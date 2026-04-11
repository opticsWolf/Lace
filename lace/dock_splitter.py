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
from typing import Optional

from PySide6.QtCore import Qt, QEvent, QSize
from PySide6.QtGui import QPainter, QColor
from PySide6.QtWidgets import QSplitter, QSplitterHandle, QWidget

from .dock_style_manager import get_dock_style_manager
from .dock_theme import DockStyleCategory

logger = logging.getLogger(__name__)


class DockSplitterHandle(QSplitterHandle):
    """
    Custom resize handle for the DockSplitter.
    Reacts to hover events and dynamically reads its colors and thickness 
    from the global DockStyleManager.
    """
    def __init__(self, orientation: Qt.Orientation, parent: 'DockSplitter'):
        super().__init__(orientation, parent)
        self.setAttribute(Qt.WA_Hover, True)
        self._is_hovered = False
        
        # New: Space for layout vs visual thickness
        self._total_width = 6   # The physical clickable/gap area
        self._handle_width = 2  # The visual colored line

        self._style_mgr = get_dock_style_manager()
        self._style_mgr.register(self, DockStyleCategory.SPLITTER)
        self.refresh_style()

    def refresh_style(self):
        """Fetches the latest splitter styles from the active theme."""
        styles = self._style_mgr.get_all(DockStyleCategory.SPLITTER)
        
        self._c_handle = styles.get("handle_color", QColor(45, 45, 45))
        self._c_hover = styles.get("handle_hover_color", QColor(0, 122, 204))
        self._handle_width = styles.get("handle_width", 2)
        self._total_width = styles.get("total_width", 6)
        self._handle_margin = styles.get("handle_margin", 4)  # <--- Load the margin
        
        self.update()

    def on_style_changed(self, category: DockStyleCategory, changes: dict):
        """Callback triggered by DockStyleManager when the theme switches."""
        self.refresh_style()

    def enterEvent(self, event: QEvent):
        """Triggered when the mouse hovers over the resize handle."""
        self._is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent):
        """Triggered when the mouse leaves the resize handle."""
        self._is_hovered = False
        self.update()
        super().leaveEvent(event)

    def sizeHint(self) -> QSize:
        """Sets the physical layout width of the splitter."""
        size = super().sizeHint()
        if self.orientation() == Qt.Horizontal:
            size.setWidth(self._total_width)
        else:
            size.setHeight(self._total_width)
        return size

    def paintEvent(self, event):
        """Paints a themed rounded-cap handle centered within a wider gap."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        color = self._c_hover if self._is_hovered else self._c_handle
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        
        full_rect = self.rect()
        radius = self._handle_width / 2
        m = self._handle_margin

        if self.orientation() == Qt.Horizontal:
            # Center horizontally, apply margin to top/bottom
            offset = (full_rect.width() - self._handle_width) // 2
            draw_rect = full_rect.adjusted(offset, m, 
                                           -(full_rect.width() - self._handle_width - offset), 
                                           -m)
        else:
            # Center vertically, apply margin to left/right
            offset = (full_rect.height() - self._handle_width) // 2
            draw_rect = full_rect.adjusted(m, offset, 
                                           -m, 
                                           -(full_rect.height() - self._handle_width - offset))

        painter.drawRoundedRect(draw_rect, radius, radius)


class DockSplitter(QSplitter):
    """
    The core layout divider for the docking framework.
    Manages nested child visibility and spawns customized, theme-aware handles.
    """
    def __init__(self, orientation: Qt.Orientation = Qt.Horizontal, parent: Optional[QWidget] = None):
        super().__init__(orientation, parent)
        self.setProperty("dock_splitter", True)

    def createHandle(self) -> QSplitterHandle:
        """Overrides default handle creation to inject our themed handle."""
        return DockSplitterHandle(self.orientation(), self)

    def has_visible_content(self) -> bool:
        """
        Recursively checks if this splitter contains any actually visible widgets.
        Used by the utility functions to dynamically hide empty layout branches.
        """
        for i in range(self.count()):
            widget = self.widget(i)
            if widget and not widget.isHidden():
                # If the child is also a DockSplitter, we must check it recursively
                if isinstance(widget, DockSplitter):
                    if widget.has_visible_content():
                        return True
                else:
                    return True
        return False