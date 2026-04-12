# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0
"""

from typing import TYPE_CHECKING, List, Optional

from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QSize, QRect, QPoint, QEvent
from PySide6.QtGui import QMouseEvent, QColor
from PySide6.QtWidgets import (
    QFrame, QMenu, QSplitter, QVBoxLayout, QHBoxLayout, QLabel,
    QToolButton, QStyle, QGraphicsDropShadowEffect, QWidget
)

from .enums import DockWidgetArea, DockWidgetFeature
from .util import start_drag_distance
from .dock_style_manager import get_dock_style_manager
from .dock_theme import DockStyleCategory
from .sidebar_title_bar import OverlayTitleBar

if TYPE_CHECKING:
    from .dock_widget import DockWidget

_ANIMATION_DURATION_MS = 50
_RESIZE_HANDLE_WIDTH = 6

class SideBarContainer(QFrame):
    """
    Animated overlay hosting an active dock widget with dynamic 
    resize tracking and keyboard focus management.
    """
    pin_back_requested = Signal(object)
    drag_unpin_requested = Signal(object)
    close_requested = Signal()
    resize_started = Signal()
    resize_finished = Signal()
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("autoHideOverlay")
        self.setFrameShape(QFrame.NoFrame)
        self.setAttribute(Qt.WA_Hover, True)
        self.setMouseTracking(True)
        
        self._current_widgets: List['DockWidget'] = []
        self._area = DockWidgetArea.left
        self._is_resizing = False
        
        # Shadow effect
        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(20)
        self._shadow.setColor(QColor(0, 0, 0, 80))
        self._shadow.setOffset(4, 0)
        self.setGraphicsEffect(self._shadow)
        
        # Animation
        self._slide_anim = QPropertyAnimation(self, b"geometry")
        self._slide_anim.setDuration(_ANIMATION_DURATION_MS)
        self._slide_anim.setEasingCurve(QEasingCurve.OutCubic)
        
        # Content splitter
        self._splitter = QSplitter(Qt.Vertical)
        self._splitter.setHandleWidth(2)
        self._splitter.setChildrenCollapsible(False)
        
        # Title bar (Separated logic)
        self._title_bar = OverlayTitleBar()
        self._title_bar.close_requested.connect(self.close_requested.emit)
        self._title_bar.reattach_requested.connect(self.pin_back_requested.emit)
        self._title_bar.detach_requested.connect(self.drag_unpin_requested.emit)
        
        # Layout
        self._content_layout = QVBoxLayout(self)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)
        self._content_layout.addWidget(self._title_bar)
        self._content_layout.addWidget(self._splitter, 1)
        
        self._size_hint = QSize(300, 200)

        # --- Style Manager Integration ---
        self._style_mgr = get_dock_style_manager()
        self._style_mgr.register(self, DockStyleCategory.SIDEPANEL)
        self.refresh_style()

        if parent:
            parent.installEventFilter(self)

        self.hide()

    def setParent(self, parent: QWidget | None):
        """Ensure we monitor the parent for resize events."""
        if self.parentWidget():
            self.parentWidget().removeEventFilter(self)
        super().setParent(parent)
        if parent:
            parent.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.parentWidget() and event.type() == QEvent.Resize:
            if self.isVisible():
                parent_size = event.size()
                
                if self._area in (DockWidgetArea.left, DockWidgetArea.right):
                    self.setFixedHeight(parent_size.height())
                    
                elif self._area in (DockWidgetArea.top, DockWidgetArea.bottom):
                    self.setFixedWidth(parent_size.width())
                    
        return super().eventFilter(obj, event)

    # --- Presentation & Focus ---

    def show_widget(self, dock_widget: 'DockWidget', area: DockWidgetArea, 
                    animate: bool = True, size: QSize = None):
        if size:
            self._size_hint = size
        
        self._area = area
        self._current_widgets = [dock_widget]
        
        # Update title bar content
        self._title_bar.set_widget(dock_widget)
        
        self._update_resize_margins()
        self._update_shadow_direction()
        
        while self._splitter.count():
            w = self._splitter.widget(0)
            w.hide()
            w.setParent(None)
        
        self._splitter.addWidget(dock_widget)
        dock_widget.show()
        self._update_geometry()
        
        if animate and not self.isVisible():
            start_rect = self._get_hidden_geometry()
            end_rect = self._get_visible_geometry()
            self.setGeometry(start_rect)
            self.show()
            
            try:
                self._slide_anim.finished.disconnect(self._focus_inner_widget)
            except RuntimeError:
                pass
                
            self._slide_anim.finished.connect(self._focus_inner_widget)
            self._slide_anim.setStartValue(start_rect)
            self._slide_anim.setEndValue(end_rect)
            self._slide_anim.start()
        else:
            self.setGeometry(self._get_visible_geometry())
            self.show()
            self._focus_inner_widget()
            
        self.raise_()

    def _focus_inner_widget(self):
        """Pass keyboard focus to the actual content."""
        if self._current_widgets:
            dock_widget = self._current_widgets[0]
            inner = dock_widget.widget()
            if inner:
                inner.setFocus()
            else:
                dock_widget.setFocus()

    def hide_widget(self, animate: bool = True):
        if not self.isVisible():
            return
        
        if animate:
            self._slide_anim.setStartValue(self.geometry())
            self._slide_anim.setEndValue(self._get_hidden_geometry())
            self._slide_anim.finished.connect(self._on_hide_finished)
            self._slide_anim.start()
        else:
            self._on_hide_finished()
            
    def _on_hide_finished(self):
        self.hide()
        for w in self._current_widgets:
            w.setParent(None)
        self._current_widgets = []
        self._title_bar.set_widget(None)
        
        try:
            self._slide_anim.finished.disconnect(self._on_hide_finished)
        except RuntimeError:
            pass

    # --- Geometry & Resize ---

    def _get_visible_geometry(self) -> QRect:
        parent = self.parentWidget()
        if not parent:
            return self.geometry()
        
        pr = parent.rect()
        size = self._size_hint
        
        if self._area == DockWidgetArea.left:
            bar = self._find_sibling_bar(DockWidgetArea.left)
            x = bar.width() if bar and bar.isVisible() else 0
            return QRect(x, 0, size.width(), pr.height())
        elif self._area == DockWidgetArea.right:
            bar = self._find_sibling_bar(DockWidgetArea.right)
            bar_w = bar.width() if bar and bar.isVisible() else 0
            return QRect(pr.width() - size.width() - bar_w, 0, 
                        size.width(), pr.height())
        elif self._area == DockWidgetArea.bottom:
            bar = self._find_sibling_bar(DockWidgetArea.bottom)
            bar_h = bar.height() if bar and bar.isVisible() else 0
            return QRect(0, pr.height() - size.height() - bar_h,
                        pr.width(), size.height())
        
        return QRect()
    
    def _get_hidden_geometry(self) -> QRect:
        visible = self._get_visible_geometry()
        if self._area == DockWidgetArea.left:
            return visible.translated(-visible.width(), 0)
        elif self._area == DockWidgetArea.right:
            return visible.translated(visible.width(), 0)
        elif self._area == DockWidgetArea.bottom:
            return visible.translated(0, visible.height())
        return visible
    
    def _update_geometry(self):
        self.setGeometry(self._get_visible_geometry())

    def _update_resize_margins(self):
        m = _RESIZE_HANDLE_WIDTH
        if self._area == DockWidgetArea.left:
            self._content_layout.setContentsMargins(0, 0, m, 0)
        elif self._area == DockWidgetArea.right:
            self._content_layout.setContentsMargins(m, 0, 0, 0)
        elif self._area == DockWidgetArea.bottom:
            self._content_layout.setContentsMargins(0, m, 0, 0)
        else:
            self._content_layout.setContentsMargins(0, 0, 0, 0)

    def _update_shadow_direction(self):
        if self._area == DockWidgetArea.left:
            self._shadow.setOffset(4, 0)
        elif self._area == DockWidgetArea.right:
            self._shadow.setOffset(-4, 0)
        elif self._area == DockWidgetArea.bottom:
            self._shadow.setOffset(0, -4)
        else:
            self._shadow.setOffset(4, 0)
    
    def _find_sibling_bar(self, area: DockWidgetArea):
        from .sidebar_tab_bar import SideTabBar
        for child in self.parentWidget().children():
            if isinstance(child, SideTabBar) and child.area == area:
                return child
        return None
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.isVisible() and self._slide_anim.state() != QPropertyAnimation.Running:
            self._size_hint = self.size()
    
    def mousePressEvent(self, ev: QMouseEvent):
        if self._is_in_resize_zone(ev.position().toPoint()):
            self._is_resizing = True
            self._resize_start_pos = ev.globalPosition().toPoint()
            self._resize_start_geometry = self.geometry()
            self.resize_started.emit()
            ev.accept()
            return
        super().mousePressEvent(ev)
    
    def mouseMoveEvent(self, ev: QMouseEvent):
        if self._is_resizing:
            self._do_resize(ev.globalPosition().toPoint())
            ev.accept()
            return
        
        if self._is_in_resize_zone(ev.position().toPoint()):
            if self._area in (DockWidgetArea.left, DockWidgetArea.right):
                self.setCursor(Qt.SizeHorCursor)
            else:
                self.setCursor(Qt.SizeVerCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        
        super().mouseMoveEvent(ev)
    
    def mouseReleaseEvent(self, ev: QMouseEvent):
        if self._is_resizing:
            self._is_resizing = False
            self.resize_finished.emit()
            ev.accept()
            return
        super().mouseReleaseEvent(ev)
    
    def _is_in_resize_zone(self, pos: QPoint) -> bool:
        if self._area == DockWidgetArea.left:
            return pos.x() >= self.width() - _RESIZE_HANDLE_WIDTH
        elif self._area == DockWidgetArea.right:
            return pos.x() <= _RESIZE_HANDLE_WIDTH
        elif self._area == DockWidgetArea.bottom:
            return pos.y() <= _RESIZE_HANDLE_WIDTH
        return False
    
    def _do_resize(self, global_pos: QPoint):
        delta = global_pos - self._resize_start_pos
        geo = self._resize_start_geometry
        
        if self._area == DockWidgetArea.left:
            new_width = max(200, min(600, geo.width() + delta.x()))
            self.setGeometry(geo.x(), geo.y(), new_width, geo.height())
        elif self._area == DockWidgetArea.right:
            new_width = max(200, min(600, geo.width() - delta.x()))
            self.setGeometry(geo.x() + delta.x(), geo.y(), new_width, geo.height())
        elif self._area == DockWidgetArea.bottom:
            new_height = max(150, min(500, geo.height() - delta.y()))
            self.setGeometry(geo.x(), geo.y() + delta.y(), geo.width(), new_height)
        
        self._size_hint = self.size()

    # --- Style Manager ---

    def refresh_style(self):
        s = self._style_mgr.get_all(DockStyleCategory.SIDEPANEL)

        bg = s.get("bg_normal")
        bg_css = bg.name() if bg else "palette(window)"

        self.setStyleSheet(f"""
            #autoHideOverlay {{
                background-color: {bg_css};
            }}
        """)

        # Shadow
        shadow_color = s.get("shadow_color")
        if shadow_color:
            self._shadow.setColor(shadow_color)
        self._shadow.setBlurRadius(s.get("shadow_blur_radius", 20))

    def on_style_changed(self, category: DockStyleCategory, changes: dict):
        self.refresh_style()