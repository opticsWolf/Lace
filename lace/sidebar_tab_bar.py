# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0
"""

from typing import TYPE_CHECKING, Dict, List, Optional

from PySide6.QtCore import Qt, Signal, QPoint, QEvent, QPropertyAnimation, QSize, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QSizePolicy, QLabel, QMenu, QWidget, QToolButton, QScrollArea
)

from .enums import DockWidgetArea, DockWidgetFeature
from .sidebar_tab import VerticalTabButton
from .dock_context_menu import DockMenuMixin, MenuSection
from .dock_style_manager import get_dock_style_manager
from .dock_theme import DockStyleCategory

if TYPE_CHECKING:
    from .dock_widget import DockWidget

class SideTabBar(QFrame, DockMenuMixin):
    """Advanced sidebar with drag-drop reordering, drop zones, unified menus, and overflow scrolling."""
    
    # Generate Tab List, Detach/Reattach, Close, and Close Others automatically
    _menu_sections = MenuSection.TAB_LIST | MenuSection.DETACH | MenuSection.CLOSE | MenuSection.CLOSE_OTHERS
    _menu_close_label = "Close"
    
    tab_hover_enter = Signal(object)
    tab_hover_leave = Signal(object)
    tab_clicked = Signal(object)
    tab_drag_started = Signal(object)
    tab_moved = Signal(object, int)  # button, new_index
    sidebar_activated = Signal()
    
    def __init__(self, area: DockWidgetArea, parent: QWidget = None, width: int = 48):
        super().__init__(parent)
        self._area = area
        self._sidebar_width = width
        self._buttons: List[VerticalTabButton] = []
        self._widget_map: Dict['DockWidget', VerticalTabButton] = {}
        self._drop_indicator: Optional[QLabel] = None
        self._context_menu_widget: Optional['DockWidget'] = None
        
        self.setObjectName("sideTabBar")
        self.setProperty("area", area.name)
        
        # --- 1. Main Outer Layout ---
        self._main_layout = QVBoxLayout()
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)
        self.setLayout(self._main_layout)

        # --- 2. Overflow Scroll Controls ---
        self._scroll_prev_btn = QToolButton()
        self._scroll_prev_btn.setAutoRaise(True)
        self._scroll_next_btn = QToolButton()
        self._scroll_next_btn.setAutoRaise(True)
        
        # --- 3. Total Items Counter ---
        self._counter_lbl = QLabel("0")
        self._counter_lbl.setAlignment(Qt.AlignCenter)

        self._scroll_prev_btn.setArrowType(Qt.UpArrow)
        self._scroll_next_btn.setArrowType(Qt.DownArrow)
        self._scroll_prev_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._scroll_next_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._counter_lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self._scroll_prev_btn.setFixedHeight(16)
        self._scroll_next_btn.setFixedHeight(16)
            
        self._scroll_prev_btn.clicked.connect(lambda: self._scroll_by(-40))
        self._scroll_next_btn.clicked.connect(lambda: self._scroll_by(40))

        # --- 4. Inner Scroll Area (Transparent) ---
        self._scroll_area = QScrollArea()
        self._scroll_area.setFrameShape(QFrame.NoFrame)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setStyleSheet("background: transparent;")
        
        self._scroll_area.setSizeAdjustPolicy(QScrollArea.AdjustToContents)
        
        self._scroll_container = QWidget()
        self._scroll_container.setObjectName("sideTabBarScrollContainer")
        self._scroll_container.setStyleSheet("background: transparent;")
        
        self._scroll_container.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        self._scroll_area.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Expanding)
        
        self._layout = QVBoxLayout()
        self._layout.setContentsMargins(2, 4, 2, 4)
        #self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)
        #self._layout.setSpacing(0)
        self._layout.addStretch(1)
        
        self._scroll_container.setLayout(self._layout)
        self._scroll_area.setWidget(self._scroll_container)
        
        # --- Assemble Main Layout ---
        self._main_layout.addWidget(self._scroll_prev_btn)
        self._main_layout.addWidget(self._scroll_area, 1)
        self._main_layout.addWidget(self._scroll_next_btn)
        self._main_layout.addWidget(self._counter_lbl)
        
        self._scroll_prev_btn.hide()
        self._scroll_next_btn.hide()
        self._counter_lbl.hide()
        
        # FIX: Setting the side tab bar to "Fixed" on the minor axis turns it into a rigid
        # bar. This prevents dock splitters from manually inflating its width.
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setFixedWidth(self._sidebar_width)
        
        # Accept drops
        self.setAcceptDrops(True)

        # --- Style Manager Integration ---
        self._drop_indicator_color = QColor("#007acc")
        self._style_mgr = get_dock_style_manager()
        self._style_mgr.register(self, DockStyleCategory.SIDEBAR)
        self.refresh_style()

        self.hide()

    @property
    def area(self) -> DockWidgetArea:
        return self._area

    # ── Scroll & Overflow Engine ──────────────────────────────────────────

    def _update_scroll_visibility(self):
        """Show/hide shift buttons and the counter badge based on window compression."""
        if not self._buttons:
            self._scroll_prev_btn.hide()
            self._scroll_next_btn.hide()
            self._counter_lbl.hide()
            return

        self._counter_lbl.setText(str(self.tab_count()))

        # Determine required size vs actual physical allowance
        required = self._scroll_container.minimumSizeHint().height()
        available = self.height()

        needs_scroll = required > available
        
        self._scroll_prev_btn.setVisible(needs_scroll)
        self._scroll_next_btn.setVisible(needs_scroll)
        self._counter_lbl.setVisible(needs_scroll)

    def _scroll_by(self, delta: int):
        scrollbar = self._scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.value() + delta)

    def wheelEvent(self, event):
        """Allow smooth mouse wheel scrolling over the sidebar tabs."""
        delta = event.angleDelta().y()
        step = -40 if delta > 0 else 40
        self._scroll_by(step)
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_scroll_visibility()

    # ── DockMenuMixin Interface ───────────────────────────────────────────
    
    def count(self) -> int:
        return len(self._buttons)

    def current_index(self) -> int:
        for i, btn in enumerate(self._buttons):
            if btn.isChecked():
                return i
        return -1

    def is_tab_open(self, index: int) -> bool:
        return True

    def tab(self, index: int):
        return self._buttons[index]

    def _menu_on_switch_tab(self, index: int) -> None:
        if 0 <= index < len(self._buttons):
            self.tab_clicked.emit(self._buttons[index])

    def _menu_dock_area(self):
        return None  # Sidebars don't have a single backing area

    def _menu_dock_widget(self):
        return self._context_menu_widget

    def _menu_is_floating(self) -> bool:
        return False

    def _menu_tab_count(self) -> int:
        """Returns the number of tabs in the sidebar for the mixin's hide/disable logic."""
        return self.count()

    def _menu_is_closable(self) -> bool:
        """Dynamically check if the clicked sidebar tab is allowed to be closed."""
        widget = self._menu_dock_widget()
        return bool(widget and (DockWidgetFeature.closable in widget.features()))

    def _menu_is_floatable(self) -> bool:
        widget = self._menu_dock_widget()
        return bool(widget and (DockWidgetFeature.floatable in widget.features()))

    def _menu_show_close_others(self) -> bool:
        return len(self._buttons) > 1

    def _menu_has_sidebars(self) -> bool:
        return True

    def _menu_close(self):
        widget = self._menu_dock_widget()
        if widget:
            self._close_dock_widget(widget)

    def _menu_close_others(self):
        widget = self._menu_dock_widget()
        if widget:
            btn = self.button_for(widget)
            if btn:
                self._close_others(btn)

    def _menu_detach(self):
        widget = self._menu_dock_widget()
        if widget:
            manager = self._find_manager()
            if manager and hasattr(manager, 'sidebar_manager'):
                manager.sidebar_manager.unpin_widget_floating(widget) # FIX: Added .sidebar_manager
                
    # ─────────────────────────────────────────────────────────────────────

    def add_tab(self, dock_widget: 'DockWidget') -> VerticalTabButton:
        icon = dock_widget.icon() if hasattr(dock_widget, 'icon') else None
        
        btn = VerticalTabButton(
            dock_widget.windowTitle(), icon, parent=self._scroll_container
        )
        btn.setProperty("_dock_widget", dock_widget)
        btn.setAttribute(Qt.WA_Hover, True)
        btn.installEventFilter(self)
        btn.clicked.connect(lambda checked, b=btn: self.tab_clicked.emit(b))
        btn.drag_started.connect(lambda b=btn: self.tab_drag_started.emit(b))
        btn.context_menu_requested.connect(self._on_tab_context_menu)
        btn.close_requested.connect(lambda b=btn: self._close_tab_button(b))
        
        # FIX: Start the button HIDDEN so it doesn't flash at (0,0)
        btn.hide()
        self._layout.insertWidget(self._layout.count() - 1, btn)
        self._buttons.append(btn)
        self._widget_map[dock_widget] = btn
        
        # FIX: Only show the sidebar if we are not in the middle of a startup
        if not self.isVisible() and self.parentWidget() and self.parentWidget().isVisible():
            self.show()
        
        # FIX: Defer showing the sidebar until the layout engine has positioned it.
        # This prevents the "ghost" rendering at (0,0) during app startup.
        if not self.isVisible():
            QTimer.singleShot(0, self.show)
            
        target_size = self._get_button_max_size(btn)
        
        # FIX: Initialize the expanding axis fully open so the button slides natively along 1 axis.
        btn.setMaximumSize(16777215, 0)
        
        anim = QPropertyAnimation(btn, b"maximumSize", self) 
        anim.setDuration(100)
        anim.setEndValue(target_size)
        anim.finished.connect(self._update_scroll_visibility)
        anim.finished.connect(self.updateGeometry) 
        # FIX: Show the button only when the animation starts
        btn.show() 
        anim.start()
        
        self._update_scroll_visibility()
        self.updateGeometry() 
        return btn
    
    def _get_button_max_size(self, btn: VerticalTabButton) -> QSize:
        """Allow sufficient space based on the button's own text content hint."""
        hint = btn.sizeHint()
        return QSize(16777215, max(40, hint.height() + 10))
    
    def remove_tab(self, dock_widget: 'DockWidget'):
        btn = self._widget_map.pop(dock_widget, None)
        if btn is None:
            return
        
        btn.removeEventFilter(self)
        self._layout.removeWidget(btn)
        self._buttons.remove(btn)
        
        # FIX: Collapse naturally along the major axis without violently squeezing the width.
        anim = QPropertyAnimation(btn, b"maximumSize", self)
        anim.setDuration(100)
        anim.setEndValue(QSize(16777215, 0))
            
        anim.finished.connect(btn.deleteLater)
        anim.finished.connect(self._update_scroll_visibility)
        anim.finished.connect(self.updateGeometry) 
        anim.start()
        
        self._update_scroll_visibility()
        if not self._buttons:
            self.hide()
    
    def _unpin_tab(self, button: VerticalTabButton):
        """Unpin specific tab (move to main area without closing)."""
        dock_widget = button.property("_dock_widget")
        if dock_widget:
            manager = self._find_manager()
            if manager and hasattr(manager, 'sidebar_manager'):
                manager.sidebar_manager.unpin_widget(dock_widget) # FIX: Added .sidebar_manager
    
    def _on_tab_context_menu(self, button: VerticalTabButton, global_pos: QPoint):
        """Show unified context menu using the standard DockMenuMixin."""
        self._context_menu_widget = button.property("_dock_widget")
        widget = self._context_menu_widget
        if not widget:
            return
            
        features = widget.features()
        is_movable = DockWidgetFeature.movable in features
        is_pinnable = DockWidgetFeature.pinnable in features

        menu = QMenu(self)
        
        # --- 1. Unpin Action ---
        unpin_act = menu.addAction("Unpin from Sidebar")
        unpin_act.setToolTip("Restore this widget back to the main layout")
        unpin_act.triggered.connect(lambda: self._unpin_tab(button))
        unpin_act.setEnabled(is_pinnable) # Disable if widget cannot be pinned/unpinned
        menu.addSeparator()
        
        # --- 2. Standard Menu (Float, Close, etc.) ---
        # This will automatically respect _menu_is_closable and _menu_is_floatable
        self.build_dock_menu(menu, self)
        menu.triggered.connect(self.dispatch_dock_action)
        
        # --- 3. Move to Area Action ---
        menu.addSeparator()
        move_menu = menu.addMenu("Move to Area")
        move_menu.setEnabled(is_movable) # Disable the whole submenu if not movable
        
        move_areas = [DockWidgetArea.left, DockWidgetArea.right, DockWidgetArea.top, DockWidgetArea.bottom]
        for area in move_areas:
            if area != self._area:
                action = move_menu.addAction(area.name.title())
                action.triggered.connect(
                    lambda checked=False, a=area, dw=self._context_menu_widget: self._move_to_area(dw, a)
                )
        
        menu.exec(global_pos)
    
    def _close_dock_widget(self, dock_widget: 'DockWidget'):
        """Safely unpins the widget from the sidebar, then fully closes it."""
        if DockWidgetFeature.closable not in dock_widget.features():
            return
        manager = self._find_manager()
        if manager and hasattr(manager, 'sidebar_manager'):
            manager.sidebar_manager.unpin_widget(dock_widget) # FIX: Added .sidebar_manager
        dock_widget.toggle_view(False)

    def _close_tab_button(self, button: VerticalTabButton):
        dock_widget = button.property("_dock_widget")
        if dock_widget:
            self._close_dock_widget(dock_widget)
    
    def _close_others(self, keep_button: VerticalTabButton):
        keep_widget = keep_button.property("_dock_widget")
        for btn in list(self._buttons):
            dw = btn.property("_dock_widget")
            if dw and dw != keep_widget:
                self._close_dock_widget(dw)
    
    def _close_all(self):
        for btn in list(self._buttons):
            dw = btn.property("_dock_widget")
            if dw:
                self._close_dock_widget(dw)
    
    def _move_to_area(self, dock_widget: 'DockWidget', area: DockWidgetArea):
        manager = self._find_manager()
        if manager and hasattr(manager, 'sidebar_manager'):
            # FIX: Route through sidebar_manager
            manager.sidebar_manager.move_widget_to_area(dock_widget, area)
    
    def uncheck_all(self):
        for btn in self._buttons:
            btn.setChecked(False)
    
    def button_for(self, dock_widget: 'DockWidget') -> Optional[VerticalTabButton]:
        return self._widget_map.get(dock_widget)
    
    def tab_count(self) -> int:
        return len(self._buttons)
    
    def _find_manager(self):
        from .dock_manager import DockManager
        w = self.parentWidget()
        while w:
            if isinstance(w, DockManager):
                return w
            w = w.parentWidget()
        return None
    
    def eventFilter(self, obj, event):
        if isinstance(obj, VerticalTabButton):
            if event.type() == QEvent.HoverEnter:
                self.tab_hover_enter.emit(obj)
                self.sidebar_activated.emit()
            elif event.type() == QEvent.HoverLeave:
                self.tab_hover_leave.emit(obj)
        return super().eventFilter(obj, event)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-dockwidget"):
            event.acceptProposedAction()
            self._show_drop_indicator()
    
    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat("application/x-dockwidget"):
            event.acceptProposedAction()
            self._update_drop_indicator(event.position().toPoint())
    
    def dragLeaveEvent(self, event):
        self._hide_drop_indicator()
    
    def dropEvent(self, event):
        self._hide_drop_indicator()
        if event.mimeData().hasFormat("application/x-dockwidget"):
            pass
    
    def _show_drop_indicator(self):
        # Attach drop indicator directly to the inner scroll container
        self._drop_indicator = QLabel(self._scroll_container)
        self._drop_indicator.setStyleSheet(
            f"background-color: {self._drop_indicator_color.name()};"
        )
        self._drop_indicator.setFixedSize(3, 30)
        self._drop_indicator.show()
    
    def _update_drop_indicator(self, pos: QPoint):
        if self._drop_indicator:
            # Map outer position to correctly account for scroll offsets
            mapped_pos = self._scroll_container.mapFrom(self, pos)
            self._drop_indicator.setFixedSize(3, 30)
            self._drop_indicator.move(0, mapped_pos.y())
    
    def _hide_drop_indicator(self):
        if self._drop_indicator:
            self._drop_indicator.deleteLater()
            self._drop_indicator = None

    # --- Style Manager ---

    def refresh_style(self):
        """Apply SIDEBAR styles to the tab bar container and its decorations."""
        s = self._style_mgr.get_all(DockStyleCategory.SIDEBAR)

        # Container background
        bg = s.get("bg_color")
        bg_css = bg.name() if bg else "transparent"
        border = s.get("border_color")
        border_css = border.name() if border else "transparent"
        border_w = s.get("border_width", 1.0)

        self.setStyleSheet(f"""
            QFrame#sideTabBar {{
                background-color: {bg_css};
                border: {border_w}px solid {border_css};
            }}
        """)

        # Keep scroll internals transparent
        self._scroll_area.setStyleSheet("background: transparent;")
        self._scroll_container.setStyleSheet("background: transparent;")

        # Sidebar width
        width = s.get("width", 42)
        self._sidebar_width = width
        self.setFixedWidth(width)

        # Layout padding and spacing
        pad = s.get("padding", 2)
        self._layout.setContentsMargins(pad, pad + 2, pad, pad + 2)
        self._layout.setSpacing(s.get("tab_margin", 2))

        # Counter label (uses subtle sidebar colors, badge font metrics)
        counter_bg = s.get("tab_bg_hover_start")
        counter_bg_css = counter_bg.name() if counter_bg else "palette(mid)"
        counter_text = s.get("tab_text_normal")
        counter_text_css = counter_text.name() if counter_text else "palette(text)"
        badge_radius = s.get("badge_radius", 6)
        badge_font = s.get("badge_font_family", "Segoe UI")
        badge_size = s.get("badge_font_size", 8)

        self._counter_lbl.setStyleSheet(f"""
            QLabel {{
                font-weight: bold;
                font-size: {badge_size + 2}px;
                font-family: "{badge_font}";
                color: {counter_text_css};
                background: {counter_bg_css};
                border-radius: {badge_radius - 2}px;
                margin: 2px;
                padding: 2px;
            }}
        """)

        # Drop indicator color
        ind = s.get("indicator_color")
        if ind:
            self._drop_indicator_color = ind

    def on_style_changed(self, category: DockStyleCategory, changes: dict):
        self.refresh_style()