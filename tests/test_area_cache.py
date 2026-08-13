# -*- coding: utf-8 -*-
"""The last-added-area cache, and what removal does to it — §5.2.

``last_added_dock_area_widget()`` is public API, delegated straight from
DockManager. The cache behind it is written on every dock into a fresh area
and was meant to be cleared when that area goes away. The clearing compared
the cached *area* against the removed area's *splitter* — never equal — so the
cache kept handing out an area whose C++ half had already been deleted.
"""

import pytest
from PySide6.QtWidgets import QLabel, QMainWindow, QWidget

from lace.dock_manager import DockManager
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea


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


def test_removing_an_area_clears_it_from_the_cache(desk, qapp):
    win, dock_manager = desk
    dock_manager.add_dock_widget(DockWidgetArea.center, _mk("Alpha"))
    left = dock_manager.add_dock_widget(DockWidgetArea.left, _mk("Beta"))
    qapp.processEvents()
    assert dock_manager.last_added_dock_area_widget(DockWidgetArea.left) is left, \
        "the cache was never populated — this test would pass vacuously"

    dock_manager._root.remove_dock_area(left)
    qapp.processEvents()

    assert dock_manager.last_added_dock_area_widget(DockWidgetArea.left) is None


def test_the_cached_area_is_never_a_dead_object(desk, qapp):
    """The real failure: not a stale name, a deleted QWidget.

    Touching one raises RuntimeError, so anything the caller does with the
    area it was handed crashes rather than merely misbehaving.
    """
    import shiboken6

    win, dock_manager = desk
    dock_manager.add_dock_widget(DockWidgetArea.center, _mk("Alpha"))
    bottom = dock_manager.add_dock_widget(DockWidgetArea.bottom, _mk("Beta"))
    qapp.processEvents()

    dock_manager._root.remove_dock_area(bottom)
    qapp.processEvents()
    shiboken6.delete(bottom)  # what deleteLater gets round to eventually

    cached = dock_manager.last_added_dock_area_widget(DockWidgetArea.bottom)
    assert cached is None or shiboken6.isValid(cached), \
        "the cache handed back a deleted C++ object"


def test_other_areas_keep_their_entries(desk, qapp):
    """Only the removed area is cleared — the cache is not simply wiped."""
    win, dock_manager = desk
    dock_manager.add_dock_widget(DockWidgetArea.center, _mk("Alpha"))
    left = dock_manager.add_dock_widget(DockWidgetArea.left, _mk("Beta"))
    right = dock_manager.add_dock_widget(DockWidgetArea.right, _mk("Gamma"))
    qapp.processEvents()

    dock_manager._root.remove_dock_area(left)
    qapp.processEvents()

    assert dock_manager.last_added_dock_area_widget(DockWidgetArea.right) is right


def test_an_area_outside_a_splitter_removes_cleanly(desk, qapp):
    """find_parent() returns None there, and splitter.count() followed.

    Reachable while a layout is being rebuilt, and from the destroyed-signal
    path where the area has already been reparented away.
    """
    win, dock_manager = desk
    dock_manager.add_dock_widget(DockWidgetArea.center, _mk("Alpha"))
    orphan = dock_manager.add_dock_widget(DockWidgetArea.left, _mk("Beta"))
    qapp.processEvents()

    holder = QWidget(win)
    orphan.setParent(holder)  # out of every DockSplitter

    dock_manager._root.remove_dock_area(orphan)  # must not raise
    assert dock_manager.last_added_dock_area_widget(DockWidgetArea.left) is None
