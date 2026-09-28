# -*- coding: utf-8 -*-
"""Rounded popups: menus and combo box drop-down lists.

A top-level window is square unless it is translucent, so ``LaceStyle.polish``
makes each popup translucent before its native window exists and drops the
native (square) drop shadow. The panel then paints a rounded fill and outline;
the corners outside it stay clear.

A popup whose window already exists when LaceStyle arrives keeps a square
panel: translucency can't be switched on after creation.
"""

import math

from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QPen
from PySide6.QtWidgets import QMenu, QWidget

from lace.style import _paint as P

Role = QPalette.ColorRole
WA = Qt.WidgetAttribute

#: How much rounder a popup is than the controls inside it.
RADIUS_EXTRA = 2
#: Marks a popup this style made translucent, so ``unpolish`` undoes only that.
_ROUNDED = "_laceRoundedPopup"
#: The padding a combo popup was given, taken back exactly on ``unpolish``.
_PAD = "_laceRoundedPopupPad"
#: The window hints this style added, taken back exactly on ``unpolish``.
_ADDED = "_laceRoundedPopupHints"
#: A rounded popup has no native frame or (square) native shadow.
_HINTS = (Qt.WindowType.FramelessWindowHint, Qt.WindowType.NoDropShadowWindowHint)


def radius(style) -> float:
    """Corner radius of a popup; square when controls are."""
    return style.control_radius + RADIUS_EXTRA if style.control_radius > 0 else 0.0


def is_combo_popup(w) -> bool:
    return isinstance(w, QWidget) and w.inherits("QComboBoxPrivateContainer")


def is_popup(w) -> bool:
    return isinstance(w, QMenu) or is_combo_popup(w)


def is_rounded(w) -> bool:
    return w is not None and bool(w.property(_ROUNDED))


def pad(style) -> int:
    """Space above and below a popup's rows, so they clear the arcs."""
    return math.ceil(radius(style) / 2)


def round_popup(style, w: QWidget) -> None:
    """Make ``w`` translucent and shadowless, if its window doesn't exist yet."""
    if is_rounded(w) or radius(style) <= 0 or w.testAttribute(WA.WA_WState_Created):
        return
    if w.testAttribute(WA.WA_TranslucentBackground):
        return      # the app's own translucent popup: leave it alone
    w.setAttribute(WA.WA_TranslucentBackground, True)
    # Windows composites a translucent window only when it is also frameless.
    # (setWindowFlags: PySide's setWindowFlag drops NoDropShadowWindowHint.)
    added = [h for h in _HINTS if not w.windowFlags() & h]
    for h in added:
        w.setWindowFlags(w.windowFlags() | h)
    w.setProperty(_ROUNDED, True)
    w.setProperty(_ADDED, [int(h.value) for h in added])
    if is_combo_popup(w):
        space = pad(style)
        m = w.contentsMargins()
        w.setContentsMargins(m.left(), m.top() + space, m.right(), m.bottom() + space)
        w.setProperty(_PAD, space)


def unround_popup(style, w: QWidget) -> None:
    """Undo ``round_popup`` while the window doesn't exist yet."""
    if not is_rounded(w) or w.testAttribute(WA.WA_WState_Created):
        return
    w.setAttribute(WA.WA_TranslucentBackground, False)
    for value in w.property(_ADDED) or ():
        w.setWindowFlags(w.windowFlags() & ~Qt.WindowType(value))
    w.setProperty(_ROUNDED, None)
    w.setProperty(_ADDED, None)
    space = w.property(_PAD)
    if space:
        m = w.contentsMargins()
        w.setContentsMargins(m.left(), max(0, m.top() - space), m.right(), max(0, m.bottom() - space))
        w.setProperty(_PAD, None)


def paint(style, opt, p, w, role=Role.Window) -> None:
    """A popup's panel: a flat fill and a 1 px outline, rounded when the
    window is translucent."""
    fill = P.color(opt, role)
    line = P.legible(opt, P.stroke(opt, fill, style.outline_strength), style.border_ratio)
    if is_rounded(w):
        with P.Painting(p):
            P.rounded(p, P.half_pixel(opt.rect), radius(style), fill=fill, line=line)
        return
    p.save()
    p.fillRect(opt.rect, fill)
    p.setPen(QPen(line, 1))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(opt.rect.adjusted(0, 0, -1, -1))
    p.restore()
