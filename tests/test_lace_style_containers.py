# -*- coding: utf-8 -*-
"""LaceStyle 4b-4, containers: flat surfaces, accent underline on the selected
tab, rounded highlight on menu items, bare ticks in menus."""

import pytest
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QImage, QPainter, QPalette
from PySide6.QtWidgets import (
    QMenu, QStyle, QStyleOptionButton, QStyleOptionHeader, QStyleOptionMenuItem, QStyleOptionTab,
    QStyleOptionViewItem, QTabBar,
)

from lace import color_science as cs
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import build_dock_palette, resolve_dock_colors
from lace.lace_style import LaceStyle
from tests.theme_sets import load

S = QStyle.StateFlag
CE = QStyle.ControlElement
W, H = 100, 26
G = QPalette.ColorGroup.Active


def _palette(theme_key="kilim_dark"):
    get_dock_style_manager().apply_theme_dict(load(theme_key))
    return build_dock_palette(is_panel=False, colors=resolve_dock_colors())


def _rgb(c):
    return [c.red(), c.green(), c.blue()]


def _state(extra=S.State_None):
    return S.State_Enabled | S.State_Active | extra


def _draw(fn, opt, w=None):
    img = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    p = QPainter(img)
    fn(opt, p, w)
    p.end()
    return img


def _near(a, b) -> bool:
    return cs.contrast_ratio(_rgb(a), _rgb(b)) < 1.05


@pytest.mark.parametrize("shape, edge", [
    (QTabBar.Shape.RoundedNorth, "bottom"), (QTabBar.Shape.RoundedSouth, "top"),
    (QTabBar.Shape.RoundedWest, "right"), (QTabBar.Shape.RoundedEast, "left"),
])
def test_selected_tab_underlines_the_pane_edge(qapp, shape, edge):
    pal = _palette()
    opt = QStyleOptionTab()
    opt.rect, opt.palette, opt.state, opt.shape = QRect(0, 0, W, H), pal, _state(S.State_Selected), shape
    img = _draw(lambda o, p, w: LaceStyle().drawControl(CE.CE_TabBarTabShape, o, p, w), opt)
    at = {"bottom": (W // 2, H - 1), "top": (W // 2, 0), "right": (W - 1, H // 2), "left": (0, H // 2)}[edge]
    far = {"bottom": (W // 2, 0), "top": (W // 2, H - 1), "right": (0, H // 2), "left": (W - 1, H // 2)}[edge]
    accent = pal.color(G, QPalette.ColorRole.Accent)
    assert cs.contrast_ratio(_rgb(img.pixelColor(*at)), _rgb(accent)) < \
        cs.contrast_ratio(_rgb(img.pixelColor(*far)), _rgb(accent))


def test_unselected_tab_at_rest_is_bare(qapp):
    opt = QStyleOptionTab()
    opt.rect, opt.palette, opt.state = QRect(0, 0, W, H), _palette(), _state()
    img = _draw(lambda o, p, w: LaceStyle().drawControl(CE.CE_TabBarTabShape, o, p, w), opt)
    assert {img.pixelColor(x, y).alpha() for x in range(W) for y in range(H)} == {0}


def test_header_section_is_flat(qapp):
    pal = _palette()
    opt = QStyleOptionHeader()
    opt.rect, opt.palette, opt.state = QRect(0, 0, W, H), pal, _state()
    opt.orientation = Qt.Orientation.Horizontal
    img = _draw(lambda o, p, w: LaceStyle().drawControl(CE.CE_HeaderSection, o, p, w), opt)
    inner = {img.pixelColor(W // 2, y).rgba() for y in range(1, H - 2)}
    assert inner == {pal.color(G, QPalette.ColorRole.Button).rgba()}


def test_selected_menu_item_is_rounded_highlight(qapp):
    pal = _palette()
    opt = QStyleOptionMenuItem()
    opt.rect, opt.palette, opt.state = QRect(0, 0, W, H), pal, _state(S.State_Selected)
    opt.menuItemType, opt.text = QStyleOptionMenuItem.MenuItemType.Normal, ""
    img = _draw(lambda o, p, w: LaceStyle().drawControl(CE.CE_MenuItem, o, p, w), opt, QMenu())
    highlight = pal.color(G, QPalette.ColorRole.Highlight)
    assert _near(img.pixelColor(W // 2, H // 2), highlight)
    assert not _near(img.pixelColor(3, 1), highlight)   # rounded corner


def test_menu_bar_item_shows_selection(qapp):
    pal = _palette()
    opt = QStyleOptionMenuItem()
    opt.rect, opt.palette = QRect(0, 0, W, H), pal
    opt.state = _state(S.State_Selected | S.State_MouseOver)
    opt.menuItemType, opt.text = QStyleOptionMenuItem.MenuItemType.Normal, ""
    img = _draw(lambda o, p, w: LaceStyle().drawControl(CE.CE_MenuBarItem, o, p, w), opt)
    assert _near(img.pixelColor(W // 2, H // 2), pal.color(G, QPalette.ColorRole.Highlight))


@pytest.mark.parametrize("element", [QStyle.PrimitiveElement.PE_IndicatorCheckBox,
                                     QStyle.PrimitiveElement.PE_IndicatorRadioButton])
def test_menu_checks_are_bare(qapp, element):
    """In a menu, an unchecked item draws nothing and a checked one no box."""
    pal = _palette()
    style = LaceStyle()

    def draw(on):
        opt = QStyleOptionButton()
        opt.rect, opt.palette = QRect(0, 0, 16, 16), pal
        opt.state = _state(S.State_On if on else S.State_Off)
        return _draw(lambda o, p, w: style.drawPrimitive(element, o, p, w), opt, QMenu())
    off, on = draw(False), draw(True)
    assert {off.pixelColor(x, y).alpha() for x in range(16) for y in range(16)} == {0}
    assert on.pixelColor(1, 8).alpha() == 0 and on.pixelColor(8, 1).alpha() == 0


def test_item_view_selection_is_flat_highlight(qapp):
    pal = _palette()
    opt = QStyleOptionViewItem()
    opt.rect, opt.palette, opt.state = QRect(0, 0, W, H), pal, _state(S.State_Selected)
    img = _draw(lambda o, p, w: LaceStyle().drawPrimitive(
        QStyle.PrimitiveElement.PE_PanelItemViewItem, o, p, w), opt)
    assert {img.pixelColor(x, y).rgba() for x in range(W) for y in range(H)} == \
        {pal.color(G, QPalette.ColorRole.Highlight).rgba()}
