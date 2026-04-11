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
from .dock_theme import DockStyleCategory, BASE_DOCK_DEFAULTS


DOCK_THEMES: Dict[str, Dict[DockStyleCategory, Dict[str, Any]]] = {


    "dark": {},  # Empty dict defaults back to BASE_DOCK_DEFAULTS (VS Code 2026 Dark)

    # -------------------------------------------------------------------------
    # VS CODE LIGHT
    # -------------------------------------------------------------------------    
    "light": {
        DockStyleCategory.CORE: {
            "canvas_bg":          [238, 238, 238, 255], # Darker gray for splitters/gaps
            "border_color":       [204, 204, 204, 255],
            "accent_color":       [0, 120, 212, 255],
            "focus_border_color": [0, 120, 212, 255],
            "text_color":         [51, 51, 51, 255],
            "disabled_text_color":[160, 160, 160, 255],
        },
        DockStyleCategory.PANEL: {
            "bg_normal":          [255, 255, 255, 255], # Pure white panels
            "text_color":         [51, 51, 51, 255],
        },
        DockStyleCategory.SIDEBAR: {
            "bg_color":           [238, 238, 238, 255],
            "tab_bg_normal":      [0, 0, 0, 0],
            "tab_bg_hover_start": [218, 218, 218, 255],
            "tab_bg_hover_end":   [224, 224, 224, 255],
            "tab_bg_active":      [255, 255, 255, 255],
            "tab_text_normal":    [110, 110, 110, 255],
            "tab_text_active":    [51, 51, 51, 255],
            "indicator_color":    [0, 120, 212, 255],
            "badge_bg":           [0, 120, 212, 255],
            "badge_text":         [255, 255, 255, 255],
        },
        DockStyleCategory.TAB: {
            "bg_normal":          [238, 238, 238, 255],
            "bg_hover":           [228, 228, 228, 255],
            "bg_active":          [255, 255, 255, 255],
            "text_normal":        [110, 110, 110, 255],
            "text_active":        [51, 51, 51, 255],
            "indicator_color":    [0, 120, 212, 255],
            "close_btn_color":    [110, 110, 110, 255],
            "close_btn_bg_hover": [198, 198, 198, 255],
        },
        DockStyleCategory.TITLE_BAR: {
            "bg_normal":          [246, 246, 246, 255], # Distinct header gray
            "bg_active":          [246, 246, 246, 255],
            "text_normal":        [110, 110, 110, 255],
            "text_active":        [51, 51, 51, 255],
            "active_edge_color":  [0, 120, 212, 255],
            "button_color":       [110, 110, 110, 255],
            "button_hover_bg":    [198, 198, 198, 255],
        },
        DockStyleCategory.SPLITTER: {
            "handle_color":       [204, 204, 204, 255],
            "handle_hover_color": [0, 120, 212, 255],
        },
        DockStyleCategory.OVERLAY: {
            "frame_color":        [0, 120, 212, 255],
            "background_color":   [255, 255, 255, 255],
            "overlay_color":      [0, 120, 212, 48],
            "arrow_color":        [51, 51, 51, 255],
            "shadow_color":       [0, 0, 0, 32],
            "title_text_color":   [51, 51, 51, 255],
            "button_color":       [110, 110, 110, 255],
            "button_hover_bg":    [198, 198, 198, 255],
        },
    },

    # -------------------------------------------------------------------------
    # MIDNIGHT (Deep Blue)
    # -------------------------------------------------------------------------
    "midnight": {
        DockStyleCategory.CORE: {
            "canvas_bg":          [15, 17, 26, 255], # Deepest dark blue gap
            "border_color":       [30, 33, 45, 255],
            "accent_color":       [82, 110, 228, 255],
            "focus_border_color": [82, 110, 228, 255],
            "text_color":         [215, 220, 230, 255],
            "disabled_text_color":[90, 100, 115, 255],
        },
        DockStyleCategory.PANEL: {
            "bg_normal":          [24, 26, 35, 255], # Raised panel face
            "text_color":         [215, 220, 230, 255],
        },
        DockStyleCategory.SIDEBAR: {
            "bg_color":           [15, 17, 26, 255],
            "tab_bg_normal":      [0, 0, 0, 0],
            "tab_bg_hover_start": [35, 40, 55, 255],
            "tab_bg_hover_end":   [30, 34, 45, 255],
            "tab_bg_active":      [24, 26, 35, 255],
            "tab_text_normal":    [140, 150, 170, 255],
            "tab_text_active":    [255, 255, 255, 255],
            "indicator_color":    [82, 110, 228, 255],
            "badge_bg":           [82, 110, 228, 255],
            "badge_text":         [255, 255, 255, 255],
        },
        DockStyleCategory.TAB: {
            "bg_normal":          [20, 22, 30, 255],
            "bg_hover":           [35, 40, 55, 255],
            "bg_active":          [24, 26, 35, 255],
            "text_normal":        [140, 150, 170, 255],
            "text_active":        [255, 255, 255, 255],
            "indicator_color":    [82, 110, 228, 255],
            "close_btn_color":    [140, 150, 170, 255],
            "close_btn_bg_hover": [50, 55, 75, 255],
        },
        DockStyleCategory.TITLE_BAR: {
            "bg_normal":          [20, 22, 30, 255],
            "bg_active":          [20, 22, 30, 255],
            "text_normal":        [140, 150, 170, 255],
            "text_active":        [255, 255, 255, 255],
            "active_edge_color":  [82, 110, 228, 255],
            "button_color":       [140, 150, 170, 255],
            "button_hover_bg":    [50, 55, 75, 255],
        },
        DockStyleCategory.SPLITTER: {
            "handle_color":       [30, 33, 45, 255],
            "handle_hover_color": [82, 110, 228, 255],
        },
        DockStyleCategory.OVERLAY: {
            "frame_color":        [82, 110, 228, 255],
            "background_color":   [24, 26, 35, 255],
            "overlay_color":      [82, 110, 228, 64],
            "arrow_color":        [215, 220, 230, 255],
            "shadow_color":       [0, 0, 0, 80],
            "title_text_color":   [215, 220, 230, 255],
            "button_color":       [215, 220, 230, 255],
            "button_hover_bg":    [50, 55, 75, 255],
        },
    },

    # -------------------------------------------------------------------------
    # NORDIC (Arctic Frost)
    # -------------------------------------------------------------------------
    "nordic": {
        DockStyleCategory.CORE: {
            "canvas_bg":          [46, 52, 64, 255], # Deep background
            "border_color":       [59, 66, 82, 255],
            "accent_color":       [136, 192, 208, 255],
            "focus_border_color": [129, 161, 193, 255],
            "text_color":         [236, 239, 244, 255],
            "disabled_text_color":[76, 86, 106, 255],
        },
        DockStyleCategory.PANEL: {
            "bg_normal":          [59, 66, 82, 255], # Raised panel
            "text_color":         [236, 239, 244, 255],
        },
        DockStyleCategory.SIDEBAR: {
            "bg_color":           [46, 52, 64, 255],
            "tab_bg_normal":      [0, 0, 0, 0],
            "tab_bg_hover_start": [67, 76, 94, 255],
            "tab_bg_active":      [59, 66, 82, 255],
            "tab_text_normal":    [144, 154, 172, 255],
            "tab_text_active":    [236, 239, 244, 255],
            "indicator_color":    [136, 192, 208, 255],
        },
        DockStyleCategory.TAB: {
            "bg_normal":          [46, 52, 64, 255],
            "bg_hover":           [67, 76, 94, 255],
            "bg_active":          [59, 66, 82, 255],
            "text_normal":        [144, 154, 172, 255],
            "text_active":        [236, 239, 244, 255],
            "indicator_color":    [136, 192, 208, 255],
        },
        DockStyleCategory.TITLE_BAR: {
            "bg_normal":          [67, 76, 94, 255], # Distinct header
            "bg_active":          [67, 76, 94, 255],
            "text_active":        [216, 222, 233, 255],
            "active_edge_color":  [136, 192, 208, 255],
        },
        DockStyleCategory.SPLITTER: {
            "handle_color":       [59, 66, 82, 255],
            "handle_hover_color": [136, 192, 208, 255],
        },
    },

    # -------------------------------------------------------------------------
    # MONOKAI PRO (Vibrant Dark)
    # -------------------------------------------------------------------------
    "monokai": {
        DockStyleCategory.CORE: {
            "canvas_bg":          [25, 23, 26, 255], # FIXED: Deep background is now darker
            "border_color":       [34, 31, 34, 255],
            "accent_color":       [255, 216, 102, 255], # Yellow
            "focus_border_color": [255, 97, 136, 255],  # Pink
            "text_color":         [252, 252, 250, 255],
            "disabled_text_color":[114, 112, 114, 255],
        },
        DockStyleCategory.PANEL: {
            "bg_normal":          [45, 42, 46, 255], # FIXED: Panel is raised/lighter
            "text_color":         [252, 252, 250, 255],
        },
        DockStyleCategory.SIDEBAR: {
            "bg_color":           [25, 23, 26, 255],
            "tab_bg_active":      [45, 42, 46, 255],
            "tab_text_normal":    [147, 146, 147, 255],
            "indicator_color":    [169, 220, 118, 255], # Green
        },
        DockStyleCategory.TAB: {
            "bg_normal":          [34, 31, 34, 255],
            "bg_active":          [45, 42, 46, 255],
            "text_normal":        [147, 146, 147, 255],
            "indicator_color":    [255, 216, 102, 255],
        },
        DockStyleCategory.TITLE_BAR: {
            "bg_normal":          [34, 31, 34, 255],
            "bg_active":          [34, 31, 34, 255],
            "text_active":        [252, 252, 250, 255],
            "active_edge_color":  [255, 216, 102, 255],
        },
        DockStyleCategory.OVERLAY: {
            "frame_color":        [120, 220, 232, 255], # Cyan
            "overlay_color":      [120, 220, 232, 40],
            "arrow_color":        [252, 252, 250, 255],
        },
    },

    # -------------------------------------------------------------------------
    # WARM (Earthy / Gruvbox)
    # -------------------------------------------------------------------------
    "warm": {
        DockStyleCategory.CORE: {
            "canvas_bg":          [43, 38, 35, 255], # Deep gap
            "border_color":       [58, 52, 48, 255],
            "accent_color":       [214, 136, 63, 255],
            "focus_border_color": [214, 136, 63, 255],
            "text_color":         [235, 219, 195, 255],
            "disabled_text_color":[130, 115, 105, 255],
        },
        DockStyleCategory.PANEL: {
            "bg_normal":          [54, 49, 46, 255], # Raised panel
            "text_color":         [235, 219, 195, 255],
        },
        DockStyleCategory.SIDEBAR: {
            "bg_color":           [43, 38, 35, 255],
            "tab_bg_normal":      [0, 0, 0, 0],
            "tab_bg_hover_start": [75, 68, 64, 255],
            "tab_bg_hover_end":   [65, 59, 55, 255],
            "tab_bg_active":      [54, 49, 46, 255],
            "tab_text_normal":    [180, 165, 150, 255],
            "tab_text_active":    [255, 245, 230, 255],
            "indicator_color":    [214, 136, 63, 255],
            "badge_bg":           [214, 136, 63, 255],
            "badge_text":         [255, 255, 255, 255],
        },
        DockStyleCategory.TAB: {
            "bg_normal":          [43, 38, 35, 255],
            "bg_hover":           [60, 54, 50, 255],
            "bg_active":          [54, 49, 46, 255],
            "text_normal":        [180, 165, 150, 255],
            "text_active":        [255, 245, 230, 255],
            "indicator_color":    [214, 136, 63, 255],
            "close_btn_color":    [180, 165, 150, 255],
            "close_btn_bg_hover": [90, 82, 77, 255],
        },
        DockStyleCategory.TITLE_BAR: {
            "bg_normal":          [43, 38, 35, 255],
            "bg_active":          [43, 38, 35, 255],
            "text_normal":        [180, 165, 150, 255],
            "text_active":        [255, 245, 230, 255],
            "active_edge_color":  [214, 136, 63, 255],
            "button_color":       [180, 165, 150, 255],
            "button_hover_bg":    [90, 82, 77, 255],
        },
        DockStyleCategory.SPLITTER: {
            "handle_color":       [58, 52, 48, 255],
            "handle_hover_color": [214, 136, 63, 255],
        },
        DockStyleCategory.OVERLAY: {
            "frame_color":        [214, 136, 63, 255],
            "background_color":   [54, 49, 46, 255],
            "overlay_color":      [214, 136, 63, 64],
            "arrow_color":        [235, 219, 195, 255],
            "shadow_color":       [0, 0, 0, 80],
            "title_text_color":   [235, 219, 195, 255],
            "button_color":       [235, 219, 195, 255],
            "button_hover_bg":    [90, 82, 77, 255],
        },
    },
}