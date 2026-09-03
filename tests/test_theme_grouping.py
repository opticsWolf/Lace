# -*- coding: utf-8 -*-
"""Twenty-seven themes in one flat column, and the shape of the set is lost.

The presets are not a flat set and have not been for a while: four of them ship
as families of three, where `violet_haze_neutral` is not a preset of its own but
one key of a design.  An alphabetical menu files those counterparts away from
their parents and puts `midnight_haze_light` above `midnight_haze`; a
definition-ordered one was merely the order they happened to be written in.

``THEME_GROUPS`` is the grouping, and this pins the properties that make it
worth having: that it covers everything, that no theme can quietly fall out of
it, and that inside a family the order is the one a person would expect to
scan — dark, then neutral, then light.
"""

import pytest
from PySide6.QtGui import QColor

from lace import theme_choices, theme_groups
from lace.dock_custom_theme import DOCK_THEMES, THEME_GROUPS, THEME_SPECS
from lace.dock_theme import DockStyleCategory, build_theme

#: The families that ship as more than one key, parent first.
FAMILIES = {
    "cyberpunk_edge": ("cyberpunk_edge", "cyberpunk_edge_neutral",
                       "cyberpunk_edge_light"),
    "violet_haze": ("violet_haze", "violet_haze_neutral", "violet_haze_light"),
    "midnight_haze": ("midnight_haze", "midnight_haze_neutral",
                      "midnight_haze_light"),
    "slate_amber": ("slate_amber_dark", "slate_amber", "slate_amber_light"),
}


def _flat():
    return [key for _, choices in theme_groups() for _, key in choices]


def _panel_luminance(name: str) -> float:
    theme = build_theme(THEME_SPECS[name])
    panel = (theme[DockStyleCategory.PANEL].get("bg_normal")
             or theme[DockStyleCategory.CORE]["canvas_bg"])
    return QColor(*list(panel)[:3]).lightnessF()


def test_the_groups_cover_every_preset_exactly_once():
    """A preset in no group vanishes from every grouped menu.

    This is asserted at import in dock_custom_theme too — deliberately, because
    by the time a test run catches it the wrong file has already been pushed.
    """
    listed = [key for keys in THEME_GROUPS.values() for key in keys]
    assert len(listed) == len(set(listed)), "a theme is in two groups"
    assert set(listed) == set(THEME_SPECS)


def test_theme_groups_places_default_rather_than_dropping_it():
    """``default`` is in DOCK_THEMES but has no ThemeSpec, so no group claims it."""
    assert "default" not in {k for keys in THEME_GROUPS.values() for k in keys}
    assert set(_flat()) == set(DOCK_THEMES)
    assert _flat()[0] == "default", "the stock look should head the first group"


def test_no_group_is_empty_and_none_is_a_dumping_ground():
    """Twelve is the biggest legitimate group: four families of three."""
    for title, choices in theme_groups():
        assert choices, f"{title} is an empty submenu"
        assert len(choices) <= 12, f"{title} holds {len(choices)} — regroup it"


def test_the_flat_list_is_the_grouped_one_flattened():
    """theme_choices() still exists for flat menus, but is no longer arbitrary."""
    assert [key for _, key in theme_choices()] == _flat()


@pytest.mark.parametrize("family,members", FAMILIES.items())
def test_a_family_stays_together_in_the_menu(family, members):
    """Adjacent, in order.  A counterpart three submenus from its parent is
    indistinguishable from an unrelated preset that happens to share a word."""
    order = _flat()
    positions = [order.index(name) for name in members]
    assert positions == sorted(positions), f"{family} is out of order: {members}"
    assert positions[-1] - positions[0] == len(members) - 1, \
        f"{family} is split up by {order[positions[0]:positions[-1] + 1]}"


@pytest.mark.parametrize("family,members", FAMILIES.items())
def test_a_family_ends_on_its_lightest_member(family, members):
    """The one ordering rule inside a family, and it is by measurement.

    Not a monotonic run — a neutral is a *saturation* variant, and flattening
    the grounds toward grey moves the panel by a point either way (violet_haze
    0.267 -> 0.249, cyberpunk_edge 0.118 -> 0.127).  Sorting on lightness would
    shuffle parent and neutral on that noise.  What holds is the end: the light
    counterpart is last and is nowhere near the rest.

    slate_amber is the case that makes this worth asserting rather than
    eyeballing.  Its parent was always the light one, so the family reads dark,
    light, lighter — 0.198, 0.833, 0.967 — and the rule still names the right
    member last.
    """
    lums = [_panel_luminance(name) for name in members]
    assert lums[-1] == max(lums),         f"{family} does not end on its lightest: {list(zip(members, lums))}"
    assert lums[-1] > 0.9, f"{family}'s last member is not a light one"
    assert lums[-1] - max(lums[:-1]) > 0.1,         f"{family}'s last two are the same tier: {list(zip(members, lums))}"


@pytest.mark.parametrize("family,members", FAMILIES.items())
def test_a_neutral_is_filed_next_to_the_parent_it_came_from(family, members):
    """Dark, *neutral*, light — the neutral sits on the dark side of the run.

    It is the parent with the tint pulled out of its grounds, so it belongs
    beside the parent and not beside the light one it shares no palette with.
    """
    neutral = [name for name in members if name.endswith("_neutral")]
    if not neutral:
        pytest.skip(f"{family} ships no neutral")
    index = members.index(neutral[0])
    assert index == 1, f"{family}'s neutral is not second: {members}"
    assert abs(_panel_luminance(neutral[0]) - _panel_luminance(members[0])) < 0.1,         f"{neutral[0]} is not in its parent's tier"


def test_every_group_label_is_a_menu_title():
    for title, _ in theme_groups():
        assert title and title[0].isupper() and "_" not in title
