# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


"""Shared paint helpers for LaceStyle.

Two rules every family follows:

- **Colours only from the option's palette** (``option.palette``), in the
  colour group the option's state asks for. Nothing reads the theme directly,
  so a widget with its own palette, or no Lace theme at all, still paints
  consistently.
- **Vector only.** Glyphs are ``QPainterPath``s stroked or filled under the
  painter's current transform, never cached pixmaps, so they stay sharp on a
  zoomed ``QGraphicsView`` (Weave's canvas).
"""

from functools import lru_cache
from typing import Sequence, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPalette, QPen
from PySide6.QtWidgets import QStyle, QStyleOption

from lace import color_science as cs

State = QStyle.StateFlag
Role = QPalette.ColorRole
Group = QPalette.ColorGroup

#: Stroke strength: ``Text`` mixed over the control's fill by this much.
STROKE_MIX = 0.22
#: Hover and pressed fills: OKLCH lightness steps toward contrast.
HOVER_STEP = 0.04
PRESS_STEP = 0.08
#: Glyph pen width (chevrons, check marks), in logical pixels.
GLYPH_PEN = 1.5
#: Width of the keyboard focus ring.
FOCUS_WIDTH = 2.0
#: Contrast floor of a disabled control's outline: muted, but its shape shows.
DISABLED_RATIO = 1.5

_ACCENT = getattr(Role, "Accent", None)


# ---------------------------------------------------------------------------
# Colour
# ---------------------------------------------------------------------------
def _qcolor(v: Sequence[int]) -> QColor:
    return QColor(v[0], v[1], v[2], v[3] if len(v) > 3 else 255)


def _key(c: QColor) -> Tuple[int, int, int, int]:
    return (c.red(), c.green(), c.blue(), c.alpha())


# Colour derivations are pure functions of their colours, and a theme's
# colours are few and fixed, so each is solved once, not on every paint.
_MEMO = 4096


@lru_cache(maxsize=_MEMO)
def _mix(a, b, t):
    return cs.mix(list(a), list(b), t)


@lru_cache(maxsize=_MEMO)
def _step(c, amount):
    return cs.step(list(c), amount, toward="contrast")


@lru_cache(maxsize=_MEMO)
def _on(c, prefer):
    return cs.on_color(list(c), prefer=[list(p) for p in prefer], ratio=3.0)


@lru_cache(maxsize=_MEMO)
def _ensure(c, bg, ratio):
    return cs.ensure_contrast(list(c), list(bg), ratio)


def group(opt: QStyleOption) -> "QPalette.ColorGroup":
    """The palette group the option's state paints in."""
    if not opt.state & State.State_Enabled:
        return Group.Disabled
    return Group.Active if opt.state & State.State_Active else Group.Inactive


def color(opt: QStyleOption, role) -> QColor:
    """``role`` from the option's palette, in the option's colour group."""
    return opt.palette.color(group(opt), role)


def accent(opt: QStyleOption) -> QColor:
    """The accent for state (checked, focused, selected, fills)."""
    if _ACCENT is not None:
        return color(opt, _ACCENT)
    return color(opt, Role.Highlight)


def mix(a: QColor, b: QColor, t: float) -> QColor:
    """``a`` blended toward ``b`` by ``t``, in OKLab."""
    return _qcolor(_mix(_key(a), _key(b), t))


def step(c: QColor, amount: float) -> QColor:
    """``c`` lightened (dark colours) or darkened (light ones) by ``amount`` of OKLCH L."""
    return _qcolor(_step(_key(c), amount))


def on(c: QColor, opt: QStyleOption) -> QColor:
    """Readable glyph colour on ``c``: the palette's light or dark text, whichever reads."""
    prefer = (_key(color(opt, Role.HighlightedText)), _key(color(opt, Role.Text)))
    return _qcolor(_on(_key(c), prefer))


def stroke(opt: QStyleOption, fill: QColor, strength: float = STROKE_MIX) -> QColor:
    """The 1 px outline of a control whose face is ``fill``: text mixed over it
    by ``strength`` (the theme's ``outline_strength``)."""
    return mix(fill, color(opt, Role.Text), strength)


def legible(opt: QStyleOption, c: QColor, ratio: float, surface=None) -> QColor:
    """``c`` lifted to ``ratio`` against ``surface`` (default ``Window``).

    For the non-text UI a user has to find: indicator outlines, the focus ring,
    the scrollbar handle. Disabled controls are exempt from the target, as in
    WCAG, but keep ``DISABLED_RATIO`` so their shape stays visible.
    """
    if not opt.state & State.State_Enabled:
        ratio = min(ratio, DISABLED_RATIO)
    bg = surface if surface is not None else color(opt, Role.Window)
    return _qcolor(_ensure(_key(c), _key(bg), ratio))


def state_fill(opt: QStyleOption, fill: QColor) -> QColor:
    """``fill`` with the hover or pressed lightness step the state asks for."""
    if not opt.state & State.State_Enabled:
        return fill
    if opt.state & (State.State_Sunken | State.State_On) and opt.state & State.State_MouseOver:
        return step(fill, PRESS_STEP)
    if opt.state & State.State_Sunken:
        return step(fill, PRESS_STEP)
    if opt.state & State.State_MouseOver:
        return step(fill, HOVER_STEP)
    return fill


# ---------------------------------------------------------------------------
# Painter setup and shapes
# ---------------------------------------------------------------------------
class Painting:
    """``with Painting(p):`` saves the painter and turns antialiasing on."""

    def __init__(self, painter: QPainter):
        self.p = painter

    def __enter__(self) -> QPainter:
        self.p.save()
        self.p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        return self.p

    def __exit__(self, *exc):
        self.p.restore()
        return False


def half_pixel(rect) -> QRectF:
    """``rect`` inset so a 1 px stroke lands on whole pixels at 1x."""
    return QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5)


def rounded(painter: QPainter, rect: QRectF, radius: float, fill=None, line=None,
            width: float = 1.0) -> None:
    """A rounded rectangle, filled and/or stroked."""
    radius = max(0.0, min(radius, rect.width() / 2, rect.height() / 2))
    painter.setPen(QPen(line, width) if line is not None else Qt.PenStyle.NoPen)
    painter.setBrush(fill if fill is not None else Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(rect, radius, radius)


#: ``scaled_radius``: share of the size at the reference ``control_radius``,
#: in proportion to it otherwise, capped so small shapes never turn round.
RADIUS_SHARE = 0.22
RADIUS_REF = 4
RADIUS_MAX = 0.30


def scaled_radius(style, size: float) -> float:
    """A corner radius that scales with ``size`` and follows ``control_radius``:
    ``size * min(0.22 * control_radius / 4, 0.30)``; 0 stays square."""
    share = RADIUS_SHARE * style.control_radius / RADIUS_REF
    return size * min(share, RADIUS_MAX)


def focus_ring(painter: QPainter, rect: QRectF, radius: float, opt: QStyleOption,
               ratio: float = 3.0, width: float = FOCUS_WIDTH) -> None:
    """The accent ring (``width`` px) drawn just outside a control's stroke."""
    if width <= 0:
        return
    grow = width / 2
    r = QRectF(rect).adjusted(-grow, -grow, grow, grow)
    rounded(painter, r, radius + grow, line=legible(opt, accent(opt), ratio), width=width)


def _pen(c: QColor, width: float = GLYPH_PEN) -> QPen:
    pen = QPen(c, width)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def chevron(painter: QPainter, rect, direction: str, c: QColor, size: float = 0.0) -> None:
    """A stroked chevron centred in ``rect``, pointing ``up|down|left|right``."""
    r = QRectF(rect)
    s = size or min(r.width(), r.height(), 14.0) * 0.55
    s = max(s, 4.0)
    cx, cy = r.center().x(), r.center().y()
    h = s / 2
    q = s / 4
    pts = {
        "down":  ((cx - h, cy - q), (cx, cy + q), (cx + h, cy - q)),
        "up":    ((cx - h, cy + q), (cx, cy - q), (cx + h, cy + q)),
        "right": ((cx - q, cy - h), (cx + q, cy), (cx - q, cy + h)),
        "left":  ((cx + q, cy - h), (cx - q, cy), (cx + q, cy + h)),
    }[direction]
    path = QPainterPath(QPointF(*pts[0]))
    for pt in pts[1:]:
        path.lineTo(QPointF(*pt))
    painter.setPen(_pen(c))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(path)


def triangle(painter: QPainter, rect, direction: str, c: QColor, size: float = 0.0) -> None:
    """A filled triangle centred in ``rect``, pointing ``up|down|left|right``."""
    r = QRectF(rect)
    s = size or min(r.width(), r.height()) * 0.5
    cx, cy = r.center().x(), r.center().y()
    h, q = s / 2, s / 4
    pts = {
        "down":  ((cx - h, cy - q), (cx + h, cy - q), (cx, cy + q)),
        "up":    ((cx - h, cy + q), (cx + h, cy + q), (cx, cy - q)),
        "right": ((cx - q, cy - h), (cx - q, cy + h), (cx + q, cy)),
        "left":  ((cx + q, cy - h), (cx + q, cy + h), (cx - q, cy)),
    }[direction]
    path = QPainterPath(QPointF(*pts[0]))
    for pt in pts[1:]:
        path.lineTo(QPointF(*pt))
    path.closeSubpath()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(c)
    painter.drawPath(path)


def check_mark(painter: QPainter, rect: QRectF, c: QColor) -> None:
    """A stroked tick inside ``rect``."""
    x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()
    path = QPainterPath(QPointF(x + w * 0.24, y + h * 0.52))
    path.lineTo(QPointF(x + w * 0.43, y + h * 0.70))
    path.lineTo(QPointF(x + w * 0.77, y + h * 0.32))
    painter.setPen(_pen(c, max(GLYPH_PEN, w * 0.12)))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawPath(path)


def dash(painter: QPainter, rect: QRectF, c: QColor) -> None:
    """The partially-checked bar."""
    y = rect.center().y()
    painter.setPen(_pen(c, max(GLYPH_PEN, rect.width() * 0.12)))
    painter.drawLine(QPointF(rect.x() + rect.width() * 0.28, y),
                     QPointF(rect.right() - rect.width() * 0.28, y))


def plus_minus(painter: QPainter, rect, plus: bool, c: QColor) -> None:
    """A ``+`` or ``-`` glyph (spin boxes with PlusMinus symbols)."""
    r = QRectF(rect)
    s = min(r.width(), r.height()) * 0.5
    cx, cy = r.center().x(), r.center().y()
    painter.setPen(_pen(c))
    painter.drawLine(QPointF(cx - s / 2, cy), QPointF(cx + s / 2, cy))
    if plus:
        painter.drawLine(QPointF(cx, cy - s / 2), QPointF(cx, cy + s / 2))
