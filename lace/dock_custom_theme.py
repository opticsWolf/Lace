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
from .dock_theme import DockStyleCategory, ThemeSpec, build_theme

# =============================================================================
# THEME SPECIFICATIONS (Declarative 3- to 5-color presets)
# =============================================================================

THEME_SPECS: Dict[str, ThemeSpec] = {
    # -------------------------------------------------------------------------
    # DARK (Recessed headers, clean contrast)
    # -------------------------------------------------------------------------
    "dark": ThemeSpec(
        base       = [20, 23, 30, 255],
        accent     = [45, 85, 170, 255],    # Boosted saturation
        text       = [200, 205, 215, 255],
        surface    = [26, 30, 39, 255],
        border     = [14, 16, 22, 255],
        title_mode = "darker",              # Deep, integrated title bars
        hover_mode = "darker",             # Tabs pop from the panel
    ),

    # -------------------------------------------------------------------------
    # LIGHT (High clarity, professional light gray)
    # -------------------------------------------------------------------------
    "light": ThemeSpec(
        base       = [225, 228, 232, 255],  # Slightly deeper base for better highlights
        accent     = [54, 81, 217, 255],
        text       = [45, 50, 60, 255],
        surface    = [242, 244, 247, 255],
        border     = [205, 210, 216, 255],
        is_light   = True,
        title_mode = "darker",              # Title bars feel like part of the frame
        hover_mode = "darker",              # Recessed inactive tabs
    ),

    # -------------------------------------------------------------------------
    # MIDNIGHT (OLED-friendly, ultra-high contrast)
    # -------------------------------------------------------------------------
    "midnight": ThemeSpec(
        base       = [8, 10, 15, 255],      # Darker base
        accent     = [60, 100, 255, 255],   # Electric blue
        text       = [210, 215, 230, 255],
        surface    = [14, 18, 26, 255],
        border     = [4, 5, 8, 255],
        title_mode = "darker",
        hover_mode = "darker",              # Everything recessed except active content
    ),

    # -------------------------------------------------------------------------
    # WARM (Organic, cozy tones)
    # -------------------------------------------------------------------------
    "warm": ThemeSpec(
        base       = [38, 32, 30, 255],
        accent     = [200, 110, 60, 255],   # Richer orange
        text       = [235, 225, 210, 255],
        surface    = [46, 39, 36, 255],
        border     = [28, 23, 21, 255],
        title_mode = "lighter",             # "Elevated" headers
        hover_mode = "lighter",
    ),

    # -------------------------------------------------------------------------
    # NORDIC (Frosty and crisp)
    # -------------------------------------------------------------------------
    "nordic": ThemeSpec(
        base       = [40, 46, 58, 255],     # Deeper slate for better contrast
        accent     = [136, 192, 208, 255],
        text       = [236, 239, 244, 255],
        surface    = [46, 52, 64, 255],
        border     = [31, 35, 43, 255],
        title_mode = "darker",
        hover_mode = "lighter",
    ),

    # -------------------------------------------------------------------------
    # MONOKAI (Classic dev look, high pop)
    # -------------------------------------------------------------------------
    "monokai": ThemeSpec(
        base       = [28, 26, 29, 255],
        accent     = [255, 216, 102, 255],
        text       = [248, 248, 242, 255],
        surface    = [39, 40, 34, 255],
        border     = [20, 19, 21, 255],
        title_mode = "darker",              # Intense focus on code/content area
        hover_mode = "darker",
    ),

    # -------------------------------------------------------------------------
    # NEUTRAL (The "Silver" Workstation)
    # -------------------------------------------------------------------------
    "neutral": ThemeSpec(
        base       = [190, 193, 197, 255],  # Pushed light-gray
        accent     = [40, 110, 190, 255],
        text       = [30, 35, 45, 255],
        surface    = [210, 213, 217, 255],
        border     = [170, 173, 178, 255],
        is_light   = True,
        title_mode = "darker",              # Strong structural separation
        hover_mode = "lighter",
    ),

    # -------------------------------------------------------------------------
    # TOKYO NIGHT (Clean neon-accented dark theme)
    # -------------------------------------------------------------------------
    "tokyo_night": ThemeSpec(
        base       = [26, 27, 38, 255],
        accent     = [122, 162, 247, 255],
        text       = [192, 202, 245, 255],
        surface    = [36, 40, 59, 255],
        border     = [16, 16, 20, 255],
        title_mode = "darker",
        hover_mode = "lighter",
        success_color = [158, 206, 106, 255],
        warning_color = [224, 175, 104, 255],
        error_color   = [247, 118, 142, 255],
        info_color    = [125, 207, 255, 255],
    ),

    # -------------------------------------------------------------------------
    # CATPPUCCIN (Soothing pastel dark aesthetic)
    # -------------------------------------------------------------------------
    "catppuccin": ThemeSpec(
        base       = [30, 30, 46, 255],
        accent     = [203, 166, 247, 255],
        text       = [205, 214, 244, 255],
        surface    = [49, 50, 68, 255],
        border     = [24, 24, 37, 255],
        title_mode = "darker",
        hover_mode = "lighter",
        success_color = [166, 227, 161, 255],
        warning_color = [249, 226, 175, 255],
        error_color   = [243, 139, 168, 255],
        info_color    = [137, 180, 250, 255],
    ),

    # -------------------------------------------------------------------------
    # DRACULA (High-contrast dark theme with vibrant purple highlights)
    # -------------------------------------------------------------------------
    "dracula": ThemeSpec(
        base       = [40, 42, 54, 255],
        accent     = [189, 147, 249, 255],
        text       = [248, 248, 242, 255],
        surface    = [68, 71, 90, 255],
        border     = [25, 26, 33, 255],
        title_mode = "darker",
        hover_mode = "lighter",
        success_color = [80, 250, 123, 255],
        warning_color = [241, 250, 140, 255],
        error_color   = [255, 85, 85, 255],
        info_color    = [139, 233, 253, 255],
    ),

    # -------------------------------------------------------------------------
    # SOLARIZED DARK (Precision low-eye-strain teal/cyan dark palette)
    # -------------------------------------------------------------------------
    "solarized_dark": ThemeSpec(
        base       = [0, 43, 54, 255],
        accent     = [38, 139, 210, 255],
        text       = [131, 148, 150, 255],
        surface    = [7, 54, 66, 255],
        border     = [0, 30, 38, 255],
        title_mode = "darker",
        hover_mode = "lighter",
        success_color = [133, 153, 0, 255],
        warning_color = [181, 137, 0, 255],
        error_color   = [220, 50, 47, 255],
        info_color    = [42, 161, 152, 255],
    ),

    # -------------------------------------------------------------------------
    # SOLARIZED LIGHT (Precision low-eye-strain warm cream light palette)
    # -------------------------------------------------------------------------
    "solarized_light": ThemeSpec(
        base       = [253, 246, 227, 255],
        accent     = [38, 139, 210, 255],
        text       = [101, 123, 131, 255],
        surface    = [238, 232, 213, 255],
        border     = [211, 203, 183, 255],
        is_light   = True,
        title_mode = "darker",
        hover_mode = "darker",
        success_color = [133, 153, 0, 255],
        warning_color = [181, 137, 0, 255],
        error_color   = [220, 50, 47, 255],
        info_color    = [42, 161, 152, 255],
    ),
}

# =============================================================================
# THEME DEFINITIONS - Built dictionaries
# =============================================================================

DOCK_THEMES: Dict[str, Dict[DockStyleCategory, Dict[str, Any]]] = {
    # Default uses BASE_DOCK_DEFAULTS from dock_theme.py
    "default": {},
}
DOCK_THEMES.update({name: build_theme(spec) for name, spec in THEME_SPECS.items()})

__all__ = ["DOCK_THEMES", "THEME_SPECS"]
