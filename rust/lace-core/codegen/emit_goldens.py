#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Emit the Phase-1 parity oracles under `rust/lace-core/tests/fixtures/`.

- `themes/<name>.json` — `build_theme` output for all 27 themes
  (`default` = `BASE_DOCK_DEFAULTS`), keys lower-cased, sorted.
- `themes/_groups.json` — `theme_groups()` presentation order.
- `themes/_resolved_default_<category>.json` — `get_all()` per category
  after applying `"default"` (schema defaults merged under the engine
  output, colours as `[r,g,b,a]`); pins the future style-manager merge.

Usage (from repo root):
    QT_QPA_PLATFORM=offscreen .venv/Scripts/python.exe \\
        rust/lace-core/codegen/emit_goldens.py
"""

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from PySide6.QtGui import QColor  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from lace.dock_custom_theme import DOCK_THEMES, THEME_SPECS  # noqa: E402
from lace.dock_style_manager import get_dock_style_manager, theme_groups  # noqa: E402
from lace.dock_theme import DockStyleCategory  # noqa: E402

OUT_DIR = REPO / "rust" / "lace-core" / "tests" / "fixtures" / "themes"


def jsonable(value):
    if isinstance(value, QColor):
        return list(value.getRgb())
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    return value


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    names = ["default", *THEME_SPECS]
    assert set(DOCK_THEMES) == set(names), set(DOCK_THEMES) ^ set(names)
    for name in names:
        theme = DOCK_THEMES[name] if name != "default" else \
            __import__("lace.dock_theme", fromlist=["BASE_DOCK_DEFAULTS"]).BASE_DOCK_DEFAULTS
        payload = {cat.name.lower(): jsonable(tokens) for cat, tokens in theme.items()}
        assert set(payload) == {c.name.lower() for c in DockStyleCategory}, name
        (OUT_DIR / f"{name}.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    groups = theme_groups()
    (OUT_DIR / "_groups.json").write_text(
        json.dumps([[title, [[label, key] for label, key in choices]]
                    for title, choices in groups],
                   indent=2, sort_keys=False) + "\n", encoding="utf-8")

    app = QApplication.instance() or QApplication([])
    sm = get_dock_style_manager()
    assert sm.apply_theme("default")
    for cat in DockStyleCategory:
        payload = {token: jsonable(value) for token, value in sm.get_all(cat).items()}
        (OUT_DIR / f"_resolved_default_{cat.name.lower()}.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"wrote {len(names)} themes + groups + 8 resolved-default files to {OUT_DIR}")


if __name__ == "__main__":
    main()
