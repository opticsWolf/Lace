# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0

dock_colors — Canonical colour conversion for the docking system
================================================================
Note: Color conversion utilities have been consolidated into dock_theme.py.
This module re-exports them for backward compatibility.
"""

from .dock_theme import (
    to_qcolor, qcolor_to_list, is_color_list,
    deep_to_qcolor, deep_to_serializable
)

__all__ = [
    "to_qcolor", "qcolor_to_list", "is_color_list",
    "deep_to_qcolor", "deep_to_serializable"
]
