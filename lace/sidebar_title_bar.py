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
from PySide6.QtGui import QAction, QColor, QPainter, QPalette
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QToolButton, QWidget, QMenu
)
from .enums import DockWidgetFeature
from .dock_chrome import style_title_bar_buttons, DragDetector, ChromeToolButton
from .dock_menu import MenuSection, dock_icon, MenuContext, build_dock_context_menu, dispatch_dock_context_menu
from .dock_theme import DockStyleCategory
from .dock_styled import DockStyled

if TYPE_CHECKING:
    from .dock_widget import DockWidget


class SideBarTitleBar(QFrame, DockStyled):
    """
    Standalone Title Bar for the Overlay, managing buttons, titles, 
    context menus, and drag-to-detach behavior.
    
    Provides float, unpin, and close functionality with unified iconography
    and consistent interaction patterns.
    """
    STYLE_CATEGORIES = (DockStyleCategory.SIDEPANEL, DockStyleCategory.SIDEBAR, DockStyleCategory.CORE, DockStyleCategory.OVERLAY)
    
    _menu_sections = MenuSection.DETACH | MenuSection.CLOSE

    close_requested = Signal()
    reattach_requested = Signal(object)   # "Unpin from Sidebar"
    detach_requested = Signal(object)     # "Float"

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("overlayTitleBar")
        self.setFixedHeight(32)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_StyledBackground, False)
        self._bg_color: Optional[QColor] = None   # painted in paintEvent (no hex QSS)

        self._active_widget: Optional['DockWidget'] = None

        self._setup_ui()

        # Drag the title bar to detach the pinned panel into a floating window.
        self._drag = DragDetector(self)
        self._drag.drag_started.connect(self._on_drag_started)

        # Style Manager Integration
        self._init_dock_style()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 4, 0)
        layout.setSpacing(2)

        self._title_label = QLabel("Panel")
        self._title_label.setObjectName("overlayTitleLabel")

        # Use dock_icon for proper Normal/Disabled state handling

        # Unpin button
        self._reattach_btn = ChromeToolButton()
        self._reattach_btn.setAutoRaise(True)
        self._reattach_btn.setIcon(dock_icon("unpin", DockStyleCategory.SIDEPANEL))
        self._reattach_btn.setToolTip("Unpin from Sidebar")
        self._reattach_btn.clicked.connect(self._on_reattach_clicked)

        # Float button
        self._float_btn = ChromeToolButton()
        self._float_btn.setAutoRaise(True)
        self._float_btn.setIcon(dock_icon("float", DockStyleCategory.SIDEPANEL))
        self._float_btn.setToolTip("Float")
        self._float_btn.clicked.connect(lambda: self.detach_requested.emit(self._active_widget) if self._active_widget else None)

        # Close Button
        self._close_btn = ChromeToolButton()
        self._close_btn.setAutoRaise(True)
        self._close_btn.setIcon(dock_icon("close", DockStyleCategory.SIDEPANEL))
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

    # --- Drag Logic ---

    def _on_drag_started(self, _global_pos: QPoint):
        if self._active_widget:
            self.detach_requested.emit(self._active_widget)

    # --- Menu Logic ---

    def _gather_menu_context(self, tab_bar=None) -> MenuContext:
        widget = self._active_widget
        features = widget.features() if widget else DockWidgetFeature.none
        is_closable = bool(features & DockWidgetFeature.closable)
        is_floatable = bool(features & DockWidgetFeature.floatable)
        is_pinnable = bool(features & DockWidgetFeature.pinnable)

        return MenuContext(
            widget_type="SideBarTitleBar",
            sections=MenuSection.SIDEBAR_TAB,
            category=DockStyleCategory.SIDEPANEL,
            widget=widget,
            is_closable=is_closable,
            is_floatable=is_floatable,
            is_pinnable=is_pinnable,
            is_pinned=True,
            is_floating=False,
            has_sidebars=True,
            show_close_others=False,
            label_overrides={
                "unpin": "Unpin from Sidebar",
                "float": "Float",
                "close": "Close",
            }
        )

    def build_dock_menu(self, menu: QMenu, tab_bar=None) -> None:
        context = self._gather_menu_context(tab_bar)
        build_dock_context_menu(context, menu)

    def dispatch_dock_action(self, action: QAction) -> None:
        dispatch_dock_context_menu(action, self, fallback_widget_type="SideBarTitleBar")

    def _show_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        self.build_dock_menu(menu)
        menu.triggered.connect(self.dispatch_dock_action)
        menu.exec(self.mapToGlobal(pos))

    def _on_reattach_clicked(self):
        if self._active_widget:
            self.reattach_requested.emit(self._active_widget)

    # ── MenuActionTarget Protocol Implementation ──────────────────────────
    def menu_target_widget(self) -> Optional['DockWidget']:
        return self._active_widget

    def menu_unpin_target(self) -> None:
        self._on_reattach_clicked()

    def menu_float_target(self) -> None:
        if self._active_widget:
            self.detach_requested.emit(self._active_widget)

    def menu_close_target(self) -> None:
        self.close_requested.emit()

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
        title_text = styles.get("title_text_color")
        btn_color = styles.get("button_color")
        btn_hover = styles.get("button_hover_bg")
        disabled_color = core_styles.get("disabled_text_color")

        # Painted background (square — the overlay panel has no rounded card),
        # mirroring dock_area_title_bar's paint path instead of a hex QSS sheet.
        self._bg_color = bg
        self.update()

        # Title label styling
        font_family = styles.get("title_font_family", "Segoe UI")
        font_size = styles.get("title_font_size", 10)
        font_weight = styles.get("title_font_weight", "bold")
        bold = font_weight in ("bold", 700)

        # Label colour via palette (QLabel foreground is WindowText); the label is
        # transparent by default, so no background rule is needed.
        if title_text is not None:
            lbl_pal = self._title_label.palette()
            lbl_pal.setColor(QPalette.WindowText, title_text)
            lbl_pal.setColor(QPalette.Text, title_text)
            self._title_label.setPalette(lbl_pal)

        font = self._title_label.font()
        font.setFamily(font_family)
        font.setPointSize(font_size)
        font.setBold(bold)
        self._title_label.setFont(font)

        # Shared icon-button styling (see dock_area_title_bar — same call).
        style_title_bar_buttons(
            (self._reattach_btn, self._float_btn, self._close_btn),
            color=btn_color, hover_bg=btn_hover, disabled=disabled_color,
            radius=styles.get("button_corner_radius", 3),
            padding=styles.get("button_padding", 2),
            size=styles.get("button_size", 18),
            icon_size=styles.get("button_icon_size", 16),
            expand_vertical=styles.get("button_expand_vertical", False),
        )

        # Re-tint icons for the current theme (SIDEPANEL button colour), so they
        # recolour on theme change — mirrors DockAreaTitleBar.update_button_states.
        self._reattach_btn.setIcon(dock_icon("unpin", DockStyleCategory.SIDEPANEL))
        self._float_btn.setIcon(dock_icon("float", DockStyleCategory.SIDEPANEL))
        self._close_btn.setIcon(dock_icon("close", DockStyleCategory.SIDEPANEL))

    def paintEvent(self, event):
        bg = self._bg_color
        if bg is not None and bg.alpha() > 0:
            p = QPainter(self)
            p.fillRect(self.rect(), bg)
            p.end()

