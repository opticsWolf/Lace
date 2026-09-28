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

import math
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
#: Disabled track and fill: share of the floored colour over the plain mix.
DISABLED_BLEND = 0.5
#: Busy progress: segment length (share of the track) and one sweep, seconds.
BUSY_SPAN, BUSY_PERIOD = 0.3, 1.6


def _enabled(opt) -> bool:
    return bool(opt.state & State.State_Enabled)


def _floored(opt, plain, floored):
    """Disabled: halfway between the plain colour and the floored one."""
    return floored if _enabled(opt) else P.mix(plain, floored, DISABLED_BLEND)


def _track(opt):
    # Held to the disabled floor, so a disabled track never reads stronger
    # than an enabled one.
    track = P.mix(P.color(opt, Role.Window), P.color(opt, Role.Text), TRACK_MIX)
    return _floored(opt, track, P.legible(opt, track, P.DISABLED_RATIO))


def _fill(opt):
    acc = P.accent(opt)
    if _enabled(opt):
        return acc
    # A muted accent tinted from the track it sits on, held apart from it.
    window = P.color(opt, Role.Window)
    track = P.legible(opt, P.mix(window, P.color(opt, Role.Text), TRACK_MIX), P.DISABLED_RATIO)
    floored = P.legible(opt, P.mix(track, acc, DISABLED_TINT), P.DISABLED_RATIO, surface=track)
    return _floored(opt, P.mix(window, acc, 0.4), floored)


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


# ---------------------------------------------------------------------------
# Dial
# ---------------------------------------------------------------------------
#: Room outside the arc for the notches, and their length.
NOTCH_ROOM, NOTCH_LEN = 6.0, 3.0
#: Handle diameter, as a multiple of the groove.
DIAL_KNOB = 3.0


def _dial_angle(opt, value) -> float:
    """Qt's dial angle for ``value``, in degrees: counter-clockwise from 3
    o'clock, 240 at the minimum to -60 at the maximum (or a full turn from 6
    o'clock when the dial wraps), as QDial's own mouse mapping has it."""
    span = opt.maximum - opt.minimum
    if span <= 0:
        return 90.0
    pos = value if opt.upsideDown else opt.maximum + opt.minimum - value
    frac = (pos - opt.minimum) / span
    if opt.dialWrapping:
        return 270.0 + frac * 360.0
    return 240.0 - frac * 300.0


def _on_circle(c: QPointF, radius: float, degrees: float) -> QPointF:
    a = math.radians(degrees)
    return QPointF(c.x() + radius * math.cos(a), c.y() - radius * math.sin(a))


def dial(style, opt, p, w):
    """A flat dial: a round groove, accent from the minimum to the value, and
    the slider's round handle riding on it. Notches are short muted ticks
    outside the groove."""
    if not isinstance(opt, QStyleOptionSlider):
        return False
    r = QRectF(opt.rect)
    side = min(r.width(), r.height())
    # A small dial keeps its arc readable: the knob never tops a fifth of it.
    knob_d = min(GROOVE * DIAL_KNOB, side * 0.2)
    # QDial asks for SC_DialTickmarks exactly when its notches are visible.
    room = NOTCH_ROOM if opt.subControls & SC.SC_DialTickmarks else 0.0
    radius = side / 2 - room - knob_d / 2 - 1
    if radius <= GROOVE:
        return False
    c = r.center()
    ring = QRectF(c.x() - radius, c.y() - radius, 2 * radius, 2 * radius)
    start = _dial_angle(opt, opt.minimum)
    end = _dial_angle(opt, opt.maximum) if not opt.dialWrapping else start + 360.0
    at = _dial_angle(opt, opt.sliderPosition)
    with P.Painting(p):
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(P.pen(_track(opt), GROOVE))
        p.drawArc(ring, int(start * 16), int((end - start) * 16))
        if abs(at - start) > 0.01:
            p.setPen(P.pen(_fill(opt), GROOVE))
            p.drawArc(ring, int(start * 16), int((at - start) * 16))
        if room:
            p.setPen(P.pen(P.mix(P.color(opt, Role.Window), P.color(opt, Role.Text), 0.35), 1.0))
            step_ = opt.tickInterval or opt.pageStep or 1
            v = opt.minimum
            while v <= opt.maximum:
                a = _dial_angle(opt, v)
                inner = radius + knob_d / 2 + 1
                p.drawLine(_on_circle(c, inner, a), _on_circle(c, inner + NOTCH_LEN, a))
                v += step_
        knob = QRectF(0, 0, knob_d, knob_d)
        knob.moveCenter(_on_circle(c, radius, at))
        face = P.state_fill(opt, P.color(opt, Role.Button))
        line = P.legible(opt, P.stroke(opt, face, style.outline_strength), style.ui_ratio)
        P.rounded(p, knob, knob_d / 2, fill=face, line=line)
        if opt.state & State.State_HasFocus and opt.state & State.State_KeyboardFocusChange:
            P.focus_ring(p, knob, knob_d / 2, opt, style.ui_ratio, style.focus_width)
    return True


COMPLEX = {
    CC.CC_Slider: slider,
    CC.CC_Dial: dial,
}

CONTROLS = {
    CE.CE_ProgressBarGroove: progress_groove,
    CE.CE_ProgressBarContents: progress_contents,
}
