# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


"""Phase 4a: indicators, frames, focus ring and scrollbars.

Every draw function takes ``(style, option, painter, widget)`` and returns
True when it painted; False hands the element back to Fusion. The tables at
the bottom are what :class:`lace.lace_style.LaceStyle` dispatches on.
"""

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QPushButton, QMenu, QStyle, QToolButton,
)

from lace.style import _paint as P

PE = QStyle.PrimitiveElement
CC = QStyle.ComplexControl
SC = QStyle.SubControl
State = QStyle.StateFlag
Role = QPalette.ColorRole


# ---------------------------------------------------------------------------
# Arrows and branches
# ---------------------------------------------------------------------------
def _arrow(direction):
    def draw(style, opt, p, w):
        with P.Painting(p):
            P.chevron(p, opt.rect, direction, P.color(opt, Role.ButtonText))
        return True
    return draw


def _spin(direction, plus_minus=None):
    def draw(style, opt, p, w):
        with P.Painting(p):
            c = P.color(opt, Role.ButtonText)
            if plus_minus is None:
                P.chevron(p, opt.rect, direction, c)
            else:
                P.plus_minus(p, opt.rect, plus_minus, c)
        return True
    return draw


def branch(style, opt, p, w):
    """Tree expand/collapse: a chevron, no connector lines (as Fusion)."""
    if not opt.state & State.State_Children:
        return True
    open_ = bool(opt.state & State.State_Open)
    rtl = opt.direction == Qt.LayoutDirection.RightToLeft
    direction = "down" if open_ else ("left" if rtl else "right")
    size = min(opt.rect.width(), opt.rect.height(), 16) * 0.5
    with P.Painting(p):
        P.chevron(p, opt.rect, direction, P.color(opt, Role.Text), size=size)
    return True


# ---------------------------------------------------------------------------
# Check box, radio button, menu check
# ---------------------------------------------------------------------------
def _indicator_rect(opt) -> QRectF:
    r = QRectF(opt.rect)
    side = min(r.width(), r.height())
    sq = QRectF(0, 0, side, side)
    sq.moveCenter(r.center())
    return P.half_pixel(sq)


def _outline(style, opt, base):
    """Outline of an unchecked indicator: accent on hover, else the stroke,
    either lifted to the ``ui`` contrast target against the window."""
    hovered = opt.state & State.State_MouseOver and opt.state & State.State_Enabled
    line = P.accent(opt) if hovered else P.stroke(opt, base, style.outline_strength)
    return P.legible(opt, line, style.ui_ratio)


#: Check box corners: ``control_radius`` scaled by this (0 stays square),
#: capped at ``CHECK_RADIUS_MAX`` of the box's width so a check box never
#: reads as a radio button.
CHECK_RADIUS_SCALE = 0.5
CHECK_RADIUS_MAX = 0.30

#: Accent share of a partially checked box's fill (over Base).
PARTIAL_WASH = 0.28


def check_box(style, opt, p, w):
    if isinstance(w, QMenu):
        # Fusion draws a menu item's check through here: menus get the bare tick.
        return menu_check(style, opt, p, w) if opt.state & State.State_On else True
    r = _indicator_rect(opt)
    on = bool(opt.state & State.State_On)
    partial = bool(opt.state & State.State_NoChange)
    radius = min(style.control_radius * CHECK_RADIUS_SCALE, r.width() * CHECK_RADIUS_MAX)
    with P.Painting(p):
        if on:
            fill = P.state_fill(opt, P.accent(opt))
            P.rounded(p, r, radius, fill=fill, line=fill)
            P.check_mark(p, r, P.on(fill, opt))
        elif partial:
            # Between off and on: an accent wash, accent outline and dash.
            acc = P.accent(opt)
            wash = P.state_fill(opt, P.mix(P.color(opt, Role.Base), acc, PARTIAL_WASH))
            P.rounded(p, r, radius, fill=wash, line=P.legible(opt, acc, style.ui_ratio))
            P.dash(p, r, P.legible(opt, acc, style.ui_ratio, surface=wash))
        else:
            base = P.state_fill(opt, P.color(opt, Role.Base))
            P.rounded(p, r, radius, fill=base, line=_outline(style, opt, base))
    return True


def radio_button(style, opt, p, w):
    if isinstance(w, QMenu):
        return _menu_dot(opt, p) if opt.state & State.State_On else True
    r = _indicator_rect(opt)
    on = bool(opt.state & State.State_On)
    with P.Painting(p):
        base = P.state_fill(opt, P.color(opt, Role.Base))
        if on:
            ring = P.state_fill(opt, P.accent(opt))
            P.rounded(p, r, r.width() / 2, fill=base, line=ring, width=1.5)
            dot = QRectF(r)
            inset = r.width() * 0.28
            dot.adjust(inset, inset, -inset, -inset)
            P.rounded(p, dot, dot.width() / 2, fill=ring)
        else:
            P.rounded(p, r, r.width() / 2, fill=base, line=_outline(style, opt, base))
    return True


def menu_check(style, opt, p, w):
    """Check mark in a menu item: a bare tick (exclusive items get a dot).

    Menus only ask for it on checked items, so like Fusion it ignores State_On.
    """
    exclusive = getattr(opt, "checkType", None) is not None and \
        opt.checkType == opt.checkType.Exclusive
    if exclusive:
        return _menu_dot(opt, p)
    with P.Painting(p):
        P.check_mark(p, _indicator_rect(opt), _menu_ink(opt))
    return True


def _menu_ink(opt):
    return P.color(opt, Role.HighlightedText if opt.state & State.State_Selected else Role.Text)


def _menu_dot(opt, p):
    r = _indicator_rect(opt)
    dot = QRectF(r)
    inset = r.width() * 0.32
    dot.adjust(inset, inset, -inset, -inset)
    with P.Painting(p):
        P.rounded(p, dot, dot.width() / 2, fill=_menu_ink(opt))
    return True


# ---------------------------------------------------------------------------
# Frames and focus
# ---------------------------------------------------------------------------
def focus_rect(style, opt, p, w):
    """The keyboard focus ring. Item views show focus by their selection.

    Like Fusion, drawn only when focus came from the keyboard, so a mouse click
    doesn't leave a ring behind.
    """
    if not opt.state & State.State_KeyboardFocusChange:
        return True
    if isinstance(w, (QPushButton, QToolButton, QComboBox)):
        return True   # focus shows on the face (see _buttons)
    if isinstance(w, QAbstractItemView) or (w is not None and isinstance(w.parent(), QAbstractItemView)):
        return True
    with P.Painting(p):
        r = P.half_pixel(QRectF(opt.rect).adjusted(1, 1, -1, -1))
        P.focus_ring(p, r, style.control_radius, opt, style.ui_ratio, style.focus_width)
    return True


def frame(style, opt, p, w):
    """A plain 1 px rounded outline (``QFrame::StyledPanel`` and friends)."""
    with P.Painting(p):
        line = P.legible(opt, P.stroke(opt, P.color(opt, Role.Window), style.outline_strength),
                          style.border_ratio)
        P.rounded(p, P.half_pixel(opt.rect), style.control_radius, line=line)
    return True


def frame_line_edit(style, opt, p, w):
    """Outline of a line edit / text edit: accent when it has focus."""
    with P.Painting(p):
        base = P.color(opt, Role.Base)
        focused = opt.state & State.State_HasFocus and opt.state & State.State_Enabled
        if focused:
            line = P.legible(opt, P.accent(opt), style.ui_ratio)
        else:
            line = P.legible(opt, P.stroke(opt, base, style.outline_strength), style.border_ratio)
        P.rounded(p, P.half_pixel(opt.rect), style.control_radius, line=line)
    return True


# ---------------------------------------------------------------------------
# Scrollbars
# ---------------------------------------------------------------------------
#: Scrollbar extent per mode. ``fusion`` defers to Fusion entirely.
SCROLLBAR_EXTENT = {"thin": 8, "expanding": 10}
#: Handle thickness of an ``expanding`` bar at rest; full extent on hover.
EXPANDING_REST = 4


def _horizontal(opt) -> bool:
    return opt.orientation == Qt.Orientation.Horizontal


def _has_buttons(style) -> bool:
    """``expanding`` bars keep step buttons (arrows show when expanded); ``thin`` has none."""
    return style.scrollbar == "expanding"


def scrollbar_rect(style, opt, sc, w):
    """Sub-control rects: ``thin`` has no step buttons, the groove is the bar;
    ``expanding`` reserves a square button at each end."""
    r = QRect(opt.rect)
    horizontal = _horizontal(opt)
    thick = r.height() if horizontal else r.width()
    btn = thick if _has_buttons(style) else 0
    length = (r.width() if horizontal else r.height()) - 2 * btn
    if horizontal:
        sub = QRect(r.x(), r.y(), btn, r.height())
        add = QRect(r.right() - btn + 1, r.y(), btn, r.height())
        groove = QRect(r.x() + btn, r.y(), length, r.height())
    else:
        sub = QRect(r.x(), r.y(), r.width(), btn)
        add = QRect(r.x(), r.bottom() - btn + 1, r.width(), btn)
        groove = QRect(r.x(), r.y() + btn, r.width(), length)
    if sc == SC.SC_ScrollBarSubLine:
        return sub if btn else QRect()
    if sc == SC.SC_ScrollBarAddLine:
        return add if btn else QRect()
    if sc == SC.SC_ScrollBarGroove:
        return groove
    span = opt.maximum - opt.minimum
    min_len = style.pixelMetric(QStyle.PixelMetric.PM_ScrollBarSliderMin, opt, w)
    if span <= 0:
        handle_len = length
    else:
        handle_len = max(min_len, int(length * opt.pageStep / (span + opt.pageStep)))
    handle_len = max(0, min(handle_len, length))
    pos = QStyle.sliderPositionFromValue(opt.minimum, opt.maximum, opt.sliderPosition,
                                         max(0, length - handle_len), opt.upsideDown)
    g = groove
    if horizontal:
        handle = QRect(g.x() + pos, g.y(), handle_len, g.height())
        before = QRect(g.x(), g.y(), pos, g.height())
        after = QRect(handle.right() + 1, g.y(), g.right() - handle.right(), g.height())
    else:
        handle = QRect(g.x(), g.y() + pos, g.width(), handle_len)
        before = QRect(g.x(), g.y(), g.width(), pos)
        after = QRect(g.x(), handle.bottom() + 1, g.width(), g.bottom() - handle.bottom())
    return {SC.SC_ScrollBarSlider: handle, SC.SC_ScrollBarSubPage: before,
            SC.SC_ScrollBarAddPage: after}.get(sc, QRect())


def _step_arrows(style, opt, p, w, window, text, horizontal):
    """Filled triangles in the step buttons of an expanded ``expanding`` bar."""
    enabled = bool(opt.state & State.State_Enabled)
    sunken = bool(opt.state & State.State_Sunken)
    rtl = horizontal and opt.direction == Qt.LayoutDirection.RightToLeft
    for sc, direction, at_end in (
            (SC.SC_ScrollBarSubLine, "left" if horizontal else "up",
             opt.sliderPosition <= opt.minimum),
            (SC.SC_ScrollBarAddLine, "right" if horizontal else "down",
             opt.sliderPosition >= opt.maximum)):
        rect = QRectF(style.subControlRect(CC.CC_ScrollBar, opt, sc, w))
        if rect.isEmpty():
            continue
        if rtl:
            direction = {"left": "right", "right": "left"}[direction]
        active = enabled and bool(opt.activeSubControls & sc)
        if active:
            face = rect.adjusted(1, 1, -1, -1)
            fill = P.mix(window, text, 0.18 if sunken else 0.10)
            P.rounded(p, face, min(face.width(), face.height()) / 2, fill=fill)
        strength = 0.35 if (at_end or not enabled) else 0.85 if active else 0.62
        P.triangle(p, rect, direction, P.mix(window, text, strength),
                   size=min(rect.width(), rect.height()) * 0.5)


def scrollbar(style, opt, p, w):
    """Flat scrollbar: a rounded handle on a faint track. ``expanding`` bars
    rest as a thin handle and grow, with step arrows, on hover."""
    horizontal = _horizontal(opt)
    window = P.color(opt, Role.Window)
    text = P.color(opt, Role.Text)
    hovered = bool(opt.state & State.State_MouseOver) and bool(opt.state & State.State_Enabled)
    on_handle = bool(opt.activeSubControls & SC.SC_ScrollBarSlider)
    pressed = bool(opt.state & State.State_Sunken) and bool(opt.activeSubControls)
    expanded = hovered or pressed

    handle = QRectF(style.subControlRect(CC.CC_ScrollBar, opt, SC.SC_ScrollBarSlider, w))
    track = QRectF(opt.rect)
    thick = track.height() if horizontal else track.width()
    if style.scrollbar == "expanding" and not expanded:
        thick = min(thick, EXPANDING_REST + 2)
        # At rest the handle hugs the far edge of the bar.
        if horizontal:
            track.setTop(track.bottom() - thick + 1)
            handle.setTop(track.top())
        else:
            track.setLeft(track.right() - thick + 1)
            handle.setLeft(track.left())

    with P.Painting(p):
        if expanded:
            P.rounded(p, track, 0, fill=P.mix(window, text, 0.05))
            if _has_buttons(style):
                _step_arrows(style, opt, p, w, window, text, horizontal)
        pad = 2.0 if thick >= 7 else 1.0
        h = handle.adjusted(pad, pad, -pad, -pad)
        strength = 0.55 if (pressed and on_handle) else 0.45 if (hovered and on_handle) else 0.32
        if not opt.state & State.State_Enabled:
            strength = 0.16
        fill = P.legible(opt, P.mix(window, text, strength), style.ui_ratio)
        radius = min(h.width(), h.height()) / 2
        if h.width() > 0 and h.height() > 0 and opt.maximum > opt.minimum:
            P.rounded(p, h, radius, fill=fill)
    return True


# ---------------------------------------------------------------------------
# Dispatch tables
# ---------------------------------------------------------------------------
PRIMITIVES = {
    PE.PE_IndicatorArrowUp: _arrow("up"),
    PE.PE_IndicatorArrowDown: _arrow("down"),
    PE.PE_IndicatorArrowLeft: _arrow("left"),
    PE.PE_IndicatorArrowRight: _arrow("right"),
    PE.PE_IndicatorSpinUp: _spin("up"),
    PE.PE_IndicatorSpinDown: _spin("down"),
    PE.PE_IndicatorSpinPlus: _spin("up", plus_minus=True),
    PE.PE_IndicatorSpinMinus: _spin("down", plus_minus=False),
    PE.PE_IndicatorBranch: branch,
    PE.PE_IndicatorCheckBox: check_box,
    PE.PE_IndicatorItemViewItemCheck: check_box,
    PE.PE_IndicatorRadioButton: radio_button,
    PE.PE_IndicatorMenuCheckMark: menu_check,
    PE.PE_FrameFocusRect: focus_rect,
    PE.PE_Frame: frame,
    PE.PE_FrameLineEdit: frame_line_edit,
}

#: Complex controls and their sub-control rects; only in non-``fusion`` scrollbar modes.
COMPLEX = {CC.CC_ScrollBar: scrollbar}
SUBCONTROL_RECTS = {CC.CC_ScrollBar: scrollbar_rect}
