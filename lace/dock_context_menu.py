# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2019 Ken Lauer
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0

dock_context_menu.py
--------------------
Deprecated: context menu logic and helpers moved to dock_menu.py.
This file is maintained as a re-export shim for backwards compatibility.
"""
from __future__ import annotations

from .dock_menu import (
    MenuSection, dock_icon, find_closest_dock_area,
    MenuContext, MenuActionTarget, build_dock_context_menu,
    dispatch_dock_context_menu, menu_default_pin, menu_default_unpin,
    menu_default_pin_all, menu_default_reattach
)


class DockMenuMixin:
    """Deprecated legacy mixin; use stateless builder in dock_menu.py instead."""
    pass


__all__ = [
    "MenuSection", "dock_icon", "find_closest_dock_area", "MenuContext",
    "MenuActionTarget", "build_dock_context_menu", "dispatch_dock_context_menu",
    "DockMenuMixin", "menu_default_pin", "menu_default_unpin",
    "menu_default_pin_all", "menu_default_reattach"
]
