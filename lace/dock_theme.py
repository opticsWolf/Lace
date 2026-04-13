# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0
"""

import colorsys
import enum
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Union
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

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
class DockCoreStyleSchema:
    """Global colors and palette basics for the dock system."""
    canvas_bg: Optional[List[int]] = None    #App / Window main background
    border_color: Optional[List[int]] = None #Dock Area Widget Accent accent / highlight color
    accent_color: Optional[List[int]] = None #App / Window Accent accent / highlight color
    focus_border_color: Optional[List[int]] = None

    # Geometry
    border_width: float = 0.0 #Dock Area Widget border
    corner_radius: int = 2.0 #Dock Area Widget corner radius
    margin: int = 0 #to be kept at zero
    padding: int = 0 #probably not even used, need to check or connect

    # Typography
    text_color: Optional[List[int]] = None
    disabled_text_color: Optional[List[int]] = None
    font_family: str = "Segoe UI"
    font_size: int = 10
    font_weight: Union[str, int, QFont.Weight] = "normal"
    font_italic: bool = False
    font_underline: bool = False

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

@dataclass
class DockTabStyleSchema:
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

    # Typography
    text_normal: Optional[List[int]] = None
    text_active: Optional[List[int]] = None
    font_family: str = "Segoe UI"
    font_size: int = 10
    font_weight: Union[str, int, QFont.Weight] = "normal"
    active_font_weight: Union[str, int, QFont.Weight] = "normal"
    font_italic: bool = False
    font_underline: bool = False

    # Visual Indicators
    indicator_color: Optional[List[int]] = None
    indicator_width: int = 2
    indicator_position: str = "bottom"   # "top" or "bottom"

    # Action Buttons
    close_btn_color: Optional[List[int]] = None
    close_btn_bg_hover: Optional[List[int]] = None
    close_btn_bg_disable: Optional[List[int]] = None
    close_btn_size: int = 20
    close_btn_icon_size: int = 16
    close_btn_corner_radius: int = 3


@dataclass
class DockTitleBarStyleSchema:
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
    padding_left: int = 2
    padding_right: int = 6
    padding_top: int = 0
    border_width: float = 0.0
    corner_radius: int = 0
    padding: int = 4 #distance for the tab from edge
    margin: int = 0

    # Typography
    text_normal: Optional[List[int]] = None
    text_active: Optional[List[int]] = None
    font_family: str = "Segoe UI"
    font_size: int = 10
    font_weight: Union[str, int, QFont.Weight] = "bold"
    font_italic: bool = False
    font_underline: bool = False

    # Action Buttons (unified with overlay)
    button_color: Optional[List[int]] = None
    button_disable_clr: Optional[List[int]] = None
    button_hover_bg: Optional[List[int]] = None
    button_corner_radius: int = 3
    button_padding: int = 2
    button_expand_vertical: bool = False
    button_size: int = 18
    button_icon_size: int = 16
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

@dataclass
class DockSidePanelStyleSchema:
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
    

    # Action Buttons (unified with title bar)
    button_color: Optional[List[int]] = None
    button_disable_clr: Optional[List[int]] = None
    button_hover_bg: Optional[List[int]] = None
    button_corner_radius: int = 3
    button_padding: int = 2
    button_expand_vertical: bool = False
    button_size: int = 18
    button_icon_size: int = 16
    button_spacing: int = 2

    # Panel geometry
    corner_radius: int = 0
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

def _build_theme(
    base: list, 
    accent: list, 
    text: list, 
    is_light: bool = False,
    title_mode: str = "darker", # "lighter" or "darker" relative to panel
    hover_mode: str = "lighter"    # "lighter" or "darker" relative to panel
) -> Dict[DockStyleCategory, Dict[str, Any]]:
    """
    Build a complete dock theme from 3 primary colors.
    
    Args:
        base:     Darkest background color [R, G, B, A]
        accent:   Primary accent/highlight color [R, G, B, A]
        text:     Primary text color [R, G, B, A]
        is_light: If True, adjustments go darker instead of lighter
    """
    # Direction multiplier: light themes darken, dark themes lighten
    d = -1 if is_light else 1
    
    if title_mode == "darker":
        t_mode = -1.0
    else:
        t_mode = 1.0
    
    if hover_mode == "darker":
        h_mode = -1.0
    else:
        h_mode = 1.0
    
    # === DERIVED BACKGROUNDS ===
    _panel      = _adjust_color(base, l_off=d * 0.10)
    _title_bg   =  _adjust_color(_panel, l_off= h_mode * d * 0.05)
    _surface    = _adjust_color(base, l_off=d * 0.05)
    _hover      = _adjust_color(base, l_off= h_mode * d * 0.20)
    _hover_end  = _adjust_color(base, l_off= h_mode * d * 0.12)
    _btn_hover  = _adjust_color(base, l_off= h_mode * d * 0.15)
    
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
    
    # === UTILITY ===
    _transparent = [0, 0, 0, 0]
    _shadow      = [0, 0, 0, 64 if not is_light else 32]
    
    return {
        DockStyleCategory.CORE: {
            "canvas_bg":          base,
            "border_color":       _adjust_color(base, l_off=-0.02),
            "accent_color":       accent,
            "focus_border_color": _accent_bright,
            "text_color":         text,
            "disabled_text_color": _text_disabled,
        },
        DockStyleCategory.PANEL: {
            "bg_normal":          _panel,
            "text_color":         text,
            "input_bg":           _input_bg,
            "alternate_base":     _alternate_base,
            "button_bg":          _button_bg,
            "color_light":        _color_light,
            "color_mid":          _color_mid,
            "color_dark":         _color_dark,
            "color_shadow":       _color_shadow,
        },
        DockStyleCategory.SIDEBAR: {
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
        },
        DockStyleCategory.SIDEPANEL: {
            "bg_normal":          _panel,
            "title_text_color":   text,
            "button_color":       _text_muted,
            "button_disable_clr": _btn_disabled,
            "button_hover_bg":    _btn_hover,
            "shadow_color":       _shadow,
        },
        DockStyleCategory.TAB: {
            "bg_normal":          _title_bg,
            "bg_hover":           _hover,
            "bg_active":          _panel,
            "text_normal":        _text_muted,
            "text_active":        _text_active,
            "indicator_color":    accent,
            "close_btn_color":    _text_muted,
            "close_btn_bg_hover": _btn_hover,
            "close_btn_bg_disable": _btn_disabled,
            "title_text_color":   text,
        },
        DockStyleCategory.TITLE_BAR: {
            "bg_normal":          _title_bg,
            "bg_active":          _title_bg,
            "text_normal":        _text_muted,
            "text_active":        _text_active,
            "active_edge_color":  _accent_bright,
            "button_color":       _text_muted,
            "button_disable_clr": _btn_disabled,
            "button_hover_bg":    _btn_hover,
        },
        DockStyleCategory.SPLITTER: {
            "handle_color":       base,
            "handle_hover_color": accent,
        },
        DockStyleCategory.OVERLAY: {
            "frame_color":        _accent_bright,
            "background_color":   _panel,
            "overlay_color":      _accent_dim,
            "arrow_color":        text,
            "shadow_color":       _shadow,
        },
    }
# -------------------------------------------------------------------------
# Color Helper
# -------------------------------------------------------------------------
def _adjust_color(col, l_off=0, s_off=0, h_off=0, a_off=0):
    # Normalize input and separate alpha
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
BASE_DOCK_DEFAULTS: Dict[DockStyleCategory, Dict[str, Any]] = _build_theme(
    base   = [20, 20, 20, 255],
    accent = [0, 120, 212, 255],
    text   = [204, 204, 204, 255],
)