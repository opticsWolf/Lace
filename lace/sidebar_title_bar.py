# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0

sidebar_title_bar.py
--------------------
Standalone title bar for the sidebar overlay panel, with context menu,
drag-to-detach, and unified action naming / icons.
"""
from typing import TYPE_CHECKING, Optional
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QToolButton, QWidget, QMenu
)
from .enums import DockWidgetFeature
from .dock_context_menu import DockMenuMixin, MenuSection, dock_icon
from .util import start_drag_distance

if TYPE_CHECKING:
    from .dock_widget import DockWidget


class OverlayTitleBar(QFrame, DockMenuMixin):
    """
    Standalone Title Bar for the Overlay, managing buttons, titles, 
    context menus, and drag-to-detach behavior.
    
    Provides float, unpin, and close functionality with unified iconography
    and consistent interaction patterns.
    """
    
    _menu_sections = MenuSection.DETACH | MenuSection.CLOSE

    close_requested = Signal()
    reattach_requested = Signal(object)   # "Unpin from Sidebar"
    detach_requested = Signal(object)     # "Float"

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("overlayTitleBar")
        self.setFixedHeight(32)
        self.setAutoFillBackground(True)

        self._active_widget: Optional['DockWidget'] = None
        self._drag_start: Optional[QPoint] = None

        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 4, 0)
        layout.setSpacing(2)

        self._title_label = QLabel("Panel")
        self._title_label.setObjectName("overlayTitleLabel")

        # Unpin button — uses canonical "unpin" icon
        self._reattach_btn = QToolButton()
        self._reattach_btn.setAutoRaise(True)
        self._reattach_btn.setIcon(dock_icon("unpin"))
        self._reattach_btn.setToolTip("Unpin from Sidebar")
        self._reattach_btn.clicked.connect(self._on_reattach_clicked)

        # Float button — uses canonical "float" icon
        self._float_btn = QToolButton()
        self._float_btn.setAutoRaise(True)
        self._float_btn.setIcon(dock_icon("float"))
        self._float_btn.setToolTip("Float")
        self._float_btn.clicked.connect(lambda: self.detach_requested.emit(self._active_widget) if self._active_widget else None)

        # Close Button — uses canonical "close" icon
        self._close_btn = QToolButton()
        self._close_btn.setAutoRaise(True)
        self._close_btn.setIcon(dock_icon("close_tab"))
        self._close_btn.setToolTip("Close")
        self._close_btn.clicked.connect(self.close_requested.emit)

        layout.addWidget(self._title_label, 1)
        layout.addWidget(self._reattach_btn)
        layout.addWidget(self._float_btn)
        layout.addWidget(self._close_btn)

        # Context Menu wiring
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def set_widget(self, dock_widget: Optional['DockWidget']):
        """Updates the title and buttons based on the active widget."""
        self._active_widget = dock_widget
        
        if dock_widget:
            self._title_label.setText(dock_widget.windowTitle())
            
            features = dock_widget.features()
            is_closable = bool(features & DockWidgetFeature.closable)
            is_pinnable = bool(features & DockWidgetFeature.pinnable)
            is_floatable = bool(features & DockWidgetFeature.floatable)
            
            self._close_btn.setVisible(is_closable)
            self._reattach_btn.setVisible(is_pinnable)
            self._float_btn.setVisible(is_floatable)
        else:
            self._title_label.setText("Panel")
            self._close_btn.setVisible(True)
            self._reattach_btn.setVisible(True)
            self._float_btn.setVisible(True)

    # --- Mouse & Drag Logic ---

    def mousePressEvent(self, ev: QMouseEvent):
        if ev.button() == Qt.LeftButton:
            self._drag_start = ev.globalPosition().toPoint()
        super().mousePressEvent(ev)
    
    def mouseMoveEvent(self, ev: QMouseEvent):
        if self._drag_start:
            if (ev.globalPosition().toPoint() - self._drag_start).manhattanLength() >= start_drag_distance():
                self._drag_start = None
                if self._active_widget:
                    self.detach_requested.emit(self._active_widget)
        super().mouseMoveEvent(ev)
    
    def mouseReleaseEvent(self, ev: QMouseEvent):
        self._drag_start = None
        super().mouseReleaseEvent(ev)

    # --- Menu Logic ---

    def _build_overlay_menu(self, menu: QMenu) -> None:
        """Build the context / dropdown menu using canonical icons and labels."""
        widget = self._active_widget
        if not widget:
            return

        features = widget.features()
        is_closable = bool(features & DockWidgetFeature.closable)
        is_floatable = bool(features & DockWidgetFeature.floatable)
        is_pinnable = bool(features & DockWidgetFeature.pinnable)

        if is_pinnable:
            act = menu.addAction(dock_icon("unpin"), "Unpin from Sidebar")
            act.setToolTip("Remove from sidebar and place back in the main layout")
            act.triggered.connect(self._on_reattach_clicked)

        if is_floatable:
            act = menu.addAction(dock_icon("float"), "Float")
            act.setToolTip("Detach into a floating window")
            act.triggered.connect(self._menu_detach)

        if (is_pinnable or is_floatable) and is_closable:
            menu.addSeparator()

        if is_closable:
            act = menu.addAction(dock_icon("close"), "Close")
            act.setToolTip("Hide this panel")
            act.triggered.connect(self._menu_close)

    def _show_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        self._build_overlay_menu(menu)
        menu.exec(self.mapToGlobal(pos))

    def _on_reattach_clicked(self):
        if self._active_widget:
            self.reattach_requested.emit(self._active_widget)

    # ── DockMenuMixin required interface ──────────────────────────────────

    def _menu_dock_area(self):
        return None

    def _menu_dock_widget(self):
        return self._active_widget

    def _menu_is_floating(self) -> bool:
        return False

    def _menu_is_closable(self) -> bool:
        return bool(self._active_widget and (self._active_widget.features() & DockWidgetFeature.closable))

    def _menu_is_floatable(self) -> bool:
        return bool(self._active_widget and (self._active_widget.features() & DockWidgetFeature.floatable))

    def _menu_show_close_others(self) -> bool:
        return False

    def _menu_has_sidebars(self) -> bool:
        return True

    def _menu_close(self):
        self.close_requested.emit()

    def _menu_detach(self):
        if self._active_widget:
            self.detach_requested.emit(self._active_widget)
            
    def _menu_pin_current(self):
        self._on_reattach_clicked()

    # --- Styling ---
    
    def apply_style(self, s: dict):
        bg = s.get("background_color")
        frame = s.get("frame_color")
        title_text = s.get("title_text_color")
        btn_color = s.get("button_color")
        btn_hover = s.get("button_hover_bg")

        bg_css = bg.name() if bg else "palette(window)"
        frame_css = frame.name() if frame else "palette(mid)"
        title_css = title_text.name() if title_text else "palette(text)"
        btn_css = btn_color.name() if btn_color else "palette(text)"
        btn_hover_css = btn_hover.name() if btn_hover else "palette(mid)"

        self.setStyleSheet(f"""
            #overlayTitleBar {{
                background-color: {bg_css};
                border-bottom: 1px solid {frame_css};
            }}
        """)

        font_family = s.get("title_font_family", "Segoe UI")
        font_size = s.get("title_font_size", 10)
        font_weight = s.get("title_font_weight", "bold")
        bold = font_weight in ("bold", 700)
        weight_css = "bold" if bold else "normal"

        self._title_label.setStyleSheet(f"""
            #overlayTitleLabel {{
                color: {title_css};
                font-weight: {weight_css};
                font-family: "{font_family}";
                font-size: {font_size}pt;
                background: transparent;
            }}
        """)

        font = self._title_label.font()
        font.setFamily(font_family)
        font.setPointSize(font_size)
        font.setBold(bold)
        self._title_label.setFont(font)

        button_css = f"""
            QToolButton {{
                color: {btn_css};
                background: transparent;
                border: none;
                border-radius: 2px;
            }}
            QToolButton:hover {{
                background-color: {btn_hover_css};
            }}
        """
        self._reattach_btn.setStyleSheet(button_css)
        self._float_btn.setStyleSheet(button_css)
        self._close_btn.setStyleSheet(button_css)
