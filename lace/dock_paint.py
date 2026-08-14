# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


from math import ceil, sqrt
from dataclasses import dataclass
from typing import Optional, Tuple

from PySide6.QtCore import Qt, QRectF, QLineF, QPointF, QSizeF
from PySide6.QtGui import QBrush, QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QPolygonF

from lace.enums import DockWidgetArea, OverlayMode

_INV_SQRT2 = 1.0 / sqrt(2.0)

#: The four corners in clockwise order, and the two each edge owns — also
#: clockwise, so ``_EDGE_CORNERS[e][1]`` is where a path that skips ``e``
#: starts and ``[0]`` is where it ends.
_CLOCKWISE = ("top_left", "top_right", "bottom_right", "bottom_left")
_EDGE_CORNERS = {
    Qt.Edge.TopEdge:    ("top_left", "top_right"),
    Qt.Edge.RightEdge:  ("top_right", "bottom_right"),
    Qt.Edge.BottomEdge: ("bottom_right", "bottom_left"),
    Qt.Edge.LeftEdge:   ("bottom_left", "top_left"),
}
_OPPOSITE_EDGE = {
    Qt.Edge.TopEdge:    Qt.Edge.BottomEdge,
    Qt.Edge.BottomEdge: Qt.Edge.TopEdge,
    Qt.Edge.LeftEdge:   Qt.Edge.RightEdge,
    Qt.Edge.RightEdge:  Qt.Edge.LeftEdge,
}


def _corner_arc(rect: QRectF, radius: float,
                corner: str) -> Tuple[QRectF, float, QPointF, QPointF]:
    """``(arc_rect, start_angle, entry, square_point)`` for one corner of ``rect``.

    The sweep is always -90 degrees, so the corners chain into a clockwise
    traversal.  ``entry`` is where the arc meets the incoming edge;
    ``square_point`` is where the corner sits when it is not rounded at all.
    """
    left, top, right, bottom = rect.left(), rect.top(), rect.right(), rect.bottom()
    r, d = radius, 2.0 * radius
    if corner == "top_left":
        return (QRectF(left, top, d, d), 180.0,
                QPointF(left, top + r), QPointF(left, top))
    if corner == "top_right":
        return (QRectF(right - d, top, d, d), 90.0,
                QPointF(right - r, top), QPointF(right, top))
    if corner == "bottom_right":
        return (QRectF(right - d, bottom - d, d, d), 0.0,
                QPointF(right, bottom - r), QPointF(right, bottom))
    return (QRectF(left, bottom - d, d, d), 270.0,
            QPointF(left + r, bottom), QPointF(left, bottom))


def tab_path(rect: QRectF, radius: float,
             flat_edge: Optional[Qt.Edge] = Qt.Edge.BottomEdge,
             closed: bool = True) -> QPainterPath:
    """Path for a tab whose corners on ``flat_edge`` stay square.

    The general form behind every tab outline in Lace.  ``flat_edge`` is the
    side the tab is joined along — the bottom for a dock area's tabs, the
    window-facing or content-facing side for a sidebar's — and its two corners
    keep their right angle while the other two follow ``radius``.  Pass
    ``None`` to round all four, which leaves no edge to open and so is always
    closed.

    With ``closed=False`` the segment *along* ``flat_edge`` is left out, so a
    stroke of the result outlines the other three sides only and the tab reads
    as joined to whatever sits on that side.  Filled, an open path closes
    implicitly and is identical to the closed one, so only ever stroke it.
    """
    path = QPainterPath()
    r = max(0.0, radius)
    flat = _EDGE_CORNERS[flat_edge] if flat_edge is not None else ()
    closed = closed or not flat

    if r <= 0 and closed:
        path.addRect(rect)
        return path

    def rounded(corner: str) -> bool:
        return r > 0 and corner not in flat

    if closed:
        order = _CLOCKWISE
        arc, angle, entry, point = _corner_arc(rect, r, order[0])
        # Start where the first corner meets its incoming edge, so the run back
        # to it — the one edge no corner draws — is what closeSubpath() adds.
        path.moveTo(entry if rounded(order[0]) else point)
    else:
        # The flat edge is skipped: start at its far corner and finish on its
        # near one, covering the other three sides.
        end_corner, start_corner = _EDGE_CORNERS[flat_edge]
        start = _CLOCKWISE.index(start_corner)
        order = tuple(_CLOCKWISE[(start + step) % 4] for step in (1, 2, 3))
        path.moveTo(_corner_arc(rect, r, start_corner)[3])

    for corner in order:
        # arcTo() draws the straight run from the current point to the arc's
        # start itself, so the edges between corners need no lineTo of their own.
        arc, angle, entry, point = _corner_arc(rect, r, corner)
        if rounded(corner):
            path.arcTo(arc, angle, -90.0)
        else:
            path.lineTo(point)
    if closed:
        path.closeSubpath()
    return path


def chrome_content_margin(border_width: float, radius: float) -> int:
    """Inset that keeps a square child clear of the border and corner arcs.

    See :meth:`ChromeTokens.content_margin` for the derivation.  Exposed as a
    free function so widgets nested inside a chrome frame (e.g. a title bar)
    can compute the same inset without owning a :class:`ChromeTokens`.
    """
    corner = radius * (1.0 - _INV_SQRT2) + border_width * _INV_SQRT2
    return ceil(max(border_width, corner))


def top_rounded_path(rect: QRectF, radius: float) -> QPainterPath:
    """Path for a rect with only its two top corners rounded.

    Used for surfaces that sit flush against a lower edge (title bars, tabs):
    the top corners follow the enclosing card, the bottom stays square.
    """
    return tab_path(rect, radius, Qt.Edge.BottomEdge, closed=True)


def bottom_open_path(rect: QRectF, radius: float) -> QPainterPath:
    """Path along the left, bottom and right edges only — the top is left open.

    The mirror of :func:`top_open_path`: a "U" whose bottom corners follow the
    card's radius. Stroked, it outlines a panel whose top edge is closed by
    something else — the rule under a dock area's title bar.
    """
    path = QPainterPath()
    r = max(0.0, radius)
    left, top, right, bottom = rect.left(), rect.top(), rect.right(), rect.bottom()
    if r <= 0:
        path.moveTo(left, top)
        path.lineTo(left, bottom)
        path.lineTo(right, bottom)
        path.lineTo(right, top)
        return path
    d = 2.0 * r
    path.moveTo(left, top)
    path.lineTo(left, bottom - r)
    path.arcTo(left, bottom - d, d, d, 180.0, 90.0)          # bottom-left
    path.lineTo(right - r, bottom)
    path.arcTo(right - d, bottom - d, d, d, 270.0, 90.0)     # bottom-right
    path.lineTo(right, top)
    return path


def top_open_path(rect: QRectF, radius: float) -> QPainterPath:
    """Path along the left, top and right edges only — the bottom is left open.

    :func:`top_rounded_path` without its closing bottom segment.  Stroked, it
    outlines a tab on three sides so the tab reads as joined to the panel
    below, the way a browser tab does; filled it would be identical to the
    closed path, so only stroke it.
    """
    return tab_path(rect, radius, Qt.Edge.BottomEdge, closed=False)


def bottom_rounded_path(rect: QRectF, radius: float) -> QPainterPath:
    """Path for a rect with only its two bottom corners rounded.

    Used for surfaces that sit at the bottom of a rounded card (DockWidget):
    the bottom corners follow the enclosing card, the top stays square.
    """
    return tab_path(rect, radius, Qt.Edge.TopEdge, closed=True)



@dataclass(frozen=True)
class ChromeTokens:
    """Everything needed to paint a rounded, optionally outlined panel."""
    bg: QColor
    border: Optional[QColor] = None
    border_width: float = 0.0
    radius: float = 0.0
    focus_border: Optional[QColor] = None
    #: Draw the outline on the left, right and bottom only, starting below the
    #: title bar — the rule under the title bar closes the top. The fill is
    #: unaffected and still covers the whole rounded card.
    border_below_title: bool = False

    def content_margin(self) -> int:
        """Margin that keeps a square child clear of both the straight border
        and the rounded corner arc.

        The child's corner sits at ``(m, m)`` from the widget corner; the inner
        edge of the stroke is an arc of radius ``radius - border_width`` centred
        at ``(radius, radius)``.  Keeping the corner inside that arc requires
        ``m >= radius*(1 - 1/sqrt2) + border_width/sqrt2``; on the straight
        edges the stroke simply needs ``m >= border_width``.
        """
        return chrome_content_margin(self.border_width, self.radius)


def paint_panel_bg(p: QPainter, rect: QRectF, c: ChromeTokens) -> None:
    """Paint only the filled background of a rounded panel."""
    p.setRenderHint(QPainter.Antialiasing, True)
    w = c.border_width
    inset = (w / 2.0) + 0.5 if w > 0 else 0.0
    r = QRectF(rect).adjusted(inset, inset, -inset, -inset)
    radius = max(0.0, c.radius - inset)

    if c.bg is not None and c.bg.alpha() > 0:
        path = QPainterPath()
        path.addRoundedRect(r, radius, radius)
        p.fillPath(path, c.bg)


def paint_panel_border(p: QPainter, rect: QRectF, c: ChromeTokens,
                       focused: bool = False,
                       top: Optional[float] = None,
                       side_inset: Optional[float] = None) -> None:
    """Paint only the outline stroke of a rounded panel.

    With :attr:`ChromeTokens.border_below_title` and a ``top`` coordinate, the
    stroke covers the left, right and bottom edges only, running up to ``top``
    (the underside of the title bar) instead of closing across it.

    ``side_inset`` moves that three-sided outline inwards by that many pixels
    on the left, right and bottom, so it lines up with the tab strip's own
    outline rather than sitting a couple of pixels outside it.  Pass the
    distance from the panel's edge to the title bar's — the tab column starts
    there, so the leftmost tab's outline and the panel's left edge become one
    continuous line.  Both strokes are then centred half a pen width in from
    that same edge; a mismatch of even half a pixel antialiases into a visible
    step, so this branch deliberately drops the extra half-pixel the closed
    path uses to stay clear of the widget edge (``side_inset`` already provides
    that clearance).
    """
    w = c.border_width
    border_col = c.focus_border if (focused and c.focus_border is not None) else c.border
    if w <= 0 or border_col is None:
        return

    p.setRenderHint(QPainter.Antialiasing, True)

    if c.border_below_title and top is not None:
        # The verticals start at the title bar's bottom edge, so the rule the
        # title bar draws there becomes the fourth side.  The top corner radius
        # is dropped with the top edge — there is no corner left to round.
        m = 0.0 if side_inset is None else max(0.0, float(side_inset))
        inset = m + (w / 2.0)
        r = QRectF(rect).adjusted(inset, 0.0, -inset, -inset)
        r.setTop(min(float(top), r.bottom()))
        path = bottom_open_path(r, max(0.0, c.radius - inset))
    else:
        inset = (w / 2.0) + 0.5
        r = QRectF(rect).adjusted(inset, inset, -inset, -inset)
        path = QPainterPath()
        path.addRoundedRect(r, max(0.0, c.radius - inset), max(0.0, c.radius - inset))

    p.setPen(QPen(border_col, w))
    p.setBrush(Qt.NoBrush)
    p.drawPath(path)


def paint_panel(p: QPainter, rect: QRectF, c: ChromeTokens,
                focused: bool = False) -> None:
    """Paint a rounded panel: fill + optional outline.  THE core primitive."""
    paint_panel_bg(p, rect, c)
    paint_panel_border(p, rect, c, focused)



def _edge_strip(rect: QRectF, edge: Qt.Edge, width: float) -> QRectF:
    """Rect for an indicator strip of ``width`` along one ``edge`` of ``rect``."""
    w = float(width)
    if edge == Qt.Edge.TopEdge:
        return QRectF(rect.left(), rect.top(), rect.width(), w)
    if edge == Qt.Edge.LeftEdge:
        return QRectF(rect.left(), rect.top(), w, rect.height())
    if edge == Qt.Edge.RightEdge:
        return QRectF(rect.right() - w, rect.top(), w, rect.height())
    return QRectF(rect.left(), rect.bottom() - w, rect.width(), w)   # BottomEdge


def _outline_rect(rect: QRectF, inset: float, flat_edge: Optional[Qt.Edge],
                  closed: bool) -> QRectF:
    """``rect`` pulled in by ``inset`` on every side the outline is stroked on.

    The flat edge of an open outline carries no stroke, so nothing has to be
    kept clear of it and the three sides run right down to it.
    """
    sides = {Qt.Edge.LeftEdge: inset, Qt.Edge.TopEdge: inset,
             Qt.Edge.RightEdge: inset, Qt.Edge.BottomEdge: inset}
    if not closed and flat_edge is not None:
        sides[flat_edge] = 0.0
    return rect.adjusted(sides[Qt.Edge.LeftEdge], sides[Qt.Edge.TopEdge],
                         -sides[Qt.Edge.RightEdge], -sides[Qt.Edge.BottomEdge])


def paint_tab(p: QPainter, rect: QRectF, *, bg: Optional[QColor] = None,
              bg_gradient: Optional[Tuple[QColor, QColor]] = None,
              radius: float = 0.0,
              indicator: Optional[QColor] = None, indicator_width: int = 0,
              indicator_edge: Qt.Edge = Qt.Edge.BottomEdge,
              border: Optional[QColor] = None, border_width: float = 0.0,
              flat_edge: Optional[Qt.Edge] = Qt.Edge.BottomEdge,
              border_closed: bool = False) -> None:
    """Paint a tab: rounded background (solid ``bg`` or a horizontal
    ``bg_gradient``) + an optional active-edge indicator strip.

    ``flat_edge`` is the side the tab is joined along, whose two corners stay
    square while the other two follow ``radius`` — the bottom for a dock area's
    tabs, the window- or content-facing side for a sidebar's.  ``None`` rounds
    all four.

    The strip is clipped to the tab path so it follows the rounded corners.
    ``indicator_edge`` selects which of the four edges it hugs — Top/Bottom for
    horizontal dock tabs, Left/Right for the vertical sidebar tabs.

    ``border`` / ``border_width`` add an outline.  By default it skips the flat
    edge, which stays open so the tab reads as joined to whatever sits on that
    side; ``border_closed`` runs it the whole way round instead.  With all four
    corners rounded there is no edge left to open, so the outline is always
    closed.  It is inset by half the pen width so the stroke lands inside the
    tab rather than being clipped in half at its edge.
    """
    p.setRenderHint(QPainter.Antialiasing, True)
    path = tab_path(rect, radius, flat_edge)

    if bg_gradient is not None:
        g = QLinearGradient(rect.topLeft(), rect.topRight())
        g.setColorAt(0.0, bg_gradient[0])
        g.setColorAt(1.0, bg_gradient[1])
        p.fillPath(path, QBrush(g))
    elif bg is not None and bg.alpha() > 0:
        p.fillPath(path, bg)

    if indicator is not None and indicator_width > 0:
        p.save()
        p.setClipPath(path)
        
        edges = []
        if isinstance(indicator_edge, (list, tuple, set)):
            edges = list(indicator_edge)
        elif isinstance(indicator_edge, str):
            edges = [e.strip() for e in indicator_edge.replace(",", " ").split() if e.strip()]
        elif indicator_edge is not None:
            edges = [indicator_edge]
            
        for edge in edges:
            if edge is None or edge == "none":
                continue
            q_edge = edge
            if isinstance(edge, str):
                edge_lower = edge.lower().strip()
                if edge_lower == "top":
                    q_edge = Qt.Edge.TopEdge
                elif edge_lower == "bottom":
                    q_edge = Qt.Edge.BottomEdge
                elif edge_lower == "left":
                    q_edge = Qt.Edge.LeftEdge
                elif edge_lower == "right":
                    q_edge = Qt.Edge.RightEdge
                else:
                    continue
            p.fillRect(_edge_strip(rect, q_edge, indicator_width), indicator)
        p.restore()

    if border is not None and border_width > 0 and border.alpha() > 0:
        inset = border_width / 2.0
        closed = border_closed or flat_edge is None
        outline = tab_path(_outline_rect(rect, inset, flat_edge, closed),
                           max(0.0, radius - inset), flat_edge, closed=closed)
        pen = QPen(border, border_width)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        p.drawPath(outline)


def create_high_dpi_drop_indicator_pixmap(
        size: QSizeF, area: DockWidgetArea, mode: OverlayMode,
        colors: Tuple[QColor, QColor, QColor, QColor, QColor],
        device_pixel_ratio: float = 1.0) -> QPixmap:
    """Create a high-DPI drop indicator pixmap for the specified area."""
    border_color, background_color, shadow_color, overlay_color, arrow_color = colors

    pixmap_size = QSizeF(size * device_pixel_ratio)
    pm = QPixmap(pixmap_size.toSize())
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    
    p.setRenderHint(QPainter.Antialiasing)

    shadow_rect = QRectF(pm.rect())

    base_rect = QRectF()
    base_rect.setSize(shadow_rect.size() * 0.7)
    base_rect.moveCenter(shadow_rect.center())

    p.fillRect(shadow_rect, shadow_color)

    p.save()
    
    area_rect = QRectF()
    area_line = QLineF()
    non_area_rect = QRectF()

    if area == DockWidgetArea.top:
        area_rect = QRectF(base_rect.x(), base_rect.y(), base_rect.width(),
                           base_rect.height() * .5)
        non_area_rect = QRectF(base_rect.x(), shadow_rect.height() * .5,
                               base_rect.width(), base_rect.height() * .5)
        area_line = QLineF(area_rect.bottomLeft(), area_rect.bottomRight())
    elif area == DockWidgetArea.right:
        area_rect = QRectF(shadow_rect.width() * .5, base_rect.y(),
                           base_rect.width() * .5, base_rect.height())
        non_area_rect = QRectF(base_rect.x(), base_rect.y(),
                               base_rect.width() * .5, base_rect.height())
        area_line = QLineF(area_rect.topLeft(), area_rect.bottomLeft())
    elif area == DockWidgetArea.bottom:
        area_rect = QRectF(base_rect.x(), shadow_rect.height() * .5,
                           base_rect.width(), base_rect.height() * .5)
        non_area_rect = QRectF(base_rect.x(), base_rect.y(),
                               base_rect.width(), base_rect.height() * .5)
        area_line = QLineF(area_rect.topLeft(), area_rect.topRight())
    elif area == DockWidgetArea.left:
        area_rect = QRectF(base_rect.x(), base_rect.y(),
                           base_rect.width() * .5, base_rect.height())
        non_area_rect = QRectF(shadow_rect.width() * .5, base_rect.y(),
                               base_rect.width() * .5, base_rect.height())
        area_line = QLineF(area_rect.topRight(), area_rect.bottomRight())

    baseSize = base_rect.size()
    
    if (OverlayMode.container == mode and area != DockWidgetArea.center):
        base_rect = area_rect

    p.fillRect(base_rect, background_color)
    
    if area_rect.isValid():
        pen = p.pen()
        pen.setColor(border_color)
        p.setBrush(overlay_color)
        p.setPen(Qt.NoPen)
        p.drawRect(area_rect)
        
        pen = p.pen()
        pen.setWidth(1)
        pen.setColor(border_color)
        pen.setStyle(Qt.DashLine)
        p.setPen(pen)
        p.drawLine(area_line)

    p.restore()
    p.save()

    pen = p.pen()
    pen.setColor(border_color)
    pen.setWidth(1)
    p.setBrush(Qt.NoBrush)
    p.setPen(pen)
    p.drawRect(base_rect)

    p.setBrush(border_color)
    frame_rect = QRectF(base_rect.topLeft(),
                        QSizeF(base_rect.width(), baseSize.height() / 10))
    p.drawRect(frame_rect)
    
    p.restore()

    if (OverlayMode.container == mode and area != DockWidgetArea.center):
        arrow_rect = QRectF()
        arrow_rect.setSize(baseSize)
        arrow_rect.setWidth(arrow_rect.width() / 4.6)
        arrow_rect.setHeight(arrow_rect.height() / 2)
        arrow_rect.moveCenter(QPointF(0, 0))

        arrow = QPolygonF()
        arrow.append(arrow_rect.topLeft())
        arrow.append(QPointF(arrow_rect.right(), arrow_rect.center().y()))
        arrow.append(arrow_rect.bottomLeft())

        p.setPen(Qt.NoPen)
        p.setBrush(arrow_color)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.translate(non_area_rect.center().x(), non_area_rect.center().y())
        
        if area == DockWidgetArea.top:
            p.rotate(-90)
        elif area == DockWidgetArea.right:
            pass
        elif area == DockWidgetArea.bottom:
            p.rotate(90)
        elif area == DockWidgetArea.left:
            p.rotate(180)

        p.drawPolygon(arrow)

    p.end()

    pm.setDevicePixelRatio(device_pixel_ratio)
    return pm

