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
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import QRect, Signal
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QAbstractButton, QBoxLayout

from .util import (find_parent, DEBUG_LEVEL, hide_empty_parent_splitters,
                   emit_top_level_event_for_widget)
from .enums import TitleBarButton, DockWidgetFeature
from .dock_area_layout import DockAreaLayout
from .dock_chrome import ChromeFrame
from .dock_paint import ChromeTokens
from .dock_styled import DockStyled
from .dock_theme import DockStyleCategory

if TYPE_CHECKING:
    from . import DockContainerWidget, DockManager, DockWidget, DockAreaTabBar, DockAreaTitleBar

logger = logging.getLogger(__name__)


class DockAreaWidget(ChromeFrame, DockStyled):
    STYLE_CATEGORIES = (DockStyleCategory.CORE, DockStyleCategory.PANEL)
    tab_bar_clicked = Signal(int)
    current_changing = Signal(int)
    current_changed = Signal(int)
    view_toggled = Signal(bool)

    def __init__(self, dock_manager: 'DockManager', parent: 'DockContainerWidget'):
        super().__init__(parent)
        
        self._dock_manager = dock_manager
        self._layout = QBoxLayout(QBoxLayout.TopToBottom)
        self._contents_layout: DockAreaLayout = None
        self._title_bar: 'DockAreaTitleBar' = None
        self._update_title_bar_buttons = False
        self._locked_name = None

        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self.setLayout(self._layout)
        
        self._contents_layout = DockAreaLayout(self._layout)
        self._create_title_bar()

        self._init_dock_style()

        from PySide6.QtWidgets import QApplication
        qapp = QApplication.instance()
        if qapp:
            qapp.focusChanged.connect(self._on_app_focus_changed)

    @property
    def locked_name(self) -> Optional[str]:
        return self._locked_name

    @locked_name.setter
    def locked_name(self, name: Optional[str]):
        self._locked_name = name
        self._update_title_bar_button_states()

    def _on_app_focus_changed(self, old_widget, new_widget):
        try:
            if self.isHidden() or not self.isVisible():
                return
            if new_widget is not None:
                try:
                    if not new_widget.isVisible():
                        return
                except RuntimeError:
                    return
                if self.isAncestorOf(new_widget) or (new_widget is self):
                    if self._dock_manager:
                        self._dock_manager.set_active_dock_area(self)
                    else:
                        self.set_chrome_focused(True)
        except RuntimeError:
            return

    def set_chrome_focused(self, focused: bool):
        super().set_chrome_focused(focused)
        for widget in self.opened_dock_widgets():
            tab = widget.tab_widget()
            if tab:
                tab.refresh_style()

    def mousePressEvent(self, event):
        try:
            if self._dock_manager and not self.isHidden():
                self._dock_manager.set_active_dock_area(self)
        except RuntimeError:
            pass
        super().mousePressEvent(event)

    def __repr__(self):
        return f'<{self.__class__.__name__}>'

    def _create_title_bar(self):
        from .dock_area_title_bar import DockAreaTitleBar
        self._title_bar = DockAreaTitleBar(self)
        self._layout.addWidget(self._title_bar)

        tab_bar = self._tab_bar()
        tab_bar.tab_close_requested.connect(self.on_tab_close_requested)
        self._title_bar.tab_bar_clicked.connect(self.set_current_index)
        tab_bar.tab_moved.connect(self.reorder_dock_widget)

    def _tab_bar(self) -> 'DockAreaTabBar':
        return self._title_bar.tab_bar()

    def dock_manager(self) -> 'DockManager':
        return self._dock_manager

    def _update_title_bar_button_states(self):
        """Delegates synchronization of the title bar buttons to the title bar itself."""
        if self.isHidden():
            self._update_title_bar_buttons = True
            return

        if self._title_bar:
            self._title_bar.update_button_states()

        self._update_title_bar_buttons = False

    def update_title_bar_button_states(self):
        self._update_title_bar_button_states()

    def on_tab_close_requested(self, index: int):
        logger.debug('DockAreaWidget.onTabCloseRequested %s', index)
        self.dock_widget(index).toggle_view(False)

    def reorder_dock_widget(self, from_index: int, to_index: int):
        logger.debug('DockAreaWidget.reorderDockWidget')
        if (from_index >= self._contents_layout.count() or
                from_index < 0 or
                to_index >= self._contents_layout.count() or
                to_index < 0 or
                from_index == to_index):
            return

        widget = self._contents_layout.widget(from_index)
        self._contents_layout.remove_widget(widget)
        self._contents_layout.insert_widget(to_index, widget)
        self.set_current_index(to_index)

    def insert_dock_widget(self, index: int, dock_widget: 'DockWidget', activate: bool = True):
        self._contents_layout.insert_widget(index, dock_widget)
        dock_widget.tab_widget().set_dock_area_widget(self)
        tab_widget = dock_widget.tab_widget()

        tab_bar = self._tab_bar()
        tab_bar.blockSignals(True)
        tab_bar.insert_tab(index, tab_widget)
        tab_bar.blockSignals(False)

        tab_widget.setVisible(not dock_widget.is_closed())
        dock_widget.setProperty('index', index)
        if activate:
            self.set_current_index(index)

        if self._dock_manager:
            dock_widget.set_dock_manager(self._dock_manager)
        dock_widget.set_dock_area(self)
        self._update_title_bar_button_states()

    def add_dock_widget(self, dock_widget: 'DockWidget'):
        self.insert_dock_widget(self._contents_layout.count(), dock_widget)

    def remove_dock_widget(self, dock_widget: 'DockWidget'):
        logger.debug('DockAreaWidget.removeDockWidget')
        next_open_dock_widget = self.next_open_dock_widget(dock_widget)
        self._contents_layout.remove_widget(dock_widget)
        tab_widget = dock_widget.tab_widget()
        tab_widget.hide()
        self._tab_bar().remove_tab(tab_widget)
        dock_container = self.dock_container()
        
        if next_open_dock_widget is not None:
            self.set_current_dock_widget(next_open_dock_widget)
        elif (self._contents_layout.is_empty() and
                  dock_container.dock_area_count() > 1):
            logger.debug('Dock Area empty')
            dock_container.remove_dock_area(self)
            self.deleteLater()
        else:
            self.hide_area_with_no_visible_content()

        self._update_title_bar_button_states()
        self.update_title_bar_visibility()
        
        top_level_dock_widget = dock_container.top_level_dock_widget()
        if top_level_dock_widget is not None:
            top_level_dock_widget.emit_top_level_changed(True)

        if DEBUG_LEVEL > 0:
            dock_container.dump_layout()

    def toggle_dock_widget_view(self, dock_widget: 'DockWidget', open_: bool):
        self.update_title_bar_visibility()
        self._update_title_bar_button_states()

    def next_open_dock_widget(self, dock_widget: 'DockWidget') -> Optional['DockWidget']:
        open_dock_widgets = self.opened_dock_widgets()
        count = len(open_dock_widgets)
        if count > 1 or (count == 1 and open_dock_widgets[0] != dock_widget):
            if open_dock_widgets[-1] == dock_widget:
                next_dock_widget = open_dock_widgets[-2]
            else:
                next_index = open_dock_widgets.index(dock_widget) + 1
                next_dock_widget = open_dock_widgets[next_index]
            return next_dock_widget
        return None

    def index(self, dock_widget: 'DockWidget') -> int:
        return self._contents_layout.index_of(dock_widget)

    def hide_area_with_no_visible_content(self):
        self.toggle_view(False)

        from .dock_splitter import DockSplitter
        splitter = find_parent(DockSplitter, self)
        hide_empty_parent_splitters(splitter)

        container = self.dock_container()
        if not container.is_floating():
            return

        self.update_title_bar_visibility()
        top_level_widget = container.top_level_dock_widget()
        floating_widget = container.floating_widget()
        if top_level_widget is not None:
            floating_widget.update_window_title()
            emit_top_level_event_for_widget(top_level_widget, True)
        elif not container.opened_dock_areas():
            floating_widget.hide()

    def update_title_bar_visibility(self):
        container = self.dock_container()
        if not container:
            return

        if self._title_bar:
            self._title_bar.setVisible(True)

    def internal_set_current_dock_widget(self, dock_widget: 'DockWidget'):
        index = self.index(dock_widget)
        if index < 0:
            return
        self.set_current_index(index)

    def mark_title_bar_menu_outdated(self):
        if self._title_bar:
            self._title_bar.mark_tabs_menu_outdated()

    def toggle_view(self, open_: bool):
        self.setVisible(open_)
        self.view_toggled.emit(open_)

    def dock_manager(self) -> 'DockManager':
        return self._dock_manager

    def dock_container(self) -> 'DockContainerWidget':
        from .dock_container_widget import DockContainerWidget
        return find_parent(DockContainerWidget, self)

    def title_bar_geometry(self) -> QRect:
        return self._title_bar.geometry()

    def content_area_geometry(self) -> QRect:
        return self._contents_layout.geometry()

    def dock_widgets_count(self) -> int:
        return self._contents_layout.count()

    def dock_widgets(self) -> list:
        return [
            self.dock_widget(i)
            for i in range(self._contents_layout.count())
        ]

    def open_dock_widgets_count(self) -> int:
        return len(self.opened_dock_widgets())

    def opened_dock_widgets(self) -> list:
        return [w for w in self.dock_widgets() if not w.is_closed()]

    def dock_widget(self, index: int) -> 'DockWidget':
        return self._contents_layout.widget(index)

    def current_index(self) -> int:
        return self._contents_layout.current_index()

    def index_of_first_open_dock_widget(self) -> int:
        for i in range(self._contents_layout.count()):
            if not self.dock_widget(i).is_closed():
                return i
        return -1

    def current_dock_widget(self) -> Optional['DockWidget']:
        current_index = self.current_index()
        if current_index < 0:
            return None
        return self.dock_widget(current_index)

    def set_current_dock_widget(self, dock_widget: 'DockWidget'):
        if self.dock_manager().is_restoring_state():
            return
        self.internal_set_current_dock_widget(dock_widget)

    def save_state(self) -> dict:
        current_dock_widget = self.current_dock_widget()
        name = current_dock_widget.objectName() if current_dock_widget else ''
        logger.debug('DockAreaWidget.saveState TabCount: %s current: %s',
                     self._contents_layout.count(), name)

        return {
            "type": "Area",
            "tabs": self._contents_layout.count(),
            "current": name,
            "widgets": [self.dock_widget(i).save_state() for i in range(self._contents_layout.count())]
        }

    @property
    def closable(self):
        return bool(self.features() & DockWidgetFeature.closable)

    @property
    def movable(self):
        return bool(self.features() & DockWidgetFeature.movable)

    @property
    def floatable(self):
        return bool(self.features() & DockWidgetFeature.floatable)

    @property
    def pinnable(self):
        return bool(self.features() & DockWidgetFeature.pinnable)

    def features(self) -> DockWidgetFeature:
        # --- FIX: Only intersect the features of OPEN dock widgets! ---
        # Prevents hidden/closed widgets from falsely locking the area.
        features = DockWidgetFeature.all_features
        has_locked = False
        for dock_widget in self.opened_dock_widgets():
            features &= dock_widget.features()
            if getattr(dock_widget, 'locked_to_area', None) or self.locked_name:
                has_locked = True
        if has_locked:
            features |= DockWidgetFeature.floatable
            features &= ~DockWidgetFeature.pinnable
        return features

    def title_bar_button(self, which: TitleBarButton) -> QAbstractButton:
        return self._title_bar.button(which)

    def is_maximized(self) -> bool:
        """Return True if this area is currently maximized within its container."""
        container = self.dock_container()
        return container is not None and container.is_area_maximized(self)

    def toggle_maximize(self):
        """Toggle the maximize/restore state of this dock area."""
        container = self.dock_container()
        if container is not None:
            container.toggle_maximize_dock_area(self)

    def setVisible(self, visible: bool):
        super().setVisible(visible)
        if self._update_title_bar_buttons:
            self._update_title_bar_button_states()

    def set_current_index(self, index: int):
        tab_bar = self._tab_bar()
        if index < 0 or index > (tab_bar.count() - 1):
            logger.warning('Invalid index %s', index)
            return

        try:
            if self._dock_manager and not self._dock_manager.is_restoring_state():
                self._dock_manager.set_active_dock_area(self)
        except RuntimeError:
            pass

        self.current_changing.emit(index)
        tab_bar.set_current_index(index)
        self._contents_layout.set_current_index(index)
        self._contents_layout.current_widget().show()
        self.current_changed.emit(index)

    def close_area(self):
        for dock_widget in list(self.opened_dock_widgets()):
            if dock_widget.features() & DockWidgetFeature.closable:
                dock_widget.toggle_view(False)

    def close_other_areas(self):
        self.dock_container().close_other_areas(self)

    def refresh_style(self):
        core = self._style_mgr.get_all(DockStyleCategory.CORE)
        panel = self._style_mgr.get_all(DockStyleCategory.PANEL)

        panel_bg = panel.get("bg_normal")

        # Painted chrome: rounded panel_bg fill + optional outline, with the
        # focus outline as a colour swap.  This is the artifact-free
        # replacement for the border/radius stylesheet that had to be disabled.
        self.set_chrome(ChromeTokens(
            bg=panel_bg,
            border=core.get("border_color"),
            border_width=core.get("border_width", 0.0),
            radius=core.get("corner_radius", 0),
            focus_border=core.get("focus_border_color"),
        ))

        title_styles = self._style_mgr.get_all(DockStyleCategory.TITLE_BAR)
        title_margin = title_styles.get("margin")
        if self._layout is not None:
            m_card = self.chrome().content_margin()
            if title_margin is not None:
                from math import ceil
                bw = self.chrome().border_width
                bw_int = ceil(bw) if bw > 0 else 0
                m_title = bw_int + max(0, int(title_margin))
                self._layout.setContentsMargins(bw_int, m_title, bw_int, bw_int)
            else:
                self._layout.setContentsMargins(m_card, m_card, m_card, m_card)

        # Propagate the panel background to children via the Window palette
        # role so standard Qt widgets inside the area inherit it.
        if panel_bg:
            pal = self.palette()
            pal.setColor(QPalette.ColorRole.Window, panel_bg)
            self.setPalette(pal)

