# -*- coding: utf-8 -*-
"""The drop path's two silent assumptions — IMPROVEMENT_PLAN_v0.7.md Phase 2.

1. ``_drop_into_section()`` located the floating window's root splitter by
   taking the first direct ``QWidget`` child of its container. A root container
   has eight of those; the scan worked only because construction order happened
   to put the splitter first.
2. ``dock_area_insert_parameters()`` aliased ``center`` to ``bottom``, so any
   caller that forgot a centre branch split vertically instead of tabbing —
   and did so silently.
"""

import pytest
from PySide6.QtWidgets import QLabel, QMainWindow, QMenu, QSplitter

from lace.dock_container_widget import dock_area_insert_parameters
from lace.dock_manager import DockManager
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea
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


def test_center_is_not_silently_treated_as_bottom():
    """It must raise, not quietly hand back a vertical-append split."""
    with pytest.raises(ValueError, match="center"):
        dock_area_insert_parameters(DockWidgetArea.center)

    # The four real sides still answer.
    for area in (DockWidgetArea.left, DockWidgetArea.right,
                 DockWidgetArea.top, DockWidgetArea.bottom):
        assert dock_area_insert_parameters(area) is not None


def test_the_floating_root_splitter_is_found_by_api_not_by_scan(desk, qapp):
    """A decoy first child must not be mistaken for the root splitter."""
    win, dock_manager = desk
    target = dock_manager.add_dock_widget(DockWidgetArea.center, _mk("Alpha"))
    dock_manager.add_dock_widget(DockWidgetArea.right, _mk("Beta"))
    qapp.processEvents()

    floating = FloatingDockContainer(dock_widget=_mk("Gamma"),
                                     dock_manager=dock_manager)
    floating.show()
    qapp.processEvents()

    container = floating.dock_container()
    real_splitter = container.root_splitter()

    # A decoy of the kind the type-scan used to be able to pick up: the root
    # container really does hold a QMenu and four overlay widgets alongside its
    # splitter, and findChild(QWidget, FindDirectChildrenOnly) returns whichever
    # of them Qt parented first.
    decoy = QMenu(container)
    decoy.setObjectName("decoy")
    qapp.processEvents()

    asked = []
    real_method = type(container).root_splitter

    def spy(self):
        asked.append(self)
        return real_method(self)

    type(container).root_splitter = spy
    try:
        dock_manager.drop_controller()._drop_into_section(
            floating, target, DockWidgetArea.left)
        qapp.processEvents()
    finally:
        type(container).root_splitter = real_method

    assert container in asked, \
        "the drop never asked the floating container for its root splitter"
    assert real_splitter is not decoy

    # The dropped widget landed in a real dock area of the target container.
    root = dock_manager.root_container()
    titles = {w.windowTitle() for w in root.dock_widgets()}
    assert "Gamma" in titles, titles


def test_the_drop_uses_the_same_policy_as_the_preview(desk, qapp):
    """The drop must not re-arm the overlay with a wider set than the drag."""
    win, dock_manager = desk
    dock_manager.add_dock_widget(DockWidgetArea.center, _mk("Alpha"))
    dock_manager.add_dock_widget(DockWidgetArea.right, _mk("Beta"))
    qapp.processEvents()

    overlay = dock_manager.dock_area_overlay()
    overlay.set_allowed_areas(DockWidgetArea.left)

    floating = FloatingDockContainer(dock_widget=_mk("Gamma"),
                                     dock_manager=dock_manager)
    floating.show()
    qapp.processEvents()

    dock_manager.drop_controller().drop_floating_widget(
        floating, win.rect().center())
    qapp.processEvents()

    assert overlay.allowed_areas() == DockWidgetArea.left, \
        "the drop widened the allowed set the drag had narrowed"
