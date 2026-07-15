# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2019 Ken Lauer
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace, adapted from qtpydocking.
# Original code Copyright (c) 2019 Ken Lauer (BSD-3-Clause).
# Modifications Copyright (c) 2026 opticsWolf (Apache-2.0).


import logging
from typing import TYPE_CHECKING, Optional, Union

from PySide6.QtCore import QEvent, QSize, Qt, Signal, QRectF
from PySide6.QtGui import QAction, QIcon, QPalette, QShowEvent
from PySide6.QtWidgets import (QBoxLayout, QFrame, QScrollArea,
                               QSplitter, QToolBar, QWidget)

# --- ADDED IMPORTS ---
from .dock_styled import DockStyled
from .dock_theme import DockStyleCategory, resolve_dock_colors, build_dock_palette
from .enums import (DockWidgetFeature, WidgetState, ToggleViewActionMode,
                    InsertMode)
from .util import find_parent, emit_top_level_event_for_widget

if TYPE_CHECKING:
    from . import DockAreaWidget, DockManager, DockWidgetTab

logger = logging.getLogger(__name__)


class DockWidget(QFrame, DockStyled):
    STYLE_CATEGORIES = (DockStyleCategory.PANEL, DockStyleCategory.CORE)
    view_toggled = Signal(bool)
    closed = Signal()
    title_changed = Signal(str)
    top_level_changed = Signal(bool)
    features_changed = Signal(DockWidgetFeature)

    def __init__(self, title: str, parent: QWidget = None):
        super().__init__(parent)
        
        # Flattened private properties
        self._layout = QBoxLayout(QBoxLayout.TopToBottom)
        self._widget: QWidget = None
        self._tab_widget: 'DockWidgetTab' = None
        self._features = DockWidgetFeature.all_features
        self._dock_manager: 'DockManager' = None
        self._dock_area: 'DockAreaWidget' = None
        self._toggle_view_action: QAction = None
        self._closed = False
        self._scroll_area: QScrollArea = None
        self._tool_bar: QToolBar = None
        self._tool_bar_style_docked = Qt.ToolButtonIconOnly
        self._tool_bar_style_floating = Qt.ToolButtonTextUnderIcon
        self._tool_bar_icon_size_docked = QSize(16, 16)
        self._tool_bar_icon_size_floating = QSize(24, 24)
        self._is_floating_top_level = False
        self._widget_state = WidgetState.docked  # <-- NEW: Track current state
        self._style_dirty = False  # Track if style refresh is pending

        # Make the DockWidget frame borderless
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setAutoFillBackground(True)
        self.setBackgroundRole(QPalette.ColorRole.Window) # Native Qt behavior

        self._layout.setContentsMargins(6, 6, 6, 6)
        self._layout.setSpacing(0)
        self.setLayout(self._layout)
        self.setWindowTitle(title)
        self.setObjectName(title)

        from .dock_widget_tab import DockWidgetTab
        self._tab_widget = DockWidgetTab(dock_widget=self, parent=None)
        
        self._toggle_view_action = QAction(title, self)
        self._toggle_view_action.setCheckable(True)
        self._toggle_view_action.triggered.connect(self.toggle_view)
        
        self.set_toolbar_floating_style(False)

        # --- NEW: Style Manager Integration ---
        self._init_dock_style()

    def __repr__(self):
        return f'<{self.__class__.__name__} title={self.windowTitle()!r}>'

    def _show_dock_widget(self):
        if self.is_in_sidebar():
            if self._dock_manager and hasattr(self._dock_manager, 'sidebar_manager'):
                self._dock_manager.sidebar_manager.show_widget(self)
            return

        from .floating_dock_container import FloatingDockContainer
        if not self._dock_area:
            floating_widget = FloatingDockContainer(dock_widget=self)
            floating_widget.resize(self.size())
            floating_widget.show()
            return

        self._dock_area.toggle_view(True)
        self._dock_area.set_current_dock_widget(self)
        self._tab_widget.show()

        splitter = find_parent(QSplitter, self._dock_area)
        while splitter and not splitter.isVisible():
            splitter.show()
            splitter = find_parent(QSplitter, splitter)

        container = self._dock_area.dock_container()
        if container.is_floating():
            floating_widget = find_parent(FloatingDockContainer, container)
            floating_widget.show()

        if self._dock_manager and hasattr(self._dock_manager, 'sidebar_manager'):
            self._dock_manager.sidebar_manager.raise_overlays()

    def _hide_dock_widget(self):
        if self.is_in_sidebar():
            if self._dock_manager and hasattr(self._dock_manager, 'sidebar_manager'):
                self._dock_manager.sidebar_manager.hide_widget(self)
            return

        self._tab_widget.hide()
        self._update_parent_dock_area()

    def _update_parent_dock_area(self):
        if not self._dock_area:
            return

        next_dock_widget = self._dock_area.next_open_dock_widget(self)
        if next_dock_widget is not None:
            self._dock_area.set_current_dock_widget(next_dock_widget)
        else:
            self._dock_area.hide_area_with_no_visible_content()

    def _setup_tool_bar(self):
        self._tool_bar = QToolBar(self)
        self._tool_bar.setObjectName("dockWidgetToolBar")
        
        # PURE NATIVE APPROACH: 
        # Makes the toolbar transparent without overriding the style engine.
        self._tool_bar.setAutoFillBackground(False)
        self._tool_bar.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # (Optional) If Fusion style draws a grip/handle you want to hide:
        #self._tool_bar.setMovable(False) 
        
        self._layout.insertWidget(0, self._tool_bar)
        self._tool_bar.setIconSize(QSize(16, 16))
        self._tool_bar.toggleViewAction().setEnabled(False)
        self._tool_bar.toggleViewAction().setVisible(False)
        self.top_level_changed.connect(self.set_toolbar_floating_style)

    def _setup_scroll_area(self):
        self._scroll_area = QScrollArea(self)
        self._scroll_area.setObjectName("dockWidgetScrollArea")
        
        # Replaces 'border: none; background-color: transparent;'
        self._scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_area.viewport().setAutoFillBackground(False)
        
        self._scroll_area.setWidgetResizable(True)
        self._layout.addWidget(self._scroll_area)

    def set_toolbar_floating_style(self, floating: bool):
        if not self._tool_bar:
            return

        icon_size = (self._tool_bar_icon_size_floating
                     if floating
                     else self._tool_bar_icon_size_docked)
        if icon_size != self._tool_bar.iconSize():
            self._tool_bar.setIconSize(icon_size)

        button_style = (self._tool_bar_style_floating
                        if floating
                        else self._tool_bar_style_docked)
        if button_style != self._tool_bar.toolButtonStyle():
            self._tool_bar.setToolButtonStyle(button_style)

    def set_dock_manager(self, dock_manager: 'DockManager'):
        self._dock_manager = dock_manager

    def set_dock_area(self, dock_area: 'DockAreaWidget'):
        self._dock_area = dock_area
        self._toggle_view_action.setChecked((dock_area is not None or self.is_in_sidebar()) and not self.is_closed())
        
        # If the widget is moved back to the main window, reset its state to docked
        if dock_area:
            container = dock_area.dock_container()
            if container and not container.is_floating():
                self.set_widget_state(WidgetState.docked)

        self.refresh_style()

    def set_toggle_view_action_checked(self, checked: bool):
        action = self._toggle_view_action
        action.blockSignals(True)
        action.setChecked(checked)
        action.blockSignals(False)

    def save_state(self) -> dict:
        """Phase 2: Modernized dict-based state saving."""
        return {
            "type": "Widget",
            "name": self.objectName(),
            "closed": self._closed
        }

    def flag_as_unassigned(self):
        self._closed = True
        parent_widget = getattr(self._dock_manager, '_root', None) or self._dock_manager
        logger.debug('flag_as_unassigned %s -> setParent %s', self, parent_widget)
        self.setParent(parent_widget)
        self.setVisible(False)
        self.set_dock_area(None)

        tab_widget = self.tab_widget()
        logger.debug('flag_as_unassigned %s -> setParent %s', tab_widget, self)
        tab_widget.setParent(self)

    def emit_top_level_changed(self, floating: bool):
        if floating != self._is_floating_top_level:
            self._is_floating_top_level = floating
            self.top_level_changed.emit(self._is_floating_top_level)

    def set_closed_state(self, closed: bool):
        self._closed = closed

    def toggle_view_internal(self, open_: bool):
        dock_container = self.dock_container()
        top_level_dock_widget_before = (dock_container.top_level_dock_widget()
                                        if dock_container else None)
        if open_:
            self._show_dock_widget()
        else:
            self._hide_dock_widget()

        self._closed = not open_
        self._toggle_view_action.blockSignals(True)
        self._toggle_view_action.setChecked(open_)
        self._toggle_view_action.blockSignals(False)
        
        if self._dock_area:
            self._dock_area.toggle_dock_widget_view(self, open_)

        if open_ and top_level_dock_widget_before:
            emit_top_level_event_for_widget(top_level_dock_widget_before, False)

        dock_container = self.dock_container()
        top_level_dock_widget_after = (dock_container.top_level_dock_widget()
                                       if dock_container else None)
        emit_top_level_event_for_widget(top_level_dock_widget_after, True)
        
        if dock_container is not None:
            floating_container = dock_container.floating_widget()
            if floating_container is not None:
                floating_container.update_window_title()

        if not open_:
            self.closed.emit()

        self.view_toggled.emit(open_)

    def minimumSizeHint(self) -> QSize:
        return QSize(60, 40)

    def set_widget(self, widget: QWidget, insert_mode: InsertMode = InsertMode.auto_scroll_area):
        scroll_area = isinstance(widget, QScrollArea)
        if scroll_area or InsertMode.force_no_scroll_area == insert_mode:
            self._layout.addWidget(widget)
            if scroll_area:
                viewport = widget.viewport()
                if viewport is not None:
                    viewport.setProperty('dockWidgetContent', True)
        else:
            self._setup_scroll_area()
            self._scroll_area.setWidget(widget)

        self._widget = widget
        self._widget.setProperty("dockWidgetContent", True)
        self._update_bottom_mask()

    def take_widget(self):
        self._scroll_area.takeWidget()
        widget = self._widget
        self._layout.removeWidget(widget)
        widget.setParent(None)
        return widget

    def widget(self) -> QWidget:
        return self._widget

    def tab_widget(self) -> 'DockWidgetTab':
        return self._tab_widget

    def set_features(self, features: DockWidgetFeature):
        if self._features == features:
            return
        self._features = features
        self.features_changed.emit(self._features)
        if self._tab_widget:
            self._tab_widget.update_close_button_visibility()
        if self._dock_area:
            self._dock_area._update_title_bar_button_states()

    def set_feature(self, flag: DockWidgetFeature, on: bool = True):
        old_features = self._features
        if on:
            self._features |= flag
        else:
            self._features &= ~flag
        if self._features != old_features:
            self.features_changed.emit(self._features)
            if self._tab_widget:
                self._tab_widget.update_close_button_visibility()
            if self._dock_area:
                self._dock_area._update_title_bar_button_states()

    def features(self) -> DockWidgetFeature:
        return self._features

    def dock_manager(self) -> 'DockManager':
        return self._dock_manager

    def dock_container(self) -> Optional['DockContainerWidget']:
        return self._dock_area.dock_container() if self._dock_area else None

    def dock_area_widget(self) -> 'DockAreaWidget':
        return self._dock_area

    def is_floating(self) -> bool:
        if not self.is_in_floating_container():
            return False
        return self.dock_container().top_level_dock_widget() is self

    def is_in_floating_container(self) -> bool:
        container = self.dock_container()
        return container and container.is_floating()

    def is_in_sidebar(self) -> bool:
        if self._widget_state in (WidgetState.pinned_shown, WidgetState.pinned_hidden):
            return True
        if self._dock_manager and hasattr(self._dock_manager, 'sidebar_manager'):
            return self._dock_manager.sidebar_manager.is_pinned(self)
        return False

    def is_pinned(self) -> bool:
        return self.is_in_sidebar()

    def is_closed(self) -> bool:
        return self._closed

    def toggle_view_action(self) -> QAction:
        return self._toggle_view_action

    def set_toggle_view_action_mode(self, mode: ToggleViewActionMode):
        is_action_mode = ToggleViewActionMode.toggle == mode
        self._toggle_view_action.setCheckable(is_action_mode)
        icon = QIcon() if is_action_mode else self._tab_widget.icon()
        if icon is not None:
            self._toggle_view_action.setIcon(icon)

    def set_icon(self, icon: Union[QIcon, str]):
        self._tab_widget.set_icon(icon)
        if not self._toggle_view_action.isCheckable() and self._tab_widget.icon():
            self._toggle_view_action.setIcon(self._tab_widget.icon())

    def icon(self) -> QIcon:
        return self._tab_widget.icon()

    def set_default_icon_name(self, name: str):
        self._tab_widget.set_default_icon_name(name)
        if not self._toggle_view_action.isCheckable() and self._tab_widget.icon():
            self._toggle_view_action.setIcon(self._tab_widget.icon())

    def default_icon_name(self) -> str:
        return self._tab_widget.default_icon_name()

    def set_custom_icon(self, icon: Union[QIcon, str]):
        self._tab_widget.set_custom_icon(icon)
        if not self._toggle_view_action.isCheckable() and self._tab_widget.icon():
            self._toggle_view_action.setIcon(self._tab_widget.icon())

    def custom_icon(self) -> QIcon:
        return self._tab_widget.custom_icon()

    def set_custom_icon_name(self, name: str):
        self._tab_widget.set_custom_icon_name(name)
        if not self._toggle_view_action.isCheckable() and self._tab_widget.icon():
            self._toggle_view_action.setIcon(self._tab_widget.icon())

    def custom_icon_name(self) -> str:
        return self._tab_widget.custom_icon_name()

    def tool_bar(self) -> QToolBar:
        return self._tool_bar

    def create_default_tool_bar(self) -> QToolBar:
        if not self._tool_bar:
            self._setup_tool_bar()
        return self._tool_bar

    def set_tool_bar(self, tool_bar: QToolBar):
        if self._tool_bar:
            self._tool_bar.deleteLater()
            self._tool_bar = None

        self._tool_bar = tool_bar
        self._layout.insertWidget(0, self._tool_bar)
        self.top_level_changed.connect(self.set_toolbar_floating_style)
        self.set_toolbar_floating_style(self.is_floating())

    def set_tool_bar_style(self, style: Qt.ToolButtonStyle, state: WidgetState):
        if WidgetState.floating == state:
            self._tool_bar_style_floating = style
        else:
            self._tool_bar_style_docked = style
        self.set_toolbar_floating_style(self.is_floating())

    def tool_bar_style(self, state: WidgetState) -> Qt.ToolButtonStyle:
        return (self._tool_bar_style_floating
                if WidgetState.floating == state
                else self._tool_bar_style_docked)

    def set_tool_bar_icon_size(self, icon_size: QSize, state: WidgetState):
        if WidgetState.floating == state:
            self._tool_bar_icon_size_floating = icon_size
        else:
            self._tool_bar_icon_size_docked = icon_size
        self.set_toolbar_floating_style(self.is_floating())

    def tool_bar_icon_size(self, state: WidgetState) -> QSize:
        return (self._tool_bar_icon_size_floating
                if WidgetState.floating == state
                else self._tool_bar_icon_size_docked)

    def set_tab_tool_tip(self, text: str):
        if self._tab_widget:
            self._tab_widget.setToolTip(text)
        if self._toggle_view_action:
            self._toggle_view_action.setToolTip(text)
        if self._dock_area:
            self._dock_area.mark_title_bar_menu_outdated()
            
    def widget_state(self) -> WidgetState:
        return self._widget_state

    def set_widget_state(self, state: WidgetState):
        """Updates the widget state and triggers relevant UI adjustments (e.g., toolbar sizing)."""
        if self._widget_state != state:
            self._widget_state = state
            
            # Use floating toolbar style for detached windows AND open sidebar overlays
            is_large_context = state in (WidgetState.floating, WidgetState.pinned_shown)
            self.set_toolbar_floating_style(is_large_context)

    def event(self, e: QEvent) -> bool:
        if e.type() == QEvent.WindowTitleChange:
            title = self.windowTitle()
            if self._tab_widget:
                self._tab_widget.set_text(title)
            if self._toggle_view_action:
                self._toggle_view_action.setText(title)
            if self._dock_area:
                self._dock_area.mark_title_bar_menu_outdated()
            self.title_changed.emit(title)

        return super().event(e)

    def showEvent(self, event: QShowEvent):
        """Refresh style when widget becomes visible to ensure palette is current."""
        super().showEvent(event)
        # Apply any pending style changes that occurred while hidden
        if self._style_dirty:
            self._style_dirty = False
            self.refresh_style()

    def refresh_style(self):
        """
        Applies the localized panel palette override and strictly pushes
        it down to children to bypass Qt StyleSheet inheritance breaks.
        """
        colors = resolve_dock_colors()
        pal = build_dock_palette(is_panel=True, colors=colors)
        self.setPalette(pal)

        if self.is_in_sidebar():
            card_radius = self._style_mgr.get(DockStyleCategory.SIDEPANEL, "corner_radius")
            if card_radius is None:
                card_radius = self._style_mgr.get(DockStyleCategory.CORE, "corner_radius", 0)
            card_border = self._style_mgr.get(DockStyleCategory.SIDEPANEL, "border_width")
            if card_border is None:
                card_border = self._style_mgr.get(DockStyleCategory.CORE, "border_width", 0.0)
        else:
            card_radius = self._style_mgr.get(DockStyleCategory.CORE, "corner_radius", 0)
            card_border = self._style_mgr.get(DockStyleCategory.CORE, "border_width", 0.0)
        from math import ceil
        bw_int = ceil(card_border) if card_border > 0 else 0
        if card_radius > 0 and not self.is_floating():
            self._bottom_radius = max(0.0, float(card_radius - bw_int))
            self.setAutoFillBackground(False)
            self.setAttribute(Qt.WA_StyledBackground, False)
        else:
            self._bottom_radius = 0.0
            self.setAutoFillBackground(True)
            self.setBackgroundRole(QPalette.ColorRole.Window)

        margin_raw = self._style_mgr.get(DockStyleCategory.PANEL, "content_margin", 6)
        if isinstance(margin_raw, (int, float)):
            left = right = top = bottom = int(margin_raw)
        elif isinstance(margin_raw, (list, tuple)):
            if len(margin_raw) == 1:
                left = right = top = bottom = int(margin_raw[0])
            elif len(margin_raw) >= 2:
                left = right = bottom = int(margin_raw[0])
                top = int(margin_raw[1])
        else:
            left = right = top = bottom = 6
        self._layout.setContentsMargins(left, top, right, bottom)

        # Force the panel palette onto the immediate content layer
        # so Qt StyleSheets don't sever the inheritance to user widgets.
        if self._scroll_area:
            self._scroll_area.setPalette(pal)
            if self._scroll_area.widget():
                self._scroll_area.widget().setPalette(pal)
        elif self._widget:
            self._widget.setPalette(pal)

        self.update()
        self._update_bottom_mask()

    def paintEvent(self, event) -> None:
        from PySide6.QtGui import QPainter
        from .dock_paint import bottom_rounded_path
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        bg = self.palette().color(QPalette.ColorRole.Window)
        if bg.alpha() > 0:
            if getattr(self, "_bottom_radius", 0.0) > 0.0:
                path = bottom_rounded_path(QRectF(self.rect()), self._bottom_radius)
                p.fillPath(path, bg)
            else:
                p.fillRect(self.rect(), bg)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Children (QScrollArea / user widget) are already resized at this point.
        # Apply the mask synchronously — no timer needed.
        self._apply_bottom_mask_sync()

    def _apply_bottom_mask_sync(self) -> None:
        """Apply the bottom mask synchronously. Call from resizeEvent or refresh_style."""
        if getattr(self, "_mask_applying", False):
            return  # already applying in this event cycle
        self._mask_applying = True
        try:
            self._apply_bottom_mask()
        finally:
            self._mask_applying = False

    def _update_bottom_mask(self) -> None:
        """Thin wrapper for backwards compatibility with callers outside resizeEvent."""
        target = self._scroll_area or self._widget
        if not target:
            return
        self._apply_bottom_mask_sync()

    def _apply_bottom_mask(self) -> None:
        target = self._scroll_area or self._widget
        if not target or not self.isVisible() or not target.isVisible():
            return
        radius = getattr(self, "_bottom_radius", 0.0)
        m_bottom = self._layout.contentsMargins().bottom()
        target_radius = max(0.0, radius - m_bottom) if radius > 0.0 else 0.0

        current_cache = (target.rect().size(), target_radius)
        if getattr(self, "_last_mask_cache", None) == current_cache:
            return
        self._last_mask_cache = current_cache

        if target_radius > 0.0 and target.width() > 0 and target.height() > 0:
            from PySide6.QtGui import QRegion
            from .dock_paint import bottom_rounded_path
            path = bottom_rounded_path(QRectF(target.rect()), target_radius)
            target.setMask(QRegion(path.toFillPolygon().toPolygon()))
        else:
            target.clearMask()

    def on_style_changed(self, category: DockStyleCategory, changes: dict):
        """Callback triggered by DockStyleManager when the theme switches."""
        # Listen for both PANEL and CORE changes just in case shared colors update
        if category in (DockStyleCategory.PANEL, DockStyleCategory.CORE):
            if self.isVisible():
                self.refresh_style()
            else:
                # Defer refresh until widget becomes visible
                self._style_dirty = True

    def toggle_view(self, open_: bool):
        sender = self.sender()
        if sender is self._toggle_view_action and not self._toggle_view_action.isCheckable():
            open_ = True

        if self._closed != (not open_):
            self.toggle_view_internal(open_)
        elif open_ and self._dock_area:
            self._dock_area.set_current_dock_widget(self)