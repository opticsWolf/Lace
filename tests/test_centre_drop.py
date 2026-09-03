# -*- coding: utf-8 -*-
"""Dropping on the centre of a container — IMPROVEMENT_PLAN_v0.7.md Phase 3.

Two independent causes kept a floating widget from tabbing into a one-area
container:

1. The drag offered ``no_area`` (== 0) for a solo area, so DockOverlayCross
   hid *every* indicator, centre included, and cursor_location() could only
   return invalid.
2. ``_drop_into_container()`` had no centre branch, and
   ``dock_area_insert_parameters()`` aliased centre to bottom, so a centre drop
   that did get through split vertically instead of tabbing.

Plus two smaller defects in the tabbing path itself: dropped widgets were
prepended rather than appended, and an all-closed drop called
``set_current_index(-1)``.
"""

import logging

import pytest
from PySide6.QtWidgets import QLabel, QMainWindow

from lace.dock_manager import DockManager
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea
from lace.floating_behaviour import allowed_areas_for
from lace.floating_dock_container import FloatingDockContainer


@pytest.fixture
def desk(qapp):
    win = QMainWindow()
    win.resize(900, 600)
    dock_manager = DockManager(win)
    win.show()
    qapp.processEvents()
    yield win, dock_manager
    win.close()


def _mk(name):
    dock_widget = DockWidget(name)
    dock_widget.set_widget(QLabel(name))
    return dock_widget


def _float(dock_manager, name):
    floating = FloatingDockContainer(dock_widget=_mk(name),
                                     dock_manager=dock_manager)
    floating.show()
    return floating


def test_a_solo_area_offers_the_centre_indicator(desk, qapp):
    win, dock_manager = desk
    area = dock_manager.add_dock_widget(DockWidgetArea.center, _mk("Alpha"))
    qapp.processEvents()

    container = dock_manager.root_container()
    assert container.visible_dock_area_count() == 1, "fixture is not solo"

    allowed = allowed_areas_for(container, area)
    assert allowed & DockWidgetArea.center, \
        "a lone dock area offered no centre indicator, so it could not be tabbed into"


def test_a_multi_area_container_still_offers_everything(desk, qapp):
    win, dock_manager = desk
    area = dock_manager.add_dock_widget(DockWidgetArea.center, _mk("Alpha"))
    dock_manager.add_dock_widget(DockWidgetArea.right, _mk("Beta"))
    qapp.processEvents()

    allowed = allowed_areas_for(dock_manager.root_container(), area)
    assert allowed == DockWidgetArea.all_dock_areas


def test_dropping_on_centre_of_a_solo_container_tabs(desk, qapp):
    """One dock area with two tabs — not two dock areas."""
    win, dock_manager = desk
    dock_manager.add_dock_widget(DockWidgetArea.center, _mk("Alpha"))
    qapp.processEvents()

    container = dock_manager.root_container()
    dock_manager.drop_controller()._drop_into_container(
        _float(dock_manager, "Beta"), DockWidgetArea.center)
    qapp.processEvents()

    assert len(container.opened_dock_areas()) == 1, \
        "a centre drop split the container instead of tabbing into it"
    titles = [w.windowTitle() for w in container.dock_widgets()]
    assert titles == ["Alpha", "Beta"], titles


def test_dropped_tabs_are_appended_not_prepended(desk, qapp):
    win, dock_manager = desk
    target = dock_manager.add_dock_widget(DockWidgetArea.center, _mk("Alpha"))
    qapp.processEvents()

    dock_manager.drop_controller()._drop_into_center_of_section(
        _float(dock_manager, "Beta"), target)
    qapp.processEvents()

    titles = [w.windowTitle() for w in target.dock_widgets()]
    assert titles[0] == "Alpha", f"the pre-existing tab lost index 0: {titles}"
    assert titles == ["Alpha", "Beta"], titles


def test_the_dropped_widget_becomes_current(desk, qapp):
    win, dock_manager = desk
    target = dock_manager.add_dock_widget(DockWidgetArea.center, _mk("Alpha"))
    qapp.processEvents()

    dock_manager.drop_controller()._drop_into_center_of_section(
        _float(dock_manager, "Beta"), target)
    qapp.processEvents()

    current = target.current_dock_widget()
    assert current is not None and current.windowTitle() == "Beta", \
        "the selection was not carried across into the target's numbering"


def test_an_all_closed_drop_does_not_log_an_invalid_index(desk, qapp, caplog):
    win, dock_manager = desk
    target = dock_manager.add_dock_widget(DockWidgetArea.center, _mk("Alpha"))
    qapp.processEvents()

    floating = _float(dock_manager, "Beta")
    for dock_widget in floating.dock_container().dock_widgets():
        dock_widget.toggle_view(False)
    qapp.processEvents()

    with caplog.at_level(logging.WARNING):
        dock_manager.drop_controller()._drop_into_center_of_section(floating, target)
        qapp.processEvents()

    offenders = [r.getMessage() for r in caplog.records if "Invalid index" in r.getMessage()]
    assert not offenders, offenders


def test_multi_area_centre_drop_still_splits(desk, qapp):
    """The deliberate fallback: centre of a multi-area container is ambiguous.

    Guards the decision rather than a bug — this one passes on 2f16f8e too,
    where it happened by accident through the center/bottom alias.
    """
    win, dock_manager = desk
    dock_manager.add_dock_widget(DockWidgetArea.center, _mk("Alpha"))
    dock_manager.add_dock_widget(DockWidgetArea.right, _mk("Beta"))
    qapp.processEvents()

    container = dock_manager.root_container()
    before = len(container.opened_dock_areas())
    dock_manager.drop_controller()._drop_into_container(
        _float(dock_manager, "Gamma"), DockWidgetArea.center)
    qapp.processEvents()

    assert len(container.opened_dock_areas()) == before + 1
