# -*- coding: utf-8 -*-
"""ensure_title_bar_visible(), and the name it used to have — §5.3.

The method was called update_title_bar_visibility() and was an unconditional
setVisible(True): a name promising a decision that the body never made. Lace's
title bar carries the tab strip, so there is no state in which an attached
area hides it — upstream ADS can, because there the tabs are a separate
widget. Renamed rather than given the hide case it never wanted.
"""

import warnings

import pytest
from PySide6.QtWidgets import QLabel, QMainWindow

from lace.dock_manager import DockManager
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea


@pytest.fixture
def area(qapp):
    win = QMainWindow()
    win.resize(800, 600)
    dock_manager = DockManager(win)
    dock_widget = DockWidget("Alpha")
    dock_widget.set_widget(QLabel("Alpha"))
    dock_area = dock_manager.add_dock_widget(DockWidgetArea.center, dock_widget)
    win.show()
    qapp.processEvents()
    yield dock_area
    win.close()


def test_it_shows_the_title_bar(area, qapp):
    area._title_bar.setVisible(False)
    area.ensure_title_bar_visible()
    assert area._title_bar.isVisible()


def test_a_detached_area_is_left_alone(area, qapp):
    """Mid-move between containers there is no container — and no crash."""
    area.setParent(None)
    area._title_bar.setVisible(False)
    assert area.dock_container() is None

    area.ensure_title_bar_visible()  # must not raise

    assert not area._title_bar.isVisible(), \
        "an unparented area showed a title bar into nothing"


def test_the_old_name_still_works_but_warns(area, qapp):
    """Renaming public API without a bridge would break callers silently."""
    area._title_bar.setVisible(False)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        area.update_title_bar_visibility()

    assert area._title_bar.isVisible(), "the alias stopped doing the work"
    assert any(issubclass(w.category, DeprecationWarning) for w in caught), \
        "the old name was kept without saying it is deprecated"


def test_nothing_inside_lace_still_calls_the_old_name():
    """The alias is for downstreams; internal use would keep warning forever."""
    import pathlib

    root = pathlib.Path(__file__).resolve().parent.parent / "lace"
    offenders = [p.name for p in root.glob("*.py")
                 if p.name != "dock_area_widget.py"
                 and "update_title_bar_visibility" in p.read_text(encoding="utf-8")]
    assert not offenders, offenders
