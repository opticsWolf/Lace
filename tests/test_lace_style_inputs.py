# -*- coding: utf-8 -*-
"""LaceStyle 4b-2, inputs: one flat rounded field, accent outline on focus,
buttons drawn inside the field."""

import pytest
from PySide6.QtCore import QRect
from PySide6.QtGui import QImage, QPainter, QPalette
from PySide6.QtWidgets import (
    QAbstractSpinBox, QComboBox, QLineEdit, QSpinBox, QStyle, QStyleOptionComboBox,
    QStyleOptionFrame, QStyleOptionSpinBox,
)

from lace import color_science as cs
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import build_dock_palette, resolve_dock_colors
from lace.lace_style import LaceStyle
from tests.theme_sets import load

S = QStyle.StateFlag
W, H = 100, 26
Step = QAbstractSpinBox.StepEnabledFlag


def _palette(theme_key="kilim_dark"):
    get_dock_style_manager().apply_theme_dict(load(theme_key))
    return build_dock_palette(is_panel=False, colors=resolve_dock_colors())


def _rgb(c):
    return [c.red(), c.green(), c.blue()]


def _state(extra=S.State_None):
    return S.State_Enabled | S.State_Active | extra


def _canvas():
    img = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    return img


def _line_edit(style, pal, state):
    opt = QStyleOptionFrame()
    opt.rect, opt.palette, opt.state, opt.lineWidth = QRect(0, 0, W, H), pal, _state(state), 1
    img = _canvas()
    p = QPainter(img)
    style.drawPrimitive(QStyle.PrimitiveElement.PE_PanelLineEdit, opt, p, QLineEdit())
    p.end()
    return img


def _spin(style, pal, state=S.State_None, step=Step.StepUpEnabled | Step.StepDownEnabled,
          symbols=QAbstractSpinBox.ButtonSymbols.UpDownArrows):
    opt = QStyleOptionSpinBox()
    opt.rect, opt.palette, opt.state = QRect(0, 0, W, H), pal, _state(state)
    opt.frame, opt.subControls, opt.stepEnabled, opt.buttonSymbols = True, QStyle.SubControl.SC_All, step, symbols
    img = _canvas()
    p = QPainter(img)
    style.drawComplexControl(QStyle.ComplexControl.CC_SpinBox, opt, p, QSpinBox())
    p.end()
    rects = {sc: style.subControlRect(QStyle.ComplexControl.CC_SpinBox, opt, sc, QSpinBox())
             for sc in (QStyle.SubControl.SC_SpinBoxUp, QStyle.SubControl.SC_SpinBoxDown)}
    return img, rects


@pytest.mark.parametrize("focus", [False, True], ids=["rest", "focus"])
def test_line_edit_field_is_flat_base(qapp, theme_key, focus):
    pal = _palette(theme_key)
    img = _line_edit(LaceStyle(), pal, S.State_HasFocus if focus else S.State_None)
    inner = {img.pixelColor(x, y).rgba() for x in range(4, W - 4) for y in range(4, H - 4)}
    assert inner == {pal.color(QPalette.ColorGroup.Active, QPalette.ColorRole.Base).rgba()}


def test_focused_field_outline_is_accent(qapp):
    pal = _palette()
    accent = _rgb(pal.color(QPalette.ColorGroup.Active, QPalette.ColorRole.Accent))
    rest = _line_edit(LaceStyle(), pal, S.State_None).pixelColor(W // 2, 0)
    focus = _line_edit(LaceStyle(), pal, S.State_HasFocus).pixelColor(W // 2, 0)
    assert cs.contrast_ratio(_rgb(focus), accent) < cs.contrast_ratio(_rgb(rest), accent)


def _ink(img, rect):
    """Distinct colours inside ``rect``: a glyph adds more than the flat fill."""
    return {img.pixelColor(x, y).rgba() for x in range(rect.left() + 1, rect.right())
            for y in range(rect.top() + 1, rect.bottom())}


def test_spin_buttons_draw_glyphs_and_dim_when_stepping_is_off(qapp):
    pal = _palette()
    style = LaceStyle()
    up_sc, down_sc = QStyle.SubControl.SC_SpinBoxUp, QStyle.SubControl.SC_SpinBoxDown
    img, rects = _spin(style, pal)
    assert len(_ink(img, rects[up_sc])) > 2 and len(_ink(img, rects[down_sc])) > 2
    # At the maximum: the up glyph is dimmer (less contrast with Base) than the down one.
    img, rects = _spin(style, pal, step=Step.StepDownEnabled)
    base = _rgb(pal.color(QPalette.ColorGroup.Active, QPalette.ColorRole.Base))

    def strongest(rect):
        return max(cs.contrast_ratio(_rgb(img.pixelColor(x, y)), base)
                   for x in range(rect.left(), rect.right() + 1)
                   for y in range(rect.top(), rect.bottom() + 1))
    assert strongest(rects[up_sc]) < strongest(rects[down_sc])


def test_spin_without_buttons_draws_only_the_field(qapp):
    pal = _palette()
    img, rects = _spin(LaceStyle(), pal, symbols=QAbstractSpinBox.ButtonSymbols.NoButtons)
    for r in rects.values():
        if not r.isEmpty():
            assert len(_ink(img, r)) <= 2


@pytest.mark.parametrize("editable", [False, True], ids=["button", "editable"])
def test_combo_draws_vector_arrow(qapp, editable):
    pal = _palette()
    style = LaceStyle()
    opt = QStyleOptionComboBox()
    opt.rect, opt.palette, opt.state = QRect(0, 0, W, H), pal, _state()
    opt.editable, opt.frame, opt.subControls = editable, True, QStyle.SubControl.SC_All
    img = _canvas()
    p = QPainter(img)
    style.drawComplexControl(QStyle.ComplexControl.CC_ComboBox, opt, p, QComboBox())
    p.end()
    arrow = style.subControlRect(QStyle.ComplexControl.CC_ComboBox, opt,
                                 QStyle.SubControl.SC_ComboBoxArrow, QComboBox())
    assert len(_ink(img, arrow)) > 2
