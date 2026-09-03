# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


from typing import Any, Optional
from enum import Enum, auto
from PySide6.QtCore import Qt, Signal, QPoint, QSize, QRect, QRectF
from PySide6.QtGui import (
    QPainter, QFontMetrics, QIcon, QColor, QPen, QMouseEvent, QFont
)
from PySide6.QtWidgets import QToolButton, QWidget, QSizePolicy

from lace.dock_chrome import DragDetector
from lace.dock_paint import paint_tab
from lace.enums import DockWidgetArea
from lace.dock_styled import DockStyled
from lace.dock_icon_provider import get_icon_provider
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import DEFAULT_ICON_SIZE, DockStyleCategory


class TabBadgePosition(Enum):
    top_left = auto()
    top_right = auto()
    bottom_left = auto()
    bottom_right = auto()


#: The edge of a sidebar tab that faces the window edge its bar runs along.
#: The tab's flat side is this one or its opposite — see ``tab_flat_edge``.
_OUTWARD_EDGE = {
    DockWidgetArea.left:   Qt.Edge.LeftEdge,
    DockWidgetArea.right:  Qt.Edge.RightEdge,
    DockWidgetArea.top:    Qt.Edge.TopEdge,
    DockWidgetArea.bottom: Qt.Edge.BottomEdge,
}
_OPPOSITE_EDGE = {
    Qt.Edge.LeftEdge:   Qt.Edge.RightEdge,
    Qt.Edge.RightEdge:  Qt.Edge.LeftEdge,
    Qt.Edge.TopEdge:    Qt.Edge.BottomEdge,
    Qt.Edge.BottomEdge: Qt.Edge.TopEdge,
}


class VerticalTabButton(QToolButton, DockStyled):
    """Advanced tab button with badges, context menu, and enhanced visuals."""
    # TAB is read for the corner radius the sidebar tabs share with the dock
    # widget tabs; without it declared they would keep the old radius when a
    # theme changes only TAB.corner_radius.
    STYLE_CATEGORIES = (DockStyleCategory.SIDEBAR, DockStyleCategory.TAB)

    drag_started = Signal(object)
    context_menu_requested = Signal(object, QPoint)
    close_requested = Signal(object)
    
    def __init__(self, text: str, icon: QIcon = None,
                 parent: QWidget = None, badge_position: TabBadgePosition = TabBadgePosition.top_right):
        super().__init__(parent)
        self._text = text
        self._icon = icon or QIcon()
        #: Name of an SVG in the icon set.  When set, the icon is re-rendered
        #: through the provider in the tab's own text colour, so it tracks the
        #: theme and the checked state the way the label beside it does; the
        #: QIcon above stays as the fallback for callers that pass a pixmap.
        self._icon_name: Optional[str] = None
        self._tinted_icon: Optional[QIcon] = None
        self._tinted_icon_key: tuple = ()
        self._badge_count: Any = 0
        self._badge_position: TabBadgePosition = badge_position
        self._is_hovered = False
        self._area: DockWidgetArea = DockWidgetArea.left  # Which sidebar this tab belongs to
        
        # --- Cached style values (overwritten by refresh_style) ---
        self._badge_color = QColor("#ff6b6b")
        self._badge_text_color = QColor(Qt.white)
        self._highlight_color = QColor(0, 122, 204)
        self._bg_active = QColor(45, 45, 45)
        self._bg_normal = None      # transparent unless a theme fills it
        self._bg_hover_start = QColor(60, 60, 60)
        self._bg_hover_end = QColor(45, 45, 45)
        self._text_active = QColor(Qt.white)
        self._text_normal = QColor(204, 204, 204)
        self._indicator_width = 3
        self._indicator_position = "left"  # "left" or "right"
        self._tab_corner_radius = 0.0
        self._tab_flat_edge = "all"
        self._border_normal = None
        self._border_active = None
        self._border_hover = None   # None follows _border_normal
        self._border_width = 0.0
        self._border_closed = False
        self._icon_size = DEFAULT_ICON_SIZE
        self._icon_gap = 8

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

    def set_icon_name(self, name: Optional[str]):
        """Draw this tab's icon from the icon set named *name*.

        Takes precedence over the QIcon passed to the constructor, which
        remains the fallback when the name resolves to nothing.
        """
        if name == self._icon_name:
            return
        self._icon_name = name or None
        self._tinted_icon = None
        self._tinted_icon_key = ()
        self.updateGeometry()
        self.update()

    def icon_name(self) -> Optional[str]:
        return self._icon_name

    def _resolved_icon(self) -> QIcon:
        """The icon to paint, tinted to match the label beside it.

        Sidebar tabs used to paint whatever QIcon they were handed, so a dark
        icon stayed dark on a dark theme while the text next to it turned
        light.  Named icons go through the provider in the tab's own
        active/normal text colour instead.
        """
        if not self._icon_name:
            return self._icon
        mgr = get_dock_style_manager()
        checked = self.isChecked()
        color = self._text_active if checked else self._text_normal
        key = (self._icon_name, checked, self._icon_size,
               color.name() if isinstance(color, QColor) else color,
               mgr.generation)
        if key == self._tinted_icon_key and self._tinted_icon is not None:
            return self._tinted_icon
        try:
            icon = get_icon_provider().get(
                self._icon_name,
                DockStyleCategory.SIDEBAR,
                active=checked,
                disabled=not self.isEnabled(),
                size=self._icon_size,
                color=color,
            )
        except (ValueError, RuntimeError):
            icon = QIcon()
        if icon.isNull():
            icon = self._icon
        self._tinted_icon = icon
        self._tinted_icon_key = key
        return icon

    def sizeHint(self) -> QSize:
        fm = QFontMetrics(self.font())
        text_w = fm.horizontalAdvance(self._text)
        icon_space = (self._icon_size + self._icon_gap
                      if not self._resolved_icon().isNull() else 0)
        pad = 22  # FIX: Increased padding slightly to prevent visual clipping
        
        return QSize(1, text_w + icon_space + pad)
    
    def minimumSizeHint(self) -> QSize:
        return self.sizeHint()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # 1+2. Background/hover + selection indicator + outline via the shared
        # paint_tab (the vertical sidebar indicator hugs a Left/Right edge).
        # One call for all three states: an idle tab's fill is transparent in
        # every shipped theme but it may still carry an outline, so the call
        # cannot be skipped on that branch.
        rect = QRectF(self.rect())
        radius, flat_edge, border_closed = self._tab_shape()
        checked = self.isChecked()
        # Normal / hover / active, the same triple the dock widget tabs use.
        # paint_tab skips a fully transparent fill, which is what tab_bg_normal
        # is until a theme sets it.
        gradient = None
        if checked:
            fill = self._bg_active
        elif self._is_hovered:
            fill, gradient = None, (self._bg_hover_start, self._bg_hover_end)
        else:
            fill = self._bg_normal
        paint_tab(
            p, rect,
            bg=fill,
            bg_gradient=gradient,
            radius=radius, flat_edge=flat_edge,
            indicator=self._highlight_color if checked else None,
            indicator_width=self._indicator_width,
            indicator_edge=self._indicator_edge(),
            border=self._border_color(checked, self._is_hovered),
            border_width=self._border_width,
            border_closed=border_closed,
        )

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
        icon = self._resolved_icon()
        icon_size = self._icon_size if not icon.isNull() else 0
        gap = self._icon_gap if icon_size > 0 else 0
        
        # Calculate the total width of the block to center it vertically
        total_content_w = icon_size + gap + text_w
        current_x = (r_width - total_content_w) / 2
        
        # Set text color based on state
        text_color = self._text_active if self.isChecked() else self._text_normal
        p.setPen(QPen(text_color))
        
        # Draw Icon
        if icon_size > 0:
            iy = (r_height - icon_size) / 2
            icon.paint(p, int(current_x), int(iy), icon_size, icon_size)
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

        ``indicator_position`` "left" = the window-facing edge, "right" = the
        one facing the docked content; on the right-hand sidebar the literal
        left/right of both flips.  (Preserves the pre-paint_tab mapping.)
        """
        is_right = self._area == DockWidgetArea.right
        if self._indicator_position == "right":
            return Qt.Edge.LeftEdge if is_right else Qt.Edge.RightEdge
        return Qt.Edge.RightEdge if is_right else Qt.Edge.LeftEdge

    def _tab_shape(self) -> tuple:
        """``(radius, flat_edge, border_closed)`` for the current ``tab_flat_edge``.

        Resolved per paint rather than cached in :meth:`refresh_style`: the
        flat side follows :attr:`_area`, which ``set_area`` can move after the
        style has been read.
        """
        outward = _OUTWARD_EDGE.get(self._area, Qt.Edge.LeftEdge)
        if self._tab_flat_edge == "none":
            # No flat edge, so nothing for the outline to leave open.
            return self._tab_corner_radius, None, True
        if self._tab_flat_edge == "inward":
            return self._tab_corner_radius, _OPPOSITE_EDGE[outward], self._border_closed
        if self._tab_flat_edge == "outward":
            return self._tab_corner_radius, outward, self._border_closed
        # "all" (and anything unrecognised): every corner square, and no one
        # edge singled out — so the outline, if any, runs the whole way round.
        return 0.0, outward, True

    def _border_color(self, checked: bool, hovered: bool = False) -> Optional[QColor]:
        """The outline this state paints, or ``None`` for no outline.

        A transparent colour means "no outline in this state", which is how a
        theme outlines only the active tab — the same contract the dock widget
        tabs' ``border_normal_color`` / ``border_active_color`` pair has.

        Checked wins over hovered, as in the fill above; and an *unset* hover
        colour is not the same as a transparent one — unset the hover is not a
        state of its own and keeps the inactive outline, which is what every
        theme without the token expects.
        """
        if checked:
            color = self._border_active
        elif hovered and self._border_hover is not None:
            color = self._border_hover
        else:
            color = self._border_normal
        return color if color is not None and color.alpha() > 0 else None

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
        # No `or` fallback like the lines around it: there is nothing to fall
        # back to. Transparent is the intended value and what every shipped
        # theme seeds this with, and paint_tab skips a zero-alpha fill.
        self._bg_normal = s.get("tab_bg_normal")
        self._bg_hover_start = s.get("tab_bg_hover_start") or self._bg_hover_start
        self._bg_hover_end = s.get("tab_bg_hover_end") or self._bg_hover_end
        self._text_active = s.get("tab_text_active") or self._text_active
        self._text_normal = s.get("tab_text_normal") or self._text_normal
        self._highlight_color = s.get("indicator_color") or self._highlight_color
        self._indicator_width = s.get("indicator_width", 3)
        self._indicator_position = s.get("indicator_position", "left")
        self._tab_flat_edge = s.get("tab_flat_edge") or "all"
        # An unset radius follows the dock widget tabs, so the two kinds of tab
        # are rounded alike unless the theme pins the sidebar's own value.
        radius = s.get("tab_corner_radius")
        if radius is None:
            radius = self._style_mgr.get(DockStyleCategory.TAB, "corner_radius", 0)
        self._tab_corner_radius = float(radius or 0)
        self._border_normal = s.get("tab_border_normal_color")
        self._border_active = s.get("tab_border_active_color")
        self._border_hover = s.get("tab_border_hover_color")
        self._border_width = float(s.get("tab_border_width") or 0.0)
        self._border_closed = bool(s.get("tab_border_closed", False))
        self._icon_size = int(s.get("tab_icon_size", DEFAULT_ICON_SIZE) or
                              DEFAULT_ICON_SIZE)
        self._icon_gap = int(s.get("tab_icon_gap", 8))
        # Drop the tint, not just the geometry: the icon is coloured from
        # tab_text_active / tab_text_normal, which this method has just
        # re-read, so a cached pixmap here is a pixmap in the old theme.
        self._tinted_icon = None
        self._tinted_icon_key = ()
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

