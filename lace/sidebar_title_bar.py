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
from PySide6.QtCore import Qt, Signal, QPoint, QSize
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QToolButton, QWidget, QMenu, QSizePolicy
)
from .enums import DockWidgetFeature
from .dock_context_menu import DockMenuMixin, MenuSection, dock_icon
from .util import start_drag_distance
from .dock_theme import DockStyleCategory
from .dock_style_manager import get_dock_style_manager

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

        # Style Manager Integration
        self._style_mgr = get_dock_style_manager()
        self._style_mgr.register(self, DockStyleCategory.SIDEPANEL)
        self.refresh_style()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 4, 0)
        layout.setSpacing(2)

        self._title_label = QLabel("Panel")
        self._title_label.setObjectName("overlayTitleLabel")

        # Use dock_icon for proper Normal/Disabled state handling

        # Unpin button
        self._reattach_btn = QToolButton()
        self._reattach_btn.setAutoRaise(True)
        self._reattach_btn.setIcon(dock_icon("unpin", DockStyleCategory.OVERLAY))
        self._reattach_btn.setToolTip("Unpin from Sidebar")
        self._reattach_btn.clicked.connect(self._on_reattach_clicked)

        # Float button
        self._float_btn = QToolButton()
        self._float_btn.setAutoRaise(True)
        self._float_btn.setIcon(dock_icon("float", DockStyleCategory.OVERLAY))
        self._float_btn.setToolTip("Float")
        self._float_btn.clicked.connect(lambda: self.detach_requested.emit(self._active_widget) if self._active_widget else None)

        # Close Button
        self._close_btn = QToolButton()
        self._close_btn.setAutoRaise(True)
        self._close_btn.setIcon(dock_icon("close", DockStyleCategory.OVERLAY))
        self._close_btn.setToolTip("Close")
        self._close_btn.clicked.connect(self.close_requested.emit)

        layout.addWidget(self._title_label, 1)
        layout.addWidget(self._reattach_btn)
        layout.addWidget(self._float_btn)
        layout.addWidget(self._close_btn)

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

        # Use dock_icon for proper Normal/Disabled state handling in menus

        if is_pinnable:
            act = menu.addAction(dock_icon("unpin", DockStyleCategory.OVERLAY), "Unpin from Sidebar")
            act.setToolTip("Remove from sidebar and place back in the main layout")
            act.triggered.connect(self._on_reattach_clicked)

        if is_floatable:
            act = menu.addAction(dock_icon("float", DockStyleCategory.OVERLAY), "Float")
            act.setToolTip("Detach into a floating window")
            act.triggered.connect(self._menu_detach)

        if (is_pinnable or is_floatable) and is_closable:
            menu.addSeparator()

        if is_closable:
            act = menu.addAction(dock_icon("close", DockStyleCategory.OVERLAY), "Close")
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

    def refresh_style(self):
        """Refresh styling from the DockStyleManager (mirrors dock_area_title_bar)."""
        styles = self._style_mgr.get_all(DockStyleCategory.SIDEPANEL)
        core_styles = self._style_mgr.get_all(DockStyleCategory.CORE)
        sidebar_styles = self._style_mgr.get_all(DockStyleCategory.SIDEBAR)

        # Apply Geometry
        self.setFixedHeight(styles.get("height", 32))
        self.layout().setSpacing(styles.get("button_spacing", 2))
        self.layout().setContentsMargins(
            styles.get("padding_left", 8),
            styles.get("padding_top", 0),
            styles.get("padding_right", 4),
            0
        )

        # Resolve Colors with fallbacks
        bg = styles.get("bg_normal")
        frame = sidebar_styles.get("border_color")
        title_text = styles.get("title_text_color")
        btn_color = styles.get("button_color")
        btn_hover = styles.get("button_hover_bg")
        disabled_color = core_styles.get("disabled_text_color")

        bg_css = bg.name() if bg else "palette(window)"
        frame_css = frame.name() if frame else "palette(mid)"
        title_css = title_text.name() if title_text else "palette(text)"
        btn_css = btn_color.name() if btn_color else "palette(text)"
        btn_hover_css = btn_hover.name() if btn_hover else "palette(mid)"
        disabled_css = disabled_color.name() if disabled_color else "palette(mid)"

        # Title bar container styling
        # self.setStyleSheet(f"""
        #     #overlayTitleBar {{
        #         background-color: {bg_css};
        #         border-bottom: 1px solid {frame_css};
        #     }}
        # """)
        self.setStyleSheet(f"""
            #overlayTitleBar {{
                background-color: {bg_css};
            }}
        """)

        # Title label styling
        font_family = styles.get("title_font_family", "Segoe UI")
        font_size = styles.get("title_font_size", 10)
        font_weight = styles.get("title_font_weight", "bold")
        bold = font_weight in ("bold", 700)

        self._title_label.setStyleSheet(f"""
            #overlayTitleLabel {{
                color: {title_css};
                font-weight: {"bold" if bold else "normal"};
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

        # Button styling
        btn_radius = styles.get("button_corner_radius", 3)
        btn_padding = styles.get("button_padding", 2)
        btn_size = styles.get("button_size", 18)
        btn_icon_size = styles.get("button_icon_size", 16)
        btn_expand_v = styles.get("button_expand_vertical", False)

        button_css = f"""
            QToolButton {{
                color: {btn_css};
                background: transparent;
                border: none;
                border-radius: {btn_radius}px;
                padding: {btn_padding}px;
                min-width: {btn_size}px;
                min-height: {btn_size}px;
            }}
            QToolButton:hover {{
                background-color: {btn_hover_css};
            }}
            QToolButton:disabled {{
                color: {disabled_css};
            }}
        """

        v_policy = QSizePolicy.Expanding if btn_expand_v else QSizePolicy.Fixed
        icon_size = QSize(btn_icon_size, btn_icon_size)

        for btn in (self._reattach_btn, self._float_btn, self._close_btn):
            btn.setStyleSheet(button_css)
            btn.setSizePolicy(QSizePolicy.Fixed, v_policy)
            btn.setIconSize(icon_size)

    def on_style_changed(self, category: DockStyleCategory, changes: dict):
        """Called by DockStyleManager when subscribed categories change."""
        self.refresh_style()