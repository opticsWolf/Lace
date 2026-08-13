# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


from typing import TYPE_CHECKING, List, Optional

from PySide6.QtCore import (Qt, Signal, QPropertyAnimation, QEasingCurve, QSize, QRect,
                            QPoint, QPointF, QEvent)
from PySide6.QtGui import QMouseEvent, QColor, QPainter
from PySide6.QtWidgets import (
    QFrame, QSplitter, QVBoxLayout, QGraphicsDropShadowEffect, QWidget
)

from lace.enums import DockWidgetArea, SideBarFocusBehavior
from lace.dock_styled import DockStyled
from lace.dock_theme import DockStyleCategory
from lace.dock_chrome import resolve_sidebar_title_bar_rule
from lace.sidebar_title_bar import SideBarTitleBar

if TYPE_CHECKING:
    from lace.dock_manager import DockManager
    from lace.dock_widget import DockWidget

_ANIMATION_DURATION_MS = 50
_RESIZE_HANDLE_WIDTH = 6
_MIN_SIDEBAR_WIDTH = 200
_MIN_SIDEBAR_HEIGHT = 150
_MIN_CENTER_GAP = 50  # Minimum space to preserve in center / prevent overlap

class SideBarContainer(QFrame, DockStyled):
    """
    Animated overlay hosting an active dock widget with dynamic 
    resize tracking and keyboard focus management.
    """
    STYLE_CATEGORIES = (DockStyleCategory.SIDEPANEL, DockStyleCategory.CORE, DockStyleCategory.SIDEBAR, DockStyleCategory.TITLE_BAR)
    pin_back_requested = Signal(object)
    drag_unpin_requested = Signal(object)
    close_requested = Signal()
    resize_started = Signal()
    resize_finished = Signal()
    maximize_requested = Signal()
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("autoHideOverlay")
        self.setFrameShape(QFrame.NoFrame)
        self.setAttribute(Qt.WA_Hover, True)
        self.setMouseTracking(True)
        
        self._current_widgets: List['DockWidget'] = []
        self._area = DockWidgetArea.left
        self._is_resizing = False
        # Painted chrome — every one of these is read by paintEvent, which can
        # run before the first refresh_style().  Declared here so the paint code
        # reads them directly instead of guessing a default per access site.
        self._bg: QColor | None = None   # painted in paintEvent (no hex QSS)
        self._corner_radius: float = 0.0
        self._border_width: float = 0.0
        self._border_color: QColor | None = None
        self._focus_border_color: QColor | None = None
        self._sidebar_focused = False

        # Set from outside: SidebarManager assigns the manager right after
        # construction, and show_widget() records where focus came from.
        self._dock_manager: Optional['DockManager'] = None
        self._last_focused_widget: QWidget | None = None
        self._last_focused_dock_widget: Optional['DockWidget'] = None

        self._focus_behavior = SideBarFocusBehavior.take_focus_and_restore
        self.setFocusPolicy(Qt.StrongFocus)
        from PySide6.QtWidgets import QApplication
        qapp = QApplication.instance()
        if qapp:
            qapp.focusChanged.connect(self._on_app_focus_changed)
        
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
        self._slide_anim.finished.connect(self._on_anim_finished)
        self._sliding_in = True
        
        # Content splitter
        self._splitter = QSplitter(Qt.Vertical)
        self._splitter.setHandleWidth(2)
        self._splitter.setChildrenCollapsible(False)
        
        # Title bar (Separated logic)
        self._title_bar = SideBarTitleBar()
        self._title_bar.close_requested.connect(self.close_requested.emit)
        self._title_bar.reattach_requested.connect(self.pin_back_requested.emit)
        self._title_bar.detach_requested.connect(self.drag_unpin_requested.emit)
        self._title_bar.maximize_requested.connect(self._on_maximize_clicked)
        
        # Layout
        self._content_layout = QVBoxLayout(self)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)
        self._content_layout.addWidget(self._title_bar)
        self._content_layout.addWidget(self._splitter, 1)
        
        self._size_hint = QSize(300, 200)
        
        # Maximize state
        self._maximized = False
        self._pre_maximize_size = QSize()

        # --- Style Manager Integration ---
        self._init_dock_style()

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
                # Clamp size_hint if it exceeds new maximums after resize
                if self._area in (DockWidgetArea.left, DockWidgetArea.right):
                    max_w = self._get_max_width()
                    if self._size_hint.width() > max_w:
                        self._size_hint.setWidth(max_w)
                elif self._area in (DockWidgetArea.top, DockWidgetArea.bottom):
                    max_h = self._get_max_height()
                    if self._size_hint.height() > max_h:
                        self._size_hint.setHeight(max_h)
                
                self._update_geometry()
                    
        return super().eventFilter(obj, event)

    # --- Presentation & Focus ---

    @property
    def focus_behavior(self) -> SideBarFocusBehavior:
        return self._focus_behavior

    @focus_behavior.setter
    def focus_behavior(self, behavior: SideBarFocusBehavior):
        self._focus_behavior = behavior

    def show_widget(self, dock_widget: 'DockWidget', area: DockWidgetArea, 
                    animate: bool = True, size: QSize = None):
        if self._focus_behavior in (SideBarFocusBehavior.take_focus_and_restore, SideBarFocusBehavior.take_focus_only):
            from PySide6.QtWidgets import QApplication
            fw = QApplication.focusWidget()
            last_dw = None
            if fw and not self.isAncestorOf(fw):
                self._last_focused_widget = fw
                from lace.dock_widget import DockWidget
                curr = fw
                while curr:
                    if isinstance(curr, DockWidget):
                        last_dw = curr
                        break
                    curr = curr.parentWidget()
            if last_dw is None and self._dock_manager is not None:
                active_area = getattr(self._dock_manager, '_active_dock_area', None)
                if active_area and active_area.current_dock_widget():
                    last_dw = active_area.current_dock_widget()
            self._last_focused_dock_widget = last_dw
        else:
            self._last_focused_widget = None
            self._last_focused_dock_widget = None

        if size:
            self._size_hint = size
        
        self._area = area
        self._current_widgets = [dock_widget]
        
        # Reset maximized state when switching widgets (hover tab switch)
        if self._maximized:
            self._maximized = False
            self._title_bar.update_maximize_state(False)
            self._pre_maximize_size = QSize()
        
        # Update title bar content
        self._title_bar.set_widget(dock_widget)
        
        self._update_layout_margins()
        self._update_shadow_direction()
        
        while self._splitter.count():
            w = self._splitter.widget(0)
            w.hide()
            w.setParent(None)
        
        self._splitter.addWidget(dock_widget)
        dock_widget.show()
        if hasattr(dock_widget, 'refresh_style'):
            dock_widget.refresh_style()
        if hasattr(self._title_bar, 'refresh_style'):
            self._title_bar.refresh_style()
        self._update_geometry()
        
        if animate and not self.isVisible():
            start_rect = self._get_hidden_geometry()
            end_rect = self._get_visible_geometry()
            self.setGeometry(start_rect)
            self.show()
            self.raise_()
            if (bar := self._find_sibling_bar(self._area)):
                bar.raise_()
            
            self._sliding_in = True
            if self._focus_behavior in (SideBarFocusBehavior.take_focus_and_restore, SideBarFocusBehavior.take_focus_only):
                self._focus_inner_widget()
            self._slide_anim.setStartValue(start_rect)
            self._slide_anim.setEndValue(end_rect)
            self._slide_anim.start()
        else:
            self.setGeometry(self._get_visible_geometry())
            self.show()
            self.raise_()
            if (bar := self._find_sibling_bar(self._area)):
                bar.raise_()
            if self._focus_behavior in (SideBarFocusBehavior.take_focus_and_restore, SideBarFocusBehavior.take_focus_only):
                self._focus_inner_widget()

    def _on_app_focus_changed(self, old_widget, new_widget):
        try:
            if not self.isVisible() or new_widget is None:
                if self._sidebar_focused:
                    self._sidebar_focused = False
                    self.update()
                    self._title_bar.refresh_focus_tint()
                return
            
            is_ours = self.isAncestorOf(new_widget) or (new_widget is self)
            if is_ours != self._sidebar_focused:
                self._sidebar_focused = is_ours
                self.update()
                self._title_bar.refresh_focus_tint()
        except RuntimeError:
            pass

    def is_chrome_focused(self) -> bool:
        """Whether this overlay holds focus — the same test its outline paints by.

        Named to match :meth:`DockAreaWidget.is_chrome_focused`, so the title
        bars of both can ask their parent the same question.
        """
        return bool(self._sidebar_focused)

    def _focus_inner_widget(self):
        """Pass keyboard focus to the actual content."""
        if self._current_widgets:
            dock_widget = self._current_widgets[0]
            inner = dock_widget.widget()
            if inner:
                if inner.focusPolicy() == Qt.NoFocus:
                    inner.setFocusPolicy(Qt.StrongFocus)
                inner.setFocus(Qt.OtherFocusReason)
            else:
                if dock_widget.focusPolicy() == Qt.NoFocus:
                    dock_widget.setFocusPolicy(Qt.StrongFocus)
                dock_widget.setFocus(Qt.OtherFocusReason)
            from PySide6.QtWidgets import QApplication
            fw = QApplication.focusWidget()
            if not self.isAncestorOf(fw) and fw is not self:
                self.setFocus(Qt.OtherFocusReason)

    def hide_widget(self, animate: bool = True):
        if not self.isVisible():
            return
        
        if animate:
            self._sliding_in = False
            self._slide_anim.setStartValue(self.geometry())
            self._slide_anim.setEndValue(self._get_hidden_geometry())
            self._slide_anim.start()
        else:
            self._on_hide_finished()

    def _on_maximize_clicked(self):
        """Toggle maximize/restore for the sidebar overlay."""
        if self._maximized:
            self._restore_maximized()
        else:
            self._maximize()
    
    def _maximize(self):
        """Expand the sidebar overlay to fill the center area (like VS Code panel maximize)."""
        parent = self.parentWidget()
        if not parent:
            return
        
        # Save current size
        self._pre_maximize_size = self.size()
        
        # Calculate maximized geometry - expand to fill center area only
        pr = parent.rect()
        gap = 16  # Small gap around the maximized sidebar
        
        # Get tab bar dimensions for constraints
        left_bar = self._find_sibling_bar(DockWidgetArea.left)
        left_bar_width = left_bar.width() if left_bar and left_bar.isVisible() else 0
        
        right_bar = self._find_sibling_bar(DockWidgetArea.right)
        right_bar_width = right_bar.width() if right_bar and right_bar.isVisible() else 0
        
        bottom_bar = self._find_sibling_bar(DockWidgetArea.bottom)
        bottom_bar_height = bottom_bar.height() if bottom_bar and bottom_bar.isVisible() else 0
        
        if self._area == DockWidgetArea.left:
            # Expand to fill center area, capped at 8/3× original width or center area (whichever is smaller)
            center_start = left_bar_width
            center_width = pr.width() - left_bar_width - right_bar_width - gap
            max_width = min(int(self._pre_maximize_size.width() * 8 / 3), center_width, pr.width() - gap)
            new_width = max(_MIN_SIDEBAR_WIDTH, min(max_width, pr.width() - left_bar_width - right_bar_width))
            geo = QRect(center_start, 0, new_width, pr.height())
            
        elif self._area == DockWidgetArea.right:
            # Expand to fill center area, capped at 8/3× original width or center area (whichever is smaller)
            center_width = pr.width() - left_bar_width - right_bar_width - gap
            max_width = min(int(self._pre_maximize_size.width() * 8 / 3), center_width, pr.width() - gap)
            new_width = max(_MIN_SIDEBAR_WIDTH, min(max_width, pr.width() - left_bar_width - right_bar_width))
            center_start = pr.width() - right_bar_width - new_width
            geo = QRect(center_start, 0, new_width, pr.height())
            
        elif self._area == DockWidgetArea.bottom:
            # Expand upward to fill center area
            center_height = pr.height() - bottom_bar_height - gap
            geo = QRect(0, 0, pr.width(), max(_MIN_SIDEBAR_HEIGHT, center_height))
        else:
            geo = QRect(0, 0, pr.width(), pr.height())
        
        self._maximized = True
        self.setGeometry(geo)
        # Don't update _size_hint — keep original size so
        # _get_visible_geometry doesn't miscalculate position
        self._title_bar.update_maximize_state(True)
        
        # Update resize zone cursor
        if self._area == DockWidgetArea.left:
            self.setCursor(Qt.SizeHorCursor)
        elif self._area == DockWidgetArea.right:
            self.setCursor(Qt.SizeHorCursor)
        elif self._area == DockWidgetArea.bottom:
            self.setCursor(Qt.SizeVerCursor)
    
    def _restore_maximized(self):
        """Restore sidebar to its previous size."""
        if not self._maximized:
            return
        
        self._maximized = False
        
        # Restore previous size
        if self._pre_maximize_size.isValid() and self._pre_maximize_size.width() > 0:
            size = self._pre_maximize_size
            # Update _size_hint BEFORE calling _get_visible_geometry so
            # position calculations use the correct width/height
            self._size_hint = size
            geo = self._get_visible_geometry()
            self.setGeometry(geo)
        
        self._title_bar.update_maximize_state(False)
        self._pre_maximize_size = QSize()
        
        # Reset cursor
        self.setCursor(Qt.ArrowCursor)
    
    def _on_anim_finished(self):
        if self._sliding_in:
            if self._focus_behavior in (SideBarFocusBehavior.take_focus_and_restore, SideBarFocusBehavior.take_focus_only):
                self._focus_inner_widget()
        else:
            self._on_hide_finished()
            
    def _on_hide_finished(self):
        self.hide()
        # Reset maximized state so next show starts fresh
        if self._maximized:
            self._maximized = False
            self._title_bar.update_maximize_state(False)
            self._pre_maximize_size = QSize()
        for w in self._current_widgets:
            w.setParent(None)
        self._current_widgets = []
        self._title_bar.set_widget(None)
        if self._focus_behavior == SideBarFocusBehavior.take_focus_and_restore:
            self._restore_previous_focus()
        else:
            self._last_focused_widget = None
            self._last_focused_dock_widget = None

    def _restore_previous_focus(self):
        target_restored = False
        if self._last_focused_widget is not None:
            try:
                w = self._last_focused_widget
                if w and w.isVisible() and not self.isAncestorOf(w):
                    if w.focusPolicy() == Qt.NoFocus:
                        w.setFocusPolicy(Qt.StrongFocus)
                    w.setFocus(Qt.OtherFocusReason)
                    target_restored = True
            except RuntimeError:
                pass

        if not target_restored and self._last_focused_dock_widget is not None:
            try:
                dw = self._last_focused_dock_widget
                if dw and dw.isVisible() and not self.isAncestorOf(dw):
                    inner = dw.widget()
                    if inner and inner.isVisible():
                        if inner.focusPolicy() == Qt.NoFocus:
                            inner.setFocusPolicy(Qt.StrongFocus)
                        inner.setFocus(Qt.OtherFocusReason)
                    else:
                        if dw.focusPolicy() == Qt.NoFocus:
                            dw.setFocusPolicy(Qt.StrongFocus)
                        dw.setFocus(Qt.OtherFocusReason)
                    area = dw.dock_area_widget()
                    if area and hasattr(area, '_dock_manager') and area._dock_manager:
                        area._dock_manager.set_active_dock_area(area)
                    target_restored = True
            except RuntimeError:
                pass

        if not target_restored and self.parentWidget():
            from lace.dock_area_widget import DockAreaWidget
            for child in self.parentWidget().findChildren(DockAreaWidget):
                if child.isVisible() and child.current_dock_widget():
                    dw = child.current_dock_widget()
                    if not self.isAncestorOf(dw) and dw.isVisible():
                        inner = dw.widget()
                        if inner and inner.isVisible():
                            if inner.focusPolicy() == Qt.NoFocus:
                                inner.setFocusPolicy(Qt.StrongFocus)
                            inner.setFocus(Qt.OtherFocusReason)
                        else:
                            if dw.focusPolicy() == Qt.NoFocus:
                                dw.setFocusPolicy(Qt.StrongFocus)
                            dw.setFocus(Qt.OtherFocusReason)
                        if hasattr(child, '_dock_manager') and child._dock_manager:
                            child._dock_manager.set_active_dock_area(child)
                        break
        self._last_focused_widget = None
        self._last_focused_dock_widget = None

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

    def update_title_bar_buttons(self):
        """Update the button states on the title bar."""
        if self._title_bar:
            self._title_bar.update_button_states()

    def _update_layout_margins(self):
        from math import ceil
        bw = self._border_width
        bw_int = ceil(bw + 0.5) if bw > 0 else 0

        title_styles = self._style_mgr.get_all(DockStyleCategory.TITLE_BAR)
        title_margin = title_styles.get("margin")
        m_top = bw_int + (int(title_margin) if title_margin is not None else 0)

        left = bw_int
        right = bw_int
        top = m_top
        bottom = bw_int

        m = max(bw_int, _RESIZE_HANDLE_WIDTH)
        if self._area == DockWidgetArea.left:
            right = m
        elif self._area == DockWidgetArea.right:
            left = m
        elif self._area == DockWidgetArea.bottom:
            top = max(m_top, m)
        elif self._area == DockWidgetArea.top:
            bottom = max(bw_int, m)

        self._content_layout.setContentsMargins(left, top, right, bottom)

    def _update_resize_margins(self):
        self._update_layout_margins()

    def _update_shadow_direction(self):
        if self._area == DockWidgetArea.left:
            self._shadow.setOffset(4, 0)
        elif self._area == DockWidgetArea.right:
            self._shadow.setOffset(-4, 0)
        elif self._area == DockWidgetArea.bottom:
            self._shadow.setOffset(0, -4)
        else:
            self._shadow.setOffset(4, 0)
    
    def _get_max_width(self) -> int:
        """Calculate maximum allowed width based on parent and opposite sidebar."""
        parent = self.parentWidget()
        if not parent:
            return 600
        
        if self._area not in (DockWidgetArea.left, DockWidgetArea.right):
            return parent.width()
        
        available = parent.width()
        
        # Account for our own tab bar
        own_bar = self._find_sibling_bar(self._area)
        own_bar_width = own_bar.width() if own_bar and own_bar.isVisible() else 0
        
        # Account for opposite tab bar to prevent covering it
        opposite_area = (DockWidgetArea.right 
                        if self._area == DockWidgetArea.left 
                        else DockWidgetArea.left)
        opposite_bar = self._find_sibling_bar(opposite_area)
        opposite_bar_width = opposite_bar.width() if opposite_bar and opposite_bar.isVisible() else 0
        
        max_width = available - own_bar_width - opposite_bar_width - _MIN_CENTER_GAP
        return max(_MIN_SIDEBAR_WIDTH, max_width)

    def _get_max_height(self) -> int:
        """Calculate maximum allowed height based on parent."""
        parent = self.parentWidget()
        if not parent:
            return 500
        
        if self._area != DockWidgetArea.bottom:
            return parent.height()
        
        available = parent.height()
        
        # Account for bottom tab bar
        own_bar = self._find_sibling_bar(DockWidgetArea.bottom)
        own_bar_height = own_bar.height() if own_bar and own_bar.isVisible() else 0
        
        max_height = available - own_bar_height - _MIN_CENTER_GAP
        return max(_MIN_SIDEBAR_HEIGHT, max_height)

    def _find_sibling_bar(self, area: DockWidgetArea):
        from lace.sidebar_tab_bar import SideTabBar
        parent = self.parentWidget()
        if parent is None:
            return None
        for child in parent.children():
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
            max_w = self._get_max_width()
            new_width = max(_MIN_SIDEBAR_WIDTH, min(max_w, geo.width() + delta.x()))
            self.setGeometry(geo.x(), geo.y(), new_width, geo.height())
            
        elif self._area == DockWidgetArea.right:
            max_w = self._get_max_width()
            new_width = max(_MIN_SIDEBAR_WIDTH, min(max_w, geo.width() - delta.x()))
            new_x = geo.x() + geo.width() - new_width
            self.setGeometry(new_x, geo.y(), new_width, geo.height())
            
        elif self._area == DockWidgetArea.bottom:
            max_h = self._get_max_height()
            new_height = max(_MIN_SIDEBAR_HEIGHT, min(max_h, geo.height() - delta.y()))
            new_y = geo.y() + geo.height() - new_height
            self.setGeometry(geo.x(), new_y, geo.width(), new_height)
        
        # Auto-exit maximized state when resizing
        if self._maximized:
            self._maximized = False
            self._title_bar.update_maximize_state(False)
            self._size_hint = self.size()
            self.setCursor(Qt.ArrowCursor)
            self._pre_maximize_size = QSize()
        else:
            self._size_hint = self.size()

    # --- Style Manager ---

    def paintEvent(self, event):
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPainterPath, QPen
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        r = QRectF(self.rect())
        radius = self._corner_radius
        bw = self._border_width

        if radius > 0 or bw > 0:
            if bw > 0:
                inset = (bw / 2.0) + 0.5
                r = r.adjusted(inset, inset, -inset, -inset)
            path = QPainterPath()
            if radius > 0:
                path.addRoundedRect(r, radius, radius)
            else:
                path.addRect(r)

            if self._bg is not None and self._bg.alpha() > 0:
                p.fillPath(path, self._bg)

            if bw > 0:
                bcolor = (self._focus_border_color if self._sidebar_focused
                          else self._border_color)
                if bcolor is None:
                    bcolor = self._border_color
                if isinstance(bcolor, QColor) and bcolor.alpha() > 0:
                    pen = QPen(bcolor, bw)
                    p.setPen(pen)
                    p.drawPath(path)
        else:
            if self._bg is not None and self._bg.alpha() > 0:
                p.fillRect(self.rect(), self._bg)

        self._paint_title_stripe(p, r, bw)
        p.end()
        super().paintEvent(event)

    def _paint_title_stripe(self, p, inner: "QRectF", bw: float) -> None:
        """Continue the header's bottom stripe out to the card outline.

        The header cannot reach: the layout insets it by _RESIZE_HANDLE_WIDTH on
        whichever edge the panel is resized from, so its own stripe stopped
        several pixels short of the outline on that side.  Widening the header
        instead would put it over the resize zone, which is hit-tested on this
        widget's mouse events and would then never see them.

        So the same line is drawn here across the full interior, at the same y.
        The header paints its portion on top with identical width and colour --
        both ask resolve_sidebar_title_bar_rule() -- so the two cannot disagree
        and the result reads as one unbroken line.
        """
        from PySide6.QtGui import QPen
        title_bar = self._title_bar
        if title_bar is None or not title_bar.isVisible():
            return

        width, color = resolve_sidebar_title_bar_rule(
            self._style_mgr, self.is_chrome_focused())
        if width <= 0 or color is None or color.alpha() <= 0:
            return

        geo = title_bar.geometry()
        y = geo.y() + geo.height() - width / 2.0
        half = bw / 2.0 if bw > 0 else 0.0
        p.setPen(QPen(color, float(width)))
        p.drawLine(QPointF(inner.left() + half, y), QPointF(inner.right() - half, y))

    def refresh_style(self):
        s = self._style_mgr.get_all(DockStyleCategory.SIDEPANEL)
        core_styles = self._style_mgr.get_all(DockStyleCategory.CORE)
        title_styles = self._style_mgr.get_all(DockStyleCategory.TITLE_BAR)

        self._bg = s.get("bg_normal")

        card_radius = s.get("corner_radius")
        if card_radius is None:
            card_radius = core_styles.get("corner_radius", 0)
        self._corner_radius = float(card_radius) if card_radius is not None else 0.0

        card_border = s.get("border_width")
        if card_border is None or card_border <= 0.0:
            card_border = core_styles.get("border_width", 0.0)
        if card_border is None or card_border <= 0.0:
            card_border = 1.0
        self._border_width = float(card_border)

        bcolor = s.get("border_color")
        if bcolor is None:
            bcolor = core_styles.get("border_color")
        self._border_color = bcolor

        fcolor = s.get("focus_border_color")
        if fcolor is None:
            fcolor = core_styles.get("focus_border_color")
        self._focus_border_color = fcolor

        self._update_layout_margins()

        self.update()

        # Shadow
        shadow_color = s.get("shadow_color")
        if shadow_color:
            self._shadow.setColor(shadow_color)
        self._shadow.setBlurRadius(s.get("shadow_blur_radius", 20))


