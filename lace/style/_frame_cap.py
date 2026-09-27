# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.

"""Rounded corners for framed scroll areas (text edits, list, tree and table
views) under LaceStyle.

The frame's outline is rounded, but the viewport inside is a square child
that paints over the arc. :class:`FrameCap` is a transparent overlay above
the viewport and scroll bars: it paints the backdrop over the corners outside
the rounded frame, antialiased, then strokes the outline. This is the same
technique the dock card uses for ``corner_clip="cap"``.
"""

from PySide6.QtCore import QEvent, QObject, QRectF, Qt
from PySide6.QtGui import QPainter, QPainterPath
from PySide6.QtWidgets import QAbstractScrollArea, QFrame, QStyle, QStyleOptionFrame, QWidget

from lace.dock_paint import corner_cap_path, paint_corner_cap

#: Attribute on the scroll area holding its cap.
ATTR = "_lace_frame_cap"


def wants_cap(w: QWidget) -> bool:
    """A framed scroll area that isn't a combo box's popup list."""
    if not isinstance(w, QAbstractScrollArea):
        return False
    parent = w.parentWidget()
    return parent is None or not parent.inherits("QComboBoxPrivateContainer")


def cap_of(w: QWidget):
    return getattr(w, ATTR, None) if w is not None else None


class FrameCap(QWidget):
    """Overlay that caps a scroll area's corners and draws its frame."""

    def __init__(self, area: QAbstractScrollArea, style):
        super().__init__(area)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setAutoFillBackground(False)
        self._area = area
        self._style = style
        self._key = None
        self._cap = QPainterPath()
        setattr(area, ATTR, self)
        area.installEventFilter(self)
        self.restack()

    def detach(self) -> None:
        self._area.removeEventFilter(self)
        if getattr(self._area, ATTR, None) is self:
            delattr(self._area, ATTR)
        self.setParent(None)
        self.deleteLater()

    def restack(self) -> None:
        self.setGeometry(self._area.rect())
        self.raise_()
        self.update()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        t = event.type()
        if t in (QEvent.Type.Resize, QEvent.Type.Show):
            self.restack()
        elif t == QEvent.Type.ChildAdded and event.child() is not self:
            # A viewport or scroll bar added later would stack above the cap.
            self.raise_()
        return False

    def _active(self) -> bool:
        a = self._area
        return a.frameShape() != QFrame.Shape.NoFrame and not a.property("dockWidgetContent")

    def _cap_path(self, radius: float) -> QPainterPath:
        """The corners outside the frame's rounded outer edge, per size and radius."""
        key = (self.size(), radius)
        if key != self._key:
            rect = QRectF(self.rect())
            keep = QPainterPath()
            keep.addRoundedRect(rect, radius, radius)
            self._key, self._cap = key, corner_cap_path(rect, keep)
        return self._cap

    def paintEvent(self, event) -> None:
        if not self._active():
            return
        from lace.dock_chrome import backdrop_color, has_native_child
        p = QPainter(self)
        radius = float(self._style.control_radius)
        if radius > 0 and not has_native_child(self._area):
            paint_corner_cap(p, self._cap_path(radius), backdrop_color(self._area))
        opt = QStyleOptionFrame()
        opt.initFrom(self._area)
        opt.rect = self.rect()
        opt.frameShape = self._area.frameShape()
        opt.lineWidth = self._area.lineWidth()
        opt.midLineWidth = self._area.midLineWidth()
        # widget=None: the frame primitive skips areas that own a cap, so the
        # outline is drawn once, here, above the viewport.
        self._style.drawPrimitive(QStyle.PrimitiveElement.PE_Frame, opt, p, None)


__all__ = ["FrameCap", "wants_cap", "cap_of"]
