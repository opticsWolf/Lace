# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


"""Phase 4b-3: sliders and progress bars.

Slider: a 4 px rounded groove, filled with the accent up to the handle, and a
round handle with a 1 px stroke. Progress bar: a rounded track with a rounded
accent fill; the busy state is a segment sliding along the track. Sub-control
and sub-element rects stay Fusion's.
"""

import time

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import QPalette, QPen
from PySide6.QtWidgets import QSlider, QStyle, QStyleOptionProgressBar, QStyleOptionSlider

from lace.style import _paint as P

CE = QStyle.ControlElement
CC = QStyle.ComplexControl
SC = QStyle.SubControl
State = QStyle.StateFlag
Role = QPalette.ColorRole

#: Groove thickness of sliders and progress tracks' minimum, in px.
GROOVE = 4.0
#: Track colour: text mixed over the window by this much.
TRACK_MIX = 0.16
#: Disabled fill: accent share mixed over the track.
DISABLED_TINT = 0.45
#: Busy progress: segment length (share of the track) and one sweep, seconds.
BUSY_SPAN, BUSY_PERIOD = 0.3, 1.6


def _enabled(opt) -> bool:
    return bool(opt.state & State.State_Enabled)


def _track(opt):
    # Held to the disabled floor in every state, so a disabled track never
    # reads stronger than an enabled one.
    track = P.mix(P.color(opt, Role.Window), P.color(opt, Role.Text), TRACK_MIX)
    return P.legible(opt, track, P.DISABLED_RATIO)


def _fill(opt):
    acc = P.accent(opt)
    if _enabled(opt):
        return acc
    # A muted accent tinted from the track it sits on, held apart from it.
    track = _track(opt)
    return P.legible(opt, P.mix(track, acc, DISABLED_TINT), P.DISABLED_RATIO, surface=track)


# ---------------------------------------------------------------------------
# Slider
# ---------------------------------------------------------------------------
def _ticks(style, opt, p, groove: QRectF, horizontal: bool):
    TP = QSlider.TickPosition
    if opt.tickPosition == TP.NoTicks or opt.maximum <= opt.minimum:
        return
    interval = opt.tickInterval or opt.pageStep or 1
    handle_len = style.pixelMetric(QStyle.PixelMetric.PM_SliderLength, opt, None)
    span = (opt.rect.width() if horizontal else opt.rect.height()) - handle_len
    color = P.mix(P.color(opt, Role.Window), P.color(opt, Role.Text), 0.35)
    p.setPen(QPen(color, 1))
    tick = 4
    v = opt.minimum
    while v <= opt.maximum:
        pos = QStyle.sliderPositionFromValue(opt.minimum, opt.maximum, v, span, opt.upsideDown)
        c = pos + handle_len / 2 + 0.5
        for side in (TP.TicksAbove, TP.TicksBelow):
            if not opt.tickPosition.value & side.value:
                continue
            if horizontal:
                y = opt.rect.top() + 0.5 if side == TP.TicksAbove else opt.rect.bottom() - tick + 0.5
                p.drawLine(QPointF(opt.rect.x() + c, y), QPointF(opt.rect.x() + c, y + tick - 1))
            else:
                x = opt.rect.left() + 0.5 if side == TP.TicksAbove else opt.rect.right() - tick + 0.5
                p.drawLine(QPointF(x, opt.rect.y() + c), QPointF(x + tick - 1, opt.rect.y() + c))
        v += interval


def slider(style, opt, p, w):
    if not isinstance(opt, QStyleOptionSlider):
        return False
    horizontal = opt.orientation == Qt.Orientation.Horizontal
    groove_r = QRectF(style.subControlRect(CC.CC_Slider, opt, SC.SC_SliderGroove, w))
    handle_r = QRectF(style.subControlRect(CC.CC_Slider, opt, SC.SC_SliderHandle, w))
    with P.Painting(p):
        if opt.subControls & SC.SC_SliderGroove and not groove_r.isEmpty():
            c = groove_r.center()
            if horizontal:
                g = QRectF(groove_r.left(), c.y() - GROOVE / 2, groove_r.width(), GROOVE)
            else:
                g = QRectF(c.x() - GROOVE / 2, groove_r.top(), GROOVE, groove_r.height())
            P.rounded(p, g, GROOVE / 2, fill=_track(opt))
            # Accent from the minimum end to the handle's centre.
            hc = handle_r.center()
            filled = QRectF(g)
            if horizontal:
                if opt.upsideDown:
                    filled.setLeft(hc.x())
                else:
                    filled.setRight(hc.x())
            else:
                if opt.upsideDown:
                    filled.setTop(hc.y())
                else:
                    filled.setBottom(hc.y())
            if filled.width() > 0 and filled.height() > 0:
                P.rounded(p, filled, GROOVE / 2, fill=_fill(opt))
        if opt.subControls & SC.SC_SliderTickmarks:
            _ticks(style, opt, p, groove_r, horizontal)
        if opt.subControls & SC.SC_SliderHandle and not handle_r.isEmpty():
            d = min(handle_r.width(), handle_r.height()) - 2
            knob = QRectF(0, 0, d, d)
            knob.moveCenter(handle_r.center())
            knob = P.half_pixel(knob.toAlignedRect())
            active = bool(opt.activeSubControls & SC.SC_SliderHandle)
            handle_opt_state = opt.state
            if not active:
                opt.state &= ~(State.State_MouseOver | State.State_Sunken)
            face = P.state_fill(opt, P.color(opt, Role.Button))
            opt.state = handle_opt_state
            line = P.legible(opt, P.stroke(opt, face, style.outline_strength), style.ui_ratio)
            P.rounded(p, knob, knob.width() / 2, fill=face, line=line)
            if opt.state & State.State_HasFocus and opt.state & State.State_KeyboardFocusChange:
                P.focus_ring(p, knob, knob.width() / 2, opt, style.ui_ratio, style.focus_width)
    return True


# ---------------------------------------------------------------------------
# Progress bar
# ---------------------------------------------------------------------------
def _horizontal_bar(opt) -> bool:
    return bool(opt.state & State.State_Horizontal)


def _bar_rect(opt) -> QRectF:
    return QRectF(opt.rect)


def progress_groove(style, opt, p, w):
    if not isinstance(opt, QStyleOptionProgressBar):
        return False
    r = _bar_rect(opt)
    with P.Painting(p):
        radius = min(style.control_radius, min(r.width(), r.height()) / 2)
        P.rounded(p, P.half_pixel(r), radius, fill=_track(opt))
    return True


def progress_contents(style, opt, p, w):
    if not isinstance(opt, QStyleOptionProgressBar):
        return False
    r = _bar_rect(opt)
    horizontal = _horizontal_bar(opt)
    length = r.width() if horizontal else r.height()
    busy = opt.minimum == opt.maximum == 0
    if busy:
        # Without a widget to animate (renders, tests) the segment rests mid-track.
        animate = w is not None and w.isVisible()
        t = (time.monotonic() % BUSY_PERIOD) / BUSY_PERIOD if animate else 0.5
        seg = length * BUSY_SPAN
        start, size = -seg + t * (length + seg), seg
        if animate:
            QTimer.singleShot(33, w.update)
    else:
        span = opt.maximum - opt.minimum
        frac = 0.0 if span <= 0 else max(0.0, min(1.0, (opt.progress - opt.minimum) / span))
        start, size = 0.0, length * frac
        if horizontal:
            reverse = opt.invertedAppearance != (opt.direction == Qt.LayoutDirection.RightToLeft)
        else:
            reverse = not opt.invertedAppearance   # vertical bars fill from the bottom
        if reverse:
            start = length - size
    if size <= 0:
        return True
    if horizontal:
        bar = QRectF(r.left() + start, r.top(), size, r.height())
    else:
        bar = QRectF(r.left(), r.top() + start, r.width(), size)
    bar = bar.intersected(r)
    radius = min(style.control_radius, min(r.width(), r.height()) / 2)
    with P.Painting(p):
        p.setClipRect(opt.rect)
        P.rounded(p, P.half_pixel(bar), radius, fill=_fill(opt))
    return True


COMPLEX = {
    CC.CC_Slider: slider,
}

CONTROLS = {
    CE.CE_ProgressBarGroove: progress_groove,
    CE.CE_ProgressBarContents: progress_contents,
}
