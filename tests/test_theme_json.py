# -*- coding: utf-8 -*-
"""JSON theme loading tests — ThemeJson / load_theme_json (theme_models.py).

Pytest counterpart of dev_smoke/smoke_theme_json.py, using tmp_path fixtures:
valid loading (hex + RGBA colors), unknown-key tolerance, pydantic validation
failures, and application through the style manager.
"""

import json

import pytest

from lace import ThemeJson, load_theme_json
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import DockStyleCategory, deep_to_serializable

VALID_THEME = {
    "name": "PytestTheme",
    "base": [14, 11, 28, 255],
    "accent": "#ff007f",                       # hex string
    "text": [245, 245, 255, 255],
    "surface": [24, 19, 44, 255],
    "focus_border_color": "#00f0ff",
    "tooltip_bg": "#1b2430",
    "tooltip_text": [225, 230, 240, 255],
    "title_mode": "darker",
    "hover_mode": "lighter",
    "corner_radius": 10,
    "border_width": 1.5,
    "title_height": 32,
    "tab_radius": 8,
    "content_margin": [8, 2],
    "indicator_width": 2.0,
    "indicator_position": "bottom",
    "tab_dimming": True,
    "future_unknown_key": "ignored",
}


@pytest.fixture()
def theme_file(tmp_path):
    path = tmp_path / "theme.json"
    path.write_text(json.dumps(VALID_THEME), encoding="utf-8")
    return path


def test_load_valid_json_theme(theme_file):
    theme = ThemeJson.load(theme_file)
    assert theme.name == "PytestTheme"
    assert theme.accent == "#ff007f"           # hex kept as-is in the model
    assert theme.content_margin == [8, 2]
    assert theme.corner_radius == 10


def test_load_ignores_unknown_keys(theme_file):
    theme = ThemeJson.load(theme_file)
    assert "future_unknown_key" not in theme.model_dump()


def test_build_theme_dict_covers_all_categories(theme_file):
    theme_dict = ThemeJson.load(theme_file).build_theme_dict()
    assert set(theme_dict) == set(DockStyleCategory)


def test_hex_colors_resolve_to_rgba(theme_file):
    theme_dict = load_theme_json(theme_file)
    core = theme_dict[DockStyleCategory.CORE]
    assert deep_to_serializable(core["accent_color"]) == [255, 0, 127, 255]
    assert deep_to_serializable(core["focus_border_color"]) == [0, 240, 255, 255]
    assert deep_to_serializable(core["tooltip_bg"]) == [27, 36, 48, 255]
    assert deep_to_serializable(core["tooltip_text"]) == [225, 230, 240, 255]


def test_load_theme_json_helper_matches_build(theme_file):
    assert load_theme_json(theme_file) == ThemeJson.load(theme_file).build_theme_dict()


def test_applying_json_theme_dict(qapp, theme_file):
    sm = get_dock_style_manager()
    sm.apply_theme_dict(load_theme_json(theme_file))
    assert sm.get(DockStyleCategory.CORE, "canvas_bg").getRgb()[:3] == (14, 11, 28)
    assert sm.get(DockStyleCategory.CORE, "accent_color").getRgb()[:3] == (255, 0, 127)
    assert sm.get(DockStyleCategory.TAB, "corner_radius") == 8
    assert sm.get(DockStyleCategory.PANEL, "content_margin") == [8.0, 2.0]
    assert sm.get(DockStyleCategory.CORE, "tooltip_bg").getRgb()[:3] == (27, 36, 48)
    assert sm.get(DockStyleCategory.CORE, "tooltip_text").getRgb()[:3] == (225, 230, 240)


# ---------------------------------------------------------------------------
# Validation failures
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("payload,error", [
    ({**VALID_THEME, "base": [300, 0, 0]}, "ValidationError"),
    ({**VALID_THEME, "text": True}, "ValidationError"),          # bool is not a colour
    ({**VALID_THEME, "text": [1, 2, 3, 4, 5]}, "ValidationError"),  # too many channels
    ({**VALID_THEME, "text": {"r": 1}}, "ValidationError"),     # dict is not a colour
    ({k: v for k, v in VALID_THEME.items() if k != "accent"}, "ValidationError"),
])
def test_invalid_theme_payloads_raise(tmp_path, payload, error):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(Exception) as excinfo:
        ThemeJson.load(path)
    assert type(excinfo.value).__name__ == error


def test_malformed_json_raises_json_decode_error(tmp_path):
    path = tmp_path / "bad_syntax.json"
    path.write_text('{ "base": [1, 2, 3] ', encoding="utf-8")
    with pytest.raises(Exception) as excinfo:
        ThemeJson.load(path)
    assert type(excinfo.value).__name__ == "JSONDecodeError"


def test_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        ThemeJson.load(tmp_path / "nope.json")
