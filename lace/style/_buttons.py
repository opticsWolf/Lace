# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


"""Phase 4b-1: push buttons and tool buttons.

Fusion paints every button face (push, tool, and the face of a non-editable
combo box) through ``PE_PanelButtonCommand``, so that one override gives them
all the flat look: a ``Button`` fill with a 1 px outline, hover and pressed as
lightness steps, checked as an accent wash, the default button filled with the
accent. Keyboard focus replaces the outline with the accent ring.
"""

from PySide6.QtCore import QRectF
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QPushButton, QStyle, QStyleOptionButton, QToolButton,
)

from lace.style import _paint as P

PE = QStyle.PrimitiveElement
CE = QStyle.ControlElement
State = QStyle.StateFlag
Role = QPalette.ColorRole
Feature = QStyleOptionButton.ButtonFeature

#: Accent share of a checked (toggled) button's fill; matches the partial check.
CHECKED_WASH = 0.28
#: Extra room on each side of a split button's chevron, px.
SPLIT_PAD = 1


def _features(opt):
    return opt.features if isinstance(opt, QStyleOptionButton) else Feature.None_


def _is_default(opt) -> bool:
    return bool(_features(opt) & Feature.DefaultButton) and bool(opt.state & State.State_Enabled)


def _is_flat(opt) -> bool:
    return bool(_features(opt) & Feature.Flat) or bool(opt.state & State.State_AutoRaise)


def _keyboard_focus(opt) -> bool:
    return bool(opt.state & State.State_HasFocus) and bool(opt.state & State.State_KeyboardFocusChange)


def face_colors(style, opt):
    """``(fill, line)`` for a button face in the option's state; either may be None."""
    base = P.color(opt, Role.Button)
    acc = P.accent(opt)
    on = bool(opt.state & State.State_On)
    active = bool(opt.state & (State.State_MouseOver | State.State_Sunken)) and \
        bool(opt.state & State.State_Enabled)
    if _is_default(opt):
        fill = P.state_fill(opt, acc)
        return fill, fill
    if on:
        fill = P.state_fill(opt, P.mix(base, acc, CHECKED_WASH))
        return fill, P.legible(opt, acc, style.ui_ratio)
    if _is_flat(opt):
        # Flat and auto-raise buttons show a face only while hovered or pressed.
        return (P.state_fill(opt, base) if active else None), None
    fill = P.state_fill(opt, base)
    line = P.legible(opt, P.stroke(opt, base, style.outline_strength), style.border_ratio)
    return fill, line


def _face(style, opt, p, rect: QRectF):
    fill, line = face_colors(style, opt)
    r = P.half_pixel(rect)
    radius = style.control_radius
    with P.Painting(p):
        if _keyboard_focus(opt) and opt.state & State.State_Enabled:
            # The ring sits inside the widget so no layout has to make room.
            inset = style.focus_width / 2
            P.rounded(p, r, radius, fill=fill)
            if style.focus_width > 0:
                ring = r.adjusted(inset - 0.5, inset - 0.5, 0.5 - inset, 0.5 - inset)
                P.rounded(p, ring, max(0.0, radius - inset + 0.5),
                          line=P.legible(opt, P.accent(opt), style.ui_ratio), width=style.focus_width)
            elif line is not None:
                P.rounded(p, r, radius, line=line)
        else:
            P.rounded(p, r, radius, fill=fill, line=line)


def _split_button(w) -> bool:
    return isinstance(w, QToolButton) and w.popupMode() == QToolButton.ToolButtonPopupMode.MenuButtonPopup


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------
def panel_button_command(style, opt, p, w):
    _face(style, opt, p, QRectF(opt.rect))
    return True


def panel_button_tool(style, opt, p, w):
    rect = QRectF(opt.rect)
    if _split_button(w):
        # One rounded field with the drop-down part: run the face on past the
        # right edge (clipped) so the seam is square.
        p.save()
        p.setClipRect(opt.rect)
        _face(style, opt, p, rect.adjusted(0, 0, style.control_radius + 1, 0))
        p.restore()
    else:
        _face(style, opt, p, rect)
    return True


def indicator_button_drop_down(style, opt, p, w):
    """The menu part of a split tool button: the same face, a 1 px divider."""
    rect = QRectF(opt.rect)
    p.save()
    p.setClipRect(opt.rect)
    _face(style, opt, p, rect.adjusted(-style.control_radius - 1, 0, 0, 0))
    p.restore()
    fill, line = face_colors(style, opt)
    if fill is not None or line is not None:
        base = fill if fill is not None else P.color(opt, Role.Button)
        divider = P.stroke(opt, base, style.outline_strength)
        with P.Painting(p):
            x = rect.left() + 0.5
            P.rounded(p, QRectF(x - 0.5, rect.top() + 4, 1, rect.height() - 8), 0, fill=divider)
    return True


def frame_default_button(style, opt, p, w):
    """The default button is marked by its accent fill; no extra frame."""
    return True


# ---------------------------------------------------------------------------
# Controls
# ---------------------------------------------------------------------------
def push_button_label(style, opt, p, w):
    """Label on an accent face (the default button) in the readable on-colour."""
    if not _is_default(opt) or not isinstance(opt, QStyleOptionButton):
        return False
    fill, _ = face_colors(style, opt)
    copy = QStyleOptionButton(opt)
    pal = QPalette(copy.palette)
    glyph = P.on(fill, opt)
    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive):
        pal.setColor(group, Role.ButtonText, glyph)
    copy.palette = pal
    style.baseStyle().drawControl(CE.CE_PushButtonLabel, copy, p, w)
    return True


#: Widgets whose focus LaceStyle shows on the face itself, not by a focus rect.
FOCUS_ON_FACE = (QPushButton, QToolButton)

PRIMITIVES = {
    PE.PE_PanelButtonCommand: panel_button_command,
    PE.PE_PanelButtonBevel: panel_button_command,
    PE.PE_PanelButtonTool: panel_button_tool,
    PE.PE_IndicatorButtonDropDown: indicator_button_drop_down,
    PE.PE_FrameDefaultButton: frame_default_button,
}

CONTROLS = {
    CE.CE_PushButtonLabel: push_button_label,
}
