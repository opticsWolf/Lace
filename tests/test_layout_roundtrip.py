# -*- coding: utf-8 -*-
"""Layout save/restore round-trip tests — docs/CODE_REVIEW.md §6.

These assert *placement*, not just the boolean returned by restore_state().
Before the v0.5.1 fix, restore_state() returned True while orphaning every
dock widget, and the only round-trip check in the repo (a dev_smoke script
asserting that boolean) passed on the broken build.
"""

import pytest
from PySide6.QtWidgets import QLabel, QMainWindow

from lace.dock_manager import DockManager
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea


@pytest.fixture
def manager(qapp):
    win = QMainWindow()
    dm = DockManager(win)
    win.resize(1000, 700)
    win.show()
    qapp.processEvents()
    yield dm
    win.close()


def _mk(name):
    dock_widget = DockWidget(name)
    dock_widget.set_widget(QLabel(name))
    return dock_widget


def _snapshot(dm):
    """The placement facts a restore must reproduce."""
    return {
        name: (
            dw.is_closed(),
            dw.dock_area_widget() is not None,
            dw.dock_area_widget().index(dw) if dw.dock_area_widget() else -1,
            dw.is_pinned(),
        )
        for name, dw in dm.dock_widgets_map().items()
    }


def test_docked_widgets_survive_roundtrip(manager, qapp):
    area = manager.add_dock_widget(DockWidgetArea.left, _mk("Alpha"))
    manager.add_dock_widget(DockWidgetArea.center, _mk("Beta"), area)
    manager.add_dock_widget(DockWidgetArea.bottom, _mk("Gamma"))
    qapp.processEvents()

    before = _snapshot(manager)
    assert manager.restore_state(manager.save_state()) is True
    qapp.processEvents()

    assert _snapshot(manager) == before, "widgets were not restored to their dock areas"
    for dock_widget in manager.dock_widgets_map().values():
        assert dock_widget.dock_area_widget() is not None, \
            f"{dock_widget.objectName()} was orphaned by restore"
        assert not dock_widget.is_closed()


def test_active_tab_survives_roundtrip(manager, qapp):
    area = manager.add_dock_widget(DockWidgetArea.left, _mk("Alpha"))
    manager.add_dock_widget(DockWidgetArea.center, _mk("Beta"), area)
    area.set_current_index(1)
    qapp.processEvents()

    manager.restore_state(manager.save_state())
    qapp.processEvents()
    assert manager.root_container().dock_area(0).current_index() == 1


def test_closed_widget_stays_closed(manager, qapp):
    area = manager.add_dock_widget(DockWidgetArea.left, _mk("Alpha"))
    beta = _mk("Beta")
    manager.add_dock_widget(DockWidgetArea.center, beta, area)
    beta.toggle_view(False)
    qapp.processEvents()
    assert beta.is_closed()

    manager.restore_state(manager.save_state())
    qapp.processEvents()
    assert beta.is_closed(), "a closed widget was reopened by restore"
    assert not manager.find_dock_widget("Alpha").is_closed()


def test_maximize_state_is_not_left_dangling(manager, qapp):
    manager.add_dock_widget(DockWidgetArea.left, _mk("Alpha"))
    area = manager.add_dock_widget(DockWidgetArea.bottom, _mk("Gamma"))
    area.toggle_maximize()
    qapp.processEvents()

    manager.restore_state(manager.save_state())
    qapp.processEvents()

    container = manager.root_container()
    maximized = container._maximized_dock_area
    live_areas = [container.dock_area(i) for i in range(container.dock_area_count())]
    assert maximized is None or maximized in live_areas, \
        "restore left _maximized_dock_area pointing at a destroyed area"


def test_restore_reports_failure_on_corrupt_payload(manager, qapp):
    manager.add_dock_widget(DockWidgetArea.left, _mk("Alpha"))
    qapp.processEvents()

    assert manager.restore_state("{not valid json") is False
    assert manager.restore_state('{"type": "NotLace", "version": 0}') is False


def test_restore_ignores_widgets_that_no_longer_exist(manager, qapp):
    manager.add_dock_widget(DockWidgetArea.left, _mk("Alpha"))
    manager.add_dock_widget(DockWidgetArea.bottom, _mk("Gamma"))
    qapp.processEvents()
    state = manager.save_state()

    # Simulate an application that dropped a panel between releases.
    manager.remove_dock_widget(manager.find_dock_widget("Gamma"))
    qapp.processEvents()

    assert manager.restore_state(state) is True
    qapp.processEvents()
    assert manager.find_dock_widget("Alpha").dock_area_widget() is not None
