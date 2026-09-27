"""Colour drift of every theme token against the 0.7.6 snapshot, with a budget.

    <python> dev_smoke/theme_drift.py [--themes all] [--detail THEME ...]

Each changed token is measured as OKLab ΔE and classed:

- **explicit**: a colour the theme sets itself (dock_theme.explicit_tokens).
  May move only slightly (theme_contrast.EXPLICIT_MAX_DE), and only where it
  missed a contrast or separation rule; if the cap stops it short, that is
  reported as "capped", not failed.
- **text**: a foreground in theme_contrast.CONTRAST_PAIRS that isn't
  explicit. May move as far as its contrast floor needs; listed, not budgeted.
- **derived**: every other colour (surfaces, hovers, bevels). The OKLCH
  steps replace HLS ones, so these move more: budget DERIVED_MAX_DE.

Exits non-zero when a token is over budget or a theme misses a rule.
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from lace import color_science as cs
from lace.theme_contrast import CONTRAST_PAIRS, EXPLICIT_MAX_DE, audit
from tests.baselines.theme_tokens import SNAPSHOT, tokens
from lace.dock_theme import explicit_tokens
from tests.theme_sets import FIXTURES, load, resolve

DERIVED_MAX_DE = 0.15
TEXT_TOKENS = {".".join(p.token) for p in CONTRAST_PAIRS}


def spec_for(key):
    if key.startswith("kilim_"):
        from lace.theme_models import ThemeJson
        return ThemeJson.load(FIXTURES / f"{key}.json").to_theme_spec()
    from lace.dock_custom_theme import THEME_SPECS
    return THEME_SPECS[key]


def is_colour(v):
    return isinstance(v, list) and len(v) in (3, 4) and all(isinstance(x, int) for x in v)


def drift(key, base, explicit):
    """[(token, class, ΔE, old, new)] for every changed colour token."""
    now, then = tokens(key), base[key]
    # A token sharing its colour with a text token is that text (the badge
    # text is the muted text; the overlay frame is the title's active edge).
    text_values = {tuple(now[c][t]) for c, t in (n.split(".") for n in TEXT_TOKENS)
                   if c in now and is_colour(now[c].get(t))}
    rows = []
    for cat in sorted(set(now) | set(then)):
        for tok in sorted(set(now.get(cat, {})) | set(then.get(cat, {}))):
            a, b = then.get(cat, {}).get(tok), now.get(cat, {}).get(tok)
            if not (is_colour(a) and is_colour(b)) or a == b:
                continue
            name = f"{cat}.{tok}"
            if name in explicit:
                kind = "explicit"
            elif name in TEXT_TOKENS or tuple(b) in text_values:
                kind = "text"
            else:
                kind = "derived"
            rows.append((name, kind, cs.delta_e(a, b), a, b))
    return rows


def over_budget(kind, de):
    if kind == "explicit":
        return de > EXPLICIT_MAX_DE + 0.005
    if kind == "derived":
        return de > DERIVED_MAX_DE
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--themes", default="all")
    ap.add_argument("--detail", nargs="*", default=[], help="themes to list token by token")
    args = ap.parse_args()
    QApplication.instance() or QApplication([])
    base = json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    bad = warned = 0
    print(f"{'theme':24} {'changed':>7} {'explicit':>14} {'derived':>14} {'text':>14}  rules")
    for key in resolve(args.themes):
        explicit = explicit_tokens(spec_for(key))
        rows = drift(key, base, explicit)
        by = {k: [r[2] for r in rows if r[1] == k] for k in ("explicit", "derived", "text")}
        cell = lambda v: f"{len(v):3} max {max(v):.3f}" if v else f"{0:3}          "
        found = audit(load(key))
        # An explicit colour stops at its cap even if that is short of the
        # floor: the author's choice wins over the rule. Reported, not failed.
        capped = [m for m in found if m.token in explicit or m.unreachable]
        misses = [m for m in found if not (m.token in explicit or m.unreachable)]
        over = [r for r in rows if over_budget(r[1], r[2])]
        bad += len(over) + len(misses)
        warned += len(capped)
        flag = "" if not (over or misses) else "  <-- " + ", ".join(
            [f"{r[0]} over ({r[2]:.3f})" for r in over] +
            [f"{m.token} {m.value}/{m.target}" for m in misses])
        note = "" if not capped else "  (capped: " + ", ".join(
            f"{m.token} {m.value}/{m.target}" + (" unreachable" if m.unreachable else "")
            for m in capped) + ")"
        print(f"{key:24} {len(rows):7} {cell(by['explicit']):>14} {cell(by['derived']):>14} "
              f"{cell(by['text']):>14}  {len(misses)}{flag}{note}")
        if key in args.detail:
            for name, kind, de, a, b in sorted(rows, key=lambda r: -r[2]):
                print(f"    {kind:8} {de:.3f}  {name:40} {a} -> {b}")
    print(f"\nbudget: explicit <= {EXPLICIT_MAX_DE}, derived <= {DERIVED_MAX_DE}, "
          "text = as far as its floor needs")
    print(f"{warned} capped short of their floor (reported, not failed): an explicit colour "
          "at its drift cap, or a floor no colour reaches on the theme's own surface")
    print("OK" if not bad else f"{bad} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
