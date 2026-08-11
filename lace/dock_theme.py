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
class DockCoreStyleSchema(_FontFields):
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
    corner_radius: int = 2.0 #Dock Area Widget corner radius
    margin: int = 0 #to be kept at zero
    padding: int = 0 #probably not even used, need to check or connect

    # Typography — font_* provided by _FontFields
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
    
    # Geometry
    border_width: float = 2.0
    corner_radius: int = 8
    padding: int = 0
    margin: int = 0
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
    border_color: Optional[List[int]] = None

    # Geometry
    border_width: float = 0.0
    corner_radius: int = 0
    padding: int = 10
    margin: int = 0

    # Typography — bare font_* provided by _FontFields; tabs add an active weight.
    text_normal: Optional[List[int]] = None
    text_active: Optional[List[int]] = None
    active_font_weight: Union[str, int, QFont.Weight] = "normal"

    # Visual Indicators
    indicator_color: Optional[List[int]] = None
    indicator_width: int = 2
    indicator_position: str = "bottom"   # "top" or "bottom"
    tab_dimming: bool = False

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
    bg_active: Optional[List[int]] = None
    border_color: Optional[List[int]] = None

    # Active Edge — colored strip on focused dock area (VS Code style)
    active_edge_color: Optional[List[int]] = None
    active_edge_width: int = 2

    # Geometry
    height: int = 30
    padding_left: int = 0
    padding_right: int = 6
    padding_top: int = 0
    border_width: float = 0.0
    # Bottom-edge rule under the title bar, drawn in border_color. Falls back
    # to border_width when 0. Fed by ThemeSpec.title_border_bottom.
    border_bottom: float = 0.0
    corner_radius: int = 0
    padding: int = 4 #distance for the tab from edge
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
    corner_radius: int = 0
    padding: int = 0
    margin: int = 0

    # Tab Buttons - Backgrounds
    tab_bg_normal: Optional[List[int]] = None
    tab_bg_hover_start: Optional[List[int]] = None
    tab_bg_hover_end: Optional[List[int]] = None
    tab_bg_active: Optional[List[int]] = None

    # Tab Buttons - Geometry
    tab_corner_radius: int = 4
    tab_padding: int = 8
    tab_margin: int = 2

    # Tab Buttons - Typography
    tab_text_normal: Optional[List[int]] = None
    tab_text_active: Optional[List[int]] = None
    tab_text_disabled: Optional[List[int]] = None
    tab_font_family: str = "Segoe UI"
    tab_font_size: int = 10
    tab_font_weight: Union[str, int, QFont.Weight] = "normal"
    tab_active_font_weight: Union[str, int, QFont.Weight] = "normal"
    tab_font_italic: bool = False
    tab_font_underline: bool = False

    # Highlights & Badges
    indicator_color: Optional[List[int]] = None
    indicator_width: int = 3
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
    is_light: bool = False
    title_mode: str = "darker"   # "darker" | "lighter" relative to panel
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
    title_margin: Optional[int] = None
    title_border_width: Optional[float] = None
    title_border_bottom: Optional[float] = None
    title_border_color: Optional[Union[QColor, List[int]]] = None
    tab_radius: Optional[int] = None
    tab_margin: Optional[int] = None
    content_margin: Optional[Union[int, float, List[int], Tuple[int, ...]]] = None
    tab_dimming: bool = False
    indicator_width: Optional[int] = None
    indicator_position: Optional[Union[str, List[str], Tuple[str, ...]]] = None

    # Tooltip colors — when omitted, derived from the panel/text seed colors.
    tooltip_bg: Optional[Union[QColor, List[int]]] = None
    tooltip_text: Optional[Union[QColor, List[int]]] = None


def _as_rgba(col: Union[QColor, List[int]]) -> List[int]:
    """Normalise a QColor or list to an ``[r, g, b, a]`` list for the colour math."""
    if isinstance(col, QColor):
        return [col.red(), col.green(), col.blue(), col.alpha()]
    return list(col)


def build_theme(spec: ThemeSpec) -> Dict[DockStyleCategory, Dict[str, Any]]:
    """Build a complete dock theme from a :class:`ThemeSpec` (public API)."""
    return _build_theme(
        _as_rgba(spec.base), _as_rgba(spec.accent), _as_rgba(spec.text),
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
        title_border_width=spec.title_border_width,
        title_border_bottom=spec.title_border_bottom,
        title_border_color=_as_rgba(spec.title_border_color) if spec.title_border_color is not None else None,
        tab_radius=spec.tab_radius,
        tab_margin=spec.tab_margin,
        content_margin=spec.content_margin,
        tab_dimming=spec.tab_dimming,
        indicator_width=spec.indicator_width,
        indicator_position=spec.indicator_position,
        tooltip_bg=_as_rgba(spec.tooltip_bg) if spec.tooltip_bg is not None else None,
        tooltip_text=_as_rgba(spec.tooltip_text) if spec.tooltip_text is not None else None,
    )


def _build_theme(
    base: list, 
    accent: list, 
    text: list, 
    is_light: bool = False,
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
    title_margin: Optional[int] = None,
    title_border_width: Optional[float] = None,
    title_border_bottom: Optional[float] = None,
    title_border_color: Optional[list] = None,
    tab_radius: Optional[int] = None,
    tab_margin: Optional[int] = None,
    content_margin: Optional[Union[int, float, List[int], Tuple[int, ...]]] = None,
    tab_dimming: bool = False,
    indicator_width: Optional[int] = None,
    indicator_position: Optional[Union[str, List[str], Tuple[str, ...]]] = None,
    tooltip_bg: Optional[list] = None,
    tooltip_text: Optional[list] = None,
) -> Dict[DockStyleCategory, Dict[str, Any]]:
    """
    Build a complete dock theme from 3 to 5 primary colors plus status tokens.
    
    Args:
        base:     Darkest background color [R, G, B, A]
        accent:   Primary accent/highlight color [R, G, B, A]
        text:     Primary text color [R, G, B, A]
        is_light: If True, adjustments go darker instead of lighter
        surface:  Optional inner content area background [R, G, B, A]
        border:   Optional structural border/divider color [R, G, B, A]
    """
    # Direction multiplier: light themes darken, dark themes lighten
    d = -1 if is_light else 1
    
    if title_mode == "darker":
        t_mode = -1.0
    else:
        t_mode = 1.0
    
    # hover_amount: "darker" mode yields a balanced subtle hover (8%), "lighter" mode yields clear tactile hover (12%)
    hover_amt = 0.08 if hover_mode == "darker" else 0.12
    
    # === DERIVED BACKGROUNDS ===
    _panel      = surface if surface is not None else _adjust_color(base, l_off=d * 0.10)
    _border     = border if border is not None else _adjust_color(base, l_off=-0.02)
    
    # Neutral border derived from surface or base depending on light/dark theme
    _ref_col        = _panel if surface is not None else base
    _neutral_border = border if border is not None else _adjust_color(_ref_col, l_off=(-0.12 if is_light else 0.08))
    _focus_border   = focus_border_color if focus_border_color is not None else (border if border is not None else _adjust_color(accent, l_off=0.15))
    
    # Title bar / header background: step darker (-0.06) or lighter (+0.06) relative to panel without double-inverting via d
    _title_bg   = _adjust_color(_panel, l_off= t_mode * 0.06)

    # Tooltip surface: a clearly-distinct step off the panel so the popup pops
    # against any surface (lighter on dark themes, darker on light themes);
    # text defaults to the full-strength seed text color.
    _tooltip_bg   = tooltip_bg if tooltip_bg is not None else _adjust_color(_panel, l_off=d * 0.09)
    _tooltip_text = tooltip_text if tooltip_text is not None else text
    
    # Interactive hovers: always step in the direction of high contrast (lighter on dark containers, darker on light containers)
    _hover      = _contrasting_hover(base, amount=hover_amt)
    _hover_end  = _contrasting_hover(base, amount=max(0.04, hover_amt * 0.65))
    _btn_hover  = _contrasting_hover(base, amount=hover_amt)

    # Button hover fill, resolved *relative to the container it sits on* so it always contrasts reliably.
    _btn_hover_title = _contrasting_hover(_title_bg, amount=hover_amt)
    _btn_hover_panel = _contrasting_hover(_panel, amount=hover_amt)

    # Input widget backgrounds (for QLineEdit, QTextEdit, tables, etc.)
    _input_bg       = _adjust_color(_panel, l_off=-d * 0.04)  # Slightly darker than panel
    _alternate_base = _adjust_color(_input_bg, l_off=d * 0.06)  # Visible contrast for zebra rows
    
    # Button face background
    _button_bg = _adjust_color(_panel, l_off=d * 0.08)
    
    # 3D structural colors (for widget borders, scrollbars, frames)
    _color_light  = _adjust_color(_panel, l_off=d * 0.15)   # Highlight edge
    _color_mid    = _adjust_color(_panel, l_off=-d * 0.05)  # Mid-tone border
    _color_dark   = _adjust_color(_panel, l_off=-d * 0.12)  # Shadow edge
    _color_shadow = [0, 0, 0, 72 if not is_light else 48]   # Drop shadow
    
    # === DERIVED TEXT ===
    _text_muted    = _adjust_color(text, l_off=-d * 0.10)
    _text_disabled = _adjust_color(text, l_off=-d * 0.30)
    _text_active   = _adjust_color(text, l_off=d * 0.20)
    
    # === BUTTON DISABLED (tinted with theme color) ===
    # Push base towards mid-gray while preserving hue tint
    _btn_disabled = _adjust_color(base, l_off=d * 0.20, s_off=0.05)
    
    # === ACCENT VARIANTS ===
    _accent_bright = _adjust_color(accent, l_off=0.15)
    _accent_dim    = _adjust_color(accent, a_off=-0.75)
    
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
        DockStyleCategory.SIDEBAR: _build_sidebar(base, accent, _panel, _hover, _hover_end, _text_muted, _text_active, _text_disabled, _transparent),
        DockStyleCategory.SIDEPANEL: _build_sidepanel(text, _panel, _text_muted, _btn_disabled, _btn_hover_panel, _shadow, _focus_border, _neutral_border),
        DockStyleCategory.TAB: _build_tab(text, accent, _title_bg, _panel, _hover, _text_muted, _text_active, _btn_disabled, _btn_hover_panel, _neutral_border),
        DockStyleCategory.TITLE_BAR: _build_titlebar(_title_bg, _text_muted, _text_active, _accent_bright, _btn_disabled, _btn_hover_title, _neutral_border),
        DockStyleCategory.SPLITTER: _build_splitter(base, accent),
        DockStyleCategory.OVERLAY: _build_overlay(text, _panel, _accent_bright, _accent_dim, _shadow),
    }

    if corner_radius is not None:
        theme[DockStyleCategory.CORE]["corner_radius"] = corner_radius
        theme[DockStyleCategory.PANEL]["corner_radius"] = corner_radius
        theme[DockStyleCategory.SIDEPANEL]["corner_radius"] = corner_radius
    if border_width is not None:
        theme[DockStyleCategory.CORE]["border_width"] = border_width
        theme[DockStyleCategory.PANEL]["border_width"] = border_width
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
    if tab_radius is not None:
        theme[DockStyleCategory.TAB]["corner_radius"] = tab_radius
    if tab_margin is not None:
        theme[DockStyleCategory.TAB]["margin"] = tab_margin
    if content_margin is not None:
        theme[DockStyleCategory.PANEL]["content_margin"] = content_margin

    theme[DockStyleCategory.TAB]["tab_dimming"] = tab_dimming
    if indicator_width is not None:
        theme[DockStyleCategory.TAB]["indicator_width"] = indicator_width
    if indicator_position is not None:
        theme[DockStyleCategory.TAB]["indicator_position"] = indicator_position

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


def _build_sidebar(base, accent, _panel, _hover, _hover_end, _text_muted, _text_active, _text_disabled, _transparent):
    return {
        "bg_color":           base,
        "tab_bg_normal":      _transparent,
        "tab_bg_hover_start": _hover,
        "tab_bg_hover_end":   _hover_end,
        "tab_bg_active":      _panel,
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
        "border_color":       _neutral_border,
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


def _build_titlebar(_title_bg, _text_muted, _text_active, _accent_bright, _btn_disabled, _btn_hover_title, _neutral_border):
    return {
        "bg_normal":          _title_bg,
        "bg_active":          _title_bg,
        "border_color":       _neutral_border,
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
    
    input_bg_raw = sm.get(DockStyleCategory.PANEL, "input_bg")
    if input_bg_raw:
        input_bg = to_qcolor(input_bg_raw)
    else:
        input_bg = QColor(panel_bg).darker(115)
    
    alternate_base_raw = sm.get(DockStyleCategory.PANEL, "alternate_base")
    if alternate_base_raw:
        alternate_base = to_qcolor(alternate_base_raw)
    else:
        alternate_base = QColor(input_bg).lighter(112)
    
    button_bg_raw = sm.get(DockStyleCategory.PANEL, "button_bg")
    if button_bg_raw:
        button_bg = to_qcolor(button_bg_raw)
    else:
        button_bg = QColor(panel_bg).lighter(120)
    
    color_light_raw = sm.get(DockStyleCategory.PANEL, "color_light")
    if color_light_raw:
        color_light = to_qcolor(color_light_raw)
    else:
        color_light = QColor(panel_bg).lighter(140)
    
    color_mid_raw = sm.get(DockStyleCategory.PANEL, "color_mid")
    if color_mid_raw:
        color_mid = to_qcolor(color_mid_raw)
    else:
        color_mid = QColor(panel_bg).darker(115)
    
    color_dark_raw = sm.get(DockStyleCategory.PANEL, "color_dark")
    if color_dark_raw:
        color_dark = to_qcolor(color_dark_raw)
    else:
        color_dark = QColor(panel_bg).darker(130)
    
    color_shadow_raw = sm.get(DockStyleCategory.PANEL, "color_shadow")
    if color_shadow_raw:
        color_shadow = to_qcolor(color_shadow_raw)
    else:
        color_shadow = QColor(0, 0, 0, 80)

    disabled_text = QColor(text_color)
    disabled_text.setAlpha(max(0, text_color.alpha() // 3))

    placeholder_text = QColor(text_color)
    placeholder_text.setAlpha(max(0, text_color.alpha() // 2))

    highlighted_text = _get_contrasting_text_color(accent)
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
        highlighted_text=highlighted_text, success_color=success,
        warning_color=warning, error_color=error, info_color=info,
        tooltip_bg=tooltip_bg, tooltip_text=tooltip_text
    )


def _apply_shared_roles(pal: QPalette, c: DockThemeColors):
    """Applies palette roles that are identical across all dock contexts."""
    pal.setColor(QPalette.ColorRole.Highlight, c.accent_color)
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
    """Constructs a QPalette for the docking system."""
    c = colors or resolve_dock_colors()
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
    return pal


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