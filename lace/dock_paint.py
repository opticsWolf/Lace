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

from .enums import DockWidgetArea, OverlayMode

_INV_SQRT2 = 1.0 / sqrt(2.0)


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
    path = QPainterPath()
    r = max(0.0, radius)
    if r <= 0:
        path.addRect(rect)
        return path
    left, top, right, bottom = rect.left(), rect.top(), rect.right(), rect.bottom()
    d = 2.0 * r
    path.moveTo(left, bottom)
    path.lineTo(left, top + r)
    path.arcTo(left, top, d, d, 180.0, -90.0)          # top-left
    path.lineTo(right - r, top)
    path.arcTo(right - d, top, d, d, 90.0, -90.0)       # top-right
    path.lineTo(right, bottom)
    path.closeSubpath()
    return path


def bottom_rounded_path(rect: QRectF, radius: float) -> QPainterPath:
    """Path for a rect with only its two bottom corners rounded.

    Used for surfaces that sit at the bottom of a rounded card (DockWidget):
    the bottom corners follow the enclosing card, the top stays square.
    """
    path = QPainterPath()
    r = max(0.0, radius)
    if r <= 0:
        path.addRect(rect)
        return path
    left, top, right, bottom = rect.left(), rect.top(), rect.right(), rect.bottom()
    d = 2.0 * r
    path.moveTo(left, top)
    path.lineTo(right, top)
    path.lineTo(right, bottom - r)
    path.arcTo(right - d, bottom - d, d, d, 0.0, -90.0)       # bottom-right
    path.lineTo(left + r, bottom)
    path.arcTo(left, bottom - d, d, d, 270.0, -90.0)         # bottom-left
    path.closeSubpath()
    return path



@dataclass(frozen=True)
class ChromeTokens:
    """Everything needed to paint a rounded, optionally outlined panel."""
    bg: QColor
    border: Optional[QColor] = None
    border_width: float = 0.0
    radius: float = 0.0
    focus_border: Optional[QColor] = None

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


def paint_panel(p: QPainter, rect: QRectF, c: ChromeTokens,
                focused: bool = False) -> None:
    """Paint a rounded panel: fill + optional outline.  THE core primitive.

    Baked-in rules:
      * the pen is inset by ``border_width / 2`` so the stroke is never clipped
        by the widget rect (the classic "my 2px border looks like 1px" bug);
      * fill and stroke follow the *same* path, so there is no seam between
        them and no square bleed at the corners;
      * the host widget must be transparent (see :class:`ChromeFrame`) so the
        area outside the rounded path shows the parent, not this widget's fill.
    """
    p.setRenderHint(QPainter.Antialiasing, True)

    w = c.border_width
    inset = (w / 2.0) + 0.5 if w > 0 else 0.0
    r = QRectF(rect).adjusted(inset, inset, -inset, -inset)
    radius = max(0.0, c.radius - inset)

    path = QPainterPath()
    path.addRoundedRect(r, radius, radius)

    if c.bg is not None and c.bg.alpha() > 0:
        p.fillPath(path, c.bg)

    border_col = c.focus_border if (focused and c.focus_border is not None) else c.border
    if w > 0 and border_col is not None:
        p.setPen(QPen(border_col, w))
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)


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


def paint_tab(p: QPainter, rect: QRectF, *, bg: Optional[QColor] = None,
              bg_gradient: Optional[Tuple[QColor, QColor]] = None,
              radius: float = 0.0,
              indicator: Optional[QColor] = None, indicator_width: int = 0,
              indicator_edge: Qt.Edge = Qt.Edge.BottomEdge) -> None:
    """Paint a tab: top-rounded background (solid ``bg`` or a horizontal
    ``bg_gradient``) + an optional active-edge indicator strip.

    The strip is clipped to the tab path so it follows the rounded corners.
    ``indicator_edge`` selects which of the four edges it hugs — Top/Bottom for
    horizontal dock tabs, Left/Right for the vertical sidebar tabs.
    """
    p.setRenderHint(QPainter.Antialiasing, True)
    path = top_rounded_path(rect, radius)

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
        p.fillRect(_edge_strip(rect, indicator_edge, indicator_width), indicator)
        p.restore()


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

