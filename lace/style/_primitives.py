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
from PySide6.QtWidgets import QAbstractItemView, QStyle

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
    line = P.accent(opt) if hovered else P.stroke(opt, base)
    return P.legible(opt, line, style.ui_ratio)


def check_box(style, opt, p, w):
    r = _indicator_rect(opt)
    on = bool(opt.state & State.State_On)
    partial = bool(opt.state & State.State_NoChange)
    radius = max(2.0, r.width() * 0.22)
    with P.Painting(p):
        if on or partial:
            fill = P.state_fill(opt, P.accent(opt))
            P.rounded(p, r, radius, fill=fill, line=fill)
            glyph = P.on(fill, opt)
            if on:
                P.check_mark(p, r, glyph)
            else:
                P.dash(p, r, glyph)
        else:
            base = P.state_fill(opt, P.color(opt, Role.Base))
            P.rounded(p, r, radius, fill=base, line=_outline(style, opt, base))
    return True


def radio_button(style, opt, p, w):
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
    r = _indicator_rect(opt)
    c = P.color(opt, Role.HighlightedText if opt.state & State.State_Selected else Role.Text)
    with P.Painting(p):
        exclusive = getattr(opt, "checkType", None) is not None and \
            opt.checkType == opt.checkType.Exclusive
        if exclusive:
            dot = QRectF(r)
            inset = r.width() * 0.32
            dot.adjust(inset, inset, -inset, -inset)
            P.rounded(p, dot, dot.width() / 2, fill=c)
        else:
            P.check_mark(p, r, c)
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
    if isinstance(w, QAbstractItemView) or (w is not None and isinstance(w.parent(), QAbstractItemView)):
        return True
    with P.Painting(p):
        r = P.half_pixel(QRectF(opt.rect).adjusted(1, 1, -1, -1))
        P.focus_ring(p, r, style.control_radius, opt, style.ui_ratio)
    return True


def frame(style, opt, p, w):
    """A plain 1 px rounded outline (``QFrame::StyledPanel`` and friends)."""
    with P.Painting(p):
        line = P.legible(opt, P.stroke(opt, P.color(opt, Role.Window)), style.border_ratio)
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
            line = P.legible(opt, P.stroke(opt, base), style.border_ratio)
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


def scrollbar_rect(style, opt, sc, w):
    """Sub-control rects of a thin bar: no step buttons, the groove is the bar."""
    r = QRect(opt.rect)
    horizontal = _horizontal(opt)
    length = r.width() if horizontal else r.height()
    if sc in (SC.SC_ScrollBarAddLine, SC.SC_ScrollBarSubLine):
        return QRect()
    if sc == SC.SC_ScrollBarGroove:
        return r
    span = opt.maximum - opt.minimum
    min_len = style.pixelMetric(QStyle.PixelMetric.PM_ScrollBarSliderMin, opt, w)
    if span <= 0:
        handle_len = length
    else:
        handle_len = max(min_len, int(length * opt.pageStep / (span + opt.pageStep)))
    handle_len = min(handle_len, length)
    pos = QStyle.sliderPositionFromValue(opt.minimum, opt.maximum, opt.sliderPosition,
                                         length - handle_len, opt.upsideDown)
    if horizontal:
        handle = QRect(r.x() + pos, r.y(), handle_len, r.height())
        before = QRect(r.x(), r.y(), pos, r.height())
        after = QRect(handle.right() + 1, r.y(), r.right() - handle.right(), r.height())
    else:
        handle = QRect(r.x(), r.y() + pos, r.width(), handle_len)
        before = QRect(r.x(), r.y(), r.width(), pos)
        after = QRect(r.x(), handle.bottom() + 1, r.width(), r.bottom() - handle.bottom())
    return {SC.SC_ScrollBarSlider: handle, SC.SC_ScrollBarSubPage: before,
            SC.SC_ScrollBarAddPage: after}.get(sc, QRect())


def scrollbar(style, opt, p, w):
    """Thin scrollbar: a rounded handle on a faint track, no step buttons."""
    horizontal = _horizontal(opt)
    window = P.color(opt, Role.Window)
    text = P.color(opt, Role.Text)
    hovered = bool(opt.state & State.State_MouseOver) and bool(opt.state & State.State_Enabled)
    on_handle = bool(opt.activeSubControls & SC.SC_ScrollBarSlider)
    pressed = on_handle and bool(opt.state & State.State_Sunken)

    handle = QRectF(style.subControlRect(CC.CC_ScrollBar, opt, SC.SC_ScrollBarSlider, w))
    track = QRectF(opt.rect)
    thick = track.height() if horizontal else track.width()
    if style.scrollbar == "expanding" and not (hovered or pressed):
        thick = min(thick, EXPANDING_REST + 2)
        # At rest the handle hugs the far edge of the bar.
        if horizontal:
            track.setTop(track.bottom() - thick + 1)
            handle.setTop(track.top())
        else:
            track.setLeft(track.right() - thick + 1)
            handle.setLeft(track.left())

    with P.Painting(p):
        if hovered or pressed:
            P.rounded(p, track, 0, fill=P.mix(window, text, 0.05))
        pad = 2.0 if thick >= 7 else 1.0
        h = handle.adjusted(pad, pad, -pad, -pad)
        strength = 0.55 if pressed else 0.45 if (hovered and on_handle) else 0.32
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
