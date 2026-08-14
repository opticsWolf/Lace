# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.
#

"""Lace — Advanced PySide6 Docking System.

Public API is imported explicitly at the top level for discoverability
and IDE/mypy compatibility.
"""

__version__ = "0.5.63"

# ---------------------------------------------------------------------------
# Core Classes
# ---------------------------------------------------------------------------
from lace.dock_area_widget import DockAreaWidget
from lace.dock_container_widget import DockContainerWidget, DropController
from lace.dock_manager import DockManager
from lace.dock_widget import DockWidget
from lace.dock_widget_tab import DockWidgetTab
from lace.dock_splitter import DockSplitter, DockSplitterHandle
from lace.floating_behaviour import FloatingContainerBehaviour
from lace.floating_dock_container import FloatingDockContainer
from lace.dock_icon_provider import DockIconProvider, get_icon_provider
from lace.dock_theme import (
    DockStyleCategory,
    ThemeSpec,
    build_theme,
    build_tooltip_palette,
    deep_to_qcolor,
    deep_to_serializable,
)
from lace.dock_style_manager import (
    DockStyleManager,
    apply_dock_theme,
    get_dock_style_manager,
    theme_choices,
)
from lace.dock_theme_bridge import DockThemeBridge
from lace.dock_menu_bar import DockMenuBarStyler
from lace.theme_manager import ThemeManager
from lace.theme_models import ThemeJson, load_theme_json
from lace.sidebar_manager import SidebarManager
from lace.sidebar_container import SideBarContainer
from lace.sidebar_tab import TabBadgePosition, VerticalTabButton
from lace.sidebar_tab_bar import SideTabBar
from lace.sidebar_title_bar import SideBarTitleBar
from lace.dock_area_tab_bar import DockAreaTabBar
from lace.dock_area_title_bar import DockAreaTitleBar
from lace.dock_chrome import DragDetector, ChromeToolButton, ChromeFrame
from lace.dock_overlay import DockOverlay, DockOverlayCross
from lace.dock_context_menu import DockMenuMixin, MenuSection, MenuContext, MenuActionTarget
from lace.dock_signals import DockSignals
from lace.layout_serializer import (
    LayoutError,
    LayoutIOError,
    InvalidFormatError,
    RestoreFailureError,
    LayoutPersistenceManager,
    LayoutSerializer,
    LayoutStateBuilder,
)
from lace.dock_paint import ChromeTokens
from lace.eliding_label import ElidingLabel

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
from lace.enums import (
    DockInsertParam,
    DockWidgetArea,
    DockFlags,
    TitleBarButton,
    OverlayMode,
    InsertMode,
    DragState,
    InsertionOrder,
    DockWidgetFeature,
    WidgetState,
    ToggleViewActionMode,
    SideBarFocusBehavior,
    TitleBarMode,
)

# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------
from lace.util import (
    emit_top_level_event_for_widget,
    is_floating_dock_container,
    find_floating_dock_container,
    start_drag_distance,
    create_transparent_pixmap,
    hide_empty_parent_splitters,
    find_parent,
    find_child,
    find_children,
    dump_layout,
)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
# The imports above are the public API — there is no dynamic fallback.  The
# PEP 562 __getattr__ that used to live here imported every module in the
# package on the first missed attribute (so it was not lazy), registered every
# public callable it found (so lace.<any internal helper> resolved), and
# swallowed ImportError with a warning (so a broken module degraded silently).

__all__ = [
    "__version__",
    # Core
    "DockAreaWidget",
    "DockContainerWidget",
    "DropController",
    "DockManager",
    "DockWidget",
    "DockWidgetTab",
    "DockSplitter",
    "DockSplitterHandle",
    "FloatingDockContainer",
    "FloatingContainerBehaviour",
    "DockIconProvider",
    "get_icon_provider",
    "DockAreaTabBar",
    "DockAreaTitleBar",
    "DockOverlay",
    "DockOverlayCross",
    "DockSignals",
    "ElidingLabel",
    # Chrome & painting
    "DragDetector",
    "ChromeToolButton",
    "ChromeFrame",
    "ChromeTokens",
    # Theming
    "DockStyleCategory",
    "ThemeSpec",
    "build_theme",
    "build_tooltip_palette",
    "deep_to_qcolor",
    "deep_to_serializable",
    "DockStyleManager",
    "apply_dock_theme",
    "get_dock_style_manager",
    "theme_choices",
    "DockThemeBridge",
    "DockMenuBarStyler",
    "ThemeManager",
    "ThemeJson",
    "load_theme_json",
    # Sidebar
    "SidebarManager",
    "SideBarContainer",
    "TabBadgePosition",
    "VerticalTabButton",
    "SideTabBar",
    "SideBarTitleBar",
    # Context menus
    "DockMenuMixin",
    "MenuSection",
    "MenuContext",
    "MenuActionTarget",
    # Layout persistence
    "LayoutError",
    "LayoutIOError",
    "InvalidFormatError",
    "RestoreFailureError",
    "LayoutPersistenceManager",
    "LayoutSerializer",
    "LayoutStateBuilder",
    # Enums
    "DockInsertParam",
    "DockWidgetArea",
    "DockFlags",
    "TitleBarButton",
    "OverlayMode",
    "InsertMode",
    "DragState",
    "InsertionOrder",
    "DockWidgetFeature",
    "WidgetState",
    "ToggleViewActionMode",
    "SideBarFocusBehavior",
    "TitleBarMode",
    # Utilities
    "emit_top_level_event_for_widget",
    "is_floating_dock_container",
    "find_floating_dock_container",
    "start_drag_distance",
    "create_transparent_pixmap",
    "hide_empty_parent_splitters",
    "find_parent",
    "find_child",
    "find_children",
    "dump_layout",
]
