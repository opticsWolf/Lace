# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


"""Audit: check a built theme against the Phase 2 contrast and separation
rules, plus a few checks only a theme author needs.

The rules are :mod:`lace.theme_contrast`'s, so a theme passes here exactly
when it passes the engine's own contrast table. Misses split three ways:

- **failures**: a derived colour short of its floor. The engine fixes these
  itself, so one here is a bug, or a spec the engine can't reconcile.
- **capped**: a colour the spec set itself, short of its floor. The engine
  only nudges explicit colours (``EXPLICIT_MAX_DE``); the author decides.
- **unreachable**: no colour at all meets the floor on that surface; the
  surface itself has to move.

Warnings cover the rest: an accent too close to the base, a focus ring that
vanishes on the panel, colours clipped to fit sRGB while being derived.
"""

from dataclasses import dataclass, field, replace
from typing import Dict, List, NamedTuple, Optional, Sequence, Tuple

from lace import color_science as cs
from lace.dock_theme import ThemeSpec, build_theme, explicit_tokens
from lace.theme_contrast import CONTRAST_TARGETS, Finding, audit as _rules


class Miss(NamedTuple):
    token: str       # "CATEGORY.key"
    surface: str
    value: float     # contrast ratio, or lightness gap for separation
    target: float
    kind: str        # "contrast" | "separation"
    role: str


class Suggestion(NamedTuple):
    token: str
    old: List[int]
    new: List[int]
    dL: float        # OKLCH lightness change


class Warning(NamedTuple):
    kind: str
    message: str


def _hex(c: Sequence[int]) -> str:
    s = "#%02x%02x%02x" % tuple(c[:3])
    return s + ("%02x" % c[3] if len(c) > 3 and c[3] != 255 else "")


@dataclass
class AuditReport:
    contrast: str
    depth: str
    failures: List[Miss] = field(default_factory=list)
    capped: List[Miss] = field(default_factory=list)
    unreachable: List[Miss] = field(default_factory=list)
    warnings: List[Warning] = field(default_factory=list)
    theme: Dict = field(default_factory=dict, repr=False)

    @property
    def passed(self) -> bool:
        """No derived colour misses: the engine's own contrast table passes."""
        return not self.failures

    @property
    def strict_passed(self) -> bool:
        """Every reachable floor is met, the spec's own colours included."""
        return not self.failures and not self.capped

    def suggest(self) -> List[Suggestion]:
        """The smallest lightness change (OKLCH L only, hue and chroma kept)
        that fixes each failing or capped miss."""
        out = []
        by_token: Dict[str, List[Miss]] = {}
        for m in self.failures + self.capped:
            by_token.setdefault(m.token, []).append(m)
        for token, misses in by_token.items():
            fg = _lookup(self.theme, token)
            if fg is None:
                continue
            new = list(fg)
            # A colour can miss on several surfaces (panel text on the panel,
            # a button and a field): one suggestion that clears them all.
            # Every surface here lies on the same side of the colour, so each
            # pass only pushes it further the same way.
            for _ in range(2):
                for m in misses:
                    bg = _lookup(self.theme, m.surface)
                    if bg is None:
                        continue
                    if m.kind == "contrast":
                        new = cs.ensure_contrast(new, list(bg), m.target)
                    else:
                        # Separation: step the surface further from its parent.
                        sign = 1.0 if cs.to_oklch(fg)[0] >= cs.to_oklch(bg)[0] else -1.0
                        gap = abs(cs.to_oklch(new)[0] - cs.to_oklch(bg)[0])
                        if gap < m.target:
                            new = cs.step(new, sign * (m.target - gap + 0.002))
            new = list(new[:len(fg)])
            if new != list(fg):
                out.append(Suggestion(token, list(fg), new,
                                      round(cs.to_oklch(new)[0] - cs.to_oklch(fg)[0], 4)))
        return out

    def lines(self) -> List[str]:
        """A human-readable report."""
        out = [f"contrast={self.contrast} depth={self.depth}: "
               + ("PASS" if self.strict_passed else "PASS (capped colours)" if self.passed
                  else "FAIL")]
        for title, misses in (("failures", self.failures), ("capped", self.capped),
                              ("unreachable", self.unreachable)):
            for m in misses:
                unit = ":1" if m.kind == "contrast" else " dL"
                out.append(f"  {title:11} {m.token} on {m.surface}: "
                           f"{m.value}{unit} < {m.target}{unit}")
        for s in self.suggest():
            out.append(f"  suggest     {s.token}: {_hex(s.old)} -> {_hex(s.new)} (dL {s.dL:+})")
        for w in self.warnings:
            out.append(f"  warning     {w.kind}: {w.message}")
        return out


def _lookup(theme, dotted: str):
    cat, key = dotted.split(".", 1)
    for k, values in theme.items():
        if getattr(k, "name", k) == cat:
            return values.get(key)
    return None


def _miss(f: Finding) -> Miss:
    return Miss(f.token, f.surface, f.value, f.target, f.kind, f.role)


def audit(spec: ThemeSpec, *, contrast: Optional[str] = None, depth: Optional[str] = None,
          clipped: Sequence[str] = ()) -> AuditReport:
    """Check ``spec`` at its own levels, or at ``contrast`` / ``depth``.

    ``clipped``: colour names that lost chroma to fit sRGB while being
    derived (``Palette.clipped``), reported as warnings.
    """
    contrast = contrast or spec.contrast
    depth = depth or spec.depth
    spec = replace(spec, contrast=contrast, depth=depth)
    theme = build_theme(spec)
    explicit = explicit_tokens(spec)
    report = AuditReport(contrast, depth, theme=theme)
    for f in _rules(theme, contrast, depth):
        m = _miss(f)
        if f.unreachable:
            report.unreachable.append(m)
        elif f.token in explicit:
            report.capped.append(m)
        else:
            report.failures.append(m)

    core, panel = _category(theme, "CORE"), _category(theme, "PANEL")
    accent = spec_color(spec.accent)
    ui = CONTRAST_TARGETS["ui"][contrast]
    ratio = cs.contrast_ratio(accent, spec_color(spec.base))
    if ratio < ui:
        report.warnings.append(Warning(
            "accent", f"accent {_hex(accent)} is {ratio:.2f}:1 on the base, "
                      f"under the {ui}:1 UI floor: selections and checks will look faint"))
    focus = core.get("focus_border_color")
    if focus is not None and panel.get("bg_normal") is not None:
        r = cs.contrast_ratio(focus, panel["bg_normal"])
        if r < ui:
            report.warnings.append(Warning(
                "focus", f"focus ring is {r:.2f}:1 on the panel, under the {ui}:1 UI floor"))
    for name in clipped:
        report.warnings.append(Warning("gamut", f"{name} lost chroma to fit sRGB"))
    return report


#: How close (ΔE, OKLab) a spec colour must be to a suggestion's old value to
#: be taken as its source. The engine may have nudged it that far.
FIX_MATCH_DE = 0.08


def apply_fix(spec: ThemeSpec, suggestion: Suggestion) -> Optional[Tuple[ThemeSpec, str]]:
    """``spec`` with ``suggestion`` applied to the spec colour it came from,
    and that field's name; None when no spec colour carries it.

    The source is found by colour, not by name: every spec colour near the
    suggestion's old value is tried, nearest first, and the first one whose
    change clears the miss without adding a new one wins.
    """
    from lace.theme_kit.family import _COLOUR_FIELDS
    before = audit(spec)
    count = len(before.failures) + len(before.capped)
    candidates = []
    for name in _COLOUR_FIELDS:
        value = getattr(spec, name)
        if value is None:
            continue
        rgba = spec_color(value)
        de = cs.delta_e(rgba, suggestion.old)
        if de <= FIX_MATCH_DE:
            candidates.append((de, name, rgba))
    for _, name, rgba in sorted(candidates):
        new = list(suggestion.new[:3]) + [rgba[3] if len(rgba) > 3 else 255]
        fixed = replace(spec, **{name: new})
        after = audit(fixed)
        misses = after.failures + after.capped
        if (len(misses) < count
                and all(m.token != suggestion.token for m in misses)):
            return fixed, name
    return None


def spec_color(value) -> List[int]:
    from lace.theme_kit.derive import to_rgba
    return to_rgba(value)


def _category(theme, name: str) -> Dict:
    for k, values in theme.items():
        if getattr(k, "name", k) == name:
            return values
    return {}


__all__ = ["AuditReport", "Miss", "Suggestion", "Warning", "apply_fix", "audit"]

