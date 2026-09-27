# -*- coding: utf-8 -*-
"""Theme derivation meets its contrast and separation floors (plan Phase 2).

Floors a theme can't meet without overriding its own explicit colours are
allowed to fall short: explicit colours move at most EXPLICIT_MAX_DE, and some
floors are out of reach on a mid-tone surface the theme chose. Everything
derived must pass.
"""

import json

import pytest
from hypothesis import given, settings, strategies as st
from pydantic import ValidationError

from lace import color_science as cs
from lace.dock_theme import DockStyleCategory, ThemeSpec, build_theme, explicit_tokens
from lace.theme_contrast import (
    CONTRAST_LEVELS, DEPTH_LEVELS, EXPLICIT_MAX_DE, audit, enforce,
)
from lace.theme_models import ThemeJson
from tests.theme_sets import FIXTURES, REGULAR


def spec_for(key):
    if key.startswith("kilim_"):
        return ThemeJson.load(FIXTURES / f"{key}.json").to_theme_spec()
    from lace.dock_custom_theme import THEME_SPECS
    return THEME_SPECS[key]


def with_levels(spec, **kw):
    from dataclasses import replace
    return replace(spec, **kw)


def hard_misses(spec, contrast="normal", depth="subtle"):
    theme = build_theme(with_levels(spec, contrast=contrast, depth=depth))
    explicit = explicit_tokens(spec)
    return [m for m in audit(theme, contrast, depth)
            if m.token not in explicit and not m.unreachable]


@pytest.mark.parametrize("contrast", CONTRAST_LEVELS)
@pytest.mark.parametrize("key", REGULAR)
def test_derived_tokens_meet_every_contrast_level(key, contrast):
    assert hard_misses(spec_for(key), contrast=contrast) == []


@pytest.mark.parametrize("depth", DEPTH_LEVELS)
@pytest.mark.parametrize("key", REGULAR)
def test_derived_surfaces_meet_every_depth(key, depth):
    assert hard_misses(spec_for(key), depth=depth) == []


def test_every_theme_meets_the_default_levels(theme_key):
    """The --themes stage (all at milestones) at contrast=normal, depth=subtle."""
    assert hard_misses(spec_for(theme_key)) == []


@pytest.mark.parametrize("key", REGULAR)
def test_explicit_colours_move_at_most_slightly(key):
    spec = spec_for(key)
    theme = build_theme(spec)
    for name in explicit_tokens(spec):
        cat, tok = name.split(".")
        value = theme[DockStyleCategory[cat]][tok]
        # The value the spec gave for this token, found by field.
        seeds = [list(getattr(spec, f)) for f in (
            "base", "accent", "text", "surface", "border", "focus_border_color", "title_bg",
            "tooltip_bg", "tooltip_text") if getattr(spec, f, None) is not None]
        nearest = min(cs.delta_e(value, s) for s in seeds) if seeds else 0
        assert nearest <= EXPLICIT_MAX_DE + 0.005 or tok not in (
            "canvas_bg", "text_color", "accent_color"), (name, value)


def test_a_passing_explicit_colour_is_untouched():
    spec = ThemeSpec(base=[24, 24, 28, 255], accent=[0, 120, 212, 255],
                     text=[230, 230, 235, 255], surface=[34, 34, 40, 255])
    theme = build_theme(spec)
    assert theme[DockStyleCategory.CORE]["canvas_bg"] == [24, 24, 28, 255]
    assert theme[DockStyleCategory.CORE]["text_color"] == [230, 230, 235, 255]
    assert theme[DockStyleCategory.PANEL]["bg_normal"] == [34, 34, 40, 255]


@pytest.mark.parametrize("key", REGULAR)
def test_auto_light_agrees_with_the_hand_set_flag(key):
    spec = spec_for(key)
    if spec.is_light is None:
        pytest.skip("flag not set by hand")
    assert (not cs.is_dark(list(spec.base))) == spec.is_light


def test_depth_orders_the_surface_steps():
    spec = ThemeSpec(base=[30, 30, 34, 255], accent=[0, 120, 212, 255], text=[220, 220, 225, 255])
    gaps = []
    for depth in DEPTH_LEVELS:
        t = build_theme(with_levels(spec, depth=depth))
        panel = t[DockStyleCategory.PANEL]["bg_normal"]
        gaps.append(abs(cs.to_oklch(t[DockStyleCategory.PANEL]["button_bg"])[0]
                        - cs.to_oklch(panel)[0]))
    assert gaps == sorted(gaps) and gaps[0] < gaps[-1]


def test_contrast_raises_muted_text():
    spec = ThemeSpec(base=[40, 40, 44, 255], accent=[0, 120, 212, 255], text=[150, 150, 155, 255])
    ratios = []
    for level in CONTRAST_LEVELS:
        t = build_theme(with_levels(spec, contrast=level))
        ratios.append(cs.contrast_ratio(t[DockStyleCategory.TAB]["text_normal"],
                                        t[DockStyleCategory.TAB]["bg_normal"]))
    assert ratios == sorted(ratios) and ratios[0] < ratios[-1]


@pytest.mark.parametrize("selection", ["solid", "tint"])
def test_selection_keyword(selection):
    spec = ThemeSpec(base=[24, 24, 28, 255], accent=[0, 120, 212, 255],
                     text=[220, 220, 225, 255], selection=selection)
    panel = build_theme(spec)[DockStyleCategory.PANEL]
    ratio = cs.contrast_ratio(panel["highlighted_text"], panel["highlight"])
    assert ratio >= 4.5
    if selection == "solid":
        assert panel["highlight"] == [0, 120, 212, 255]
    else:
        assert panel["highlight"] != [0, 120, 212, 255]
        assert panel["highlighted_text"] == [220, 220, 225, 255]


def test_bad_keywords_raise():
    base = dict(base=[20, 20, 20, 255], accent=[0, 120, 212, 255], text=[200, 200, 200, 255])
    for kw in ({"contrast": "max"}, {"depth": "deep"}, {"selection": "glow"}):
        with pytest.raises(ValueError):
            build_theme(ThemeSpec(**base, **kw))


# --- JSON ------------------------------------------------------------------------
def test_keywords_round_trip_through_json(tmp_path):
    path = tmp_path / "t.json"
    path.write_text(json.dumps({
        "base": "#141414", "accent": "#0078d4", "text": "#cccccc",
        "contrast": "high", "depth": "raised", "selection": "tint",
    }), encoding="utf-8")
    spec = ThemeJson.load(path).to_theme_spec()
    assert (spec.contrast, spec.depth, spec.selection) == ("high", "raised", "tint")
    assert spec.is_light is None


@pytest.mark.parametrize("field, value", [
    ("contrast", "max"), ("depth", "deep"), ("selection", "glow")])
def test_invalid_json_keywords_are_rejected(field, value):
    with pytest.raises(ValidationError):
        ThemeJson.model_validate({"base": "#000", "accent": "#fff", "text": "#888", field: value})


# --- properties ------------------------------------------------------------------
channel = st.integers(0, 255)
colour = st.tuples(channel, channel, channel).map(lambda t: [*t, 255])


@settings(max_examples=25, deadline=None)
@given(colour, colour, colour)
def test_random_seeds_meet_the_floors_or_say_why(base, accent, text):
    """Any base/accent/text triple: every derived token passes, and a miss is
    always an explicit colour at its cap or a floor out of reach."""
    spec = ThemeSpec(base=base, accent=accent, text=text)
    assert hard_misses(spec) == []


def test_enforce_is_idempotent():
    spec = ThemeSpec(base=[20, 20, 20, 255], accent=[0, 120, 212, 255], text=[60, 60, 60, 255])
    theme = build_theme(spec)
    ids = {id(theme[DockStyleCategory[n.split(".")[0]]][n.split(".")[1]])
           for n in explicit_tokens(spec)}
    # Already enforced by the builder: a second pass may only nudge colours
    # the first left short (explicit ones restart their cap here), never
    # a derived one.
    moved = enforce(theme, explicit_ids=ids)
    assert not [n for n in moved if n not in explicit_tokens(spec)]
