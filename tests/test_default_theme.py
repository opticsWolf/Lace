# -*- coding: utf-8 -*-
"""The default theme — an alias, not a preset.

``"default"`` names whichever preset or JSON theme ``set_default_theme`` (or a
settings file) chose; ``dark`` unless told otherwise. It is the look before any
theme is applied and the floor every theme dict is applied over, and menus do
not list it.
"""

import json

import pytest

import lace.dock_style_manager as dsm
from lace import get_default_theme, load_settings, set_default_theme, theme_choices
from lace.dock_custom_theme import DOCK_THEMES
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import DockStyleCategory

CORE = DockStyleCategory.CORE


@pytest.fixture(autouse=True)
def restore_default(qapp):
    source, tokens = dsm._default_source, dsm._default_tokens
    yield
    dsm._default_source, dsm._default_tokens = source, tokens
    get_dock_style_manager().apply_theme("default")


def _canvas(theme=None):
    manager = get_dock_style_manager()
    if theme is not None:
        assert manager.apply_theme(theme)
    return manager.get(CORE, "canvas_bg").name()


def test_default_is_dark_and_not_a_menu_entry():
    assert get_default_theme() == "dark"
    assert _canvas("default") == _canvas("dark")
    assert "default" not in DOCK_THEMES
    assert "default" not in {key for _, key in theme_choices()}


def test_a_preset_can_be_the_default():
    set_default_theme("mocha")
    assert get_default_theme() == "mocha"
    assert _canvas("default") == _canvas("mocha")


def test_the_default_is_the_floor_for_partial_theme_dicts():
    """A theme dict that leaves a token out takes it from the default."""
    set_default_theme("light")
    manager = get_dock_style_manager()
    manager.apply_theme_dict({CORE: {"accent_color": [255, 0, 0, 255]}})
    assert manager.get(CORE, "canvas_bg").name() == _canvas("light")


def test_switching_the_default_repaints_a_manager_showing_it():
    manager = get_dock_style_manager()
    manager.apply_theme("default")
    set_default_theme("cream")
    assert manager.current_theme == "default"
    assert _canvas() == _canvas("cream")


def test_switching_the_default_leaves_a_named_preset_alone():
    manager = get_dock_style_manager()
    before = _canvas("monokai")
    set_default_theme("cream")
    assert manager.current_theme == "monokai"
    assert _canvas() == before


def test_an_unknown_source_is_refused_and_changes_nothing(tmp_path):
    with pytest.raises(ValueError):
        set_default_theme("no_such_theme")
    with pytest.raises(ValueError):
        set_default_theme(tmp_path / "missing.json")
    assert get_default_theme() == "dark"


def _theme_file(tmp_path):
    path = tmp_path / "house.json"
    path.write_text(json.dumps({
        "name": "House", "base": [40, 10, 10, 255],
        "accent": "#ff8800", "text": [240, 240, 240, 255],
    }), encoding="utf-8")
    return path


def test_a_json_theme_can_be_the_default(tmp_path):
    path = _theme_file(tmp_path)
    set_default_theme(path)
    assert get_default_theme() == path
    red = get_dock_style_manager()
    red.apply_theme("default")
    canvas = red.get(CORE, "canvas_bg")
    assert canvas.red() > canvas.green() and canvas.red() > canvas.blue()


def test_settings_file_names_a_preset(tmp_path):
    settings = tmp_path / "lace.json"
    settings.write_text(json.dumps({"default_theme": "slate", "app_key": 1}),
                        encoding="utf-8")
    assert load_settings(settings)["app_key"] == 1, "the app's own keys come back"
    assert get_default_theme() == "slate"


def test_settings_file_names_a_json_theme_relative_to_itself(tmp_path):
    _theme_file(tmp_path)
    settings = tmp_path / "lace.json"
    settings.write_text(json.dumps({"default_theme": "house.json"}), encoding="utf-8")
    load_settings(settings)
    assert get_default_theme() == tmp_path / "house.json"


def test_settings_file_without_the_key_changes_nothing(tmp_path):
    settings = tmp_path / "lace.json"
    settings.write_text("{}", encoding="utf-8")
    load_settings(settings)
    assert get_default_theme() == "dark"
