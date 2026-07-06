# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0

dock_chrome — reusable painted-chrome widgets
==============================================

Widgets that render their own rounded / outlined chrome via
:mod:`dock_paint`, instead of hex-baked Qt stylesheets.
"""

from typing import Iterable

from PySide6.QtCore import Qt, QEvent, QObject, QPoint, QRectF, QSize, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QAbstractButton, QFrame, QSizePolicy, QWidget

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
    title bars: transparent face, rounded hover background, uniform sizing.

    Previously this exact stylesheet + sizing loop was duplicated verbatim in
    both title bars; they now both call here.
    """
    color_css = color.name() if color else "palette(text)"
    hover_css = hover_bg.name() if hover_bg else "palette(mid)"
    disabled_css = disabled.name() if disabled else "palette(mid)"

    css = f"""
        QToolButton {{
            color: {color_css};
            background: transparent;
            border: none;
            border-radius: {radius}px;
            padding: {padding}px;
            min-width: {size}px;
            min-height: {size}px;
        }}
        QToolButton:hover {{
            background-color: {hover_css};
        }}
        QToolButton:disabled {{
            color: {disabled_css};
        }}
    """
    v_policy = QSizePolicy.Expanding if expand_vertical else QSizePolicy.Fixed
    icon = QSize(icon_size, icon_size)
    for btn in buttons:
        btn.setStyleSheet(css)
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
