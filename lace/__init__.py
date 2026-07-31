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

__version__ = "0.2.5"

# ---------------------------------------------------------------------------
# Core Classes
# ---------------------------------------------------------------------------
from .dock_area_widget import DockAreaWidget
from .dock_container_widget import DockContainerWidget, DropController
from .dock_manager import DockManager
from .dock_widget import DockWidget
from .dock_widget_tab import DockWidgetTab
from .dock_splitter import DockSplitter, DockSplitterHandle
from .floating_dock_container import FloatingDockContainer
from .dock_icon_provider import DockIconProvider, get_icon_provider
from .dock_theme import (
    DockStyleCategory,
    ThemeSpec,
    build_theme,
    deep_to_qcolor,
    deep_to_serializable,
)
from .dock_style_manager import (
    DockStyleManager,
    apply_dock_theme,
    get_dock_style_manager,
)
from .dock_theme_bridge import DockThemeBridge
from .theme_manager import ThemeManager
from .sidebar_manager import SidebarManager
from .sidebar_container import SideBarContainer
from .sidebar_tab import TabBadgePosition, VerticalTabButton
from .sidebar_tab_bar import SideTabBar
from .sidebar_title_bar import SideBarTitleBar
from .dock_area_tab_bar import DockAreaTabBar
from .dock_area_title_bar import DockAreaTitleBar
from .dock_chrome import DragDetector, ChromeToolButton, ChromeFrame
from .dock_overlay import DockOverlay, DockOverlayCross
from .dock_context_menu import DockMenuMixin, MenuSection, MenuContext, MenuActionTarget
from .dock_signals import DockSignals
from .layout_serializer import (
    LayoutError,
    LayoutIOError,
    InvalidFormatError,
    RestoreFailureError,
    LayoutPersistenceManager,
    LayoutSerializer,
    LayoutStateBuilder,
)
from .dock_paint import ChromeTokens
from .eliding_label import ElidingLabel

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
from .enums import (
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
)

# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------
from .util import (
    emit_top_level_event_for_widget,
    start_drag_distance,
    create_transparent_pixmap,
    hide_empty_parent_splitters,
    find_parent,
    find_child,
    find_children,
    dump_layout,
)

# ---------------------------------------------------------------------------
# PEP 562 Lazy Loading (fallback for non-standard attribute access)
# ---------------------------------------------------------------------------

import importlib
import logging
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_MODEL_REGISTRY: Dict[str, Any] = {}
_IS_INITIALIZED: bool = False
_DISCOVERY_LOCK = Lock()

# Modules to skip during discovery (already imported above)
_SKIP_MODULES = frozenset(
    {
        "__init__",
        "_trace",
        "dock_colors",
        "dock_signals",
        "dock_paint",
        "dock_context_menu",
        "dock_styled",
        "util",
        "enums",
        "eliding_label",
        "dock_area_layout",
        "dock_container_state",
        "dock_theme_bridge",
        "dock_style_manager",
        "dock_theme",
        "theme_manager",
        "layout_serializer",
        "dock_icon_provider",
    }
)


def _discover_models() -> None:
    """Discover and register public callables defined in package modules.

    Uses importlib.resources.files() for Python 3.9+ compatibility.
    Discovery is idempotent and thread-safe.
    """
    global _IS_INITIALIZED

    if _IS_INITIALIZED:
        return

    with _DISCOVERY_LOCK:
        if _IS_INITIALIZED:
            return

        package_path = [str(Path(__file__).parent)]

        # Use importlib.resources for reliable module discovery
        try:
            from importlib.resources import files as resources_files

            package_dir = resources_files(__name__)
            discovered = sorted(
                [
                    (None, mod.stem, False)
                    for mod in package_dir.iterdir()
                    if mod.name.endswith(".py")
                    and not mod.name.startswith("_")
                    and mod.stem not in _SKIP_MODULES
                ],
                key=lambda t: t[1],
            )
        except Exception:
            # Fallback: direct filesystem scan
            discovered = []
            for mod in Path(package_path[0]).glob("*.py"):
                mod_name = mod.stem
                if mod_name.startswith("_") or mod_name in _SKIP_MODULES:
                    continue
                discovered.append((None, mod_name, False))

        for finder, mod_name, is_pkg in discovered:
            if is_pkg:
                continue

            try:
                module = importlib.import_module(f".{mod_name}", package=__name__)
            except ImportError as exc:
                logger.warning("Failed to import '%s': %s", mod_name, exc)
                continue

            for name, obj in vars(module).items():
                if (
                    callable(obj)
                    and not name.startswith("_")
                    and getattr(obj, "__module__", None) == module.__name__
                ):
                    _MODEL_REGISTRY[name] = obj

        _IS_INITIALIZED = True


# ---------------------------------------------------------------------------
# Lazy Loading (PEP 562)
# ---------------------------------------------------------------------------

def __getattr__(name: str) -> Any:
    """Lazy attribute access hook.

    Trigger discovery on first attribute lookup,
    then resolve the symbol from the registry.
    """
    if not _IS_INITIALIZED:
        _discover_models()

    if name in _MODEL_REGISTRY:
        return _MODEL_REGISTRY[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> List[str]:
    """Extended dir() to include lazily-discovered names."""
    if not _IS_INITIALIZED:
        _discover_models()

    base = list(globals().keys())
    dynamic = list(_MODEL_REGISTRY.keys())
    return sorted(set(base + dynamic))


def get_model_registry() -> Dict[str, Any]:
    """Return the dictionary of discovered model callables.

    Returns:
        Dict[str, Any]: Mapping of public model names to model objects.
    """
    if not _IS_INITIALIZED:
        _discover_models()
    return _MODEL_REGISTRY
