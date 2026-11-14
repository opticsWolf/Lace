# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2019 Ken Lauer
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace, adapted from qtpydocking.
# Original code Copyright (c) 2019 Ken Lauer (BSD-3-Clause).
# Modifications Copyright (c) 2026 opticsWolf (Apache-2.0).


from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QMouseEvent, QResizeEvent
from PySide6.QtWidgets import QLabel, QWidget


class ElidingLabel(QLabel):
    clicked = Signal()
    double_clicked = Signal()
    #: Emitted when the painted text starts or stops being elided.  Callers
    #: that own the tooltip use it to install or clear the full text.
    elided_changed = Signal(bool)

    def __init__(self, text='', parent: QWidget = None, flags: Qt.WindowFlags = Qt.Widget):
        super().__init__(text, parent=parent, f=flags)

        # Flattened private properties
        self._elide_mode = Qt.ElideNone
        self._text = ''
        self._elided = False

        if text:
            self._text = text

    def _set_elided(self, elided: bool):
        elided = bool(elided)
        if elided != self._elided:
            self._elided = elided
            self.elided_changed.emit(elided)

    def is_elided(self) -> bool:
        return self._elided

    def _elide_text(self, width: int):
        if self._is_mode_elide_none():
            super().setText(self._text)
            self._set_elided(False)
            return

        fm = self.fontMetrics()
        text = fm.elidedText(self._text, self._elide_mode,
                             width - self.margin() * 2 - self.indent())
        if text == "…" and self._text:
            text = self._text[0]

        super().setText(text)
        self._set_elided(bool(self._text) and text != self._text)

    def _is_mode_elide_none(self) -> bool:
        return Qt.ElideNone == self._elide_mode

    def mouseReleaseEvent(self, event: QMouseEvent):
        super().mouseReleaseEvent(event)
        if event.button() != Qt.LeftButton:
            return
        self.clicked.emit()

    def resizeEvent(self, event: QResizeEvent):
        if not self._is_mode_elide_none():
            self._elide_text(event.size().width())
        super().resizeEvent(event)

    def mouseDoubleClickEvent(self, ev: QMouseEvent):
        self.double_clicked.emit()
        super().mouseDoubleClickEvent(ev)

    def elide_mode(self) -> Qt.TextElideMode:
        return self._elide_mode

    def set_elide_mode(self, mode: Qt.TextElideMode):
        self._elide_mode = mode
        self._elide_text(self.size().width())

    def minimumSizeHint(self) -> QSize:
        if not self.pixmap().isNull() or self._is_mode_elide_none():
            return super().minimumSizeHint()

        fm = self.fontMetrics()
        return QSize(fm.horizontalAdvance(self._text[:2] + "…"), fm.height())

    def sizeHint(self) -> QSize:
        if not self.pixmap().isNull() or self._is_mode_elide_none():
            return super().sizeHint()

        fm = self.fontMetrics()
        return QSize(fm.horizontalAdvance(self._text), super().sizeHint().height())

    def setText(self, text: str):
        self._text = text
        if self._is_mode_elide_none():
            super().setText(text)
            self._set_elided(False)
        else:
            self._elide_text(self.size().width())

    def text(self) -> str:
        return self._text