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

A scroll area's viewport is a square child that fills itself, so on its own it
paints over the rounded frame's corners. :class:`RoundedArea` takes the fill
away from it instead of covering it up afterwards:

- the viewport stops filling its background, and the area paints that fill
  itself, rounded and antialiased, beneath the viewport and the outline;
- the viewport, the scroll bars and the corner widget are masked to the rounded
  shape, so content drawn to the edge (a selected row, a scroll bar's groove)
  stays inside it.

Nothing is painted over the corners, so nothing needs to know what lies behind
the area. The corners show whatever is really there: a panel, a gradient, a
translucent window, a widget embedded in a ``QGraphicsScene`` (a Weave node),
or a faded item. The area's own pixels blend with all of these as any widget's
do.

The mask is aliased; it only cuts content that reaches into a corner. The
visible edge is the antialiased fill and outline underneath.

A viewport that did not fill its background (an app's transparent view) gets no
fill, only the mask. Unframed areas, and a dock's own content flush with its
card, are left as they were.
"""

from functools import partial

from PySide6.QtCore import QEvent, QObject, QRectF, Qt, QTimer
from PySide6.QtGui import QPainter, QPainterPath, QPalette, QRegion
from PySide6.QtWidgets import QAbstractScrollArea, QFrame, QWidget

from lace.style import _paint as P

#: Every live controller, by id. PySide keeps a Python child alive only through
#: its parent's wrapper, and a widget Qt created in C++ (a calendar's table, a
#: font combo's list) may have a transient one: without this, the controller's
#: Python half is collected while the C++ object still filters events, and Qt
#: calls into an empty wrapper. Entries leave when the object is destroyed.
_LIVE = {}


def wants_rounding(w: QWidget) -> bool:
    """A scroll area that isn't a combo box's popup list."""
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


def rounding_of(w: QWidget):
    """The area's controller, found among its direct children (a Python
    attribute on the area would vanish with a transient wrapper)."""
    if w is None:
        return None
    return w.findChild(RoundedArea, options=Qt.FindChildOption.FindDirectChildrenOnly)


#: Area events after which the controller re-checks its mode: a theme switch
#: (palette, style), dock content tagged, a viewport or scroll bar added.
_SYNC_EVENTS = (QEvent.Type.Show, QEvent.Type.PaletteChange, QEvent.Type.StyleChange,
                QEvent.Type.DynamicPropertyChange, QEvent.Type.ChildAdded,
                QEvent.Type.ChildRemoved)
#: Child events after which the masks are refitted.
_GEOMETRY_EVENTS = (QEvent.Type.Move, QEvent.Type.Resize, QEvent.Type.Show)


def _native(widget: QWidget) -> bool:
    """Whether ``widget`` holds a native child window, which a mask on its
    parent does not clip (see docs/frameless-webengine-findings.md)."""
    return any(w.testAttribute(Qt.WidgetAttribute.WA_NativeWindow) and not w.isWindow()
               for w in widget.findChildren(QWidget))


class RoundedArea(QObject):
    """Rounds a scroll area: its fill beneath the viewport, its children
    masked to the shape. Owned by the area; see the module docstring."""

    def __init__(self, area: QAbstractScrollArea, style):
        super().__init__(area)
        self._area = area
        self._style = style
        self._active = False
        self._viewport = None
        self._fills = False          # the viewport filled itself before
        self._mask_key = None
        self._masked = []            # children carrying a mask of ours
        self._sync_queued = False
        _LIVE[id(self)] = self
        self.destroyed.connect(partial(_LIVE.pop, id(self), None))
        area.installEventFilter(self)
        self.sync()

    # -- state -------------------------------------------------------------------
    def mode(self):
        """``None``, ``"cap"`` (rounded, no outline) or ``"frame"`` (rounded
        inside an outline).

        A dock widget's own content is framed by the card. Flush with it, the
        card's corners round it and it needs nothing. Inset by the dock's
        content margin on every side, it is a box of its own: rounded, but no
        outline, since its fill already sets it off the panel.
        """
        a = self._area
        if not a.property("dockWidgetContent"):
            return "frame" if a.frameShape() != QFrame.Shape.NoFrame else None
        return "cap" if _inset_in_dock(a) else None

    def is_active(self) -> bool:
        return self._active

    def _radius(self) -> float:
        return float(self._style.control_radius)

    def _wanted(self) -> bool:
        return self.mode() is not None and self._radius() > 0 and not _native(self._area)

    def detach(self) -> None:
        """Hand the area back as it was: viewport fill, no masks."""
        self._deactivate()
        self._area.removeEventFilter(self)
        for child in self._children():
            child.removeEventFilter(self)
        self.setParent(None)
        self.deleteLater()

    def queue_sync(self) -> None:
        """Re-check on the next event pass (safe from inside a paint)."""
        if not self._sync_queued:
            self._sync_queued = True
            QTimer.singleShot(0, self, self.sync)

    def sync(self) -> None:
        """Take the viewport's fill and mask the children when the area is
        rounded; give the fill back and drop the masks when it is not."""
        self._sync_queued = False
        viewport = self._area.viewport()
        if viewport is not self._viewport:
            if self._viewport is not None and self._active:
                self._restore_fill()
            self._viewport = viewport
            self._fills = viewport is not None and viewport.autoFillBackground()
        for child in self._children():
            child.removeEventFilter(self)     # idempotent: no double filters
            child.installEventFilter(self)
        if not self._wanted():
            self._deactivate()
            return
        if not self._active:
            self._active = True
            if self._fills and self._viewport is not None:
                self._viewport.setAutoFillBackground(False)
        self._fit_masks(force=True)
        self._area.update()

    def _deactivate(self) -> None:
        if not self._active:
            return
        self._active = False
        self._restore_fill()
        for child in self._masked:
            try:
                child.clearMask()
            except RuntimeError:      # deleted with its C++ object
                pass
        self._masked = []
        self._mask_key = None
        self._area.update()

    def _restore_fill(self) -> None:
        if self._fills and self._viewport is not None:
            try:
                self._viewport.setAutoFillBackground(True)
            except RuntimeError:
                pass

    # -- shapes ------------------------------------------------------------------
    def fill_shape(self) -> QRectF:
        """Where the fill goes: under the outline, or the contents box."""
        if self.mode() == "frame":
            return P.half_pixel(self._area.rect())
        return QRectF(self._area.contentsRect())

    def clip_path(self) -> QPainterPath:
        """The rounded shape the children are masked to, in area coordinates:
        the contents box, its corners concentric with the outline's."""
        rect = QRectF(self._area.contentsRect())
        radius = self._radius()
        if self.mode() == "frame":
            radius = max(0.0, radius - self._area.frameWidth())
        radius = min(radius, rect.width() / 2, rect.height() / 2)
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        return path

    def _children(self):
        return [c for c in self._area.findChildren(
                    QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly)
                if not c.isWindow()]

    def _fit_masks(self, force: bool = False) -> None:
        children = self._children()
        key = (self._area.size(), self._area.frameWidth(), self._radius(), self.mode(),
               tuple((id(c), c.geometry().getRect(), c.isVisible()) for c in children))
        if not force and key == self._mask_key:
            return
        self._mask_key = key
        region = QRegion(self.clip_path().toFillPolygon().toPolygon())
        masked = []
        for child in children:
            geo = child.geometry()
            own = region.intersected(geo)
            if own == QRegion(geo):
                child.clearMask()         # wholly inside the shape: no mask
                continue
            child.setMask(own.translated(-geo.topLeft()))
            masked.append(child)
        for child in self._masked:
            if child not in masked:
                try:
                    child.clearMask()
                except RuntimeError:
                    pass
        self._masked = masked

    # -- painting ----------------------------------------------------------------
    def _paint_fill(self) -> None:
        """The viewport's background, rounded, beneath everything else."""
        viewport = self._viewport
        if viewport is None:
            return
        area = self._area
        pal = viewport.palette()
        group = (QPalette.ColorGroup.Disabled if not area.isEnabled()
                 else QPalette.ColorGroup.Active if area.isActiveWindow()
                 else QPalette.ColorGroup.Inactive)
        brush = pal.brush(group, viewport.backgroundRole())
        p = QPainter(area)
        with P.Painting(p):
            P.rounded(p, self.fill_shape(), self._radius(), fill=brush)
        p.end()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        t = event.type()
        if obj is self._area:
            if t == QEvent.Type.Paint:
                if self._active != self._wanted():
                    self.queue_sync()       # framed or unframed since last look
                elif self._active and self._fills:
                    self._paint_fill()      # then the area paints its outline
            elif t == QEvent.Type.Resize and self._active:
                self._fit_masks()
            elif t in _SYNC_EVENTS:
                self.queue_sync()
        elif self._active and t in _GEOMETRY_EVENTS:
            self._fit_masks()
        return False


__all__ = ["RoundedArea", "wants_rounding", "rounding_of"]
