# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


"""Theme kit command line.

    python -m lace.theme_kit derive --base "#1b1d23" --accent "#4f8cff" --chassis edge --out my_theme.json
    python -m lace.theme_kit audit my_theme.json
    python -m lace.theme_kit audit --preset slate_amber
    python -m lace.theme_kit family my_theme.json --out-dir themes/
    python -m lace.theme_kit chassis --preset violet_haze
    python -m lace.theme_kit studio --preset slate_amber

``audit`` exits 1 when a floor is missed (the theme's own colours included;
``--allow-capped`` forgives those), so it can gate CI on a project's themes.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from lace.theme_contrast import CONTRAST_LEVELS, DEPTH_LEVELS
from lace.theme_kit import (CHASSIS, audit, chassis_of, compose, derive, export, family,
                            variant_of)


def _load(path: Optional[str], preset: Optional[str]) -> Tuple[object, str]:
    """A ThemeSpec and a name, from a JSON file or a Lace preset."""
    if preset:
        from lace.dock_custom_theme import THEME_SPECS
        if preset not in THEME_SPECS:
            raise SystemExit(f"unknown preset {preset!r}; one of: {', '.join(THEME_SPECS)}")
        return THEME_SPECS[preset], preset
    if not path:
        raise SystemExit("give a theme JSON file or --preset NAME")
    from lace.theme_models import ThemeJson
    model = ThemeJson.load(path)
    return model.to_theme_spec(), model.name or Path(path).stem


def _source(p: argparse.ArgumentParser) -> None:
    p.add_argument("file", nargs="?", help="theme JSON file")
    p.add_argument("--preset", help="a built-in Lace preset instead of a file")


def cmd_derive(a) -> int:
    pal = derive(a.base, a.accent, a.text, surface=a.surface, border=a.border,
                 contrast=a.contrast, depth=a.depth, selection=a.selection,
                 title_mode=a.title_mode, hover_mode=a.hover_mode,
                 neutral_tint=a.neutral_tint, status=a.status)
    spec = compose(pal, a.chassis)
    text = export.to_json(spec, a.out, name=a.name)
    if a.out is None:
        sys.stdout.write(text)
    report = audit(spec, clipped=pal.clipped)
    for line in report.lines():
        print(line, file=sys.stderr)
    return 0


def cmd_audit(a) -> int:
    spec, name = _load(a.file, a.preset)
    report = audit(spec, contrast=a.contrast, depth=a.depth)
    print(name)
    for line in report.lines():
        print(line)
    ok = report.passed if a.allow_capped else report.strict_passed
    return 0 if ok else 1


def cmd_family(a) -> int:
    spec, name = _load(a.file, a.preset)
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    own = variant_of(spec)
    for variant, member in family(spec).items():
        key = name if variant == own else f"{name}_{variant}"
        path = out / f"{key}.json"
        export.to_json(member, path, name=key)
        report = audit(member)
        print(f"{path}  {'(source) ' if variant == own else ''}{report.lines()[0]}")
    return 0


def cmd_chassis(a) -> int:
    if not a.file and not a.preset:
        for name, tokens in CHASSIS.items():
            print(f"{name:8} {len(tokens):2} tokens")
        return 0
    spec, name = _load(a.file, a.preset)
    chassis, overrides = chassis_of(spec)
    print(f"{name}: chassis {chassis!r} + {len(overrides)} overrides")
    for key, value in overrides.items():
        print(f"  {key} = {value!r}")
    return 0


def cmd_studio(a) -> int:
    from lace.theme_kit.studio import run
    spec, name = _load(a.file, a.preset) if (a.file or a.preset) else (None, "my_theme")
    return run(spec, name, screenshot=a.screenshot, tab=a.tab, zoom=a.zoom)


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m lace.theme_kit", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("derive", help="a theme from seed colours")
    d.add_argument("--base", required=True)
    d.add_argument("--accent", required=True)
    d.add_argument("--text")
    d.add_argument("--surface")
    d.add_argument("--border")
    d.add_argument("--chassis", default="classic", choices=list(CHASSIS))
    d.add_argument("--contrast", default="normal", choices=CONTRAST_LEVELS)
    d.add_argument("--depth", default="subtle", choices=DEPTH_LEVELS)
    d.add_argument("--selection", default="solid", choices=("solid", "tint"))
    d.add_argument("--title-mode", default="darker", choices=("darker", "lighter"))
    d.add_argument("--hover-mode", default="lighter", choices=("darker", "lighter"))
    d.add_argument("--neutral-tint", type=float, default=0.0)
    d.add_argument("--status", action="store_true", help="also derive status colours")
    d.add_argument("--name")
    d.add_argument("--out", help="JSON file to write; stdout if omitted")
    d.set_defaults(run=cmd_derive)

    au = sub.add_parser("audit", help="check a theme's contrast and separation")
    _source(au)
    au.add_argument("--contrast", choices=CONTRAST_LEVELS)
    au.add_argument("--depth", choices=DEPTH_LEVELS)
    au.add_argument("--allow-capped", action="store_true",
                    help="pass even if the theme's own colours miss a floor")
    au.set_defaults(run=cmd_audit)

    f = sub.add_parser("family", help="dark / neutral / light members of a theme")
    _source(f)
    f.add_argument("--out-dir", required=True)
    f.set_defaults(run=cmd_family)

    c = sub.add_parser("chassis", help="list chassis, or find a theme's")
    _source(c)
    c.set_defaults(run=cmd_chassis)

    s = sub.add_parser("studio", help="build a theme by eye in the Theme Studio")
    _source(s)
    s.add_argument("--screenshot", help="save the window to this PNG and quit")
    s.add_argument("--tab", type=int, default=0, help="preview tab: 0 layout, 1 controls")
    s.add_argument("--zoom", type=int, default=100, help="control gallery zoom, 100-400")
    s.set_defaults(run=cmd_studio)

    a = ap.parse_args(argv)
    return a.run(a)


if __name__ == "__main__":
    sys.exit(main())
