# -*- coding: utf-8 -*-
"""Splitter junction detection and its handle cache — docs/CODE_REVIEW.md §4.3.

Junction detection answers "which perpendicular handles cross the cursor?", and
it runs on every hover-move over any handle. It used to call findChildren() —
a full recursive tree walk — each time. The list is now cached on the container
and invalidated wherever the area layout changes, so these tests pin both
halves: the cache is used, and it does not go stale.
"""

import pytest

from lace.dock_splitter import DockSplitterHandle
from lace.enums import DockWidgetArea


@pytest.fixture
def grid(make_desk):
    """A 2x2-ish layout, so several splitters (and handles) exist."""
    desk = make_desk(900, 700)
    desk.add(DockWidgetArea.left, "Alpha")
    desk.add(DockWidgetArea.right, "Beta")
    desk.add(DockWidgetArea.bottom, "Gamma")
    desk.show()
    return desk.manager, desk.win, desk.widget


def _container(dock_manager):
    return dock_manager.root_container()


def _handles(dock_manager):
    return _container(dock_manager).findChildren(DockSplitterHandle)


def test_junction_lookup_uses_the_cache(grid, qapp, monkeypatch):
    dock_manager, _, _ = grid
    container = _container(dock_manager)
    handle = _handles(dock_manager)[0]

    handle._all_handles()          # prime it
    walks = []
    original = type(container).findChildren
    monkeypatch.setattr(
        type(container), "findChildren",
        lambda self, *a, **k: (walks.append(a), original(self, *a, **k))[1])

    for _ in range(5):
        handle._find_intersecting_handles(handle.mapToGlobal(handle.rect().center()))

    assert not walks, "junction detection still walks the widget tree per call"


def test_adding_an_area_invalidates_the_cache(grid, qapp):
    dock_manager, _, mk = grid
    container = _container(dock_manager)
    handle = _handles(dock_manager)[0]

    before = list(handle._all_handles())
    assert container._handle_cache is not None, "nothing was cached"

    dock_manager.add_dock_widget(DockWidgetArea.top, mk("Delta"))
    qapp.processEvents()

    assert container._handle_cache is None, "adding an area left the cache primed"
    after = handle._all_handles()
    assert len(after) > len(before), \
        "the new splitter's handle never reached the rebuilt cache"


def test_removing_a_widget_invalidates_the_cache(grid, qapp):
    dock_manager, _, mk = grid
    container = _container(dock_manager)
    extra = mk("Delta")
    area = dock_manager.add_dock_widget(DockWidgetArea.top, extra)
    qapp.processEvents()

    handle = _handles(dock_manager)[0]
    handle._all_handles()
    assert container._handle_cache is not None

    dock_manager.remove_dock_widget(extra)
    qapp.processEvents()
    assert container._handle_cache is None, "removing an area left the cache primed"


def test_stale_handles_do_not_raise(grid, qapp):
    """A cached handle whose C++ object is gone must be skipped, not raised on."""
    dock_manager, _, _ = grid
    container = _container(dock_manager)
    handle = _handles(dock_manager)[0]

    class Dead:
        def isVisible(self):
            raise RuntimeError("Internal C++ object already deleted.")

    container._handle_cache = [Dead()] + list(handle._all_handles())
    handle._find_intersecting_handles(handle.mapToGlobal(handle.rect().center()))


def test_restoring_a_layout_invalidates_the_cache(grid, qapp):
    """The third layout-change choke point — Plan v0.7 §1.3.

    ``restore_container_state()`` rebuilds the whole splitter tree, but used to
    reset only the area list and the visible count. The handle cache survived,
    so junction detection kept hit-testing handles from the discarded tree.
    """
    dock_manager, _, _ = grid
    container = _container(dock_manager)

    handle = _handles(dock_manager)[0]
    handle._all_handles()
    assert container._handle_cache is not None, "cache was never primed"

    state = dock_manager.save_state()
    assert dock_manager.restore_state(state)
    qapp.processEvents()

    assert container._handle_cache is None, \
        "a layout restore left the cache holding handles from the old tree"
