# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


"""Chassis: the geometry and styling a theme wears, apart from its colours.

A theme is a :class:`~lace.theme_kit.derive.Palette` plus a chassis. The
chassis are taken from the presets that introduced each look. Colour tokens
in a chassis (a tab outline, a sidebar ring) are written as *roles* so the
same chassis fits any palette:

- ``"focus"``: the palette's focus colour, or its accent when it has none
- ``"accent"``, ``"border"``: those palette colours
- ``"clear"``: fully transparent
- ``(role, alpha)``: the role's colour at that alpha
"""

from dataclasses import fields
from typing import Any, Dict, List, Optional, Tuple, Union

from lace.dock_theme import ThemeSpec
from lace.theme_kit.derive import PALETTE_FIELDS, Palette

Role = Union[str, Tuple[str, int]]

#: Name -> tokens. "stock" is Lace's default geometry: nothing set.
CHASSIS: Dict[str, Dict[str, Any]] = {
    "stock": {},
    # dark, light, neutral, Kilim classic: 4 px, 1.5 px border, inset title bar.
    "classic": dict(
        corner_radius=4, tab_radius=4, border_width=1.5, title_margin=0.5,
        content_margin=0.5, tab_dimming=True,
    ),
    # nordic, solarized_*: no border.
    "flat": dict(border_width=0.0),
    # The former midnight preset: square card, 0.5 px hairline.
    "square": dict(
        corner_radius=0, tab_radius=4, border_width=0.5, title_margin=0.0,
        content_margin=4.0, tab_dimming=True,
    ),
    # cyberpunk_edge*, Kilim neo: 10 px, flush title bar with a 1.5 px rule,
    # ringed sidebar tabs.
    "edge": dict(
        corner_radius=10, border_width=1.5, title_height=32, title_padding_left=0,
        title_padding_right=8, title_button_spacing=6, title_margin=0,
        title_border_bottom=1.5, title_border_focus_color="focus",
        tab_radius=8, tab_margin=3, content_margin=(8, 2), tab_dimming=True,
        indicator_width=1.5, indicator_position="bottom",
        sidebar_tab_flat_edge="none", sidebar_tab_border_width=1.5,
        sidebar_tab_border_color="border", sidebar_tab_border_active_color="focus",
        sidebar_indicator_width=1.5,
    ),
    # violet_haze*, midnight_haze*: 10 px, a 2 px frame starting below the
    # title bar, outlined tabs.
    "haze": dict(
        corner_radius=10, border_width=2.0, title_height=32, title_padding_right=8,
        title_button_spacing=6, title_border_bottom=2.0, border_below_title=True,
        tab_radius=8, tab_margin=3, tab_border_width=2.0, tab_border_active_color="focus",
        content_margin=(8, 2), tab_dimming=True, indicator_position="none",
        sidebar_tab_flat_edge="none", sidebar_tab_border_width=2.0,
        sidebar_tab_border_color="clear", sidebar_indicator_width=2.0,
    ),
    # cyberpunk_neon: 10 px, the border carries the glow, pill sidebar tabs
    # ringed on activation.
    "neon": dict(
        corner_radius=10, border_width=1.5, title_height=32, title_padding_left=0,
        title_padding_right=8, title_button_spacing=6, title_margin=0,
        tab_radius=8, tab_margin=3, content_margin=(8, 2), tab_dimming=True,
        indicator_width=2.0, indicator_position="bottom",
        sidebar_tab_flat_edge="none", sidebar_tab_border_width=1.5,
        sidebar_tab_border_color="clear", sidebar_tab_border_active_color="focus",
        sidebar_indicator_width=1.5,
    ),
}

_SPEC_FIELDS = tuple(f.name for f in fields(ThemeSpec))
#: Everything a chassis may set: every ThemeSpec field a palette doesn't own.
CHASSIS_FIELDS: Tuple[str, ...] = tuple(f for f in _SPEC_FIELDS if f not in PALETTE_FIELDS)

for _name, _tokens in CHASSIS.items():
    _bad = set(_tokens) - set(CHASSIS_FIELDS)
    assert not _bad, f"chassis {_name!r} sets non-chassis fields {_bad}"


def resolve_role(role: Role, palette: Palette) -> Optional[List[int]]:
    """A chassis colour role on ``palette``; None if the palette lacks it."""
    alpha = None
    if isinstance(role, tuple):
        role, alpha = role
    if role == "clear":
        return [0, 0, 0, 0]
    if role == "focus":
        colour = palette.focus_border_color or palette.accent
    elif role in ("accent", "border"):
        colour = getattr(palette, role)
    else:
        raise ValueError(f"unknown chassis colour role {role!r}")
    if colour is None:
        return None
    colour = list(colour)
    if alpha is not None:
        colour = colour[:3] + [int(alpha)]
    return colour


def _resolve(chassis: Union[str, Dict[str, Any]], palette: Palette) -> Dict[str, Any]:
    tokens = CHASSIS[chassis] if isinstance(chassis, str) else chassis
    out = {}
    for key, value in tokens.items():
        if isinstance(value, (str, tuple)) and key.endswith("_color"):
            value = resolve_role(value, palette)
        out[key] = value
    return out


def compose(palette: Palette, chassis: Union[str, Dict[str, Any]] = "classic",
            **overrides) -> ThemeSpec:
    """A ThemeSpec from a palette and a chassis. Overrides win over both."""
    bad = set(overrides) - set(_SPEC_FIELDS)
    if bad:
        raise TypeError(f"not ThemeSpec fields: {sorted(bad)}")
    kwargs = palette.as_spec_kwargs()
    kwargs.update(_resolve(chassis, palette))
    kwargs.update(overrides)
    return ThemeSpec(**kwargs)


def palette_of(spec: ThemeSpec) -> Palette:
    """The palette part of a spec."""
    return Palette(**{f: getattr(spec, f) for f in PALETTE_FIELDS})


def _same(a, b) -> bool:
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return list(a) == list(b)
    return a == b


def chassis_of(spec: ThemeSpec) -> Tuple[str, Dict[str, Any]]:
    """The closest chassis, and the overrides the spec needs on top of it.

    ``compose(palette_of(spec), *chassis_of(spec))`` rebuilds ``spec``
    exactly. Closest means fewest overrides; ties go to CHASSIS order.
    """
    pal = palette_of(spec)
    best = None
    for name in CHASSIS:
        composed = compose(pal, name)
        extra = {f: getattr(spec, f) for f in CHASSIS_FIELDS
                 if not _same(getattr(composed, f), getattr(spec, f))}
        if best is None or len(extra) < len(best[1]):
            best = (name, extra)
    return best


def restyle(spec: ThemeSpec, chassis: str) -> ThemeSpec:
    """``spec``'s palette on another chassis, dropping its own geometry."""
    return compose(palette_of(spec), chassis)


__all__ = ["CHASSIS", "CHASSIS_FIELDS", "chassis_of", "compose", "palette_of",
           "resolve_role", "restyle"]
