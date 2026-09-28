# -*- coding: utf-8 -*-
"""Rounded popups with a soft shadow: menus and combo box drop-down lists.

A top-level window is square unless it is translucent, so ``LaceStyle.polish``
makes each popup translucent and frameless before its native window exists,
and drops the native (square) drop shadow. The window grows by ``SHADOW`` on
every side; the panel paints a rounded fill and outline inside that margin and
a soft painted shadow in it. When the popup shows, ``ShadowShift`` moves the
window back by the margin, so the panel sits exactly where Qt placed it.

A popup whose window already exists when LaceStyle arrives keeps a square
panel and no shadow: translucency can't be switched on after creation.
"""

import math

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QPalette, QPen
from PySide6.QtWidgets import QAbstractItemView, QApplication, QMenu, QWidget

from lace.style import _paint as P

Role = QPalette.ColorRole
WA = Qt.WidgetAttribute

#: How much rounder a popup is than the controls inside it.
RADIUS_EXTRA = 2
#: Transparent margin around a rounded popup's panel, where its shadow falls.
SHADOW = 8
#: How far the shadow drops below the panel.
SHADOW_DROP = 2
#: Shadow opacity at the panel's edge, on dark and on light surfaces.
SHADOW_DARK, SHADOW_LIGHT = 0.42, 0.16

#: Marks a popup this style made translucent, so ``unpolish`` undoes only that.
_ROUNDED = "_laceRoundedPopup"
#: The margins a combo popup was given, taken back exactly on ``unpolish``.
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


def combo_fill(w, opt) -> QColor:
    """The colour a combo popup's rows sit on, for its panel and padding to
    match them.

    A plain combo's ``QComboMenuDelegate`` fills each row with Window from
    the view's palette resolved over the app's ``QMenu`` palette; an editable
    combo's rows sit on the view's Base.
    """
    view = w.findChild(QAbstractItemView)
    if view is None:
        return P.color(opt, Role.Base)
    group = opt.palette.currentColorGroup()
    delegate = view.itemDelegate()
    if delegate is not None and delegate.inherits("QComboMenuDelegate"):
        menu = view.palette().resolve(QApplication.palette("QMenu"))
        return menu.color(group, Role.Window)
    return view.palette().color(group, Role.Base)


def is_popup(w) -> bool:
    return (isinstance(w, QMenu) or is_combo_popup(w)) and w.isWindow()


def is_rounded(w) -> bool:
    return w is not None and bool(w.property(_ROUNDED))


def pad(style) -> int:
    """Space above and below a popup's rows, so they clear the arcs."""
    return math.ceil(radius(style) / 2)


def margin(w) -> int:
    """The shadow margin around ``w``'s panel: 0 unless it is rounded."""
    return SHADOW if is_rounded(w) else 0


def round_popup(style, w: QWidget, shift: "ShadowShift") -> None:
    """Make ``w`` translucent, frameless and shadowed, if its window doesn't
    exist yet."""
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
        # A menu insets its rows through PM_MenuHMargin/VMargin; a combo's
        # list sits in the container's layout, so it takes contents margins.
        side, ends = SHADOW, SHADOW + pad(style)
        m = w.contentsMargins()
        w.setContentsMargins(m.left() + side, m.top() + ends, m.right() + side, m.bottom() + ends)
        w.setProperty(_PAD, [side, ends])
    w.installEventFilter(shift)


def unround_popup(style, w: QWidget, shift: "ShadowShift") -> None:
    """Undo ``round_popup`` while the window doesn't exist yet."""
    if not is_rounded(w) or w.testAttribute(WA.WA_WState_Created):
        return
    w.removeEventFilter(shift)
    w.setAttribute(WA.WA_TranslucentBackground, False)
    for value in w.property(_ADDED) or ():
        w.setWindowFlags(w.windowFlags() & ~Qt.WindowType(value))
    w.setProperty(_ROUNDED, None)
    w.setProperty(_ADDED, None)
    added = w.property(_PAD)
    if added:
        side, ends = added
        m = w.contentsMargins()
        w.setContentsMargins(max(0, m.left() - side), max(0, m.top() - ends),
                             max(0, m.right() - side), max(0, m.bottom() - ends))
        w.setProperty(_PAD, None)


class ShadowShift(QObject):
    """Moves a rounded popup back by its shadow margin as it shows, so its
    panel lands where Qt placed the window. Qt sends Show before the native
    window appears, so the move never flickers."""

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Show and is_rounded(obj):
            s = SHADOW
            if is_combo_popup(obj):
                # Qt sized the popup to the combo, margins included: widen it
                # by the side margins so the panel matches the combo's width.
                g = obj.geometry()
                obj.setGeometry(g.x() - s, g.y() - s, g.width() + 2 * s, g.height())
            else:
                parent = _parent_menu(obj)
                if parent is None:
                    obj.move(obj.pos() - QPoint(s, s))
                else:
                    # Qt already lifts a submenu by its top margin (shadow
                    # included) to line its first row up with the action;
                    # it only needs pulling back towards its parent.
                    left = obj.geometry().center().x() < parent.geometry().center().x()
                    obj.move(obj.pos() + QPoint(s if left else -s, 0))
        return False


def _parent_menu(menu) -> "QMenu | None":
    """The open menu ``menu`` is a submenu of, if any."""
    parent = QApplication.activePopupWidget()
    if isinstance(parent, QMenu) and parent is not menu:
        if any(a.menu() is menu for a in parent.actions()):
            return parent
    return None


def _shadow(p, panel: QRectF, r: float, strength: float) -> None:
    """A soft shadow: rounded layers, each a little wider and fainter, so the
    opacity falls off (about quadratically) over ``SHADOW`` px."""
    n = SHADOW
    total = n * (n + 1) / 2
    p.setPen(Qt.PenStyle.NoPen)
    for i in range(n, 0, -1):
        layer = QColor(0, 0, 0)
        layer.setAlphaF(min(1.0, strength * (n - i + 1) / total * 1.8))
        p.setBrush(layer)
        spread = panel.adjusted(-i, -i, i, i).translated(0, SHADOW_DROP)
        p.drawRoundedRect(spread, r + i, r + i)


def paint(style, opt, p, w, fill: QColor = None) -> None:
    """A popup's panel: a flat fill (Window unless given) and a 1 px outline.
    Rounded, and over a soft shadow in its margin, when the window is
    translucent."""
    if fill is None:
        fill = P.color(opt, Role.Window)
    line = P.legible(opt, P.stroke(opt, fill, style.outline_strength), style.border_ratio)
    if is_rounded(w):
        s = SHADOW
        panel = QRect(opt.rect).adjusted(s, s, -s, -s)
        r = radius(style)
        strength = SHADOW_DARK if fill.lightnessF() < 0.5 else SHADOW_LIGHT
        with P.Painting(p):
            _shadow(p, QRectF(panel), r, strength)
            P.rounded(p, P.half_pixel(panel), r, fill=fill, line=line)
        return
    p.save()
    p.fillRect(opt.rect, fill)
    p.setPen(QPen(line, 1))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(opt.rect.adjusted(0, 0, -1, -1))
    p.restore()
