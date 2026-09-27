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

from typing import List, Sequence

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

_ACCENT = getattr(Role, "Accent", None)


# ---------------------------------------------------------------------------
# Colour
# ---------------------------------------------------------------------------
def _rgba(c: QColor) -> List[int]:
    return [c.red(), c.green(), c.blue(), c.alpha()]


def _qcolor(v: Sequence[int]) -> QColor:
    return QColor(v[0], v[1], v[2], v[3] if len(v) > 3 else 255)


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
    return _qcolor(cs.mix(_rgba(a), _rgba(b), t))


def step(c: QColor, amount: float) -> QColor:
    """``c`` lightened (dark colours) or darkened (light ones) by ``amount`` of OKLCH L."""
    return _qcolor(cs.step(_rgba(c), amount, toward="contrast"))


def on(c: QColor, opt: QStyleOption) -> QColor:
    """Readable glyph colour on ``c``: the palette's light or dark text, whichever reads."""
    prefer = (_rgba(color(opt, Role.HighlightedText)), _rgba(color(opt, Role.Text)))
    return _qcolor(cs.on_color(_rgba(c), prefer=prefer, ratio=3.0))


def stroke(opt: QStyleOption, fill: QColor) -> QColor:
    """The 1 px outline of a control whose face is ``fill``: text mixed over it."""
    return mix(fill, color(opt, Role.Text), STROKE_MIX)


def legible(opt: QStyleOption, c: QColor, ratio: float, surface=None) -> QColor:
    """``c`` lifted to ``ratio`` against ``surface`` (default ``Window``).

    For the non-text UI a user has to find: indicator outlines, the focus ring,
    the scrollbar handle. Disabled controls are exempt, as in WCAG.
    """
    if not opt.state & State.State_Enabled:
        return c
    bg = surface if surface is not None else color(opt, Role.Window)
    return _qcolor(cs.ensure_contrast(_rgba(c), _rgba(bg), ratio))


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


def focus_ring(painter: QPainter, rect: QRectF, radius: float, opt: QStyleOption,
               ratio: float = 3.0) -> None:
    """The 2 px accent ring drawn just outside a control's stroke."""
    grow = FOCUS_WIDTH / 2
    r = QRectF(rect).adjusted(-grow, -grow, grow, grow)
    rounded(painter, r, radius + grow, line=legible(opt, accent(opt), ratio), width=FOCUS_WIDTH)


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
