# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0

Note: Sidebar state persistence classes have been consolidated into layout_serializer.py.
This module re-exports them for backward compatibility.
"""

from .layout_serializer import SidebarState, SidebarStateManager

__all__ = ["SidebarState", "SidebarStateManager"]