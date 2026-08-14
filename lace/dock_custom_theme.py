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

        # Sidebar tabs: rounded on all four corners, so the outline closes all
        # the way round — a detached pill rather than something joined to the
        # strip. Only the active tab is ringed; the inactive ones are bare.
        # (cyberpunk_edge draws the same shape but rings every tab — the two
        # presets are the pair that shows both halves of that choice.)
        sidebar_tab_flat_edge = "none",
        sidebar_tab_border_width = 2.0,
        sidebar_tab_border_color = [0, 0, 0, 0],         # inactive: no ring
        sidebar_tab_border_active_color = [0, 240, 255, 255],   # focus cyan
        # The strip shares the ring's content-facing edge and is painted first,
        # so at an equal width the ring covers it exactly and the active tab is
        # one clean line all the way round. That is why it is pinned here: the
        # 3px default is wider than the 2px ring, and the px it stuck out was
        # inside the tab — a pink sliver against the cyan.
        sidebar_indicator_width = 2.0,
    ),

    # -------------------------------------------------------------------------
    # CYBERPUNK EDGE (amber / violet "night city" — sodium light, not neon gas)
    #
    # The reference theme for title_border_bottom: a dedicated line along the
    # bottom edge of the tab/title bar, separate from the card outline, which
    # dims to violet when the dock area loses focus and burns amber when it has
    # it.  Deliberately a different cyberpunk palette from cyberpunk_neon
    # (indigo / pink / cyan) so the two are told apart at a glance.
    #
    # Note the two border tokens interact — dock_area_title_bar paints the full
    # outline when TITLE_BAR.border_width > 0 and only otherwise falls through
    # to the bottom rule. title_border_width is therefore left unset here;
    # setting it would suppress the very line this preset exists to show.
    # -------------------------------------------------------------------------
    "cyberpunk_edge": ThemeSpec(
        base       = [17, 13, 20, 255],     # Near-black plum, rain-slick asphalt
        accent     = [255, 154, 0, 255],    # Sodium-lamp amber
        text       = [242, 232, 224, 255],  # Warm off-white, not clinical
        surface    = [31, 24, 36, 255],     # Deep aubergine inner panel
        title_bg   = [10, 7, 13, 255],      # Near-black header: a deeper step
                                            # off the panel than the derived
                                            # 0.06 lightness, so the tab strip
                                            # reads as a distinct band
        border     = [110, 72, 148, 190],   # Muted violet, unfocused
        focus_border_color = [255, 154, 0, 255],   # Amber, focused
        title_mode = "darker",
        hover_mode = "lighter",
        success_color = [120, 224, 143, 255],   # Muted jade
        warning_color = [255, 196, 61, 255],    # Warm amber
        error_color   = [255, 84, 84, 255],     # Signal red
        info_color    = [186, 137, 255, 255],   # Violet

        # Geometrical Adjustments
        corner_radius = 10,
        border_width = 1.5,
        title_height = 32,
        title_padding_left = 0,
        title_padding_right = 8,
        title_button_spacing = 6,
        title_margin = 0,
        title_border_bottom = 1.5,          # the rule this preset demonstrates
        # No title_border_color: the rule inherits the muted violet border while
        # the area is unfocused and swaps to amber when it is focused — the same
        # active/inactive treatment as the card outline.  The focus colour is
        # the theme accent, which is also the active tab's indicator colour, so
        # the two segments of the line agree on hue as well as width.
        title_border_focus_color = [255, 154, 0, 255],
        tab_radius = 8,
        tab_margin = 3,
        content_margin = (8, 2),
        # Matches title_border_bottom: the active tab's indicator sits on the
        # same edge as the rule, so a different width made the line step
        # thicker under the active tab (measured 2px vs 1.5px).
        indicator_width = 1.5,
        indicator_position = "bottom",
        tab_dimming        = True,

        # Sidebar tabs: cyberpunk_neon's shape, but every tab is ringed, not
        # only the active one — the same violet/amber active-inactive treatment
        # this preset gives its card outline and its bottom rule.
        sidebar_tab_flat_edge = "none",
        sidebar_tab_border_width = 1.5,
        sidebar_tab_border_color = [110, 72, 148, 190],         # muted violet
        sidebar_tab_border_active_color = [255, 154, 0, 255],   # amber
        # 1.5 throughout, as everywhere else in this preset: the strip shares
        # the ring's content-facing edge and is painted under it, so an unequal
        # width steps that edge — left at the 3px default it doubled the amber
        # there. Nothing is lost by hiding it: amber against violet is already
        # what tells the two states apart.
        sidebar_indicator_width = 1.5,
    ),

    # -------------------------------------------------------------------------
    # SLATE AMBER — cyberpunk_edge's warmth on neutral's light industrial grey.
    #
    # The third of the trio below that shows how tab edges can be drawn, and the
    # only light one: it keeps cyberpunk_edge's *bottom rule* (the line runs
    # under the whole tab strip, and the active tab breaks it) to prove the rule
    # is not a dark-theme trick.  Amber is darkened from the neon 255,154,0 —
    # that hue has too little contrast against a light panel to read as a line.
    # -------------------------------------------------------------------------
    "slate_amber": ThemeSpec(
        base       = [196, 194, 190, 255],  # Warm machine grey
        accent     = [186, 98, 0, 255],     # Burnt amber, legible on light
        text       = [38, 34, 30, 255],     # Warm near-black
        surface    = [216, 214, 209, 255],  # Paper-white inner panel
        border     = [166, 162, 154, 255],  # Grey, unfocused
        focus_border_color = [186, 98, 0, 255],    # Amber, focused
        is_light   = True,
        title_mode = "darker",
        hover_mode = "lighter",

        # Geometrical Adjustments
        corner_radius = 4,
        border_width = 1.5,
        title_margin = 0.5,
        tab_radius = 4,
        content_margin = 0.5,
        # The rule, exactly as cyberpunk_edge draws it: no title_border_width
        # (which would paint the full outline and suppress the rule), and the
        # focus colour matched to the indicator so both segments of the line
        # agree on hue as well as width.
        title_border_bottom = 1.5,
        title_border_focus_color = [186, 98, 0, 255],
        indicator_width = 1.5,
        indicator_position = "bottom",
        tab_dimming = True,
    ),

    # -------------------------------------------------------------------------
    # NEON DUSK — cyberpunk_neon's neon on dracula's softer indigo.
    #
    # Shows the tab *outline*: every tab is drawn on its left, top and right
    # edges, the bottom left open so the tab reads as joined to the panel below.
    # Inactive tabs take the muted indigo, the active one the neon pink — the
    # inverse of slate_amber, where the line is on the inactive tabs.
    #
    # There is no card outline: border_width is 0, so the rule under the tab
    # strip is the only structural line, and the panel below it is bounded by
    # its own background rather than a stroke.  The rule and the tab outline
    # together close the inactive tabs on all four sides while the active tab
    # keeps its open bottom — which is what makes the active one read as a notch
    # cut out of the strip.
    #
    # No indicator at all: the outline already marks the active tab in the
    # accent colour.  At "bottom" the indicator would land on exactly the edge
    # the outline leaves open and fill the gap back in; at "top" it would stack
    # on the outline's own top edge at a different width, thickening it.
    # -------------------------------------------------------------------------
    "neon_dusk": ThemeSpec(
        base       = [34, 36, 48, 255],     # Dracula's indigo, a shade cooler
        accent     = [255, 92, 170, 255],   # Neon pink, pulled toward pastel
        text       = [240, 240, 248, 255],
        surface    = [50, 53, 70, 255],     # Lifted indigo inner panel
        title_bg   = [24, 26, 36, 255],     # Darker strip, so outlines read
        border     = [98, 114, 164, 200],   # Dracula "comment" blue-grey
        focus_border_color = [139, 233, 253, 255],  # Dracula cyan
        title_mode = "darker",
        hover_mode = "lighter",
        success_color = [80, 250, 123, 255],
        warning_color = [241, 250, 140, 255],
        error_color   = [255, 85, 85, 255],
        info_color    = [139, 233, 253, 255],

        # Geometrical Adjustments
        corner_radius = 8,
        border_width = 0.0,                 # No card outline around the area
        title_height = 32,
        title_padding_right = 8,
        title_button_spacing = 6,
        tab_radius = 8,
        tab_margin = 3,
        content_margin = (8, 2),
        # Matches tab_border_width: the rule and the tabs' own edges meet along
        # the same line, so a different width would step where they join.  No
        # title_border_color / _focus_color: the rule inherits the theme's
        # border while unfocused and its focus colour when focused, the same
        # swap the tab outline makes.
        # An even whole number, so the stroke covers whole pixels: a 1.5px pen
        # has to straddle a pixel boundary, and the half-covered row beside the
        # solid one reads as a faint second line rather than a soft edge.
        title_border_bottom = 2.0,
        # The outline both states share a width; only the colour differs, so
        # every tab's edges sit on the same pixels and the strip stays even.
        tab_border_width = 2.0,
        tab_border_color = [98, 114, 164, 160],     # Inactive: muted indigo
        tab_border_active_color = [255, 92, 170, 255],   # Active: neon pink
        indicator_position = "none",
        tab_dimming = True,
    ),

    # -------------------------------------------------------------------------
    # VIOLET HAZE — dracula's palette with cyberpunk_edge's geometry.
    #
    # The same outline as neon_dusk, with the inactive colour set fully
    # transparent so only the *active* tab is drawn: the classic browser look,
    # where the selected tab is a framed notch out of the strip and the rest
    # are bare.  A transparent colour, rather than a missing one, is what turns
    # a state off — the theme builder seeds both colours for every theme.
    #
    # Like neon_dusk it drops the card outline and rules off the tab strip
    # instead, which here is the whole effect: with no outline on the inactive
    # tabs, the rule runs unbroken behind them and stops only at the active
    # tab's open bottom.
    # -------------------------------------------------------------------------
    "violet_haze": ThemeSpec(
        base       = [40, 42, 54, 255],     # Dracula background
        accent     = [189, 147, 249, 255],  # Dracula purple
        text       = [248, 248, 242, 255],  # Dracula foreground
        surface    = [58, 61, 78, 255],     # Lifted panel, so the notch shows
        title_bg   = [30, 31, 40, 255],     # Recessed strip
        border     = [68, 71, 90, 255],
        focus_border_color = [189, 147, 249, 255],
        title_mode = "darker",
        hover_mode = "lighter",
        success_color = [80, 250, 123, 255],
        warning_color = [241, 250, 140, 255],
        error_color   = [255, 85, 85, 255],
        info_color    = [139, 233, 253, 255],

        # Geometrical Adjustments
        corner_radius = 10,
        # The outline runs down the left, across the bottom and back up the
        # right, stopping at the title bar's underside — title_border_bottom
        # below is the fourth side, so the frame closes without doubling a line
        # across the header.
        border_width = 2.0,
        border_below_title = True,
        title_height = 32,
        title_padding_right = 8,
        title_button_spacing = 6,
        tab_radius = 8,
        tab_margin = 3,
        content_margin = (8, 2),
        # Whole pixels, like the frame above — see neon_dusk.
        title_border_bottom = 2.0,          # Matches tab_border_width below
        tab_border_width = 2.0,
        tab_border_color = [98, 114, 164, 200],     # Inactive: Dracula comment
        tab_border_active_color = [189, 147, 249, 255],
        indicator_position = "none",
        tab_dimming = True,
    ),

    # -------------------------------------------------------------------------
    # MIDNIGHT HAZE (violet_haze's geometry over midnight's near-black, with
    # the frame as the only focus indicator)
    # -------------------------------------------------------------------------
    # Every edge belongs to the focused area's active tab: its outline turns
    # the corner at the title bar's underside and runs down, along the bottom
    # and back up as the area's frame, with the rule under the strip closing
    # the top.  Everything else — inactive tabs, and every widget in an area
    # that does not have focus — is drawn without a single line, so the eye has
    # exactly one place to land.  That is what tab_border_unfocused_color buys:
    # unset, the outline would merely dim.
    "midnight_haze": ThemeSpec(
        base       = [24, 26, 35, 255],     # Halfway between the two bases
        accent     = [125, 124, 252, 255],  # Dracula purple met electric blue
        text       = [229, 232, 236, 255],
        surface    = [36, 40, 52, 255],     # Lifted panel, so the notch shows
        title_bg   = [16, 18, 25, 255],     # Recessed strip, near-black
        border     = [42, 46, 60, 255],     # Splitters and seams only
        focus_border_color = [125, 124, 252, 255],
        title_mode = "darker",
        hover_mode = "lighter",
        success_color = [80, 250, 123, 255],
        warning_color = [241, 250, 140, 255],
        error_color   = [255, 85, 85, 255],
        info_color    = [139, 233, 253, 255],

        # Geometrical Adjustments — violet_haze's, unchanged
        corner_radius = 10,
        border_width = 2.0,
        border_below_title = True,
        title_height = 32,
        title_padding_right = 8,
        title_button_spacing = 6,
        tab_radius = 8,
        tab_margin = 3,
        content_margin = (8, 2),
        title_border_bottom = 2.0,          # Matches tab_border_width below
        tab_border_width = 2.0,
        tab_border_color = [0, 0, 0, 0],            # Inactive: no outline
        tab_border_active_color = [125, 124, 252, 255],
        tab_border_unfocused_color = [0, 0, 0, 0],  # Unfocused: no outline, no
                                                    # rule, and so no frame
        indicator_position = "none",
        tab_dimming = True,
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
