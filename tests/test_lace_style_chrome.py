# -*- coding: utf-8 -*-
"""LaceStyle chrome: splitter grips, tab close buttons, QFrame lines and
boxes, dials, toolbar handles and separators, size grips, and the calendar's
weekend colour."""

import pytest
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QImage, QPainter, QPalette
from PySide6.QtWidgets import (
    QCalendarWidget, QDial, QFrame, QSplitter, QStyle, QStyleFactory, QStyleOption,
    QStyleOptionFrame, QStyleOptionSizeGrip, QTextEdit,
)

from lace import color_science as cs
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import build_dock_palette, resolve_dock_colors
from lace.lace_style import LaceStyle
from lace.style import _chrome
from tests.theme_sets import load

S = QStyle.StateFlag
PE = QStyle.PrimitiveElement
CE = QStyle.ControlElement


@pytest.fixture
def themed(qapp):
    get_dock_style_manager().apply_theme_dict(load("kilim_dark"))
    return build_dock_palette(is_panel=False, colors=resolve_dock_colors())


def _paint(draw, w, h):
    img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    p = QPainter(img)
    draw(p)
    p.end()
    return img


def _option(cls, palette, rect, state=S(0)):
    opt = cls()
    opt.rect = rect
    opt.palette = palette
    opt.state = S.State_Enabled | S.State_Active | state
    return opt


def _painted(img, x, y) -> bool:
    return img.pixelColor(x, y).alpha() > 60


def _ratio(fg, bg) -> float:
    return cs.contrast_ratio([fg.red(), fg.green(), fg.blue(), 255],
                             [bg.red(), bg.green(), bg.blue()])


# ---------------------------------------------------------------------------
# Splitter
# ---------------------------------------------------------------------------
def _grip(style, palette, state=S(0), size=(12, 100)):
    w, h = size
    opt = _option(QStyleOption, palette, QRect(0, 0, w, h), S.State_Horizontal | state)
    img = _paint(lambda p: style.drawControl(CE.CE_Splitter, opt, p, None), w, h)
    thick = sum(_painted(img, x, h // 2) for x in range(w))
    length = sum(_painted(img, w // 2, y) for y in range(h))
    return img, thick, length


def test_splitter_handle_leaves_room_around_the_grip(qapp):
    style = LaceStyle()
    width = style.pixelMetric(QStyle.PixelMetric.PM_SplitterWidth)
    assert width == _chrome.SPLITTER_GRIP + _chrome.SPLITTER_GROW + 2 * _chrome.SPLITTER_PAD
    split = QSplitter()
    split.setStyle(style)
    split.addWidget(QTextEdit())
    split.addWidget(QTextEdit())
    assert split.handleWidth() == width
    split.show()
    # Hover reaches the handle (Fusion enables it), so the grip can grow.
    assert split.handle(1).testAttribute(Qt.WidgetAttribute.WA_Hover)
    split.hide()


def test_splitter_grip_is_faint_and_grows_accented_on_hover(qapp, themed):
    style = LaceStyle()
    img, thick, length = _grip(style, themed)
    assert thick == _chrome.SPLITTER_GRIP
    assert abs(length - 50) <= 1
    hover_img, hover_thick, _ = _grip(style, themed, S.State_MouseOver)
    assert hover_thick == _chrome.SPLITTER_GRIP + _chrome.SPLITTER_GROW
    _, drag_thick, _ = _grip(style, themed, S.State_Sunken)
    assert drag_thick == hover_thick
    window = themed.color(QPalette.ColorRole.Window)
    rest = img.pixelColor(6, 50)
    hover = hover_img.pixelColor(6, 50)
    # Faint at rest; the accent (held to the ui floor) on hover.
    assert _ratio(rest, window) < _ratio(hover, window)
    assert _ratio(hover, window) >= style.ui_ratio - 0.05


def test_splitter_length_token(qapp, themed):
    _, _, length = _grip(LaceStyle(splitter_length=30), themed)
    assert abs(length - 30) <= 1
    # Never longer than the handle.
    _, _, clipped = _grip(LaceStyle(splitter_length=500), themed, size=(12, 80))
    assert clipped == 80


def test_narrow_splitter_handle_keeps_fusion(qapp, themed):
    opt = _option(QStyleOption, themed, QRect(0, 0, 2, 100), S.State_Horizontal)
    assert _chrome.splitter(LaceStyle(), opt, None, None) is False


def test_splitter_length_is_a_theme_keyword(qapp):
    from lace.dock_theme import DockStyleCategory, ThemeSpec, build_theme
    from lace.dock_theme_bridge import DockThemeBridge
    from lace.theme_models import ThemeJson
    from PySide6.QtWidgets import QWidget
    spec = ThemeSpec(base=[30, 30, 34, 255], accent=[0, 120, 215, 255],
                     text=[230, 230, 230, 255], splitter_length=70)
    assert build_theme(spec)[DockStyleCategory.CORE]["splitter_length"] == 70
    js = ThemeJson(base="#1e1e22", accent="#0078d7", text="#e6e6e6", splitter_length=64)
    assert js.to_theme_spec().splitter_length == 64
    w = QWidget()
    bridge = DockThemeBridge(target=w)
    get_dock_style_manager().update(DockStyleCategory.CORE, splitter_length=42)
    bridge.refresh_dock_palette()
    assert w.style().splitter_length == 42
    get_dock_style_manager().update(DockStyleCategory.CORE, splitter_length=50)


def test_dock_splitters_keep_their_own_width(qapp):
    """The dock splitter sizes its handles from its tokens, not the metric."""
    from lace.dock_splitter import DockSplitter
    split = DockSplitter()
    split.setStyle(LaceStyle())
    split.addWidget(QTextEdit())
    split.addWidget(QTextEdit())
    handle = split.handle(1)
    assert handle.sizeHint().width() == handle._total_width


# ---------------------------------------------------------------------------
# Tab close button
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("hover", [False, True], ids=["rest", "hover"])
def test_tab_close_is_a_cross_with_a_hover_wash(qapp, themed, hover):
    opt = _option(QStyleOption, themed, QRect(0, 0, 16, 16), S.State_MouseOver if hover else S(0))
    img = _paint(lambda p: LaceStyle().drawPrimitive(PE.PE_IndicatorTabClose, opt, p, None), 16, 16)
    assert _painted(img, 8, 8)                  # the cross's centre
    assert _painted(img, 8, 2) == hover         # the wash reaches the edge only on hover


# ---------------------------------------------------------------------------
# QFrame lines and boxes
# ---------------------------------------------------------------------------
def _frame(style, palette, shape, shadow=QFrame.Shadow.Sunken, size=(40, 12)):
    opt = _option(QStyleOptionFrame, palette, QRect(0, 0, *size))
    opt.frameShape = shape
    opt.lineWidth = 1
    opt.midLineWidth = 0
    opt.state |= S.State_Sunken if shadow == QFrame.Shadow.Sunken else S.State_Raised
    return _paint(lambda p: style.drawControl(CE.CE_ShapedFrame, opt, p, None), *size)


@pytest.mark.parametrize("shadow", [QFrame.Shadow.Sunken, QFrame.Shadow.Raised, QFrame.Shadow.Plain])
def test_hline_is_one_flat_line(qapp, themed, shadow):
    img = _frame(LaceStyle(), themed, QFrame.Shape.HLine, shadow)
    rows = [y for y in range(12) if _painted(img, 20, y)]
    assert len(rows) == 1
    fusion = _frame(QStyleFactory.create("Fusion"), themed, QFrame.Shape.HLine, QFrame.Shadow.Sunken)
    assert sum(_painted(fusion, 20, y) for y in range(12)) == 2     # Fusion's two-tone bevel


def test_vline_is_one_flat_line(qapp, themed):
    img = _frame(LaceStyle(), themed, QFrame.Shape.VLine, size=(12, 40))
    assert sum(_painted(img, x, 20) for x in range(12)) == 1


@pytest.mark.parametrize("shape", [QFrame.Shape.Box, QFrame.Shape.Panel, QFrame.Shape.WinPanel])
def test_boxes_are_a_flat_outline(qapp, themed, shape):
    img = _frame(LaceStyle(), themed, shape, size=(40, 30))
    assert _painted(img, 20, 0) and _painted(img, 0, 15)       # edges
    assert not _painted(img, 20, 15)                            # no fill
    assert not _painted(img, 20, 1)                             # no second bevel line


# ---------------------------------------------------------------------------
# Dial
# ---------------------------------------------------------------------------
def test_dial_is_flat_with_an_accent_arc(qapp, themed):
    dial = QDial()
    dial.setStyle(LaceStyle())
    dial.setPalette(themed)
    dial.setNotchesVisible(True)
    dial.setValue(60)
    dial.resize(80, 80)
    img = dial.grab().toImage()
    accent = themed.color(QPalette.ColorRole.Highlight)
    near = sum(1 for x in range(80) for y in range(80)
               if abs(img.pixelColor(x, y).hue() - accent.hue()) < 12
               and img.pixelColor(x, y).saturation() > 80)
    assert near > 30
    # No shaded knob across the middle: the centre is the plain background.
    assert img.pixelColor(40, 40) == img.pixelColor(2, 2)


# ---------------------------------------------------------------------------
# Toolbars and size grips: muted text colour
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("element", [PE.PE_IndicatorToolBarHandle, PE.PE_IndicatorToolBarSeparator])
def test_toolbar_lines_are_muted(qapp, themed, element):
    style = LaceStyle()
    opt = _option(QStyleOption, themed, QRect(0, 0, 10, 30), S.State_Horizontal)
    img = _paint(lambda p: style.drawPrimitive(element, opt, p, None), 10, 30)
    lit = [img.pixelColor(x, 15) for x in range(10) if img.pixelColor(x, 15).alpha() == 255]
    assert lit
    window = themed.color(QPalette.ColorRole.Window)
    from lace.theme_contrast import CONTRAST_TARGETS
    assert max(_ratio(c, window) for c in lit) >= CONTRAST_TARGETS["muted"]["normal"] - 0.1


def test_size_grip_draws_in_its_corner(qapp, themed):
    opt = _option(QStyleOptionSizeGrip, themed, QRect(0, 0, 16, 16))
    opt.corner = Qt.Corner.BottomRightCorner
    img = _paint(lambda p: LaceStyle().drawControl(CE.CE_SizeGrip, opt, p, None), 16, 16)
    assert any(_painted(img, x, y) for x in range(10, 16) for y in range(10, 16))
    assert not any(_painted(img, x, y) for x in range(0, 6) for y in range(0, 6))


# ---------------------------------------------------------------------------
# Calendar weekends
# ---------------------------------------------------------------------------
def test_calendar_weekends_follow_the_theme(qapp, themed):
    style = LaceStyle()
    cal = QCalendarWidget()
    cal.setPalette(themed)
    cal.setStyle(style)
    cal.ensurePolished()        # as on first show
    weekend = _chrome._weekend_days(cal)
    assert weekend
    colour = cal.weekdayTextFormat(weekend[0]).foreground().color()
    assert colour != Qt.GlobalColor.red
    assert colour == _chrome.weekend_color(style, cal)
    # A theme switch (palette change) re-tints.
    get_dock_style_manager().apply_theme_dict(load("light"))
    light = build_dock_palette(is_panel=False, colors=resolve_dock_colors())
    cal.setPalette(light)
    assert cal.weekdayTextFormat(weekend[0]).foreground().color() == \
        _chrome.weekend_color(style, cal)
    # Leaving LaceStyle restores Qt's red.
    cal.setStyle(QStyleFactory.create("Fusion"))
    assert cal.weekdayTextFormat(weekend[0]).foreground().color() == Qt.GlobalColor.red
