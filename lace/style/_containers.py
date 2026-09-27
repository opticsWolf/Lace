# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


"""Phase 4b-4: tabs, group boxes, headers, menus, item views, tooltips, tool box.

Flat surfaces with one 1 px line where a separation is needed. Selection is
shown with the accent: an underline on the selected tab, a rounded highlight
on menu items. Labels, icons and all rects stay Fusion's -- where Fusion paints
a selection fill inside a label element, it is handed a transparent highlight
so only the flat fill drawn here shows.
"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPalette, QPen
from PySide6.QtWidgets import (
    QStyle, QStyleOptionHeader, QStyleOptionMenuItem, QStyleOptionTab, QTabBar,
)

from lace.style import _paint as P
from lace.style._primitives import frame

PE = QStyle.PrimitiveElement
CE = QStyle.ControlElement
State = QStyle.StateFlag
Role = QPalette.ColorRole
Shape = QTabBar.Shape

#: Selected tab's accent underline, px.
TAB_UNDERLINE = 2.0
#: Hover wash of item-view rows and unselected tabs: text over the surface.
HOVER_WASH = 0.06


def _enabled(opt) -> bool:
    return bool(opt.state & State.State_Enabled)


def _hovered(opt) -> bool:
    return bool(opt.state & State.State_MouseOver) and _enabled(opt)


def _line(style, opt, surface: QColor) -> QColor:
    return P.legible(opt, P.stroke(opt, surface, style.outline_strength), style.border_ratio)


def _hline(p, x1, x2, y, color):
    p.setPen(QPen(color, 1))
    p.drawLine(QPointF(x1, y + 0.5), QPointF(x2, y + 0.5))


def _vline(p, x, y1, y2, color):
    p.setPen(QPen(color, 1))
    p.drawLine(QPointF(x + 0.5, y1), QPointF(x + 0.5, y2))


def _base_without_highlight(style, element, opt, p, w):
    """Fusion's label drawing, minus its selection fill."""
    pal = QPalette(opt.palette)
    for g in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive, QPalette.ColorGroup.Disabled):
        pal.setColor(g, Role.Highlight, QColor(0, 0, 0, 0))
    saved = opt.palette
    opt.palette = pal
    try:
        style.baseStyle().drawControl(element, opt, p, w)
    finally:
        opt.palette = saved


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
def _pane_edge(shape) -> str:
    """Which edge of a tab faces its pane."""
    if shape in (Shape.RoundedSouth, Shape.TriangularSouth):
        return "top"
    if shape in (Shape.RoundedWest, Shape.TriangularWest):
        return "right"
    if shape in (Shape.RoundedEast, Shape.TriangularEast):
        return "left"
    return "bottom"


def tab_shape(style, opt, p, w):
    if not isinstance(opt, QStyleOptionTab):
        return False
    r = QRectF(opt.rect)
    edge = _pane_edge(opt.shape)
    selected = bool(opt.state & State.State_Selected)
    window = P.color(opt, Role.Window)
    with P.Painting(p):
        if selected or _hovered(opt):
            fill = window if selected else P.mix(window, P.color(opt, Role.Text), HOVER_WASH)
            # Round the corners away from the pane; square them where the tab meets it.
            radius = style.control_radius
            grow = {"bottom": (0, 0, 0, radius), "top": (0, -radius, 0, 0),
                    "right": (0, 0, radius, 0), "left": (-radius, 0, 0, 0)}[edge]
            p.setClipRect(r)
            P.rounded(p, r.adjusted(*grow), radius, fill=fill)
        if selected:
            bar = QRectF(r)
            u = TAB_UNDERLINE
            if edge == "bottom":
                bar.setTop(r.bottom() - u)
            elif edge == "top":
                bar.setBottom(r.top() + u)
            elif edge == "right":
                bar.setLeft(r.right() - u)
            else:
                bar.setRight(r.left() + u)
            accent = P.legible(opt, P.accent(opt), style.ui_ratio) if _enabled(opt) else \
                P.mix(window, P.accent(opt), 0.4)
            p.fillRect(bar, accent)
    return True


def tab_bar_base(style, opt, p, w):
    """The line under a tab bar that runs on past the last tab."""
    r = opt.rect
    color = _line(style, opt, P.color(opt, Role.Window))
    with P.Painting(p):
        p.setRenderHint(p.RenderHint.Antialiasing, False)
        edge = _pane_edge(getattr(opt, "shape", Shape.RoundedNorth))
        if edge == "bottom":
            _hline(p, r.left(), r.right(), r.bottom(), color)
        elif edge == "top":
            _hline(p, r.left(), r.right(), r.top(), color)
        elif edge == "right":
            _vline(p, r.right(), r.top(), r.bottom(), color)
        else:
            _vline(p, r.left(), r.top(), r.bottom(), color)
    return True


# ---------------------------------------------------------------------------
# Headers
# ---------------------------------------------------------------------------
def header_section(style, opt, p, w):
    if not isinstance(opt, QStyleOptionHeader):
        return False
    r = opt.rect
    fill = P.color(opt, Role.Button)
    if _hovered(opt) or opt.state & State.State_Sunken:
        fill = P.state_fill(opt, fill)
    line = _line(style, opt, fill)
    p.save()
    p.fillRect(r, fill)
    horizontal = opt.orientation == Qt.Orientation.Horizontal
    _hline(p, r.left(), r.right(), r.bottom(), line)
    if horizontal:
        # Separator at the trailing edge, inset so sections read as one strip.
        _vline(p, r.right(), r.top() + 4, r.bottom() - 4, line)
    else:
        _vline(p, r.right(), r.top(), r.bottom(), line)
    p.restore()
    return True


def header_arrow(style, opt, p, w):
    if not isinstance(opt, QStyleOptionHeader):
        return False
    up = opt.sortIndicator == QStyleOptionHeader.SortIndicator.SortUp
    with P.Painting(p):
        P.chevron(p, QRectF(opt.rect), "up" if up else "down",
                  P.legible(opt, P.color(opt, Role.ButtonText), style.ui_ratio,
                            P.color(opt, Role.Button)))
    return True


# ---------------------------------------------------------------------------
# Menus and menu bar
# ---------------------------------------------------------------------------
def panel_menu(style, opt, p, w):
    """Menu popups are plain rectangles: a flat fill and a 1 px line."""
    fill = P.color(opt, Role.Window)
    p.save()
    p.fillRect(opt.rect, fill)
    p.setPen(QPen(_line(style, opt, fill), 1))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(opt.rect.adjusted(0, 0, -1, -1))
    p.restore()
    return True


def _selection(style, opt, p, rect: QRectF, radius: float):
    with P.Painting(p):
        P.rounded(p, rect, radius, fill=P.color(opt, Role.Highlight))


def menu_item(style, opt, p, w):
    if not isinstance(opt, QStyleOptionMenuItem):
        return False
    if opt.menuItemType == QStyleOptionMenuItem.MenuItemType.Separator:
        y = opt.rect.center().y()
        p.save()
        _hline(p, opt.rect.left() + 6, opt.rect.right() - 6, y, _line(style, opt, P.color(opt, Role.Window)))
        p.restore()
        return True
    if opt.state & State.State_Selected and _enabled(opt):
        _selection(style, opt, p, QRectF(opt.rect).adjusted(3, 1, -3, -1), style.control_radius)
    _base_without_highlight(style, CE.CE_MenuItem, opt, p, w)
    return True


def menu_bar_item(style, opt, p, w):
    if not isinstance(opt, QStyleOptionMenuItem):
        return False
    # Fusion fills the item's background, which would cover a selection drawn
    # first, so the label is drawn here.
    active = bool(opt.state & State.State_Selected and opt.state & (State.State_Sunken | State.State_MouseOver)
                  and _enabled(opt))
    p.fillRect(opt.rect, P.color(opt, Role.Window))
    if active:
        _selection(style, opt, p, QRectF(opt.rect).adjusted(1, 2, -1, -2), style.control_radius)
    align = Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextShowMnemonic | Qt.TextFlag.TextDontClip
    if not style.styleHint(QStyle.StyleHint.SH_UnderlineShortcut, opt, w):
        align |= Qt.TextFlag.TextHideMnemonic
    style.drawItemText(p, opt.rect, int(align), opt.palette, _enabled(opt), opt.text,
                       Role.HighlightedText if active else Role.ButtonText)
    return True


def menu_bar_empty(style, opt, p, w):
    p.fillRect(opt.rect, P.color(opt, Role.Window))
    return True


# ---------------------------------------------------------------------------
# Item views, tooltips, tool box
# ---------------------------------------------------------------------------
def item_view_item(style, opt, p, w):
    """Flat selection; a faint wash on hover. Rows stay square so columns join."""
    base = P.color(opt, Role.Base)
    if opt.state & State.State_Selected:
        fill = P.color(opt, Role.Highlight)
    elif _hovered(opt):
        fill = P.mix(base, P.color(opt, Role.Text), HOVER_WASH)
    else:
        bg = getattr(opt, "backgroundBrush", None)
        if bg is not None and bg.style() != Qt.BrushStyle.NoBrush:
            p.fillRect(opt.rect, bg)
        return True
    p.fillRect(opt.rect, fill)
    return True


def tooltip(style, opt, p, w):
    fill = P.color(opt, Role.ToolTipBase)
    p.save()
    p.fillRect(opt.rect, fill)
    p.setPen(QPen(_line(style, opt, fill), 1))
    p.drawRect(opt.rect.adjusted(0, 0, -1, -1))
    p.restore()
    return True


def tool_box_tab(style, opt, p, w):
    fill = P.color(opt, Role.Button)
    if _hovered(opt) or opt.state & State.State_Sunken:
        fill = P.state_fill(opt, fill)
    with P.Painting(p):
        P.rounded(p, P.half_pixel(opt.rect), style.control_radius, fill=fill, line=_line(style, opt, fill))
    return True


PRIMITIVES = {
    PE.PE_FrameTabWidget: frame,
    PE.PE_FrameTabBarBase: tab_bar_base,
    PE.PE_FrameGroupBox: frame,
    PE.PE_IndicatorHeaderArrow: header_arrow,
    PE.PE_PanelMenu: panel_menu,
    PE.PE_PanelItemViewItem: item_view_item,
    PE.PE_PanelTipLabel: tooltip,
}

CONTROLS = {
    CE.CE_TabBarTabShape: tab_shape,
    CE.CE_HeaderSection: header_section,
    CE.CE_MenuItem: menu_item,
    CE.CE_MenuBarItem: menu_bar_item,
    CE.CE_MenuBarEmptyArea: menu_bar_empty,
    CE.CE_ToolBoxTabShape: tool_box_tab,
}
