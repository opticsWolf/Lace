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

from typing import TYPE_CHECKING, Optional
import logging

from PySide6.QtCore import QEvent, QPoint, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QAction, QContextMenuEvent, QCursor, QFontMetrics, QIcon, QMouseEvent, QPainter, QPalette
from PySide6.QtWidgets import QBoxLayout, QFrame, QLabel, QMenu, QSizePolicy, QWidget, QPushButton

from .util import start_drag_distance
from .enums import DragState, DockFlags, DockWidgetArea, DockWidgetFeature, WidgetState
from .eliding_label import ElidingLabel
from .dock_paint import paint_tab
from .dock_chrome import ChromeToolButton
from .dock_styled import DockStyled
from .dock_theme import DockStyleCategory
from .dock_menu import (
    MenuSection, dock_icon, MenuContext, build_dock_context_menu,
    dispatch_dock_context_menu, menu_default_pin, menu_default_unpin,
    menu_default_pin_all, menu_default_reattach
)


if TYPE_CHECKING:
    from . import DockWidget, DockAreaWidget, FloatingDockContainer

logger = logging.getLogger(__name__)


class DockWidgetTab(QFrame, DockStyled):
    STYLE_CATEGORIES = (DockStyleCategory.TAB,)
    _menu_sections = MenuSection.TAB

    active_tab_changed = Signal()
    clicked = Signal()
    close_requested = Signal()
    close_other_tabs_requested = Signal()
    moved = Signal(QPoint)

    def __init__(self, dock_widget: 'DockWidget', parent: QWidget = None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_NoMousePropagation, True)
        
        # Flattened private properties
        self._dock_widget = dock_widget
        self._icon_label = None
        self._title_label = None
        self._drag_start_mouse_position = QPoint()
        self._is_active_tab = False
        self._dock_area: 'DockAreaWidget' = None
        self._drag_state = DragState.inactive
        self._floating_widget: 'FloatingDockContainer' = None
        self._icon = QIcon()
        self._close_button = None

        # Painted-chrome state (populated by refresh_style).
        self._hovered = False
        self._bg_normal = None
        self._bg_active = None
        self._bg_hover = None
        self._indicator = None
        self._ind_width = 2
        self._ind_top = False
        self._radius = 0.0
        self.setAttribute(Qt.WA_Hover, True)

        self._create_layout()

        # --- ADDED: Style Manager Integration ---
        self._init_dock_style()
        if self._dock_widget and hasattr(self._dock_widget, 'features_changed'):
            self._dock_widget.features_changed.connect(lambda f: self.update_close_button_visibility())

    def _create_layout(self):
        self._title_label = ElidingLabel(text=self._dock_widget.windowTitle())
        self._title_label.set_elide_mode(Qt.ElideRight)
        self._title_label.setObjectName("dockWidgetTabLabel")
        self._title_label.setAlignment(Qt.AlignCenter)
        
        # Use dock_icon for proper Normal/Disabled state handling.
        # ChromeToolButton paints its own rounded hover (no :hover QSS); it is
        # flat by default (autoRaise), matching the old border-less push button.
        self._close_button = ChromeToolButton()
        self._close_button.setObjectName("tabCloseButton")
        self._close_button.setIcon(dock_icon("close_tab", DockStyleCategory.TAB))

        self._close_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._close_button.setVisible(False)
        self._close_button.setToolTip("Close")
        self._close_button.clicked.connect(self.close_requested)

        fm = QFontMetrics(self._title_label.font())
        spacing = round(fm.height() / 4.0)

        layout = QBoxLayout(QBoxLayout.LeftToRight)
        layout.setContentsMargins(2 * spacing, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)
        layout.addWidget(self._title_label, 1)
        layout.addSpacing(spacing)
        layout.addWidget(self._close_button)
        layout.addSpacing(round(spacing * 4.0 / 3.0))
        layout.setAlignment(Qt.AlignCenter)
        self._title_label.setVisible(True)

    def _move_tab(self, ev: QMouseEvent):
        ev.accept()
        move_to_pos = self.mapToParent(ev.position().toPoint()) - self._drag_start_mouse_position
        move_to_pos.setY(0)
        self.move(move_to_pos)
        self.raise_()

    def _is_dragging_state(self, drag_state: DragState) -> bool:
        return self._drag_state == drag_state

    def _start_floating(self, dragging_state: DragState = DragState.floating_widget) -> bool:
        if not self._floatable:
            return False
        dock_container = self._dock_widget.dock_container()
        if dock_container is None:
            return False

        if (dock_container.is_floating()
                and (dock_container.visible_dock_area_count() == 1)
                and (self._dock_widget.dock_area_widget().dock_widgets_count() == 1)):
            return False

        self._drag_state = dragging_state
        size = self._dock_area.size()

        from .floating_dock_container import FloatingDockContainer

        if self._dock_area.dock_widgets_count() > 1:
            self._floating_widget = FloatingDockContainer(dock_widget=self._dock_widget)
        else:
            self._floating_widget = FloatingDockContainer(dock_area=self._dock_area)

        if dragging_state == DragState.floating_widget:
            self._floating_widget.start_dragging(self._drag_start_mouse_position, size, self)
            overlay = self._dock_widget.dock_manager().container_overlay()
            overlay.set_allowed_areas(DockWidgetArea.outer_dock_areas)
        else:
            self._floating_widget.init_floating_geometry(self._drag_start_mouse_position, size)

        self._dock_widget.emit_top_level_changed(True)
        return True

    def _test_config_flag(self, flag: DockFlags) -> bool:
        if self._dock_area:
            return flag in self._dock_area.dock_manager().config_flags
        elif self._dock_widget and self._dock_widget.dock_manager():
            return flag in self._dock_widget.dock_manager().config_flags
        return False

    @property
    def _floatable(self):
        if not self._test_config_flag(DockFlags.floatable_tabs):
            return False
        return bool(self._dock_widget and (self._dock_widget.features() & DockWidgetFeature.floatable))

    @property
    def _pinnable(self):
        if not self._test_config_flag(DockFlags.pinnable_tabs):
            return False
        return bool(self._dock_widget and (self._dock_widget.features() & DockWidgetFeature.pinnable))

    def on_detach_action_triggered(self):
        if self._floatable:
            self._drag_start_mouse_position = self.mapFromGlobal(QCursor.pos())
            self._start_floating(DragState.inactive)

    def mousePressEvent(self, ev: QMouseEvent):
        if ev.button() == Qt.LeftButton:
            ev.accept()
            self._drag_start_mouse_position = ev.position().toPoint()
            self._drag_state = DragState.mouse_pressed
            self.clicked.emit()
            return
        elif ev.button() == Qt.MiddleButton:
            if self._test_config_flag(DockFlags.middle_mouse_button_closes_tab) and self.is_closable():
                ev.accept()
                self.close_requested.emit()
                return
        super().mousePressEvent(ev)

    def mouseReleaseEvent(self, ev: QMouseEvent):
        if ev.button() == Qt.MiddleButton:
            ev.accept()
            return
        if self._is_dragging_state(DragState.tab) and self._dock_area:
            self.moved.emit(ev.globalPosition().toPoint())

        self._drag_start_mouse_position = QPoint()
        self._drag_state = DragState.inactive
        super().mouseReleaseEvent(ev)

    def mouseMoveEvent(self, ev: QMouseEvent):
        if (not (ev.buttons() & Qt.LeftButton)
                or self._is_dragging_state(DragState.inactive)):
            self._drag_state = DragState.inactive
            return super().mouseMoveEvent(ev)

        if self._is_dragging_state(DragState.floating_widget):
            if self._floating_widget is not None:
                self._floating_widget.move_floating()
            else:
                self._drag_state = DragState.inactive
            return super().mouseMoveEvent(ev)

        if self._is_dragging_state(DragState.tab):
            self._move_tab(ev)

        drag_distance_y = abs(self._drag_start_mouse_position.y() - ev.position().toPoint().y())
        start_dist = start_drag_distance()
        
        if drag_distance_y >= start_dist:
            if (self._dock_area and self._dock_area.dock_container() and self._dock_area.dock_container().is_floating()
                    and self._dock_area.open_dock_widgets_count() == 1
                    and self._dock_area.dock_container().visible_dock_area_count() == 1):
                
                # --- FIX: Inject the Title Bar's Native Delegation Logic ---
                from .floating_dock_container import FloatingDockContainer
                floating_window = self.window()
                
                if isinstance(floating_window, FloatingDockContainer):
                    self._drag_state = DragState.floating_widget
                    self._floating_widget = floating_window
                    
                    mapped_start_pos = self.mapTo(floating_window, self._drag_start_mouse_position)
                    floating_window.start_dragging(mapped_start_pos, floating_window.size(), self)
                return
                # --- END FIX ---

            if self._floatable:
                self._start_floating()
                
        elif (self._dock_area and self._dock_area.open_dock_widgets_count() > 1
              and (ev.position().toPoint() - self._drag_start_mouse_position).manhattanLength() >= start_dist):
            self._drag_state = DragState.tab
        else:
            return super().mouseMoveEvent(ev)

    def contextMenuEvent(self, ev: QContextMenuEvent):
        ev.accept()
        self._drag_start_mouse_position = ev.pos()
        menu = QMenu(self)
        self.build_dock_menu(menu)
        menu.triggered.connect(self.dispatch_dock_action)
        menu.exec(self.mapToGlobal(ev.pos()))

    # ── MenuActionTarget & Menu Builder ───────────────────────────────────
    def _menu_is_floating(self) -> bool:
        container = self._dock_area.dock_container() if self._dock_area else None
        return container is not None and container.is_floating()

    def _menu_is_pinned(self) -> bool:
        if not self._dock_widget:
            return False
        state = self._dock_widget.widget_state()
        return state in (WidgetState.pinned_shown, WidgetState.pinned_hidden)

    def _menu_has_sidebars(self) -> bool:
        try:
            return self._dock_area.dock_manager().sidebar_manager.has_sidebars
        except (AttributeError, RuntimeError):
            return False

    def _gather_menu_context(self, tab_bar: Optional['DockAreaTabBar'] = None) -> MenuContext:
        count = self._dock_area.open_dock_widgets_count() if self._dock_area else 1
        is_floating = self._menu_is_floating()
        open_widgets = self._dock_area.opened_dock_widgets() if self._dock_area else []
        other_closable = sum(
            1 for dw in open_widgets
            if dw != self._dock_widget and (dw.features() & DockWidgetFeature.closable)
        )
        show_close_others = (other_closable > 0)
        is_pinnable = self._pinnable

        return MenuContext(
            widget_type="DockWidgetTab",
            sections=MenuSection.TAB,
            category=DockStyleCategory.TAB,
            widget=self._dock_widget,
            area=self._dock_area,
            tab_bar=tab_bar,
            count=count,
            is_closable=self.is_closable(),
            is_floatable=self._floatable,
            is_pinnable=is_pinnable,
            is_pinned=self._menu_is_pinned(),
            is_floating=is_floating,
            has_sidebars=self._menu_has_sidebars(),
            show_close_others=show_close_others,
            label_overrides={
                "close": "Close",
                "close_others": "Close Others",
                "float": "Float",
                "dock": "Dock",
            }
        )

    def build_dock_menu(self, menu: QMenu, tab_bar: Optional['DockAreaTabBar'] = None) -> None:
        context = self._gather_menu_context(tab_bar)
        build_dock_context_menu(context, menu)

    def dispatch_dock_action(self, action: QAction) -> None:
        dispatch_dock_context_menu(action, self, fallback_widget_type="DockWidgetTab")

    # ── MenuActionTarget Protocol Implementation ──────────────────────────
    def menu_target_widget(self) -> Optional['DockWidget']:
        return self._dock_widget

    def menu_pin_target(self) -> None:
        menu_default_pin(self._dock_widget, self._dock_area)

    def menu_unpin_target(self) -> None:
        menu_default_unpin(self._dock_widget, self._dock_area)

    def menu_pin_all_target(self) -> None:
        menu_default_pin_all(self._dock_area)

    def menu_float_target(self) -> None:
        self.on_detach_action_triggered()

    def menu_dock_target(self) -> None:
        menu_default_reattach(self._dock_area)

    def menu_close_target(self) -> None:
        self.close_requested.emit()

    def menu_close_others_target(self) -> None:
        self.close_other_tabs_requested.emit()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if (self._floatable and self._dock_area and self._dock_area.dock_container() and
                (not self._dock_area.dock_container().is_floating()
                 or self._dock_area.dock_widgets_count() > 1)):
            self._drag_start_mouse_position = event.position().toPoint()
            self._start_floating(DragState.inactive)

        super().mouseDoubleClickEvent(event)

    def is_active_tab(self) -> bool:
        return self._is_active_tab

    def update_close_button_visibility(self):
        if not self._dock_widget:
            return
        closable = bool(self._dock_widget.features() & DockWidgetFeature.closable)
        show_tab_close = self._test_config_flag(DockFlags.show_tab_close_button)
        active_tab_only = self._test_config_flag(DockFlags.active_tab_has_close_button)
        if not closable or not show_tab_close:
            self._close_button.setVisible(False)
        else:
            self._close_button.setVisible(not active_tab_only or self.is_active_tab())

    def set_active_tab(self, active: bool):
        if self._is_active_tab == active:
            self.update_close_button_visibility()
            return
        self._is_active_tab = active
        self.update_close_button_visibility()
        self.refresh_style() 
        self.active_tab_changed.emit()

    def dock_widget(self) -> 'DockWidget':
        return self._dock_widget

    def set_dock_area_widget(self, dock_area: 'DockAreaWidget'):
        self._dock_area = dock_area
        self.update_close_button_visibility()

    def dock_area_widget(self) -> 'DockAreaWidget':
        return self._dock_area

    def set_icon(self, icon: QIcon):
        layout = self.layout()
        if not self._icon_label and icon.isNull():
            return

        if not self._icon_label:
            self._icon_label = QLabel()
            self._icon_label.setAlignment(Qt.AlignVCenter)
            self._icon_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
            self._icon_label.setToolTip(self._title_label.toolTip())
            layout.insertWidget(0, self._icon_label, Qt.AlignVCenter)
            layout.insertSpacing(1, round(1.5 * layout.contentsMargins().left() / 2.0))
        elif icon.isNull():
            layout.removeWidget(self._icon_label)
            layout.removeItem(layout.itemAt(0))
            self._icon_label.deleteLater()
            self._icon_label = None

        self._icon = icon
        if self._icon_label:
            self._icon_label.setPixmap(icon.pixmap(self.windowHandle(), QSize(16, 16)))
            self._icon_label.setVisible(True)

    def icon(self) -> QIcon:
        return self._icon

    def text(self) -> str:
        return self._title_label.text()

    def set_text(self, title: str):
        self._title_label.setText(title)

    def is_closable(self) -> bool:
        return bool(self._dock_widget and (self._dock_widget.features() & DockWidgetFeature.closable))

    def event(self, e: QEvent) -> bool:
        if e.type() == QEvent.ToolTipChange:
            text = self.toolTip()
            self._title_label.setToolTip(text)
        return super().event(e)

    def refresh_style(self):
        """Cache TAB colours for the painted background/indicator and style the
        child label and close button (the only remaining stylesheet)."""
        styles = self._style_mgr.get_all(DockStyleCategory.TAB)
        is_active = self._is_active_tab

        # 1. Painted-chrome state (consumed by paintEvent).
        self._bg_normal = styles.get("bg_normal")
        self._bg_active = styles.get("bg_active")
        self._bg_hover = styles.get("bg_hover")
        self._indicator = styles.get("indicator_color")
        self._ind_width = styles.get("indicator_width", 2)
        self._ind_top = styles.get("indicator_position", "bottom") == "top"
        self._radius = styles.get("corner_radius", 0)
        self.setAutoFillBackground(False)
        self.setAttribute(Qt.WA_StyledBackground, False)

        # 2. Label colour via palette; close-button hover painted (no QSS at all
        #    on the tab, so its painted background is never masked by a sheet and
        #    the label palette isn't overridden by a parent-stylesheet cascade).
        text_color = styles.get("text_active") if is_active else styles.get("text_normal")
        if text_color is not None and self._title_label is not None:
            pal = self._title_label.palette()
            pal.setColor(QPalette.WindowText, text_color)
            self._title_label.setPalette(pal)
        self._close_button.set_hover_chrome(
            styles.get("close_btn_bg_hover"),
            styles.get("close_btn_corner_radius", 3),
        )

        btn_size = styles.get("close_btn_size", 20)
        icon_size_val = styles.get("close_btn_icon_size", 16)
        self._close_button.setFixedSize(QSize(btn_size, btn_size))
        self._close_button.setIconSize(QSize(icon_size_val, icon_size_val))

        # 3. Typography.
        font = self.font()
        font.setFamily(styles.get("font_family", "Segoe UI"))
        font.setPointSize(styles.get("font_size", 10))
        weight = styles.get("active_font_weight" if is_active else "font_weight", "normal")
        font.setBold(weight in ("bold", 700))
        self.setFont(font)
        if self._title_label:
            self._title_label.setFont(font)
        self.update()

    def paintEvent(self, event):
        if self._bg_active is None:
            return  # not styled yet
        if self._is_active_tab:
            fill = self._bg_active
        elif self._hovered:
            fill = self._bg_hover
        else:
            fill = self._bg_normal
        p = QPainter(self)
        paint_tab(
            p, QRectF(self.rect()),
            bg=fill, radius=self._radius,
            indicator=self._indicator if self._is_active_tab else None,
            indicator_width=self._ind_width,
            indicator_edge=Qt.Edge.TopEdge if self._ind_top else Qt.Edge.BottomEdge,
        )

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

