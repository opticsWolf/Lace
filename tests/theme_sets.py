# -*- coding: utf-8 -*-
"""The theme sets the 0.8 plan tests against (docs/IMPROVEMENT_PLAN_v0.8.md).

Three staged sets, picked by scope of work, plus ALL for numbers-only checks:

- QUICK (5): one theme per axis — dark classic, light neo, the reference
  slate, neon, and a light code classic.
- REGULAR (11): the Kilim family plus neon, slate and two code classics.
- FULL (20): REGULAR plus nine themes chosen for ground they add.
- ALL: every Lace preset and every Kilim fixture.

Kilim themes are loaded from tests/fixtures/themes/kilim_*.json (see
regen_kilim.py there); everything else is a Lace preset.
"""

import os
from pathlib import Path
from typing import Any, Dict, List

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "themes"

QUICK: List[str] = [
    "kilim_dark",
    "kilim_light_neo",
    "slate_amber",
    "cyberpunk_neon",
    "solarized_light",
]

REGULAR: List[str] = [
    "kilim_dark",
    "kilim_midnight",
    "kilim_warm",
    "kilim_neutral",
    "kilim_light",
    "kilim_midnight_neo",
    "kilim_light_neo",
    "cyberpunk_neon",
    "slate_amber",
    "dracula",
    "solarized_light",
]

FULL: List[str] = REGULAR + [
    "midnight",
    "monokai",
    "nordic",
    "catppuccin",
    "solarized_dark",
    "neon_dusk",
    "cyberpunk_edge_neutral",
    "violet_haze_light",
    "midnight_haze",
]


def kilim_keys() -> List[str]:
    return sorted(p.stem for p in FIXTURES.glob("kilim_*.json"))


def all_themes() -> List[str]:
    from lace.dock_custom_theme import DOCK_THEMES
    return sorted(DOCK_THEMES) + kilim_keys()


def resolve(stage: str) -> List[str]:
    """Theme keys for a stage name; ``auto`` asks select_theme_set."""
    stage = stage.lower()
    if stage == "auto":
        from tests.select_theme_set import select_stage
        stage = select_stage()
    if stage == "all":
        return all_themes()
    return list({"quick": QUICK, "regular": REGULAR, "full": FULL}[stage])


def from_env(default: str = "quick") -> List[str]:
    """The set named by LACE_TEST_THEMES (set by run_all.py / pytest --themes)."""
    return resolve(os.environ.get("LACE_TEST_THEMES", default))


def load(key: str) -> Dict[Any, Dict[str, Any]]:
    """The full theme token dict for a key, preset or Kilim fixture."""
    if key.startswith("kilim_"):
        from lace.theme_models import load_theme_json
        return load_theme_json(FIXTURES / f"{key}.json")
    from lace.dock_custom_theme import DOCK_THEMES
    return DOCK_THEMES[key]
