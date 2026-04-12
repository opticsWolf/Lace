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

    "default": {},  # Empty dict defaults back to BASE_DOCK_DEFAULTS (VS Code 2026 Dark)    

    # -------------------------------------------------------------------------
    # DARK (Weave Default Base)
    # -------------------------------------------------------------------------
    "dark": {
        DockStyleCategory.CORE: {
            "canvas_bg":          [20, 23, 30, 255],    # From Weave Canvas bg_color
            "border_color":       [20, 20, 20, 255],    # From Weave Node outline_color
            "accent_color":       [32, 64, 128, 255],   # From Weave Node header_bg
            "focus_border_color": [60, 120, 200, 255],  # From Weave Node sel_border_color
            "text_color":         [200, 205, 215, 255], # From Weave Node body_text_color
            "disabled_text_color":[110, 110, 110, 255],
        },
        DockStyleCategory.PANEL: {
            "bg_normal":          [38, 41, 46, 255],    # From Weave Node body_bg
            "text_color":         [200, 205, 215, 255],
        },
        DockStyleCategory.SIDEBAR: {
            "bg_color":           [30, 33, 40, 255],
            "tab_bg_normal":      [0, 0, 0, 0],
            "tab_bg_hover_start": [50, 55, 62, 255],
            "tab_bg_hover_end":   [45, 48, 55, 255],
            "tab_bg_active":      [38, 41, 46, 255],
            "tab_text_normal":    [163, 166, 173, 255], # From Weave Minimap text_color
            "tab_text_active":    [224, 236, 255, 255], # From Weave Node title_text_color
            "indicator_color":    [32, 64, 128, 255],
            "badge_bg":           [32, 64, 128, 255],
            "badge_text":         [255, 255, 255, 255],
        },
        DockStyleCategory.TAB: {
            "bg_normal":          [30, 33, 40, 255],
            "bg_hover":           [45, 48, 55, 255],
            "bg_active":          [38, 41, 46, 255],
            "text_normal":        [150, 150, 150, 255],
            "text_active":        [224, 236, 255, 255],
            "indicator_color":    [60, 120, 200, 255],
            "close_btn_color":    [192, 195, 203, 192], # From Weave minimize_btn_normal
            "close_btn_bg_hover": [202, 205, 213, 224],
            "close_btn_bg_disable": [110, 110, 210, 255],
        },
        DockStyleCategory.TITLE_BAR: {
            "bg_normal":          [30, 33, 40, 255],
            "bg_active":          [30, 33, 40, 255],
            "text_normal":        [150, 150, 150, 255],
            "text_active":        [224, 236, 255, 255],
            "active_edge_color":  [60, 120, 200, 255],
            "button_color":       [150, 150, 150, 255],
            "button_hover_bg":    [62, 62, 62, 255],
        },
        DockStyleCategory.SPLITTER: {
            "handle_color":       [20, 23, 30, 255],
            "handle_hover_color": [32, 64, 128, 255],
        },
        DockStyleCategory.OVERLAY: {
            "frame_color":        [60, 120, 200, 255],
            "background_color":   [38, 41, 46, 255],
            "overlay_color":      [32, 64, 128, 64],
            "arrow_color":        [224, 236, 255, 255],
            "shadow_color":       [0, 0, 0, 64],
            "title_text_color":   [224, 236, 255, 255],
            "button_color":       [150, 150, 150, 255],
            "button_hover_bg":    [62, 62, 62, 255],
        },
    },

    # -------------------------------------------------------------------------
    # LIGHT (Weave Light)
    # -------------------------------------------------------------------------    
    "light": {
        DockStyleCategory.CORE: {
            "canvas_bg":          [230, 232, 235, 255], # From Weave Light Canvas
            "border_color":       [180, 185, 190, 255], # From Weave Light Node outline
            "accent_color":       [54, 81, 217, 255],   # From Weave Light Node header
            "focus_border_color": [54, 81, 217, 255],
            "text_color":         [50, 55, 65, 255],    # From Weave Light Node body text
            "disabled_text_color":[160, 160, 160, 255],
        },
        DockStyleCategory.PANEL: {
            "bg_normal":          [250, 252, 255, 255], # From Weave Light Node body_bg
            "text_color":         [50, 55, 65, 255],
        },
        DockStyleCategory.SIDEBAR: {
            "bg_color":           [240, 242, 245, 255],
            "tab_bg_normal":      [0, 0, 0, 0],
            "tab_bg_hover_start": [220, 225, 230, 255],
            "tab_bg_hover_end":   [210, 215, 220, 255],
            "tab_bg_active":      [250, 252, 255, 255],
            "tab_text_normal":    [80, 85, 95, 255],    # From Weave Light Minimap text
            "tab_text_active":    [30, 35, 40, 255],    # From Weave Light Node title text
            "indicator_color":    [54, 81, 217, 255],
            "badge_bg":           [54, 81, 217, 255],
            "badge_text":         [255, 255, 255, 255],
        },
        DockStyleCategory.TAB: {
            "bg_normal":          [240, 242, 245, 255],
            "bg_hover":           [230, 235, 240, 255],
            "bg_active":          [250, 252, 255, 255],
            "text_normal":        [110, 110, 110, 255],
            "text_active":        [30, 35, 40, 255],
            "indicator_color":    [54, 81, 217, 255],
            "close_btn_color":    [110, 110, 110, 255],
            "close_btn_bg_hover": [198, 198, 198, 255],
            "close_btn_bg_disable": [220, 220, 220, 255],
        },
        DockStyleCategory.TITLE_BAR: {
            "bg_normal":          [240, 242, 245, 255],
            "bg_active":          [240, 242, 245, 255],
            "text_normal":        [110, 110, 110, 255],
            "text_active":        [30, 35, 40, 255],
            "active_edge_color":  [54, 81, 217, 255],
            "button_color":       [110, 110, 110, 255],
            "button_hover_bg":    [198, 198, 198, 255],
        },
        DockStyleCategory.SPLITTER: {
            "handle_color":       [230, 232, 235, 255], # From Weave Light grid color
            "handle_hover_color": [54, 81, 217, 255],
        },
        DockStyleCategory.OVERLAY: {
            "frame_color":        [54, 81, 217, 255],
            "background_color":   [250, 252, 255, 255],
            "overlay_color":      [54, 81, 217, 48],
            "arrow_color":        [30, 35, 40, 255],
            "shadow_color":       [0, 0, 0, 32],
            "title_text_color":   [30, 35, 40, 255],
            "button_color":       [110, 110, 110, 255],
            "button_hover_bg":    [198, 198, 198, 255],
        },
    },

    # -------------------------------------------------------------------------
    # MIDNIGHT (Weave Midnight)
    # -------------------------------------------------------------------------
    "midnight": {
        DockStyleCategory.CORE: {
            "canvas_bg":          [10, 13, 20, 255],    # From Weave Midnight Canvas
            "border_color":       [10, 12, 18, 255],    # From Weave Midnight Node outline
            "accent_color":       [54, 81, 217, 255],   # From Weave Midnight Node header
            "focus_border_color": [54, 81, 217, 255],
            "text_color":         [200, 205, 220, 255], # From Weave Midnight body text
            "disabled_text_color":[90, 100, 115, 255],
        },
        DockStyleCategory.PANEL: {
            "bg_normal":          [22, 25, 32, 255],    # From Weave Midnight body_bg
            "text_color":         [200, 205, 220, 255],
        },
        DockStyleCategory.SIDEBAR: {
            "bg_color":           [15, 18, 25, 255],
            "tab_bg_normal":      [0, 0, 0, 0],
            "tab_bg_hover_start": [35, 40, 55, 255],
            "tab_bg_hover_end":   [30, 34, 45, 255],
            "tab_bg_active":      [22, 25, 32, 255],
            "tab_text_normal":    [140, 150, 170, 255],
            "tab_text_active":    [255, 255, 255, 255],
            "indicator_color":    [54, 81, 217, 255],
            "badge_bg":           [54, 81, 217, 255],
            "badge_text":         [255, 255, 255, 255],
        },
        DockStyleCategory.TAB: {
            "bg_normal":          [15, 18, 25, 255],
            "bg_hover":           [35, 40, 55, 255],
            "bg_active":          [22, 25, 32, 255],
            "text_normal":        [140, 150, 170, 255],
            "text_active":        [255, 255, 255, 255],
            "indicator_color":    [54, 81, 217, 255],
            "close_btn_color":    [140, 150, 170, 255],
            "close_btn_bg_hover": [50, 55, 75, 255],
            "close_btn_bg_disable": [40, 45, 60, 255],
        },
        DockStyleCategory.TITLE_BAR: {
            "bg_normal":          [15, 18, 25, 255],
            "bg_active":          [15, 18, 25, 255],
            "text_normal":        [140, 150, 170, 255],
            "text_active":        [255, 255, 255, 255],
            "active_edge_color":  [54, 81, 217, 255],
            "button_color":       [140, 150, 170, 255],
            "button_hover_bg":    [50, 55, 75, 255],
        },
        DockStyleCategory.SPLITTER: {
            "handle_color":       [10, 13, 20, 255],
            "handle_hover_color": [54, 81, 217, 255],
        },
        DockStyleCategory.OVERLAY: {
            "frame_color":        [54, 81, 217, 255],
            "background_color":   [22, 25, 32, 255],
            "overlay_color":      [54, 81, 217, 64],
            "arrow_color":        [200, 205, 220, 255],
            "shadow_color":       [0, 0, 0, 80],
            "title_text_color":   [200, 205, 220, 255],
            "button_color":       [200, 205, 220, 255],
            "button_hover_bg":    [50, 55, 75, 255],
        },
    },

    # -------------------------------------------------------------------------
    # WARM (Weave Warm)
    # -------------------------------------------------------------------------
    "warm": {
        DockStyleCategory.CORE: {
            "canvas_bg":          [35, 28, 25, 255],    # From Weave Warm Canvas
            "border_color":       [65, 55, 50, 255],    # From Weave Warm grid_color
            "accent_color":       [160, 90, 50, 255],   # From Weave Warm header_bg
            "focus_border_color": [200, 140, 80, 255],  # From Weave Warm sel_border
            "text_color":         [230, 220, 200, 255], # From Weave Warm body_text
            "disabled_text_color":[130, 115, 105, 255],
        },
        DockStyleCategory.PANEL: {
            "bg_normal":          [55, 48, 44, 255],    # From Weave Warm body_bg
            "text_color":         [230, 220, 200, 255],
        },
        DockStyleCategory.SIDEBAR: {
            "bg_color":           [45, 38, 35, 255],
            "tab_bg_normal":      [0, 0, 0, 0],
            "tab_bg_hover_start": [75, 68, 64, 255],
            "tab_bg_hover_end":   [65, 59, 55, 255],
            "tab_bg_active":      [55, 48, 44, 255],
            "tab_text_normal":    [173, 166, 163, 255], # From Weave Warm Minimap text
            "tab_text_active":    [255, 245, 230, 255], # From Weave Warm title text
            "indicator_color":    [160, 90, 50, 255],
            "badge_bg":           [160, 90, 50, 255],
            "badge_text":         [255, 255, 255, 255],
            "shadow_color":       [0, 0, 0, 80],
            "title_text_color":   [230, 220, 200, 255],
            "button_color":       [230, 220, 200, 255],
            "button_hover_bg":    [90, 82, 77, 255],
        },
        DockStyleCategory.TAB: {
            "bg_normal":          [45, 38, 35, 255],
            "bg_hover":           [60, 54, 50, 255],
            "bg_active":          [55, 48, 44, 255],
            "text_normal":        [180, 165, 150, 255],
            "text_active":        [255, 245, 230, 255],
            "indicator_color":    [160, 90, 50, 255],
            "close_btn_color":    [180, 165, 150, 255],
            "close_btn_bg_hover": [90, 82, 77, 255],
            "close_btn_bg_disable": [110, 110, 210, 255],
        },
        DockStyleCategory.TITLE_BAR: {
            "bg_normal":          [45, 38, 35, 255],
            "bg_active":          [45, 38, 35, 255],
            "text_normal":        [180, 165, 150, 255],
            "text_active":        [255, 245, 230, 255],
            "active_edge_color":  [200, 140, 80, 255],
            "button_color":       [180, 165, 150, 255],
            "button_hover_bg":    [90, 82, 77, 255],
        },
        DockStyleCategory.SPLITTER: {
            "handle_color":       [35, 28, 25, 255],
            "handle_hover_color": [160, 90, 50, 255],
        },
        DockStyleCategory.OVERLAY: {
            "frame_color":        [200, 140, 80, 255],
            "background_color":   [55, 48, 44, 255],
            "overlay_color":      [160, 90, 50, 64],
            "arrow_color":        [230, 220, 200, 255],
            "shadow_color":       [0, 0, 0, 80],
        },
    },
}