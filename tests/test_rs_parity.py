# -*- coding: utf-8 -*-
"""Rust-core parity tests — Phase 6 exit gate.

Every 0.7.6 theme/layout JSON must produce identical output through the old
Python implementation and through `_lace_rs`, so the port can take over
without anyone noticing. Golden files live in
`rust/lace-core/tests/fixtures/`; the oracles here are computed live from
`lace.*` instead, so the two sides cannot share a stale fixture.
"""

import json
from pathlib import Path

import pytest

import _lace_rs
import lace_rs
from lace.dock_custom_theme import DOCK_THEMES, THEME_SPECS
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import DockStyleCategory, deep_to_serializable
from lace.layout_serializer import (
    LayoutError,
    LayoutIOError,
    InvalidFormatError,
    RestoreFailureError,
)

FIXTURES = Path("rust/lace-core/tests/fixtures")
LAYOUTS = FIXTURES / "layouts"


def _norm_theme(theme):
    """`{CATEGORY: tokens}` with JSON-safe values, keys sorted, for `==`."""
    flat = {cat.name.lower(): deep_to_serializable(tokens) for cat, tokens in theme.items()}
    return json.loads(json.dumps(flat, sort_keys=True))


def test_extension_error_hierarchy_matches_python():
    assert issubclass(_lace_rs.LayoutIOError, _lace_rs.LayoutError)
    assert issubclass(_lace_rs.InvalidFormatError, _lace_rs.LayoutError)
    assert issubclass(_lace_rs.RestoreFailureError, _lace_rs.LayoutError)
    assert not issubclass(_lace_rs.LayoutIOError, _lace_rs.InvalidFormatError)
    # Same names as lace.layout_serializer, so `except` clauses transfer.
    assert _lace_rs.LayoutError.__name__ == LayoutError.__name__
    assert _lace_rs.InvalidFormatError.__name__ == InvalidFormatError.__name__
    assert _lace_rs.RestoreFailureError.__name__ == RestoreFailureError.__name__
    assert _lace_rs.LayoutIOError.__name__ == LayoutIOError.__name__


def test_available_themes_match_specs():
    assert set(_lace_rs.available_themes()) == {"default"} | set(THEME_SPECS)
    assert _lace_rs.available_themes()[0] == "default"


@pytest.mark.parametrize("name", ["default", *sorted(THEME_SPECS)])
def test_build_theme_matches_python_engine(name):
    from lace.dock_custom_theme import THEME_SPECS as SPECS
    from lace.dock_theme import BASE_DOCK_DEFAULTS, build_theme

    expected = _norm_theme(
        BASE_DOCK_DEFAULTS if name == "default" else build_theme(SPECS[name])
    )
    assert json.loads(_lace_rs.build_theme(name)) == expected


def test_build_merged_theme_matches_manager_get_all(qapp):
    sm = get_dock_style_manager()
    assert sm.apply_theme("cyberpunk_neon")
    expected = json.loads(json.dumps(
        {cat.name.lower(): deep_to_serializable(dict(sm.get_all(cat)))
         for cat in DockStyleCategory},
        sort_keys=True,
    ))
    assert json.loads(_lace_rs.build_merged_theme("cyberpunk_neon")) == expected
    sm.apply_theme("default")


def test_theme_groups_match_python():
    from lace.dock_style_manager import theme_groups

    assert json.loads(json.dumps(lace_rs.theme_groups())) == [
        [title, [[label, key] for label, key in choices]]
        for title, choices in theme_groups()
    ]


def test_validate_layout_accepts_shipped_scenarios():
    for path in sorted(LAYOUTS.glob("*.json")):
        if path.stem in {
            "wrong_type", "future_schema", "version_mismatch", "missing_keys",
            "bad_geometry_zero", "bad_geometry_huge", "bad_geometry_type",
            "sizes_mismatch", "unnamed_widget",
        }:
            continue
        text = path.read_text(encoding="utf-8")
        roster = list(json.loads(text)["widget_states"])
        report = lace_rs.validate_layout(text, 0, roster)
        assert report["warnings"] == [] or path.stem == "legacy", path.stem
        assert report["pruned"] == [], path.stem
        # Save/restore/save stability through the bindings. Legacy files
        # normalize the absent schema field to 0 on re-save.
        expected = json.loads(text)
        if path.stem == "legacy":
            expected = {**expected, "schema": 0}
        assert json.loads(json.dumps(report["doc"], sort_keys=True)) == \
            json.loads(json.dumps(expected, sort_keys=True)), path.stem


@pytest.mark.parametrize("name,exc", [
    ("wrong_type", "_lace_rs.InvalidFormatError"),
    ("future_schema", "_lace_rs.InvalidFormatError"),
    ("version_mismatch", "_lace_rs.InvalidFormatError"),
    ("missing_keys", "_lace_rs.InvalidFormatError"),
    ("bad_geometry_zero", "_lace_rs.InvalidFormatError"),
    ("bad_geometry_huge", "_lace_rs.InvalidFormatError"),
    ("bad_geometry_type", "_lace_rs.InvalidFormatError"),
    ("sizes_mismatch", "_lace_rs.RestoreFailureError"),
    ("unnamed_widget", "_lace_rs.RestoreFailureError"),
])
def test_validate_layout_rejects_with_matching_errors(name, exc):
    text = (LAYOUTS / f"{name}.json").read_text(encoding="utf-8")
    expected = eval(exc)  # noqa: S307 - test-local parametrize, no input
    with pytest.raises(expected):
        lace_rs.validate_layout(text)
    # ... and every one of them is still catchable as LayoutError.
    with pytest.raises(_lace_rs.LayoutError):
        lace_rs.validate_layout(text)


def test_ops_roundtrip_through_bindings_matches_core():
    doc = lace_rs.blank_layout(0)
    doc = lace_rs.dock_widget(doc, "Alpha", "center")
    doc = lace_rs.dock_widget(doc, "Beta", "center")
    doc = lace_rs.dock_widget(doc, "Gamma", "right", target=(0, []))
    doc = lace_rs.set_current(doc, 0, [0], "Beta")
    doc, cid = lace_rs.float_widget(doc, "Gamma")
    assert cid.startswith("float-")
    doc = lace_rs.move_widget(doc, "Gamma", "center", 0, [])
    doc, removed = lace_rs.gc_empty_floats(doc)
    assert removed == [cid]
    doc = lace_rs.pin_widget(doc, "Beta", "left")
    doc = lace_rs.unpin_widget(doc, "Beta")
    doc, found = lace_rs.set_closed(doc, "Beta", True)
    assert found
    assert lace_rs.drop_edges(doc, 0) == ["center"], "solo area offers centre only"
    report = lace_rs.validate_layout(doc)
    assert report["warnings"] == [] and report["pruned"] == []
    doc, found = lace_rs.remove_widget(doc, "Beta")
    assert found
    assert not lace_rs.remove_widget(doc, "Beta")[1]


def test_ops_reject_like_python():
    doc = lace_rs.blank_layout(0)
    with pytest.raises(ValueError, match="unknown edge"):
        lace_rs.dock_widget(doc, "X", "sideways")
    with pytest.raises(_lace_rs.InvalidFormatError):
        lace_rs.validate_layout("{not json")
    with pytest.raises(_lace_rs.LayoutError):
        lace_rs.move_widget(doc, "Nobody", "center", 0, [])


VALID_THEME = {
    "name": "ParityTheme",
    "base": [14, 11, 28, 255],
    "accent": "#ff007f",
    "text": [245, 245, 255, 255],
    "corner_radius": 10,
    "content_margin": [8, 2],
    "indicator_position": "bottom",
    "tab_dimming": True,
    "future_unknown_key": "ignored",
}


def test_load_theme_file_matches_python(tmp_path):
    from lace.theme_models import load_theme_json

    path = tmp_path / "theme.json"
    path.write_text(json.dumps(VALID_THEME), encoding="utf-8")
    expected = json.loads(json.dumps(
        {cat.name.lower(): deep_to_serializable(tokens)
         for cat, tokens in load_theme_json(path).items()},
        sort_keys=True,
    ))
    assert json.loads(_lace_rs.load_theme_file(str(path))) == expected
    assert lace_rs.load_theme_file(path)["core"]["accent_color"] == [255, 0, 127, 255]


@pytest.mark.parametrize("payload,exc", [
    ({**VALID_THEME, "base": [300, 0, 0]}, "ValidationError"),
    ({**VALID_THEME, "text": True}, "ValidationError"),
    ({**VALID_THEME, "text": [1, 2, 3, 4, 5]}, "ValidationError"),
    ({k: v for k, v in VALID_THEME.items() if k != "accent"}, "ValidationError"),
])
def test_invalid_theme_files_raise_validation(tmp_path, payload, exc):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(getattr(_lace_rs, exc)):
        lace_rs.load_theme_file(path)


def test_malformed_theme_file_raises_value_error(tmp_path):
    path = tmp_path / "bad_syntax.json"
    path.write_text('{ "base": [1, 2, 3] ', encoding="utf-8")
    with pytest.raises(ValueError):
        lace_rs.load_theme_file(path)


def test_missing_theme_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        lace_rs.load_theme_file(tmp_path / "nope.json")


def test_dock_themes_registry_still_intact():
    assert set(DOCK_THEMES) == {"default"} | set(THEME_SPECS)
