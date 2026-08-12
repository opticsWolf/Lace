# -*- coding: utf-8 -*-
"""The tab outline: left, top and right edges, bottom left open.

The alternative to TITLE_BAR.border_bottom. Where the rule runs *under* the
strip and the active tab breaks it, the outline runs *around* each tab and
leaves the bottom open, so the tab reads as joined to the panel below the way a
browser tab does. Which tabs get one is decided purely by the two colours: a
transparent one turns that state off.

Rendered pixels rather than token values wherever the claim is about what is
drawn — the geometry is the point of this feature, and a token that reaches
paint_tab but lands on the wrong edge would pass a token-level test.
"""

import pytest
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QLabel, QMainWindow

from lace.dock_custom_theme import THEME_SPECS
from lace.dock_manager import DockManager
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import DockStyleCategory, ThemeSpec, build_theme
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea

OUTLINE_THEMES = ("neon_dusk", "violet_haze")


@pytest.fixture
def desk(qapp):
    win = QMainWindow()
    win.resize(900, 600)
    dock_manager = DockManager(win)

    def mk(name):
        dock_widget = DockWidget(name)
        dock_widget.set_widget(QLabel(name))
        return dock_widget

    area = dock_manager.add_dock_widget(DockWidgetArea.left, mk("Alpha"))
    dock_manager.add_dock_widget(DockWidgetArea.center, mk("Beta"), area)
    other = dock_manager.add_dock_widget(DockWidgetArea.bottom, mk("Gamma"))
    win.show()
    qapp.processEvents()
    dock_manager.set_active_dock_area(area)
    qapp.processEvents()

    yield dock_manager, area, other

    win.close()
    get_dock_style_manager().apply_theme("default")


def _tabs(area):
    tabs = [area.dock_widget(i).tab_widget() for i in range(area.dock_widgets_count())]
    active = [t for t in tabs if t._is_active_tab]
    inactive = [t for t in tabs if not t._is_active_tab]
    assert active and inactive, "need one of each for this test to mean anything"
    return active[0], inactive[0]


def _render(tab, qapp):
    # The offscreen cursor sits at (0, 0), which is over the first tab — clear
    # the hover flag or half these reads come back in the hover background.
    tab._hovered = False
    qapp.processEvents()
    img = QImage(tab.size(), QImage.Format_ARGB32)
    img.fill(0)
    tab.render(img)
    return img


def _outline_edges(tab, qapp):
    """Which edges the outline actually paints, as a set of names.

    Measured by rendering the same tab twice, with and without the outline, and
    asking which edges changed. A difference rather than a match against the
    outline's own colour: a 1.5px stroke is antialiased across two pixel rows,
    so whether any single pixel comes back *exactly* the outline colour depends
    on where the stroke happens to land — closing the bottom of the path
    produced a 25%-covered row that an exact match read as untouched.

    Only the middle third of each edge is sampled. The corners are antialiased
    against the strip, and the side strokes legitimately run all the way down
    to the bottom row; what separates an open bottom from a closed one is the
    horizontal span between them, not its endpoints.
    """
    on = _render(tab, qapp)
    saved = tab._outline_width
    tab._outline_width = 0.0
    try:
        off = _render(tab, qapp)
    finally:
        tab._outline_width = saved

    w, h = tab.width(), tab.height()
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


def _spec(**overrides):
    base = dict(
        base=[20, 20, 30, 255],
        accent=[255, 100, 180, 255],
        text=[240, 240, 250, 255],
        tab_border_width=2.0,
        # As the shipped outline presets do — and here it is load-bearing: the
        # default "bottom" indicator is the accent, the same colour these tests
        # give the active outline, so it would paint the outline's colour onto
        # the very edge the outline is supposed to leave open.
        indicator_position="none",
    )
    base.update(overrides)
    return ThemeSpec(**base)


# ── Geometry ──────────────────────────────────────────────────────────────
def test_outline_covers_three_edges_and_leaves_the_bottom_open(desk, qapp):
    get_dock_style_manager().apply_theme("violet_haze")
    qapp.processEvents()   # DockStyled defers refresh_style to the next frame
    _, area, _ = desk
    active, _ = _tabs(area)

    outline = active._outline_color
    assert outline is not None and active._outline_width > 0

    assert _outline_edges(active, qapp) == {"left", "top", "right"}, \
        "the outline must cover exactly three edges and leave the bottom open"


def test_top_open_path_omits_the_bottom_segment(qapp):
    """The helper is top_rounded_path minus its closeSubpath()."""
    from PySide6.QtCore import QRectF
    from lace.dock_paint import top_open_path, top_rounded_path

    rect = QRectF(0, 0, 60, 24)
    for radius in (0.0, 6.0):
        open_path = top_open_path(rect, radius)
        closed = top_rounded_path(rect, radius)
        assert open_path.elementCount() < closed.elementCount() or \
            not open_path.contains(rect.center()), \
            f"radius={radius}: the open path still closes across the bottom"
        # Both start and end on the bottom edge, so the three drawn sides span
        # the full height.
        assert open_path.elementAt(0).y == pytest.approx(rect.bottom())
        last = open_path.elementAt(open_path.elementCount() - 1)
        assert last.y == pytest.approx(rect.bottom())


# ── Which tabs get an outline ─────────────────────────────────────────────
def test_transparent_colour_turns_a_state_off(desk, qapp):
    """A transparent colour, not a missing one, is how a state opts out."""
    _, area, _ = desk
    manager = get_dock_style_manager()
    manager.apply_theme_dict(build_theme(_spec(
        tab_border_color=[0, 0, 0, 0],
        tab_border_active_color=[255, 100, 180, 255],
    )))
    qapp.processEvents()

    active, inactive = _tabs(area)
    assert active._outline_color is not None, "the active tab lost its outline"
    assert inactive._outline_color is None, "a transparent colour still drew"

    assert _outline_edges(active, qapp) == {"left", "top", "right"}
    assert not _outline_edges(inactive, qapp), \
        "an unoutlined tab still has ink on its edges"


def test_zero_width_disables_the_outline_entirely(desk, qapp):
    _, area, _ = desk
    manager = get_dock_style_manager()
    # The colours stay set — only the width is zeroed, which is the master
    # switch every theme relies on to leave the outline off by default.
    outlined = build_theme(_spec(tab_border_active_color=[255, 100, 180, 255]))
    bare = build_theme(_spec(tab_border_active_color=[255, 100, 180, 255],
                             tab_border_width=0.0))
    manager.apply_theme_dict(outlined)
    qapp.processEvents()
    active, _ = _tabs(area)
    color = active._outline_color
    assert _outline_edges(active, qapp), "nothing drawn to switch off"

    manager.apply_theme_dict(bare)
    qapp.processEvents()
    assert not _outline_edges(active, qapp), "border_width=0 still drew an outline"


def test_both_states_can_differ(desk, qapp):
    _, area, _ = desk
    manager = get_dock_style_manager()
    manager.apply_theme_dict(build_theme(_spec(
        tab_border_color=[100, 110, 160, 255],
        tab_border_active_color=[255, 100, 180, 255],
    )))
    qapp.processEvents()

    active, inactive = _tabs(area)
    assert active._outline_color != inactive._outline_color
    for tab in (active, inactive):
        assert _outline_edges(tab, qapp) == {"left", "top", "right"}, \
            "both states are outlined, on the same three edges"
    # ...and the two are told apart on screen, not only in the token dict.
    mid = inactive.height() // 2
    assert _render(active, qapp).pixelColor(0, mid) != \
        _render(inactive, qapp).pixelColor(0, mid), \
        "the two outlines render identically"


def test_outline_width_is_shared_by_both_states(desk, qapp):
    """One width for both, so every tab's edges sit on the same pixels."""
    _, area, _ = desk
    get_dock_style_manager().apply_theme("neon_dusk")
    qapp.processEvents()
    active, inactive = _tabs(area)
    assert active._outline_width == inactive._outline_width > 0


# ── Focus ─────────────────────────────────────────────────────────────────
def test_active_outline_dims_with_the_area(desk, qapp):
    dock_manager, area, other = desk
    get_dock_style_manager().apply_theme_dict(build_theme(_spec(
        tab_border_active_color=[255, 100, 180, 255], tab_dimming=True)))
    qapp.processEvents()

    active, _ = _tabs(area)
    focused = active._outline_color
    dock_manager.set_active_dock_area(other)
    qapp.processEvents()
    assert active._outline_color != focused, "the outline ignored the focus change"


def test_outline_does_not_dim_without_tab_dimming(desk, qapp):
    dock_manager, area, other = desk
    get_dock_style_manager().apply_theme_dict(build_theme(_spec(
        tab_border_active_color=[255, 100, 180, 255], tab_dimming=False)))
    qapp.processEvents()

    active, _ = _tabs(area)
    focused = active._outline_color
    dock_manager.set_active_dock_area(other)
    qapp.processEvents()
    assert active._outline_color == focused


# ── The shipped presets ───────────────────────────────────────────────────
def test_slate_amber_ships_the_rule_not_the_outline(qapp):
    manager = get_dock_style_manager()
    manager.apply_theme("slate_amber")
    try:
        tab = manager.get_all(DockStyleCategory.TAB)
        title_bar = manager.get_all(DockStyleCategory.TITLE_BAR)
        assert title_bar["border_bottom"] > 0, "slate_amber lost its bottom rule"
        assert not tab["border_width"], "slate_amber draws both treatments at once"
    finally:
        manager.apply_theme("default")


def test_neon_dusk_outlines_every_tab(qapp):
    manager = get_dock_style_manager()
    manager.apply_theme("neon_dusk")
    try:
        tab = manager.get_all(DockStyleCategory.TAB)
        assert tab["border_width"] > 0
        assert tab["border_normal_color"].alpha() > 0, "inactive tabs are unoutlined"
        assert tab["border_active_color"].alpha() > 0
        assert tab["border_normal_color"] != tab["border_active_color"], \
            "neon_dusk renders active and inactive tabs identically"
    finally:
        manager.apply_theme("default")


def test_violet_haze_outlines_only_the_active_tab(qapp):
    manager = get_dock_style_manager()
    manager.apply_theme("violet_haze")
    try:
        tab = manager.get_all(DockStyleCategory.TAB)
        assert tab["border_width"] > 0
        assert tab["border_normal_color"].alpha() == 0, \
            "violet_haze exists to show the active-tab-only look"
        assert tab["border_active_color"].alpha() > 0
    finally:
        manager.apply_theme("default")


@pytest.mark.parametrize("name", OUTLINE_THEMES)
def test_outline_presets_avoid_the_conflicting_settings(name):
    """The rule and the outline are alternatives, and so are the outline and a
    bottom indicator: at "bottom" the indicator fills the gap the outline
    deliberately leaves open."""
    spec = THEME_SPECS[name]
    assert spec.tab_border_width, f"{name} is meant to demonstrate the outline"
    assert not spec.title_border_bottom, \
        f"{name} sets both the rule and the outline; that boxes inactive tabs"
    assert spec.indicator_position == "none", \
        f"{name} stacks an indicator on an edge the outline already owns"
