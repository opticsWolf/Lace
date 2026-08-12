# -*- coding: utf-8 -*-
"""The stripe under the sidebar overlay's title bar.

The sidebar overlay hosts a single widget and has no tab strip, so its header
stands in for one. The stripe therefore tracks what a dock area draws along the
same edge and appears only when both halves of that edge exist: the dock-area
title bar draws a bottom rule, *and* tabs draw an indicator along their bottom.

A theme with a rule but no bottom indicator — neon_dusk and violet_haze, which
mark the active tab with an outline instead — gets no stripe, rather than a
line nothing else in the theme echoes.
"""

import pytest
from PySide6.QtCore import QSize
from PySide6.QtWidgets import QLabel, QMainWindow

from lace.dock_chrome import (
    resolve_sidebar_title_bar_rule,
    resolve_title_bar_bottom_rule,
    tab_has_bottom_indicator,
)
from lace.dock_custom_theme import DOCK_THEMES
from lace.dock_manager import DockManager
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import DockStyleCategory, ThemeSpec, build_theme
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea


@pytest.fixture
def overlay(qapp):
    """A pinned widget shown in the sidebar overlay, so its title bar exists."""
    win = QMainWindow()
    win.resize(900, 600)
    dock_manager = DockManager(win)
    dock_widget = DockWidget("Alpha")
    dock_widget.set_widget(QLabel("x"))
    dock_manager.add_dock_widget(DockWidgetArea.left, dock_widget)
    win.show()
    qapp.processEvents()

    sidebar = dock_manager.sidebar_manager

    def show(theme):
        get_dock_style_manager().apply_theme(theme)
        qapp.processEvents()
        if not sidebar.is_pinned(dock_widget):
            sidebar.pin_widget(dock_widget, area=DockWidgetArea.left)
        qapp.processEvents()
        panel = sidebar._overlay
        panel.show_widget(dock_widget, DockWidgetArea.left,
                          animate=False, size=QSize(300, 400))
        qapp.processEvents()
        return panel._title_bar

    yield show

    win.close()
    get_dock_style_manager().apply_theme("default")


def _panel(title_bar):
    """The SideBarContainer hosting this header."""
    parent = title_bar.parent()
    while parent is not None and not hasattr(parent, "is_chrome_focused"):
        parent = parent.parent()
    assert parent is not None, "the header is not inside a sidebar container"
    return parent


def _spec(**overrides):
    base = dict(
        base=[20, 20, 30, 255],
        accent=[255, 100, 180, 255],
        text=[240, 240, 250, 255],
        border=[100, 110, 160, 255],
        title_border_bottom=1.5,
    )
    base.update(overrides)
    return ThemeSpec(**base)


# ── The gate ──────────────────────────────────────────────────────────────
def test_no_bottom_indicator_means_no_stripe(qapp):
    manager = get_dock_style_manager()
    try:
        manager.apply_theme_dict(build_theme(_spec(indicator_position="none")))
        assert resolve_title_bar_bottom_rule(manager)[0] > 0, \
            "the rule itself must still be there, or this proves nothing"
        assert resolve_sidebar_title_bar_rule(manager) == (0.0, None)
    finally:
        manager.apply_theme("default")


def test_top_indicator_means_no_stripe(qapp):
    """The indicator has to be on the *bottom* — that is the shared edge."""
    manager = get_dock_style_manager()
    try:
        manager.apply_theme_dict(build_theme(_spec(indicator_position="top")))
        assert resolve_sidebar_title_bar_rule(manager) == (0.0, None)
    finally:
        manager.apply_theme("default")


def test_no_rule_means_no_stripe(qapp):
    """A bottom indicator alone supplies no colour or width to draw with."""
    manager = get_dock_style_manager()
    try:
        manager.apply_theme_dict(build_theme(_spec(title_border_bottom=None)))
        assert tab_has_bottom_indicator(manager)
        assert resolve_sidebar_title_bar_rule(manager) == (0.0, None)
    finally:
        manager.apply_theme("default")


def test_stripe_matches_the_area_rule(qapp):
    manager = get_dock_style_manager()
    try:
        manager.apply_theme_dict(build_theme(_spec(indicator_position="bottom")))
        assert resolve_sidebar_title_bar_rule(manager) == \
            resolve_title_bar_bottom_rule(manager)
    finally:
        manager.apply_theme("default")


def test_full_outline_suppresses_the_stripe_too(qapp):
    """border_width > 0 means the area paints an outline, not a rule."""
    manager = get_dock_style_manager()
    try:
        manager.apply_theme_dict(build_theme(_spec(title_border_width=1.0)))
        assert resolve_sidebar_title_bar_rule(manager) == (0.0, None)
    finally:
        manager.apply_theme("default")


@pytest.mark.parametrize("position,expected", [
    ("bottom", True),
    ("none", False),
    ("top", False),
    ("top bottom", True),
    (["bottom"], True),
    (["top", "left"], False),
    ("BOTTOM", True),
])
def test_indicator_edge_forms(qapp, position, expected):
    """indicator_position takes a name, a separated list, or a sequence."""
    manager = get_dock_style_manager()
    try:
        manager.apply_theme_dict(build_theme(_spec(indicator_position=position)))
        assert tab_has_bottom_indicator(manager) is expected
    finally:
        manager.apply_theme("default")


def test_zero_indicator_width_means_no_bottom_indicator(qapp):
    manager = get_dock_style_manager()
    try:
        manager.apply_theme_dict(build_theme(_spec(indicator_width=0.0)))
        assert not tab_has_bottom_indicator(manager)
    finally:
        manager.apply_theme("default")


# ── Against the widget itself ─────────────────────────────────────────────
@pytest.mark.parametrize("theme", ["cyberpunk_edge", "slate_amber"])
def test_striped_presets_paint_the_area_rule_colour(overlay, theme):
    title_bar = overlay(theme)
    manager = get_dock_style_manager()
    # Focus-aware: a shown overlay takes focus, so its stripe is the focus
    # colour, not the resting one.
    focused = _panel(title_bar).is_chrome_focused()
    width, color = resolve_title_bar_bottom_rule(manager, focused)

    assert title_bar._title_border_bottom == width > 0
    assert title_bar._title_border_color.getRgb() == color.getRgb(), \
        "the stripe is not the colour of the dock-area title bar's bottom border"


@pytest.mark.parametrize("theme", ["neon_dusk", "violet_haze"])
def test_outline_presets_show_no_stripe(overlay, theme, qapp):
    """These have a rule but mark the active tab with an outline, not a
    bottom indicator — so the sidebar header carries no line."""
    title_bar = overlay(theme)
    manager = get_dock_style_manager()
    assert resolve_title_bar_bottom_rule(manager)[0] > 0, \
        f"{theme} lost its rule; this test would then pass for the wrong reason"

    assert not title_bar._title_border_bottom
    assert title_bar._title_border_color is None

    # ...and nothing is painted on the bottom row.
    image = title_bar.grab().toImage()
    row = {image.pixelColor(x, title_bar.height() - 1).name()
           for x in range(4, image.width() - 4)}
    assert len(row) == 1, f"{theme} painted something along the header's bottom: {row}"


@pytest.mark.parametrize("theme", ["cyberpunk_edge", "slate_amber"])
def test_stripe_tracks_the_overlay_focus(overlay, theme, qapp):
    """The stripe must be the colour the overlay's own outline is using.

    The overlay paints its card outline with focus_border_color while focused,
    so a stripe pinned to the resting colour put a violet line under an amber
    outline on cyberpunk_edge.
    """
    title_bar = overlay(theme)
    panel = _panel(title_bar)

    seen = {}
    for focused in (False, True):
        panel._sidebar_focused = focused
        title_bar.refresh_focus_tint()
        qapp.processEvents()
        outline = panel._focus_border_color if focused else panel._border_color
        assert title_bar._title_border_color.getRgb() == outline.getRgb(), \
            f"focused={focused}: stripe does not match the panel outline"
        seen[focused] = title_bar._title_border_color.getRgb()

    assert seen[False] != seen[True], \
        f"{theme} renders both focus states identically; this proves nothing"


def test_focus_change_repaints_the_stripe(overlay, qapp):
    """A stale cached colour is the failure mode: the container used to
    update() itself on focus without telling its header."""
    title_bar = overlay("cyberpunk_edge")
    panel = _panel(title_bar)

    panel._sidebar_focused = False
    title_bar.refresh_focus_tint()
    resting = title_bar._title_border_color.getRgb()

    # Leave the flag alone: _on_app_focus_changed derives it, and pre-setting
    # it would make the transition a no-op and the test vacuous.
    panel._on_app_focus_changed(None, title_bar)
    qapp.processEvents()
    assert title_bar._title_border_color.getRgb() != resting, \
        "the header kept the resting colour after the overlay took focus"


@pytest.mark.parametrize("theme", sorted(DOCK_THEMES))
def test_every_theme_agrees_with_the_gate(overlay, theme):
    """The widget must never disagree with the resolver, for any shipped theme."""
    title_bar = overlay(theme)
    width, color = resolve_sidebar_title_bar_rule(
        get_dock_style_manager(), _panel(title_bar).is_chrome_focused())
    assert title_bar._title_border_bottom == width
    if color is None:
        assert title_bar._title_border_color is None
    else:
        assert title_bar._title_border_color.getRgb() == color.getRgb()
