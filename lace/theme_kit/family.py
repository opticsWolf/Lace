# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


"""Family: the dark, neutral and light members of one theme.

Every colour the spec sets is moved to the member's lightness while keeping
its hue, the way the hand-made ``*_neutral`` / ``*_light`` presets were
made. The rules, calibrated on those presets:

- **base** moves to the member's lightness (:data:`BASE_L`); the neutrals'
  chroma scales with the member (:data:`NEUTRAL_CHROMA`).
- **surfaces** (surface, title bar, fills) keep their signed step off the
  base: a raised surface stays raised, a recessed title bar recessed.
- **lines** (any ``*border*`` colour) keep pointing toward the text: lighter
  than the base on dark, darker on light, by :data:`LINE_SCALE` of the step.
- **text** goes to the member's text lightness (:data:`TEXT_L`).
- **chromatic colours** (accent, focus, tinted outlines) keep their
  contrast with the base, capped at what a mid-tone or light base allows
  (:data:`CHROMA_CAP`), on the far side of the base from it.
- **status colours** are re-derived for the member (:func:`status_colors`).

Alpha is kept; transparent colours stay transparent.
"""

from dataclasses import fields, replace
from typing import Dict, List, Optional, Tuple

from lace import color_science as cs
from lace.dock_theme import ThemeSpec
from lace.theme_kit.derive import STATUS_HUES, fit, status_colors, to_rgba

VARIANTS = ("dark", "neutral", "light")

#: OKLCH lightness of the base per member. A dark source keeps its own.
BASE_L: Dict[str, float] = {"dark": 0.22, "neutral": 0.72, "light": 0.92}
#: Text lightness per member.
TEXT_L: Dict[str, float] = {"dark": 0.93, "neutral": 0.25, "light": 0.25}
#: Chroma of the neutrals relative to the dark member.
NEUTRAL_CHROMA: Dict[str, float] = {"dark": 1.0, "neutral": 0.45, "light": 0.75}
#: Line steps off the base relative to the dark member.
LINE_SCALE: Dict[str, float] = {"dark": 1.0, "neutral": 0.8, "light": 0.8}
#: Most contrast a chromatic colour keeps with the base, per member.
CHROMA_CAP: Dict[str, float] = {"dark": 7.0, "neutral": 2.8, "light": 4.2}
#: Below this OKLCH chroma a colour counts as a neutral.
NEUTRAL_C = 0.05
#: Text chroma cap: text stays close to grey.
TEXT_C = 0.025

_TEXT_FIELDS = ("text", "tooltip_text")
_COLOUR_FIELDS = tuple(f.name for f in fields(ThemeSpec)
                       if f.name.endswith(("_color", "_bg", "_bg_normal", "_bg_active",
                                           "_bg_hover_start", "_bg_hover_end"))
                       or f.name in ("base", "accent", "text", "surface", "border"))


def variant_of(spec: ThemeSpec) -> str:
    """Which member ``spec`` is, from its base lightness."""
    L = cs.to_oklch(to_rgba(spec.base))[0]
    if L < cs.DARK_L:
        return "dark"
    return "light" if L >= 0.85 else "neutral"


def _at_ratio(C: float, h: float, alpha: int, bg: List[int], ratio: float,
              darker: bool) -> List[int]:
    """The colour of hue ``h`` / chroma ``C`` at ``ratio`` against ``bg``, on
    the ``darker`` (or lighter) side of it; the far end if out of reach."""
    L_bg = cs.to_oklch(bg)[0]
    lo, hi = (0.0, L_bg) if darker else (L_bg, 1.0)
    for _ in range(32):
        mid = (lo + hi) / 2
        r = cs.contrast_ratio(fit(mid, C, h, alpha)[0], bg)
        # Moving away from bg raises the ratio: darker => lower L.
        if (r >= ratio) == darker:
            lo = mid
        else:
            hi = mid
    return fit(lo if darker else hi, C, h, alpha)[0]


def _member(spec: ThemeSpec, src: str, dst: str) -> ThemeSpec:
    base = to_rgba(spec.base)
    bL, bC, bh, ba = cs.to_oklch(base)
    new_bL = bL if dst == src == "dark" else BASE_L[dst]
    chroma = NEUTRAL_CHROMA[dst] / NEUTRAL_CHROMA[src]
    new_base = fit(new_bL, bC * chroma, bh, ba)[0]
    darker = not cs.is_dark(new_base)

    out = {"base": new_base}
    for name in _COLOUR_FIELDS:
        value = getattr(spec, name)
        if name == "base" or value is None or name in STATUS_HUES:
            continue
        c = to_rgba(value)
        if len(c) > 3 and c[3] == 0:
            out[name] = c
            continue
        L, C, h, a = cs.to_oklch(c)
        if name in _TEXT_FIELDS:
            out[name] = fit(TEXT_L[dst], min(C, TEXT_C), h if C > 0.01 else bh, a)[0]
        elif C < NEUTRAL_C:
            off = L - bL
            if "border" in name:
                step = abs(off) * LINE_SCALE[dst] / LINE_SCALE[src]
                new_L = new_bL - step if darker else new_bL + step
            else:
                new_L = new_bL + off
            out[name] = fit(min(max(new_L, 0.0), 0.99), C * chroma, h, a)[0]
        else:
            # Solved opaque, then given back its alpha: a translucent ring is
            # the same colour as its opaque twin (a hover ring and its
            # active one), and must stay so.
            ratio = min(cs.contrast_ratio(c[:3] + [255], base), CHROMA_CAP[dst])
            out[name] = _at_ratio(C, h, 255, new_base, ratio, darker)[:3] + [a]

    member = replace(spec, is_light=darker, **out)
    if dst == "light":
        member = replace(member, hover_mode="darker")
    if any(getattr(spec, n) is not None for n in STATUS_HUES):
        member = replace(member, **status_colors(member))
    return member


def family(spec: ThemeSpec) -> Dict[str, ThemeSpec]:
    """``{"dark": ..., "neutral": ..., "light": ...}``; ``spec`` itself is
    the member matching its own base."""
    src = variant_of(spec)
    return {v: spec if v == src else _member(spec, src, v) for v in VARIANTS}


def spec_delta(a: ThemeSpec, b: ThemeSpec) -> Tuple[float, float, Optional[str]]:
    """Mean and max ΔE (OKLab) over the colours both specs set, and the
    field with the max: how far ``a`` is from ``b`` as an author sees it."""
    des = []
    for name in _COLOUR_FIELDS:
        x, y = getattr(a, name), getattr(b, name)
        if x is None or y is None:
            continue
        x, y = to_rgba(x), to_rgba(y)
        if (len(x) > 3 and x[3] == 0) and (len(y) > 3 and y[3] == 0):
            continue
        des.append((cs.delta_e(x, y), name))
    if not des:
        return 0.0, 0.0, None
    worst = max(des)
    return sum(d for d, _ in des) / len(des), worst[0], worst[1]


__all__ = ["BASE_L", "CHROMA_CAP", "VARIANTS", "family", "spec_delta", "variant_of"]
