# -*- coding: utf-8 -*-
"""Theme preset integrity tests — ARCHITECTURE.md §3.9 (dock_custom_theme.py).

Every preset in THEME_SPECS must build into DOCK_THEMES, cover all eight
DockStyleCategory namespaces with valid RGBA token values, carry sane geometry,
and apply cleanly through the style manager.
"""

import pytest

from lace.dock_custom_theme import THEME_SPECS, DOCK_THEMES
from lace.dock_style_manager import apply_dock_theme, get_dock_style_manager
from lace.dock_theme import (
    DockStyleCategory,
    build_theme,
    resolve_dock_colors,
    is_color_list,
)

COLOR_TOKEN = (
    "canvas_bg", "border_color", "accent_color", "focus_border_color",
    "text_color", "disabled_text_color", "success_color", "warning_color",
    "error_color", "info_color",
)


def test_dock_themes_registry_matches_specs():
    assert set(DOCK_THEMES) == {"default"} | set(THEME_SPECS)
    assert len(DOCK_THEMES) >= 14  # default + 13 named presets


def test_all_presets_build_all_categories():
    for name, spec in THEME_SPECS.items():
        theme = build_theme(spec)
        assert set(theme) == set(DockStyleCategory), name
        assert theme[DockStyleCategory.CORE], f"{name}: empty CORE namespace"


def test_core_color_tokens_are_valid_rgba_lists():
    for name, spec in THEME_SPECS.items():
        core = build_theme(spec)[DockStyleCategory.CORE]
        for token in COLOR_TOKEN:
            assert token in core, f"{name}: missing {token}"
            value = core[token]
            assert is_color_list(value), f"{name}: {token} = {value!r}"
            if len(value) == 4:
                assert 0 <= value[3] <= 255, f"{name}: {token} alpha out of range"


def test_geometry_tokens_are_numeric():
    for name, spec in THEME_SPECS.items():
        theme = build_theme(spec)
        for category, tokens in theme.items():
            for key, value in tokens.items():
                if key in ("corner_radius", "border_width", "height",
                           "margin", "padding", "title_height", "title_margin",
                           "tab_radius", "tab_margin", "indicator_width",
                           "button_size", "button_icon_size", "badge_radius"):
                    assert isinstance(value, (int, float)), f"{name}.{category}.{key}"
                    assert value >= 0, f"{name}.{category}.{key} negative"


def test_spec_geometries_reach_theme_dict():
    """Spot-check that geometry overrides declared in specs actually land."""
    cyber = DOCK_THEMES["cyberpunk_neon"]
    assert cyber[DockStyleCategory.CORE]["corner_radius"] == 10
    assert cyber[DockStyleCategory.TITLE_BAR]["height"] == 32
    assert cyber[DockStyleCategory.TAB]["corner_radius"] == 8
    assert cyber[DockStyleCategory.TAB]["indicator_width"] == 2
    assert cyber[DockStyleCategory.PANEL]["content_margin"] == (8, 2)


@pytest.mark.parametrize("name", sorted(THEME_SPECS))
def test_every_preset_applies_and_resolves(name, qapp):
    assert apply_dock_theme(name), name
    colors = resolve_dock_colors()
    assert colors.canvas_bg.isValid()
    assert colors.text_color.isValid()
    sm = get_dock_style_manager()
    assert sm.get(DockStyleCategory.CORE, "accent_color").isValid()
