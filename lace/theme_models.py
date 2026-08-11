# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


"""Pydantic models for loading Lace themes from JSON files.

JSON theme files mirror the declarative :class:`~lace.dock_theme.ThemeSpec`
format (3-5 seed colors plus optional geometry/typography overrides), so the
full theme is derived the same way as the built-in presets.  Colours may be
written either as ``[r, g, b(, a)]`` lists or as ``"#rrggbb"`` / SVG name
strings.

Example ``my_theme.json``::

    {
        "name": "MyTheme",
        "base":   [14, 11, 28, 255],
        "accent": "#ff007f",
        "text":   [245, 245, 255, 255],
        "surface": [24, 19, 44, 255],
        "is_light": false,
        "corner_radius": 8,
        "tab_dimming": true
    }

Load and apply::

    from lace.theme_models import load_theme_json
    from lace.dock_style_manager import get_dock_style_manager

    theme = load_theme_json("my_theme.json")
    get_dock_style_manager().apply_theme_dict(theme)
"""


import json
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional, Union

from pydantic import AfterValidator, BaseModel, ConfigDict

from lace.dock_theme import (
    DockStyleCategory,
    ThemeSpec,
    build_theme,
    qcolor_to_list,
    to_qcolor,
)


# ---------------------------------------------------------------------------
# Colour coercion
# ---------------------------------------------------------------------------
def _validate_color(value: Any) -> Any:
    """Accept ``'#hex'`` / SVG colour-name strings or ``[r, g, b(, a)]`` lists.

    The hex/name string itself is trusted and resolved to an RGBA list later
    via Qt's ``QColor`` (so this model stays Qt-free); channel lists are fully
    validated here.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        if len(value) not in (3, 4):
            raise ValueError(
                f"colour must have 3 or 4 channels [r, g, b(, a)], got {len(value)}"
            )
        for ch in value:
            if isinstance(ch, bool) or not isinstance(ch, int) or not (0 <= ch <= 255):
                raise ValueError(f"colour channel must be an int in 0..255, got {ch!r}")
        return [int(c) for c in value]
    raise ValueError(
        f"colour must be a hex string or [r, g, b(, a)] list, got {value!r}"
    )


Color = Annotated[Union[str, List[int]], AfterValidator(_validate_color)]


# ---------------------------------------------------------------------------
# Theme JSON schema (mirrors ThemeSpec)
# ---------------------------------------------------------------------------
class ThemeJson(BaseModel):
    """Validated JSON representation of a declarative Lace theme.

    Field names and defaults match :class:`~lace.dock_theme.ThemeSpec`.
    Unknown keys are ignored so future metadata can be embedded safely.
    """

    model_config = ConfigDict(extra="ignore")

    # --- Seed colours ------------------------------------------------------
    name: Optional[str] = None
    base: Color
    accent: Color
    text: Color
    surface: Optional[Color] = None
    border: Optional[Color] = None
    focus_border_color: Optional[Color] = None

    # --- Generation behaviour ----------------------------------------------
    is_light: bool = False
    title_mode: str = "darker"   # "darker" | "lighter" relative to panel
    hover_mode: str = "lighter"  # "darker" | "lighter" relative to panel

    # --- Status colours ------------------------------------------------------
    success_color: Optional[Color] = None
    warning_color: Optional[Color] = None
    error_color: Optional[Color] = None
    info_color: Optional[Color] = None

    # --- Tooltip colours -----------------------------------------------------
    tooltip_bg: Optional[Color] = None
    tooltip_text: Optional[Color] = None

    # --- Geometry / typography overrides -------------------------------------
    corner_radius: Optional[int] = None
    border_width: Optional[float] = None
    title_height: Optional[int] = None
    title_padding_left: Optional[int] = None
    title_padding_right: Optional[int] = None
    title_button_spacing: Optional[int] = None
    # int, not float — ThemeSpec.title_margin is int. Kept aligned so the JSON
    # schema and the dataclass cannot drift apart.
    title_margin: Optional[int] = None
    title_border_width: Optional[float] = None
    title_border_bottom: Optional[float] = None
    title_border_color: Optional[Color] = None
    tab_radius: Optional[int] = None
    tab_margin: Optional[int] = None
    content_margin: Optional[Union[int, float, List[float]]] = None
    tab_dimming: bool = False
    indicator_width: Optional[int] = None   # matches ThemeSpec.indicator_width
    indicator_position: Optional[Union[str, List[str]]] = None

    # ---------------------------------------------------------------------------
    @classmethod
    def load(cls, path: Union[str, Path]) -> "ThemeJson":
        """Parse and validate a JSON theme file.

        Raises ``json.JSONDecodeError`` for malformed JSON and
        ``pydantic.ValidationError`` for schema violations.
        """
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(raw)

    def to_theme_spec(self) -> ThemeSpec:
        """Convert this validated JSON theme into a :class:`ThemeSpec`."""
        def rgba(col: Union[str, List[int]]) -> List[int]:
            # Hex/name strings are resolved through Qt's canonical converter.
            return qcolor_to_list(to_qcolor(col)) if isinstance(col, str) else list(col)

        return ThemeSpec(
            base=rgba(self.base),
            accent=rgba(self.accent),
            text=rgba(self.text),
            surface=rgba(self.surface) if self.surface is not None else None,
            border=rgba(self.border) if self.border is not None else None,
            focus_border_color=rgba(self.focus_border_color)
            if self.focus_border_color is not None
            else None,
            is_light=self.is_light,
            title_mode=self.title_mode,
            hover_mode=self.hover_mode,
            success_color=rgba(self.success_color) if self.success_color is not None else None,
            warning_color=rgba(self.warning_color) if self.warning_color is not None else None,
            error_color=rgba(self.error_color) if self.error_color is not None else None,
            info_color=rgba(self.info_color) if self.info_color is not None else None,
            tooltip_bg=rgba(self.tooltip_bg) if self.tooltip_bg is not None else None,
            tooltip_text=rgba(self.tooltip_text) if self.tooltip_text is not None else None,
            corner_radius=self.corner_radius,
            border_width=self.border_width,
            title_height=self.title_height,
            title_padding_left=self.title_padding_left,
            title_padding_right=self.title_padding_right,
            title_button_spacing=self.title_button_spacing,
            title_margin=self.title_margin,
            title_border_width=self.title_border_width,
            title_border_bottom=self.title_border_bottom,
            title_border_color=rgba(self.title_border_color)
            if self.title_border_color is not None
            else None,
            tab_radius=self.tab_radius,
            tab_margin=self.tab_margin,
            content_margin=self.content_margin,
            tab_dimming=self.tab_dimming,
            indicator_width=self.indicator_width,
            indicator_position=self.indicator_position,
        )

    def build_theme_dict(self) -> Dict[DockStyleCategory, Dict[str, Any]]:
        """Derive the full theme token dict (like ``DOCK_THEMES`` entries)."""
        return build_theme(self.to_theme_spec())


def load_theme_json(path: Union[str, Path]) -> Dict[DockStyleCategory, Dict[str, Any]]:
    """One-shot helper: load a JSON theme file and derive the full theme dict."""
    return ThemeJson.load(path).build_theme_dict()


__all__ = ["ThemeJson", "load_theme_json", "Color", "_validate_color"]
