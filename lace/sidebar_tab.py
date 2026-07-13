# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


from typing import Any, Union, Optional
from enum import Enum, auto
from PySide6.QtCore import Qt, Signal, QPoint, QSize, QRect, QRectF
from PySide6.QtGui import (
    QPainter, QFontMetrics, QIcon, QColor, QPen, QMouseEvent, QFont
)
from PySide6.QtWidgets import QToolButton, QWidget, QSizePolicy

from .dock_chrome import DragDetector
from .dock_paint import paint_tab
from .enums import DockWidgetArea
from .dock_styled import DockStyled
from .dock_theme import DockStyleCategory


class TabBadgePosition(Enum):
    top_left = auto()
    top_right = auto()
    bottom_left = auto()
    bottom_right = auto()


class VerticalTabButton(QToolButton, DockStyled):
    """Advanced tab button with badges, context menu, and enhanced visuals."""
    STYLE_CATEGORIES = (DockStyleCategory.SIDEBAR,)
    
    drag_started = Signal(object)
    context_menu_requested = Signal(object, QPoint)
    close_requested = Signal(object)
    
    def __init__(self, text: str, icon: QIcon = None,
                 parent: QWidget = None, badge_position: TabBadgePosition = TabBadgePosition.top_right):
        super().__init__(parent)
        self._text = text
        self._icon = icon or QIcon()
        self._badge_count: Any = 0
        self._badge_position: TabBadgePosition = badge_position
        self._is_hovered = False
        self._area: DockWidgetArea = DockWidgetArea.left  # Which sidebar this tab belongs to
        
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
        self._indicator_position = "left"  # "left" or "right"
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

        # Drag off the sidebar to tear the panel into a floating window.
        self._drag = DragDetector(self)
        self._drag.drag_started.connect(lambda _pos: self.drag_started.emit(self))

        # --- Style Manager Integration ---
        self._init_dock_style()
    
    def text(self) -> str:
        """Returns the text of the tab so the context menu can read it."""
        return self._text
    
    def set_area(self, area: DockWidgetArea):
        """Set which sidebar this tab belongs to (for indicator mirroring)."""
        self._area = area
        self.update()    

    @property
    def badge_position(self) -> TabBadgePosition:
        return self._badge_position

    def set_badge_position(self, position: TabBadgePosition):
        self._badge_position = position
        self.update()
    
    def set_badge(self, value: Any, color: QColor = None, position: TabBadgePosition = None):
        """Set notification badge count or text (e.g., number, '!', '?')."""
        if isinstance(value, int):
            self._badge_count = max(0, value)
        elif isinstance(value, str):
            self._badge_count = value.strip()
        else:
            self._badge_count = 0
            
        if color:
            self._badge_color = color
        if position is not None:
            self._badge_position = position
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
        if ev.button() == Qt.MiddleButton:
            # Middle click to close/unpin
            self.close_requested.emit(self)
        super().mousePressEvent(ev)

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

        # 1+2. Background/hover + selection indicator via the shared paint_tab
        # (square: radius 0; the vertical sidebar indicator hugs a Left/Right edge).
        rect = QRectF(self.rect())
        if self.isChecked():
            paint_tab(p, rect, bg=self._bg_active,
                      indicator=self._highlight_color,
                      indicator_width=self._indicator_width,
                      indicator_edge=self._indicator_edge())
        elif self._is_hovered:
            paint_tab(p, rect, bg_gradient=(self._bg_hover_start, self._bg_hover_end))
        # else: idle — transparent, nothing painted

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
        if self._badge_count != 0 and self._badge_count != "" and self._badge_count is not None:
            self._draw_badge(p, self.rect())
            
        p.end()
    
    def _indicator_edge(self) -> Qt.Edge:
        """Which edge the active-tab indicator hugs, mirrored per sidebar side.

        ``indicator_position`` "right" = outer edge, "left" = inner edge; on the
        right-hand sidebar both flip.  (Preserves the pre-paint_tab mapping.)
        """
        is_right = self._area == DockWidgetArea.right
        if self._indicator_position == "right":
            return Qt.Edge.LeftEdge if is_right else Qt.Edge.RightEdge
        return Qt.Edge.RightEdge if is_right else Qt.Edge.LeftEdge

    def _draw_badge(self, p: QPainter, rect: QRect):
        """Draw notification badge."""
        if self._badge_count == 0 or self._badge_count == "" or self._badge_count is None:
            return
        
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(self._badge_color)
        
        # Position badge dynamically according to self._badge_position
        if self._badge_position == TabBadgePosition.top_left:
            badge_rect = QRect(4, 4, 12, 12)
        elif self._badge_position == TabBadgePosition.bottom_left:
            badge_rect = QRect(4, rect.height() - 16, 12, 12)
        elif self._badge_position == TabBadgePosition.bottom_right:
            badge_rect = QRect(rect.width() - 16, rect.height() - 16, 12, 12)
        else:  # TabBadgePosition.top_right
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
        
        if isinstance(self._badge_count, int):
            text = str(min(self._badge_count, 99))
        else:
            text = str(self._badge_count)[:3]
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
        self._indicator_position = s.get("indicator_position", "left")
        self._tab_corner_radius = s.get("tab_corner_radius", 4)
        self._badge_color = s.get("badge_bg") or self._badge_color
        self._badge_text_color = s.get("badge_text") or self._badge_text_color
        badge_pos = s.get("badge_position")
        if isinstance(badge_pos, TabBadgePosition):
            self._badge_position = badge_pos
        elif isinstance(badge_pos, str):
            try:
                self._badge_position = TabBadgePosition[badge_pos]
            except KeyError:
                pass

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

