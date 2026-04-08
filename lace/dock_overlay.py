# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2019 Ken Lauer
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0

This file is part of Lace, adapted from qtpydocking.
Original code Copyright (c) 2019 Ken Lauer (BSD-3-Clause).
Modifications Copyright (c) 2026 opticsWolf (Apache-2.0).
"""

from typing import Dict, Optional

from PySide6.QtCore import (QEvent, QPoint, QPointF, QRect, Qt, QSizeF, QRectF,
                            QLineF, QTimer)
from PySide6.QtGui import (QColor, QCursor, QHideEvent, QPainter,
                           QPalette, QShowEvent, QPixmap, QPolygonF)
from PySide6.QtWidgets import QFrame, QWidget, QLabel, QGridLayout

# Note: area_alignment removed completely!
from .enums import OverlayMode, DockWidgetArea
from .dock_style_manager import get_dock_style_manager
from .dock_theme import DockStyleCategory


class DockOverlay(QFrame):
    """Overlay widget for showing drop targets during drag operations."""

    def __init__(self, parent: QWidget, mode: OverlayMode):
        super().__init__(parent)
        self._allowed_areas = DockWidgetArea.invalid
        self._cross = None
        self._target_widget = None
        self._target_rect = QRect()
        self._last_location = DockWidgetArea.invalid
        self._drop_preview_enabled = True
        self._mode = mode
        self._drop_area_rect = QRect()

        # Cache for style colors to avoid repeated lookups
        self._cached_frame_color: Optional[QColor] = None
        self._cached_overlay_color: Optional[QColor] = None
        
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setWindowOpacity(1.0)
        self.setWindowTitle("DockOverlay")
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Connect to style manager
        self._style_mgr = get_dock_style_manager()
        self._style_mgr.register(self, DockStyleCategory.OVERLAY)
        
        self._cross = DockOverlayCross(self)
        self._cross.setVisible(False)

    def __repr__(self):
        return f'<DockOverlay mode={self._mode}>'

    def refresh_style(self):
        # Clear cached styles to force reload on next use
        self._cached_frame_color = None
        self._cached_overlay_color = None
        self.update()

    def on_style_changed(self, category: DockStyleCategory, changes: dict):
        self.refresh_style()

    def _get_cached_style_colors(self) -> tuple[QColor, QColor]:
        """Get cached style colors. Fetch from manager if not yet cached."""
        if self._cached_frame_color is None or self._cached_overlay_color is None:
            styles = self._style_mgr.get_all(DockStyleCategory.OVERLAY)
            self._cached_frame_color = styles.get("frame_color", QColor(32, 64, 128, 255))
            self._cached_overlay_color = styles.get("overlay_color", QColor(32, 64, 128, 64))
        return self._cached_frame_color, self._cached_overlay_color

    def set_allowed_areas(self, areas: DockWidgetArea):
        if areas != self._allowed_areas:
            self._allowed_areas = areas
            if self._cross:
                self._cross.reset()

    def allowed_areas(self) -> DockWidgetArea:
        return self._allowed_areas

    def drop_area_under_cursor(self) -> DockWidgetArea:
        result = self._cross.cursor_location() if self._cross else DockWidgetArea.invalid
        if result != DockWidgetArea.invalid:
            return result

        # Simplified fallback logic - actual implementation would be more detailed
        dock_area_widget = self._target_widget
        if hasattr(dock_area_widget, '__class__') and 'DockAreaWidget' in str(type(dock_area_widget)):
            pos = dock_area_widget.mapFromGlobal(QCursor.pos())
            # In a real implementation, this would calculate position-based area detection

        return DockWidgetArea.invalid

    def show_overlay(self, target: QWidget) -> DockWidgetArea:
        if self._target_widget is target:
            da = self.drop_area_under_cursor()
            if da != self._last_location:
                self.repaint()
                self._last_location = da
            return da

        self._target_widget = target
        self._target_rect = QRect()
        self._last_location = DockWidgetArea.invalid

        self.resize(target.size())
        top_left = target.mapToGlobal(target.rect().topLeft())
        self.move(top_left)
        if self._cross:
            self._cross.update_position()
            self._cross.update_overlay_icons()
        self.show()
        
        return self.drop_area_under_cursor()

    def hide_overlay(self):
        self.hide()
        self._target_widget = None
        self._target_rect = QRect()
        self._last_location = DockWidgetArea.invalid

    def enable_drop_preview(self, enable: bool):
        self._drop_preview_enabled = enable
        self.update()

    def drop_overlay_rect(self) -> QRect:
        return self._drop_area_rect

    def event(self, e: QEvent) -> bool:
        result = super().event(e)
        if e.type() == QEvent.Polish and self._cross:
            self._cross.setup_overlay_cross(self._mode)
        return result

    def paintEvent(self, e):
        if not self._drop_preview_enabled:
            self._drop_area_rect = QRect()
            return

        r = self.rect()
        da = self.drop_area_under_cursor()
        factor = (3 if OverlayMode.container == self._mode else 2)

        if da == DockWidgetArea.top:
            r.setHeight(r.height() // factor)
        elif da == DockWidgetArea.right:
            r.setX(int(r.width() * (1 - 1. / factor)))
        elif da == DockWidgetArea.bottom:
            r.setY(int(r.height() * (1 - 1. / factor)))
        elif da == DockWidgetArea.left:
            r.setWidth(r.width() // factor)
        elif da == DockWidgetArea.center:
            r = self.rect()
        else:
            return

        # Use cached colors for better performance
        frame_color, overlay_color = self._get_cached_style_colors()

        painter = QPainter(self)
        pen = painter.pen()
        pen.setColor(frame_color)
        pen.setStyle(Qt.SolidLine)
        pen.setWidth(1)
        pen.setCosmetic(True)
        painter.setPen(pen)
        
        painter.setBrush(overlay_color)
        painter.drawRect(r.adjusted(0, 0, -1, -1))
        self._drop_area_rect = r

        # FIX: End the painter
        painter.end()

    def showEvent(self, e: QShowEvent):
        if self._cross:
            self._cross.show()
        super().showEvent(e)

    def hideEvent(self, e: QHideEvent):
        if self._cross:
            self._cross.hide()
        super().hideEvent(e)

    @property
    def mode(self) -> OverlayMode:
        return self._mode

    @property
    def cross(self):
        return self._cross


class DockOverlayCross(QWidget):
    """Widget that draws the visual indicator for drop areas."""
    
    _all_areas = [
        DockWidgetArea.left,
        DockWidgetArea.right,
        DockWidgetArea.top,
        DockWidgetArea.bottom,
        DockWidgetArea.center,
    ]

    def __init__(self, overlay: DockOverlay):
        super().__init__(overlay.parentWidget())
        self._mode = OverlayMode.dock_area
        self._dock_overlay = overlay
        self._drop_indicator_widgets = {}
        self._grid_layout = None
        
        # Cache for style colors to avoid repeated lookups in icon creation
        self._cached_border_color: Optional[QColor] = None
        self._cached_background_color: Optional[QColor] = None
        self._cached_shadow_color: Optional[QColor] = None
        self._cached_overlay_color: Optional[QColor] = None
        self._cached_arrow_color: Optional[QColor] = None
        
        # Initialize device pixel ratio tracking 
        self._last_device_pixel_ratio = 0.1

        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setWindowTitle("DockOverlayCross")
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Connect to style manager
        self._style_mgr = get_dock_style_manager()
        self._style_mgr.register(self, DockStyleCategory.OVERLAY)
        
        self._grid_layout = QGridLayout()
        self._grid_layout.setSpacing(0)
        self.setLayout(self._grid_layout)

    def refresh_style(self):
        # Clear cached styles to force reload on next use
        self._cached_border_color = None
        self._cached_background_color = None
        self._cached_shadow_color = None
        self._cached_overlay_color = None
        self._cached_arrow_color = None
        
        # Force the pixel ratio check to fail so icons actually redraw!
        self._last_device_pixel_ratio = -1 
        
        self.update_overlay_icons()
        self.update()

    def on_style_changed(self, category: DockStyleCategory, changes: dict):
        self.refresh_style()

    def _get_cached_style_colors(self) -> tuple[QColor, QColor, QColor, QColor, QColor]:
        """Get cached style colors. Fetch from manager if not yet cached."""
        if (self._cached_border_color is None or 
            self._cached_background_color is None or
            self._cached_shadow_color is None or
            self._cached_overlay_color is None or
            self._cached_arrow_color is None):
            
            styles = self._style_mgr.get_all(DockStyleCategory.OVERLAY)
            self._cached_border_color = styles.get("frame_color", QColor(32, 64, 128, 255))
            self._cached_background_color = styles.get("background_color", QColor(38, 41, 46, 255))
            self._cached_shadow_color = styles.get("shadow_color", QColor(0, 0, 0, 64))
            self._cached_overlay_color = styles.get("overlay_color", QColor(32, 64, 128, 64))
            self._cached_arrow_color = styles.get("arrow_color", QColor(200, 205, 215, 255))
        return (self._cached_border_color,
                self._cached_background_color,
                self._cached_shadow_color,
                self._cached_overlay_color,
                self._cached_arrow_color)

    def _area_grid_position(self, area: DockWidgetArea) -> QPoint:
        area_positions = {
            OverlayMode.dock_area: {
                DockWidgetArea.top: QPoint(1, 2),
                DockWidgetArea.right: QPoint(2, 3),
                DockWidgetArea.bottom: QPoint(3, 2),
                DockWidgetArea.left: QPoint(2, 1),
                DockWidgetArea.center: QPoint(2, 2),
            },
            OverlayMode.container: {
                DockWidgetArea.top: QPoint(0, 2),
                DockWidgetArea.right: QPoint(2, 4),
                DockWidgetArea.bottom: QPoint(4, 2),
                DockWidgetArea.left: QPoint(2, 0),
                DockWidgetArea.center: QPoint(2, 2),
            },
        }
        return area_positions[self._mode].get(area, QPoint())

    def _create_drop_indicator_widget(self, area: DockWidgetArea) -> QLabel:
        """Create a drop indicator widget for the specified area."""
        l = QLabel()
        l.setObjectName("DockWidgetAreaLabel")
        
        # Set up the pixmap with proper dimensions
        metric = 3.0 * l.fontMetrics().height()
        size = QSizeF(metric, metric)
        l.setPixmap(self._create_high_dpi_drop_indicator_pixmap(size, area))
        l.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        l.setAttribute(Qt.WA_TranslucentBackground)
        l.setProperty("dockWidgetArea", area)
        return l

    def _update_drop_indicator_icon(self, label: QLabel):
        """Update the drop indicator icon for a specific widget."""
        metric = 3.0 * label.fontMetrics().height()
        size = QSizeF(metric, metric)
        area = label.property("dockWidgetArea")
        label.setPixmap(
            self._create_high_dpi_drop_indicator_pixmap(size, area)
        )

    def _create_high_dpi_drop_indicator_pixmap(
            self, size: QSizeF, area: DockWidgetArea) -> QPixmap:
        """Create a high-DPI drop indicator pixmap for the specified area."""
        
        # Use cached colors for better performance
        border_color, background_color, shadow_color, overlay_color, arrow_color = \
            self._get_cached_style_colors()

        window = self.window()
        device_pixel_ratio = window.devicePixelRatio() if window else 1.0

        pixmap_size = QSizeF(size * device_pixel_ratio)
        pm = QPixmap(pixmap_size.toSize())
        pm.fill(QColor(0, 0, 0, 0))
        p = QPainter(pm)
        
        # Enable antialiasing for smooth edges
        p.setRenderHint(QPainter.Antialiasing)

        shadow_rect = QRectF(pm.rect())

        base_rect = QRectF()
        base_rect.setSize(shadow_rect.size() * 0.7)
        base_rect.moveCenter(shadow_rect.center())

        # Draw shadow background  
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

        # Get the size of a regular element for reference
        baseSize = base_rect.size()
        
        # Handle container mode special cases  
        if (OverlayMode.container == self._mode and area != DockWidgetArea.center):
            base_rect = area_rect

        p.fillRect(base_rect, background_color)
        
        # Draw active area rectangle with border
        if area_rect.isValid():
            pen = p.pen()
            pen.setColor(border_color)
            p.setBrush(overlay_color)
            p.setPen(Qt.NoPen)
            p.drawRect(area_rect)
            
            # Add dashed line to indicate direction
            pen = p.pen()
            pen.setWidth(1)
            pen.setColor(border_color)
            pen.setStyle(Qt.DashLine)
            p.setPen(pen)
            p.drawLine(area_line)

        p.restore()
        p.save()

        # Draw outer border 
        pen = p.pen()
        pen.setColor(border_color)
        pen.setWidth(1)
        p.setBrush(Qt.NoBrush)
        p.setPen(pen)
        p.drawRect(base_rect)

        # draw window title bar
        p.setBrush(border_color)
        frame_rect = QRectF(base_rect.topLeft(),
                            QSizeF(base_rect.width(), baseSize.height() / 10))
        p.drawRect(frame_rect)
        
        p.restore()

        # Draw arrow for outer container drop indicators
        if (OverlayMode.container == self._mode and area != DockWidgetArea.center):
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

        # FIX: Explicitly end the painter to release the C++ lock before handing it to the UI
        p.end()

        pm.setDevicePixelRatio(device_pixel_ratio)
        return pm

    def cursor_location(self) -> DockWidgetArea:
        """Determine which drop area the cursor is currently over."""
        pos = self.mapFromGlobal(QCursor.pos())
        allowed_areas = self._dock_overlay.allowed_areas()
        
        for area, widget in self._drop_indicator_widgets.items():
            if (area in allowed_areas and widget
                    and widget.isVisible()
                    and widget.geometry().contains(pos)):
                return area
                
        return DockWidgetArea.invalid

    def setup_overlay_cross(self, mode: OverlayMode):
        """Initialize the overlay cross with widgets for all areas."""
        self._mode = mode
        area_widgets = {
            area: self._create_drop_indicator_widget(area)
            for area in self._all_areas
        }
        self.set_area_widgets(area_widgets)

    def update_overlay_icons(self):
        """Update all drop indicator icons based on current device pixel ratio."""
        # Check if device pixel ratio has changed to avoid unnecessary updates
        window = self.window()
        if not window:
            return
            
        device_pixel_ratio = window.devicePixelRatio()
        if device_pixel_ratio == self._last_device_pixel_ratio:
            return

        for widget in self._drop_indicator_widgets.values():
            self._update_drop_indicator_icon(widget)

        self._last_device_pixel_ratio = device_pixel_ratio

    def reset(self):
        """Reset visibility of drop indicators based on allowed areas."""
        allowed_areas = self._dock_overlay.allowed_areas()
        
        # This would normally be implemented to show/hide widgets
        # but we're maintaining the simplified structure for now
        pass

    def update_position(self):
        """Update position and size of the overlay cross."""
        self.resize(self._dock_overlay.size())
        top_left = self._dock_overlay.pos()
        
        offset = QPoint(
            (self.width() - self._dock_overlay.width()) // 2,
            (self.height() - self._dock_overlay.height()) // 2
        )
        cross_top_left = top_left - offset
        self.move(cross_top_left)

    def showEvent(self, event: QShowEvent):
        """Handle showing the overlay cross."""
        if not self._drop_indicator_widgets:
            self.setup_overlay_cross(self._mode)
        self.update_position()

    def set_area_widgets(self, widgets: dict):
        """Set the area widgets for all drop indicators."""
        # Delete old widgets.
        for area, widget in self._drop_indicator_widgets.items():
            self._grid_layout.removeWidget(widget)
            widget.deleteLater()

        self._drop_indicator_widgets.clear()

        # Insert new widgets into grid.
        self._drop_indicator_widgets = widgets
        for area, widget in self._drop_indicator_widgets.items():
            pos = self._area_grid_position(area)
            self._grid_layout.addWidget(widget, pos.x(), pos.y())

        if OverlayMode.dock_area == self._mode:
            self._grid_layout.setContentsMargins(0, 0, 0, 0)
            stretch_values = [1, 0, 0, 0, 1]
        else:
            self._grid_layout.setContentsMargins(4, 4, 4, 4)
            stretch_values = [0, 1, 1, 1, 0]

        for i, stretch in enumerate(stretch_values):
            self._grid_layout.setRowStretch(i, stretch)
            self._grid_layout.setColumnStretch(i, stretch)

        self.reset()
