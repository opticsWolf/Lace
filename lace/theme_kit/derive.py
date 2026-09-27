# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


"""Palettes: the seed colours and colour keywords of a theme.

:func:`derive` turns two or three seeds into a :class:`Palette`;
:func:`status_colors` gives it success / warning / error / info colours that
read equally strong on it. The rest of the theme (surfaces, hovers, text on
each surface) is derived later by :func:`lace.dock_theme.build_theme`, the
same engine the presets go through.
"""

from dataclasses import dataclass, fields
from typing import Dict, List, Optional, Sequence, Tuple, Union

from lace import color_science as cs
from lace.theme_contrast import CONTRAST_TARGETS

RGBA = List[int]
ColorLike = Union[str, Sequence[int], "QColor"]  # noqa: F821 - QColor accepted too

#: The ThemeSpec fields a palette owns; everything else belongs to a chassis.
PALETTE_FIELDS: Tuple[str, ...] = (
    "base", "accent", "text", "surface", "border", "focus_border_color", "title_bg",
    "is_light", "contrast", "depth", "selection", "title_mode", "hover_mode",
    "success_color", "warning_color", "error_color", "info_color",
    "tooltip_bg", "tooltip_text",
)

#: Conventional status hues (OKLCH degrees): green, amber, red, blue.
STATUS_HUES: Dict[str, float] = {
    "success_color": 150.0, "warning_color": 80.0, "error_color": 27.0, "info_color": 250.0,
}
#: Status chroma, reduced further wherever sRGB can't hold it.
STATUS_CHROMA = 0.15
#: Status lightness stays in this band, so on a mid-tone base, where no
#: lightness reaches the target, the colours don't go to black or white.
STATUS_L_RANGE = (0.45, 0.85)

#: Largest chroma ``neutral_tint=1`` gives the neutrals, and the most of the
#: accent's own chroma it may borrow.
TINT_CHROMA = 0.03


def to_rgba(value: Optional[ColorLike]) -> Optional[RGBA]:
    """``"#rrggbb"``, an SVG name, a list or a QColor as ``[r, g, b, a]``."""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        v = [int(x) for x in value]
        return v + [255] if len(v) == 3 else v
    from lace.dock_theme import qcolor_to_list, to_qcolor
    c = to_qcolor(value)
    if not c.isValid():
        raise ValueError(f"not a colour: {value!r}")
    return qcolor_to_list(c)


@dataclass
class Palette:
    """Seed colours plus colour keywords; see PALETTE_FIELDS.

    ``clipped`` names the colours that had to lose chroma to fit sRGB while
    being derived; :func:`lace.theme_kit.audit` reports them.
    """
    base: RGBA
    accent: RGBA
    text: RGBA
    surface: Optional[RGBA] = None
    border: Optional[RGBA] = None
    focus_border_color: Optional[RGBA] = None
    title_bg: Optional[RGBA] = None
    is_light: Optional[bool] = None
    contrast: str = "normal"
    depth: str = "subtle"
    selection: str = "solid"
    title_mode: str = "darker"
    hover_mode: str = "lighter"
    success_color: Optional[RGBA] = None
    warning_color: Optional[RGBA] = None
    error_color: Optional[RGBA] = None
    info_color: Optional[RGBA] = None
    tooltip_bg: Optional[RGBA] = None
    tooltip_text: Optional[RGBA] = None
    clipped: Tuple[str, ...] = ()

    def as_spec_kwargs(self) -> dict:
        return {f: getattr(self, f) for f in PALETTE_FIELDS}


def fit(L: float, C: float, h: float, alpha: int = 255) -> Tuple[RGBA, bool]:
    """``from_oklch``, and whether it had to reduce chroma to fit sRGB."""
    rgba = cs.from_oklch(L, C, h, alpha)
    return rgba, C - cs.to_oklch(rgba)[1] > 0.005


def _tint(rgba: Optional[RGBA], accent: RGBA, amount: float) -> Tuple[Optional[RGBA], bool]:
    """``rgba`` with its hue turned to the accent's and a little of its chroma."""
    if rgba is None or amount <= 0:
        return rgba, False
    L, C, _, a = cs.to_oklch(rgba)
    _, aC, ah, _ = cs.to_oklch(accent)
    extra = amount * min(TINT_CHROMA, aC)
    return fit(L, C + extra, ah, a)


def derive(base: ColorLike, accent: ColorLike, text: Optional[ColorLike] = None, *,
           surface: Optional[ColorLike] = None, border: Optional[ColorLike] = None,
           focus_border_color: Optional[ColorLike] = None,
           title_bg: Optional[ColorLike] = None,
           contrast: str = "normal", depth: str = "subtle", selection: str = "solid",
           title_mode: str = "darker", hover_mode: str = "lighter",
           neutral_tint: float = 0.0, status: bool = False) -> Palette:
    """A palette from two seeds (three with ``text``).

    ``text`` defaults to the more readable of near-black and near-white on
    the base. ``is_light`` is left to the engine, which reads it off the base.
    ``neutral_tint`` (0..1) turns the neutrals (base, surface, border, title)
    toward the accent's hue, the way ``slate_amber`` and ``midnight_haze``
    were tuned by hand. ``status=True`` also fills the status colours.
    """
    if not 0.0 <= neutral_tint <= 1.0:
        raise ValueError("neutral_tint must be within 0..1")
    base_c, accent_c = to_rgba(base), to_rgba(accent)
    clipped = []
    tinted = {}
    for name, value in (("base", base_c), ("surface", to_rgba(surface)),
                        ("border", to_rgba(border)), ("title_bg", to_rgba(title_bg))):
        tinted[name], lost = _tint(value, accent_c, neutral_tint)
        if lost:
            clipped.append(name)
    text_c = to_rgba(text) if text is not None else cs.on_color(tinted["base"])
    pal = Palette(
        base=tinted["base"], accent=accent_c, text=text_c,
        surface=tinted["surface"], border=tinted["border"], title_bg=tinted["title_bg"],
        focus_border_color=to_rgba(focus_border_color),
        contrast=contrast, depth=depth, selection=selection,
        title_mode=title_mode, hover_mode=hover_mode,
    )
    if status:
        colours, lost = _status(pal)
        for name, value in colours.items():
            setattr(pal, name, value)
        clipped += lost
    pal.clipped = tuple(clipped)
    return pal


def _status(pal: Union[Palette, "ThemeSpec"]) -> Tuple[Dict[str, RGBA], List[str]]:  # noqa: F821
    base = to_rgba(pal.base)
    target = CONTRAST_TARGETS["muted"][getattr(pal, "contrast", "normal")]
    lighter = cs.is_dark(base)
    lo, hi = STATUS_L_RANGE

    def colours(L):
        return {name: fit(L, STATUS_CHROMA, h) for name, h in STATUS_HUES.items()}

    # One lightness for all four: the first, moving away from the base, at
    # which every hue reaches the target; the band's far end if none does.
    steps = [lo + (hi - lo) * i / 80 for i in range(81)]
    if not lighter:
        steps.reverse()
    chosen = steps[-1]
    for L in steps:
        if all(cs.contrast_ratio(c, base) >= target for c, _ in colours(L).values()):
            chosen = L
            break
    out = colours(chosen)
    return {n: c for n, (c, _) in out.items()}, [n for n, (_, lost) in out.items() if lost]


def status_colors(pal) -> Dict[str, RGBA]:
    """Success / warning / error / info for a palette (or ThemeSpec).

    The hues stay conventional; all four share one lightness and chroma, so
    none reads stronger than the others, and that lightness is the first,
    moving away from the base, where each meets the theme's "muted" floor.
    """
    return _status(pal)[0]


__all__ = ["PALETTE_FIELDS", "Palette", "derive", "fit", "status_colors", "to_rgba"]


# Every palette field is a ThemeSpec field of the same name (checked at import).
def _check_fields():
    from lace.dock_theme import ThemeSpec
    spec = {f.name for f in fields(ThemeSpec)}
    missing = set(PALETTE_FIELDS) - spec
    assert not missing, f"PALETTE_FIELDS not on ThemeSpec: {missing}"


_check_fields()
del _check_fields
