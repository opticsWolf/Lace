# Parity fixtures (populated in Phases 1–2)

This directory will hold machine-readable oracles extracted from the Python
test-suite so the Rust port can assert byte-level compatibility:

| Phase | Fixture | Source |
|---|---|---|
| 1 | `theme_presets.json` — all 27 resolved `build_theme()` outputs (focused + unfocused) | `tests/test_theme_counterparts.py`, `test_theme_presets.py` |
| 1 | `theme_schema.json` — accepted `ThemeJson` keys | `tests/test_theme_schema.py`, `test_theme_json.py` |
| 2 | `layouts/*.json` — 0.7.x `save_state()` outputs | `tests/test_layout_roundtrip.py`, `test_area_insertion.py` |

Rule: fixtures are copied verbatim from Python-side outputs, never
hand-edited. If a fixture disagrees with the Rust code, the Rust code is
wrong until proven otherwise.
