# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


"""Perceptual colour maths for theme derivation.

One place that knows how to lighten, darken, mix and check colours, in a
space where equal steps look equal. HLS lightness is not that space: +0.1 L
on a yellow is a much larger visible change than on a blue. OKLCH (Björn
Ottosson's OKLab in polar form) is close enough, and cheap.

Colours are ``[r, g, b, a]`` lists of ints 0..255 -- the format the theme
builder already uses -- so nothing here depends on Qt. Contrast follows
WCAG 2.x.
"""

import math
from typing import List, Optional, Sequence, Tuple

RGBA = List[int]

#: OKLCH lightness below which a colour counts as dark.
DARK_L = 0.6

_WHITE: RGBA = [255, 255, 255, 255]
_BLACK: RGBA = [0, 0, 0, 255]


# ---------------------------------------------------------------------------
# sRGB <-> linear <-> OKLab <-> OKLCH
# ---------------------------------------------------------------------------
def _to_linear(c: float) -> float:
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _from_linear(c: float) -> float:
    c = 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    return c * 255.0


def _rgb(rgba: Sequence[int]) -> Tuple[int, int, int, int]:
    a = rgba[3] if len(rgba) > 3 else 255
    return int(rgba[0]), int(rgba[1]), int(rgba[2]), int(a)


def _linear_to_oklab(r: float, g: float, b: float) -> Tuple[float, float, float]:
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = (math.copysign(abs(v) ** (1 / 3), v) for v in (l, m, s))
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def _oklab_to_linear(L: float, a: float, b: float) -> Tuple[float, float, float]:
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)


def to_oklab(rgba: Sequence[int]) -> Tuple[float, float, float, int]:
    r, g, b, a = _rgb(rgba)
    return (*_linear_to_oklab(_to_linear(r), _to_linear(g), _to_linear(b)), a)


def to_oklch(rgba: Sequence[int]) -> Tuple[float, float, float, int]:
    """``(L, C, h, a)``: L 0..1, chroma, hue in degrees 0..360."""
    L, a_, b_, alpha = to_oklab(rgba)
    C = math.hypot(a_, b_)
    h = math.degrees(math.atan2(b_, a_)) % 360.0
    return L, C, h, alpha


def _in_gamut(lin: Tuple[float, float, float], eps: float = 1e-6) -> bool:
    return all(-eps <= c <= 1 + eps for c in lin)


def _pack(lin: Tuple[float, float, float], alpha: int) -> RGBA:
    return [max(0, min(255, round(_from_linear(max(0.0, min(1.0, c)))))) for c in lin] + [
        max(0, min(255, int(alpha)))]


def from_oklch(L: float, C: float, h: float, a: int = 255) -> RGBA:
    """OKLCH to sRGB, gamut-mapped by reducing chroma (L and hue kept)."""
    L = max(0.0, min(1.0, L))
    C = max(0.0, C)
    hr = math.radians(h)
    ca, sa = math.cos(hr), math.sin(hr)

    lin = _oklab_to_linear(L, C * ca, C * sa)
    if _in_gamut(lin):
        return _pack(lin, a)
    lo, hi = 0.0, C
    for _ in range(24):
        mid = (lo + hi) / 2
        if _in_gamut(_oklab_to_linear(L, mid * ca, mid * sa)):
            lo = mid
        else:
            hi = mid
    return _pack(_oklab_to_linear(L, lo * ca, lo * sa), a)


# ---------------------------------------------------------------------------
# WCAG
# ---------------------------------------------------------------------------
def _composite(fg: Sequence[int], bg: Sequence[int]) -> RGBA:
    """``fg`` over an opaque ``bg`` (plain sRGB alpha blending, as Qt paints)."""
    fr, fg_, fb, fa = _rgb(fg)
    br, bg_, bb, _ = _rgb(bg)
    t = fa / 255.0
    return [round(fr * t + br * (1 - t)), round(fg_ * t + bg_ * (1 - t)),
            round(fb * t + bb * (1 - t)), 255]


def relative_luminance(rgba: Sequence[int]) -> float:
    r, g, b, _ = _rgb(rgba)
    return 0.2126 * _to_linear(r) + 0.7152 * _to_linear(g) + 0.0722 * _to_linear(b)


def contrast_ratio(fg: Sequence[int], bg: Sequence[int]) -> float:
    """WCAG contrast of ``fg`` drawn on ``bg``; a translucent ``fg`` is composited first."""
    if _rgb(fg)[3] < 255:
        fg = _composite(fg, bg)
    l1, l2 = relative_luminance(fg), relative_luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def is_dark(rgba: Sequence[int]) -> bool:
    return to_oklch(rgba)[0] < DARK_L


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------
def step(rgba: Sequence[int], dL: float, *, toward: Optional[str] = None) -> RGBA:
    """Shift perceptual lightness by ``dL``, keeping hue and chroma.

    ``toward="contrast"`` takes ``abs(dL)`` in the direction away from the
    colour itself: lighter for a dark colour, darker for a light one.
    """
    L, C, h, a = to_oklch(rgba)
    if toward == "contrast":
        dL = abs(dL) if L < DARK_L else -abs(dL)
    elif toward is not None:
        raise ValueError(f"toward must be None or 'contrast', got {toward!r}")
    return from_oklch(L + dL, C, h, a)


def mix(a: Sequence[int], b: Sequence[int], t: float) -> RGBA:
    """``a`` blended toward ``b`` by ``t`` (0 = a, 1 = b), in OKLab."""
    t = max(0.0, min(1.0, t))
    La, aa, ba, alpha_a = to_oklab(a)
    Lb, ab, bb, alpha_b = to_oklab(b)
    lin = _oklab_to_linear(La + (Lb - La) * t, aa + (ab - aa) * t, ba + (bb - ba) * t)
    return _pack(lin, round(alpha_a + (alpha_b - alpha_a) * t))


def ensure_contrast(fg: Sequence[int], bg: Sequence[int], ratio: float) -> RGBA:
    """``fg`` with the smallest lightness shift that reaches ``ratio`` on ``bg``.

    Hue is kept (chroma only shrinks where the gamut forces it) and so is
    alpha. ``fg`` comes back unchanged when it already passes. When no
    lightness reaches the ratio, the best reachable colour is returned.
    """
    fg = list(_rgb(fg))
    if contrast_ratio(fg, bg) >= ratio:
        return fg
    L, C, h, a = to_oklch(fg)

    best, best_shift = None, None
    for end in (1.0, 0.0):
        if contrast_ratio(from_oklch(end, C, h, a), bg) < ratio:
            continue
        # Contrast grows monotonically moving away from bg toward this end.
        # The predicate tests the rounded 8-bit colour, so ``hi`` always
        # passes -- no nudging after the search.
        lo, hi = L, end
        for _ in range(30):
            mid = (lo + hi) / 2
            if contrast_ratio(from_oklch(mid, C, h, a), bg) >= ratio:
                hi = mid
            else:
                lo = mid
        if best is None or abs(hi - L) < best_shift:
            best, best_shift = from_oklch(hi, C, h, a), abs(hi - L)
    if best is not None:
        return best
    ends = [from_oklch(e, C, h, a) for e in (1.0, 0.0)]
    return max(ends, key=lambda c: contrast_ratio(c, bg))


def on_color(bg: Sequence[int], *, prefer: Optional[Sequence[Sequence[int]]] = None,
             ratio: float = 4.5) -> RGBA:
    """Readable text colour for ``bg``.

    Picks whichever of ``prefer`` (typically the theme's light and dark text;
    default white and black) contrasts most, then lifts it to ``ratio`` if
    it falls short. White or black always reach 4.58:1, so the default never
    fails; a themed pair may be adjusted.
    """
    candidates = [list(_rgb(c)) for c in (prefer or (_WHITE, _BLACK))]
    best = max(candidates, key=lambda c: contrast_ratio(c, bg))
    return ensure_contrast(best, bg, ratio)


__all__ = [
    "DARK_L", "to_oklab", "to_oklch", "from_oklch", "relative_luminance",
    "contrast_ratio", "is_dark", "step", "mix", "ensure_contrast", "on_color",
]
