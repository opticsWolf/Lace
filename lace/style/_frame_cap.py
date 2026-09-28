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

The overlay costs nothing where it has no work: it stays hidden on scroll
areas without a frame (and on flush dock content), and where it is shown it
is masked to the corners and edge strips it paints, so typing or scrolling
in the viewport never repaints it.
"""

from functools import partial
from math import ceil

from PySide6.QtCore import QEvent, QObject, QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QPainter, QPainterPath, QRegion
from PySide6.QtWidgets import QAbstractScrollArea, QFrame, QStyle, QStyleOptionFrame, QWidget

from lace.dock_paint import corner_cap_path, paint_corner_cap

#: Every live cap, by id. PySide keeps a Python child alive only through its
#: parent's wrapper, and a widget Qt created in C++ (a calendar's table, a
#: font combo's list) may have a transient one: without this, the cap's Python
#: half is collected while the C++ overlay still filters and paints, and Qt
#: calls into an empty wrapper. Entries leave when the overlay is destroyed.
_LIVE = {}


def wants_cap(w: QWidget) -> bool:
    """A framed scroll area that isn't a combo box's popup list."""
    if not isinstance(w, QAbstractScrollArea):
        return False
    parent = w.parentWidget()
    return parent is None or not parent.inherits("QComboBoxPrivateContainer")


def _inset_in_dock(w: QWidget) -> bool:
    """Whether ``w`` sits inside its dock widget's content margins on every
    side, clear of the card's edges."""
    d = w.parentWidget()
    while d is not None and not hasattr(d, "_cap_shape"):   # the DockWidget
        d = d.parentWidget()
    if d is None:
        return False
    m = d._layout.contentsMargins()
    return min(m.left(), m.top(), m.right(), m.bottom()) > 0


def cap_of(w: QWidget):
    """The area's cap, found among its direct children (a Python attribute on
    the area would vanish with a transient wrapper)."""
    if w is None:
        return None
    return w.findChild(FrameCap, options=Qt.FindChildOption.FindDirectChildrenOnly)


#: Area events after which the cap re-checks its mode, geometry and mask:
#: a theme switch (palette, style), dock content tagged or margins changed.
_SYNC_EVENTS = (QEvent.Type.Show, QEvent.Type.Resize, QEvent.Type.DynamicPropertyChange,
                QEvent.Type.PaletteChange, QEvent.Type.StyleChange)


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
        self._mask_key = None
        self._sync_queued = False
        _LIVE[id(self)] = self
        self.destroyed.connect(partial(_LIVE.pop, id(self), None))
        area.installEventFilter(self)
        self.hide()
        self.sync()

    def detach(self) -> None:
        self._area.removeEventFilter(self)
        self.setParent(None)
        self.deleteLater()

    def sync(self) -> None:
        """Show the cap only when it has work; keep it covering the area, on
        top, and masked to what it paints."""
        self._sync_queued = False
        mode = self._mode()
        radius = float(self._style.control_radius)
        if mode is None or (mode == "cap" and radius <= 0):
            if self.isVisible():
                self.hide()
            return
        if self.geometry() != self._area.rect():
            self.setGeometry(self._area.rect())
        self._fit_mask(mode, radius)
        self.raise_()
        self.show()
        self.update()

    def _fit_mask(self, mode=None, radius=None) -> None:
        mode = self._mode() if mode is None else mode
        if mode is None:
            return
        radius = float(self._style.control_radius) if radius is None else radius
        key = (self.size(), radius, mode, self._area.frameWidth())
        if key != self._mask_key:
            self._mask_key = key
            self.setMask(self._mask(mode, radius))

    def queue_sync(self) -> None:
        """Re-check on the next event pass (safe from inside a paint)."""
        if not self._sync_queued:
            self._sync_queued = True
            QTimer.singleShot(0, self, self.sync)

    def _mask(self, mode: str, radius: float) -> QRegion:
        """The corner squares, plus the edge strips the outline runs along."""
        r = self.rect()
        fw = self._area.frameWidth()
        s = fw + ceil(radius) + 1
        region = QRegion()
        for x, y in ((r.left(), r.top()), (r.right() - s + 1, r.top()),
                     (r.left(), r.bottom() - s + 1), (r.right() - s + 1, r.bottom() - s + 1)):
            region = region.united(QRect(x, y, s, s))
        if mode == "frame":
            e = max(1, fw) + 1
            for strip in (QRect(r.left(), r.top(), r.width(), e),
                          QRect(r.left(), r.bottom() - e + 1, r.width(), e),
                          QRect(r.left(), r.top(), e, r.height()),
                          QRect(r.right() - e + 1, r.top(), e, r.height())):
                region = region.united(strip)
        return region

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        t = event.type()
        if t == QEvent.Type.Resize and self.isVisible():
            # Follow the area at once; showing and hiding waits for the next
            # pass, so an app-wide palette change never re-enters from here.
            self.setGeometry(self._area.rect())
            self._fit_mask()
        elif t in _SYNC_EVENTS:
            self.queue_sync()
        elif t == QEvent.Type.ChildAdded and event.child() is not self:
            # A viewport or scroll bar added later would stack above the cap.
            self.raise_()
        return False

    def _mode(self):
        """``None``, ``"cap"`` (corners only) or ``"frame"`` (corners and outline).

        A dock widget's own content is framed by the card. Flush with it, the
        card's corners round it and it needs nothing. Inset by the dock's
        content margin on every side, it is a box of its own: it gets rounded
        corners, but no outline, since its fill already sets it off the panel.
        """
        a = self._area
        if not a.property("dockWidgetContent"):
            return "frame" if a.frameShape() != QFrame.Shape.NoFrame else None
        return "cap" if _inset_in_dock(a) else None

    def _cap_path(self, radius: float, inner: bool) -> QPainterPath:
        """The corners outside the rounded shape, per size and radius.

        With an outline the shape is the frame's outer edge. Without one
        (``inner``) the frame strip is bare and the visible box is the
        viewport, so the shape is the contents rect.
        """
        key = (self.size(), radius, inner)
        if key != self._key:
            rect = QRectF(self.rect())
            keep = QPainterPath()
            keep.addRoundedRect(QRectF(self._area.contentsRect()) if inner else rect,
                                radius, radius)
            self._key, self._cap = key, corner_cap_path(rect, keep)
        return self._cap

    def paintEvent(self, event) -> None:
        mode = self._mode()
        if mode is None:
            self.queue_sync()
            return
        from lace.dock_chrome import backdrop_color, has_native_child
        p = QPainter(self)
        radius = float(self._style.control_radius)
        if radius > 0 and not has_native_child(self._area):
            paint_corner_cap(p, self._cap_path(radius, mode != "frame"),
                             backdrop_color(self._area))
        if mode != "frame":
            return
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
