# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


"""Phase 4b-2: line edits, combo boxes and spin boxes.

Each input is one rounded field: a recessed ``Base`` fill with a 1 px outline
that turns accent on focus. Combo and spin boxes draw their buttons inside
that field, with vector chevrons and no separator bevels; hover and press show
as a tint on the button area only. Sub-control rects stay Fusion's.
"""

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainterPath, QPalette
from PySide6.QtWidgets import (
    QAbstractSpinBox, QStyle, QStyleOptionComboBox, QStyleOptionFrame, QStyleOptionSpinBox,
)

from lace.style import _buttons
from lace.style import _paint as P

PE = QStyle.PrimitiveElement
CC = QStyle.ComplexControl
SC = QStyle.SubControl
State = QStyle.StateFlag
Role = QPalette.ColorRole


def _enabled(opt) -> bool:
    return bool(opt.state & State.State_Enabled)


def _focused(opt) -> bool:
    return bool(opt.state & State.State_HasFocus) and _enabled(opt)


def field_outline(style, opt, base):
    """Outline of an input field: accent while focused, else the stroke."""
    if _focused(opt):
        return P.legible(opt, P.accent(opt), style.ui_ratio)
    return P.legible(opt, P.stroke(opt, base, style.outline_strength), style.border_ratio)


def _field(style, opt, p, rect, framed=True):
    """The rounded field: Base fill and (optionally) its outline."""
    base = P.color(opt, Role.Base)
    r = P.half_pixel(rect)
    P.rounded(p, r, style.control_radius, fill=base,
              line=field_outline(style, opt, base) if framed else None)
    return r


def _button_tint(style, opt, p, field: QRectF, rect: QRectF, active: bool, pressed: bool):
    """Hover / press tint of a button area, clipped to the rounded field."""
    if not (active and _enabled(opt)):
        return
    base = P.color(opt, Role.Base)
    tint = P.step(base, P.PRESS_STEP if pressed else P.HOVER_STEP)
    clip = QPainterPath()
    inner = field.adjusted(0.5, 0.5, -0.5, -0.5)
    clip.addRoundedRect(inner, max(0.0, style.control_radius - 0.5), max(0.0, style.control_radius - 0.5))
    p.save()
    p.setClipPath(clip, Qt.ClipOperation.IntersectClip)
    P.rounded(p, rect, 0, fill=tint)
    p.restore()


def _glyph_color(opt, enabled=True):
    c = P.color(opt, Role.ButtonText if not opt.state & State.State_ReadOnly else Role.Text)
    if not enabled:
        c = P.mix(P.color(opt, Role.Base), c, 0.35)
    return c


# ---------------------------------------------------------------------------
# Line edits
# ---------------------------------------------------------------------------
def panel_line_edit(style, opt, p, w):
    """Line-edit background, plus its frame when it has one."""
    framed = isinstance(opt, QStyleOptionFrame) and opt.lineWidth > 0
    with P.Painting(p):
        if framed:
            _field(style, opt, p, QRectF(opt.rect))
        else:
            # Frameless (inside a spin or combo box): a plain Base fill.
            P.rounded(p, QRectF(opt.rect), 0, fill=P.color(opt, Role.Base))
    return True


# ---------------------------------------------------------------------------
# Combo box
# ---------------------------------------------------------------------------
def combo_box(style, opt, p, w):
    if not isinstance(opt, QStyleOptionComboBox):
        return False
    arrow = QRectF(style.subControlRect(CC.CC_ComboBox, opt, SC.SC_ComboBoxArrow, w))
    on_arrow = bool(opt.activeSubControls & SC.SC_ComboBoxArrow)
    hovered = bool(opt.state & State.State_MouseOver)
    pressed = bool(opt.state & State.State_Sunken)
    with P.Painting(p):
        if opt.editable:
            field = _field(style, opt, p, QRectF(opt.rect), framed=opt.frame)
            _button_tint(style, opt, p, field, arrow, on_arrow and (hovered or pressed),
                         pressed and on_arrow)
            glyph = _glyph_color(opt, _enabled(opt))
        else:
            # A button face (flat Button fill, outline, focus ring) from 4b-1.
            _buttons._face(style, opt, p, QRectF(opt.rect))
            fill, _ = _buttons.face_colors(style, opt)
            glyph = P.color(opt, Role.ButtonText)
            if not _enabled(opt) and fill is not None:
                glyph = P.mix(fill, glyph, 0.5)
        if opt.subControls & SC.SC_ComboBoxArrow and not arrow.isEmpty():
            P.chevron(p, arrow, "down", glyph, size=min(arrow.width(), arrow.height(), 14.0) * 0.5)
    return True


# ---------------------------------------------------------------------------
# Spin box
# ---------------------------------------------------------------------------
def spin_box(style, opt, p, w):
    if not isinstance(opt, QStyleOptionSpinBox):
        return False
    Symbols = QAbstractSpinBox.ButtonSymbols
    Step = QAbstractSpinBox.StepEnabledFlag
    with P.Painting(p):
        field = _field(style, opt, p, QRectF(opt.rect), framed=opt.frame)
        if opt.buttonSymbols == Symbols.NoButtons:
            return True
        hovered = bool(opt.state & State.State_MouseOver)
        pressed = bool(opt.state & State.State_Sunken)
        plus_minus = opt.buttonSymbols == Symbols.PlusMinus
        for sc, direction, step, plus in (
                (SC.SC_SpinBoxUp, "up", Step.StepUpEnabled, True),
                (SC.SC_SpinBoxDown, "down", Step.StepDownEnabled, False)):
            if not opt.subControls & sc:
                continue
            rect = QRectF(style.subControlRect(CC.CC_SpinBox, opt, sc, w))
            if rect.isEmpty():
                continue
            enabled = _enabled(opt) and bool(opt.stepEnabled & step)
            active = bool(opt.activeSubControls & sc)
            if enabled:
                _button_tint(style, opt, p, field, rect, active and (hovered or pressed),
                             active and pressed)
            c = _glyph_color(opt, enabled)
            if plus_minus:
                P.plus_minus(p, rect, plus, c)
            else:
                P.chevron(p, rect, direction, c, size=min(rect.width(), rect.height() * 2, 12.0) * 0.6)
    return True


PRIMITIVES = {
    PE.PE_PanelLineEdit: panel_line_edit,
}

COMPLEX = {
    CC.CC_ComboBox: combo_box,
    CC.CC_SpinBox: spin_box,
}
