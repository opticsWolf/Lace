# -*- coding: utf-8 -*-
"""The light and neutral counterparts of the four edge-treatment presets.

Each counterpart keeps its parent's *geometry* exactly — the radii, the line
widths, which edges are drawn and which are left open — and changes only the
palette.  That is the whole contract: a pair should read as one design in two
keys, not as two designs.  It is also the part that rots silently, because
tuning a radius on the parent and forgetting the counterpart looks like nothing
at all until the two are seen side by side.

The palette side is checked for the properties that actually make a light
variant usable rather than merely lighter: the accent has to darken enough to
survive on a near-white panel, and the neutral variants have to keep their four
semantic colours chromatic.
"""

import pytest

from lace.dock_custom_theme import THEME_SPECS
from lace.dock_theme import DockStyleCategory, build_theme


#: parent -> its counterparts.
FAMILIES = {
    "cyberpunk_edge": ("cyberpunk_edge_light", "cyberpunk_edge_neutral"),
    "violet_haze": ("violet_haze_light", "violet_haze_neutral"),
    "midnight_haze": ("midnight_haze_light", "midnight_haze_neutral"),
    "slate_amber": ("slate_amber_dark",),
}

PAIRS = [(parent, child)
         for parent, children in FAMILIES.items()
         for child in children]

LIGHT = [c for _, c in PAIRS if c.endswith("_light")]
NEUTRAL = [c for _, c in PAIRS if c.endswith("_neutral")]

#: Every ThemeSpec field that describes shape rather than colour.
GEOMETRY = (
    "corner_radius", "border_width", "title_height", "title_padding_left",
    "title_padding_right", "title_button_spacing", "title_margin",
    "title_border_width", "title_border_bottom", "border_below_title",
    "tab_radius", "tab_margin", "tab_border_width", "content_margin",
    "indicator_width", "indicator_position", "tab_dimming",
    "sidebar_tab_flat_edge", "sidebar_tab_radius", "sidebar_tab_border_width",
    "sidebar_indicator_width",
)

SEMANTIC = ("success_color", "warning_color", "error_color", "info_color")


def _lin(channel: int) -> float:
    c = channel / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _luminance(rgba) -> float:
    r, g, b = list(rgba)[:3]
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def _contrast(a, b) -> float:
    la, lb = _luminance(a), _luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def _panel(name: str):
    theme = build_theme(THEME_SPECS[name])
    panel = theme[DockStyleCategory.PANEL].get("bg_normal")
    return panel or theme[DockStyleCategory.CORE]["canvas_bg"]


def _core(name: str, token: str):
    return build_theme(THEME_SPECS[name])[DockStyleCategory.CORE][token]


def test_every_counterpart_is_registered():
    for parent, child in PAIRS:
        assert parent in THEME_SPECS
        assert child in THEME_SPECS, f"{child} is not a shipped preset"


@pytest.mark.parametrize("parent,child", PAIRS)
def test_a_counterpart_keeps_its_parents_geometry(parent, child):
    """Palette only.  A radius that moved on one and not the other is a bug."""
    p, c = THEME_SPECS[parent], THEME_SPECS[child]
    differing = {field: (getattr(p, field), getattr(c, field))
                 for field in GEOMETRY
                 if getattr(p, field) != getattr(c, field)}
    assert not differing, f"{child} drifted from {parent}: {differing}"


@pytest.mark.parametrize("name", LIGHT)
def test_a_light_counterpart_is_actually_light(name):
    p = THEME_SPECS[name]
    assert p.is_light is True, f"{name} is not flagged is_light"
    assert _luminance(_panel(name)) > 0.7, f"{name}'s panel is not a light panel"


@pytest.mark.parametrize("name", LIGHT)
def test_a_light_counterpart_darkens_its_accent_enough_to_read(name):
    """A neon that glows on near-black is a smear on white.

    The accent is not decoration here — it draws the focused area's frame, the
    active tab's outline and the rule under the tab strip, all of them 1.5-2px.
    Below about 3:1 those stop being lines.
    """
    ratio = _contrast(_core(name, "accent_color"), _panel(name))
    assert ratio >= 3.0, f"{name}: accent is {ratio:.2f}:1 on its own panel"


@pytest.mark.parametrize("name", [c for _, c in PAIRS])
def test_every_counterpart_keeps_its_body_text_legible(name):
    ratio = _contrast(_core(name, "text_color"), _panel(name))
    assert ratio >= 7.0, f"{name}: text is {ratio:.2f}:1 on its own panel"


@pytest.mark.parametrize("name", NEUTRAL)
def test_a_neutral_counterpart_drains_the_decorative_hue(name):
    """The accent goes grey; a channel spread is what "not grey" looks like."""
    r, g, b = list(_core(name, "accent_color"))[:3]
    assert max(r, g, b) - min(r, g, b) <= 16, \
        f"{name}: accent {(r, g, b)} still carries a hue"


@pytest.mark.parametrize("name", NEUTRAL)
def test_a_neutral_counterpart_keeps_its_semantic_colours(name):
    """success/warning/error/info are meaning, not decoration.

    A greyed-out error colour is not a subtler error colour; it is one the
    user can no longer tell from the success colour.
    """
    seen = []
    for token in SEMANTIC:
        r, g, b = list(_core(name, token))[:3]
        assert max(r, g, b) - min(r, g, b) > 40, \
            f"{name}: {token} was drained along with the accent"
        seen.append((r, g, b))
    assert len(set(seen)) == len(SEMANTIC), f"{name}: two status colours collide"


@pytest.mark.parametrize("parent,child", PAIRS)
def test_a_counterpart_moves_its_accent(parent, child):
    """Same geometry, different key — an identical accent means nothing moved."""
    assert list(_core(parent, "accent_color")) != list(_core(child, "accent_color"))


def test_slate_amber_ships_as_a_light_dark_pair():
    """slate_amber was always the light one; slate_amber_dark is its other half."""
    assert THEME_SPECS["slate_amber"].is_light is True
    assert THEME_SPECS["slate_amber_dark"].is_light is False
    assert _luminance(_panel("slate_amber")) > 0.6
    assert _luminance(_panel("slate_amber_dark")) < 0.1
