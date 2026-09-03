# -*- coding: utf-8 -*-
"""One spelling of "insert a dock area" — IMPROVEMENT_PLAN_v0.7.md Phase 1.

There used to be two insertion paths with different post-conditions. The drop
path split the target evenly, wired the ``destroyed`` guard and recorded the
new area in the last-added cache; the programmatic path
(``_dock_widget_into_dock_area``) did none of those three. Both now go through
``_finish_area_insertion()`` and ``split_share()``, and these tests pin that.
"""

import pytest
from PySide6.QtWidgets import QLabel, QMainWindow

from lace.dock_manager import DockManager
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea
from lace.util import split_share


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


def _connected(dock_area, container):
    """True if *dock_area* wired its destroyed guard back to *container*."""
    try:
        dock_area.destroyed.disconnect(container.remove_dock_area)
    except (RuntimeError, TypeError):
        return False
    dock_area.destroyed.connect(container.remove_dock_area)
    return True


def test_split_share_subtracts_the_handle_gutters():
    assert split_share(900, 6, 2) == 447
    assert split_share(900, 0, 3) == 300
    assert split_share(100, 6, 1) == 100


def test_a_targeted_split_divides_the_target_evenly(desk, qapp):
    """A left-split of an area gives both panes half of it, not 1/5th."""
    win, dock_manager = desk
    first = dock_manager.add_dock_widget(DockWidgetArea.center, _mk("Alpha"))
    qapp.processEvents()

    target_width = first.width()
    assert target_width > 100, "fixture did not lay out"

    dock_manager.add_dock_widget(
        DockWidgetArea.left, _mk("Beta"), first)
    qapp.processEvents()

    # A center-then-left insert nests a horizontal splitter inside the
    # vertical root, so ask for the splitter that actually holds the target.
    from PySide6.QtWidgets import QSplitter
    from lace.util import find_parent

    splitter = find_parent(QSplitter, first)
    sizes = splitter.sizes()
    assert len(sizes) == 2, sizes
    expected = split_share(target_width, splitter.handleWidth(), 2)
    assert abs(sizes[0] - expected) <= 2, sizes
    assert abs(sizes[1] - expected) <= 2, sizes


def test_a_targeted_split_records_the_last_added_area(desk, qapp):
    win, dock_manager = desk
    first = dock_manager.add_dock_widget(DockWidgetArea.center, _mk("Alpha"))
    qapp.processEvents()

    new_area = dock_manager.add_dock_widget(
        DockWidgetArea.left, _mk("Beta"), first)
    qapp.processEvents()

    assert dock_manager.last_added_dock_area_widget(DockWidgetArea.left) is new_area


def test_every_insertion_path_wires_the_destroyed_guard(desk, qapp):
    """Both the container path and the targeted-split path connect it."""
    win, dock_manager = desk
    container = dock_manager.root_container()

    from_container = dock_manager.add_dock_widget(
        DockWidgetArea.center, _mk("Alpha"))
    qapp.processEvents()
    assert _connected(from_container, container)

    from_split = dock_manager.add_dock_widget(
        DockWidgetArea.left, _mk("Beta"), from_container)
    qapp.processEvents()
    assert _connected(from_split, container)


def test_restored_areas_carry_the_destroyed_guard(desk, qapp):
    win, dock_manager = desk
    container = dock_manager.root_container()
    dock_manager.add_dock_widget(DockWidgetArea.center, _mk("Alpha"))
    dock_manager.add_dock_widget(DockWidgetArea.left, _mk("Beta"))
    qapp.processEvents()

    state = dock_manager.save_state()
    assert dock_manager.restore_state(state)
    qapp.processEvents()

    areas = list(container._dock_areas)
    assert areas, "restore produced no dock areas"
    for area in areas:
        assert _connected(area, container), f"{area} restored without the guard"
