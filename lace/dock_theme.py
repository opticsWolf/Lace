# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


import colorsys
import enum
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Union, Tuple
from PySide6.QtGui import QFont, QColor, QPalette

class DockStyleCategory(enum.Enum):
    """Namespaces for different dock component style groups."""
    CORE = enum.auto()
    PANEL = enum.auto()
    TAB = enum.auto()
    TITLE_BAR = enum.auto()
    SIDEBAR = enum.auto()
    SIDEPANEL = enum.auto()
    SPLITTER = enum.auto()
    OVERLAY = enum.auto()


@dataclass
class _FontFields:
    """Shared typography block for schemas exposing bare ``font_*`` tokens.

    Composed via dataclass inheritance (like :class:`_ActionButtonFields`) so the
    field names stay flat (``font_family`` etc.) and every ``styles.get("font_*")``
    consumer is untouched. Subclasses re-declare only a differing default
    or add fields (TAB adds ``active_font_weight``). Schemas that prefix their
    fonts (``tab_font_*`` in the sidebar, ``title_font_*`` in the side panel)
    can't share this block because consumers read the flat names verbatim.
    """
    font_family: str = "Segoe UI"
    font_size: int = 10
    font_weight: Union[str, int, QFont.Weight] = "normal"
    font_italic: bool = False
    font_underline: bool = False


@dataclass
class DockCoreStyleSchema:
    """Global colors and palette basics for the dock system."""
    canvas_bg: Optional[List[int]] = None    #App / Window main background
    border_color: Optional[List[int]] = None #Dock Area Widget Accent accent / highlight color
    accent_color: Optional[List[int]] = None #App / Window Accent accent / highlight color
    focus_border_color: Optional[List[int]] = None

    # Semantic / Status Colors
    success_color: Optional[List[int]] = None
    warning_color: Optional[List[int]] = None
    error_color: Optional[List[int]] = None
    info_color: Optional[List[int]] = None

    # Geometry
    border_width: float = 0.0 #Dock Area Widget border
    #: Draw the area outline on the left, right and bottom only, stopping at
    #: the underside of the title bar, whose own bottom rule then closes the
    #: top. No effect when border_width is 0.
    border_below_title: bool = False
    corner_radius: int = 2.0 #Dock Area Widget corner radius
    # Contents margins and spacing of the dock container's layout.
    margin: int = 0
    padding: int = 0

    # LaceStyle knobs (DockThemeBridge pushes them via LaceStyle.set_tokens)
    #: Corner radius of every standard control; 0 = square.
    control_radius: int = 4
    #: Scrollbar look: "thin" | "expanding" | "fusion".
    scrollbar: str = "expanding"
    #: How content meets a dock area's rounded corners: "cap" | "inset" | "none".
    corner_clip: str = "cap"
    #: Pen width of the keyboard focus ring; 0 hides it.
    focus_width: float = 2.0
    #: Share of text colour mixed over a control's fill for its outline (0-1).
    outline_strength: float = 0.22
    #: Outline input fields and framed views while unfocused; False leaves
    #: only the fill, and the accent ring a focused field takes.
    field_outline: bool = True
    #: Length of a splitter handle's grip, in px.
    splitter_length: int = 50
    #: The theme's contrast level ("low" | "normal" | "high"); sets the floor
    #: LaceStyle holds its non-text UI (outlines, focus ring) to.
    contrast: str = "normal"

    # Text
    text_color: Optional[List[int]] = None
    disabled_text_color: Optional[List[int]] = None

    # Tooltips (QToolTip palette: ToolTipBase / ToolTipText)
    tooltip_bg: Optional[List[int]] = None
    tooltip_text: Optional[List[int]] = None

@dataclass
class DockPanelStyleSchema:
    """Content area inside the dock widgets."""
    # Backgrounds & Borders
    bg_normal: Optional[List[int]] = None
    text_color: Optional[List[int]] = None
    
    # Input widget backgrounds (QLineEdit, QTextEdit, QListView, etc.)
    input_bg: Optional[List[int]] = None        # Base role - input field background
    alternate_base: Optional[List[int]] = None  # AlternateBase role - table row striping
    
    # Button styling
    button_bg: Optional[List[int]] = None       # Button role - button face background
    
    # 3D structural colors (spinbox borders, scrollbar grooves, frame edges)
    color_light: Optional[List[int]] = None     # Light role - highlight edge
    color_mid: Optional[List[int]] = None       # Mid role - mid-tone border
    color_dark: Optional[List[int]] = None      # Dark role - shadow edge
    color_shadow: Optional[List[int]] = None    # Shadow role - drop shadow

    # Selection (Highlight / HighlightedText roles), set by ThemeSpec.selection
    highlight: Optional[List[int]] = None
    highlighted_text: Optional[List[int]] = None

    # Geometry: the dock area's outline and radius are CORE's.
    # Content inset DockWidget applies to its own layout. A scalar, a
    # (horizontal, top) pair, a (left, top, right) triple, or a
    # (left, top, right, bottom) 4-tuple. NOT a colour: colour-ness is decided
    # by the declared annotation, and this one is deliberately not
    # Optional[List[int]] — see dock_style_manager._color_fields.
    content_margin: Union[int, float, List[int], Tuple[int, ...]] = 6

@dataclass
class DockTabStyleSchema(_FontFields):
    """Standard dock area tabs (horizontal)."""
    # Backgrounds & Borders
    bg_normal: Optional[List[int]] = None
    bg_hover: Optional[List[int]] = None
    bg_active: Optional[List[int]] = None
    # Tab outline, drawn on the left/top/right edges only — the bottom stays
    # open so the tab reads as joined to the panel below.  Paired
    # normal/active like bg_* and text_*.  A transparent colour on either side
    # skips that state, so a theme can outline only the active tab.
    border_normal_color: Optional[List[int]] = None
    border_active_color: Optional[List[int]] = None
    #: The active tab's outline while its dock area is *unfocused*.  Left
    #: unset, the active colour is dimmed halfway into the tab's background
    #: (with tab_dimming) or kept as-is.  A transparent colour makes the
    #: outline — and, under border_below_title, the whole frame that continues
    #: it — a focus indicator: present only on the area you are working in.
    border_unfocused_color: Optional[List[int]] = None

    # Geometry
    #: Master switch for the outline above: 0.0 draws none at all.
    border_width: float = 0.0
    corner_radius: int = 0
    margin: int = 0

    # Typography — bare font_* provided by _FontFields; tabs add an active weight.
    text_normal: Optional[List[int]] = None
    text_active: Optional[List[int]] = None
    active_font_weight: Union[str, int, QFont.Weight] = "normal"

    # Visual Indicators
    indicator_color: Optional[List[int]] = None
    indicator_width: float = 2.0
    indicator_position: str = "bottom"   # "top" or "bottom"
    tab_dimming: bool = False

    tab_icon_size: int = 16   # the widget's own icon, left of the label.
                              # DockWidgetTab.update_icon() read this token
                              # before any schema declared it, so themes that
                              # set it were rejected with "unknown token" while
                              # the code read as though it worked.

    # Action Buttons
    close_btn_color: Optional[List[int]] = None
    close_btn_bg_hover: Optional[List[int]] = None
    close_btn_bg_disable: Optional[List[int]] = None
    close_btn_size: int = 17
    close_btn_icon_size: int = 14   # matches the title-bar button icon size; sits
                                    # inside the padded hover fill with clear margin
    close_btn_corner_radius: int = 3
    close_btn_padding: int = 2      # QSS box is min + 2*padding + 3; with size=17 /
                                    # padding=2 the box is 24x24 and the 14px icon
                                    # centers exactly (even content rect, no
                                    # half-pixel rounding like size=20/pad=1)
    close_btn_expand_vertical: bool = False  # keep the close button a fixed square,
                                             # unlike the title-bar buttons which stretch


#: Fallback display size for an icon whose caller names no size token.
#: The one literal — the six sites that hardcoded it disagreed (14 in
#: dock_menu and dock_area_title_bar, 16 in the rest), and the 14s were dead
#: for every category that declares button_icon_size.
DEFAULT_ICON_SIZE = 16


@dataclass
class _ActionButtonFields:
    """Shared action-button styling for title bars and the sidebar panel.

    Composed via dataclass inheritance so the field names stay flat
    (``button_color`` etc.); ``button_spacing`` differs per host and is
    declared by each schema.
    """
    button_color: Optional[List[int]] = None
    button_disable_clr: Optional[List[int]] = None
    button_hover_bg: Optional[List[int]] = None
    button_corner_radius: int = 3
    button_padding: int = 2
    button_expand_vertical: bool = False
    button_size: int = 17   # QSS box = min + 2*padding + 3; 17/2 -> 24x24 box with an
                            # even 20px content rect so the 16px icon centers exactly
                            # (18/2 gave a 25px box with odd 21px content -> 0.5px drift)
    button_icon_size: int = 16


@dataclass
class DockTitleBarStyleSchema(_ActionButtonFields, _FontFields):
    """Dock area title bars."""
    # Backgrounds & Borders
    bg_normal: Optional[List[int]] = None
    border_color: Optional[List[int]] = None
    # Swapped in for border_color while the dock area holds focus, exactly as
    # CORE.focus_border_color swaps for CORE.border_color on the area's own
    # outline. Falls back to the CORE pair when unset.
    focus_border_color: Optional[List[int]] = None

    # Active edge: an accent strip along the top of a focused dock area's
    # title bar (VS Code style), drawn over the tabs. Off at width 0, the
    # default, so a theme opts in by setting a width.
    active_edge_color: Optional[List[int]] = None
    active_edge_width: float = 0.0

    # Geometry
    height: int = 30
    padding_left: int = 0
    padding_right: int = 6
    padding_top: int = 0
    border_width: float = 0.0
    # Bottom-edge rule under the title bar, drawn in border_color. Falls back
    # to border_width when 0. Fed by ThemeSpec.title_border_bottom.
    border_bottom: float = 0.0
    margin: int = 0

    # Typography — bare font_* provided by _FontFields; the window title uses
    # the default size (13px, like the native/qframeless title bar) and normal
    # weight. Themes may override either with "bold" / larger sizes.
    text_normal: Optional[List[int]] = None
    text_active: Optional[List[int]] = None
    font_size: int = 13
    font_weight: Union[str, int, QFont.Weight] = "normal"

    # Action Buttons — shared block via _ActionButtonFields; only spacing differs.
    button_spacing: int = 4


@dataclass
class DockSidebarStyleSchema:
    """Enhanced auto-hide sidebar styling."""
    # General Container
    width: int = 30
    bg_color: Optional[List[int]] = None
    border_color: Optional[List[int]] = None
    border_width: float = 1.0
    padding: int = 0

    # Tab Buttons - Backgrounds
    tab_bg_normal: Optional[List[int]] = None
    tab_bg_hover_start: Optional[List[int]] = None
    tab_bg_hover_end: Optional[List[int]] = None
    tab_bg_active: Optional[List[int]] = None

    # Tab Buttons - Geometry
    #: Radius of the corners ``tab_flat_edge`` leaves rounded.  ``None`` follows
    #: the dock widget tabs' own ``TAB.corner_radius``, so the two kinds of tab
    #: are rounded alike unless a theme says otherwise.
    tab_corner_radius: Optional[int] = None
    #: Which edge of the tab stays square: ``"outward"`` (the window edge the
    #: sidebar runs along — left in a left sidebar, right in a right one),
    #: ``"inward"`` (the edge facing the docked content), or ``"none"`` for a
    #: tab rounded on all four corners.  ``"all"``, the default, keeps every
    #: corner square and ignores ``tab_corner_radius`` — the plain rectangle
    #: sidebar tabs have always been.
    tab_flat_edge: str = "all"
    tab_margin: int = 2
    #: Edge length of the icon drawn on a sidebar tab, and the gap between it
    #: and the label.  Both were hardcoded in ``VerticalTabButton.paintEvent``,
    #: so a theme that scaled its fonts up left the icons behind.
    tab_icon_size: int = DEFAULT_ICON_SIZE
    tab_icon_gap: int = 8

    # Tab Buttons - Outline, mirroring the dock widget tabs' border_* block.
    # A transparent colour on either side skips that state, so a theme can
    # outline only the active tab.
    tab_border_normal_color: Optional[List[int]] = None
    tab_border_active_color: Optional[List[int]] = None
    #: Outline for a hovered, inactive tab.  Unset — not transparent — means the
    #: hover is not a state of its own and keeps ``tab_border_normal_color``,
    #: which is what every theme did before this existed.  The active tab is
    #: never this: a checked tab keeps its own outline under the cursor, the
    #: same precedence the fill triple uses.
    tab_border_hover_color: Optional[List[int]] = None
    #: Master switch for the outline above: 0.0 draws none at all.
    tab_border_width: float = 0.0
    #: Whether the outline closes across the flat edge.  Left open (the
    #: default) the tab reads as joined to the sidebar strip, the way a dock
    #: tab's open bottom joins it to the panel below.  Ignored when there is no
    #: flat edge to leave open — all four corners rounded is always closed.
    tab_border_closed: bool = False

    # Tab Buttons - Typography
    tab_text_normal: Optional[List[int]] = None
    tab_text_active: Optional[List[int]] = None
    tab_text_disabled: Optional[List[int]] = None
    tab_font_family: str = "Segoe UI"
    tab_font_size: int = 10
    tab_font_weight: Union[str, int, QFont.Weight] = "normal"
    #: Label weight on the open tab; ``None`` keeps ``tab_font_weight``.
    tab_active_font_weight: Optional[Union[str, int, QFont.Weight]] = None
    tab_font_italic: bool = False
    tab_font_underline: bool = False

    # Highlights & Badges
    indicator_color: Optional[List[int]] = None
    # Float like the dock tabs' own indicator_width, so a theme can match the
    # strip to a fractional outline width — a mismatch steps the edge they share.
    indicator_width: float = 3.0
    indicator_position: str = "right"  # "left" or "right"

    badge_bg: Optional[List[int]] = None
    badge_text: Optional[List[int]] = None
    badge_font_family: str = "Segoe UI"
    badge_font_size: int = 8
    badge_font_weight: Union[str, int, QFont.Weight] = "bold"
    badge_radius: int = 6
    badge_position: Any = "top_right"

@dataclass
class DockSidePanelStyleSchema(_ActionButtonFields):
    # Sidebar dock panel
    bg_normal: Optional[List[int]] = None
    height: int = 30
    padding_left: int = 10
    padding_right: int = 6
    padding_top: int = 0
    title_text_color: Optional[List[int]] = None
    title_font_family: str = "Segoe UI"
    title_font_size: int = 10
    title_font_weight: Union[str, int, QFont.Weight] = "bold"
    

    # Action Buttons — shared block via _ActionButtonFields; only spacing differs.
    button_spacing: int = 2

    # Panel geometry
    corner_radius: int = 0
    border_width: float = 1.0
    border_color: Optional[List[int]] = None
    focus_border_color: Optional[List[int]] = None
    shadow_blur_radius: int = 20
    shadow_color: Optional[List[int]] = None

@dataclass
class DockSplitterStyleSchema:
    """Layout splitters and resize handles."""
    handle_color: Optional[List[int]] = None
    handle_hover_color: Optional[List[int]] = None
    handle_width: int =  3
    total_width:  int =  7
    handle_margin: int = 0

@dataclass
class DockOverlayStyleSchema:
    """Drag-and-drop overlay and sidebar overlay panel styling."""
    # Drag overlay
    frame_color: Optional[List[int]] = None
    background_color: Optional[List[int]] = None
    overlay_color: Optional[List[int]] = None
    arrow_color: Optional[List[int]] = None
    shadow_color: Optional[List[int]] = None


# ============================================================================
# Theme Builder
# ============================================================================

@dataclass(frozen=True)
class ThemeSpec:
    """Declarative 5-colour (or 3-colour) theme input for :func:`build_theme`.

    Replaces the positional args of :func:`_build_theme` at call sites.
    ``base``/``accent``/``text`` accept either an ``[r, g, b, a]`` list or a
    ``QColor``; both funnel into the same list-based colour math.
    Optional ``surface`` and ``border`` provide separate control over inner
    panel surfaces and structural borders.
    """
    base: Union[QColor, List[int]]
    accent: Union[QColor, List[int]]
    text: Union[QColor, List[int]]
    surface: Optional[Union[QColor, List[int]]] = None
    border: Optional[Union[QColor, List[int]]] = None
    focus_border_color: Optional[Union[QColor, List[int]]] = None
    #: None decides from the base colour (OKLCH lightness below 0.6 is dark).
    is_light: Optional[bool] = None
    #: WCAG floor for text and UI tokens: "low" | "normal" | "high".
    #: Colours that already pass are left alone.
    contrast: str = "normal"
    #: How far derived surfaces step off each other: "flat" | "subtle" | "raised".
    depth: str = "subtle"
    #: Selected items: "solid" accent fill, or "tint", an accent wash that
    #: keeps the normal text colour.
    selection: str = "solid"
    #: LaceStyle scrollbars: "thin" | "expanding" | "fusion".
    scrollbar: str = "expanding"
    #: How dock content meets the card's rounded corners: "cap" paints the
    #: backdrop over them, "inset" keeps content clear, "none" leaves it.
    corner_clip: str = "cap"
    #: Corner radius of every LaceStyle control; 0 = square.
    control_radius: int = 4
    #: Pen width of LaceStyle's keyboard focus ring; 0 hides it.
    focus_width: float = 2.0
    #: LaceStyle outline strength: text mixed over a control's fill (0-1).
    outline_strength: float = 0.22
    #: LaceStyle outlines input fields and framed views while unfocused.
    #: False drops that line; a focused field keeps its accent ring.
    field_outline: bool = True
    #: Length of LaceStyle's splitter grip, in px.
    splitter_length: int = 50
    title_mode: str = "darker"   # "darker" | "lighter" relative to panel
    #: Explicit tab/title-bar background. Overrides the derived value, which
    #: is a fixed 0.06 lightness step off the panel and so cannot be widened
    #: from a preset. Same role for the header that `surface` plays for the panel.
    title_bg: Optional[Union[QColor, List[int]]] = None
    hover_mode: str = "lighter"  # "darker" | "lighter" relative to panel
    success_color: Optional[Union[QColor, List[int]]] = None
    warning_color: Optional[Union[QColor, List[int]]] = None
    error_color: Optional[Union[QColor, List[int]]] = None
    info_color: Optional[Union[QColor, List[int]]] = None
    corner_radius: Optional[int] = None
    border_width: Optional[float] = None
    title_height: Optional[int] = None
    title_padding_left: Optional[int] = None
    title_padding_right: Optional[int] = None
    title_button_spacing: Optional[int] = None
    title_margin: Optional[float] = None
    title_border_width: Optional[float] = None
    title_border_bottom: Optional[float] = None
    title_border_color: Optional[Union[QColor, List[int]]] = None
    #: Title-bar border colour while the dock area is focused. Defaults to the
    #: theme's focus_border_color, mirroring the area's own outline.
    title_border_focus_color: Optional[Union[QColor, List[int]]] = None
    #: Limit the dock-area outline to the left, right and bottom edges, ending
    #: at the title bar's underside so its bottom rule closes the frame. Pair
    #: with title_border_bottom, which supplies that fourth side.
    border_below_title: Optional[bool] = None
    tab_radius: Optional[int] = None
    tab_margin: Optional[int] = None
    #: Tab outline width; 0 (the default) draws no outline. The outline runs
    #: along the left/top/right edges only — the bottom is left open, which is
    #: what makes a tab read as joined to the panel below. An alternative to
    #: ``title_border_bottom``, not a companion: setting both boxes in the
    #: inactive tabs on all four sides.
    tab_border_width: Optional[float] = None
    #: Outline colour for inactive tabs. A fully transparent colour
    #: (``[0, 0, 0, 0]``) outlines only the active tab — the browser-tab look.
    tab_border_color: Optional[Union[QColor, List[int]]] = None
    #: Outline colour for the active tab. Defaults to the theme's accent.
    tab_border_active_color: Optional[Union[QColor, List[int]]] = None
    #: Outline colour for the active tab while its area is unfocused. Omitted,
    #: the active colour dims (see ``tab_dimming``); transparent
    #: (``[0, 0, 0, 0]``) drops the outline entirely, so only the area you are
    #: working in is outlined. With ``border_below_title`` the area's frame
    #: follows it, and the whole frame becomes the focus indicator.
    tab_border_unfocused_color: Optional[Union[QColor, List[int]]] = None
    content_margin: Optional[Union[int, float, List[int], Tuple[int, ...]]] = None
    tab_dimming: bool = False
    indicator_width: Optional[float] = None
    indicator_position: Optional[Union[str, List[str], Tuple[str, ...]]] = None

    # --- Sidebar tabs -------------------------------------------------------
    # The vertical auto-hide tabs, whose shape and outline mirror the dock
    # widget tabs above. Left unset they stay the plain rectangles they have
    # always been, so a theme opts in one field at a time.
    #: Which edge of a sidebar tab stays square: ``"outward"`` (the window edge
    #: the sidebar runs along), ``"inward"`` (facing the docked content),
    #: ``"none"`` to round all four corners, or ``"all"`` (the default) to
    #: round none. Anything but ``"all"`` engages ``sidebar_tab_radius``.
    sidebar_tab_flat_edge: Optional[str] = None
    #: Corner radius for those rounded corners. Omitted, the sidebar tabs take
    #: the dock widget tabs' ``tab_radius``, so the two agree by default.
    sidebar_tab_radius: Optional[int] = None
    #: The sidebar tab's three-state fill: inactive, hovered (a horizontal
    #: gradient between the two ``hover`` colours), and active. Each falls back
    #: to the derived value when unset — transparent for ``normal``, a step off
    #: the base for the hover pair, the panel colour for ``active``.
    #:
    #: Set ``normal`` to the accent at a low alpha and every tab is tinted with
    #: the highlight colour rather than only the selected one. How deep that
    #: tint can go is decided by the hover pair: derived, it carries no accent
    #: and sits at a fixed lightness, so a tint pushed past it makes an idle tab
    #: out-glow a hovered one. Give hover the accent too and the ceiling rises
    #: with it.
    sidebar_tab_bg_normal: Optional[Union[QColor, List[int]]] = None
    sidebar_tab_bg_hover_start: Optional[Union[QColor, List[int]]] = None
    sidebar_tab_bg_hover_end: Optional[Union[QColor, List[int]]] = None
    sidebar_tab_bg_active: Optional[Union[QColor, List[int]]] = None
    #: Sidebar tab outline width; 0 (the default) draws none. The outline skips
    #: the flat edge unless ``sidebar_tab_border_closed`` is set.
    sidebar_tab_border_width: Optional[float] = None
    #: Outline colour for inactive sidebar tabs. A fully transparent colour
    #: (``[0, 0, 0, 0]``) outlines only the active one.
    sidebar_tab_border_color: Optional[Union[QColor, List[int]]] = None
    #: Outline colour for the active sidebar tab. Defaults to the accent.
    sidebar_tab_border_active_color: Optional[Union[QColor, List[int]]] = None
    #: Outline colour for a hovered, inactive sidebar tab. Unlike the pair
    #: above this one is *not* seeded: left out, a hovered tab keeps the
    #: inactive outline. Set it — with the inactive colour transparent — and the
    #: outline becomes the hover cue, appearing under the cursor and nowhere
    #: else.
    sidebar_tab_border_hover_color: Optional[Union[QColor, List[int]]] = None
    #: Close the outline across the flat edge instead of leaving it open.
    #: Ignored with all four corners rounded, which is always closed.
    sidebar_tab_border_closed: Optional[bool] = None
    #: Width and edge of the sidebar tab's highlight strip — the counterpart of
    #: ``indicator_width`` / ``indicator_position`` for the dock widget tabs.
    #: ``"left"`` is the window-facing edge, ``"right"`` the content-facing one.
    #: Give it the same width as the outline: the strip sits *on* one of the
    #: outline's edges, so a mismatch steps that edge thicker.
    sidebar_indicator_width: Optional[float] = None
    sidebar_indicator_position: Optional[str] = None

    # Tooltip colors — when omitted, derived from the panel/text seed colors.
    tooltip_bg: Optional[Union[QColor, List[int]]] = None
    tooltip_text: Optional[Union[QColor, List[int]]] = None


from lace import color_science as _cs
from lace.theme_contrast import CONTRAST_TARGETS as _CONTRAST_TARGETS, enforce as _enforce

#: Disabled text on disabled fills (palette Disabled group): the "normal" floor.
_DISABLED_TARGET = _CONTRAST_TARGETS["disabled"]["normal"]

_CONTRAST_LEVELS = ("low", "normal", "high")
_DEPTH_LEVELS = ("flat", "subtle", "raised")

#: OKLCH lightness steps per derived surface, by depth (flat, subtle, raised).
#: "subtle" is calibrated to the median step 0.7.6 produced over every preset,
#: so the default look is kept while the per-theme spread (HLS steps grew and
#: shrank with the base colour) goes away.
_DEPTH: Dict[str, Tuple[float, float, float]] = {
    "panel":   (0.03, 0.05, 0.08),    # off base, when no surface is given
    "border":  (0.04, 0.06, 0.09),    # neutral border off the panel/base
    "title":   (0.03, 0.05, 0.07),    # off panel, sign from title_mode
    "tooltip": (0.05, 0.08, 0.11),    # off panel
    "hover":   (0.06, 0.09, 0.12),    # toward contrast; x0.7 for hover_mode="darker"
    "input":   (0.02, 0.035, 0.05),   # recessed off panel
    "alt":     (0.03, 0.05, 0.07),    # zebra rows off input
    "button":  (0.04, 0.07, 0.10),    # off panel
    "light":   (0.09, 0.13, 0.17),    # Fusion bevel highlight
    "mid":     (0.03, 0.045, 0.06),   # Fusion mid tone
    "dark":    (0.08, 0.11, 0.14),    # Fusion shadow edge
}


def _as_rgba(col: Union[QColor, List[int]]) -> List[int]:
    """Normalise a QColor or list to an ``[r, g, b, a]`` list for the colour math."""
    if isinstance(col, QColor):
        return [col.red(), col.green(), col.blue(), col.alpha()]
    return list(col)


def build_theme(spec: ThemeSpec) -> Dict[DockStyleCategory, Dict[str, Any]]:
    """Build a complete dock theme from a :class:`ThemeSpec` (public API)."""
    return _build_theme(**_spec_kwargs(spec))


def explicit_tokens(spec: ThemeSpec) -> set:
    """``"CATEGORY.token"`` names whose colour the spec set itself.

    For drift reports: these may only move slightly (theme_contrast).
    """
    names: set = set()
    _build_theme(**_spec_kwargs(spec), _explicit_out=names)
    return names


def _spec_kwargs(spec: ThemeSpec) -> Dict[str, Any]:
    return dict(base=_as_rgba(spec.base), accent=_as_rgba(spec.accent), text=_as_rgba(spec.text),
        is_light=spec.is_light, title_mode=spec.title_mode, hover_mode=spec.hover_mode,
        surface=_as_rgba(spec.surface) if spec.surface is not None else None,
        border=_as_rgba(spec.border) if spec.border is not None else None,
        focus_border_color=_as_rgba(spec.focus_border_color) if spec.focus_border_color is not None else None,
        success_color=_as_rgba(spec.success_color) if spec.success_color is not None else None,
        warning_color=_as_rgba(spec.warning_color) if spec.warning_color is not None else None,
        error_color=_as_rgba(spec.error_color) if spec.error_color is not None else None,
        info_color=_as_rgba(spec.info_color) if spec.info_color is not None else None,
        corner_radius=spec.corner_radius,
        border_width=spec.border_width,
        title_height=spec.title_height,
        title_padding_left=spec.title_padding_left,
        title_padding_right=spec.title_padding_right,
        title_button_spacing=spec.title_button_spacing,
        title_margin=spec.title_margin,
        title_bg=_as_rgba(spec.title_bg) if spec.title_bg is not None else None,
        title_border_width=spec.title_border_width,
        title_border_bottom=spec.title_border_bottom,
        title_border_color=_as_rgba(spec.title_border_color) if spec.title_border_color is not None else None,
        title_border_focus_color=_as_rgba(spec.title_border_focus_color) if spec.title_border_focus_color is not None else None,
        border_below_title=spec.border_below_title,
        tab_radius=spec.tab_radius,
        tab_margin=spec.tab_margin,
        tab_border_width=spec.tab_border_width,
        tab_border_color=_as_rgba(spec.tab_border_color) if spec.tab_border_color is not None else None,
        tab_border_active_color=_as_rgba(spec.tab_border_active_color) if spec.tab_border_active_color is not None else None,
        tab_border_unfocused_color=_as_rgba(spec.tab_border_unfocused_color) if spec.tab_border_unfocused_color is not None else None,
        content_margin=spec.content_margin,
        tab_dimming=spec.tab_dimming,
        indicator_width=spec.indicator_width,
        indicator_position=spec.indicator_position,
        sidebar_tab_flat_edge=spec.sidebar_tab_flat_edge,
        sidebar_tab_radius=spec.sidebar_tab_radius,
        sidebar_tab_bg_normal=_as_rgba(spec.sidebar_tab_bg_normal) if spec.sidebar_tab_bg_normal is not None else None,
        sidebar_tab_bg_hover_start=_as_rgba(spec.sidebar_tab_bg_hover_start) if spec.sidebar_tab_bg_hover_start is not None else None,
        sidebar_tab_bg_hover_end=_as_rgba(spec.sidebar_tab_bg_hover_end) if spec.sidebar_tab_bg_hover_end is not None else None,
        sidebar_tab_bg_active=_as_rgba(spec.sidebar_tab_bg_active) if spec.sidebar_tab_bg_active is not None else None,
        sidebar_tab_border_width=spec.sidebar_tab_border_width,
        sidebar_tab_border_color=_as_rgba(spec.sidebar_tab_border_color) if spec.sidebar_tab_border_color is not None else None,
        sidebar_tab_border_active_color=_as_rgba(spec.sidebar_tab_border_active_color) if spec.sidebar_tab_border_active_color is not None else None,
        sidebar_tab_border_hover_color=_as_rgba(spec.sidebar_tab_border_hover_color) if spec.sidebar_tab_border_hover_color is not None else None,
        sidebar_tab_border_closed=spec.sidebar_tab_border_closed,
        sidebar_indicator_width=spec.sidebar_indicator_width,
        sidebar_indicator_position=spec.sidebar_indicator_position,
        tooltip_bg=_as_rgba(spec.tooltip_bg) if spec.tooltip_bg is not None else None,
        tooltip_text=_as_rgba(spec.tooltip_text) if spec.tooltip_text is not None else None,
        contrast=spec.contrast,
        depth=spec.depth,
        selection=spec.selection,
        scrollbar=spec.scrollbar,
        corner_clip=spec.corner_clip,
        control_radius=spec.control_radius,
        focus_width=spec.focus_width,
        outline_strength=spec.outline_strength,
        field_outline=spec.field_outline,
        splitter_length=spec.splitter_length,
    )


def _build_theme(
    base: list, 
    accent: list, 
    text: list, 
    is_light: Optional[bool] = False,
    title_mode: str = "darker", # "lighter" or "darker" relative to panel
    hover_mode: str = "lighter",    # "lighter" or "darker" relative to panel
    surface: Optional[list] = None,
    border: Optional[list] = None,
    focus_border_color: Optional[list] = None,
    success_color: Optional[list] = None,
    warning_color: Optional[list] = None,
    error_color: Optional[list] = None,
    info_color: Optional[list] = None,
    corner_radius: Optional[int] = None,
    border_width: Optional[float] = None,
    title_height: Optional[int] = None,
    title_padding_left: Optional[int] = None,
    title_padding_right: Optional[int] = None,
    title_button_spacing: Optional[int] = None,
    title_margin: Optional[float] = None,
    title_bg: Optional[list] = None,
    title_border_width: Optional[float] = None,
    title_border_bottom: Optional[float] = None,
    title_border_color: Optional[list] = None,
    title_border_focus_color: Optional[list] = None,
    border_below_title: Optional[bool] = None,
    tab_radius: Optional[int] = None,
    tab_margin: Optional[int] = None,
    tab_border_width: Optional[float] = None,
    tab_border_color: Optional[list] = None,
    tab_border_active_color: Optional[list] = None,
    tab_border_unfocused_color: Optional[list] = None,
    content_margin: Optional[Union[int, float, List[int], Tuple[int, ...]]] = None,
    tab_dimming: bool = False,
    indicator_width: Optional[int] = None,
    indicator_position: Optional[Union[str, List[str], Tuple[str, ...]]] = None,
    sidebar_tab_flat_edge: Optional[str] = None,
    sidebar_tab_radius: Optional[int] = None,
    sidebar_tab_bg_normal: Optional[list] = None,
    sidebar_tab_bg_hover_start: Optional[list] = None,
    sidebar_tab_bg_hover_end: Optional[list] = None,
    sidebar_tab_bg_active: Optional[list] = None,
    sidebar_tab_border_width: Optional[float] = None,
    sidebar_tab_border_color: Optional[list] = None,
    sidebar_tab_border_active_color: Optional[list] = None,
    sidebar_tab_border_hover_color: Optional[list] = None,
    sidebar_tab_border_closed: Optional[bool] = None,
    sidebar_indicator_width: Optional[float] = None,
    sidebar_indicator_position: Optional[str] = None,
    tooltip_bg: Optional[list] = None,
    tooltip_text: Optional[list] = None,
    contrast: str = "normal",
    depth: str = "subtle",
    selection: str = "solid",
    scrollbar: str = "expanding",
    corner_clip: str = "cap",
    control_radius: int = 4,
    focus_width: float = 2.0,
    outline_strength: float = 0.22,
    field_outline: bool = True,
    splitter_length: int = 50,
    _explicit_out: Optional[set] = None,
) -> Dict[DockStyleCategory, Dict[str, Any]]:
    """
    Build a complete dock theme from 3 to 5 primary colors plus status tokens.
    
    Args:
        base:     Darkest background color [R, G, B, A]
        accent:   Primary accent/highlight color [R, G, B, A]
        text:     Primary text color [R, G, B, A]
        is_light: If True, adjustments go darker instead of lighter; None
                  decides from the base colour's lightness
        contrast: "low" | "normal" | "high" -- the WCAG floors text and UI
                  tokens are lifted to (lace.theme_contrast)
        depth:    "flat" | "subtle" | "raised" -- how far derived surfaces
                  step off each other
        selection: "solid" (accent fill) | "tint" (accent wash over the input)
        surface:  Optional inner content area background [R, G, B, A]
        border:   Optional structural border/divider color [R, G, B, A]
    """
    if contrast not in _CONTRAST_LEVELS:
        raise ValueError(f"contrast must be one of {_CONTRAST_LEVELS}, got {contrast!r}")
    if depth not in _DEPTH_LEVELS:
        raise ValueError(f"depth must be one of {_DEPTH_LEVELS}, got {depth!r}")
    if selection not in ("solid", "tint"):
        raise ValueError(f"selection must be 'solid' or 'tint', got {selection!r}")

    # The contrast pass edits colour lists in place: work on copies, so a
    # caller's own lists (reused across builds) never change under it.
    def _own(c):
        return None if c is None else _as_rgba(c)

    base, accent, text = _own(base), _own(accent), _own(text)
    (surface, border, focus_border_color, title_bg, tooltip_bg, tooltip_text,
     success_color, warning_color, error_color, info_color, title_border_color,
     title_border_focus_color, tab_border_color, tab_border_active_color,
     tab_border_unfocused_color, sidebar_tab_bg_normal, sidebar_tab_bg_hover_start,
     sidebar_tab_bg_hover_end, sidebar_tab_bg_active, sidebar_tab_border_color,
     sidebar_tab_border_active_color, sidebar_tab_border_hover_color) = map(_own, (
        surface, border, focus_border_color, title_bg, tooltip_bg, tooltip_text,
        success_color, warning_color, error_color, info_color, title_border_color,
        title_border_focus_color, tab_border_color, tab_border_active_color,
        tab_border_unfocused_color, sidebar_tab_bg_normal, sidebar_tab_bg_hover_start,
        sidebar_tab_bg_hover_end, sidebar_tab_bg_active, sidebar_tab_border_color,
        sidebar_tab_border_active_color, sidebar_tab_border_hover_color))

    # Every seed list the spec supplied. The contrast pass may nudge these
    # only slightly (theme_contrast.EXPLICIT_MAX_DE); derived colours are free.
    explicit_ids = frozenset(id(c) for c in (
        base, accent, text, surface, border, focus_border_color, title_bg,
        tooltip_bg, tooltip_text, success_color, warning_color, error_color, info_color,
        title_border_color, title_border_focus_color, tab_border_color,
        tab_border_active_color, tab_border_unfocused_color, sidebar_tab_bg_normal,
        sidebar_tab_bg_hover_start, sidebar_tab_bg_hover_end, sidebar_tab_bg_active,
        sidebar_tab_border_color, sidebar_tab_border_active_color,
        sidebar_tab_border_hover_color,
    ) if c is not None)

    # Unset, light or dark follows the base colour's perceptual lightness.
    if is_light is None:
        is_light = not _cs.is_dark(base)
    # Direction multiplier: light themes darken, dark themes lighten
    d = -1 if is_light else 1
    t_mode = -1.0 if title_mode == "darker" else 1.0
    # "darker" hovers are the quieter of the two.
    hover_scale = 0.7 if hover_mode == "darker" else 1.0

    level = _DEPTH_LEVELS.index(depth)

    def dl(name: str) -> float:
        return _DEPTH[name][level]

    def step(col, dL):
        return _cs.step(col, dL)

    def away(col, dL):
        """Step off ``col`` toward contrast with itself (lighter if dark)."""
        return _cs.step(col, dL, toward="contrast")

    # === DERIVED BACKGROUNDS (OKLCH lightness steps, see _DEPTH) ===
    _panel      = surface if surface is not None else step(base, d * dl("panel"))

    # Neutral border derived from surface or base depending on light/dark theme
    _ref_col        = _panel if surface is not None else base
    _neutral_border = border if border is not None else step(_ref_col, d * dl("border"))
    _focus_border   = focus_border_color if focus_border_color is not None else (border if border is not None else step(accent, d * 0.07))

    # Title bar / header background: a step darker or lighter than the panel,
    # by title_mode, independent of the theme's direction.
    _title_bg   = title_bg if title_bg is not None else step(_panel, t_mode * dl("title"))

    # Tooltip surface: a clearly-distinct step off the panel so the popup pops
    # against any surface (lighter on dark themes, darker on light themes);
    # text defaults to the full-strength seed text color.
    _tooltip_bg   = tooltip_bg if tooltip_bg is not None else step(_panel, d * dl("tooltip"))
    _tooltip_text = tooltip_text if tooltip_text is not None else text

    # Interactive hovers: always step in the direction of high contrast (lighter on dark containers, darker on light containers)
    hover_dl    = dl("hover") * hover_scale
    _hover      = away(base, hover_dl)
    _hover_end  = away(base, max(0.03, hover_dl * 0.65))

    # Button hover fill, resolved *relative to the container it sits on* so it always contrasts reliably.
    _btn_hover_title = away(_title_bg, hover_dl)
    _btn_hover_panel = away(_panel, hover_dl)

    # Input widget backgrounds (for QLineEdit, QTextEdit, tables, etc.): recessed
    _input_bg       = step(_panel, -d * dl("input"))
    _alternate_base = step(_input_bg, d * dl("alt"))  # zebra rows

    # Button face background
    _button_bg = step(_panel, d * dl("button"))

    # 3D structural colors (for widget borders, scrollbars, frames)
    _color_light  = step(_panel, d * dl("light"))   # Highlight edge
    _color_mid    = step(_panel, -d * dl("mid"))    # Mid-tone border
    _color_dark   = step(_panel, -d * dl("dark"))   # Shadow edge
    _color_shadow = [0, 0, 0, 72 if not is_light else 48]   # Drop shadow

    # === DERIVED TEXT (toward the background, or away for "active") ===
    _text_muted    = step(text, -d * 0.09)
    _text_disabled = step(text, -d * 0.26)
    _text_active   = step(text, d * 0.15)

    # === BUTTON DISABLED: a glyph colour between base and text ===
    _btn_disabled = step(base, d * 0.20)

    # === ACCENT VARIANTS ===
    # The bright accent steps *toward contrast with the canvas*, so on a light
    # theme it darkens and stays visible instead of washing out.
    _accent_bright = step(accent, d * 0.07)
    _accent_dim    = accent[:3] + [round(accent[3] * 0.25) if len(accent) > 3 else 64]

    # === SELECTION ===
    if selection == "solid":
        _highlight = accent
        _highlighted_text = _cs.on_color(accent, prefer=(_text_active, base))
    else:
        tint = accent[:3] + [72]
        _highlight = _cs._composite(tint, _input_bg)
        _highlighted_text = text
    
    # === STATUS COLORS ===
    _success = success_color if success_color is not None else ([78, 201, 112, 255] if not is_light else [34, 134, 58, 255])
    _warning = warning_color if warning_color is not None else ([230, 167, 0, 255] if not is_light else [179, 134, 0, 255])
    _error   = error_color if error_color is not None else ([241, 76, 76, 255] if not is_light else [203, 36, 49, 255])
    _info    = info_color if info_color is not None else ([55, 148, 255, 255] if not is_light else [0, 102, 214, 255])
    
    # === UTILITY ===
    _transparent = [0, 0, 0, 0]
    _shadow      = [0, 0, 0, 64 if not is_light else 32]
    
    theme = {
        DockStyleCategory.CORE: _build_core(base, accent, text, _text_disabled, _focus_border, _neutral_border, _success, _warning, _error, _info, _tooltip_bg, _tooltip_text),
        DockStyleCategory.PANEL: _build_panel(text, _panel, _input_bg, _alternate_base, _button_bg, _color_light, _color_mid, _color_dark, _color_shadow),
        DockStyleCategory.SIDEBAR: _build_sidebar(base, accent, _panel, _hover, _hover_end, _text_muted, _text_active, _text_disabled, _transparent, _neutral_border),
        DockStyleCategory.SIDEPANEL: _build_sidepanel(text, _panel, _text_muted, _btn_disabled, _btn_hover_panel, _shadow, _focus_border, _neutral_border),
        DockStyleCategory.TAB: _build_tab(text, accent, _title_bg, _panel, _hover, _text_muted, _text_active, _btn_disabled, _btn_hover_panel, _neutral_border),
        DockStyleCategory.TITLE_BAR: _build_titlebar(_title_bg, _text_muted, _text_active, _accent_bright, _btn_disabled, _btn_hover_title, _neutral_border, _focus_border),
        DockStyleCategory.SPLITTER: _build_splitter(base, accent),
        DockStyleCategory.OVERLAY: _build_overlay(text, _panel, _accent_bright, _accent_dim, _shadow),
    }

    # LaceStyle knobs; DockThemeBridge hands them to LaceStyle.set_tokens.
    theme[DockStyleCategory.CORE].update(
        contrast=contrast, scrollbar=scrollbar, control_radius=control_radius,
        focus_width=focus_width, outline_strength=outline_strength,
        field_outline=field_outline,
        splitter_length=splitter_length, corner_clip=corner_clip)

    if corner_radius is not None:
        theme[DockStyleCategory.CORE]["corner_radius"] = corner_radius
        theme[DockStyleCategory.SIDEPANEL]["corner_radius"] = corner_radius
    if border_width is not None:
        theme[DockStyleCategory.CORE]["border_width"] = border_width
        theme[DockStyleCategory.SIDEPANEL]["border_width"] = border_width
    if title_height is not None:
        theme[DockStyleCategory.TITLE_BAR]["height"] = title_height
    if title_padding_left is not None:
        theme[DockStyleCategory.TITLE_BAR]["padding_left"] = title_padding_left
    if title_padding_right is not None:
        theme[DockStyleCategory.TITLE_BAR]["padding_right"] = title_padding_right
    if title_button_spacing is not None:
        theme[DockStyleCategory.TITLE_BAR]["button_spacing"] = title_button_spacing
    if title_margin is not None:
        theme[DockStyleCategory.TITLE_BAR]["margin"] = title_margin
    if title_border_width is not None:
        theme[DockStyleCategory.TITLE_BAR]["border_width"] = title_border_width
    if title_border_bottom is not None:
        theme[DockStyleCategory.TITLE_BAR]["border_bottom"] = title_border_bottom
    if title_border_color is not None:
        theme[DockStyleCategory.TITLE_BAR]["border_color"] = title_border_color
    if title_border_focus_color is not None:
        theme[DockStyleCategory.TITLE_BAR]["focus_border_color"] = title_border_focus_color
    if tab_radius is not None:
        theme[DockStyleCategory.TAB]["corner_radius"] = tab_radius
    if tab_margin is not None:
        theme[DockStyleCategory.TAB]["margin"] = tab_margin
    if border_below_title is not None:
        theme[DockStyleCategory.CORE]["border_below_title"] = border_below_title
    if tab_border_width is not None:
        theme[DockStyleCategory.TAB]["border_width"] = tab_border_width
    if tab_border_color is not None:
        theme[DockStyleCategory.TAB]["border_normal_color"] = tab_border_color
    if tab_border_active_color is not None:
        theme[DockStyleCategory.TAB]["border_active_color"] = tab_border_active_color
    if tab_border_unfocused_color is not None:
        theme[DockStyleCategory.TAB]["border_unfocused_color"] = tab_border_unfocused_color
    if content_margin is not None:
        theme[DockStyleCategory.PANEL]["content_margin"] = content_margin

    theme[DockStyleCategory.TAB]["tab_dimming"] = tab_dimming
    if indicator_width is not None:
        theme[DockStyleCategory.TAB]["indicator_width"] = indicator_width
    if indicator_position is not None:
        theme[DockStyleCategory.TAB]["indicator_position"] = indicator_position

    # Sidebar tabs. The radius is deliberately *not* defaulted here: left
    # unset the token stays None, which the tab resolves against
    # TAB.corner_radius at paint time, so the two kinds of tab keep the same
    # roundness even when a theme changes only tab_radius.
    if sidebar_tab_flat_edge is not None:
        theme[DockStyleCategory.SIDEBAR]["tab_flat_edge"] = sidebar_tab_flat_edge
    if sidebar_tab_radius is not None:
        theme[DockStyleCategory.SIDEBAR]["tab_corner_radius"] = sidebar_tab_radius
    if sidebar_tab_bg_normal is not None:
        theme[DockStyleCategory.SIDEBAR]["tab_bg_normal"] = sidebar_tab_bg_normal
    if sidebar_tab_bg_hover_start is not None:
        theme[DockStyleCategory.SIDEBAR]["tab_bg_hover_start"] = sidebar_tab_bg_hover_start
    if sidebar_tab_bg_hover_end is not None:
        theme[DockStyleCategory.SIDEBAR]["tab_bg_hover_end"] = sidebar_tab_bg_hover_end
    if sidebar_tab_bg_active is not None:
        theme[DockStyleCategory.SIDEBAR]["tab_bg_active"] = sidebar_tab_bg_active
    if sidebar_tab_border_width is not None:
        theme[DockStyleCategory.SIDEBAR]["tab_border_width"] = sidebar_tab_border_width
    if sidebar_tab_border_color is not None:
        theme[DockStyleCategory.SIDEBAR]["tab_border_normal_color"] = sidebar_tab_border_color
    if sidebar_tab_border_active_color is not None:
        theme[DockStyleCategory.SIDEBAR]["tab_border_active_color"] = sidebar_tab_border_active_color
    if sidebar_tab_border_hover_color is not None:
        theme[DockStyleCategory.SIDEBAR]["tab_border_hover_color"] = sidebar_tab_border_hover_color
    if sidebar_tab_border_closed is not None:
        theme[DockStyleCategory.SIDEBAR]["tab_border_closed"] = sidebar_tab_border_closed
    if sidebar_indicator_width is not None:
        theme[DockStyleCategory.SIDEBAR]["indicator_width"] = sidebar_indicator_width
    if sidebar_indicator_position is not None:
        theme[DockStyleCategory.SIDEBAR]["indicator_position"] = sidebar_indicator_position

    theme[DockStyleCategory.PANEL]["highlight"] = _highlight
    theme[DockStyleCategory.PANEL]["highlighted_text"] = list(_highlighted_text)

    if _explicit_out is not None:
        _explicit_out.update(f"{cat.name}.{key}" for cat, values in theme.items()
                             for key, v in values.items() if id(v) in explicit_ids)

    # Lift whatever still misses its floor; shared lists carry each fix to
    # every token that uses the colour.
    _enforce(theme, contrast=contrast, depth=depth, explicit_ids=explicit_ids)
    return theme


def _build_core(base, accent, text, _text_disabled, _focus_border, _neutral_border, _success, _warning, _error, _info, _tooltip_bg, _tooltip_text):
    return {
        "canvas_bg":          base,
        "border_color":       _neutral_border,
        "accent_color":       accent,
        "focus_border_color": _focus_border,
        "text_color":         text,
        "disabled_text_color": _text_disabled,
        "success_color":      _success,
        "warning_color":      _warning,
        "error_color":        _error,
        "info_color":         _info,
        "tooltip_bg":         _tooltip_bg,
        "tooltip_text":       _tooltip_text,
    }


def _build_panel(text, _panel, _input_bg, _alternate_base, _button_bg, _color_light, _color_mid, _color_dark, _color_shadow):
    return {
        "bg_normal":          _panel,
        "text_color":         text,
        "input_bg":           _input_bg,
        "alternate_base":     _alternate_base,
        "button_bg":          _button_bg,
        "color_light":        _color_light,
        "color_mid":          _color_mid,
        "color_dark":         _color_dark,
        "color_shadow":       _color_shadow,
    }


def _build_sidebar(base, accent, _panel, _hover, _hover_end, _text_muted, _text_active, _text_disabled, _transparent, _neutral_border):
    return {
        "bg_color":           base,
        "tab_bg_normal":      _transparent,
        "tab_bg_hover_start": _hover,
        "tab_bg_hover_end":   _hover_end,
        "tab_bg_active":      _panel,
        # Outline colours are seeded but inert: tab_border_width defaults to 0,
        # so a theme opts in by setting sidebar_tab_border_width — exactly as
        # the dock widget tabs' own outline works.
        "tab_border_normal_color": _neutral_border,
        "tab_border_active_color": accent,
        "tab_text_normal":    _text_muted,
        "tab_text_active":    _text_active,
        "tab_text_disabled":  _text_disabled,
        "indicator_color":    accent,
        "badge_bg":           accent,
        "badge_text":         _text_muted,
    }


def _build_sidepanel(text, _panel, _text_muted, _btn_disabled, _btn_hover_panel, _shadow, _focus_border, _neutral_border):
    return {
        "bg_normal":          _panel,
        "title_text_color":   text,
        "button_color":       _text_muted,
        "button_disable_clr": _btn_disabled,
        "button_hover_bg":    _btn_hover_panel,
        "shadow_color":       _shadow,
        "border_color":       _neutral_border,
        "focus_border_color": _focus_border,
        "border_width":       1.0,
    }


def _build_tab(text, accent, _title_bg, _panel, _hover, _text_muted, _text_active, _btn_disabled, _btn_hover_panel, _neutral_border):
    return {
        "bg_normal":          _title_bg,
        "bg_hover":           _hover,
        "bg_active":          _panel,
        # Outline colours are seeded but inert: border_width defaults to 0, so
        # a theme opts in by setting tab_border_width.
        "border_normal_color": _neutral_border,
        "border_active_color": accent,
        "text_normal":        _text_muted,
        "text_active":        _text_active,
        "indicator_color":    accent,
        # close_btn_color: bright text blended 70/30 with the tab background
        # (_panel), so the glyph reads clearly but harmonizes with the tab
        # instead of floating as pure white/grey.
        "close_btn_color":    _blend_rgba(_text_active, _panel, 0.30),
        "close_btn_bg_hover": _btn_hover_panel,
        "close_btn_bg_disable": _btn_disabled,
    }


def _build_titlebar(_title_bg, _text_muted, _text_active, _accent_bright, _btn_disabled, _btn_hover_title, _neutral_border, _focus_border):
    return {
        "bg_normal":          _title_bg,
        "border_color":       _neutral_border,
        "focus_border_color": _focus_border,
        "text_normal":        _text_muted,
        "text_active":        _text_active,
        "active_edge_color":  _accent_bright,
        "button_color":       _text_muted,
        "button_disable_clr": _btn_disabled,
        "button_hover_bg":    _btn_hover_title,
    }


def _build_splitter(base, accent):
    return {
        "handle_color":       base,
        "handle_hover_color": accent,
    }


def _build_overlay(text, _panel, _accent_bright, _accent_dim, _shadow):
    return {
        "frame_color":        _accent_bright,
        "background_color":   _panel,
        "overlay_color":      _accent_dim,
        "arrow_color":        text,
        "shadow_color":       _shadow,
    }

# -------------------------------------------------------------------------
# Color Helper
# -------------------------------------------------------------------------
def _contrasting_hover(col, amount: float = 0.10):
    """Button-hover fill that always contrasts with its container ``col``:
    lighten a dark surface, darken a light one.  Keeps hover visible even when
    the theme's derived hover would collide with the container background.
    """
    rgb = [x / 255.0 for x in col[:3]]
    _, l, _ = colorsys.rgb_to_hls(*rgb)
    direction = 1.0 if l < 0.5 else -1.0
    return _adjust_color(col, l_off=direction * amount)


def _blend_rgba(c1: list, c2: list, factor: float = 0.2) -> list:
    """Blend color list ``c2`` into ``c1`` by ``factor`` (0..1), per channel.

    ``factor=0.2`` -> 80% of ``c1`` + 20% of ``c2``.  Used to harmonize a
    glyph color with its container (e.g. the tab close icon against the tab
    background) instead of leaving it as a pure isolated color.
    """
    return [
        round(c1[i] * (1.0 - factor) + c2[i] * factor)
        for i in range(min(len(c1), len(c2)))
    ]


def _adjust_color(col, l_off=0, s_off=0, h_off=0, a_off=0):    # Normalize input and separate alpha
    rgba = [x / 255.0 for x in col]
    rgb, a = rgba[:3], rgba[3:]

    # Convert, apply offsets, and clamp/wrap
    h, l, s = colorsys.rgb_to_hls(*rgb)
    clamp = lambda x: max(0.0, min(1.0, x))
    
    h = (h + h_off) % 1.0
    l = clamp(l + l_off)
    s = clamp(s + s_off)
    
    # Reconstruct RGB
    new_rgb = list(colorsys.hls_to_rgb(h, l, s))
    
    # Handle Alpha and scale back to 255
    if a:
        new_rgb.append(clamp(a[0] + a_off))
        
    return [round(x * 255) for x in new_rgb]

# -------------------------------------------------------------------------
# VS CODE 2026 DARK (Default Theme)
# -------------------------------------------------------------------------
BASE_DOCK_DEFAULTS: Dict[DockStyleCategory, Dict[str, Any]] = build_theme(ThemeSpec(
    base               = [24, 24, 24, 255],
    accent             = [0, 120, 212, 255],
    text               = [204, 204, 204, 255],
    surface            = [31, 31, 31, 255],
    border             = [24, 24, 24, 0],
    #focus_border_color = [0, 156, 255, 255],
    title_mode         = "lighter",
    hover_mode         = "lighter",
    corner_radius      = 4,
    tab_radius         = 4,
    border_width       = 1.5,
    title_margin       = 0.0,
    content_margin     = 0.0,
))


# -------------------------------------------------------------------------
# Canonical Colour Conversion (formerly dock_colors.py)
# -------------------------------------------------------------------------
def to_qcolor(val: Any) -> QColor:
    """Canonical converter: ``QColor`` | ``'#hex'`` / colour name | ``[r,g,b(,a)]`` -> ``QColor``."""
    if isinstance(val, QColor):
        return QColor(val)
    if isinstance(val, str):
        return QColor(val)  # handles '#rgb', '#rrggbb', '#aarrggbb', SVG names
    if isinstance(val, (list, tuple)) and len(val) >= 3:
        return QColor(
            int(val[0]), int(val[1]), int(val[2]),
            int(val[3]) if len(val) > 3 else 255,
        )
    return QColor(0, 0, 0)


def qcolor_to_list(c: QColor) -> List[int]:
    """Inverse of :func:`to_qcolor` for the list form (JSON-safe)."""
    return [c.red(), c.green(), c.blue(), c.alpha()]


def is_color_list(val: Any) -> bool:
    """True for a 3- or 4-element list/tuple of numbers (an ``[r,g,b(,a)]`` colour)."""
    return (
        isinstance(val, (list, tuple))
        and 3 <= len(val) <= 4
        and all(isinstance(c, (int, float)) for c in val)
    )


def deep_to_qcolor(value: Any) -> Any:
    """Recursively convert colour lists / hex strings to ``QColor``."""
    if isinstance(value, QColor):
        return value
    if is_color_list(value):
        return to_qcolor(value)
    if isinstance(value, str):
        return to_qcolor(value) if value.startswith("#") else value
    if isinstance(value, dict):
        return {k: deep_to_qcolor(v) for k, v in value.items()}
    if isinstance(value, list):
        return [deep_to_qcolor(v) for v in value]
    return value


def deep_to_serializable(value: Any) -> Any:
    """Recursively convert ``QColor`` back to JSON-safe ``[r,g,b,a]`` lists."""
    if isinstance(value, QColor):
        return qcolor_to_list(value)
    if isinstance(value, dict):
        return {k: deep_to_serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [deep_to_serializable(v) for v in value]
    return value


# -------------------------------------------------------------------------
# Palette Construction & Bridge (formerly dock_palette_bridge.py)
# -------------------------------------------------------------------------
_snapshot_cache: Optional[tuple[int, "DockThemeColors"]] = None


def _get_contrasting_text_color(col: Union[QColor, List[int]]) -> QColor:
    """Computes relative luminance to determine whether white or dark text
    provides readable contrast against the given background/accent colour."""
    qcol = to_qcolor(col)
    r = qcol.redF()
    g = qcol.greenF()
    b = qcol.blueF()
    def _lin(v):
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    L = 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)
    if L > 0.4:
        return QColor(20, 20, 20)
    return QColor(255, 255, 255)


@dataclass(frozen=True, slots=True)
class DockThemeColors:
    """All resolved colours needed to build a dock widget palette."""
    canvas_bg:        QColor
    title_bg:         QColor
    panel_bg:         QColor
    text_color:       QColor
    accent_color:     QColor
    border_color:     QColor
    input_bg:         QColor
    alternate_base:   QColor
    button_bg:        QColor
    color_light:      QColor
    color_mid:        QColor
    color_dark:       QColor
    color_shadow:     QColor
    disabled_text:    QColor
    placeholder_text: QColor
    highlight:        QColor
    highlighted_text: QColor
    success_color:    QColor
    warning_color:    QColor
    error_color:      QColor
    info_color:       QColor
    tooltip_bg:       QColor
    tooltip_text:     QColor


def resolve_dock_colors() -> DockThemeColors:
    """Return the current resolved dock colours, cached by manager generation."""
    global _snapshot_cache
    from lace.dock_style_manager import get_dock_style_manager
    sm = get_dock_style_manager()
    if _snapshot_cache is not None and _snapshot_cache[0] == sm.generation:
        return _snapshot_cache[1]
    colors = _resolve_uncached(sm)
    _snapshot_cache = (sm.generation, colors)
    return colors


def _resolve_uncached(sm) -> DockThemeColors:
    canvas_bg = to_qcolor(sm.get(DockStyleCategory.CORE, "canvas_bg", [20, 20, 20]))
    title_bg = to_qcolor(sm.get(DockStyleCategory.TITLE_BAR, "bg_normal", [37, 37, 38]))
    panel_bg = to_qcolor(sm.get(DockStyleCategory.PANEL, "bg_normal", [30, 30, 30]))
    text_color = to_qcolor(sm.get(DockStyleCategory.CORE, "text_color", [204, 204, 204]))
    accent = to_qcolor(sm.get(DockStyleCategory.CORE, "accent_color", [0, 120, 212]))
    border = to_qcolor(sm.get(DockStyleCategory.CORE, "border_color", [45, 45, 45]))
    
    # Fallbacks for partial themes: the same OKLCH steps the builder uses at
    # depth="subtle", signed by the panel's own lightness.
    d = 1 if _cs.is_dark(qcolor_to_list(panel_bg)) else -1

    def token_or_step(key, off, dL):
        raw = sm.get(DockStyleCategory.PANEL, key)
        if raw:
            return to_qcolor(raw)
        return to_qcolor(_cs.step(qcolor_to_list(off), dL))

    input_bg = token_or_step("input_bg", panel_bg, -d * _DEPTH["input"][1])
    alternate_base = token_or_step("alternate_base", input_bg, d * _DEPTH["alt"][1])
    button_bg = token_or_step("button_bg", panel_bg, d * _DEPTH["button"][1])
    color_light = token_or_step("color_light", panel_bg, d * _DEPTH["light"][1])
    color_mid = token_or_step("color_mid", panel_bg, -d * _DEPTH["mid"][1])
    color_dark = token_or_step("color_dark", panel_bg, -d * _DEPTH["dark"][1])
    
    color_shadow_raw = sm.get(DockStyleCategory.PANEL, "color_shadow")
    if color_shadow_raw:
        color_shadow = to_qcolor(color_shadow_raw)
    else:
        color_shadow = QColor(0, 0, 0, 80)

    disabled_text = QColor(text_color)
    disabled_text.setAlpha(max(0, text_color.alpha() // 3))

    placeholder_text = QColor(text_color)
    placeholder_text.setAlpha(max(0, text_color.alpha() // 2))

    highlight_raw = sm.get(DockStyleCategory.PANEL, "highlight")
    highlight = to_qcolor(highlight_raw) if highlight_raw else QColor(accent)
    highlighted_raw = sm.get(DockStyleCategory.PANEL, "highlighted_text")
    highlighted_text = (to_qcolor(highlighted_raw) if highlighted_raw
                        else to_qcolor(_cs.on_color(qcolor_to_list(highlight))))
    success = to_qcolor(sm.get(DockStyleCategory.CORE, "success_color", [78, 201, 112]))
    warning = to_qcolor(sm.get(DockStyleCategory.CORE, "warning_color", [230, 167, 0]))
    error = to_qcolor(sm.get(DockStyleCategory.CORE, "error_color", [241, 76, 76]))
    info = to_qcolor(sm.get(DockStyleCategory.CORE, "info_color", [55, 148, 255]))
    tooltip_bg = to_qcolor(sm.get(DockStyleCategory.CORE, "tooltip_bg", [48, 48, 48]))
    tooltip_text = to_qcolor(sm.get(DockStyleCategory.CORE, "tooltip_text", [220, 220, 220]))

    return DockThemeColors(
        canvas_bg=canvas_bg, title_bg=title_bg, panel_bg=panel_bg,
        text_color=text_color, accent_color=accent, border_color=border,
        input_bg=input_bg, alternate_base=alternate_base,
        button_bg=button_bg, color_light=color_light, color_mid=color_mid,
        color_dark=color_dark, color_shadow=color_shadow,
        disabled_text=disabled_text, placeholder_text=placeholder_text,
        highlight=highlight, highlighted_text=highlighted_text, success_color=success,
        warning_color=warning, error_color=error, info_color=info,
        tooltip_bg=tooltip_bg, tooltip_text=tooltip_text
    )


def _apply_shared_roles(pal: QPalette, c: DockThemeColors):
    """Applies palette roles that are identical across all dock contexts."""
    pal.setColor(QPalette.ColorRole.Highlight, c.highlight)
    pal.setColor(QPalette.ColorRole.HighlightedText, c.highlighted_text)
    if hasattr(QPalette.ColorRole, "Link"):
        pal.setColor(QPalette.ColorRole.Link, c.accent_color)
    if hasattr(QPalette.ColorRole, "LinkVisited"):
        pal.setColor(QPalette.ColorRole.LinkVisited, c.accent_color)
    pal.setColor(QPalette.ColorRole.ToolTipBase, c.tooltip_bg)
    pal.setColor(QPalette.ColorRole.ToolTipText, c.tooltip_text)
    pal.setColor(QPalette.ColorRole.PlaceholderText, c.placeholder_text)
    
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText, QPalette.ColorRole.ButtonText):
        pal.setColor(QPalette.ColorGroup.Disabled, role, c.disabled_text)


def build_dock_palette(
    is_panel: bool = False, 
    base_palette: Optional[QPalette] = None, 
    colors: Optional[DockThemeColors] = None
) -> QPalette:
    """Constructs a QPalette for the docking system.

    Without a ``base_palette`` the result depends only on ``colors``, so it
    is built once per colour snapshot: every widget that restyles on a theme
    switch asks for the same palette.
    """
    global _palette_cache
    c = colors or resolve_dock_colors()
    if base_palette is None:
        if _palette_cache[0] is not c:
            _palette_cache = (c, {})
        cached = _palette_cache[1].get(is_panel)
        if cached is None:
            cached = _palette_cache[1][is_panel] = _build_dock_palette(is_panel, None, c)
        return QPalette(cached)
    return _build_dock_palette(is_panel, base_palette, c)


#: (colour snapshot, {is_panel: QPalette}) for build_dock_palette.
_palette_cache: tuple = (None, {})


def _build_dock_palette(is_panel: bool, base_palette: Optional[QPalette],
                        c: DockThemeColors) -> QPalette:
    pal = QPalette(base_palette) if base_palette else QPalette()

    primary_bg = c.panel_bg if is_panel else c.canvas_bg

    pal.setColor(QPalette.ColorRole.Window, primary_bg)
    pal.setColor(QPalette.ColorRole.WindowText, c.text_color)

    pal.setColor(QPalette.ColorRole.Base, c.input_bg)
    pal.setColor(QPalette.ColorRole.AlternateBase, c.alternate_base)
    pal.setColor(QPalette.ColorRole.Text, c.text_color)

    pal.setColor(QPalette.ColorRole.Button, c.button_bg)
    pal.setColor(QPalette.ColorRole.ButtonText, c.text_color)

    pal.setColor(QPalette.ColorRole.Light, c.color_light)
    pal.setColor(QPalette.ColorRole.Mid, c.color_mid)
    pal.setColor(QPalette.ColorRole.Dark, c.color_dark)
    pal.setColor(QPalette.ColorRole.Shadow, c.color_shadow)

    _apply_shared_roles(pal, c)
    _apply_state_groups(pal, c, primary_bg)
    return pal


#: Qt >= 6.6 only; guarded so older bindings still build a palette.
_ACCENT_ROLE = getattr(QPalette.ColorRole, "Accent", None)


def _apply_state_groups(pal: QPalette, c: DockThemeColors, window: QColor) -> None:
    """Fill the roles the base set leaves to Qt, then the Inactive and Disabled groups.

    Every role in every group ends up set from the theme, so nothing falls
    back to the platform palette (a light Windows default under a dark
    theme). ``setColor`` without a group writes all three groups; the
    Inactive and Disabled overrides come after.
    """
    L = qcolor_to_list
    win, base, button = L(window), L(c.input_bg), L(c.button_bg)

    # Midlight sits between Button and Light, as Fusion expects.
    pal.setColor(QPalette.ColorRole.Midlight, to_qcolor(_cs.mix(button, L(c.color_light), 0.5)))
    # BrightText: text that must read on Dark (Fusion's pressed/indicator fills).
    pal.setColor(QPalette.ColorRole.BrightText, to_qcolor(_cs.on_color(L(c.color_dark))))
    if _ACCENT_ROLE is not None:
        pal.setColor(_ACCENT_ROLE, c.accent_color)

    # --- Inactive: selection loses its colour when the window loses focus,
    # like Windows 11 and macOS; everything else matches Active.
    Li, Ci, hi, ai = _cs.to_oklch(L(c.highlight))
    quiet = _cs.from_oklch(Li, Ci * 0.3, hi, ai)
    I = QPalette.ColorGroup.Inactive
    pal.setColor(I, QPalette.ColorRole.Highlight, to_qcolor(quiet))
    pal.setColor(I, QPalette.ColorRole.HighlightedText,
                 to_qcolor(_cs.ensure_contrast(L(c.highlighted_text), _cs._composite(quiet, base), 4.5)))

    # --- Disabled: fills fade toward the window, text stays legible on them.
    D = QPalette.ColorGroup.Disabled
    target = _DISABLED_TARGET
    d_base = _cs.mix(base, win, 0.5)
    d_button = _cs.mix(button, win, 0.5)
    d_high = _cs.mix(L(c.highlight), win, 0.6)
    pal.setColor(D, QPalette.ColorRole.Window, window)
    pal.setColor(D, QPalette.ColorRole.Base, to_qcolor(d_base))
    pal.setColor(D, QPalette.ColorRole.AlternateBase, to_qcolor(_cs.mix(L(c.alternate_base), win, 0.5)))
    pal.setColor(D, QPalette.ColorRole.Button, to_qcolor(d_button))
    pal.setColor(D, QPalette.ColorRole.Highlight, to_qcolor(d_high))
    if _ACCENT_ROLE is not None:
        pal.setColor(D, _ACCENT_ROLE, to_qcolor(_cs.mix(L(c.accent_color), win, 0.6)))
    dis = L(c.disabled_text)

    def legible(surface):
        # A translucent disabled text (some themes use alpha ~85) can't
        # reach the floor by lightness alone: flatten it onto its surface
        # first -- the same colour there -- then adjust.
        return to_qcolor(_cs.ensure_contrast(_cs._composite(dis, surface), surface, target))

    for role, surface in ((QPalette.ColorRole.WindowText, win), (QPalette.ColorRole.Text, d_base),
                          (QPalette.ColorRole.ButtonText, d_button),
                          (QPalette.ColorRole.HighlightedText, d_high),
                          (QPalette.ColorRole.PlaceholderText, d_base)):
        pal.setColor(D, role, legible(surface))


def build_tooltip_palette(
    base_palette: Optional[QPalette] = None,
    colors: Optional[DockThemeColors] = None,
) -> QPalette:
    """Build a :class:`QPalette` carrying the theme's tooltip colors.

    Qt renders tooltips in a top-level ``QTipLabel`` that reads its palette
    from ``QToolTip::palette()`` (cached the first time a tooltip is shown) —
    never from the widget that triggered the tooltip, and never from the
    application palette alone.  Hand the result to ``QToolTip.setPalette()``
    whenever a theme is applied so every tooltip in the app follows it.
    """
    c = colors or resolve_dock_colors()
    pal = QPalette(base_palette) if base_palette else QPalette()
    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive):
        pal.setColor(group, QPalette.ColorRole.ToolTipBase, c.tooltip_bg)
        pal.setColor(group, QPalette.ColorRole.ToolTipText, c.tooltip_text)
    return pal