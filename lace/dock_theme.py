# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0
"""

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
    border_width: float = 1.0 #Dock Area Widget border
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
    close_btn_size: int = 16
    close_btn_icon_size: int = 12
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
    height: int = 24
    border_width: float = 0.0
    corner_radius: int = 0
    padding: int = 4
    margin: int = 0

    # Typography
    text_normal: Optional[List[int]] = None
    text_active: Optional[List[int]] = None
    font_family: str = "Segoe UI"
    font_size: int = 10
    font_weight: Union[str, int, QFont.Weight] = "bold"
    font_italic: bool = False
    font_underline: bool = False

    # Action Buttons
    button_color: Optional[List[int]] = None
    button_hover_bg: Optional[List[int]] = None
    button_size: int = 20
    button_icon_size: int = 14
    button_spacing: int = 4
    button_corner_radius: int = 3


@dataclass
class DockSidebarStyleSchema:
    """Enhanced auto-hide sidebar styling."""
    # General Container
    width: int = 42
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
    tab_font_family: str = "Segoe UI"
    tab_font_size: int = 10
    tab_font_weight: Union[str, int, QFont.Weight] = "normal"
    tab_active_font_weight: Union[str, int, QFont.Weight] = "normal"
    tab_font_italic: bool = False
    tab_font_underline: bool = False

    # Highlights & Badges
    indicator_color: Optional[List[int]] = None
    indicator_width: int = 3

    badge_bg: Optional[List[int]] = None
    badge_text: Optional[List[int]] = None
    badge_font_family: str = "Segoe UI"
    badge_font_size: int = 8
    badge_font_weight: Union[str, int, QFont.Weight] = "bold"
    badge_radius: int = 6


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

    # Sidebar overlay panel
    title_text_color: Optional[List[int]] = None
    title_font_family: str = "Segoe UI"
    title_font_size: int = 10
    title_font_weight: Union[str, int, QFont.Weight] = "bold"
    button_color: Optional[List[int]] = None
    button_hover_bg: Optional[List[int]] = None
    button_corner_radius: int = 3
    corner_radius: int = 0
    shadow_blur_radius: int = 20


# ============================================================================
# BASE DEFAULTS  (VS Code 2026 Dark)
# ============================================================================

BASE_DOCK_DEFAULTS: Dict[DockStyleCategory, Dict[str, Any]] = {
    DockStyleCategory.CORE: {
        "canvas_bg":          [220, 20, 20, 255],
        "border_color":       [45, 45, 45, 255],
        "accent_color":       [0, 120, 212, 255],
        "focus_border_color": [0, 120, 212, 255],
        "text_color":         [204, 204, 204, 255],
        "disabled_text_color":[110, 110, 110, 255],

    },
    DockStyleCategory.PANEL: {
        "bg_normal":          [30, 30, 30, 255],
        "text_color":         [204, 204, 204, 255],
    },
    DockStyleCategory.SIDEBAR: {
        "bg_color":           [20, 20, 20, 255],
        "tab_bg_normal":      [0, 0, 0, 0],
        "tab_bg_hover_start": [51, 51, 51, 255],
        "tab_bg_hover_end":   [45, 45, 46, 255],
        "tab_bg_active":      [30, 30, 30, 255],
        "tab_text_normal":    [150, 150, 150, 255],
        "tab_text_active":    [255, 255, 255, 255],
        "indicator_color":    [0, 120, 212, 255],
        "badge_bg":           [0, 120, 212, 255],
        "badge_text":         [255, 255, 255, 255],

    },
    DockStyleCategory.TAB: {
        "bg_normal":          [37, 37, 38, 255],
        "bg_hover":           [44, 44, 45, 255],
        "bg_active":          [30, 30, 30, 255],
        "text_normal":        [150, 150, 150, 255],
        "text_active":        [255, 255, 255, 255],
        "indicator_color":    [0, 120, 212, 255],
        "close_btn_color":    [150, 150, 150, 255],
        "close_btn_bg_hover": [62, 62, 62, 255],
        "close_btn_corner_radius": 3,
    },
    DockStyleCategory.TITLE_BAR: {
        "bg_normal":          [37, 37, 38, 255],
        "bg_active":          [37, 37, 38, 255],
        "text_normal":        [150, 150, 150, 255],
        "text_active":        [255, 255, 255, 255],
        "active_edge_color":  [0, 120, 212, 255],
        "button_color":       [150, 150, 150, 255],
        "button_hover_bg":    [62, 62, 62, 255],
        "button_corner_radius": 3,
    },
    DockStyleCategory.SPLITTER: {
        "handle_color":       [20, 20, 20, 255],
        "handle_hover_color": [0, 120, 212, 255],

    },
    DockStyleCategory.OVERLAY: {
        "frame_color":        [0, 120, 212, 255],
        "background_color":   [37, 37, 38, 255],
        "overlay_color":      [0, 120, 212, 64],
        "arrow_color":        [204, 204, 204, 255],
        "shadow_color":       [0, 0, 0, 64],
        "title_text_color":   [204, 204, 204, 255],
        "button_color":       [204, 204, 204, 255],
        "button_hover_bg":    [62, 62, 62, 255],
    },
}
