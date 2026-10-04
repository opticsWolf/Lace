# -*- coding: utf-8 -*-
"""Rounded popups with a soft shadow: menus, combo box drop-down lists and
list popups such as a ``QCompleter``'s.

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

#: Where a popup's radius sits between its controls' (0) and the dock
#: cards' (1): a popup is a floating panel holding controls, rounder than
#: the controls but not as round as a card.
RADIUS_BLEND = 1 / 3
#: Transparent margin around a rounded popup's panel, where its shadow falls.
SHADOW = 5
#: How far the shadow drops below the panel.
SHADOW_DROP = 1
#: Shadow opacity at the panel's edge, on dark and on light surfaces.
SHADOW_DARK, SHADOW_LIGHT = 0.26, 0.09

#: Marks a popup this style made translucent, so ``unpolish`` undoes only that.
_ROUNDED = "_laceRoundedPopup"
#: The margins a combo popup was given, taken back exactly on ``unpolish``.
_PAD = "_laceRoundedPopupPad"
#: The padding this style added to a list popup's viewport margins.
_VIEWPORT_PAD = "_laceRoundedPopupViewportPad"
#: A list popup's viewport filled itself before this style turned that off.
_VIEWPORT_FILL = "_laceRoundedPopupViewportFill"
#: The geometry ``ShadowShift`` last gave a list popup, to tell its own
#: moves from the ones Qt makes as the list grows and shrinks.
_PLACED = "_laceRoundedPopupPlaced"
#: The window hints this style added, taken back exactly on ``unpolish``.
_ADDED = "_laceRoundedPopupHints"
#: A rounded popup has no native frame or (square) native shadow.
_HINTS = (Qt.WindowType.FramelessWindowHint, Qt.WindowType.NoDropShadowWindowHint)


def radius(style) -> float:
    """Corner radius of a popup; square when controls are.

    ``control + (corner - control) * RADIUS_BLEND``, rounded to whole
    pixels and never below the controls' own radius: 4 px on the classic
    chassis (4 / 4), 6 px on neo (control 4, cards 10).
    """
    control = style.control_radius
    if control <= 0:
        return 0.0
    blended = control + (style.corner_radius - control) * RADIUS_BLEND
    return float(max(control, round(blended)))


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


def is_list_popup(w) -> bool:
    """An item view that is its own popup window: a ``QCompleter``'s list
    (Qt reparents it to no parent with ``Qt.Popup``), or an app's drop-down
    list made the same way."""
    return (isinstance(w, QAbstractItemView) and w.isWindow()
            and (w.windowType() == Qt.WindowType.Popup))


def list_fill(w, opt) -> QColor:
    """The colour a list popup's rows sit on: its viewport's Base."""
    return w.palette().color(opt.palette.currentColorGroup(), Role.Base)


def is_popup(w) -> bool:
    return (isinstance(w, QMenu) or is_combo_popup(w) or is_list_popup(w)) and w.isWindow()


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
    if is_list_popup(w):
        # A QFrame keeps its frame width as its contents margins, so a list
        # popup takes the shadow margin through its frame width
        # (PM_DefaultFrameWidth) and the padding at its ends through its
        # viewport margins.
        _sync_list_pad(w, pad(style))
        w.setFrameStyle(w.frameStyle())     # re-reads the frame width
        if w.viewport().autoFillBackground():
            # The panel paints the rows' ground, rounded; a square viewport
            # fill would cover its corners.
            w.viewport().setAutoFillBackground(False)
            w.setProperty(_VIEWPORT_FILL, True)
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
    if is_list_popup(w):
        _sync_list_pad(w, 0)
        w.setFrameStyle(w.frameStyle())     # back to the plain frame width
    if w.property(_VIEWPORT_FILL):
        w.viewport().setAutoFillBackground(True)
        w.setProperty(_VIEWPORT_FILL, None)
    w.setProperty(_PLACED, None)


def _sync_list_pad(w, ends: int) -> None:
    """Set the padding this style keeps in a list popup's viewport margins
    (above and below its rows) to ``ends``, keeping the app's own margins."""
    old = w.property(_VIEWPORT_PAD) or 0
    if ends == old:
        return
    m = w.viewportMargins()
    w.setViewportMargins(m.left(), max(0, m.top() - old) + ends,
                         m.right(), max(0, m.bottom() - old) + ends)
    w.setProperty(_VIEWPORT_PAD, ends or None)


def _place_list_popup(w) -> None:
    """Grow a list popup around the rect Qt gave it, so its panel covers that
    rect: wider by the shadow on each side, taller by the shadow and padding
    at each end. Below its anchor the panel's top stays on Qt's; above it
    (no room below), its bottom does."""
    g = w.geometry()
    if g == w.property(_PLACED):
        return      # this filter's own move, or Qt hasn't moved it since
    _sync_list_pad(w, pad(w.style()))     # the theme may have changed the radius
    s, ends = SHADOW, SHADOW + pad(w.style())
    y = g.y() - s
    anchor = QApplication.focusWidget()
    if anchor is not None and anchor is not w:
        if g.bottom() <= anchor.mapToGlobal(anchor.rect().center()).y():
            y = g.y() - s - 2 * (ends - s)
    placed = QRect(g.x() - s, y, g.width() + 2 * s, g.height() + 2 * ends)
    w.setProperty(_PLACED, placed)
    w.setGeometry(placed)


class ShadowShift(QObject):
    """Moves a rounded popup back by its shadow margin as it shows, so its
    panel lands where Qt placed the window. Qt sends Show before the native
    window appears, so the move never flickers.

    A list popup (``QCompleter``) is placed again whenever Qt moves or
    resizes it, which it does on every keystroke as the matches change."""

    _LIST_EVENTS = (QEvent.Type.Show, QEvent.Type.Move, QEvent.Type.Resize)

    def eventFilter(self, obj, event):
        if is_list_popup(obj) and is_rounded(obj):
            if event.type() == QEvent.Type.Hide:
                obj.setProperty(_PLACED, None)
            elif event.type() in self._LIST_EVENTS and obj.isVisible():
                _place_list_popup(obj)
            return False
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
