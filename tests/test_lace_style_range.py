# -*- coding: utf-8 -*-
"""LaceStyle 4b-3, range controls: flat groove with an accent fill up to the
handle, round handle; rounded progress track and fill."""

import pytest
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QImage, QPainter, QPalette
from PySide6.QtWidgets import QSlider, QStyle, QStyleOptionProgressBar, QStyleOptionSlider

from lace import color_science as cs
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import build_dock_palette, resolve_dock_colors
from lace.lace_style import LaceStyle
from tests.theme_sets import load

S = QStyle.StateFlag
W, H = 120, 20


def _palette(theme_key="kilim_dark"):
    get_dock_style_manager().apply_theme_dict(load(theme_key))
    return build_dock_palette(is_panel=False, colors=resolve_dock_colors())


def _rgb(c):
    return [c.red(), c.green(), c.blue()]


def _canvas():
    img = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    return img


def _slider(style, pal, value=40, upside_down=False):
    opt = QStyleOptionSlider()
    opt.rect, opt.palette = QRect(0, 0, W, H), pal
    opt.state = S.State_Enabled | S.State_Active | S.State_Horizontal
    opt.orientation = Qt.Orientation.Horizontal
    opt.minimum, opt.maximum, opt.sliderPosition, opt.sliderValue = 0, 100, value, value
    opt.upsideDown = upside_down
    opt.subControls = QStyle.SubControl.SC_SliderGroove | QStyle.SubControl.SC_SliderHandle
    img = _canvas()
    p = QPainter(img)
    style.drawComplexControl(QStyle.ComplexControl.CC_Slider, opt, p, QSlider())
    p.end()
    handle = style.subControlRect(QStyle.ComplexControl.CC_Slider, opt,
                                  QStyle.SubControl.SC_SliderHandle, QSlider())
    return img, handle


def _closer_to_accent(pal, a, b) -> bool:
    accent = _rgb(pal.color(QPalette.ColorGroup.Active, QPalette.ColorRole.Accent))
    return cs.contrast_ratio(_rgb(a), accent) < cs.contrast_ratio(_rgb(b), accent)


@pytest.mark.parametrize("upside_down", [False, True], ids=["normal", "upside-down"])
def test_slider_groove_is_accent_on_the_minimum_side(qapp, upside_down):
    pal = _palette()
    img, handle = _slider(LaceStyle(), pal, upside_down=upside_down)
    y = handle.center().y()
    left, right = img.pixelColor(handle.left() - 6, y), img.pixelColor(handle.right() + 6, y)
    filled, empty = (right, left) if upside_down else (left, right)
    assert _closer_to_accent(pal, filled, empty)


def test_slider_handle_is_round(qapp):
    img, handle = _slider(LaceStyle(), _palette())
    # The handle's corner stays transparent-ish outside the circle, unlike its centre.
    c = handle.center()
    assert img.pixelColor(c).alpha() == 255
    assert img.pixelColor(handle.left() + 1, handle.top() + 1).alpha() < 255


def _progress(style, pal, progress, busy=False):
    opt = QStyleOptionProgressBar()
    opt.rect, opt.palette = QRect(0, 0, W, 8), pal
    opt.state = S.State_Enabled | S.State_Active | S.State_Horizontal
    opt.minimum, opt.maximum, opt.progress = (0, 0, 0) if busy else (0, 100, progress)
    img = _canvas()
    p = QPainter(img)
    style.drawControl(QStyle.ControlElement.CE_ProgressBarGroove, opt, p, None)
    style.drawControl(QStyle.ControlElement.CE_ProgressBarContents, opt, p, None)
    p.end()
    return img


def test_progress_fills_proportionally(qapp):
    pal = _palette()
    img = _progress(LaceStyle(), pal, 50)
    assert _closer_to_accent(pal, img.pixelColor(W // 4, 4), img.pixelColor(3 * W // 4, 4))


def test_busy_progress_draws_a_segment(qapp):
    pal = _palette()
    img = _progress(LaceStyle(), pal, 0, busy=True)
    assert _closer_to_accent(pal, img.pixelColor(W // 2, 4), img.pixelColor(4, 4))


def test_progress_ends_are_rounded(qapp):
    img = _progress(LaceStyle(), _palette(), 100)
    assert img.pixelColor(0, 0).alpha() < img.pixelColor(W // 2, 0).alpha()
