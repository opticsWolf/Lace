# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Flag, auto
from typing import TYPE_CHECKING, Dict, Optional, Protocol, Any, List

from PySide6.QtCore import QPoint, QRect, QSize
from PySide6.QtGui import QAction, QColor, QIcon, QPainter
from PySide6.QtWidgets import QApplication, QMenu, QStyle

from .enums import DockWidgetArea, DockWidgetFeature, WidgetState, DockFlags
from .dock_style_manager import get_dock_style_manager
from .dock_theme import DockStyleCategory
from .dock_icon_provider import get_icon_provider
from ._trace import trace

if TYPE_CHECKING:
    from .dock_area_widget import DockAreaWidget
    from .dock_widget import DockWidget
    from .dock_area_tab_bar import DockAreaTabBar
    from .dock_manager import DockManager


# ── Closest-edge helper ───────────────────────────────────────────────────

def find_closest_dock_area(global_center: QPoint,
                           dock_manager: 'DockManager') -> 'DockWidgetArea':
    """Return the outer DockWidgetArea whose edge is nearest to global_center."""
    target_widget = getattr(dock_manager, '_root', None) or dock_manager
    mgr_top_left = target_widget.mapToGlobal(QPoint(0, 0))
    mgr_rect = QRect(mgr_top_left, target_widget.size())

    edge_distances = {
        DockWidgetArea.left:   abs(global_center.x() - mgr_rect.left()),
        DockWidgetArea.right:  abs(global_center.x() - mgr_rect.right()),
        DockWidgetArea.top:    abs(global_center.y() - mgr_rect.top()),
        DockWidgetArea.bottom: abs(global_center.y() - mgr_rect.bottom()),
    }
    return min(edge_distances, key=edge_distances.get)


# ── Canonical icon registry ───────────────────────────────────────────────

_ICON_SPECS: Dict[str, tuple] = {
    "tab_list":     ("text-x-generic",  QStyle.SP_FileIcon),
    "pin":          ("pin",             QStyle.SP_TitleBarShadeButton),
    "pin_all":      ("pin",             QStyle.SP_TitleBarShadeButton),
    "unpin":        ("pin",             QStyle.SP_TitleBarUnshadeButton),
    "float":        ("window-new",      QStyle.SP_TitleBarNormalButton),
    "dock":         ("window-restore",  QStyle.SP_TitleBarNormalButton),
    "close":        ("window-close",    QStyle.SP_TitleBarCloseButton),
    "close_others": ("window-close",    QStyle.SP_TitleBarCloseButton),
    "close_tab":    ("tab-close",       QStyle.SP_TitleBarCloseButton),
    "tabs_menu":    ("view-list",       QStyle.SP_TitleBarUnshadeButton),
    "maximize":     ("window-maximize", QStyle.SP_TitleBarMaxButton),
    "restore":      ("window-restore",  QStyle.SP_TitleBarNormalButton),
    "minimize":     ("window-restore",  QStyle.SP_TitleBarNormalButton),
}


def dock_icon(key: str, category: DockStyleCategory = DockStyleCategory.TITLE_BAR) -> QIcon:
    """Return the canonical icon for key, tinted for Normal and Disabled states."""
    sm = get_dock_style_manager()
    provider = get_icon_provider()
    
    icon_dim = sm.get(category, "button_icon_size", 14)
    size = QSize(icon_dim, icon_dim)
    
    normal_icon = provider.get(key, category, active=False, disabled=False, size=icon_dim)
    
    if not normal_icon.isNull():
        disabled_icon = provider.get(key, category, active=False, disabled=True, size=icon_dim)
        
        icon = QIcon()
        normal_pixmap = normal_icon.pixmap(size)
        disabled_pixmap = disabled_icon.pixmap(size) if not disabled_icon.isNull() else normal_pixmap
        
        icon.addPixmap(normal_pixmap, QIcon.Normal, QIcon.Off)
        icon.addPixmap(normal_pixmap, QIcon.Normal, QIcon.On)
        icon.addPixmap(disabled_pixmap, QIcon.Disabled, QIcon.Off)
        icon.addPixmap(disabled_pixmap, QIcon.Disabled, QIcon.On)
        return icon

    spec = _ICON_SPECS.get(key)
    if spec is None:
        return QIcon()
        
    theme_name, fallback = spec
    if QIcon.hasThemeIcon(theme_name):
        return QIcon.fromTheme(theme_name)
    
    style = QApplication.style()
    if not style:
        return QIcon()

    std_icon = style.standardIcon(fallback)
    
    def to_color(c):
        if isinstance(c, QColor): return c
        if isinstance(c, str): return QColor(c)
        if isinstance(c, (list, tuple)) and len(c) >= 3: return QColor(*c[:3])
        return QColor(150, 150, 150)

    normal_color = to_color(sm.get(category, "button_color", [150, 150, 150]))
    disabled_color = to_color(sm.get(DockStyleCategory.CORE, "disabled_text_color", [110, 110, 110]))
    
    def create_tinted_pixmap(color):
        pixmap = std_icon.pixmap(size)
        painter = QPainter(pixmap)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), color)
        painter.end()
        return pixmap

    icon = QIcon()
    icon.addPixmap(create_tinted_pixmap(normal_color), QIcon.Normal, QIcon.Off)
    icon.addPixmap(create_tinted_pixmap(normal_color), QIcon.Normal, QIcon.On)
    icon.addPixmap(create_tinted_pixmap(disabled_color), QIcon.Disabled, QIcon.Off)
    icon.addPixmap(create_tinted_pixmap(disabled_color), QIcon.Disabled, QIcon.On)
    
    return icon


class MenuSection(Flag):
    """Bit-flags controlling which sections appear in the unified dock menu."""
    NONE         = 0
    TAB_LIST     = auto()   # Checkable list of tabs with active marker
    PIN          = auto()   # Pin to sidebar actions
    UNPIN        = auto()   # Unpin from sidebar actions
    DETACH       = auto()   # Float or Dock (reattach)
    MAXIMIZE     = auto()   # Maximize / Restore dock area
    CLOSE        = auto()   # Close (area or individual tab)
    CLOSE_OTHERS = auto()   # Close Other Areas / Close Other Tabs

    # Convenient presets
    TITLE_BAR = TAB_LIST | PIN | MAXIMIZE | DETACH | CLOSE | CLOSE_OTHERS
    TAB       = PIN | MAXIMIZE | DETACH | CLOSE | CLOSE_OTHERS
    SIDEBAR_TAB = UNPIN | DETACH | CLOSE


@dataclass
class MenuContext:
    """Captured state needed to build a context menu statelessly."""
    widget_type: str
    sections: MenuSection
    category: DockStyleCategory = DockStyleCategory.TITLE_BAR
    widget: Optional['DockWidget'] = None
    area: Optional['DockAreaWidget'] = None
    tab_bar: Optional['DockAreaTabBar'] = None
    count: int = 1
    is_closable: bool = False
    is_floatable: bool = False
    is_pinnable: bool = False
    is_pinned: bool = False
    is_floating: bool = False
    has_sidebars: bool = False
    show_close_others: bool = True
    icon_overrides: Dict[str, QIcon] = field(default_factory=dict)
    label_overrides: Dict[str, str] = field(default_factory=dict)


class MenuActionTarget(Protocol):
    """Protocol for widgets that receive dispatched context menu actions."""
    def menu_target_widget(self) -> Optional['DockWidget']: ...
    def menu_close_target(self) -> None: ...
    def menu_float_target(self) -> None: ...
    def menu_dock_target(self) -> None: ...
    def menu_pin_target(self) -> None: ...
    def menu_unpin_target(self) -> None: ...
    def menu_pin_all_target(self) -> None: ...
    def menu_close_others_target(self) -> None: ...
    def menu_maximize_target(self) -> None: ...
    def menu_switch_tab_target(self, index: int) -> None: ...


# ── Stateless Menu Builder ────────────────────────────────────────────────

def build_dock_context_menu(context: MenuContext, menu: QMenu) -> None:
    """Populate menu statelessly according to context."""
    sections = context.sections
    area = context.area
    is_floating = context.is_floating
    count = context.count
    is_closable = context.is_closable
    is_floatable = context.is_floatable
    is_pinnable = context.is_pinnable
    is_pinned = context.is_pinned
    tab_bar = context.tab_bar

    icons = {key: dock_icon(key, context.category) for key in _ICON_SPECS}
    icons.update(context.icon_overrides)

    section_names = [s.name for s in MenuSection if s in sections]
    trace("menu.build", widget_type=context.widget_type, sections=section_names, count=count, is_floating=is_floating, is_pinned=is_pinned)

    _pending_sep = False
    def _sep():
        nonlocal _pending_sep
        if _pending_sep:
            menu.addSeparator()
        _pending_sep = False

    def _icon(key: str) -> QIcon:
        return icons.get(key, QIcon())

    def _label(key: str, default_label: str) -> str:
        return context.label_overrides.get(key, default_label)

    # ── Tab list (only entries when > 1 tabs) ─────────────────────
    if MenuSection.TAB_LIST in sections and tab_bar is not None and count > 1:
        current_index = tab_bar.current_index()
        for i in range(tab_bar.count()):
            if not tab_bar.is_tab_open(i):
                continue
            tab = tab_bar.tab(i)
            act = menu.addAction(_icon("tab_list"), tab.text())
            act.setToolTip(tab.toolTip())
            act.setCheckable(True)
            act.setChecked(i == current_index)
            act.setData(("switch_tab", i))
        _pending_sep = True

    # ── Sidebar pin / unpin ───────────────────────────────────────
    if MenuSection.PIN in sections or MenuSection.UNPIN in sections:
        _sep()
        if is_pinned or MenuSection.UNPIN in sections:
            if count == 1 and not is_pinnable:
                pass
            else:
                act = menu.addAction(_icon("unpin"), _label("unpin", "Unpin from Sidebar"))
                act.setToolTip("Return this widget to the main dock layout")
                act.setEnabled(is_pinnable)
                act.setData(("unpin",))
        elif context.has_sidebars and MenuSection.PIN in sections:
            if count == 1 and not is_pinnable:
                pass
            else:
                act = menu.addAction(_icon("pin"), _label("pin", "Pin to Sidebar"))
                act.setToolTip("Pin the active tab to the nearest sidebar")
                act.setEnabled(is_pinnable)
                act.setData(("pin",))

                if area and len(area.opened_dock_widgets()) > 1:
                    act = menu.addAction(_icon("pin_all"), _label("pin_all", "Pin All to Sidebar"))
                    act.setToolTip("Pin every tab in this group to the nearest sidebar")
                    all_pinnable = all(
                        DockWidgetFeature.pinnable in w.features()
                        for w in area.opened_dock_widgets()
                    )
                    act.setEnabled(all_pinnable)
                    act.setData(("pin_all",))
        _pending_sep = True

    # ── Float / Dock ──────────────────────────────────────────────
    if MenuSection.DETACH in sections:
        if count == 1 and not is_floatable:
            pass
        else:
            _sep()
            if is_floating:
                act = menu.addAction(_icon("dock"), _label("dock", "Dock Group" if count > 1 else "Dock"))
                act.setData(("dock",))
            else:
                act = menu.addAction(_icon("float"), _label("float", "Float Group" if count > 1 else "Float"))
                act.setEnabled(is_floatable)
                act.setData(("float",))
            _pending_sep = True

    # ── Maximize / Restore ────────────────────────────────────────
    if MenuSection.MAXIMIZE in sections:
        from .enums import DockFlags as _DockFlags
        mgr = area.dock_manager() if area else None
        if mgr and _DockFlags.dock_area_has_maximize_button in mgr.config_flags:
            _sep()
            if area and area.is_maximized():
                act = menu.addAction(_icon("restore"), _label("restore", "Restore"))
                act.setData(("maximize",))
            else:
                act = menu.addAction(_icon("maximize"), _label("maximize", "Maximize"))
                act.setData(("maximize",))
            _pending_sep = True

    # ── Close + Close Others ──────────────────────────────────────
    if MenuSection.CLOSE in sections:
        if count == 1 and not is_closable:
            pass
        else:
            _sep()
            act = menu.addAction(_icon("close"), _label("close", "Close Group" if count > 1 else "Close"))
            act.setEnabled(is_closable)
            act.setData(("close",))

    if MenuSection.CLOSE_OTHERS in sections and context.show_close_others:
        act = menu.addAction(_icon("close_others"), _label("close_others", "Close Other Groups" if count > 1 else "Close Others"))
        act.setData(("close_others",))


# ── Stateless Action Dispatcher ───────────────────────────────────────────

def dispatch_dock_context_menu(action: QAction, target: Any, fallback_widget_type: str = "") -> None:
    """Route a triggered menu action to the target widget implementing MenuActionTarget."""
    data = action.data()
    if not data:
        return
    if isinstance(data, (tuple, list)):
        key = data[0]
        arg = data[1] if len(data) > 1 else None
    elif isinstance(data, str):
        key = data
        arg = None
    else:
        key = str(data)
        arg = None

    widget = target.menu_target_widget() if hasattr(target, 'menu_target_widget') else None
    widget_name_or_type = widget.objectName() if widget else (fallback_widget_type or target.__class__.__name__)
    trace("menu.action", widget=widget_name_or_type, action=key)
    
    dispatch = {
        "switch_tab":   lambda: target.menu_switch_tab_target(arg) if hasattr(target, 'menu_switch_tab_target') else None,
        "pin":          lambda: target.menu_pin_target() if hasattr(target, 'menu_pin_target') else None,
        "unpin":        lambda: target.menu_unpin_target() if hasattr(target, 'menu_unpin_target') else None,
        "pin_all":      lambda: target.menu_pin_all_target() if hasattr(target, 'menu_pin_all_target') else None,
        "float":        lambda: target.menu_float_target() if hasattr(target, 'menu_float_target') else None,
        "dock":         lambda: target.menu_dock_target() if hasattr(target, 'menu_dock_target') else None,
        "maximize":     lambda: target.menu_maximize_target() if hasattr(target, 'menu_maximize_target') else None,
        "close":        lambda: target.menu_close_target() if hasattr(target, 'menu_close_target') else None,
        "close_others": lambda: target.menu_close_others_target() if hasattr(target, 'menu_close_others_target') else None,
    }
    handler = dispatch.get(key)
    if handler:
        handler()


# ── Standard Action Helpers ───────────────────────────────────────────────

def menu_default_pin(widget: Optional['DockWidget'], area: Optional['DockAreaWidget']) -> None:
    if not widget:
        return
    if area:
        mgr = area.dock_manager()
        if mgr and hasattr(mgr, 'sidebar_manager'):
            if DockFlags.pinnable_tabs not in mgr.config_flags:
                return
            mgr.sidebar_manager.pin_to_closest_sidebar(widget)


def menu_default_unpin(widget: Optional['DockWidget'], area: Optional['DockAreaWidget'], manager: Optional['DockManager'] = None) -> None:
    if widget:
        mgr = (area.dock_manager() if area else None) or manager
        if mgr and hasattr(mgr, 'sidebar_manager'):
            mgr.sidebar_manager.unpin_widget(widget)


def menu_default_pin_all(area: Optional['DockAreaWidget']) -> None:
    if not area:
        return
    mgr = area.dock_manager()
    if not mgr or not hasattr(mgr, 'sidebar_manager'):
        return
    if DockFlags.pinnable_tabs not in mgr.config_flags:
        return
    for widget in list(area.opened_dock_widgets()):
        mgr.sidebar_manager.pin_to_closest_sidebar(widget)


def menu_default_reattach(area: Optional['DockAreaWidget']) -> None:
    """Return all docks from the floating window to the nearest edge."""
    if not area:
        return
    container = area.dock_container()
    if not container or not container.is_floating():
        return
    floating = container.floating_widget()
    if floating is None:
        return

    mgr = area.dock_manager()
    floating_center = floating.mapToGlobal(
        QPoint(floating.width() // 2, floating.height() // 2)
    )
    try:
        closest = find_closest_dock_area(floating_center, mgr)
    except Exception:
        closest = DockWidgetArea.right

    groups = [
        list(a.opened_dock_widgets())
        for a in container.opened_dock_areas()
        if a.opened_dock_widgets()
    ]
    if not groups:
        return

    new_area = mgr.add_dock_widget(closest, groups[0][0])
    for widget in groups[0][1:]:
        mgr.add_dock_widget(DockWidgetArea.center, widget, new_area)
    for group in groups[1:]:
        group_area = mgr.add_dock_widget(closest, group[0])
        for widget in group[1:]:
            mgr.add_dock_widget(DockWidgetArea.center, widget, group_area)

    floating.hide()
