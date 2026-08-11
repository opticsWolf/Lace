# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


from typing import Dict, Any
from lace.dock_theme import DockStyleCategory, ThemeSpec, build_theme

# =============================================================================
# THEME SPECIFICATIONS (Declarative 3- to 5-color presets)
# =============================================================================

THEME_SPECS: Dict[str, ThemeSpec] = {
    # -------------------------------------------------------------------------
    # DARK (Recessed headers, clean contrast)
    # -------------------------------------------------------------------------
    "dark": ThemeSpec(
        base               = [20, 23, 30, 255],
        accent             = [45, 85, 170, 255],    # Boosted saturation
        text               = [200, 205, 215, 255],
        surface            = [26, 30, 39, 255],
        border             = [20, 23, 30, 255],
        focus_border_color = [45, 85, 170, 255],   # Highlight border
        title_mode         = "darker",              # Deep, integrated title bars
        hover_mode         = "darker",              # Tabs pop from the panel
        corner_radius      = 4,
        tab_radius         = 4,
        border_width       = 1.5,
        title_margin       = 0.5,
        content_margin     = 0.5,
        tab_dimming        = True,
    ),

    # -------------------------------------------------------------------------
    # LIGHT (High clarity, professional light gray)
    # -------------------------------------------------------------------------
    "light": ThemeSpec(
        base               = [218, 221, 225, 255],  # Slightly deeper base for better highlights
        accent             = [54, 81, 217, 255],
        text               = [45, 50, 60, 255],
        surface            = [245, 247, 250, 255],
        border             = [218, 221, 225, 255],
        focus_border_color = [54, 81, 217, 255],    # Highlight border
        is_light           = True,
        title_mode         = "darker",              # Title bars feel like part of the frame
        hover_mode         = "darker",              # Recessed inactive tabs
        corner_radius      = 4,
        tab_radius         = 4,
        border_width       = 1.5,
        title_margin       = 0.5,
        content_margin     = 0.5,
        tab_dimming        = True,
    ),

    # -------------------------------------------------------------------------
    # MIDNIGHT (OLED-friendly, ultra-high contrast)
    # -------------------------------------------------------------------------
    "midnight": ThemeSpec(
        base       = [8, 10, 15, 255],      # Darker base
        accent     = [60, 100, 255, 255],   # Electric blue
        text       = [210, 215, 230, 255],
        surface    = [14, 18, 26, 255],
        border     = [14, 15, 18, 255],
        focus_border_color = [44, 65, 148, 255],
        title_mode = "darker",
        hover_mode = "darker",              # Everything recessed except active content
        corner_radius      = 0,
        tab_radius         = 4,
        border_width       = 0.5,
        title_margin       = 0.0,
        content_margin     = 4.0,
        tab_dimming        = True,
    ),

    # -------------------------------------------------------------------------
    # WARM (Organic, cozy tones)
    # -------------------------------------------------------------------------
    "warm": ThemeSpec(
        base       = [38, 32, 30, 255],
        accent     = [200, 110, 60, 255],   # Richer orange
        text       = [235, 225, 210, 255],
        surface    = [46, 39, 36, 255],
        border     = [46, 39, 36, 255],
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
        border_width       = 0.0,
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
        base               = [190, 193, 197, 255],  # Pushed light-gray
        accent             = [40, 110, 190, 255],
        text               = [30, 35, 45, 255],
        surface            = [210, 213, 217, 255],
        border             = [170, 173, 178, 255],
        focus_border_color = [40, 110, 190, 255],   # Highlight border
        is_light           = True,
        title_mode         = "darker",              # Strong structural separation
        hover_mode         = "lighter",
        corner_radius      = 4,
        tab_radius         = 4,
        border_width       = 1.5,
        title_margin       = 0.5,
        content_margin     = 0.5,
        tab_dimming        = True,
    ),

    # -------------------------------------------------------------------------
    # TOKYO NIGHT (Clean neon-accented dark theme)
    # -------------------------------------------------------------------------
    "tokyo_night": ThemeSpec(
        base       = [26, 27, 38, 255],
        accent     = [122, 162, 247, 255],
        text       = [192, 202, 245, 255],
        surface    = [36, 40, 59, 255],
        border     = [26, 27, 38, 255],
        focus_border_color = [82, 122, 182, 255],   # Highlight border
        title_mode = "darker",
        hover_mode = "lighter",
        success_color = [158, 206, 106, 255],
        warning_color = [224, 175, 104, 255],
        error_color   = [247, 118, 142, 255],
        info_color    = [125, 207, 255, 255],
        indicator_position = "none",
    ),

    # -------------------------------------------------------------------------
    # CATPPUCCIN (Soothing pastel dark aesthetic)
    # -------------------------------------------------------------------------
    "catppuccin": ThemeSpec(
        base       = [30, 30, 46, 255],
        accent     = [203, 166, 247, 255],
        text       = [205, 214, 244, 255],
        surface    = [49, 50, 68, 255],
        border     = [30, 30, 46, 128],
        focus_border_color = [203, 166, 247, 128],   # Highlight border
        title_mode = "darker",
        hover_mode = "lighter",
        success_color = [166, 227, 161, 255],
        warning_color = [249, 226, 175, 255],
        error_color   = [243, 139, 168, 255],
        info_color    = [137, 180, 250, 255],
        border_width       = 2.0,
        title_margin       = 0.0,
        content_margin     = 5.0,
    ),

    # -------------------------------------------------------------------------
    # DRACULA (High-contrast dark theme with vibrant purple highlights)
    # -------------------------------------------------------------------------
    "dracula": ThemeSpec(
        base       = [40, 42, 54, 255],
        accent     = [189, 147, 249, 255],
        text       = [248, 248, 242, 255],
        surface    = [68, 71, 90, 255],
        border     = [35, 36, 43, 255],
        focus_border_color     = [189, 147, 249, 255],
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
        border_width  = 0.0,
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
        border_width  = 0.0,
    ),

    # -------------------------------------------------------------------------
    # CYBERPUNK NEON (Vibrant, ultra-contrasty, showcasing all geometry options)
    # -------------------------------------------------------------------------
    "cyberpunk_neon": ThemeSpec(
        base       = [14, 11, 28, 255],     # Deep cyber indigo
        accent     = [255, 0, 127, 255],    # Electric neon pink
        text       = [245, 245, 255, 255],  # Crisp white text
        surface    = [24, 19, 44, 255],     # Rich violet inner panel
        border     = [0, 180, 205, 205],    # Glowing cyan structural border
        focus_border_color     = [0, 240, 255, 255],    # Glowing cyan structural border
        title_mode = "darker",              # Recessed dark indigo header
        hover_mode = "lighter",             # Tabs highlight brightly on hover
        success_color = [57, 255, 20, 255], # Neon green
        warning_color = [255, 215, 0, 255], # Cyber gold
        error_color   = [255, 42, 109, 255],# Neon red
        info_color    = [5, 217, 232, 255], # Cyan
        
        # Geometrical Adjustments
        corner_radius = 10,                 # Distinct rounded card corners
        border_width = 1.5,                 # Visible glowing 1.5px cyan outline
        title_height = 32,                  # Roomy 32px title bar height
        title_padding_left = 0,             # Leftmost tabs sit flush against left edge
        title_padding_right = 8,            # 8px padding on right side
        title_button_spacing = 6,           # 6px spacing between action buttons
        title_margin = 0,                   # 0 = flush against card edges (or set 2-3 for an inset border)
        tab_radius = 8,                     # 8px rounded top corners on tabs
        tab_margin = 3,                     # 3px gap separating adjacent tabs
        content_margin = (8, 2),            # 8px left/right/bottom, tight 2px top gap under title bar
        indicator_width = 2.0,
        indicator_position = "bottom",
        tab_dimming        = True,
    ),

    # -------------------------------------------------------------------------
    # CYBERPUNK EDGE (as cyberpunk_neon, plus a rule under the tab bar)
    #
    # The reference theme for title_border_bottom: a dedicated line along the
    # bottom edge of the tab/title bar, separate from the card outline.
    #
    # Note the two tokens interact — dock_area_title_bar paints the full
    # outline when TITLE_BAR.border_width > 0 and only otherwise falls through
    # to the bottom rule. title_border_width is therefore left unset here;
    # setting it would suppress the very line this preset exists to show.
    # Both draw in title_border_color, so they cannot be coloured separately.
    # -------------------------------------------------------------------------
    "cyberpunk_edge": ThemeSpec(
        base       = [14, 11, 28, 255],     # Deep cyber indigo
        accent     = [255, 0, 127, 255],    # Electric neon pink
        text       = [245, 245, 255, 255],  # Crisp white text
        surface    = [24, 19, 44, 255],     # Rich violet inner panel
        border     = [0, 180, 205, 205],    # Glowing cyan structural border
        focus_border_color = [0, 240, 255, 255],
        title_mode = "darker",
        hover_mode = "lighter",
        success_color = [57, 255, 20, 255],
        warning_color = [255, 215, 0, 255],
        error_color   = [255, 42, 109, 255],
        info_color    = [5, 217, 232, 255],

        # Geometrical Adjustments
        corner_radius = 10,
        border_width = 1.5,
        title_height = 32,
        title_padding_left = 0,
        title_padding_right = 8,
        title_button_spacing = 6,
        title_margin = 0,
        title_border_bottom = 1.5,          # the rule this preset demonstrates
        title_border_color = [0, 240, 255, 255],   # glowing cyan
        tab_radius = 8,
        tab_margin = 3,
        content_margin = (8, 2),
        indicator_width = 2,
        indicator_position = "bottom",
        tab_dimming        = True,
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
