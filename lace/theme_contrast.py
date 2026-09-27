# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


"""What each theme token is drawn on, and how far it must stand out.

Two kinds of rule, both measured on a finished theme dict:

- **contrast** (WCAG ratio): a text or UI token against the surface it is
  painted on, with a floor per ``contrast`` level.
- **separation** (OKLCH lightness): a surface against the one it sits on, so
  that a title bar, input field or hover is visible at all. The floor is
  set by the ``depth`` level.

The builder uses these tables to fix a theme; :func:`audit` reports on one.
"""

from typing import Any, Dict, List, NamedTuple, Tuple

from lace import color_science as cs

C = "CORE"
P = "PANEL"
SB = "SIDEBAR"
SP = "SIDEPANEL"
T = "TAB"
TB = "TITLE_BAR"
OV = "OVERLAY"

#: WCAG floors per role and contrast level (docs/IMPROVEMENT_PLAN_v0.8.md).
CONTRAST_TARGETS: Dict[str, Dict[str, float]] = {
    "text":     {"low": 4.5, "normal": 7.0, "high": 10.0},
    "muted":    {"low": 3.0, "normal": 4.5, "high": 7.0},
    "disabled": {"low": 1.8, "normal": 2.3, "high": 3.0},
    "ui":       {"low": 1.5, "normal": 3.0, "high": 4.5},
    "border":   {"low": 1.15, "normal": 1.3, "high": 1.6},
    # Text on a mid-tone accent can't reach body-text floors (the best any
    # colour manages on such a fill is ~4.6:1), so selections get their own.
    "on_accent": {"low": 3.0, "normal": 4.5, "high": 7.0},
}
CONTRAST_LEVELS = ("low", "normal", "high")


class Pair(NamedTuple):
    role: str
    token: Tuple[str, str]     # (category, key) that gets adjusted
    surface: Tuple[str, str]   # (category, key) it is drawn on


#: Every foreground token and the surface it sits on. Order matters: the
#: builder fixes them top to bottom.
CONTRAST_PAIRS: Tuple[Pair, ...] = (
    Pair("text",     (C, "text_color"),            (C, "canvas_bg")),
    Pair("text",     (P, "text_color"),            (P, "bg_normal")),
    Pair("text",     (SP, "title_text_color"),     (SP, "bg_normal")),
    Pair("text",     (T, "text_active"),           (T, "bg_active")),
    Pair("text",     (TB, "text_active"),          (TB, "bg_normal")),
    Pair("text",     (C, "tooltip_text"),          (C, "tooltip_bg")),
    Pair("text",     (SB, "tab_text_active"),      (SB, "tab_bg_active")),
    Pair("muted",    (T, "text_normal"),           (T, "bg_normal")),
    Pair("muted",    (TB, "text_normal"),          (TB, "bg_normal")),
    Pair("muted",    (TB, "button_color"),         (TB, "bg_normal")),
    Pair("muted",    (SP, "button_color"),         (SP, "bg_normal")),
    Pair("muted",    (SB, "tab_text_normal"),      (SB, "bg_color")),
    Pair("muted",    (T, "close_btn_color"),       (T, "bg_active")),
    Pair("disabled", (C, "disabled_text_color"),   (P, "bg_normal")),
    Pair("disabled", (SB, "tab_text_disabled"),    (SB, "bg_color")),
    Pair("disabled", (TB, "button_disable_clr"),   (TB, "bg_normal")),
    Pair("ui",       (C, "focus_border_color"),    (C, "canvas_bg")),
    Pair("ui",       (T, "indicator_color"),       (T, "bg_normal")),
    Pair("ui",       (TB, "active_edge_color"),    (TB, "bg_normal")),
    Pair("ui",       (SB, "indicator_color"),      (SB, "bg_color")),
    # The card edge, between panel and canvas: see EITHER_SURFACE.
    Pair("border",   (C, "border_color"),          (P, "bg_normal")),
    # Last: the accent it sits on may have been nudged by the "ui" rules.
    Pair("on_accent", (P, "highlighted_text"),     (P, "highlight")),
)

#: How far (OKLab ΔE) the fixer may move a colour the theme set explicitly.
#: Enough to lift a near-miss, small enough that the theme still looks like
#: its author's choice. Derived colours move as far as they need to.
EXPLICIT_MAX_DE = 0.04
#: Borders exist only to separate, so an explicit one may move further
#: (0.12 is what the darkest presets need to show their card edge).
BORDER_MAX_DE = 0.12

#: Minimum OKLCH lightness gap between two touching surfaces, per depth.
SEPARATION_TARGETS: Dict[str, Dict[str, float]] = {
    "surface": {"flat": 0.012, "subtle": 0.02, "raised": 0.035},
    "hover":   {"flat": 0.03, "subtle": 0.04, "raised": 0.06},
}
#: ...and minimum WCAG ratio between them. A fixed lightness gap vanishes
#: near black (ΔL 0.02 at L 0.15 is ~1.02:1, invisible on a real screen);
#: the ratio asks for a bigger step the darker the surfaces are.
SEPARATION_RATIOS: Dict[str, Dict[str, float]] = {
    "surface": {"flat": 1.06, "subtle": 1.10, "raised": 1.15},
    "hover":   {"flat": 1.08, "subtle": 1.12, "raised": 1.18},
}
DEPTH_LEVELS = ("flat", "subtle", "raised")

#: (role, surface, parent). The surface is the one moved when too close.
SEPARATION_PAIRS: Tuple[Tuple[str, Tuple[str, str], Tuple[str, str]], ...] = (
    ("surface", (P, "bg_normal"),        (C, "canvas_bg")),
    ("surface", (TB, "bg_normal"),       (P, "bg_normal")),
    ("surface", (TB, "bg_normal"),       (C, "canvas_bg")),
    ("surface", (P, "input_bg"),         (P, "bg_normal")),
    ("surface", (P, "input_bg"),         (C, "canvas_bg")),
    ("surface", (P, "button_bg"),        (P, "bg_normal")),
    ("surface", (C, "tooltip_bg"),       (P, "bg_normal")),
    ("hover",   (T, "bg_hover"),         (T, "bg_normal")),
    ("hover",   (TB, "button_hover_bg"), (TB, "bg_normal")),
    ("hover",   (SP, "button_hover_bg"), (SP, "bg_normal")),
    ("hover",   (SB, "tab_bg_hover_start"), (SB, "bg_color")),
)


#: Foregrounds drawn on an edge between two surfaces. A line on an edge is
#: visible when it stands off either side; the two sides are kept apart by
#: the separation rules. So the card border is measured against whichever
#: of panel and canvas it contrasts with more, rather than against both
#: (which would need a bright line on every dark theme).
EITHER_SURFACE: Dict[Tuple[str, str], Tuple[Tuple[str, str], ...]] = {
    (C, "border_color"): ((C, "canvas_bg"),),
}


def _surface_for(theme, token, surface, fg, canvas) -> List[int]:
    """The opaque surface ``fg`` is measured against for this pair."""
    refs = (surface,) + EITHER_SURFACE.get(tuple(token), ())
    bgs = [_opaque(_rgba(v), canvas) for v in (_get(theme, r) for r in refs) if v is not None]
    return max(bgs, key=lambda b: cs.contrast_ratio(fg, b))


def _get(theme: Dict[Any, Dict[str, Any]], ref: Tuple[str, str]):
    for cat, values in theme.items():
        if getattr(cat, "name", cat) == ref[0]:
            return values.get(ref[1])
    return None


def _rgba(value) -> List[int]:
    if hasattr(value, "red"):
        return [value.red(), value.green(), value.blue(), value.alpha()]
    return list(value)


def _opaque(fg: List[int], bg: List[int]) -> List[int]:
    return cs._composite(fg, bg) if len(fg) > 3 and fg[3] < 255 else fg


def lightness_gap(a, b) -> float:
    return abs(cs.to_oklch(a)[0] - cs.to_oklch(b)[0])


def separation(a, b, role: str, depth: str) -> float:
    """How well ``a`` stands off ``b``: 1.0 meets both floors, below misses.

    The smaller of the lightness gap and the contrast ratio, each as a
    fraction of its floor, so one number can be compared and maximised.
    """
    gap = lightness_gap(a, b) / SEPARATION_TARGETS[role][depth]
    ratio = (cs.contrast_ratio(a, b) - 1) / (SEPARATION_RATIOS[role][depth] - 1)
    return min(gap, ratio)


class Finding(NamedTuple):
    kind: str        # "contrast" | "separation"
    role: str
    token: str
    surface: str
    value: float
    target: float
    #: No foreground colour at all reaches the target on this surface: the
    #: fix belongs to the surface (usually a mid-tone the theme set).
    unreachable: bool = False


def audit(theme: Dict[Any, Dict[str, Any]], contrast: str = "normal",
          depth: str = "subtle") -> List[Finding]:
    """Every rule the theme misses at the given levels."""
    out = []
    for role, token, surface in CONTRAST_PAIRS:
        fg, bg = _get(theme, token), _get(theme, surface)
        if fg is None or bg is None:
            continue
        fg, bg = _rgba(fg), _rgba(bg)
        if len(fg) > 3 and fg[3] == 0:
            continue
        bg = _surface_for(theme, token, surface, fg, _rgba(_get(theme, (C, "canvas_bg"))))
        ratio = cs.contrast_ratio(fg, bg)
        target = CONTRAST_TARGETS[role][contrast]
        if ratio < target - 1e-6:
            # Unreachable when no grey meets this floor and those of every
            # other surface the same list is drawn on (a shared muted text
            # can need black on one surface and white on the other).
            rules = [(CONTRAST_TARGETS[r][contrast],
                      _surface_for(theme, tk, sf, fg, _rgba(_get(theme, (C, "canvas_bg")))))
                     for r, tk, sf in CONTRAST_PAIRS
                     if _get(theme, tk) is _get(theme, token) and _get(theme, sf) is not None]
            reachable = any(all(cs.contrast_ratio([v, v, v, 255], q) >= t for t, q in rules)
                            for v in range(0, 256, 3))
            out.append(Finding("contrast", role, ".".join(token), ".".join(surface),
                               round(ratio, 2), target, unreachable=not reachable))
    canvas = _rgba(_get(theme, (C, "canvas_bg")))
    for role, surface, parent in SEPARATION_PAIRS:
        s, p = _get(theme, surface), _get(theme, parent)
        if s is None or p is None:
            continue
        s, p = _opaque(_rgba(s), canvas), _opaque(_rgba(p), canvas)
        score = separation(s, p, role, depth)
        if score < 1 - 1e-6:
            # Reported as a contrast ratio: the rule people can check by hand.
            out.append(Finding("separation", role, ".".join(surface), ".".join(parent),
                               round(cs.contrast_ratio(s, p), 3),
                               SEPARATION_RATIOS[role][depth]))
    return out


def _colour_lists(theme) -> List[List[int]]:
    return [v for values in theme.values() for v in values.values()
            if isinstance(v, list) and len(v) in (3, 4) and all(isinstance(x, int) for x in v)]


def _move(value: List[int], new: List[int], followers=()) -> bool:
    """Write ``new`` into ``value`` in place; True if it changed.

    ``followers`` with the old RGB take the new RGB too, keeping their own
    alpha: a theme that sets two fields to one colour (a focus border and the
    sidebar stripe that continues it, or a ring and its fainter hover) means
    them to stay the same colour.
    """
    new = list(new[:len(value)])
    old = list(value)
    if new == old:
        return False
    for other in followers:
        if other is not value and list(other[:3]) == old[:3]:
            other[:3] = new[:3]
    value[:] = new
    return True


def enforce(theme: Dict[Any, Dict[str, Any]], contrast: str = "normal",
            depth: str = "subtle", explicit_ids=frozenset()) -> List[str]:
    """Fix ``theme`` in place so it meets the rules; return what moved.

    Values are the builder's colour lists, and several tokens share one list
    (the title background is both TAB.bg_normal and TITLE_BAR.bg_normal), so
    a fix is written *into* the list and every token sharing it follows.

    Lists whose ``id`` is in ``explicit_ids`` came from the spec. They stay
    within :data:`EXPLICIT_MAX_DE` of their original value in total, however
    many rules touch them, and only move when that improves the rule they
    miss; they may still fall short. Derived colours move as far as needed.
    Surfaces are separated first, then foregrounds are fixed against the
    final surfaces.
    """
    moved = []
    canvas = _get(theme, (C, "canvas_bg"))

    # Which lists act as a surface somewhere, and which as a foreground. A
    # moved foreground drags along equal foreground-only colours, never a
    # surface that happens to share its value (and vice versa).
    surfaces = {id(_get(theme, ref)) for pairs in (
        [(p.surface,) for p in CONTRAST_PAIRS], [(s, par) for _, s, par in SEPARATION_PAIRS])
        for refs in pairs for ref in refs}
    foregrounds = {id(_get(theme, p.token)) for p in CONTRAST_PAIRS}
    colours = _colour_lists(theme)
    # Followers are colours no rule governs directly; one that is itself a
    # foreground or surface keeps whatever its own rule decided.
    governed = surfaces | foregrounds
    fg_followers = surface_followers = [c for c in colours if id(c) not in governed]
    origin = {id(c): list(c) for c in colours if id(c) in explicit_ids}

    def options(value, want, a, cap=EXPLICIT_MAX_DE):
        """Where ``value`` may go on its way to ``want``."""
        if id(value) not in origin:
            return [want]
        o = origin[id(value)]
        L, Ch, h, _ = cs.to_oklch(o)
        # The capped straight line toward the fix can pass through the
        # surface's own lightness first; the two pure lightness directions
        # are the fallbacks.
        return [cs.toward(o, t, cap)
                for t in (want, cs.from_oklch(1.0, Ch, h, a), cs.from_oklch(0.0, Ch, h, a))]

    for role, surface, parent in SEPARATION_PAIRS:
        s, p = _get(theme, surface), _get(theme, parent)
        if s is None or p is None or (len(s) > 3 and s[3] < 255):
            continue
        target = SEPARATION_TARGETS[role][depth]
        Ls, Cs, hs, a = cs.to_oklch(s)
        Lp = cs.to_oklch(p)[0]
        gap = abs(Ls - Lp)
        now = separation(s, p, role, depth)
        if now >= 1:
            continue
        # Every separation rule this list takes part in: a shared hover sits
        # on the title bar and the sidebar at once, and a fix for one side
        # must not undo the other.
        rules = [(r, _get(theme, par)) for r, sf, par in SEPARATION_PAIRS
                 if _get(theme, sf) is s and _get(theme, par) is not None]

        def failing(c):
            return sum(separation(c, q, r, depth) < 1 for r, q in rules)

        def reach(sign, q, r):
            """Nearest colour past ``q``'s floor on ``sign``'s side of it.

            A little past, so 8-bit rounding can't land it short; and near
            black small OKLCH steps round back to the same colour (L 0.03
            is still [0, 0, 0]), so widen until the rounded colour clears.
            """
            Lq = cs.to_oklch(q)[0]
            aim = SEPARATION_TARGETS[r][depth] + 0.004
            want = cs.from_oklch(Lq + sign * aim, Cs, hs, a)
            while separation(want, q, r, depth) < 1.02 and aim < 0.4:
                aim += 0.004
                want = cs.from_oklch(Lq + sign * aim, Cs, hs, a)
            return want

        # Just past each surface it touches, on either side: when it sits
        # between two of them (a title bar between canvas and panel) and
        # the gap is too narrow, the answer is past the far one.
        cands = [reach(sign, q, r) for r, q in rules for sign in (1, -1)]
        first = (1 if Ls > Lp else -1) if gap > 0.002 else (1 if Lp < cs.DARK_L else -1)
        # Fewest rules broken; then the side it is already on; then nearest.
        want = min(cands, key=lambda c: (failing(c), separation(c, p, role, depth) < 1,
                                          (cs.to_oklch(c)[0] - Lp) * first < 0,
                                          cs.delta_e(c, s)))
        best = max(options(s, want, a), key=lambda c: separation(c, p, role, depth))
        if separation(best, p, role, depth) > now and _move(s, best, surface_followers):
            moved.append(".".join(surface))

    for role, token, surface in CONTRAST_PAIRS:
        fg, bg = _get(theme, token), _get(theme, surface)
        if fg is None or bg is None or (len(fg) > 3 and fg[3] == 0):
            continue
        bg = _surface_for(theme, token, surface, list(fg), list(canvas))
        target = CONTRAST_TARGETS[role][contrast]
        now = cs.contrast_ratio(fg, bg)
        if now >= target:
            continue
        a = fg[3] if len(fg) > 3 else 255
        # Every surface this list is drawn on: the disabled text is both the
        # panel's and the sidebar's, and a fix for one must hold on the other.
        rules = [(CONTRAST_TARGETS[r][contrast], _surface_for(theme, tk, sf, list(fg), list(canvas)))
                 for r, tk, sf in CONTRAST_PAIRS
                 if _get(theme, tk) is fg and _get(theme, sf) is not None]

        def unreadable_on(c):
            return sum(cs.contrast_ratio(c, q) < t for t, q in rules)

        # A hair past each floor, so the audit's rounding can't read it short.
        # The exact floors too: on a mid-tone, black may clear 4.5 but not
        # the margin, leaving only white, which fails a sibling surface.
        wants = [cs.ensure_contrast(fg, q, t + m) for t, q in rules for m in (0.02, 0.0)]
        # The nearest fix for one surface can land in the other's dead zone
        # (black passes on the panel, grey 115 on the sidebar, neither on
        # both): chain the fixes so each is held against every surface.
        for _ in range(2):
            for t, q in rules:
                wants.append(cs.ensure_contrast(wants[-1], q, t + 0.02))
        cap = BORDER_MAX_DE if role == "border" else EXPLICIT_MAX_DE
        # And the two ends of its hue: on mid-tone surfaces the one colour
        # readable on all of them is often near black or near white.
        _, Cf, hf, _ = cs.to_oklch(fg)
        wants += [cs.from_oklch(end, Cf, hf, a) for end in (0.0, 1.0)]
        cands = [c for w in wants for c in options(fg, w, a, cap)]
        # Among the allowed moves, the one closest to the target that passes
        # everywhere, else the one that fails fewest and gets furthest here.
        best = min(cands, key=lambda c: (unreadable_on(c), cs.contrast_ratio(c, bg) < target,
                                         cs.delta_e(c, fg) if unreadable_on(c) == 0
                                         else -cs.contrast_ratio(c, bg)))
        if (cs.contrast_ratio(best, bg) > now and unreadable_on(best) <= unreadable_on(fg)
                and _move(fg, best, fg_followers)):
            moved.append(".".join(token))
    return moved


__all__ = [
    "EXPLICIT_MAX_DE", "BORDER_MAX_DE", "SEPARATION_RATIOS", "separation", "enforce",
    "CONTRAST_TARGETS", "CONTRAST_LEVELS", "CONTRAST_PAIRS", "Pair",
    "SEPARATION_TARGETS", "SEPARATION_PAIRS", "DEPTH_LEVELS",
    "Finding", "audit", "lightness_gap",
]
