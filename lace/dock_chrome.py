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

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QFrame, QWidget

from .dock_paint import ChromeTokens, paint_panel


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
