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
    canvas_bg:        QColor
    panel_bg:         QColor
    text_color:       QColor
    accent_color:     QColor
    border_color:     QColor
    input_bg:         QColor
    disabled_text:    QColor
    placeholder_text: QColor


def resolve_dock_colors() -> DockThemeColors:
    """Fetch and resolve the colours required for palette construction
    from the current ``DockStyleManager`` state."""
    sm = get_dock_style_manager()

    canvas_bg = sm.get(DockStyleCategory.CORE, "canvas_bg")
    text_color = sm.get(DockStyleCategory.CORE, "text_color")
    accent = sm.get(DockStyleCategory.CORE, "accent_color")
    border = sm.get(DockStyleCategory.CORE, "border_color")
    panel_bg = sm.get(DockStyleCategory.TITLE_BAR, "bg_normal")

    # Defensive defaults if schema values are missing
    if not isinstance(canvas_bg, QColor):
        canvas_bg = QColor(30, 30, 30)
    if not isinstance(text_color, QColor):
        text_color = QColor(204, 204, 204)
    if not isinstance(accent, QColor):
        accent = QColor(0, 120, 212)
    if not isinstance(border, QColor):
        border = QColor(45, 45, 45)
    if not isinstance(panel_bg, QColor):
        panel_bg = QColor(37, 37, 38)

    input_bg = QColor(canvas_bg).darker(115)

    disabled_text = QColor(text_color)
    disabled_text.setAlpha(max(0, text_color.alpha() // 3))

    placeholder_text = QColor(text_color)
    placeholder_text.setAlpha(max(0, text_color.alpha() // 2))

    return DockThemeColors(
        canvas_bg=canvas_bg,
        panel_bg=panel_bg,
        text_color=text_color,
        accent_color=accent,
        border_color=border,
        input_bg=input_bg,
        disabled_text=disabled_text,
        placeholder_text=placeholder_text,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Palette construction
# ══════════════════════════════════════════════════════════════════════════════

def build_dock_palette(
    window_color: Optional[QColor] = None,
    base_palette: Optional[QPalette] = None,
    colors: Optional[DockThemeColors] = None,
) -> QPalette:
    """Construct a ``QPalette`` from the current dock theme.

    Parameters
    ----------
    window_color : QColor, optional
        Override for the ``Window`` role.  Defaults to ``colors.canvas_bg``.
    base_palette : QPalette, optional
        Starting palette.  ``None`` creates a fresh ``QPalette``.
    colors : DockThemeColors, optional
        Pre-resolved colours.  ``None`` calls ``resolve_dock_colors()``.
    """
    if colors is None:
        colors = resolve_dock_colors()
    c = colors

    pal = QPalette(base_palette) if base_palette else QPalette()
    win = window_color if window_color is not None else c.canvas_bg

    # Window — dock panel backgrounds
    pal.setColor(QPalette.ColorRole.Window, win)
    pal.setColor(QPalette.ColorRole.WindowText, c.text_color)

    # Interactive leaf widgets (spinboxes, combos, line-edits inside docks)
    pal.setColor(QPalette.ColorRole.Base, c.input_bg)
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(c.input_bg).darker(110))
    pal.setColor(QPalette.ColorRole.Text, c.text_color)

    pal.setColor(QPalette.ColorRole.Button, c.panel_bg)
    pal.setColor(QPalette.ColorRole.ButtonText, c.text_color)

    # Selection / focus — accent colour
    pal.setColor(QPalette.ColorRole.Highlight, c.accent_color)
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))

    pal.setColor(QPalette.ColorRole.ToolTipBase, c.panel_bg)
    pal.setColor(QPalette.ColorRole.ToolTipText, c.text_color)

    pal.setColor(QPalette.ColorRole.PlaceholderText, c.placeholder_text)

    # Structural roles — frame edges, sunken/raised borders
    pal.setColor(QPalette.ColorRole.Mid, c.border_color)
    pal.setColor(QPalette.ColorRole.Light, QColor(c.panel_bg).lighter(140))
    pal.setColor(QPalette.ColorRole.Dark, QColor(c.panel_bg).darker(130))
    pal.setColor(QPalette.ColorRole.Shadow, QColor(0, 0, 0, 80))

    # Disabled state
    for role in (QPalette.ColorRole.Text,
                 QPalette.ColorRole.WindowText,
                 QPalette.ColorRole.ButtonText):
        pal.setColor(QPalette.ColorGroup.Disabled, role, c.disabled_text)

    return pal
