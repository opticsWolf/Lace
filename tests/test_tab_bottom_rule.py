# -*- coding: utf-8 -*-
"""The tab strip's bottom rule, and how tabs continue it.

When TITLE_BAR.border_bottom is set, the rule runs the full width under the
tab strip. Inactive tabs continue it across themselves so the line reads as
unbroken; the active tab leaves the gap, which is what makes it look joined to
the panel below. The colour follows the dock area's focus state, exactly as the
area's own outline does.
"""

import pytest
from PySide6.QtWidgets import QLabel, QMainWindow

from lace.dock_chrome import resolve_title_bar_border_color, resolve_title_bar_bottom_rule
from lace.dock_manager import DockManager
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import DockStyleCategory, ThemeSpec, build_theme
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea


NEUTRAL = [0, 180, 205, 255]
FOCUS = [0, 240, 255, 255]


def _spec(**overrides):
    base = dict(
        base=[14, 11, 28, 255],
        accent=[255, 0, 127, 255],
        text=[245, 245, 255, 255],
        border=NEUTRAL,
        focus_border_color=FOCUS,
    )
    base.update(overrides)
    return ThemeSpec(**base)


@pytest.fixture
def desk(qapp):
    """Two areas: one with two tabs, one with a single tab."""
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

    yield dock_manager, area, other

    win.close()
    get_dock_style_manager().apply_theme("default")


def _tabs(area):
    return {area.dock_widget(i).objectName(): area.dock_widget(i).tab_widget()
            for i in range(area.dock_widgets_count())}


def _draws_rule(tab):
    return (not tab._is_active_tab
            and tab._bottom_rule_width > 0
            and tab._bottom_rule_color is not None)


def test_inactive_tabs_continue_the_rule_active_tab_breaks_it(desk, qapp):
    dock_manager, area, _ = desk
    get_dock_style_manager().apply_theme_dict(build_theme(_spec(title_border_bottom=1.5)))
    dock_manager.set_active_dock_area(area)
    qapp.processEvents()

    tabs = _tabs(area)
    active = [t for t in tabs.values() if t._is_active_tab]
    inactive = [t for t in tabs.values() if not t._is_active_tab]
    assert active and inactive, "need one of each for this test to mean anything"

    for tab in inactive:
        assert _draws_rule(tab), "an inactive tab did not continue the rule"
    for tab in active:
        assert not _draws_rule(tab), "the active tab should leave a gap in the rule"


def test_tab_rule_matches_the_strip_exactly(desk, qapp):
    """Same width and colour — the two must not drift apart."""
    dock_manager, area, _ = desk
    get_dock_style_manager().apply_theme_dict(build_theme(_spec(title_border_bottom=2.0)))
    dock_manager.set_active_dock_area(area)
    qapp.processEvents()

    title_bar = area._title_bar
    for name, tab in _tabs(area).items():
        assert tab._bottom_rule_width == title_bar._border_bottom, name
        assert tab._bottom_rule_color == title_bar._border_color, name


def test_no_rule_configured_means_no_rule_drawn(desk, qapp):
    dock_manager, area, _ = desk
    get_dock_style_manager().apply_theme_dict(build_theme(_spec()))
    qapp.processEvents()

    for name, tab in _tabs(area).items():
        assert not _draws_rule(tab), f"{name} drew a rule the theme never asked for"


def test_rule_colour_follows_focus(desk, qapp):
    dock_manager, area, other = desk
    get_dock_style_manager().apply_theme_dict(build_theme(
        _spec(title_border_bottom=1.5, title_border_focus_color=FOCUS)))

    dock_manager.set_active_dock_area(area)
    qapp.processEvents()
    focused = area._title_bar._border_color
    unfocused = other._title_bar._border_color
    assert focused.getRgb() == tuple(FOCUS)
    assert unfocused.getRgb() == tuple(NEUTRAL)

    # ...and the tabs track their own area, not the global active one.
    for tab in _tabs(area).values():
        assert tab._bottom_rule_color.getRgb() == tuple(FOCUS)
    for tab in _tabs(other).values():
        assert tab._bottom_rule_color.getRgb() == tuple(NEUTRAL)

    dock_manager.set_active_dock_area(other)
    qapp.processEvents()
    assert area._title_bar._border_color.getRgb() == tuple(NEUTRAL)
    assert other._title_bar._border_color.getRgb() == tuple(FOCUS)


def test_full_outline_suppresses_the_bottom_rule(qapp):
    """border_width > 0 paints the whole outline; the rule branch never runs."""
    manager = get_dock_style_manager()
    manager.apply_theme_dict(build_theme(
        _spec(title_border_bottom=1.5, title_border_width=1.0)))
    try:
        width, color = resolve_title_bar_bottom_rule(manager)
        assert width == 0.0 and color is None
    finally:
        manager.apply_theme("default")


def test_border_colour_falls_back_to_core(qapp):
    """TITLE_BAR wins, CORE fills in — for both the normal and focus colour."""
    manager = get_dock_style_manager()
    manager.apply_theme_dict(build_theme(_spec(title_border_bottom=1.5)))
    try:
        core = manager.get_all(DockStyleCategory.CORE)
        assert resolve_title_bar_border_color(manager, focused=False) is not None
        assert resolve_title_bar_border_color(manager, focused=True).getRgb() == \
            core["focus_border_color"].getRgb()
    finally:
        manager.apply_theme("default")


def test_cyberpunk_edge_shows_the_focus_swap(desk, qapp):
    """The reference preset must actually demonstrate both states."""
    dock_manager, area, other = desk
    get_dock_style_manager().apply_theme("cyberpunk_edge")
    dock_manager.set_active_dock_area(area)
    qapp.processEvents()

    assert area._title_bar._border_color != other._title_bar._border_color, \
        "cyberpunk_edge renders focused and unfocused rules identically"
