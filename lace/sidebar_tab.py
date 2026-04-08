# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0
"""

from enum import Enum, auto
from typing import Optional

from PySide6.QtCore import Qt, Signal, QPoint, QSize, QRect
from PySide6.QtGui import (
    QPainter, QFontMetrics, QIcon, QColor, QPen, QMouseEvent, 
    QFont, QLinearGradient, QBrush
)
from PySide6.QtWidgets import QToolButton, QWidget, QSizePolicy

from .util import start_drag_distance
from .dock_style_manager import get_dock_style_manager
from .dock_theme import DockStyleCategory


class TabBadgePosition(Enum):
    top_left = auto()
    top_right = auto()
    bottom_left = auto()
    bottom_right = auto()


class VerticalTabButton(QToolButton):
    """Advanced tab button with badges, context menu, and enhanced visuals."""
    
    drag_started = Signal(object)
    context_menu_requested = Signal(object, QPoint)
    close_requested = Signal(object)
    
    def __init__(self, text: str, icon: QIcon = None,
                 parent: QWidget = None):
        super().__init__(parent)
        self._text = text
        self._icon = icon or QIcon()
        self._drag_start: Optional[QPoint] = None
        self._badge_count: int = 0
        self._is_hovered = False
        
        # --- Cached style values (overwritten by refresh_style) ---
        self._badge_color = QColor("#ff6b6b")
        self._badge_text_color = QColor(Qt.white)
        self._highlight_color = QColor(0, 122, 204)
        self._bg_active = QColor(45, 45, 45)
        self._bg_hover_start = QColor(60, 60, 60)
        self._bg_hover_end = QColor(45, 45, 45)
        self._text_active = QColor(Qt.white)
        self._text_normal = QColor(204, 204, 204)
        self._indicator_width = 3
        self._tab_corner_radius = 4
        
        self.setCheckable(True)
        self.setAutoRaise(True)
        self.setToolTip(text)
        self.setObjectName("sideTabButton")
        self.setAttribute(Qt.WA_Hover, True)
        
        # FIX: Ensure button explicitly expands into the sidebar's minor axis so it fills the width
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        # Context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)

        # --- Style Manager Integration ---
        self._style_mgr = get_dock_style_manager()
        self._style_mgr.register(self, DockStyleCategory.SIDEBAR)
        self.refresh_style()
    
    def text(self) -> str:
        """Returns the text of the tab so the context menu can read it."""
        return self._text    
    
    def set_badge(self, count: int, color: QColor = None):
        """Set notification badge count."""
        self._badge_count = max(0, count)
        if color:
            self._badge_color = color
        self.update()
    
    def clear_badge(self):
        self._badge_count = 0
        self.update()
    
    def enterEvent(self, event):
        self._is_hovered = True
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        self._is_hovered = False
        super().leaveEvent(event)
    
    def _on_context_menu(self, pos: QPoint):
        self.context_menu_requested.emit(self, self.mapToGlobal(pos))
    
    def mousePressEvent(self, ev: QMouseEvent):
        if ev.button() == Qt.LeftButton:
            self._drag_start = ev.position().toPoint()
        elif ev.button() == Qt.MiddleButton:
            # Middle click to close/unpin
            self.close_requested.emit(self)
        super().mousePressEvent(ev)
    
    def mouseMoveEvent(self, ev: QMouseEvent):
        if (self._drag_start is not None
                and (ev.position().toPoint() - self._drag_start).manhattanLength()
                >= start_drag_distance()):
            self._drag_start = None
            self.drag_started.emit(self)
            return
        super().mouseMoveEvent(ev)
    
    def mouseReleaseEvent(self, ev: QMouseEvent):
        self._drag_start = None
        super().mouseReleaseEvent(ev)
    
    def sizeHint(self) -> QSize:
        fm = QFontMetrics(self.font())
        text_w = fm.horizontalAdvance(self._text)
        icon_space = 20 if (self._icon and not self._icon.isNull()) else 0
        pad = 22  # FIX: Increased padding slightly to prevent visual clipping
        
        return QSize(1, text_w + icon_space + pad)
    
    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        # 1. Background and Hover
        if self.isChecked():
            p.fillRect(self.rect(), self._bg_active)
        elif self._is_hovered:
            gradient = QLinearGradient(0, 0, self.width(), 0)
            gradient.setColorAt(0, self._bg_hover_start)
            gradient.setColorAt(1, self._bg_hover_end)
            p.fillRect(self.rect(), QBrush(gradient))
        else:
            p.fillRect(self.rect(), QColor(0, 0, 0, 0))
        
        # 2. Selection Indicator
        if self.isChecked():
            p.fillRect(0, 0, self._indicator_width, self.height(),
                       self._highlight_color)
        
        # 3. Centered Content (Icon + Text)
        p.save()
        # Rotate coordinates: Move to top-right and rotate 90 deg clockwise
        # In this rotated space: +X axis points DOWN, +Y axis points LEFT
        p.translate(self.width(), 0)
        p.rotate(90)
        
        # Dimensions in the rotated coordinate system
        r_width = self.height()   # Physical length (height) of the button
        r_height = self.width()   # Physical width of the sidebar
        
        # Measure content for centering
        fm = p.fontMetrics()
        text_w = fm.horizontalAdvance(self._text)
        icon_size = 16 if (self._icon and not self._icon.isNull()) else 0
        gap = 8 if icon_size > 0 else 0
        
        # Calculate the total width of the block to center it vertically
        total_content_w = icon_size + gap + text_w
        current_x = (r_width - total_content_w) / 2
        
        # Set text color based on state
        text_color = self._text_active if self.isChecked() else self._text_normal
        p.setPen(QPen(text_color))
        
        # Draw Icon
        if icon_size > 0:
            iy = (r_height - icon_size) / 2
            self._icon.paint(p, int(current_x), int(iy), icon_size, icon_size)
            current_x += icon_size + gap
            
        # Draw Text
        text_rect = QRect(int(current_x), 0, int(text_w), int(r_height))
        p.drawText(text_rect, Qt.AlignCenter, self._text)
        
        p.restore()
        
        # 4. Notification Badge (Standard physical coordinates)
        if self._badge_count > 0:
            self._draw_badge(p, self.rect())
            
        p.end()
    
    def _draw_badge(self, p: QPainter, rect: QRect):
        """Draw notification badge."""
        if self._badge_count == 0:
            return
        
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(self._badge_color)
        
        # Position at top-right for vertical tabs
        badge_rect = QRect(rect.width() - 16, 4, 12, 12)
        p.drawEllipse(badge_rect)
        
        # Badge text
        p.setPen(QPen(self._badge_text_color))
        
        s = self._style_mgr.get_all(DockStyleCategory.SIDEBAR)
        badge_font = QFont(
            s.get("badge_font_family", "Segoe UI"),
            s.get("badge_font_size", 8),
        )
        weight = s.get("badge_font_weight", "bold")
        badge_font.setBold(weight in ("bold", 700, QFont.Bold))
        p.setFont(badge_font)
        
        text = str(min(self._badge_count, 99))
        p.drawText(badge_rect, Qt.AlignCenter, text)

    # --- Style Manager ---

    def refresh_style(self):
        """Read SIDEBAR styles and cache as instance attributes for paintEvent."""
        s = self._style_mgr.get_all(DockStyleCategory.SIDEBAR)

        self._bg_active = s.get("tab_bg_active") or self._bg_active
        self._bg_hover_start = s.get("tab_bg_hover_start") or self._bg_hover_start
        self._bg_hover_end = s.get("tab_bg_hover_end") or self._bg_hover_end
        self._text_active = s.get("tab_text_active") or self._text_active
        self._text_normal = s.get("tab_text_normal") or self._text_normal
        self._highlight_color = s.get("indicator_color") or self._highlight_color
        self._indicator_width = s.get("indicator_width", 3)
        self._tab_corner_radius = s.get("tab_corner_radius", 4)
        self._badge_color = s.get("badge_bg") or self._badge_color
        self._badge_text_color = s.get("badge_text") or self._badge_text_color

        # Typography
        font = self.font()
        font.setFamily(s.get("tab_font_family", "Segoe UI"))
        font.setPointSize(s.get("tab_font_size", 10))
        weight = s.get("tab_font_weight", "normal")
        font.setBold(weight in ("bold", 700, QFont.Bold))
        font.setItalic(s.get("tab_font_italic", False))
        font.setUnderline(s.get("tab_font_underline", False))
        self.setFont(font)

        self.update()

    def on_style_changed(self, category: DockStyleCategory, changes: dict):
        self.refresh_style()
