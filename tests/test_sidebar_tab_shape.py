# -*- coding: utf-8 -*-
"""The sidebar tab's shape and outline — SIDEBAR.tab_flat_edge & tab_border_*.

A sidebar tab is a vertical strip in a bar that runs along one window edge, so
"the side it is joined along" is not the bottom the way a dock widget tab's is:
it is the window-facing (``"outward"``) or the content-facing (``"inward"``)
side, and which one that is mirrors with the bar. That mirroring, and the
outline that either closes across the flat edge or leaves it open, are the whole
feature — so these read rendered pixels rather than token values wherever the
claim is about what is drawn.

Corners are measured by *alpha*, not colour: nothing else paints the button, so
a square corner comes back fully covered by the tab's own fill and a rounded one
comes back untouched, whatever the indicator happens to be doing on that edge.
"""

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QImage, QRegion
from PySide6.QtWidgets import QWidget

from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import DockStyleCategory, ThemeSpec, build_theme
from lace.enums import DockWidgetArea
from lace.sidebar_tab import VerticalTabButton

RADIUS = 6
WIDTH, HEIGHT = 30, 120


def _spec(**overrides):
    base = dict(
        base=[20, 20, 30, 255],
        accent=[255, 100, 180, 255],
        text=[240, 240, 250, 255],
        tab_radius=RADIUS,
        # Off by default here, and load-bearing: the highlight strip defaults
        # to the accent on the content-facing edge — the same colour and the
        # same pixels as the active tab's outline — so it would answer for the
        # outline on that edge in every reading below. The tests that are about
        # the strip switch it back on.
        sidebar_indicator_width=0,
    )
    base.update(overrides)
    return ThemeSpec(**base)


def _theme(**overrides):
    get_dock_style_manager().apply_theme_dict(build_theme(_spec(**overrides)))


def _tab(area=DockWidgetArea.left, checked=True):
    button = VerticalTabButton("Panel")
    button.set_area(area)
    button.resize(WIDTH, HEIGHT)
    button.setChecked(checked)
    button._is_hovered = False
    button.refresh_style()
    return button


def _render(button):
    image = QImage(button.size(), QImage.Format_ARGB32)
    image.fill(0)
    # Without DrawChildren-only flags, render() paints the palette background
    # over the whole rect first, and every corner comes back opaque whatever
    # shape the tab actually drew.
    button.render(image, QPoint(), QRegion(), QWidget.RenderFlag.DrawChildren)
    return image


def _rounded_corners(button):
    """Which corners the tab leaves uncovered, i.e. which ones are rounded."""
    image = _render(button)
    w, h = button.width() - 1, button.height() - 1
    corners = {"top_left": (0, 0), "top_right": (w, 0),
               "bottom_right": (w, h), "bottom_left": (0, h)}
    return {name for name, (x, y) in corners.items()
            if image.pixelColor(x, y).alpha() == 0}


def _inked_edges(button):
    """Which edges the outline paints on, measured by turning it off.

    A difference rather than a match against the outline's own colour: the
    stroke is antialiased across two pixel rows, so whether any single pixel
    comes back *exactly* that colour depends on where it happens to land. Only
    the middle third of each edge is sampled — the corners are shared by two
    edges, and the side strokes of an open outline legitimately run all the way
    into the flat one.
    """
    on = _render(button)
    saved = button._border_width
    button._border_width = 0.0
    try:
        off = _render(button)
    finally:
        button._border_width = saved

    w, h = button.width(), button.height()
    xs = range(w // 3, w - w // 3)
    ys = range(h // 3, h - h // 3)
    edges = {
        "left":   [(0, y) for y in ys],
        "right":  [(w - 1, y) for y in ys],
        "top":    [(x, 0) for x in xs],
        "bottom": [(x, h - 1) for x in xs],
    }
    return {name for name, points in edges.items()
            if any(on.pixelColor(x, y) != off.pixelColor(x, y) for x, y in points)}


# ── Shape ─────────────────────────────────────────────────────────────────
def test_the_default_tab_is_still_a_plain_rectangle(qapp):
    """"all" is the shipped default, and it ignores the radius entirely."""
    _theme()
    button = _tab()
    assert button._tab_flat_edge == "all"
    assert button._tab_corner_radius == RADIUS, "the radius is resolved, just unused"
    assert not _rounded_corners(button), "a default sidebar tab grew rounded corners"


@pytest.mark.parametrize("area, flat", [
    (DockWidgetArea.left, "left"),
    (DockWidgetArea.right, "right"),
])
def test_outward_keeps_the_window_facing_side_flat(qapp, area, flat):
    """The flat side follows the bar: left in a left sidebar, right in a right."""
    _theme(sidebar_tab_flat_edge="outward")
    rounded = _rounded_corners(_tab(area))
    assert rounded == {f"top_{_other(flat)}", f"bottom_{_other(flat)}"}, \
        f"{area.name} sidebar: expected the {flat} corners square, got {rounded}"


@pytest.mark.parametrize("area, flat", [
    (DockWidgetArea.left, "right"),
    (DockWidgetArea.right, "left"),
])
def test_inward_keeps_the_content_facing_side_flat(qapp, area, flat):
    _theme(sidebar_tab_flat_edge="inward")
    rounded = _rounded_corners(_tab(area))
    assert rounded == {f"top_{_other(flat)}", f"bottom_{_other(flat)}"}, \
        f"{area.name} sidebar: expected the {flat} corners square, got {rounded}"


def _other(side):
    return "right" if side == "left" else "left"


def test_none_rounds_all_four_corners(qapp):
    _theme(sidebar_tab_flat_edge="none")
    assert _rounded_corners(_tab()) == {"top_left", "top_right",
                                        "bottom_right", "bottom_left"}


def test_the_flat_side_moves_when_the_tab_changes_bars(qapp):
    """set_area() runs after the style is read, so the shape cannot be cached."""
    _theme(sidebar_tab_flat_edge="outward")
    button = _tab(DockWidgetArea.left)
    assert _rounded_corners(button) == {"top_right", "bottom_right"}
    button.set_area(DockWidgetArea.right)
    assert _rounded_corners(button) == {"top_left", "bottom_left"}


# ── Radius ────────────────────────────────────────────────────────────────
def test_the_radius_follows_the_dock_widget_tabs(qapp):
    """Unset, the sidebar tab is rounded exactly as much as a dock tab is."""
    _theme(tab_radius=10, sidebar_tab_flat_edge="outward")
    manager = get_dock_style_manager()
    assert manager.get(DockStyleCategory.SIDEBAR, "tab_corner_radius") is None
    assert _tab()._tab_corner_radius == 10 == manager.get(
        DockStyleCategory.TAB, "corner_radius")


def test_an_explicit_sidebar_radius_wins(qapp):
    _theme(tab_radius=10, sidebar_tab_radius=3, sidebar_tab_flat_edge="outward")
    assert _tab()._tab_corner_radius == 3


def test_a_zero_radius_squares_the_corners_off(qapp):
    """0 is a pinned value, not "unset" — it must not fall back to the tab's."""
    _theme(tab_radius=10, sidebar_tab_radius=0, sidebar_tab_flat_edge="none")
    button = _tab()
    assert button._tab_corner_radius == 0
    assert not _rounded_corners(button)


# ── Outline ───────────────────────────────────────────────────────────────
def test_no_outline_until_a_width_is_set(qapp):
    """The width is the master switch; the colours are seeded but inert."""
    _theme()
    manager = get_dock_style_manager()
    assert manager.get(DockStyleCategory.SIDEBAR, "tab_border_active_color") is not None
    assert not manager.get(DockStyleCategory.SIDEBAR, "tab_border_width")
    assert not _inked_edges(_tab())


def test_the_outline_leaves_the_flat_edge_open(qapp):
    _theme(sidebar_tab_flat_edge="outward", sidebar_tab_border_width=2.0)
    assert _inked_edges(_tab(DockWidgetArea.left)) == {"top", "right", "bottom"}, \
        "the outward (left) edge must stay open"
    assert _inked_edges(_tab(DockWidgetArea.right)) == {"top", "left", "bottom"}


def test_border_closed_runs_the_outline_the_whole_way_round(qapp):
    _theme(sidebar_tab_flat_edge="outward", sidebar_tab_border_width=2.0,
           sidebar_tab_border_closed=True)
    assert _inked_edges(_tab()) == {"left", "top", "right", "bottom"}


def test_all_four_corners_rounded_is_always_closed(qapp):
    """There is no flat edge left to leave open, so the flag cannot apply."""
    _theme(sidebar_tab_flat_edge="none", sidebar_tab_border_width=2.0,
           sidebar_tab_border_closed=False)
    assert _inked_edges(_tab()) == {"left", "top", "right", "bottom"}


def test_a_square_tab_is_outlined_on_all_four_sides(qapp):
    """"all" singles out no edge, so the outline cannot leave one open."""
    _theme(sidebar_tab_border_width=2.0, sidebar_tab_border_closed=False)
    assert _inked_edges(_tab()) == {"left", "top", "right", "bottom"}


def test_a_transparent_colour_turns_a_state_off(qapp):
    """A transparent colour, not a missing one, is how a state opts out."""
    _theme(sidebar_tab_border_width=2.0,
           sidebar_tab_border_color=[0, 0, 0, 0],
           sidebar_tab_border_active_color=[255, 100, 180, 255])
    active, inactive = _tab(checked=True), _tab(checked=False)
    assert active._border_color(True) is not None
    assert inactive._border_color(False) is None, \
        "a transparent colour still resolved to an outline"
    assert _inked_edges(active), "the active tab lost its outline"
    assert not _inked_edges(inactive), "a transparent colour still drew"


def test_both_states_can_differ(qapp):
    _theme(sidebar_tab_border_width=2.0,
           sidebar_tab_border_color=[100, 110, 160, 255],
           sidebar_tab_border_active_color=[255, 100, 180, 255])
    active, inactive = _tab(checked=True), _tab(checked=False)
    assert _inked_edges(active) == _inked_edges(inactive) == {
        "left", "top", "right", "bottom"}
    mid = HEIGHT // 2
    assert _render(active).pixelColor(0, mid) != _render(inactive).pixelColor(0, mid), \
        "the two outlines render identically"


def test_the_outline_follows_the_rounded_corners(qapp):
    """Stroked on the tab path, so a rounded corner stays uncovered."""
    _theme(sidebar_tab_flat_edge="none", sidebar_tab_border_width=2.0)
    assert _rounded_corners(_tab(checked=False)) == {
        "top_left", "top_right", "bottom_right", "bottom_left"}


# ── The highlight strip ───────────────────────────────────────────────────
def test_the_indicator_width_is_themeable(qapp):
    """SIDEBAR.indicator_width had no route in from a ThemeSpec at all."""
    _theme(sidebar_indicator_width=7, sidebar_indicator_position="left")
    button = _tab(DockWidgetArea.left)
    assert button._indicator_width == 7
    image, indicator = _render(button), button._highlight_color
    mid = HEIGHT // 2
    assert image.pixelColor(6, mid).getRgb() == indicator.getRgb()
    assert image.pixelColor(7, mid).getRgb() != indicator.getRgb(), \
        "the strip is wider than the 7px asked for"


def test_the_indicator_position_is_themeable(qapp):
    _theme(sidebar_indicator_position="right", sidebar_indicator_width=4)
    button = _tab(DockWidgetArea.left)
    assert button._indicator_position == "right"
    assert button._indicator_edge() == Qt.Edge.RightEdge
    image = _render(button)
    assert image.pixelColor(WIDTH - 1, HEIGHT // 2).getRgb() == \
        button._highlight_color.getRgb()


def test_the_indicator_is_clipped_to_the_rounded_tab(qapp):
    """It hugs an edge, but never outside the shape it belongs to."""
    _theme(sidebar_tab_flat_edge="none", sidebar_indicator_position="left",
           sidebar_indicator_width=4)
    assert _rounded_corners(_tab(DockWidgetArea.left)) == {
        "top_left", "top_right", "bottom_right", "bottom_left"}


# ── Theme plumbing ────────────────────────────────────────────────────────
def test_the_spec_reaches_the_sidebar_tokens(qapp):
    _theme(sidebar_tab_flat_edge="inward", sidebar_tab_radius=5,
           sidebar_tab_border_width=1.5, sidebar_tab_border_closed=True,
           sidebar_tab_border_color=[10, 20, 30, 255],
           sidebar_tab_border_active_color=[40, 50, 60, 255],
           sidebar_indicator_width=6, sidebar_indicator_position="right")
    sidebar = get_dock_style_manager().get_all(DockStyleCategory.SIDEBAR)
    assert sidebar["tab_flat_edge"] == "inward"
    assert sidebar["tab_corner_radius"] == 5
    assert sidebar["tab_border_width"] == 1.5
    assert sidebar["tab_border_closed"] is True
    assert sidebar["tab_border_normal_color"].getRgb() == (10, 20, 30, 255)
    assert sidebar["tab_border_active_color"].getRgb() == (40, 50, 60, 255)
    assert sidebar["indicator_width"] == 6
    assert sidebar["indicator_position"] == "right"


def test_a_json_theme_carries_the_same_fields(qapp, tmp_path):
    import json

    from lace.theme_models import load_theme_json

    path = tmp_path / "sidebar.json"
    path.write_text(json.dumps({
        "base": "#141c28", "accent": "#ff64b4", "text": "#f0f0fa",
        "sidebar_tab_flat_edge": "outward",
        "sidebar_tab_radius": 8,
        "sidebar_tab_border_width": 2.0,
        "sidebar_tab_border_color": "#64708c",
        "sidebar_tab_border_closed": True,
        "sidebar_indicator_width": 5,
    }), encoding="utf-8")

    sidebar = load_theme_json(path)[DockStyleCategory.SIDEBAR]
    assert sidebar["tab_flat_edge"] == "outward"
    assert sidebar["tab_corner_radius"] == 8
    assert sidebar["tab_border_width"] == 2.0
    assert sidebar["tab_border_normal_color"] == [100, 112, 140, 255]
    assert sidebar["tab_border_closed"] is True
    assert sidebar["indicator_width"] == 5


def test_the_shipped_themes_keep_their_square_tabs(qapp):
    """Every preset sets tab_radius; none of them opts into the new shape."""
    from lace.dock_custom_theme import DOCK_THEMES

    manager = get_dock_style_manager()
    for name in DOCK_THEMES:
        manager.apply_theme(name)
        sidebar = manager.get_all(DockStyleCategory.SIDEBAR)
        assert sidebar["tab_flat_edge"] == "all", f"{name} changed the tab shape"
        assert not sidebar["tab_border_width"], f"{name} outlines its sidebar tabs"
