# -*- coding: utf-8 -*-
"""Only one cross offers the centre at a time.

Dragging a dock onto a floating window that held a single tab drew *two*
centre indicators, side by side: the container cross was armed with all five
areas whenever the container had one visible area or fewer, and the dock area
cross was armed with ``center``.

Handing the container all five was only ever right while a lone area was
armed with ``no_area`` and so drew nothing at all.  Once a lone area got its
own centre back — that is what made a floating widget droppable into the
centre of a one-area container, 0.6.8 — the two collided.
"""

import pytest
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QLabel, QMainWindow

from lace.dock_manager import DockManager
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea
from lace.floating_dock_container import FloatingDockContainer


def _mk(name):
    dock_widget = DockWidget(name)
    dock_widget.set_widget(QLabel(name))
    return dock_widget


def _shown(overlay):
    """The drop indicators the user can actually see on *overlay*."""
    return {area for area, widget
            in overlay._cross._drop_indicator_widgets.items()
            if not widget.isHidden()}


@pytest.fixture
def float_over_float(qapp):
    """A one-area float being dragged over another one-area float."""
    win = QMainWindow()
    win.resize(900, 700)
    manager = DockManager(win)
    manager.add_dock_widget(DockWidgetArea.left, _mk("Anchor"))
    win.show()

    target_float = FloatingDockContainer(dock_widget=_mk("Unpinnable Data"),
                                         dock_manager=manager)
    target_float.show()
    dragged_float = FloatingDockContainer(dock_widget=_mk("Unclosable Logger"),
                                          dock_manager=manager)
    dragged_float.show()
    qapp.processEvents()

    target_float.move(100, 100)
    target_float.resize(400, 300)
    dragged_float.move(700, 100)
    qapp.processEvents()

    yield manager, win, target_float, dragged_float

    win.close()


def _hover_centre_of(floating):
    """Park the real cursor over *floating*'s centre and return that point.

    Both crosses hit-test ``QCursor.pos()`` rather than any position handed
    to them, so a test that only passes coordinates around resolves nothing.
    """
    pos = floating.mapToGlobal(floating.rect().center())
    QCursor.setPos(pos)
    return pos


def test_a_solo_area_float_shows_one_centre_not_two(float_over_float):
    """The bug, exactly as reported: two centre glyphs over a single tab."""
    manager, _, target_float, dragged_float = float_over_float
    dragged_float._update_drop_overlays(_hover_centre_of(target_float))

    container_shown = _shown(manager.container_overlay())
    area_shown = _shown(manager.dock_area_overlay())

    assert DockWidgetArea.center in area_shown
    assert DockWidgetArea.center not in container_shown
    assert len(container_shown & area_shown) == 0


def test_the_outer_four_still_come_from_the_container(float_over_float):
    """Splitting off a lone area is the container's job, and still offered."""
    manager, _, target_float, dragged_float = float_over_float
    dragged_float._update_drop_overlays(_hover_centre_of(target_float))

    assert _shown(manager.container_overlay()) == {
        DockWidgetArea.left, DockWidgetArea.right,
        DockWidgetArea.top, DockWidgetArea.bottom,
    }


def test_a_centre_drop_onto_the_solo_area_still_tabs(float_over_float):
    """The preview change must not cost the drop it was previewing."""
    manager, _, target_float, dragged_float = float_over_float
    target_container = target_float.dock_container()
    target_area = target_container.opened_dock_areas()[0]
    assert target_area.dock_widgets_count() == 1

    pos = _hover_centre_of(target_float)
    dragged_float._update_drop_overlays(pos)
    target_container.drop_floating_widget(
        dragged_float, target_container.mapFromGlobal(pos))

    assert target_container.dock_area_count() == 1
    titles = [w.windowTitle() for w in target_area.dock_widgets()]
    assert titles == ["Unpinnable Data", "Unclosable Logger"]
