# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


from collections import OrderedDict
from typing import Any, Dict, Tuple
from lace.dock_theme import DockStyleCategory, ThemeSpec, build_theme

# =============================================================================
# THEME SPECIFICATIONS (Declarative 3- to 5-color presets)
# =============================================================================

THEME_SPECS: Dict[str, ThemeSpec] = {
    # =========================================================================
    # BASICS
    #
    # The five that come with no story attached.  A dark and a light,
    # a black and a warm-black, and a light grey that sits lower than `light`
    # does — pick one of these when the theme is not meant to be noticed.
    # =========================================================================

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

    # =========================================================================
    # EDITOR CLASSICS
    #
    # Palettes borrowed from editors and terminals people
    # already know by sight.  The colours are theirs; the chassis underneath is
    # Lace's stock one, so these differ from each other in hue and almost nothing
    # else.
    # =========================================================================

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

    # =========================================================================
    # NEON
    #
    # Saturated accents on near-black, and the only two presets that
    # ask to be looked at.  Both are dark by construction — there is no light
    # counterpart of a neon, because the glow is the ground being dark.
    # =========================================================================

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
        sidebar_tab_border_width = 1.5,                  # as the card outline
        sidebar_tab_border_color = [0, 0, 0, 0],         # inactive: no ring
        sidebar_tab_border_active_color = [0, 240, 255, 255],   # focus cyan
        # Hover takes the accent — the pink the dock widget tabs mark their own
        # active tab with, and the colour of this sidebar's strip. It is the one
        # hover ring that stays at full alpha: the others fade a ring the active
        # state repeats, while here the two states are already a hue apart, and
        # dimming the pink would only make it read as a weaker cyan.
        sidebar_tab_border_hover_color = [255, 0, 127, 255],
        # The strip shares the ring's content-facing edge and is painted first,
        # so at an equal width the ring covers it exactly and the active tab is
        # one clean line all the way round. That is why it is pinned here: the
        # 3px default is wider than the ring, and the px it stuck out was inside
        # the tab — a pink sliver against the cyan.
        sidebar_indicator_width = 1.5,
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

        # The sidebar runs the dock tabs' notch the other way round.  A dock tab
        # is rounded on top and open along the bottom; a sidebar tab here is
        # flat against the window edge and rounded on the two content-facing
        # corners, with the outline open along that flat outward side.  So what
        # it draws is a U — and the outward edge carries nothing in any state.
        # The highlight strip stays on the content-facing edge (the default),
        # where the U already runs, rather than closing the U from the outside.
        #
        # Same 2px as everything else, on both, so the strip lands exactly on
        # the outline's inward edge instead of stepping it.
        #
        # Where the dock tabs outline every tab, the sidebar draws nothing until
        # you point at one: idle is bare, and the muted indigo the inactive dock
        # tabs wear moves to the hover instead, so what a hovered tab shows is
        # that U on its own.  Selecting it fills the U in — neon pink, the
        # seeded accent, already the dock tabs' active outline.
        sidebar_tab_flat_edge = "outward",
        sidebar_tab_border_width = 2.0,
        sidebar_tab_border_color = [0, 0, 0, 0],            # Idle: bare
        sidebar_tab_border_hover_color = [98, 114, 164, 160],   # The dock tabs' indigo
        # The U on its own, which means no hover fill either.  The derived one
        # is a lifted slab covering the whole tab shape, flat edge included, and
        # its straight window-facing side is a harder line than the U it is
        # supposed to sit behind — so the tab reads as a rectangle with three
        # sides drawn rather than as a U.  Transparent, only the U is there.
        sidebar_tab_bg_hover_start = [0, 0, 0, 0],
        sidebar_tab_bg_hover_end = [0, 0, 0, 0],
        sidebar_indicator_width = 2.0,
    ),

    # =========================================================================
    # EDGE TREATMENTS
    #
    # Four designs in which the *outline* carries the
    # meaning — which area has focus, which tab is active — rather than a fill or
    # an underline.  Each ships as a family, ordered dark, neutral, light below,
    # and every member keeps its parent's geometry exactly: the radii, the line
    # widths, which edges are drawn and which are left open.  A pair should read
    # as one design in two keys, not as two designs.
    #
    # A light counterpart is not the dark one inverted.  Three things move
    # independently: the accent darkens (a neon that glows on near-black is a
    # pale smear on white), the panel/strip *order* stays put (the strip is still
    # the darker of the two, because title_mode is "darker" in both), and
    # hover_mode flips to "darker" — a near-white panel has nowhere lighter to
    # go, which is the same reason the stock `light` preset uses it and
    # `neutral`, whose panel sits lower, does not.
    #
    # A neutral counterpart is neutral in its *grounds* only.  base, surface and
    # title_bg flatten toward grey, keeping a trace of the parent's cast so the
    # backdrop still reads warm or cool as it did; the accent, the focus outlines
    # and the four status colours are kept and at most nudged.  Draining those
    # would not make a subtler theme, it would make a different and worse one.
    #
    # slate_amber is the exception to the ordering: it was always the light one,
    # so its family runs slate_amber_dark, slate_amber, slate_amber_light —
    # dark, light, lighter.
    # =========================================================================

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
    # CYBERPUNK EDGE NEUTRAL — the sodium-lamp preset at dusk.
    #
    # Not the dark one with the tint pulled out and not the light one dimmed:
    # the grounds sit between the two and nearer the light — panel at 0.73
    # lightness against 0.12 for the parent and 0.98 for the light one.  What
    # makes it "neutral" is that those grounds are flat.  The parent's plum
    # base and aubergine panel span 7 points across their channels; these span
    # 6, which is a cast rather than a colour, so the backdrop still reads warm
    # without competing with the amber in front of it.
    #
    # A mid ground is the hardest of the three for this preset, because both
    # halves of its outline pair have to survive on it.  The amber goes to
    # 148,72,0 — deeper than the light counterpart's 186,98,0 rather than
    # lighter, because that colour measures 1.9:1 here where it makes 4.5:1 on
    # near-white.  The violet moves the other way, up from the parent's, for
    # the same reason from the other side.
    # -------------------------------------------------------------------------
    "cyberpunk_edge_neutral": ThemeSpec(
        base       = [164, 160, 166, 255],  # Mid grey, plum cast: 6 points
                                            # across the channels where the
                                            # parent's spans 7
        accent     = [148, 72, 0, 255],     # Burnt amber, deeper than either
                                            # neighbour — see above
        text       = [38, 32, 42, 255],     # Warm near-black
        surface    = [186, 182, 188, 255],  # The lit panel
        title_bg   = [150, 147, 152, 255],  # The recessed band, as on the parent
        border     = [108, 76, 146, 215],   # Muted violet, unfocused — kept:
                                            # this is the half of the pair that
                                            # says "not focused"
        focus_border_color = [148, 72, 0, 255],    # Amber, focused
        is_light   = True,
        title_mode = "darker",
        hover_mode = "lighter",
        success_color = [26, 137, 70, 255],
        warning_color = [176, 116, 0, 255],
        error_color   = [196, 42, 42, 255],
        info_color    = [108, 61, 178, 255],

        # Geometry — cyberpunk_edge's, unchanged
        corner_radius = 10,
        border_width = 1.5,
        title_height = 32,
        title_padding_left = 0,
        title_padding_right = 8,
        title_button_spacing = 6,
        title_margin = 0,
        title_border_bottom = 1.5,
        title_border_focus_color = [148, 72, 0, 255],
        tab_radius = 8,
        tab_margin = 3,
        content_margin = (8, 2),
        indicator_width = 1.5,
        indicator_position = "bottom",
        tab_dimming = True,

        sidebar_tab_flat_edge = "none",
        sidebar_tab_border_width = 1.5,
        sidebar_tab_border_color = [108, 76, 146, 215],         # muted violet
        sidebar_tab_border_active_color = [148, 72, 0, 255],    # amber
        sidebar_indicator_width = 1.5,
    ),

    # -------------------------------------------------------------------------
    # CYBERPUNK EDGE LIGHT — the sodium-lamp preset at noon.
    #
    # Keeps the big geometry (10px cards, 8px tabs, the 32px header) that is
    # what separates this preset from slate_amber — which is already the same
    # warmth on light, but on neutral's much tighter 4px chassis.  The
    # two-colour outline survives intact: muted violet while unfocused, amber
    # when focused, both darkened until they read as lines on a near-white
    # panel rather than glowing off a near-black one.
    # -------------------------------------------------------------------------
    "cyberpunk_edge_light": ThemeSpec(
        base       = [231, 226, 235, 255],  # Pale plum-tinted grey
        accent     = [186, 98, 0, 255],     # Burnt amber.  The parent's neon
                                            # 255,154,0 is the one colour that
                                            # cannot survive the move: at
                                            # 1.6:1 on a white panel it is a
                                            # smear, not a 1.5px line
        text       = [40, 32, 44, 255],     # Warm near-black, plum-leaning
        surface    = [250, 247, 251, 255],  # Near-white inner panel
        title_bg   = [219, 212, 224, 255],  # Recessed strip — the parent's
                                            # explicit title_bg exists to make
                                            # the tab strip a distinct band,
                                            # and that band has to be stepped
                                            # by hand here too
        border     = [140, 104, 170, 210],  # Muted violet, unfocused
        focus_border_color = [186, 98, 0, 255],    # Amber, focused
        is_light   = True,
        title_mode = "darker",
        hover_mode = "darker",
        success_color = [26, 137, 70, 255],
        warning_color = [176, 116, 0, 255],
        error_color   = [196, 42, 42, 255],
        info_color    = [108, 61, 178, 255],

        # Geometry — cyberpunk_edge's, unchanged
        corner_radius = 10,
        border_width = 1.5,
        title_height = 32,
        title_padding_left = 0,
        title_padding_right = 8,
        title_button_spacing = 6,
        title_margin = 0,
        title_border_bottom = 1.5,
        title_border_focus_color = [186, 98, 0, 255],
        tab_radius = 8,
        tab_margin = 3,
        content_margin = (8, 2),
        indicator_width = 1.5,
        indicator_position = "bottom",
        tab_dimming = True,

        sidebar_tab_flat_edge = "none",
        sidebar_tab_border_width = 1.5,
        sidebar_tab_border_color = [140, 104, 170, 210],        # muted violet
        sidebar_tab_border_active_color = [186, 98, 0, 255],    # amber
        sidebar_indicator_width = 1.5,
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

        # The sidebar tabs round all four corners and carry the same 2px ring,
        # but reach it a step later than the dock tabs: bare when idle, ringed
        # in the accent at half alpha under the cursor, and ringed solid when
        # selected (that last colour is the seeded default — the accent — which
        # the width above is what switches on).  So the hover ring reads as the
        # active one previewed, and the strip stays matched to it: at the 3px
        # default it would out-thickness the ring it sits on.
        sidebar_tab_flat_edge = "none",
        sidebar_tab_border_width = 2.0,
        sidebar_tab_border_color = [0, 0, 0, 0],             # Idle: bare
        sidebar_tab_border_hover_color = [189, 147, 249, 130],
        sidebar_indicator_width = 2.0,
    ),

    # -------------------------------------------------------------------------
    # VIOLET HAZE NEUTRAL — the unbroken rule, over mid grey.
    #
    # Dracula's background is a distinctly blue-violet charcoal, and against it
    # the purple accent and the blue-grey "comment" outline are two hues doing
    # similar work.  Flattening the ground separates them: the outline reads as
    # a line rather than as part of the backdrop, which is the whole point of a
    # preset whose effect is a rule running unbroken behind the inactive tabs.
    #
    # The ground lands between the parent and the light counterpart and nearer
    # the light — 0.74 lightness against 0.27 and 0.98 — and stays flat while
    # it does: 5 points across the channels where dracula's own spans 14.
    # -------------------------------------------------------------------------
    "violet_haze_neutral": ThemeSpec(
        base       = [164, 164, 169, 255],  # Mid grey, cool cast
        accent     = [104, 60, 176, 255],   # Dracula purple, deepened to hold
                                            # its 2px lines on a mid ground
        text       = [36, 34, 44, 255],
        surface    = [186, 186, 191, 255],  # Lifted panel, so the notch shows
        title_bg   = [150, 150, 155, 255],  # Recessed strip
        border     = [144, 144, 150, 255],
        focus_border_color = [104, 60, 176, 255],
        is_light   = True,
        title_mode = "darker",
        hover_mode = "lighter",
        success_color = [22, 128, 66, 255],
        warning_color = [166, 110, 0, 255],
        error_color   = [193, 40, 40, 255],
        info_color    = [20, 116, 148, 255],

        # Geometry — violet_haze's, unchanged
        corner_radius = 10,
        border_width = 2.0,
        border_below_title = True,
        title_height = 32,
        title_padding_right = 8,
        title_button_spacing = 6,
        tab_radius = 8,
        tab_margin = 3,
        content_margin = (8, 2),
        title_border_bottom = 2.0,
        tab_border_width = 2.0,
        tab_border_color = [96, 108, 150, 215],     # Inactive: the "comment"
                                                    # blue-grey, kept and taken
                                                    # down to read on a mid
                                                    # ground — it is the line
                                                    # the whole preset is built
                                                    # around
        tab_border_active_color = [104, 60, 176, 255],
        indicator_position = "none",
        tab_dimming = True,

        sidebar_tab_flat_edge = "none",
        sidebar_tab_border_width = 2.0,
        sidebar_tab_border_color = [0, 0, 0, 0],             # Idle: bare
        sidebar_tab_border_hover_color = [104, 60, 176, 150],
        sidebar_indicator_width = 2.0,
    ),

    # -------------------------------------------------------------------------
    # VIOLET HAZE LIGHT — dracula's purple on paper.
    #
    # The effect is the rule running unbroken behind the inactive tabs and
    # stopping at the active tab's open bottom, so the inactive outline has to
    # stay plainly visible without competing with the accent.  On dark that is
    # dracula's "comment" blue-grey sitting above the strip; on light it is the
    # same relationship inverted — a lavender-grey a step *below* it.
    # -------------------------------------------------------------------------
    "violet_haze_light": ThemeSpec(
        base       = [230, 228, 238, 255],  # Cool lavender-grey
        accent     = [124, 77, 196, 255],   # Dracula purple, darkened to sit
                                            # on the panel at ~5.3:1
        text       = [40, 36, 52, 255],
        surface    = [250, 249, 253, 255],  # Lifted panel, so the notch shows
        title_bg   = [217, 214, 230, 255],  # Recessed strip
        border     = [201, 197, 216, 255],
        focus_border_color = [124, 77, 196, 255],
        is_light   = True,
        title_mode = "darker",
        hover_mode = "darker",
        success_color = [22, 128, 66, 255],
        warning_color = [166, 110, 0, 255],
        error_color   = [193, 40, 40, 255],
        info_color    = [20, 116, 148, 255],

        # Geometry — violet_haze's, unchanged
        corner_radius = 10,
        border_width = 2.0,
        border_below_title = True,
        title_height = 32,
        title_padding_right = 8,
        title_button_spacing = 6,
        tab_radius = 8,
        tab_margin = 3,
        content_margin = (8, 2),
        title_border_bottom = 2.0,
        tab_border_width = 2.0,
        tab_border_color = [163, 157, 190, 210],    # Inactive: the "comment"
                                                    # role, inverted
        tab_border_active_color = [124, 77, 196, 255],
        indicator_position = "none",
        tab_dimming = True,

        sidebar_tab_flat_edge = "none",
        sidebar_tab_border_width = 2.0,
        sidebar_tab_border_color = [0, 0, 0, 0],             # Idle: bare
        sidebar_tab_border_hover_color = [124, 77, 196, 130],
        sidebar_indicator_width = 2.0,
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

        # Sidebar tabs carry the same rule: the active one is ringed and
        # nothing else is drawn at all.  Rounded on all four corners, so the
        # ring closes the whole way round — the sidebar has no notch to cut,
        # nothing for an open edge to join it to.
        sidebar_tab_flat_edge = "none",
        sidebar_tab_border_width = 2.0,
        sidebar_tab_border_color = [0, 0, 0, 0],                # Inactive: bare
        # ...bare of a *line*, but not of colour: an inactive tab is filled
        # with the accent so the whole column reads as one family, and the ring
        # alone says which is selected.  The hover state caps the alpha, and
        # lower than it looks: hover is derived from the base and carries no
        # accent, so it sits at a fixed (44, 48, 65) however deep the tint gets.
        # Measured against it — idle (36, 38, 61) at 30, (40, 41, 70) at 40,
        # (42, 43, 73) at 45 — the two cross over just past 40, and beyond that
        # an idle tab out-glows a hovered one.  30 keeps a clear margin and
        # still reads violet against the bar's (24, 26, 35).
        sidebar_tab_bg_normal = [125, 124, 252, 30],
        sidebar_tab_border_active_color = [125, 124, 252, 255],
        # Matched to the ring, which covers it — the strip is not this preset's
        # marker any more than the dock tabs' is (indicator_position = "none"
        # above).  Left at the 3px default it would show as a band inside the
        # ring, which is the one way it could still make itself seen.
        sidebar_indicator_width = 2.0,
    ),

    # -------------------------------------------------------------------------
    # MIDNIGHT HAZE NEUTRAL — the focus-only frame, at mid tone.
    #
    # The parent's idea is that exactly one area on screen carries any line at
    # all, and it puts a blue cast under that line as well as in it.  Here the
    # ground goes flat and mid — 0.73 lightness against the parent's 0.17 and
    # the light counterpart's 0.98, 5 points across the channels against the
    # parent's 11 — and the indigo-violet stays exactly where it matters: the
    # focused area's frame, the active tab's outline, and the wash over the
    # idle sidebar tabs.  One colour on screen, and it is the one that means
    # something.
    # -------------------------------------------------------------------------
    "midnight_haze_neutral": ThemeSpec(
        base       = [163, 163, 168, 255],  # Mid grey, cool cast
        accent     = [66, 65, 192, 255],    # The parent's indigo-violet,
                                            # deepened for the mid ground
        text       = [28, 30, 40, 255],
        surface    = [185, 185, 190, 255],  # Lifted panel, so the notch shows
        title_bg   = [149, 149, 154, 255],  # Recessed strip
        border     = [146, 146, 152, 255],  # Splitters and seams only
        focus_border_color = [66, 65, 192, 255],
        is_light   = True,
        title_mode = "darker",
        hover_mode = "lighter",
        success_color = [22, 128, 66, 255],
        warning_color = [166, 110, 0, 255],
        error_color   = [193, 40, 40, 255],
        info_color    = [20, 116, 148, 255],

        # Geometry — midnight_haze's, unchanged
        corner_radius = 10,
        border_width = 2.0,
        border_below_title = True,
        title_height = 32,
        title_padding_right = 8,
        title_button_spacing = 6,
        tab_radius = 8,
        tab_margin = 3,
        content_margin = (8, 2),
        title_border_bottom = 2.0,
        tab_border_width = 2.0,
        tab_border_color = [0, 0, 0, 0],            # Inactive: no outline
        tab_border_active_color = [66, 65, 192, 255],
        tab_border_unfocused_color = [0, 0, 0, 0],  # Unfocused: no line at all
        indicator_position = "none",
        tab_dimming = True,

        sidebar_tab_flat_edge = "none",
        sidebar_tab_border_width = 2.0,
        sidebar_tab_border_color = [0, 0, 0, 0],
        # The parent's ceiling, recomputed for a light ground, where the
        # whole relationship is mirrored.  The wash is a dark accent over a
        # light bar now, so an idle tab reads *darker* than the bar rather
        # than brighter, and the hover it must not cross is darker still:
        # bar (163, 163, 168), idle (150, 150, 171), hover (132, 132, 138),
        # a clean run in the other direction.  The ceiling is alpha 81 --
        # past that an idle tab out-darkens a hovered one, which is the same
        # failure the parent's alpha 30 was chosen to avoid from below.
        sidebar_tab_bg_normal = [66, 65, 192, 34],
        sidebar_tab_border_active_color = [66, 65, 192, 255],
        sidebar_indicator_width = 2.0,
    ),

    # -------------------------------------------------------------------------
    # MIDNIGHT HAZE LIGHT — the focus-only frame, in daylight.
    #
    # The parent's whole idea is that exactly one area on screen carries any
    # line at all.  That survives the move unchanged and gets *more* demanding,
    # not less: on near-black a stray line announces itself, on near-white it
    # hides.  So the two transparent colours below are load-bearing here in a
    # way they are not anywhere else in this file.
    # -------------------------------------------------------------------------
    "midnight_haze_light": ThemeSpec(
        base       = [227, 229, 237, 255],  # Cool light grey
        accent     = [83, 82, 214, 255],    # The parent's indigo-violet,
                                            # darkened to ~5.6:1 on the panel
        text       = [28, 30, 40, 255],
        surface    = [247, 248, 252, 255],  # Lifted panel, so the notch shows
        title_bg   = [213, 216, 226, 255],  # Recessed strip
        border     = [206, 209, 220, 255],  # Splitters and seams only
        focus_border_color = [83, 82, 214, 255],
        is_light   = True,
        title_mode = "darker",
        hover_mode = "darker",
        success_color = [22, 128, 66, 255],
        warning_color = [166, 110, 0, 255],
        error_color   = [193, 40, 40, 255],
        info_color    = [20, 116, 148, 255],

        # Geometry — midnight_haze's, unchanged
        corner_radius = 10,
        border_width = 2.0,
        border_below_title = True,
        title_height = 32,
        title_padding_right = 8,
        title_button_spacing = 6,
        tab_radius = 8,
        tab_margin = 3,
        content_margin = (8, 2),
        title_border_bottom = 2.0,
        tab_border_width = 2.0,
        tab_border_color = [0, 0, 0, 0],            # Inactive: no outline
        tab_border_active_color = [83, 82, 214, 255],
        tab_border_unfocused_color = [0, 0, 0, 0],  # Unfocused: no line at all
        indicator_position = "none",
        tab_dimming = True,

        sidebar_tab_flat_edge = "none",
        sidebar_tab_border_width = 2.0,
        sidebar_tab_border_color = [0, 0, 0, 0],
        # The parent tints every idle sidebar tab with the accent and lets the
        # ring alone say which is selected, capped just below where an idle tab
        # would out-glow a hovered one.  That ceiling moves here, and in the
        # other direction: hover_mode is "darker" on light, so the hover state
        # darkens off the base while the tint lightens toward the accent, and
        # the two separate instead of converging: measured, an idle tab reads
        # (212, 214, 235) and a hovered one (202, 206, 221), on opposite sides
        # of the bar's own (227, 229, 237) in hue but both below it in value.
        # So the limit is no longer a crossover, it is simply that the wash
        # must not read as a second selected tab.
        sidebar_tab_bg_normal = [83, 82, 214, 26],
        sidebar_tab_border_active_color = [83, 82, 214, 255],
        sidebar_indicator_width = 2.0,
    ),

    # -------------------------------------------------------------------------
    # SLATE AMBER DARK — the machine shop after hours.
    #
    # slate_amber is the light one already — proving the bottom rule is not a
    # dark-theme trick was the whole reason it exists — so this is the
    # counterpart it never had.  Geometry is identical, which means the tight
    # 4px chassis it takes from neutral rather than the 10px one cyberpunk_edge
    # uses.  The amber moves the opposite way from the light variants above:
    # 186,98,0 was darkened *for* paper and sinks into a dark panel, so it
    # lifts back toward the sodium original without going all the way to neon.
    # -------------------------------------------------------------------------
    "slate_amber_dark": ThemeSpec(
        base       = [42, 40, 37, 255],     # Warm machine grey, dark
        accent     = [230, 150, 45, 255],   # Amber, lifted to read on dark
        text       = [232, 228, 222, 255],  # Warm off-white
        surface    = [54, 51, 47, 255],     # Lifted inner panel
        border     = [74, 70, 65, 255],     # Warm grey, unfocused
        focus_border_color = [230, 150, 45, 255],  # Amber, focused
        title_mode = "darker",
        hover_mode = "lighter",
        success_color = [120, 224, 143, 255],
        warning_color = [255, 196, 61, 255],
        error_color   = [255, 96, 84, 255],
        info_color    = [138, 180, 248, 255],

        # Geometry — slate_amber's, unchanged
        corner_radius = 4,
        border_width = 1.5,
        title_margin = 0.5,
        tab_radius = 4,
        content_margin = 0.5,
        title_border_bottom = 1.5,
        title_border_focus_color = [230, 150, 45, 255],
        indicator_width = 1.5,
        indicator_position = "bottom",
        tab_dimming = True,

        # Bare when idle, the ring previewed at part alpha under the cursor,
        # solid when selected — slate_amber's treatment exactly.
        sidebar_tab_flat_edge = "none",
        sidebar_tab_border_width = 1.5,
        sidebar_tab_border_color = [0, 0, 0, 0],               # Inactive: bare
        sidebar_tab_border_hover_color = [230, 150, 45, 160],
        sidebar_tab_border_active_color = [230, 150, 45, 255],
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

        # Sidebar tabs: cyberpunk_edge's, in this theme's colours — a closed
        # rounded ring at the same 1.5px this theme rules everything else with,
        # and the strip pinned to it so the ring covers it exactly on the edge
        # they share.  Two departures: an inactive tab is bare where edge rings
        # every one of them in its muted violet, and the hover carries the ring
        # at part alpha, so pointing at a tab previews the ring selecting it
        # would fill in.
        sidebar_tab_flat_edge = "none",
        sidebar_tab_border_width = 1.5,
        sidebar_tab_border_color = [0, 0, 0, 0],               # Inactive: bare
        sidebar_tab_border_hover_color = [186, 98, 0, 160],
        sidebar_tab_border_active_color = [186, 98, 0, 255],   # Amber, as the
                                                               # focus border
        sidebar_indicator_width = 1.5,
    ),

    # -------------------------------------------------------------------------
    # SLATE AMBER LIGHT — the machine shop under better lighting.
    #
    # Not a counterpart of slate_amber in the sense the six above are
    # counterparts: it is the same light theme a tier brighter, for a room or a
    # monitor where the parent's warm machine grey reads as dingy rather than
    # industrial.  slate_amber stays exactly as it was; this sits beside it.
    #
    # The greys carry the whole change — base and panel move up roughly 35
    # points, the border with them — and the amber moves the *other* way.  That
    # is not a stylistic choice: amber is what draws the rule under the tab
    # strip, the focused card's outline and the active sidebar ring, all at
    # 1.5px, and every point the ground gains is a point of separation those
    # lines lose.  186,98,0 measures 4.04:1 on the brighter panel where it was
    # 4.94:1 on the parent's; deepening it to 176,92,0 puts it back to 4.44:1,
    # which is what keeps a 1.5px line reading as a line.
    #
    # hover_mode stays "lighter", as on the parent, and is worth stating
    # because the three *_light presets above all had to flip it to "darker".
    # They are near-white panels with nowhere lighter to go; this one is not
    # quite that bright.  Measured, "lighter" separates the hover from the tab
    # strip by 34 points here against the parent's 35 — the same tab bar, in a
    # brighter key — where "darker" would have flattened it to 26.
    # -------------------------------------------------------------------------
    "slate_amber_light": ThemeSpec(
        base       = [230, 227, 222, 255],  # Warm machine grey, lifted
        accent     = [176, 92, 0, 255],     # Burnt amber, deepened to hold the
                                            # 1.5px lines against the brighter
                                            # ground
        text       = [42, 37, 32, 255],     # Warm near-black
        surface    = [249, 247, 244, 255],  # Near-white paper inner panel
        border     = [201, 196, 188, 255],  # Warm grey, unfocused
        focus_border_color = [176, 92, 0, 255],    # Amber, focused
        is_light   = True,
        title_mode = "darker",
        hover_mode = "lighter",

        # Geometry — slate_amber's, unchanged
        corner_radius = 4,
        border_width = 1.5,
        title_margin = 0.5,
        tab_radius = 4,
        content_margin = 0.5,
        title_border_bottom = 1.5,
        title_border_focus_color = [176, 92, 0, 255],
        indicator_width = 1.5,
        indicator_position = "bottom",
        tab_dimming = True,

        # Bare when idle, the ring previewed at part alpha under the cursor,
        # solid when selected — slate_amber's treatment exactly.
        sidebar_tab_flat_edge = "none",
        sidebar_tab_border_width = 1.5,
        sidebar_tab_border_color = [0, 0, 0, 0],               # Inactive: bare
        sidebar_tab_border_hover_color = [176, 92, 0, 160],
        sidebar_tab_border_active_color = [176, 92, 0, 255],
        sidebar_indicator_width = 1.5,
    ),
}

# =============================================================================
# THEME GROUPS
# =============================================================================

#: Group label -> the keys in it, both in presentation order.
#:
#: This is the same four sections THEME_SPECS is written in above, named so a
#: menu can show them.  Twenty-six entries in one flat list is a scroll, and it
#: hides the thing a reader most needs to see: that `violet_haze_neutral` is
#: not a preset of its own but one key of a design that ships in three.
#:
#: The order within a group is deliberate — the families run dark, neutral,
#: light, with slate_amber's dark, light, lighter as the stated exception.
#: Sorting these alphabetically would file the counterparts away from their
#: parents and put `midnight_haze_light` above `midnight_haze`.
THEME_GROUPS: "OrderedDict[str, Tuple[str, ...]]" = OrderedDict((
    ("Basics", (
        "dark", "light", "neutral", "midnight", "warm",
    )),
    ("Editor Classics", (
        "dracula", "monokai", "nordic", "catppuccin", "tokyo_night",
        "solarized_dark", "solarized_light",
    )),
    ("Neon", (
        "cyberpunk_neon", "neon_dusk",
    )),
    ("Edge Treatments", (
        "cyberpunk_edge", "cyberpunk_edge_neutral", "cyberpunk_edge_light",
        "violet_haze", "violet_haze_neutral", "violet_haze_light",
        "midnight_haze", "midnight_haze_neutral", "midnight_haze_light",
        "slate_amber_dark", "slate_amber", "slate_amber_light",
    )),
))

# A preset that is not in a group would simply vanish from every grouped menu,
# which is the kind of omission nobody notices until someone asks where their
# theme went.  Checked at import so it cannot ship.
_GROUPED = [key for keys in THEME_GROUPS.values() for key in keys]
assert len(_GROUPED) == len(set(_GROUPED)), "a theme is in two groups"
assert set(_GROUPED) == set(THEME_SPECS), (
    "THEME_GROUPS and THEME_SPECS disagree: "
    f"{set(_GROUPED) ^ set(THEME_SPECS)}")
del _GROUPED


# =============================================================================
# THEME DEFINITIONS - Built dictionaries
# =============================================================================

DOCK_THEMES: Dict[str, Dict[DockStyleCategory, Dict[str, Any]]] = {
    # Default uses BASE_DOCK_DEFAULTS from dock_theme.py
    "default": {},
}
DOCK_THEMES.update({name: build_theme(spec) for name, spec in THEME_SPECS.items()})

__all__ = ["DOCK_THEMES", "THEME_SPECS", "THEME_GROUPS"]
