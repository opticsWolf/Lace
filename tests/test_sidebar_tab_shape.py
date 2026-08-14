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
        # Off by default here: the strip defaults to the accent on the
        # content-facing edge, the same pixels the active tab's outline uses,
        # and it would answer for the outline in any direct pixel read. The
        # tests that are about the strip switch it back on; _inked_edges
        # switches it off itself, so it holds for the presets too.
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


def _render(button, image=None):
    if image is None:
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

    The highlight strip is switched off for both renders. It sits *on* one of
    the outline's edges, and in a theme where the two share a colour —
    cyberpunk_edge rings and stripes its active tab in the same amber — it goes
    on painting that edge with the outline gone, so the difference reads as an
    edge the outline never drew.
    """
    saved_strip, button._indicator_width = button._indicator_width, 0.0
    try:
        on = _render(button)
        saved = button._border_width
        button._border_width = 0.0
        try:
            off = _render(button)
        finally:
            button._border_width = saved
    finally:
        button._indicator_width = saved_strip

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


def test_the_outline_can_be_the_hover_cue(qapp):
    """With the inactive colour off, the ring appears under the cursor only."""
    _theme(sidebar_tab_flat_edge="none", sidebar_tab_border_width=2.0,
           sidebar_tab_border_color=[0, 0, 0, 0],
           sidebar_tab_border_hover_color=[189, 147, 249, 255])
    idle = _tab(checked=False)
    hovered = _tab(checked=False)
    hovered._is_hovered = True
    assert not _inked_edges(idle), "an idle tab is ringed"
    assert _inked_edges(hovered) == {"left", "top", "right", "bottom"}


def test_an_unset_hover_outline_is_not_a_transparent_one(qapp):
    """Unset, hover is not a state of its own — it keeps the inactive ring.

    The distinction the token turns on: were "unset" read as "no outline", every
    theme that rings its inactive tabs would lose that ring under the cursor.
    """
    _theme(sidebar_tab_border_width=2.0,
           sidebar_tab_border_color=[100, 110, 160, 255])
    assert get_dock_style_manager().get(
        DockStyleCategory.SIDEBAR, "tab_border_hover_color") is None
    button = _tab(checked=False)
    assert button._border_color(False, True) == button._border_color(False, False)
    button._is_hovered = True
    assert _inked_edges(button) == {"left", "top", "right", "bottom"}


def test_the_active_tab_keeps_its_own_outline_under_the_cursor(qapp):
    """Checked wins over hovered, the same precedence the fill uses."""
    _theme(sidebar_tab_border_width=2.0,
           sidebar_tab_border_active_color=[255, 100, 180, 255],
           sidebar_tab_border_hover_color=[80, 250, 123, 255])
    button = _tab(checked=True)
    button._is_hovered = True
    assert button._border_color(True, True).getRgb() == (255, 100, 180, 255)


def test_the_outline_follows_the_rounded_corners(qapp):
    """Stroked on the tab path, so a rounded corner stays uncovered."""
    _theme(sidebar_tab_flat_edge="none", sidebar_tab_border_width=2.0)
    assert _rounded_corners(_tab(checked=False)) == {
        "top_left", "top_right", "bottom_right", "bottom_left"}


# ── The inactive tab's own background ─────────────────────────────────────
def _fill(button, background=None):
    """The colour in the middle of the tab, clear of any edge treatment.

    Pass ``background`` to composite over it — a translucent fill reads as its
    own alpha against nothing, which is not what it looks like on the bar.
    """
    image = QImage(button.size(), QImage.Format_ARGB32)
    image.fill(0 if background is None else background)
    image = _render(button) if background is None else _render(button, image)
    return image.pixelColor(WIDTH // 2, HEIGHT // 2).getRgb()


def test_an_inactive_tab_paints_nothing_by_default(qapp):
    """tab_bg_normal is transparent in every shipped theme."""
    _theme()
    assert get_dock_style_manager().get(
        DockStyleCategory.SIDEBAR, "tab_bg_normal").alpha() == 0
    assert _fill(_tab(checked=False)) == (0, 0, 0, 0)


def test_an_inactive_tab_can_carry_a_background(qapp):
    _theme(sidebar_tab_bg_normal=[125, 124, 252, 255])
    assert _fill(_tab(checked=False)) == (125, 124, 252, 255)
    assert _fill(_tab(checked=True)) != (125, 124, 252, 255), \
        "the active tab lost its own background"


def test_the_inactive_background_can_be_the_highlight_colour(qapp):
    """The point of the token: every tab tinted with the accent, not just the
    active one. A low alpha reads as a tint rather than a slab."""
    accent = [255, 100, 180, 255]
    _theme(sidebar_tab_bg_normal=accent)
    idle = _tab(checked=False)
    assert _fill(idle) == tuple(accent) == \
        get_dock_style_manager().get(
            DockStyleCategory.SIDEBAR, "indicator_color").getRgb()

    _theme(sidebar_tab_bg_normal=[255, 100, 180, 40])
    tinted = _fill(_tab(checked=False))
    assert tinted[3] == 40, "the alpha was dropped, so it is a slab not a tint"


def test_hover_still_wins_over_the_inactive_background(qapp):
    """Normal / hover / active, the same triple the dock widget tabs use."""
    _theme(sidebar_tab_bg_normal=[125, 124, 252, 255])
    hovered = _tab(checked=False)
    hovered._is_hovered = True
    assert _fill(hovered) != (125, 124, 252, 255)


def test_the_whole_fill_triple_is_themeable(qapp):
    """Normal, hover and active — the hover pair as a horizontal gradient."""
    _theme(sidebar_tab_bg_normal=[10, 20, 30, 255],
           sidebar_tab_bg_hover_start=[200, 40, 40, 255],
           sidebar_tab_bg_hover_end=[40, 40, 200, 255],
           sidebar_tab_bg_active=[90, 200, 90, 255])
    assert _fill(_tab(checked=False)) == (10, 20, 30, 255)
    assert _fill(_tab(checked=True)) == (90, 200, 90, 255)

    hovered = _tab(checked=False)
    hovered._is_hovered = True
    image, mid = _render(hovered), HEIGHT // 2
    assert image.pixelColor(1, mid).getRgb()[0] > 150, "the gradient's start is missing"
    assert image.pixelColor(WIDTH - 2, mid).getRgb()[2] > 150, "...and its end"


def test_an_accent_hover_lifts_the_tints_ceiling(qapp):
    """Why the hover pair matters, not just that it is settable.

    A derived hover carries no accent and sits at a fixed lightness, so a tint
    pushed past it makes an idle tab out-glow a hovered one. Giving hover the
    accent as well raises the ceiling with it — the same alpha that inverts the
    two below is comfortably clear of them above.
    """
    accent, deep = [125, 124, 252], 90

    def luminance(hovered, **overrides):
        _theme(sidebar_tab_bg_normal=accent + [deep], **overrides)
        bar = get_dock_style_manager().get(DockStyleCategory.SIDEBAR, "bg_color")
        button = _tab(checked=False)
        button._is_hovered = hovered
        return sum(_fill(button, bar)[:3])

    assert luminance(True) < luminance(False), \
        "a derived hover was already brighter, so there is no ceiling to lift"
    assert luminance(True, sidebar_tab_bg_hover_start=accent + [160],
                     sidebar_tab_bg_hover_end=accent + [160]) > luminance(False), \
        "an accent hover still loses to the tint underneath it"


def test_the_background_follows_the_tabs_shape(qapp):
    """It is the tab's fill, so a rounded corner stays uncovered."""
    _theme(sidebar_tab_flat_edge="none", sidebar_tab_bg_normal=[125, 124, 252, 255])
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
           sidebar_tab_border_hover_color=[70, 80, 90, 255],
           sidebar_indicator_width=6, sidebar_indicator_position="right")
    sidebar = get_dock_style_manager().get_all(DockStyleCategory.SIDEBAR)
    assert sidebar["tab_flat_edge"] == "inward"
    assert sidebar["tab_corner_radius"] == 5
    assert sidebar["tab_border_width"] == 1.5
    assert sidebar["tab_border_closed"] is True
    assert sidebar["tab_border_normal_color"].getRgb() == (10, 20, 30, 255)
    assert sidebar["tab_border_active_color"].getRgb() == (40, 50, 60, 255)
    assert sidebar["tab_border_hover_color"].getRgb() == (70, 80, 90, 255)
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
        "sidebar_tab_border_hover_color": "#bd93f9",
        "sidebar_tab_border_closed": True,
        "sidebar_indicator_width": 5,
    }), encoding="utf-8")

    sidebar = load_theme_json(path)[DockStyleCategory.SIDEBAR]
    assert sidebar["tab_flat_edge"] == "outward"
    assert sidebar["tab_corner_radius"] == 8
    assert sidebar["tab_border_width"] == 2.0
    assert sidebar["tab_border_normal_color"] == [100, 112, 140, 255]
    assert sidebar["tab_border_hover_color"] == [189, 147, 249, 255]
    assert sidebar["tab_border_closed"] is True
    assert sidebar["indicator_width"] == 5


# ── The shipped presets ───────────────────────────────────────────────────
#: The presets that ring their sidebar tabs. Every other one sets tab_radius
#: but leaves the sidebar alone, so its tabs stay rectangles.
RINGED = ("cyberpunk_neon", "cyberpunk_edge", "midnight_haze", "violet_haze",
          "neon_dusk")
#: Of those, the ones shaped as a closed pill. neon_dusk is the odd one out: it
#: keeps a flat edge, so its outline is open along it.
PILL = RINGED[:4]
#: The ones that leave an *idle* tab bare — cyberpunk_edge and neon_dusk ring
#: both states. violet_haze belongs here: its extra ring is a hover state, and
#: an idle tab is as bare as the other two's.
ACTIVE_ONLY = ("cyberpunk_neon", "midnight_haze", "violet_haze")


def test_only_the_ringed_presets_opt_into_the_new_shape(qapp):
    """Every other preset sets tab_radius and still gets square sidebar tabs."""
    from lace.dock_custom_theme import DOCK_THEMES

    manager = get_dock_style_manager()
    for name in DOCK_THEMES:
        if name in RINGED:
            continue
        manager.apply_theme(name)
        sidebar = manager.get_all(DockStyleCategory.SIDEBAR)
        assert sidebar["tab_flat_edge"] == "all", f"{name} changed the tab shape"
        assert not sidebar["tab_border_width"], f"{name} outlines its sidebar tabs"


@pytest.mark.parametrize("name", PILL)
def test_the_pill_presets_share_one_shape(qapp, name):
    """Rounded on all four corners, so the ring closes the whole way round."""
    get_dock_style_manager().apply_theme(name)
    sidebar = get_dock_style_manager().get_all(DockStyleCategory.SIDEBAR)
    assert sidebar["tab_flat_edge"] == "none"
    assert sidebar["tab_border_width"] > 0
    assert _rounded_corners(_tab()) == {"top_left", "top_right",
                                        "bottom_right", "bottom_left"}
    assert _inked_edges(_tab()) == {"left", "top", "right", "bottom"}


@pytest.mark.parametrize("name", PILL)
def test_the_strip_matches_the_ring_it_sits_on(qapp, name):
    """Unequal widths step the edge the two share — the reason cyberpunk_edge
    already pins indicator_width to title_border_bottom.

    The strip is painted first and the ring covers it, so at equal widths the
    active tab is one clean line all the way round; left at the 3px default the
    strip stuck out inside the ring (a pink sliver in neon, doubled amber in
    edge). Measured on the content-facing edge, which is the one they share.
    """
    from math import ceil

    manager = get_dock_style_manager()
    manager.apply_theme(name)
    sidebar = manager.get_all(DockStyleCategory.SIDEBAR)
    assert sidebar["indicator_width"] == sidebar["tab_border_width"] > 0

    button = _tab(DockWidgetArea.left, checked=True)
    assert button._indicator_edge() == Qt.Edge.RightEdge, "not the shared edge"
    # One pixel further in than the ring can reach (its width, plus the row it
    # antialiases into). Nothing but the tab's own fill belongs there; a
    # too-wide strip is what would put ink on it.
    x = WIDTH - ceil(sidebar["tab_border_width"]) - 1
    assert _render(button).pixelColor(x, HEIGHT // 2).getRgb() == \
        sidebar["tab_bg_active"].getRgb(), \
        f"{name}: the line on the shared edge is thicker than the ring"


def test_midnight_haze_fills_its_inactive_tabs_with_the_accent(qapp):
    """The only preset that sets tab_bg_normal: every tab is tinted, and the
    ring alone says which is selected."""
    manager = get_dock_style_manager()
    manager.apply_theme("midnight_haze")
    sidebar = manager.get_all(DockStyleCategory.SIDEBAR)
    fill = sidebar["tab_bg_normal"]
    assert fill.alpha() > 0, "midnight_haze went back to a bare inactive tab"
    assert fill.getRgb()[:3] == sidebar["indicator_color"].getRgb()[:3], \
        "the inactive fill is not the highlight colour"

    bar = sidebar["bg_color"]
    idle = _fill(_tab(checked=False), bar)
    assert idle != bar.getRgb(), "nothing was painted over the bar"
    assert idle[2] > idle[0] + 15, f"the tint does not read as the accent: {idle}"

    hovered = _tab(checked=False)
    hovered._is_hovered = True
    hover = _fill(hovered, bar)
    assert hover != idle, "hover is indistinguishable from an idle tab"
    # Hover is derived from the base and carries no accent, so it can only stay
    # convincing while it is the *lighter* of the two — which is what caps the
    # alpha. Past that an idle tab out-glows a hovered one.
    assert sum(hover[:3]) > sum(idle[:3]), \
        f"a hovered tab is darker than an idle one: {hover} vs {idle}"


def test_no_other_preset_fills_its_inactive_tabs(qapp):
    from lace.dock_custom_theme import DOCK_THEMES

    manager = get_dock_style_manager()
    for name in DOCK_THEMES:
        if name == "midnight_haze":
            continue
        manager.apply_theme(name)
        assert not manager.get_all(
            DockStyleCategory.SIDEBAR)["tab_bg_normal"].alpha(), \
            f"{name} fills its inactive sidebar tabs"


@pytest.mark.parametrize("name", ACTIVE_ONLY)
def test_these_presets_ring_only_the_active_tab(qapp, name):
    get_dock_style_manager().apply_theme(name)
    active, inactive = _tab(checked=True), _tab(checked=False)
    assert inactive._border_color(False) is None, "the inactive tab is ringed"
    assert active._border_color(True) is not None
    assert not _inked_edges(inactive)
    assert _inked_edges(active) == {"left", "top", "right", "bottom"}


def test_violet_haze_rings_a_hovered_tab(qapp):
    """The only preset whose ring is a hover cue: bare, then a preview of the
    active ring under the cursor, then the solid accent when selected."""
    manager = get_dock_style_manager()
    manager.apply_theme("violet_haze")
    sidebar = manager.get_all(DockStyleCategory.SIDEBAR)
    hover, active = sidebar["tab_border_hover_color"], sidebar["tab_border_active_color"]
    assert hover.getRgb()[:3] == active.getRgb()[:3], "the hover ring is off-accent"
    assert 0 < hover.alpha() < active.alpha(), "the hover ring is not the fainter one"

    hovered = _tab(checked=False)
    hovered._is_hovered = True
    assert _inked_edges(hovered) == {"left", "top", "right", "bottom"}
    assert not _inked_edges(_tab(checked=False)), "an idle tab is ringed too"


@pytest.mark.parametrize("area, inside, outside", [
    (DockWidgetArea.left, "right", "left"),
    (DockWidgetArea.right, "left", "right"),
])
def test_neon_dusk_puts_the_ring_inside_and_the_strip_outside(qapp, area, inside, outside):
    """Its dock tabs' notch, run the other way round.

    Rounded and outlined on the content-facing side, flat and open against the
    window edge — and the highlight strip on that open edge, so the strip is
    what closes the outline instead of a rule under a tab bar. Both mirror with
    the sidebar the tab is in.
    """
    manager = get_dock_style_manager()
    manager.apply_theme("neon_dusk")
    sidebar = manager.get_all(DockStyleCategory.SIDEBAR)
    assert sidebar["tab_flat_edge"] == "outward"
    assert sidebar["indicator_position"] == "left", "the strip moved back inside"
    assert sidebar["indicator_width"] == sidebar["tab_border_width"] == 2.0

    assert _rounded_corners(_tab(area)) == {f"top_{inside}", f"bottom_{inside}"}
    assert _inked_edges(_tab(area)) == {"top", "bottom", inside}, \
        "the outline does not leave the window-facing edge open"

    # The strip fills that open edge, in the same accent the active ring uses.
    image = _render(_tab(area, checked=True))
    x = 0 if outside == "left" else WIDTH - 1
    assert image.pixelColor(x, HEIGHT // 2).getRgb() == \
        sidebar["indicator_color"].getRgb() == \
        sidebar["tab_border_active_color"].getRgb()


def test_no_other_preset_rings_on_hover(qapp):
    from lace.dock_custom_theme import DOCK_THEMES

    manager = get_dock_style_manager()
    for name in DOCK_THEMES:
        if name == "violet_haze":
            continue
        manager.apply_theme(name)
        assert manager.get_all(
            DockStyleCategory.SIDEBAR)["tab_border_hover_color"] is None, \
            f"{name} took on a hover ring"


def test_cyberpunk_edge_rings_every_tab_in_two_colours(qapp):
    """Its sidebar mirrors its card outline: violet unfocused, amber active."""
    get_dock_style_manager().apply_theme("cyberpunk_edge")
    active, inactive = _tab(checked=True), _tab(checked=False)
    assert inactive._border_color(False) is not None, "the inactive tab lost its ring"
    assert active._border_color(True) != inactive._border_color(False)
    for tab in (active, inactive):
        assert _inked_edges(tab) == {"left", "top", "right", "bottom"}
    mid = HEIGHT // 2
    assert _render(active).pixelColor(0, mid) != _render(inactive).pixelColor(0, mid), \
        "the two rings render identically"
