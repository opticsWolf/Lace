# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2019 Ken Lauer
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0

This file is part of Lace, adapted from qtpydocking.
Original code Copyright (c) 2019 Ken Lauer (BSD-3-Clause).
Modifications Copyright (c) 2026 opticsWolf (Apache-2.0).

dock_context_menu.py
--------------------
Unified context/popup menu mixin for dock title bars and tabs.

Usage
-----
1. Inherit DockMenuMixin alongside the Qt base class.
2. Set class-level _menu_sections to control which sections appear.
3. Implement _menu_dock_area() to return the relevant DockAreaWidget.
4. Override _menu_* hooks for consumer-specific behaviour.
5. Override _menu_icons() to replace any icon; unmentioned keys keep their
   default. Return an empty dict to suppress all icons.

Canonical action names
----------------------
    "tab_list"     – checkable tab entries (only shown when ≥ 2 tabs)
    "pin"          – Pin (active tab) to Sidebar
    "pin_all"      – Pin All to Sidebar
    "unpin"        – Unpin from Sidebar (reattach into the dock layout)
    "float"        – Float (detach into a floating window)
    "dock"         – Dock  (reattach a floating window)
    "close"        – Close
    "close_others" – Close Others
"""
from __future__ import annotations

from enum import Flag, auto
from typing import TYPE_CHECKING, Dict, Optional

from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QStyle

from .enums import DockWidgetArea, DockWidgetFeature

if TYPE_CHECKING:
    from .dock_area_widget import DockAreaWidget
    from .dock_widget import DockWidget
    from .dock_area_tab_bar import DockAreaTabBar
    from .dock_manager import DockManager


# ── Closest-edge helper ───────────────────────────────────────────────────

def find_closest_dock_area(global_center: QPoint,
                           dock_manager: 'DockManager') -> 'DockWidgetArea':
    """Return the outer ``DockWidgetArea`` whose edge is nearest to *global_center*.

    Measures the absolute pixel distance from *global_center* to each of
    the four edges of *dock_manager* (in global screen coordinates) and
    returns the one with the smallest distance.  The result is always one
    of ``left``, ``right``, ``top``, or ``bottom``.

    This is the single shared implementation used by:
    * ``_menu_reattach``   – dock a floating window at the nearest edge
    * ``SidebarManager.unpin_widget``   – dock from sidebar at the nearest edge
    * ``SidebarManager.pin_to_closest_sidebar`` – pin to the nearest sidebar
    """
    mgr_top_left = dock_manager.mapToGlobal(QPoint(0, 0))
    mgr_rect = QRect(mgr_top_left, dock_manager.size())

    edge_distances = {
        DockWidgetArea.left:   abs(global_center.x() - mgr_rect.left()),
        DockWidgetArea.right:  abs(global_center.x() - mgr_rect.right()),
        DockWidgetArea.top:    abs(global_center.y() - mgr_rect.top()),
        DockWidgetArea.bottom: abs(global_center.y() - mgr_rect.bottom()),
    }
    return min(edge_distances, key=edge_distances.get)


# ── Canonical icon registry ───────────────────────────────────────────────

# Maps each action key to (XDG-theme-name, QStyle-fallback).
# Every component (title bar, tab, sidebar overlay) should resolve icons
# through this table so they always match.
_ICON_SPECS: Dict[str, tuple] = {
    "tab_list":     ("text-x-generic",  QStyle.SP_FileIcon),
    "pin":          ("pin",             QStyle.SP_TitleBarShadeButton),
    "pin_all":      ("pin",             QStyle.SP_TitleBarShadeButton),
    "unpin":        ("pin",             QStyle.SP_TitleBarUnshadeButton),
    "float":        ("window-new",      QStyle.SP_TitleBarNormalButton),
    "dock":         ("window-restore",  QStyle.SP_TitleBarNormalButton),
    "close":        ("window-close",    QStyle.SP_TitleBarCloseButton),
    "close_others": ("window-close",    QStyle.SP_TitleBarCloseButton),
    "tabs_menu":    ("view-list",       QStyle.SP_TitleBarUnshadeButton),
}


def dock_icon(key: str) -> QIcon:
    """Return the canonical icon for *key*.

    Looks up the XDG theme icon first (native on Linux/macOS); falls back
    to the QStyle standard pixmap on Windows or when the theme is missing.

    This is the **single source of truth** for every icon used in dock
    title bars, tab context menus, and sidebar overlays.
    """
    spec = _ICON_SPECS.get(key)
    if spec is None:
        return QIcon()
    theme_name, fallback = spec
    if QIcon.hasThemeIcon(theme_name):
        return QIcon.fromTheme(theme_name)
    style = QApplication.style()
    return style.standardIcon(fallback) if style else QIcon()


class MenuSection(Flag):
    """Bit-flags controlling which sections appear in the unified dock menu."""
    NONE         = 0
    TAB_LIST     = auto()   # Checkable list of tabs with active marker
    PIN          = auto()   # Pin to sidebar actions
    DETACH       = auto()   # Float or Dock (reattach)
    CLOSE        = auto()   # Close (area or individual tab)
    CLOSE_OTHERS = auto()   # Close Other Areas / Close Other Tabs

    # Convenient presets
    TITLE_BAR = TAB_LIST | PIN | DETACH | CLOSE | CLOSE_OTHERS
    TAB       = PIN | DETACH | CLOSE | CLOSE_OTHERS


class DockMenuMixin:
    """
    Mixin providing a unified context/popup menu for dock title bars and tabs.

    Subclasses must implement:
        _menu_dock_area() -> Optional[DockAreaWidget]

    Override these class attributes to customise labels:
        _menu_sections           (default: MenuSection.TITLE_BAR)

    Override _menu_icons() to replace individual icons.  The method must
    return a dict mapping action keys to QIcon instances.  Any key not
    present in the returned dict falls back to the canonical default.
    Valid keys: see ``_ICON_SPECS``.
    """

    _menu_sections: MenuSection = MenuSection.TITLE_BAR

    # ── Icon provider ─────────────────────────────────────────────────────

    def _menu_icons(self) -> Dict[str, QIcon]:
        """Return a dict of action-key → QIcon overrides.

        Only keys present in the returned dict are changed; every other
        action keeps its canonical default icon.  Return {} to keep all
        defaults untouched.
        """
        return {}

    @staticmethod
    def _get_default_icons() -> Dict[str, QIcon]:
        """Built-in default icons from the canonical registry."""
        return {key: dock_icon(key) for key in _ICON_SPECS}

    def _resolved_icons(self) -> Dict[str, QIcon]:
        """Merge defaults with any consumer overrides (overrides win)."""
        icons = self._get_default_icons()
        icons.update(self._menu_icons())
        return icons

    # ── Required interface ────────────────────────────────────────────────

    def _menu_dock_area(self) -> Optional['DockAreaWidget']:
        raise NotImplementedError

    def _menu_dock_widget(self) -> Optional['DockWidget']:
        """Dock widget this menu acts on. Defaults to the active tab."""
        area = self._menu_dock_area()
        return area.current_dock_widget() if area else None

    # ── State queries (override as needed) ────────────────────────────────

    def _menu_is_floating(self) -> bool:
        area = self._menu_dock_area()
        if not area:
            return False
        container = area.dock_container()
        return container is not None and container.is_floating()

    def _menu_has_sidebars(self) -> bool:
        try:
            return self._menu_dock_area().dock_manager().sidebar_manager.has_sidebars
        except (AttributeError, RuntimeError):
            return False

    def _menu_is_closable(self) -> bool:
        """Whether the *active widget* can be closed."""
        widget = self._menu_dock_widget()
        return bool(widget and (DockWidgetFeature.closable in widget.features()))

    def _menu_is_area_closable(self) -> bool:
        """Whether the whole area can be closed (all tabs closable)."""
        area = self._menu_dock_area()
        return bool(area and area.closable)

    def _menu_is_floatable(self) -> bool:
        """Whether the active widget / area can float."""
        area = self._menu_dock_area()
        return bool(area and area.floatable)

    def _menu_is_pinnable(self) -> bool:
        """Check if the active widget is allowed to be pinned."""
        widget = self._menu_dock_widget()
        return bool(widget and (DockWidgetFeature.pinnable in widget.features()))

    def _menu_show_close_others(self) -> bool:
        """Whether the Close Others action should appear."""
        return not self._menu_is_floating()

    def _menu_tab_count(self) -> int:
        """Returns the number of open tabs in the current area/sidebar."""
        area = self._menu_dock_area()
        return area.open_dock_widgets_count() if area else 1

    # ── Label helpers (context-aware: single vs group) ────────────────────

    def _label_close(self, count: int) -> str:
        return "Close Group" if count > 1 else "Close"

    def _label_close_others(self, count: int) -> str:
        return "Close Other Groups" if count > 1 else "Close Others"

    def _label_float(self, count: int) -> str:
        return "Float Group" if count > 1 else "Float"

    def _label_dock(self, count: int) -> str:
        return "Dock Group" if count > 1 else "Dock"

    def _label_pin(self, count: int) -> str:
        return "Pin to Sidebar"

    def _label_pin_all(self) -> str:
        return "Pin All to Sidebar"

    # ── Menu builder ──────────────────────────────────────────────────────

    def build_dock_menu(self, menu: QMenu,
                        tab_bar: Optional['DockAreaTabBar'] = None) -> None:
        """Populate *menu* in-place according to _menu_sections and state."""
        sections     = self._menu_sections
        area         = self._menu_dock_area()
        is_floating  = self._menu_is_floating()
        icons        = self._resolved_icons()
        _pending_sep = False

        count        = self._menu_tab_count()
        is_closable  = self._menu_is_closable()
        is_floatable = self._menu_is_floatable()
        is_pinnable  = self._menu_is_pinnable()

        def _sep():
            nonlocal _pending_sep
            if _pending_sep:
                menu.addSeparator()
            _pending_sep = False

        def _icon(key: str) -> QIcon:
            return icons.get(key, QIcon())

        # ── Tab list (only entries when ≥ 2 tabs) ────────────────────
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

        # ── Sidebar pin ───────────────────────────────────────────────
        if MenuSection.PIN in sections and self._menu_has_sidebars():
            if count == 1 and not is_pinnable:
                pass  # Hide completely for single unpinnable widget
            else:
                _sep()
                act = menu.addAction(_icon("pin"), self._label_pin(count))
                act.setToolTip("Pin the active tab to the nearest sidebar")
                act.setEnabled(is_pinnable)
                act.setData(("pin",))

                if area and len(area.opened_dock_widgets()) > 1:
                    act = menu.addAction(_icon("pin_all"), self._label_pin_all())
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
                pass  # Hide completely
            else:
                _sep()
                if is_floating:
                    act = menu.addAction(_icon("dock"), self._label_dock(count))
                    act.setData(("dock",))
                else:
                    act = menu.addAction(_icon("float"), self._label_float(count))
                    act.setEnabled(is_floatable)
                    act.setData(("float",))
                _pending_sep = True

        # ── Close + Close Others ──────────────────────────────────────
        if MenuSection.CLOSE in sections:
            if count == 1 and not is_closable:
                pass  # Hide completely
            else:
                _sep()
                act = menu.addAction(_icon("close"), self._label_close(count))
                act.setEnabled(is_closable)
                act.setData(("close",))

        if MenuSection.CLOSE_OTHERS in sections and self._menu_show_close_others():
            act = menu.addAction(_icon("close_others"), self._label_close_others(count))
            act.setData(("close_others",))

    # ── Dispatcher ────────────────────────────────────────────────────────

    def dispatch_dock_action(self, action: QAction) -> None:
        """Route a triggered menu action to the appropriate handler."""
        data = action.data()
        if not data:
            return
        key = data[0]
        dispatch = {
            "switch_tab":  lambda: self._menu_on_switch_tab(data[1]),
            "pin":         self._menu_pin_current,
            "pin_all":     self._menu_pin_all,
            "float":       self._menu_detach,
            "dock":        self._menu_reattach,
            "close":       self._menu_close,
            "close_others": self._menu_close_others,
        }
        handler = dispatch.get(key)
        if handler:
            handler()

    # ── Default action implementations ────────────────────────────────────

    def _menu_on_switch_tab(self, index: int) -> None:
        pass  # Overridden by title bar

    def _menu_pin_current(self) -> None:
        widget = self._menu_dock_widget()
        if not widget:
            return
        area = self._menu_dock_area()
        if area:
            mgr = area.dock_manager()
            if mgr and hasattr(mgr, 'sidebar_manager'):
                mgr.sidebar_manager.pin_to_closest_sidebar(widget)

    def _menu_pin_all(self) -> None:
        area = self._menu_dock_area()
        if not area:
            return
        mgr = area.dock_manager()
        if not mgr or not hasattr(mgr, 'sidebar_manager'):
            return
        for widget in list(area.opened_dock_widgets()):
            mgr.sidebar_manager.pin_to_closest_sidebar(widget)

    def _menu_detach(self) -> None:
        pass  # Overridden by each consumer

    def _menu_reattach(self) -> None:
        """Return all docks from the floating window to the nearest edge."""
        area = self._menu_dock_area()
        if not area:
            return
        container = area.dock_container()
        if not container or not container.is_floating():
            return
        floating = container.floating_widget()
        if floating is None:
            return

        mgr = area.dock_manager()

        # Determine the closest edge of the main dock manager.
        floating_center = floating.mapToGlobal(
            QPoint(floating.width() // 2, floating.height() // 2)
        )
        try:
            closest = find_closest_dock_area(floating_center, mgr)
        except Exception:
            closest = DockWidgetArea.right  # safe fallback

        # Snapshot before mutation — add_dock_widget modifies the container live.
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

    def _menu_close(self) -> None:
        pass  # Overridden by each consumer

    def _menu_close_others(self) -> None:
        area = self._menu_dock_area()
        if area:
            area.close_other_areas()
