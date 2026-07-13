# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


from typing import Iterable, Optional

from PySide6.QtCore import Qt, QEvent, QObject, QPoint, QRectF, QSize, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QAbstractButton, QFrame, QSizePolicy, QToolButton, QWidget

from .dock_paint import ChromeTokens, paint_panel
from .util import start_drag_distance


class DragDetector(QObject):
    """Emits :attr:`drag_started` once the pointer moves past the drag
    threshold with ``button`` held, without consuming the events.

    Replaces the hand-rolled mousePress/Move/Release threshold triplets that
    were duplicated across tabs and title bars.  Because the filter returns
    ``False``, the host widget still receives every event (so clicks / toggles
    keep working); this only *observes* to fire the drag signal.
    """
    drag_started = Signal(QPoint)  # global position where the press began

    def __init__(self, widget: QWidget, button: Qt.MouseButton = Qt.LeftButton):
        super().__init__(widget)
        self._button = button
        self._press_pos = None
        widget.installEventFilter(self)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        t = event.type()
        if t == QEvent.MouseButtonPress and event.button() == self._button:
            self._press_pos = event.globalPosition().toPoint()
        elif t == QEvent.MouseMove and self._press_pos is not None:
            moved = (event.globalPosition().toPoint() - self._press_pos).manhattanLength()
            if moved >= start_drag_distance():
                pos, self._press_pos = self._press_pos, None
                self.drag_started.emit(pos)
        elif t in (QEvent.MouseButtonRelease, QEvent.Leave):
            self._press_pos = None
        return False  # never consume — observers only


def _contrast_step(color: QColor, amount: float) -> QColor:
    """Shift ``color`` by ``amount`` lightness in the contrasting direction
    (lighten a dark colour, darken a light one) — the same rule the theme uses
    to derive hover, so pressed continues that direction a little further.
    """
    l = color.lightnessF()
    delta = amount if l < 0.5 else -amount
    hue = color.hueF()
    if hue < 0:                     # achromatic (grey): hue is undefined
        hue = 0.0
    out = QColor.fromHslF(hue, color.saturationF(),
                          max(0.0, min(1.0, l + delta)))
    out.setAlphaF(color.alphaF())
    return out


class ChromeToolButton(QToolButton):
    """Icon tool button that paints its own rounded hover background instead of
    a ``:hover`` stylesheet colour.

    Only the *hover fill* is painted; sizing (padding / min-size / radius) stays
    a colour-free stylesheet applied by :func:`style_title_bar_buttons`, so the
    exact button metrics are preserved.  Hover is tracked by a settable flag
    (``set_hovered``) — identical under the cursor and in offscreen pixel checks,
    the same pattern ``DockWidgetTab``/``VerticalTabButton`` already use.
    """

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setAutoRaise(True)
        self._hover_bg: Optional[QColor] = None
        self._hover_radius: float = 3.0
        self._hovered = False

    def set_hover_chrome(self, hover_bg: Optional[QColor], radius: float) -> None:
        self._hover_bg = hover_bg
        self._hover_radius = max(0.0, radius)
        self.update()

    def set_hovered(self, on: bool) -> None:
        if on != self._hovered:
            self._hovered = on
            self.update()

    def enterEvent(self, event) -> None:
        self.set_hovered(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.set_hovered(False)
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        pressed = self.isDown()
        if (self.isEnabled() and (self._hovered or pressed)
                and self._hover_bg is not None and self._hover_bg.alpha() > 0):
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing, True)
            path = QPainterPath()
            path.addRoundedRect(QRectF(self.rect()), self._hover_radius, self._hover_radius)
            # Pressed continues the hover's contrasting direction 0.03 further
            # (theme-consistent, unlike a flat dark wash); hover is 0.10.
            fill = _contrast_step(self._hover_bg, 0.03) if pressed else self._hover_bg
            p.fillPath(path, fill)
            p.end()
        super().paintEvent(event)   # icon (and menu arrow) draw on top


def style_title_bar_buttons(
    buttons: Iterable[QAbstractButton],
    *,
    color: QColor = None,
    hover_bg: QColor = None,
    disabled: QColor = None,
    radius: int = 3,
    padding: int = 2,
    size: int = 18,
    icon_size: int = 16,
    expand_vertical: bool = False,
) -> None:
    """Apply the shared icon-button styling used by the dock-area and sidebar
    title bars: uniform sizing + painted rounded hover background.

    The hover background is painted by :class:`ChromeToolButton` (no more
    ``:hover`` colour QSS); the stylesheet applied here carries *sizing only*
    (no colour / no ``palette()`` role), so it neither goes stale on theme
    change nor blocks deleting the theme-bridge nudge.  ``color`` / ``disabled``
    are accepted for call-site compatibility but unused — the icons are
    pre-coloured pixmaps and disabled state greys them automatically.
    """
    css = f"""
        QToolButton {{
            background: transparent;
            border: none;
            border-radius: {radius}px;
            padding: {padding}px;
            min-width: {size}px;
            min-height: {size}px;
        }}
    """
    v_policy = QSizePolicy.Expanding if expand_vertical else QSizePolicy.Fixed
    icon = QSize(icon_size, icon_size)
    for btn in buttons:
        btn.setStyleSheet(css)
        if isinstance(btn, ChromeToolButton):
            btn.set_hover_chrome(hover_bg, radius)
        btn.setSizePolicy(QSizePolicy.Fixed, v_policy)
        btn.setIconSize(icon)


class ChromeFrame(QFrame):
    """A ``QFrame`` that paints an antialiased rounded/outlined panel.

    The widget is transparent to Qt's native fill, so the area outside the
    rounded corners shows the *parent's* background — corners stay clean on
    any canvas colour.  A focus outline is a pen-colour swap only, so toggling
    it never changes geometry (no layout jitter).

    Subclasses (or owners) call :meth:`set_chrome` whenever the theme changes.
    """

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setAutoFillBackground(False)
        self._chrome = ChromeTokens(bg=QColor(0, 0, 0, 0))
        self._chrome_focused = False

    def set_chrome(self, chrome: ChromeTokens) -> None:
        """Apply new chrome tokens and inset the layout so children never
        overlap the outline or the corner arcs."""
        self._chrome = chrome
        layout = self.layout()
        if layout is not None:
            m = chrome.content_margin()
            layout.setContentsMargins(m, m, m, m)
        self.update()

    def set_chrome_focused(self, focused: bool) -> None:
        """Swap to the focus outline colour (repaint only; margins constant)."""
        if focused != self._chrome_focused:
            self._chrome_focused = focused
            self.update()

    def chrome(self) -> ChromeTokens:
        return self._chrome

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        paint_panel(p, QRectF(self.rect()), self._chrome, self._chrome_focused)
