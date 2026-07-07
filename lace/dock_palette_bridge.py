# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0

dock_palette_bridge — Single source of truth for dock widget palette construction
=================================================================================
Note: Palette bridge utilities have been consolidated into dock_theme.py.
This module re-exports them for backward compatibility.
"""

from .dock_theme import (
    DockThemeColors, resolve_dock_colors, build_dock_palette
)

__all__ = [
    "DockThemeColors", "resolve_dock_colors", "build_dock_palette"
]