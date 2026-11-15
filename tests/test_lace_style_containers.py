# -*- coding: utf-8 -*-
"""LaceStyle 4b-4, containers: flat surfaces, accent selection and neutral
hover on tabs, rounded highlight on menu items, bare ticks in menus."""

import pytest
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QImage, QPainter, QPalette
from PySide6.QtWidgets import (
    QMenu, QStyle, QStyleOptionButton, QStyleOptionHeader, QStyleOptionMenuItem, QStyleOptionTab,
    QStyleOptionViewItem, QTabBar,
)

from lace import color_science as cs
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import build_dock_palette, resolve_dock_colors
from lace.lace_style import LaceStyle
from lace.style import _paint as P
from lace.style._containers import (TAB_ACTIVE_HOVER_WASH, TAB_ACTIVE_WASH,
                                    TAB_HOVER_STEP)
from tests.theme_sets import load

S = QStyle.StateFlag
CE = QStyle.ControlElement
W, H = 100, 26
G = QPalette.ColorGroup.Active


def _palette(theme_key="kilim_dark"):
    get_dock_style_manager().apply_theme_dict(load(theme_key))
    return build_dock_palette(is_panel=False, colors=resolve_dock_colors())


def _rgb(c):
    if isinstance(c, (list, tuple)):
        return list(c[:3])
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


def test_selected_tab_fills_with_the_accent_wash(qapp):
    pal = _palette()
    opt = QStyleOptionTab()
    opt.rect, opt.palette, opt.state = QRect(0, 0, W, H), pal, _state(S.State_Selected)
    img = _draw(lambda o, p, w: LaceStyle().drawControl(CE.CE_TabBarTabShape, o, p, w), opt)
    window = pal.color(G, QPalette.ColorRole.Window)
    accent = pal.color(G, QPalette.ColorRole.Accent)
    expected = cs.mix(_rgb(window), _rgb(accent), TAB_ACTIVE_WASH)
    assert _rgb(img.pixelColor(W // 2, H // 2)) == _rgb(expected)


def test_hovered_tab_gets_a_neutral_tint_lighter_than_a_selected_one(qapp):
    pal = _palette()

    def tab(state):
        opt = QStyleOptionTab()
        opt.rect, opt.palette, opt.state = QRect(0, 0, W, H), pal, _state(state)
        img = _draw(lambda o, p, w: LaceStyle().drawControl(CE.CE_TabBarTabShape, o, p, w), opt)
        return img.pixelColor(W // 2, H // 2)

    hovered = tab(S.State_MouseOver)
    selected = tab(S.State_Selected)
    window = pal.color(G, QPalette.ColorRole.Window)
    accent = pal.color(G, QPalette.ColorRole.Accent)
    assert _rgb(hovered) == _rgb(P.step(window, TAB_HOVER_STEP))
    assert _rgb(hovered) != _rgb(cs.mix(_rgb(window), _rgb(accent), TAB_ACTIVE_WASH))
    assert cs.delta_e(_rgb(selected), _rgb(window)) > cs.delta_e(_rgb(hovered), _rgb(window))


class _PointerBar(QTabBar):
    """A tab bar whose pointer position is fixed for a paint test."""

    def __init__(self, point):
        super().__init__()
        self.point = point

    def underMouse(self):
        return True

    def mapFromGlobal(self, _pos):
        return self.point


def test_tab_hover_falls_back_to_the_tab_bar_pointer(qapp):
    """QTabBar does not set State_MouseOver; the pointer position must."""
    pal = _palette()
    opt = QStyleOptionTab()
    opt.rect, opt.palette, opt.state = QRect(0, 0, W, H), pal, _state()
    bar = _PointerBar(QPoint(W // 2, H // 2))
    img = _draw(lambda o, p, w: LaceStyle().drawControl(CE.CE_TabBarTabShape, o, p, w), opt, bar)
    window = pal.color(G, QPalette.ColorRole.Window)
    accent = pal.color(G, QPalette.ColorRole.Accent)
    assert _rgb(img.pixelColor(W // 2, H // 2)) == _rgb(P.step(window, TAB_HOVER_STEP))


def test_stale_hover_state_does_not_keep_the_previous_tab_hovered(qapp):
    """Moving straight from tab to tab must not leave the old fill behind."""
    pal = _palette()
    left = QStyleOptionTab()
    left.rect, left.palette, left.state = QRect(0, 0, W, H), pal, _state(S.State_MouseOver)
    left_img = _draw(lambda o, p, w: LaceStyle().drawControl(CE.CE_TabBarTabShape, o, p, w),
                     left, _PointerBar(QPoint(W + 5, H + 5)))
    assert left_img.pixelColor(W // 2, H // 2).alpha() == 0

    right = QStyleOptionTab()
    right.rect, right.palette, right.state = QRect(0, 0, W, H), pal, _state()
    right_img = _draw(lambda o, p, w: LaceStyle().drawControl(CE.CE_TabBarTabShape, o, p, w),
                      right, _PointerBar(QPoint(W // 2, H // 2)))
    assert _rgb(right_img.pixelColor(W // 2, H // 2)) == _rgb(
        P.step(pal.color(G, QPalette.ColorRole.Window), TAB_HOVER_STEP))


def test_selected_tab_tints_more_while_hovered(qapp):
    pal = _palette()
    opt = QStyleOptionTab()
    opt.rect, opt.palette, opt.state = QRect(0, 0, W, H), pal, _state(S.State_Selected)
    bar = _PointerBar(QPoint(W // 2, H // 2))
    img = _draw(lambda o, p, w: LaceStyle().drawControl(CE.CE_TabBarTabShape, o, p, w), opt, bar)
    window = pal.color(G, QPalette.ColorRole.Window)
    accent = pal.color(G, QPalette.ColorRole.Accent)
    assert _rgb(img.pixelColor(W // 2, H // 2)) == _rgb(
        cs.mix(_rgb(window), _rgb(accent), TAB_ACTIVE_HOVER_WASH))


def test_selected_tab_away_from_the_pointer_uses_the_resting_wash(qapp):
    pal = _palette()
    opt = QStyleOptionTab()
    opt.rect, opt.palette, opt.state = QRect(0, 0, W, H), pal, _state(S.State_Selected)
    bar = _PointerBar(QPoint(W + 5, H + 5))
    img = _draw(lambda o, p, w: LaceStyle().drawControl(CE.CE_TabBarTabShape, o, p, w), opt, bar)
    window = pal.color(G, QPalette.ColorRole.Window)
    accent = pal.color(G, QPalette.ColorRole.Accent)
    assert _rgb(img.pixelColor(W // 2, H // 2)) == _rgb(
        cs.mix(_rgb(window), _rgb(accent), TAB_ACTIVE_WASH))


def test_focused_tab_label_has_no_tinted_box(qapp):
    """Fusion paints its own focus box in the tab label; only our ring remains."""
    pal = _palette("kilim_light_neo")
    opt = QStyleOptionTab()
    opt.rect, opt.palette, opt.text = QRect(0, 0, W, H), pal, ""
    opt.state = _state(S.State_HasFocus)   # mouse focus: nothing at all
    img = _draw(lambda o, p, w: LaceStyle().drawControl(CE.CE_TabBarTabLabel, o, p, w), opt)
    assert {img.pixelColor(x, y).alpha() for x in range(W) for y in range(H)} == {0}
    opt.state |= S.State_KeyboardFocusChange   # keyboard: a ring, hollow inside
    img = _draw(lambda o, p, w: LaceStyle().drawControl(CE.CE_TabBarTabLabel, o, p, w), opt)
    assert img.pixelColor(W // 2, 3).alpha() > 0 and img.pixelColor(W // 2, H // 2).alpha() == 0


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


def _separator(pal, text):
    opt = QStyleOptionMenuItem()
    opt.rect, opt.palette, opt.state = QRect(0, 0, W, H), pal, _state()
    opt.menuItemType, opt.text = QStyleOptionMenuItem.MenuItemType.Separator, text
    return opt


def _inked_columns(img):
    return [x for x in range(W) if any(img.pixelColor(x, y).alpha() for y in range(H))]


def test_menu_section_header_shows_its_title(qapp):
    """``QMenu.addSection``: the title at the start, the line after it."""
    pal = _palette()
    style = LaceStyle()
    draw = lambda o, p, w: style.drawControl(CE.CE_MenuItem, o, p, w)   # noqa: E731
    line = _draw(draw, _separator(pal, ""), QMenu())
    section = _draw(draw, _separator(pal, "Sec"), QMenu())
    # A bare separator is one row of pixels; the title has height.
    (row,) = {y for y in range(H) if line.pixelColor(W // 2, y).alpha()}
    start = _inked_columns(section)[0]
    assert any(section.pixelColor(start + dx, y).alpha()
               for dx in range(3) for y in range(H) if y != row)
    assert section.pixelColor(W - 10, row).alpha()   # the line runs on after the title


def test_menu_section_header_has_room_for_its_title(qapp):
    menu = QMenu()
    menu.setStyle(LaceStyle())
    menu.addAction("x")
    section = menu.addSection("A section title much wider than its items")
    menu.addAction("y")
    line = menu.addSeparator()      # between items: QMenu collapses bare ones at the ends
    menu.addAction("z")
    menu.sizeHint()                 # lays out the action rects
    title = menu.fontMetrics().horizontalAdvance(section.text())
    assert menu.actionGeometry(section).width() > title
    assert menu.actionGeometry(section).height() > menu.fontMetrics().height()
    assert menu.actionGeometry(line).height() < menu.fontMetrics().height()


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


@pytest.mark.parametrize("radius", [0, 4])
def test_tooltip_window_takes_the_rounded_shape(qapp, radius):
    """The tip window is masked to its corners; 0 keeps it square."""
    from PySide6.QtWidgets import QStyleOption, QWidget
    tip = QWidget(None, Qt.WindowType.ToolTip)
    tip.resize(W, H)
    opt = QStyleOption()
    opt.initFrom(tip)
    opt.palette = _palette()
    img = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(img)
    LaceStyle(control_radius=radius).drawPrimitive(QStyle.PrimitiveElement.PE_PanelTipLabel, opt, p, tip)
    p.end()
    mask = tip.mask()
    assert mask.contains(QRect(W // 2, H // 2, 1, 1).topLeft())
    assert mask.contains(QRect(0, 0, 1, 1).topLeft()) == (radius == 0)


def test_item_view_selection_is_flat_highlight(qapp):
    pal = _palette()
    opt = QStyleOptionViewItem()
    opt.rect, opt.palette, opt.state = QRect(0, 0, W, H), pal, _state(S.State_Selected)
    img = _draw(lambda o, p, w: LaceStyle().drawPrimitive(
        QStyle.PrimitiveElement.PE_PanelItemViewItem, o, p, w), opt)
    assert {img.pixelColor(x, y).rgba() for x in range(W) for y in range(H)} == \
        {pal.color(G, QPalette.ColorRole.Highlight).rgba()}
