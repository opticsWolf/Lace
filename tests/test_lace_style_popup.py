# -*- coding: utf-8 -*-
"""LaceStyle rounds menus and combo box popups: the window turns translucent
and frameless before it exists, and the panel paints a rounded fill."""

import pytest
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QComboBox, QMenu, QStyle, QStyleFactory, QStyleOptionMenuItem

from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import build_dock_palette, resolve_dock_colors
from lace.lace_style import LaceStyle
from lace.style import _popup
from tests.theme_sets import load

WA = Qt.WidgetAttribute
WT = Qt.WindowType
PE = QStyle.PrimitiveElement
PM = QStyle.PixelMetric


@pytest.fixture
def themed(qapp):
    get_dock_style_manager().apply_theme_dict(load("kilim_dark"))
    return build_dock_palette(is_panel=False, colors=resolve_dock_colors())


def _menu(style):
    menu = QMenu()
    menu.addAction("Open")
    menu.setStyle(style)
    menu.ensurePolished()
    return menu


def _combo_popup(style):
    combo = QComboBox()
    combo.addItems(["a", "b"])
    combo.setStyle(style)
    popup = combo.view().window()
    popup.setStyle(style)
    popup.ensurePolished()
    return combo, popup


def test_a_menu_becomes_a_translucent_frameless_window(qapp):
    style = LaceStyle()
    menu = _menu(style)
    assert _popup.is_rounded(menu)
    assert menu.testAttribute(WA.WA_TranslucentBackground)
    assert menu.windowFlags() & WT.FramelessWindowHint      # Windows needs it to composite
    assert menu.windowFlags() & WT.NoDropShadowWindowHint   # the native shadow is square
    # Room for the shadow all round, and rows that clear the rounded corners.
    fusion = QStyleFactory.create("Fusion")
    assert (style.pixelMetric(PM.PM_MenuHMargin, None, menu)
            == fusion.pixelMetric(PM.PM_MenuHMargin, None, menu) + _popup.SHADOW)
    assert (style.pixelMetric(PM.PM_MenuVMargin, None, menu)
            == fusion.pixelMetric(PM.PM_MenuVMargin, None, menu) + _popup.SHADOW + _popup.pad(style))


def test_square_controls_keep_square_popups(qapp):
    menu = _menu(LaceStyle(control_radius=0))
    assert not _popup.is_rounded(menu)
    assert not menu.testAttribute(WA.WA_TranslucentBackground)


@pytest.mark.parametrize("control, corner, expected", [
    (4, 4, 4),      # classic chassis
    (4, 10, 6),     # neo chassis
    (6, 12, 8),
    (4, 0, 4),      # square cards: never less round than the controls
    (0, 10, 0),     # square controls: square popups
])
def test_popup_radius_sits_a_third_of_the_way_to_the_cards(qapp, control, corner, expected):
    assert _popup.radius(LaceStyle(control_radius=control, corner_radius=corner)) == expected


@pytest.mark.parametrize("neo, expected", [(False, 4), (True, 6)])
def test_basic_themes_menu_radius(qapp, neo, expected):
    """Every classic basic theme gets 4 px menus, every neo one 6 px, through
    the tokens the theme bridge hands LaceStyle."""
    from lace.dock_custom_theme import _BASIC_PALETTES
    from lace.dock_theme import DockStyleCategory as C

    sm = get_dock_style_manager()
    for name in _BASIC_PALETTES:
        sm.apply_theme(f"{name}_neo" if neo else name)
        style = LaceStyle(control_radius=sm.get(C.CORE, "control_radius", 4),
                          corner_radius=sm.get(C.CORE, "corner_radius", 4))
        assert _popup.radius(style) == expected, name


def test_an_apps_own_translucent_popup_is_left_alone(qapp):
    menu = QMenu()
    menu.setAttribute(WA.WA_TranslucentBackground)
    menu.setStyle(LaceStyle())
    menu.ensurePolished()
    assert not _popup.is_rounded(menu)
    assert not menu.windowFlags() & WT.NoDropShadowWindowHint


def test_leaving_lace_style_restores_the_window(qapp):
    menu = _menu(LaceStyle())
    menu.setStyle(QStyleFactory.create("Fusion"))
    assert not _popup.is_rounded(menu)
    assert not menu.testAttribute(WA.WA_TranslucentBackground)
    assert not menu.windowFlags() & WT.FramelessWindowHint
    assert not menu.windowFlags() & WT.NoDropShadowWindowHint


def test_a_combo_popup_is_padded_and_restored(qapp):
    fusion = QStyleFactory.create("Fusion")
    _, plain = _combo_popup(fusion)
    before = plain.contentsMargins()
    style = LaceStyle()
    _, popup = _combo_popup(style)
    assert _popup.is_rounded(popup)
    m = popup.contentsMargins()
    ends = _popup.SHADOW + _popup.pad(style)
    assert m.top() == before.top() + ends
    assert m.bottom() == before.bottom() + ends
    assert m.left() == before.left() + _popup.SHADOW
    assert m.right() == before.right() + _popup.SHADOW
    popup.setStyle(fusion)
    assert popup.contentsMargins() == before


def _panel(style, palette, menu):
    opt = QStyleOptionMenuItem()
    opt.initFrom(menu)
    opt.palette = palette
    opt.rect = QRect(0, 0, 80, 60)
    img = QImage(80, 60, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    p = QPainter(img)
    style.drawPrimitive(PE.PE_PanelMenu, opt, p, menu)
    style.drawPrimitive(PE.PE_FrameMenu, opt, p, menu)
    p.end()
    return img


def test_a_rounded_menu_panel_sits_on_a_soft_shadow(qapp, themed):
    style = LaceStyle()
    img = _panel(style, themed, _menu(style))
    s = _popup.SHADOW
    assert img.pixelColor(40, 30).alpha() == 255            # the panel
    assert img.pixelColor(s, s).alpha() < 255               # outside its rounded corner
    below = [img.pixelColor(40, 59 - s + d).alpha() for d in range(1, s)]
    assert below[0] > 0 and below == sorted(below, reverse=True)    # fades outwards
    assert img.pixelColor(0, 0).alpha() < 20                # nearly clear at the edge


def test_a_square_menu_panel_fills_its_corners(qapp, themed):
    style = LaceStyle(control_radius=0)
    img = _panel(style, themed, _menu(style))
    assert img.pixelColor(0, 0).alpha() == 255


@pytest.mark.parametrize("editable", [False, True], ids=["plain", "editable"])
def test_a_combo_popup_fills_its_padding(qapp, themed, editable):
    """The frame rect leaves the padding out; the popup still fills it."""
    style = LaceStyle()
    combo = QComboBox()
    combo.setEditable(editable)
    combo.addItems(["a", "b"])
    combo.setStyle(style)
    popup = combo.view().window()
    popup.setStyle(style)
    popup.ensurePolished()
    popup.setPalette(themed)
    popup.resize(100, 60)
    img = QImage(100, 60, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    popup.render(img)
    s = _popup.SHADOW
    assert img.pixelColor(0, 0).alpha() < 20                # the shadow's faint edge
    assert img.pixelColor(50, s + 2).alpha() == 255         # the padding, filled


@pytest.mark.parametrize("editable", [False, True], ids=["plain", "editable"])
def test_a_combo_popups_padding_matches_its_rows(qapp, themed, editable):
    """A plain combo draws menu rows, an editable one list rows: the padding
    above and below them takes the same colour."""
    style = LaceStyle()
    combo = QComboBox()
    combo.setEditable(editable)
    combo.addItems(["alpha", "beta", "gamma"])
    combo.setStyle(style)
    combo.setPalette(themed)
    popup = combo.view().window()
    popup.setStyle(style)
    popup.setPalette(themed)
    popup.ensurePolished()
    popup.resize(160, 120)
    popup.layout().activate()
    img = QImage(160, 120, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    popup.render(img)
    view = combo.view()
    row = view.visualRect(combo.model().index(1, 0))       # an unselected row
    spot = view.mapTo(popup, row.center())
    spot.setX(popup.width() - _popup.SHADOW - 12)          # right of the text
    padding = img.pixelColor(spot.x(), _popup.SHADOW + 2)
    assert padding == img.pixelColor(spot)


def test_a_shown_menu_puts_its_panel_on_the_anchor(qapp):
    """The window grows by the shadow; showing moves it back by as much."""
    from PySide6.QtCore import QPoint
    menu = _menu(LaceStyle())
    at = QPoint(200, 150)
    menu.popup(at)
    try:
        assert menu.geometry().topLeft() == at - QPoint(_popup.SHADOW, _popup.SHADOW)
    finally:
        menu.hide()
