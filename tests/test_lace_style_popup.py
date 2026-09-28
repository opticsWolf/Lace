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
    # Rows clear the rounded corners.
    assert (style.pixelMetric(PM.PM_MenuVMargin, None, menu)
            == QStyleFactory.create("Fusion").pixelMetric(PM.PM_MenuVMargin, None, menu)
            + _popup.pad(style))


def test_square_controls_keep_square_popups(qapp):
    menu = _menu(LaceStyle(control_radius=0))
    assert not _popup.is_rounded(menu)
    assert not menu.testAttribute(WA.WA_TranslucentBackground)


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
    assert m.top() == before.top() + _popup.pad(style)
    assert m.bottom() == before.bottom() + _popup.pad(style)
    assert m.left() == before.left()
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


def test_a_rounded_menu_panel_leaves_its_corners_clear(qapp, themed):
    style = LaceStyle()
    img = _panel(style, themed, _menu(style))
    assert img.pixelColor(0, 0).alpha() == 0
    assert img.pixelColor(79, 59).alpha() == 0
    assert img.pixelColor(40, 30).alpha() == 255


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
    assert img.pixelColor(0, 0).alpha() == 0                # a clear corner
    assert img.pixelColor(50, 2).alpha() == 255             # the padding, filled
