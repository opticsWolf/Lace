# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0

Predefined themes for the Advanced Docking System.
Each theme provides a complete color palette including accent colors,
active-edge indicators, and overlay panel styling.
"""

from typing import Dict, Any
from .dock_theme import DockStyleCategory, _build_theme

# =============================================================================
# THEME DEFINITIONS - Only 3 colors each!
# =============================================================================

DOCK_THEMES: Dict[str, Dict[DockStyleCategory, Dict[str, Any]]] = {

    # Default uses BASE_DOCK_DEFAULTS from dock_theme.py
    "default": {},

    # -------------------------------------------------------------------------
    # DARK (Recessed headers, clean contrast)
    # -------------------------------------------------------------------------
    "dark": _build_theme(
        base       = [20, 23, 30, 255],
        accent     = [45, 85, 170, 255],    # Boosted saturation
        text       = [200, 205, 215, 255],
        title_mode = "darker",              # Deep, integrated title bars
        hover_mode   = "lighter",             # Tabs pop from the panel
    ),

    # -------------------------------------------------------------------------
    # LIGHT (High clarity, professional light gray)
    # -------------------------------------------------------------------------
    "light": _build_theme(
        base       = [225, 228, 232, 255], # Slightly deeper base for better highlights
        accent     = [54, 81, 217, 255],
        text       = [45, 50, 60, 255],
        is_light   = False,
        title_mode = "darker",             # Title bars feel like part of the frame
        hover_mode   = "darker",              # Recessed inactive tabs
    ),

    # -------------------------------------------------------------------------
    # MIDNIGHT (OLED-friendly, ultra-high contrast)
    # -------------------------------------------------------------------------
    "midnight": _build_theme(
        base       = [8, 10, 15, 255],     # Darker base
        accent     = [60, 100, 255, 255],   # Electric blue
        text       = [210, 215, 230, 255],
        title_mode = "darker",
        hover_mode   = "darker",              # Everything recessed except active content
    ),

    # -------------------------------------------------------------------------
    # WARM (Organic, cozy tones)
    # -------------------------------------------------------------------------
    "warm": _build_theme(
        base       = [38, 32, 30, 255],
        accent     = [200, 110, 60, 255],   # Richer orange
        text       = [235, 225, 210, 255],
        title_mode = "lighter",             # "Elevated" headers
        hover_mode   = "lighter",
    ),

    # -------------------------------------------------------------------------
    # NORDIC (Frosty and crisp)
    # -------------------------------------------------------------------------
    "nordic": _build_theme(
        base       = [40, 46, 58, 255],     # Deeper slate for better contrast
        accent     = [136, 192, 208, 255],
        text       = [236, 239, 244, 255],
        title_mode = "darker",
        hover_mode   = "lighter",
    ),

    # -------------------------------------------------------------------------
    # MONOKAI (Classic dev look, high pop)
    # -------------------------------------------------------------------------
    "monokai": _build_theme(
        base       = [28, 26, 29, 255],
        accent     = [255, 216, 102, 255],
        text       = [248, 248, 242, 255],
        title_mode = "darker",              # Intense focus on code/content area
        hover_mode   = "darker",
    ),

    # -------------------------------------------------------------------------
    # NEUTRAL (The "Silver" Workstation)
    # -------------------------------------------------------------------------
    "neutral": _build_theme(
        base       = [190, 193, 197, 255],  # Pushed light-gray
        accent     = [40, 110, 190, 255],
        text       = [30, 35, 45, 255],
        is_light   = False,
        title_mode = "darker",              # Strong structural separation
        hover_mode   = "lighter",
    ),
}