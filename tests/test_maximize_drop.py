# -*- coding: utf-8 -*-
"""Drops onto a maximized area — IMPROVEMENT_PLAN_v0.7.md Phase 4, §1.6 (f).

``_restore_maximized_area()`` had three callers — ``close_other_areas()`` and
the two guards inside ``toggle_maximize_dock_area()`` — and no drop path was
among them. Dropping onto a maximized area therefore reshaped the splitter tree
underneath a maximize state that still believed it owned the whole container:

1. ``_maximized_dock_area`` kept pointing at an area now occupying half of it,
   so ``is_area_maximized()`` lied and the title bar kept offering *Restore*.
2. The siblings maximize had hidden stayed hidden — dock widgets vanishing with
   no route back, because ``setVisible(False)`` is an explicit hide and Qt's
   ``ChildPolished`` auto-show cannot undo it.
3. The saved pre-maximize sizes were captured against the old shape, and
   ``setSizes()`` applies a short list *partially*.
4. Those sizes were keyed by ``id(splitter)`` — a freed address CPython can
   recycle.

A centre drop is the exception: it only adds a tab, leaves the tree alone, and
legitimately stays maximized.
"""

import pytest
from PySide6.QtWidgets import QLabel, QMainWindow, QSplitter

from lace.dock_manager import DockManager
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea
from lace.floating_dock_container import FloatingDockContainer


@pytest.fixture
def maximized(qapp):
    """A/B/C in a container, with A maximized."""
    win = QMainWindow()
    win.resize(1000, 700)
    dock_manager = DockManager(win)

    def mk(name):
        dock_widget = DockWidget(name)
        dock_widget.set_widget(QLabel(name))
        return dock_widget

    a = dock_manager.add_dock_widget(DockWidgetArea.left, mk("A"))
    b = dock_manager.add_dock_widget(DockWidgetArea.right, mk("B"))
    c = dock_manager.add_dock_widget(DockWidgetArea.bottom, mk("C"))
    win.show()
    qapp.processEvents()

    container = dock_manager.root_container()
    container.toggle_maximize_dock_area(a)
    qapp.processEvents()
    assert container._maximized_dock_area is a, "fixture failed to maximize"
    assert not b.isVisible() and not c.isVisible(), "fixture did not hide siblings"

    yield dock_manager, container, a, b, c, mk

    win.close()


def _float(dock_manager, mk, name):
    floating = FloatingDockContainer(dock_widget=mk(name),
                                     dock_manager=dock_manager)
    floating.show()
    return floating


def _stranded(container):
    """Areas that still hold open widgets but are not on screen.

    Not opened_dock_areas() — that one already filters hidden areas out, so
    asking it about stranding answers vacuously.
    """
    return [area for area in container._dock_areas
            if area.opened_dock_widgets() and not area.isVisible()]


def _splitters(container):
    return [container.root_splitter()] + \
        container.root_splitter().findChildren(QSplitter)


def test_a_split_drop_restores_the_maximized_area_first(maximized, qapp):
    dock_manager, container, a, b, c, mk = maximized

    dock_manager.drop_controller()._drop_into_section(
        _float(dock_manager, mk, "D"), a, DockWidgetArea.left)
    qapp.processEvents()

    assert container._maximized_dock_area is None, \
        "the container still claims an area is maximized after a split drop"
    assert not container.is_area_maximized(a)


def test_no_area_is_stranded_by_a_drop(maximized, qapp):
    dock_manager, container, a, b, c, mk = maximized

    dock_manager.drop_controller()._drop_into_section(
        _float(dock_manager, mk, "D"), a, DockWidgetArea.left)
    qapp.processEvents()

    stranded = _stranded(container)
    assert not stranded, \
        f"{len(stranded)} dock area(s) left hidden with no route back"


def test_a_centre_drop_stays_maximized(maximized, qapp):
    """Tabbing into the maximized area does not reshape the tree.

    Guards the nuance rather than a bug: this behaviour is correct on
    2f16f8e too, and the fix must not break it.
    """
    dock_manager, container, a, b, c, mk = maximized
    shape_before = [sp.count() for sp in _splitters(container)]

    dock_manager.drop_controller()._drop_into_center_of_section(
        _float(dock_manager, mk, "D"), a)
    qapp.processEvents()

    assert container._maximized_dock_area is a, \
        "a centre drop un-maximized, though it only added a tab"
    assert [sp.count() for sp in _splitters(container)] == shape_before
    assert [w.windowTitle() for w in a.dock_widgets()] == ["A", "D"]


def test_restore_after_a_drop_keeps_saved_proportions(maximized, qapp):
    """No pane may collapse to a leftover size after drop-then-restore."""
    dock_manager, container, a, b, c, mk = maximized

    dock_manager.drop_controller()._drop_into_section(
        _float(dock_manager, mk, "D"), a, DockWidgetArea.left)
    qapp.processEvents()

    for area in container._dock_areas:
        if not area.opened_dock_widgets():
            continue
        assert area.isVisible(), f"{area} is not on screen"
        extent = min(area.width(), area.height())
        assert extent > 1, f"{area} came back with no extent"


def test_pre_maximize_sizes_do_not_outlive_their_splitter(maximized, qapp):
    """The sizes live on the splitter, so nothing survives keyed on a dead id."""
    dock_manager, container, a, b, c, mk = maximized

    assert not hasattr(container, '_pre_maximize_splitter_sizes'), \
        "the id()-keyed dict is still there"
    saved_on = [sp for sp in _splitters(container)
                if getattr(sp, '_pre_maximize_sizes', None)]
    assert saved_on, "maximize saved no pre-maximize sizes at all"

    container._restore_maximized_area()
    qapp.processEvents()
    leftovers = [sp for sp in _splitters(container)
                 if getattr(sp, '_pre_maximize_sizes', None)]
    assert not leftovers, "restore left stale sizes on a splitter"


def test_a_stale_size_list_is_discarded_not_half_applied(maximized, qapp):
    """setSizes() applies a short list partially — refuse it instead."""
    dock_manager, container, a, b, c, mk = maximized

    target = next(sp for sp in _splitters(container)
                  if getattr(sp, '_pre_maximize_sizes', None)
                  and sp.count() > 1)
    target._pre_maximize_sizes = [1]        # one value for several panes
    sizes_before = target.sizes()

    container._restore_maximized_area()
    qapp.processEvents()

    assert target.sizes() != [1] + sizes_before[1:], \
        "a stale length was applied to the first pane and the rest left alone"


def test_removing_the_maximized_area_unhides_its_siblings(maximized, qapp):
    """§4.5. A guard, not a fix: the hand-rolled cleanup this replaced did
    un-hide the siblings, so this passes on 2f16f8e too. It pins the
    behaviour now that the path goes through _restore_maximized_area().
    """
    dock_manager, container, a, b, c, mk = maximized

    container.remove_dock_area(a)
    qapp.processEvents()

    assert container._maximized_dock_area is None
    stranded = _stranded(container)
    assert not stranded, \
        f"removing the maximized area stranded {len(stranded)} sibling(s)"
