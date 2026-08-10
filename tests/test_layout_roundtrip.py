# -*- coding: utf-8 -*-
"""Layout save/restore round-trip tests — docs/CODE_REVIEW.md §6.

These assert *placement*, not just the boolean returned by restore_state().
Before the v0.5.1 fix, restore_state() returned True while orphaning every
dock widget, and the only round-trip check in the repo (a dev_smoke script
asserting that boolean) passed on the broken build.
"""

import json

import pytest
from PySide6.QtWidgets import QLabel, QMainWindow

from lace.dock_manager import DockManager
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea
from lace.floating_dock_container import FloatingDockContainer


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


def test_pinned_widget_survives_roundtrip(manager, qapp):
    manager.add_dock_widget(DockWidgetArea.left, _mk("Alpha"))
    beta = _mk("Beta")
    manager.add_dock_widget(DockWidgetArea.right, beta)
    manager.sidebar_manager.pin_widget(beta, area=DockWidgetArea.left)
    qapp.processEvents()
    assert manager.sidebar_manager.is_pinned(beta)

    manager.restore_state(manager.save_state())
    qapp.processEvents()

    restored = manager.find_dock_widget("Beta")
    assert manager.sidebar_manager.is_pinned(restored), \
        "a pinned widget was not returned to its sidebar"
    assert not restored.is_closed(), \
        "a pinned widget came back closed"


def test_locking_survives_roundtrip(manager, qapp):
    beta = _mk("Beta")
    area = manager.add_dock_widget(DockWidgetArea.left, beta)
    area.locked_name = "sidebar"
    beta.locked_to_area = "sidebar"
    qapp.processEvents()

    manager.restore_state(manager.save_state())
    qapp.processEvents()

    restored = manager.find_dock_widget("Beta")
    assert restored.locked_to_area == "sidebar"
    assert restored.dock_area_widget().locked_name == "sidebar"


def test_unlocked_layout_omits_lock_keys(manager, qapp):
    manager.add_dock_widget(DockWidgetArea.left, _mk("Alpha"))
    qapp.processEvents()
    state = manager.save_state()
    assert "locked_to_area" not in state
    assert "locked_name" not in state


def test_floating_geometry_survives_roundtrip(manager, qapp):
    manager.add_dock_widget(DockWidgetArea.left, _mk("Alpha"))
    beta = _mk("Beta")
    beta.set_dock_manager(manager)
    manager.dock_widgets_map()[beta.objectName()] = beta
    floating = FloatingDockContainer(dock_widget=beta)
    floating.show()
    qapp.processEvents()

    floating.setGeometry(220, 180, 480, 360)
    qapp.processEvents()
    before = floating.geometry()

    manager.restore_state(manager.save_state())
    qapp.processEvents()

    after = manager.find_dock_widget("Beta").dock_container().floating_widget().geometry()
    assert after == before, "restore did not reproduce the floating window geometry"


def test_restore_reports_failure_on_corrupt_payload(manager, qapp):
    manager.add_dock_widget(DockWidgetArea.left, _mk("Alpha"))
    qapp.processEvents()

    assert manager.restore_state("{not valid json") is False
    assert manager.restore_state('{"type": "NotLace", "version": 0}') is False


def test_structurally_broken_tree_leaves_layout_intact(manager, qapp):
    manager.add_dock_widget(DockWidgetArea.left, _mk("Alpha"))
    manager.add_dock_widget(DockWidgetArea.bottom, _mk("Gamma"))
    qapp.processEvents()
    before = _snapshot(manager)

    # A splitter whose sizes list contradicts its count: structurally valid
    # JSON that only blows up partway through the rebuild.
    state = json.loads(manager.save_state())
    root = state["containers"][0]["data"]["root_splitter"]
    root["sizes"] = root["sizes"][:-1]

    assert manager.restore_state(json.dumps(state)) is False
    qapp.processEvents()
    assert _snapshot(manager) == before, \
        "a rejected layout still tore down the live one"


def test_legacy_system_type_is_still_accepted(manager, qapp):
    manager.add_dock_widget(DockWidgetArea.left, _mk("Alpha"))
    qapp.processEvents()

    state = json.loads(manager.save_state())
    assert state["type"] == "LaceDockingSystem"
    assert state["schema"] == 1

    # A layout written before the identifier was corrected.
    state["type"] = "QtAdvancedDockingSystem"
    del state["schema"]
    assert manager.restore_state(json.dumps(state)) is True


def test_future_schema_is_rejected(manager, qapp):
    manager.add_dock_widget(DockWidgetArea.left, _mk("Alpha"))
    qapp.processEvents()

    state = json.loads(manager.save_state())
    state["schema"] = 999
    assert manager.restore_state(json.dumps(state)) is False


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
