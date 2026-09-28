# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


"""Window chrome: splitter grips, tab close buttons, frame lines, toolbar
handles and separators, size grips, and the calendar's weekend colour.

Flat throughout: a grip is a rounded pill, a line is one stroke, a glyph is a
vector path. Nothing here changes a size, except the splitter width, which
leaves room around the grip.
"""

from PySide6.QtCore import QObject, QEvent, QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPalette, QTextCharFormat
from PySide6.QtWidgets import QCalendarWidget, QFrame, QStyle, QStyleOption, QStyleOptionFrame

from lace.style import _frame_cap
from lace.style import _paint as P
from lace.style._primitives import EXPANDING_REST
from lace.theme_contrast import CONTRAST_TARGETS

PE = QStyle.PrimitiveElement
CE = QStyle.ControlElement
State = QStyle.StateFlag
Role = QPalette.ColorRole
Shape = QFrame.Shape


def _enabled(opt) -> bool:
    return bool(opt.state & State.State_Enabled)


def muted(style, opt) -> QColor:
    """Muted text: text mixed over the window, held to the ``muted`` floor."""
    c = P.mix(P.color(opt, Role.Window), P.color(opt, Role.WindowText), MUTED_MIX)
    return P.legible(opt, c, CONTRAST_TARGETS["muted"][style.contrast])


#: Text share of the muted colour, before the contrast floor.
MUTED_MIX = 0.5


# ---------------------------------------------------------------------------
# Splitter
# ---------------------------------------------------------------------------
#: Grip thickness at rest: a pixel under the resting scroll bar handle's.
SPLITTER_GRIP = EXPANDING_REST - 1
#: How much the grip thickens under the mouse or while dragged.
SPLITTER_GROW = 2
#: Clear space on each side of the grown grip.
SPLITTER_PAD = 3
#: Text share of the grip at rest: faint, and held only to the disabled floor.
SPLITTER_REST_MIX = 0.28
#: Handle width (PM_SplitterWidth): the grown grip plus its padding.
SPLITTER_WIDTH = SPLITTER_GRIP + SPLITTER_GROW + 2 * SPLITTER_PAD


def splitter(style, opt, p, w):
    """A rounded grip, ``style.splitter_length`` long, centred in the handle:
    faint at rest, accent and ``SPLITTER_GROW`` px thicker on hover or drag.

    Handles too narrow for the grip (an app's ``setHandleWidth(2)``) keep
    Fusion's drawing.
    """
    vertical_grip = bool(opt.state & State.State_Horizontal)   # panes side by side
    r = QRectF(opt.rect)
    across, along = (r.width(), r.height()) if vertical_grip else (r.height(), r.width())
    if across < SPLITTER_GRIP:
        return False
    active = _enabled(opt) and bool(opt.state & (State.State_MouseOver | State.State_Sunken))
    thick = min(across, SPLITTER_GRIP + (SPLITTER_GROW if active else 0))
    length = min(float(style.splitter_length), along)
    grip = QRectF(0, 0, thick, length) if vertical_grip else QRectF(0, 0, length, thick)
    grip.moveCenter(r.center())
    # Whole pixels across, so the grip's edges stay crisp at any handle width.
    if vertical_grip:
        grip.moveLeft(float(round(grip.left())))
    else:
        grip.moveTop(float(round(grip.top())))
    if active:
        fill = P.legible(opt, P.accent(opt), style.ui_ratio)
    else:
        rest = P.mix(P.color(opt, Role.Window), P.color(opt, Role.WindowText), SPLITTER_REST_MIX)
        fill = P.legible(opt, rest, P.DISABLED_RATIO)
    with P.Painting(p):
        P.rounded(p, grip, thick / 2, fill=fill)
    return True


# ---------------------------------------------------------------------------
# Tab close button
# ---------------------------------------------------------------------------
#: Text share of the hover and pressed backgrounds.
CLOSE_HOVER, CLOSE_PRESS = 0.14, 0.22


def tab_close(style, opt, p, w):
    """A stroked cross; a rounded wash behind it on hover and press."""
    r = QRectF(opt.rect)
    side = min(r.width(), r.height())
    box = QRectF(0, 0, side, side)
    box.moveCenter(r.center())
    window = P.color(opt, Role.Window)
    text = P.color(opt, Role.WindowText)
    enabled = _enabled(opt)
    hovered = enabled and bool(opt.state & State.State_MouseOver)
    pressed = enabled and bool(opt.state & State.State_Sunken)
    with P.Painting(p):
        if hovered or pressed:
            wash = P.mix(window, text, CLOSE_PRESS if pressed else CLOSE_HOVER)
            P.rounded(p, box, P.scaled_radius(style, side), fill=wash)
        if not enabled:
            ink = P.legible(opt, P.mix(window, text, 0.35), P.DISABLED_RATIO)
        elif hovered or pressed or opt.state & State.State_Selected:
            ink = text
        else:
            ink = muted(style, opt)
        P.cross(p, box, ink, size=side * 0.42)
    return True


# ---------------------------------------------------------------------------
# QFrame lines and boxes
# ---------------------------------------------------------------------------
def _outline(style, opt):
    return P.legible(opt, P.stroke(opt, P.color(opt, Role.Window), style.outline_strength),
                     style.border_ratio)


def shaped_frame(style, opt, p, w):
    """``HLine``/``VLine``: one flat line; ``Box``/``Panel``/``WinPanel``: a
    flat rounded outline. No bevels, sunken or raised alike.
    ``StyledPanel`` goes on to ``PE_Frame``."""
    if not isinstance(opt, QStyleOptionFrame):
        return False
    shape = opt.frameShape
    lw = max(1, opt.lineWidth)
    r = QRectF(opt.rect)
    if shape in (Shape.HLine, Shape.VLine):
        with P.Painting(p):
            p.setPen(P.pen(_outline(style, opt), lw, round_cap=False))
            if shape == Shape.HLine:
                y = int(r.center().y()) + (0.5 if lw % 2 else 0.0)
                p.drawLine(QLineF(r.left(), y, r.right() + 1, y))
            else:
                x = int(r.center().x()) + (0.5 if lw % 2 else 0.0)
                p.drawLine(QLineF(x, r.top(), x, r.bottom() + 1))
        return True
    if shape in (Shape.Box, Shape.Panel, Shape.WinPanel):
        if w is not None and w.property("dockWidgetContent"):
            return True     # the card is its frame
        cap = _frame_cap.cap_of(w)
        if cap is not None and cap.isVisible():
            return True     # the area's FrameCap draws the outline
        inset = lw / 2
        box = r.adjusted(inset, inset, -inset, -inset)
        with P.Painting(p):
            P.rounded(p, box, style.control_radius, line=_outline(style, opt), width=lw)
        return True
    return False


# ---------------------------------------------------------------------------
# Toolbars and size grips: flat lines in the muted text colour
# ---------------------------------------------------------------------------
#: Grip line length (share of the handle) and the gap between its two lines.
HANDLE_SHARE, HANDLE_GAP = 0.45, 3.0
#: Separator inset from the toolbar's edges.
SEPARATOR_INSET = 4.0


def toolbar_handle(style, opt, p, w):
    """Two short parallel lines across the toolbar's drag handle."""
    horizontal = bool(opt.state & State.State_Horizontal)   # toolbar lies horizontally
    r = QRectF(opt.rect)
    c = r.center()
    with P.Painting(p):
        p.setPen(P.pen(muted(style, opt), 1.0))
        if horizontal:
            half = r.height() * HANDLE_SHARE / 2
            for dx in (-HANDLE_GAP / 2, HANDLE_GAP / 2):
                x = round(c.x() + dx) + 0.5
                p.drawLine(QLineF(x, c.y() - half, x, c.y() + half))
        else:
            half = r.width() * HANDLE_SHARE / 2
            for dy in (-HANDLE_GAP / 2, HANDLE_GAP / 2):
                y = round(c.y() + dy) + 0.5
                p.drawLine(QLineF(c.x() - half, y, c.x() + half, y))
    return True


def toolbar_separator(style, opt, p, w):
    """One line across the toolbar, inset from its edges."""
    horizontal = bool(opt.state & State.State_Horizontal)
    r = QRectF(opt.rect)
    c = r.center()
    with P.Painting(p):
        p.setPen(P.pen(muted(style, opt), 1.0, round_cap=False))
        if horizontal:
            x = int(c.x()) + 0.5
            p.drawLine(QLineF(x, r.top() + SEPARATOR_INSET, x, r.bottom() + 1 - SEPARATOR_INSET))
        else:
            y = int(c.y()) + 0.5
            p.drawLine(QLineF(r.left() + SEPARATOR_INSET, y, r.right() + 1 - SEPARATOR_INSET, y))
    return True


#: Diagonal grip lines, as distances from the corner.
GRIP_LINES = (4.0, 8.0, 12.0)


def size_grip(style, opt, p, w):
    """Three diagonal lines in the grip's corner."""
    r = QRectF(opt.rect)
    corner = getattr(opt, "corner", Qt.Corner.BottomRightCorner)
    right = corner in (Qt.Corner.BottomRightCorner, Qt.Corner.TopRightCorner)
    bottom = corner in (Qt.Corner.BottomRightCorner, Qt.Corner.BottomLeftCorner)
    x0 = r.right() if right else r.left()
    y0 = r.bottom() if bottom else r.top()
    sx = -1.0 if right else 1.0
    sy = -1.0 if bottom else 1.0
    reach = min(r.width(), r.height()) - 1
    with P.Painting(p):
        p.setPen(P.pen(muted(style, opt), 1.0))
        for k in GRIP_LINES:
            if k > reach:
                break
            p.drawLine(QPointF(x0 + sx * k, y0 + sy * 1), QPointF(x0 + sx * 1, y0 + sy * k))
    return True


# ---------------------------------------------------------------------------
# Calendar: weekends in the theme's accent instead of Qt's fixed red
# ---------------------------------------------------------------------------
def _weekend_days(cal: QCalendarWidget):
    working = set(cal.locale().weekdays())
    return [d for d in (Qt.DayOfWeek.Monday, Qt.DayOfWeek.Tuesday, Qt.DayOfWeek.Wednesday,
                        Qt.DayOfWeek.Thursday, Qt.DayOfWeek.Friday, Qt.DayOfWeek.Saturday,
                        Qt.DayOfWeek.Sunday) if d not in working]


def weekend_color(style, cal: QCalendarWidget) -> QColor:
    """The accent, held to the ``text`` floor on the calendar's cells."""
    opt = QStyleOption()
    opt.initFrom(cal)
    return P.legible(opt, P.accent(opt), CONTRAST_TARGETS["text"][style.contrast],
                     surface=P.color(opt, Role.Base))


def tint_weekends(style, cal: QCalendarWidget) -> None:
    fmt = QTextCharFormat()
    fmt.setForeground(QBrush(weekend_color(style, cal)))
    for day in _weekend_days(cal):
        cal.setWeekdayTextFormat(day, fmt)


def untint_weekends(cal: QCalendarWidget) -> None:
    """Qt's own look: weekends in red."""
    fmt = QTextCharFormat()
    fmt.setForeground(QBrush(Qt.GlobalColor.red))
    for day in _weekend_days(cal):
        cal.setWeekdayTextFormat(day, fmt)


class WeekendTint(QObject):
    """Re-tints a calendar's weekends when its palette or style changes (a
    theme switch). One per style, shared by every calendar it polishes."""

    def __init__(self, style):
        super().__init__(style)
        self._style = style

    def attach(self, cal: QCalendarWidget) -> None:
        cal.installEventFilter(self)
        tint_weekends(self._style, cal)

    def detach(self, cal: QCalendarWidget) -> None:
        cal.removeEventFilter(self)
        untint_weekends(cal)

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Type.PaletteChange, QEvent.Type.StyleChange) \
                and isinstance(obj, QCalendarWidget):
            tint_weekends(self._style, obj)
        return False


# ---------------------------------------------------------------------------
# Dispatch tables
# ---------------------------------------------------------------------------
PRIMITIVES = {
    PE.PE_IndicatorTabClose: tab_close,
    PE.PE_IndicatorToolBarHandle: toolbar_handle,
    PE.PE_IndicatorToolBarSeparator: toolbar_separator,
}

CONTROLS = {
    CE.CE_Splitter: splitter,
    CE.CE_ShapedFrame: shaped_frame,
    CE.CE_SizeGrip: size_grip,
}
