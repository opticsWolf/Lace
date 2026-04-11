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

from PySide6.QtCore import QPoint, Qt, Signal, QSize
from PySide6.QtGui import QAction, QCursor, QMouseEvent
from PySide6.QtWidgets import (QAbstractButton, QBoxLayout, QFrame,
                               QMenu, QSizePolicy, QStyle, QToolButton)

from .enums import DockFlags, DragState, DockWidgetFeature, TitleBarButton, DockWidgetArea
from .util import start_drag_distance
from .dock_style_manager import get_dock_style_manager
from .dock_theme import DockStyleCategory
from .dock_context_menu import DockMenuMixin, MenuSection, dock_icon

if TYPE_CHECKING:
    from . import DockAreaWidget, DockAreaTabBar, DockManager
    from .floating_dock_container import FloatingDockContainer

logger = logging.getLogger(__name__)


class DockAreaTitleBar(QFrame, DockMenuMixin):
    _menu_sections    = MenuSection.TITLE_BAR

    tab_bar_clicked = Signal(int)
    pin_button_clicked = Signal()

    def __init__(self, parent: 'DockAreaWidget'):
        super().__init__(parent)
        self._dock_area = parent
        self.setObjectName("dockAreaTitleBar")

        # Drag properties mirroring dock_widget_tab
        self._drag_state = DragState.inactive
        self._drag_start_mouse_position = QPoint()
        self._floating_widget: Optional['FloatingDockContainer'] = None

        # Flattened private properties
        self._tabs_menu_button: QToolButton = None
        self._undock_button: QToolButton = None
        self._close_button: QToolButton = None
        self._pin_button: QToolButton = None
        self._tab_bar: 'DockAreaTabBar' = None
        self._menu_outdated = True
        self._tabs_menu: QMenu = None

        self._top_layout = QBoxLayout(QBoxLayout.LeftToRight)
        self._top_layout.setContentsMargins(0, 0, 0, 0)
        self._top_layout.setSpacing(0)
        self.setLayout(self._top_layout)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
        self._create_tab_bar()
        self._create_buttons()

        # Right-click anywhere on the title bar opens the unified menu.
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(
            lambda pos: self.show_context_menu(self.mapToGlobal(pos))
        )

        # Style Manager Integration
        self._style_mgr = get_dock_style_manager()
        self._style_mgr.register(self, DockStyleCategory.TITLE_BAR)
        self.refresh_style()

    def __repr__(self):
        return f'<{self.__class__.__name__}>'

    def _create_buttons(self):
        # ── Tabs menu button (always visible) ─────────────────────────
        self._tabs_menu_button = QToolButton()
        self._tabs_menu_button.setObjectName("tabsMenuButton")
        self._tabs_menu_button.setAutoRaise(True)
        self._tabs_menu_button.setPopupMode(QToolButton.InstantPopup)
        # Use dock_icon for proper Normal/Disabled state handling
        self._tabs_menu_button.setIcon(dock_icon("tabs_menu", DockStyleCategory.TITLE_BAR))
        self._tabs_menu_button.setToolTip("Menu")

        self._tabs_menu = QMenu(self._tabs_menu_button)
        self._tabs_menu.setToolTipsVisible(True)
        self._tabs_menu.aboutToShow.connect(self.on_tabs_menu_about_to_show)
        self._tabs_menu_button.setMenu(self._tabs_menu)

        self._tabs_menu_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self._top_layout.addWidget(self._tabs_menu_button, 0)
        self._tabs_menu.triggered.connect(self.on_tabs_menu_action_triggered)
        self._tabs_menu_button.setVisible(
            self._test_config_flag(DockFlags.dock_area_has_tabs_menu_button)
        )

        # ── Pin button ────────────────────────────────────────────────
        self._pin_button = QToolButton()
        self._pin_button.setObjectName("pinButton")
        self._pin_button.setAutoRaise(True)
        self._pin_button.setToolTip("Pin to Sidebar")
        # Use dock_icon for proper Normal/Disabled state handling
        self._pin_button.setIcon(dock_icon("pin", DockStyleCategory.TITLE_BAR))
        self._pin_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self._top_layout.addWidget(self._pin_button, 0)
        self._pin_button.clicked.connect(self.on_pin_button_clicked)
        # Initially hidden; becomes visible when a sidebar is added
        self._pin_button.setVisible(self._menu_has_sidebars())

        # ── Undock (float) button ─────────────────────────────────────
        self._undock_button = QToolButton()
        self._undock_button.setObjectName("undockButton")
        self._undock_button.setAutoRaise(True)
        self._undock_button.setToolTip("Float")
        # Use dock_icon for proper Normal/Disabled state handling
        self._undock_button.setIcon(dock_icon("float", DockStyleCategory.TITLE_BAR))
        self._undock_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self._top_layout.addWidget(self._undock_button, 0)
        self._undock_button.clicked.connect(self.on_undock_button_clicked)

        # ── Close button ──────────────────────────────────────────────
        self._close_button = QToolButton()
        self._close_button.setObjectName("closeButton")
        self._close_button.setAutoRaise(True)
        # Use dock_icon for proper Normal/Disabled state handling
        self._close_button.setIcon(dock_icon("close", DockStyleCategory.TITLE_BAR))

        if self._test_config_flag(DockFlags.dock_area_close_button_closes_tab):
            self._close_button.setToolTip("Close")
        else:
            self._close_button.setToolTip("Close Group")

        self._close_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self._close_button.setIconSize(QSize(16, 16))
        self._top_layout.addWidget(self._close_button, 0)
        self._close_button.clicked.connect(self.on_close_button_clicked)

    def _create_tab_bar(self):
        from .dock_area_tab_bar import DockAreaTabBar
        self._tab_bar = DockAreaTabBar(self._dock_area)
        self._top_layout.addWidget(self._tab_bar)
    
        self._tab_bar.tab_closed.connect(self.mark_tabs_menu_outdated)
        self._tab_bar.tab_opened.connect(self.mark_tabs_menu_outdated)
        self._tab_bar.tab_inserted.connect(self.mark_tabs_menu_outdated)
        self._tab_bar.removing_tab.connect(self.mark_tabs_menu_outdated)
        self._tab_bar.tab_moved.connect(self.mark_tabs_menu_outdated)
        self._tab_bar.current_changed.connect(self.mark_tabs_menu_outdated)
        
        # --- FIX: Sync to the Area's index signal, not the Tab Bar's! ---
        # Ensures internal layout widget swap is complete before evaluating states.
        self._dock_area.current_changed.connect(self.on_current_tab_changed)
        
        self._tab_bar.tab_bar_clicked.connect(self.tab_bar_clicked)
    
        self._tab_bar.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tab_bar.customContextMenuRequested.connect(
            lambda pos: self.show_context_menu(self._tab_bar.mapToGlobal(pos))
        )

    def dock_manager(self) -> 'DockManager':
        return self._dock_area.dock_manager()

    def _test_config_flag(self, flag: DockFlags) -> bool:
        return flag in self._dock_area.dock_manager().config_flags

    # ── DockMenuMixin interface ───────────────────────────────────────────

    def _menu_dock_area(self):
        return self._dock_area

    def _menu_on_switch_tab(self, index: int):
        self._tab_bar.set_current_index(index)
        self.tab_bar_clicked.emit(index)

    def _menu_detach(self):
        self.on_undock_button_clicked()

    def _menu_close(self):
        self.on_close_button_clicked()

    def _menu_is_closable(self) -> bool:
        if self._test_config_flag(DockFlags.dock_area_close_button_closes_tab):
            widget = self._menu_dock_widget()
            return bool(widget and (widget.features() & DockWidgetFeature.closable))
        return self._dock_area.closable

    # ── Button state management ───────────────────────────────────────────

    def update_button_states(self):
        """Synchronise every title-bar button with themed icons, sizes, and widget features."""
        area = self._dock_area
        if area is None:
            return

        widget = area.current_dock_widget()
        if not widget:
            return

        count = area.open_dock_widgets_count()
        is_floating = self._menu_is_floating()
        is_pinned = self._menu_is_pinned()
        hide_disabled = self._test_config_flag(DockFlags.hide_disabled_title_bar_icons)

        icon_dim = self._style_mgr.get(DockStyleCategory.TITLE_BAR, "button_icon_size", 14)
        icon_size = QSize(icon_dim, icon_dim)

        # Tab-level features (current widget)
        tab_features = widget.features()
        tab_closable = bool(tab_features & DockWidgetFeature.closable)
        tab_floatable = bool(tab_features & DockWidgetFeature.floatable)
        tab_pinnable = bool(tab_features & DockWidgetFeature.pinnable)

        # Area-level features (aggregated)
        area_features = area.features()
        area_closable = bool(area_features & DockWidgetFeature.closable)
        area_floatable = bool(area_features & DockWidgetFeature.floatable)

        # — Tabs Menu Button —
        # Use dock_icon for proper Normal/Disabled state handling
        self._tabs_menu_button.setIcon(dock_icon("tabs_menu", DockStyleCategory.TITLE_BAR))
        self._tabs_menu_button.setIconSize(icon_size)
        self._tabs_menu_button.setVisible(self._test_config_flag(DockFlags.dock_area_has_tabs_menu_button))

        # — Close Button —
        self._close_button.setIcon(dock_icon("close", DockStyleCategory.TITLE_BAR))
        self._close_button.setIconSize(icon_size)
        
        closes_tab = self._test_config_flag(DockFlags.dock_area_close_button_closes_tab)
        if closes_tab:
            can_close = tab_closable
            self._close_button.setToolTip("Close")
        else:
            can_close = area_closable
            self._close_button.setToolTip("Close Group" if count > 1 else "Close")

        if self._test_config_flag(DockFlags.dock_area_has_close_button):
            # Use tab_closable for both hide and enable logic (responds to active tab)
            show_close = not (hide_disabled and not tab_closable)
            self._close_button.setVisible(show_close)
            self._close_button.setEnabled(tab_closable)
        else:
            self._close_button.setVisible(False)

        # — Undock / Float Button —
        undock_key = "dock" if is_floating else "float"
        self._undock_button.setIcon(dock_icon(undock_key, DockStyleCategory.TITLE_BAR))
        self._undock_button.setIconSize(icon_size)
        
        if self._test_config_flag(DockFlags.dock_area_has_undock_button):
            if is_floating:
                self._undock_button.setToolTip("Dock Group" if count > 1 else "Dock")
                self._undock_button.setVisible(True)
                self._undock_button.setEnabled(True)
            else:
                self._undock_button.setToolTip("Float Group" if count > 1 else "Float")
                # Use tab_floatable for both hide and enable logic (responds to active tab)
                show_undock = not (hide_disabled and not tab_floatable)
                self._undock_button.setVisible(show_undock)
                self._undock_button.setEnabled(tab_floatable)
        else:
            self._undock_button.setVisible(False)

        # — Pin / Unpin Button —
        pin_key = "unpin" if is_pinned else "pin"
        self._pin_button.setIcon(dock_icon(pin_key, DockStyleCategory.TITLE_BAR))
        self._pin_button.setIconSize(icon_size)
        self._pin_button.setToolTip("Unpin from Sidebar" if is_pinned else "Pin to Sidebar")
        
        has_sidebars = self._menu_has_sidebars()
        has_pin_button = self._test_config_flag(DockFlags.dock_area_has_pin_button)
        
        if has_sidebars and has_pin_button:
            show_pin = not (hide_disabled and not tab_pinnable)
            self._pin_button.setVisible(show_pin)
            self._pin_button.setEnabled(tab_pinnable)
        else:
            self._pin_button.setVisible(False)
        
    def update_pin_button_visibility(self):
        self._dock_area._update_title_bar_button_states()

    def refresh_style(self):
        # Retrieve all relevant style schemas
        styles = self._style_mgr.get_all(DockStyleCategory.TITLE_BAR)
        core_styles = self._style_mgr.get_all(DockStyleCategory.CORE)
        
        # Apply Geometry
        self.setFixedHeight(styles.get("height", 24))
        pad_left = styles.get("padding_left", 4)
        pad_right = styles.get("padding_right", 4)
        pad_top = styles.get("padding_top", 0)
        
        self._top_layout.setSpacing(styles.get("button_spacing", 4))
        self._top_layout.setContentsMargins(pad_left, pad_top, pad_right, 0)
        
        # Resolve Colors with fallbacks (matching sidebar_title_bar pattern)
        bg = styles.get("bg_normal")
        btn_color = styles.get("button_color")
        btn_hover = styles.get("button_hover_bg")
        disabled_color = core_styles.get("disabled_text_color")
        
        bg_css = bg.name() if bg else "palette(window)"
        btn_css = btn_color.name() if btn_color else "palette(text)"
        btn_hover_css = btn_hover.name() if btn_hover else "palette(mid)"
        disabled_css = disabled_color.name() if disabled_color else "palette(mid)"
        
        btn_radius = styles.get("button_corner_radius", 3)
        btn_padding = styles.get("button_padding", 4)
        btn_expand_v = styles.get("button_expand_vertical", True)
        btn_size = styles.get("button_size", 20)
        btn_icon_size = styles.get("button_icon_size", 16)
        
        # Title bar container styling only
        self.setStyleSheet(f"""
            DockAreaTitleBar {{
                background-color: {bg_css};
                border: none;
            }}
        """)
        
        # Apply button styling individually (unified with sidebar_title_bar)
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
        
        # Apply size policy based on vertical expansion setting
        v_policy = QSizePolicy.Expanding if btn_expand_v else QSizePolicy.Fixed
        icon_size = QSize(btn_icon_size, btn_icon_size)
        
        self._tabs_menu_button.setStyleSheet(button_css)
        self._tabs_menu_button.setSizePolicy(QSizePolicy.Fixed, v_policy)
        self._tabs_menu_button.setIconSize(icon_size)
        
        self._pin_button.setStyleSheet(button_css)
        self._pin_button.setSizePolicy(QSizePolicy.Fixed, v_policy)
        self._pin_button.setIconSize(icon_size)
        
        self._undock_button.setStyleSheet(button_css)
        self._undock_button.setSizePolicy(QSizePolicy.Fixed, v_policy)
        self._undock_button.setIconSize(icon_size)
        
        self._close_button.setStyleSheet(button_css)
        self._close_button.setSizePolicy(QSizePolicy.Fixed, v_policy)
        self._close_button.setIconSize(icon_size)

        # Trigger an update of the icons to ensure they reflect 
        # any changes in 'button_color'
        self.update_button_states()

    def on_style_changed(self, category: DockStyleCategory, changes: dict):
        self.refresh_style()

    def on_tabs_menu_about_to_show(self):
        if not self._menu_outdated:
            return
        menu = self._tabs_menu_button.menu()
        if menu is None:
            return
        menu.clear()
        self.build_dock_menu(menu, self._tab_bar)
        self._menu_outdated = False

    def on_tabs_menu_action_triggered(self, action: QAction):
        self.dispatch_dock_action(action)

    def on_close_button_clicked(self):
        logger.debug('DockAreaTitleBar.onCloseButtonClicked')
        if self._test_config_flag(DockFlags.dock_area_close_button_closes_tab):
            widget = self._dock_area.current_dock_widget()
            if widget and not (widget.features() & DockWidgetFeature.closable):
                return
            self._tab_bar.close_tab(self._tab_bar.current_index())
        else:
            self._dock_area.close_area()

    def on_undock_button_clicked(self):
        if self._menu_is_floating():
            self._menu_reattach()
        elif self._dock_area.floatable:
            self._tab_bar.make_area_floating(QCursor.pos(), DragState.inactive)

    def on_pin_button_clicked(self):
        self._menu_pin_current()
        self.pin_button_clicked.emit()

    def show_context_menu(self, global_pos: QPoint):
        self.mark_tabs_menu_outdated()
        self._tabs_menu.exec(global_pos)

    def on_current_tab_changed(self, index: int):
        if index < 0:
            return
        self._dock_area._update_title_bar_button_states()
        
    def mark_tabs_menu_outdated(self):
        self._menu_outdated = True

    def tab_bar(self) -> 'DockAreaTabBar':
        return self._tab_bar

    def button(self, which: TitleBarButton) -> Optional[QAbstractButton]:
        if which == TitleBarButton.tabs_menu:
            return self._tabs_menu_button
        if which == TitleBarButton.undock:
            return self._undock_button
        if which == TitleBarButton.close:
            return self._close_button
        if which == TitleBarButton.pin:
            return self._pin_button
        return None

    def setVisible(self, visible: bool):
        super().setVisible(visible)
        self.mark_tabs_menu_outdated()

    # --- Drag Functionality ---
    def _is_dragging_state(self, drag_state: DragState) -> bool:
        return self._drag_state == drag_state

    def _start_floating(self, dragging_state: DragState = DragState.floating_widget) -> bool:
        dock_container = self._dock_area.dock_container()
        if dock_container is None:
            return False

        if (dock_container.is_floating()
                and (dock_container.visible_dock_area_count() == 1)):
            return False

        self._drag_state = dragging_state
        size = self._dock_area.size()

        from .floating_dock_container import FloatingDockContainer
        self._floating_widget = FloatingDockContainer(dock_area=self._dock_area)

        if dragging_state == DragState.floating_widget:
            self._floating_widget.start_dragging(self._drag_start_mouse_position, size, self)
            overlay = self._dock_area.dock_manager().container_overlay()
            overlay.set_allowed_areas(DockWidgetArea.outer_dock_areas)
        else:
            self._floating_widget.init_floating_geometry(self._drag_start_mouse_position, size)

        top_level_dock_widget = self._floating_widget.top_level_dock_widget()
        if top_level_dock_widget is not None:
            top_level_dock_widget.emit_top_level_changed(True)

        return True

    def mousePressEvent(self, ev: QMouseEvent):
        if ev.button() == Qt.LeftButton:
            ev.accept()
            self._drag_start_mouse_position = ev.position().toPoint()
            self._drag_state = DragState.mouse_pressed
            return
        super().mousePressEvent(ev)

    def mouseReleaseEvent(self, ev: QMouseEvent):
        self._drag_start_mouse_position = QPoint()
        self._drag_state = DragState.inactive
        super().mouseReleaseEvent(ev)

    def mouseMoveEvent(self, ev: QMouseEvent):
        if not (ev.buttons() & Qt.LeftButton) or self._is_dragging_state(DragState.inactive):
            self._drag_state = DragState.inactive
            return super().mouseMoveEvent(ev)

        if self._is_dragging_state(DragState.floating_widget):
            if self._floating_widget:
                self._floating_widget.move_floating()
            return super().mouseMoveEvent(ev)

        drag_distance = (ev.position().toPoint() - self._drag_start_mouse_position).manhattanLength()
        
        if drag_distance >= start_drag_distance():
            dock_container = self._dock_area.dock_container()
            
            if dock_container and dock_container.is_floating() and dock_container.visible_dock_area_count() == 1:
                from .floating_dock_container import FloatingDockContainer
                floating_window = self.window()
                
                if isinstance(floating_window, FloatingDockContainer):
                    self._drag_state = DragState.floating_widget
                    self._floating_widget = floating_window
                    
                    mapped_start_pos = self.mapTo(floating_window, self._drag_start_mouse_position)
                    floating_window.start_dragging(mapped_start_pos, floating_window.size(), self)
                return

            if self._dock_area.floatable:
                self._start_floating()
        else:
            return super().mouseMoveEvent(ev)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if (self._dock_area.floatable and self._dock_area.dock_container() and
                (not self._dock_area.dock_container().is_floating()
                 or self._dock_area.dock_container().visible_dock_area_count() > 1)):
            self._drag_start_mouse_position = event.position().toPoint()
            self._start_floating(DragState.inactive)

        super().mouseDoubleClickEvent(event)