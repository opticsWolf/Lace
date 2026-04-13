# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0

dock_palette_bridge — Single source of truth for dock widget palette construction
=================================================================================

Resolves colours from ``DockStyleManager`` and builds a ``QPalette``
that the ``DockThemeBridge`` applies to the dock manager (or the
whole QApplication) so that standard Qt children — spinboxes, combos,
line-edits, tree-views embedded inside dock panels — match the active
dock theme without per-widget stylesheet overrides.

Architecture mirrors Weave's ``palette_bridge.py``:

    DockStyleManager → resolve_dock_colors() → DockThemeColors
                                                    │
                                                    ▼
                                         build_dock_palette()
                                                    │
                                                    ▼
                                           QPalette applied to
                                          DockManager / QApplication

The palette maps dock style tokens to Qt ``QPalette`` roles:

    Window        ← CORE.canvas_bg      (panel/dock background)
    WindowText    ← CORE.text_color
    Base          ← canvas_bg darkened   (input field backgrounds)
    AlternateBase ← Base darkened further
    Text          ← CORE.text_color
    Button        ← TAB.bg_normal       (button faces)
    ButtonText    ← CORE.text_color
    Highlight     ← CORE.accent_color   (selection / focus)
    HighlightedText ← white
    Mid / Light / Dark / Shadow ← derived structural colours
    Disabled roles              ← CORE.disabled_text_color
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PySide6.QtGui import QPalette, QColor

from .dock_style_manager import get_dock_style_manager
from .dock_theme import DockStyleCategory


# ══════════════════════════════════════════════════════════════════════════════
# Resolved dock theme colours
# ══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class DockThemeColors:
    """All resolved colours needed to build a dock widget palette.

    Consumers should treat this as read-only.  Call
    ``resolve_dock_colors()`` to get a fresh snapshot whenever the
    active theme may have changed.
    """
    canvas_bg:        QColor  # 1. The deep background (gaps/outside)
    title_bg:         QColor  # 2. The title bars and tabs
    panel_bg:         QColor  # 3. The inside of the dock widgets
    text_color:       QColor
    accent_color:     QColor
    border_color:     QColor
    input_bg:         QColor  # 4. Input field backgrounds (Base role)
    alternate_base:   QColor  # 5. Alternating row color for tables/lists
    button_bg:        QColor  # 6. Button face background
    color_light:      QColor  # 7. 3D highlight edge
    color_mid:        QColor  # 8. 3D mid-tone border
    color_dark:       QColor  # 9. 3D shadow edge
    color_shadow:     QColor  # 10. Drop shadow
    disabled_text:    QColor
    placeholder_text: QColor


def resolve_dock_colors() -> DockThemeColors:
    sm = get_dock_style_manager()

    canvas_bg = to_qcolor(sm.get(DockStyleCategory.CORE, "canvas_bg", [20, 20, 20]))
    title_bg = to_qcolor(sm.get(DockStyleCategory.TITLE_BAR, "bg_normal", [37, 37, 38]))
    panel_bg = to_qcolor(sm.get(DockStyleCategory.PANEL, "bg_normal", [30, 30, 30]))
    text_color = to_qcolor(sm.get(DockStyleCategory.CORE, "text_color", [204, 204, 204]))
    accent = to_qcolor(sm.get(DockStyleCategory.CORE, "accent_color", [0, 120, 212]))
    border = to_qcolor(sm.get(DockStyleCategory.CORE, "border_color", [45, 45, 45]))
    
    # Input backgrounds - fetch from theme or derive sensible fallbacks
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
    
    # Button background
    button_bg_raw = sm.get(DockStyleCategory.PANEL, "button_bg")
    if button_bg_raw:
        button_bg = to_qcolor(button_bg_raw)
    else:
        button_bg = QColor(panel_bg).lighter(120)
    
    # 3D structural colors
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

    return DockThemeColors(
        canvas_bg=canvas_bg, title_bg=title_bg, panel_bg=panel_bg,
        text_color=text_color, accent_color=accent, border_color=border,
        input_bg=input_bg, alternate_base=alternate_base,
        button_bg=button_bg, color_light=color_light, color_mid=color_mid,
        color_dark=color_dark, color_shadow=color_shadow,
        disabled_text=disabled_text, placeholder_text=placeholder_text
    )

def to_qcolor(val) -> QColor:
    if isinstance(val, QColor): return val
    if isinstance(val, (list, tuple)) and len(val) >= 3:
        return QColor(int(val[0]), int(val[1]), int(val[2]), int(val[3]) if len(val) > 3 else 255)
    return QColor(0, 0, 0, 255)


def _apply_shared_roles(pal: QPalette, c: DockThemeColors):
    """Applies palette roles that are identical across all dock contexts."""
    pal.setColor(QPalette.ColorRole.Highlight, c.accent_color)
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    pal.setColor(QPalette.ColorRole.ToolTipBase, c.title_bg)
    pal.setColor(QPalette.ColorRole.ToolTipText, c.text_color)
    pal.setColor(QPalette.ColorRole.PlaceholderText, c.placeholder_text)
    
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText, QPalette.ColorRole.ButtonText):
        pal.setColor(QPalette.ColorGroup.Disabled, role, c.disabled_text)


# ══════════════════════════════════════════════════════════════════════════════
# Palette construction
# ══════════════════════════════════════════════════════════════════════════════

def build_dock_palette(
    is_panel: bool = False, 
    base_palette: Optional[QPalette] = None, 
    colors: Optional[DockThemeColors] = None
) -> QPalette:
    """
    Constructs a QPalette for the docking system.
    
    Parameters
    ----------
    is_panel : bool
        If True, builds the palette for the inside of DockWidgets.
        If False, builds the CORE palette for splitters and gaps.
    """
    c = colors or resolve_dock_colors()
    pal = QPalette(base_palette) if base_palette else QPalette()

    # Only Window background varies depending on whether we are styling 
    # the deep gaps (CORE) or the raised panel faces (PANEL).
    primary_bg = c.panel_bg if is_panel else c.canvas_bg

    # 1. Window & Text
    pal.setColor(QPalette.ColorRole.Window, primary_bg)
    pal.setColor(QPalette.ColorRole.WindowText, c.text_color)

    # 2. Inputs (Base) & Alternate Base
    # CRITICAL FIX: Standard input widgets (QTextEdit, lists) live inside panels.
    # Even in the CORE palette, their Base must be derived from panel_bg to prevent
    # the canvas gap color from "bleeding" through if palette inheritance breaks.
    pal.setColor(QPalette.ColorRole.Base, c.input_bg)
    pal.setColor(QPalette.ColorRole.AlternateBase, c.alternate_base)
    pal.setColor(QPalette.ColorRole.Text, c.text_color)

    # 3. Buttons
    pal.setColor(QPalette.ColorRole.Button, c.button_bg)
    pal.setColor(QPalette.ColorRole.ButtonText, c.text_color)

    # 4. Structural Roles (Mid, Light, Dark, Shadow)
    # Used for 3D borders of standard widgets like spinboxes, scrollbars, frames
    pal.setColor(QPalette.ColorRole.Light, c.color_light)
    pal.setColor(QPalette.ColorRole.Mid, c.color_mid)
    pal.setColor(QPalette.ColorRole.Dark, c.color_dark)
    pal.setColor(QPalette.ColorRole.Shadow, c.color_shadow)

    _apply_shared_roles(pal, c)
    return pal