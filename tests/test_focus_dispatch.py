# -*- coding: utf-8 -*-
"""Focus fan-out and style-refresh error handling — plan v0.7 §7.1, §7.5.

Two hygiene contracts that only show up under load or under a bug:

* focus dispatch is O(depth), not O(open areas).  Every DockAreaWidget used to
  connect to ``QApplication.focusChanged`` itself and answer "is the focused
  widget inside me?" with an ``isAncestorOf()`` walk, so the cost of one of
  Qt's hottest signals grew with every area the user opened;
* a subscriber whose ``refresh_style()`` raises a real bug must not have it
  swallowed into a log line, leaving a widget silently wearing the old theme.
"""

import pytest
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow

from lace.dock_area_widget import DockAreaWidget
from lace.dock_manager import DockManager
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import DockStyleCategory
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea


@pytest.fixture
def four_areas(qapp):
    win = QMainWindow()
    win.resize(900, 700)
    manager = DockManager(win)

    def mk(name):
        dock_widget = DockWidget(name)
        dock_widget.set_widget(QLabel(name))
        return dock_widget

    widgets = [mk(n) for n in ("Alpha", "Beta", "Gamma", "Delta")]
    manager.add_dock_widget(DockWidgetArea.left, widgets[0])
    manager.add_dock_widget(DockWidgetArea.right, widgets[1])
    manager.add_dock_widget(DockWidgetArea.bottom, widgets[2])
    manager.add_dock_widget(DockWidgetArea.top, widgets[3])
    win.show()
    qapp.processEvents()

    yield manager, win, widgets

    win.close()


def test_areas_do_not_connect_to_focus_changed_themselves(four_areas):
    """The connection lives on the manager, once, not on every area."""
    _, _, widgets = four_areas
    for dock_widget in widgets:
        area = dock_widget.dock_area_widget()
        assert not hasattr(area, "_on_app_focus_changed"), (
            "DockAreaWidget still owns a focusChanged slot")


def test_one_dispatch_per_focus_change_not_one_per_area(four_areas):
    """Four open areas still resolve a focus change with a single lookup."""
    manager, _, widgets = four_areas
    activations = []
    original = DockAreaWidget.handle_focus_gained
    DockAreaWidget.handle_focus_gained = lambda self: (
        activations.append(self), original(self))[1]
    try:
        target = widgets[2].widget()
        manager._on_app_focus_changed(None, target)
    finally:
        DockAreaWidget.handle_focus_gained = original

    assert activations == [widgets[2].dock_area_widget()]


def test_focus_inside_an_area_still_activates_it(four_areas):
    """The cheaper dispatch must not lose the behaviour it replaced."""
    manager, _, widgets = four_areas
    manager._on_app_focus_changed(None, widgets[1].widget())
    assert manager._active_dock_area is widgets[1].dock_area_widget()


def test_focus_outside_any_area_activates_nothing(four_areas):
    """A widget with no DockAreaWidget above it resolves to no area."""
    manager, win, widgets = four_areas
    manager._on_app_focus_changed(None, widgets[0].widget())
    before = manager._active_dock_area

    stray = QLabel("stray", win)
    manager._on_app_focus_changed(None, stray)

    assert manager._active_dock_area is before


def test_a_broken_refresh_style_is_not_swallowed(qapp):
    """A genuine bug in a subscriber propagates instead of becoming a log line.

    Only ``RuntimeError`` — the deleted-C++-object case — is still caught.
    """
    class Broken:
        def refresh_style(self):
            raise ValueError("boom")

    manager = get_dock_style_manager()
    broken = Broken()
    manager.register(broken, DockStyleCategory.TAB)
    try:
        with pytest.raises(ValueError, match="boom"):
            manager.update(DockStyleCategory.TAB, corner_radius=7)
    finally:
        manager.unregister(broken, DockStyleCategory.TAB)
