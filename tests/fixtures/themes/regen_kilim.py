# -*- coding: utf-8 -*-
"""Regenerate the Kilim theme fixtures from a Kilim checkout.

Usage (from the repo root):
    <python> tests/fixtures/themes/regen_kilim.py <path-to-Kilim>

Lace can't import Kilim (its palettes live in Kilim's Rust core), so the ten
Kilim themes are kept here as JSON files and loaded through load_theme_json().
This script rebuilds them the way ``python/kilim/qt_themes.py`` does: the
palette from ``crates/kilim-core/src/kilim_themes.rs`` plus one of the two
chassis below. The chassis are copied from qt_themes.py; if Kilim changes
them, update them here too.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

PALETTE_SRC = "crates/kilim-core/src/kilim_themes.rs"
BUILDER_SRC = "python/kilim/qt_themes.py"

# qt_themes.KILIM_GEOMETRY
CLASSIC = dict(
    corner_radius=4,
    tab_radius=4,
    border_width=1.5,
    title_margin=0.5,
    content_margin=0.5,
    tab_dimming=True,
    title_mode="darker",
    hover_mode="darker",
)

# qt_themes.KILIM_NEO_GEOMETRY
NEO = dict(
    corner_radius=10,
    border_width=1.5,
    title_height=32,
    title_padding_left=0,
    title_padding_right=8,
    title_button_spacing=6,
    title_margin=0,
    tab_radius=8,
    tab_margin=3,
    content_margin=[8, 2],
    indicator_width=1.5,
    indicator_position="bottom",
    tab_dimming=True,
    title_mode="darker",
    hover_mode="lighter",
    title_border_bottom=1.5,
    sidebar_tab_flat_edge="none",
    sidebar_tab_border_width=1.5,
    sidebar_indicator_width=1.5,
)

_FIELD = re.compile(r'^\s*(lace_key|neo_key|is_light|bg|surface|border|text|accent):\s*"?([^",]+)"?,',
                    re.M)


def parse_palettes(rust_source: str) -> list:
    """One dict per ``KilimThemeDef { ... }`` block, keeping only the chrome fields."""
    blocks = rust_source.split("KilimThemeDef {")[2:]  # [0] precedes, [1] is the struct definition
    palettes = []
    for block in blocks:
        fields = dict(_FIELD.findall(block))
        fields["is_light"] = fields.get("is_light") == "true"
        palettes.append(fields)
    return palettes


def build(palette: dict, neo: bool) -> dict:
    """Mirror of qt_themes._spec / _per_palette_neo."""
    theme = dict(
        base=palette["bg"],
        accent=palette["accent"],
        text=palette["text"],
        surface=palette.get("surface", palette["bg"]),
        border=palette.get("border", palette["bg"]),
        focus_border_color=palette["accent"],
        is_light=palette["is_light"],
    )
    theme.update(NEO if neo else CLASSIC)
    if neo:
        theme.update(
            title_border_focus_color=palette["accent"],
            sidebar_tab_border_color=palette.get("border", palette["bg"]),
            sidebar_tab_border_active_color=palette["accent"],
            sidebar_tab_border_hover_color=palette["accent"],
        )
    return theme


def main(kilim_root: Path) -> None:
    commit = subprocess.run(
        ["git", "-C", str(kilim_root), "log", "-1", "--format=%h %cs", "--",
         PALETTE_SRC, BUILDER_SRC],
        capture_output=True, text=True, check=True).stdout.strip()
    palettes = parse_palettes((kilim_root / PALETTE_SRC).read_text(encoding="utf-8"))
    assert len(palettes) == 5, f"expected 5 Kilim palettes, found {len(palettes)}"

    for palette in palettes:
        for neo in (False, True):
            key = palette["neo_key" if neo else "lace_key"]
            theme = {
                "name": key,
                "_source": f"Kilim {commit}: {PALETTE_SRC} + {BUILDER_SRC} "
                           f"({'KILIM_NEO_GEOMETRY' if neo else 'KILIM_GEOMETRY'}); "
                           "regenerate with tests/fixtures/themes/regen_kilim.py",
            }
            theme.update(build(palette, neo))
            out = HERE / f"{key}.json"
            out.write_text(json.dumps(theme, indent=4) + "\n", encoding="utf-8")
            print(f"wrote {out.name}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]))
