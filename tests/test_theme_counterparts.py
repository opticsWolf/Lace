# -*- coding: utf-8 -*-
"""The light and neutral counterparts of the four edge-treatment presets.

Each counterpart keeps its parent's *geometry* exactly — the radii, the line
widths, which edges are drawn and which are left open — and changes only the
palette.  That is the whole contract: a pair should read as one design in two
keys, not as two designs.  It is also the part that rots silently, because
tuning a radius on the parent and forgetting the counterpart looks like nothing
at all until the two are seen side by side.

The palette side is checked for the properties that actually make each kind of
variant usable.  A light one has to darken its accent enough to survive on a
near-white panel.  A *neutral* one is two things at once: its grounds are flat
— base, panel and strip carry at most a trace of the parent's cast — and they
sit **between** the parent and the light counterpart, nearer the light.  What
is not neutralised is everything that carries meaning: the accent, the outlines
that mark focus, and the four status tokens.  Draining those would not make a
subtler theme, it would make a different and worse one.
"""

import pytest
from PySide6.QtGui import QColor

from lace.dock_custom_theme import THEME_SPECS
from lace.dock_theme import DockStyleCategory, build_theme


#: parent -> its counterparts.
FAMILIES = {
    "cyberpunk_edge": ("cyberpunk_edge_light", "cyberpunk_edge_neutral"),
    "violet_haze": ("violet_haze_light", "violet_haze_neutral"),
    "midnight_haze": ("midnight_haze_light", "midnight_haze_neutral"),
    "slate_amber": ("slate_amber_dark", "slate_amber_light"),
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


def _lightness(rgba) -> float:
    """HSL lightness -- how light a colour *looks*, not how much light it emits.

    The rest of this file measures in WCAG relative luminance, which is the
    right metric for a contrast ratio and the wrong one for "which tier is
    this".  Relative luminance is gamma-corrected and brutally non-linear at
    the dark end: a mid grey that reads as three-quarters of the way to white
    scores 0.48, barely above near-black's 0.05.  Asking whether a neutral
    leans light is a question about perception, so it is asked in HSL.
    """
    return QColor(*list(rgba)[:3]).lightnessF()


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


def _spread(rgba) -> int:
    """How far a colour is from grey: the gap between its widest channels."""
    r, g, b = list(rgba)[:3]
    return max(r, g, b) - min(r, g, b)


GROUNDS = ("base", "surface", "title_bg")

NEUTRAL_PAIRS = [(p, c) for p, c in PAIRS if c in NEUTRAL]


@pytest.mark.parametrize("parent,child", NEUTRAL_PAIRS)
def test_a_neutral_counterpart_flattens_its_grounds(parent, child):
    """Neutral means the grounds, and only the grounds.

    A trace of the parent's cast is allowed to stay: the point is a backdrop
    that stops competing with the accent in front of it, not a grey one.
    """
    for field in GROUNDS:
        p = getattr(THEME_SPECS[parent], field)
        c = getattr(THEME_SPECS[child], field)
        assert p is not None and c is not None, f"{child}: {field} is unset"
        assert _spread(c) < _spread(p), (
            f"{child}: {field} {list(c)[:3]} is no flatter "
            f"than {parent}'s {list(p)[:3]}")
        assert _spread(c) <= 6, (
            f"{child}: {field} {list(c)[:3]} still reads as a colour, "
            f"not as a cast")


@pytest.mark.parametrize("parent,child", NEUTRAL_PAIRS)
def test_a_neutral_counterpart_is_a_mid_tone_leaning_light(parent, child):
    """The tier, not just the flatness.

    Flattening the grounds without moving them left three presets sitting on
    near-black beside their parents, close enough that a menu offered two
    entries a user could not tell apart.  A neutral is the blend: measurably
    between its parent and the light counterpart, and on the light side of the
    midpoint rather than the dark one.

    The margins matter more than the exact figure.  0.2 of clearance at each
    end is what keeps this a third tier rather than a variation on a
    neighbour; the 0.6 floor is what makes it the *lighter* half of the
    range, which is the judgement call and so the part worth pinning.
    """
    light = child.replace("_neutral", "_light")
    dark, mid, pale = (_lightness(_panel(name))
                       for name in (parent, child, light))

    assert dark + 0.2 < mid < pale - 0.2, (
        f"{child} at {mid:.2f} is not a tier of its own between "
        f"{parent} at {dark:.2f} and {light} at {pale:.2f}")
    assert mid > (dark + pale) / 2, (
        f"{child} at {mid:.2f} sits below the midpoint of "
        f"{(dark + pale) / 2:.2f} — it should lean light")
    assert mid > 0.6, f"{child}'s panel is {mid:.2f}, not a light-leaning mid"


@pytest.mark.parametrize("name", NEUTRAL)
def test_a_mid_tone_neutral_flips_to_a_light_chassis(name):
    """is_light is not decoration: it reverses every derived adjustment.

    Body text, the hover fill, the shadow alphas and the default status
    colours are all computed off it.  A mid-tone ground with is_light left
    False gets pale text on light grey — which is exactly what these three
    would have been if the flag had been forgotten alongside the palette.
    """
    assert THEME_SPECS[name].is_light is True
    assert _contrast(_core(name, "text_color"), _panel(name)) >= 7.0


@pytest.mark.parametrize("parent,child", NEUTRAL_PAIRS)
def test_a_neutral_counterpart_keeps_its_parents_highlight(parent, child):
    """The accent survives: same hue family, adjusted rather than drained.

    It is the colour that says which area has focus, and on two of these three
    presets it is the *only* thing drawn.  Greying it out is the one change
    that would cost the variant the thing it inherited.
    """
    p = QColor(*list(_core(parent, "accent_color"))[:3])
    c = QColor(*list(_core(child, "accent_color"))[:3])

    # Relative to the parent, not an absolute floor: dracula's purple is a
    # pastel whose own saturation is only 104, so any fixed threshold high
    # enough to catch a drained amber would fail it for being itself.
    assert c.saturation() >= p.saturation() * 0.85, (
        f"{child}: accent {c.getRgb()[:3]} at saturation {c.saturation()} "
        f"was drained, not adjusted, off {parent}'s {p.saturation()}")
    shift = abs(p.hue() - c.hue())
    shift = min(shift, 360 - shift)
    assert shift <= 20, (
        f"{child}: accent moved {shift} degrees off {parent}'s hue")


@pytest.mark.parametrize("parent,child", NEUTRAL_PAIRS)
def test_a_neutral_counterpart_outcolours_its_own_ground(parent, child):
    """The whole effect in one assertion: the accent beats the backdrop.

    On the parents the gap is far narrower, because the backdrop carries the
    same hue family the accent does — which is exactly what these variants
    take away.
    """
    accent = _spread(_core(child, "accent_color"))
    ground = max(_spread(getattr(THEME_SPECS[child], f)) for f in GROUNDS)
    assert accent > ground * 10, (
        f"{child}: accent spread {accent} against a ground spread of {ground}")

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


def test_slate_amber_ships_as_three_tiers():
    """slate_amber was always light, so its family runs dark -> light -> lighter.

    slate_amber_light is not a counterpart in the sense the other six are — it
    is not the same design in another key, it is the same *light* design a tier
    brighter, and the parent is untouched beside it.
    """
    tiers = ["slate_amber_dark", "slate_amber", "slate_amber_light"]
    lums = [_luminance(_panel(name)) for name in tiers]
    assert lums == sorted(lums), f"the tiers are out of order: {list(zip(tiers, lums))}"
    assert lums[0] < 0.1, "slate_amber_dark is not a dark panel"
    assert lums[1] > 0.6
    assert lums[2] > 0.9, "slate_amber_light is not brighter than slate_amber"

    assert THEME_SPECS["slate_amber_dark"].is_light is False
    assert THEME_SPECS["slate_amber"].is_light is True
    assert THEME_SPECS["slate_amber_light"].is_light is True


def test_slate_amber_light_deepens_its_amber_as_the_ground_brightens():
    """The greys go up, the accent goes down — otherwise the lines dissolve.

    Amber draws the rule under the tab strip, the focused card's outline and
    the active sidebar ring, all at 1.5px, and every point the panel gains is a
    point of separation those lines lose.  Keeping the parent's 186,98,0 would
    have dropped them from 4.94:1 to 4.04:1.
    """
    parent, brighter = THEME_SPECS["slate_amber"], THEME_SPECS["slate_amber_light"]
    assert sum(list(brighter.base)[:3]) > sum(list(parent.base)[:3])
    assert sum(list(brighter.surface)[:3]) > sum(list(parent.surface)[:3])
    assert sum(list(brighter.accent)[:3]) < sum(list(parent.accent)[:3])

    # And the deepening more than pays for the brighter ground.
    assert _contrast(_core("slate_amber_light", "accent_color"),
                     _panel("slate_amber_light")) >            _contrast(_core("slate_amber", "accent_color"), _panel("slate_amber"))


def test_slate_amber_light_keeps_the_parents_hover_direction():
    """The three *_light counterparts flip hover_mode to "darker"; this does not.

    They are near-white panels with nowhere lighter to go.  This one is not
    quite that bright, and "lighter" separates the hover from the tab strip by
    34 points here against the parent's 35 — where "darker" flattens it to 26.
    """
    assert THEME_SPECS["slate_amber_light"].hover_mode ==            THEME_SPECS["slate_amber"].hover_mode == "lighter"

    tab = build_theme(THEME_SPECS["slate_amber_light"])[DockStyleCategory.TAB]
    strip, hover = list(tab["bg_normal"])[:3], list(tab["bg_hover"])[:3]
    assert abs(sum(strip) - sum(hover)) / 3 > 25,         f"the hover barely separates from the strip: {strip} vs {hover}"
