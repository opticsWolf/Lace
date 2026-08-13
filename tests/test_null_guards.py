# -*- coding: utf-8 -*-
"""The four null-safety spots from §5.6.

Each is a dereference of something a teardown or an in-between state sets to
None, or a positional assumption about a layout. None of them is exotic:
closing a floating window, moving a widget between containers, maximizing a
nested area, and clearing a tab's icon.
"""

import pytest
from PySide6.QtWidgets import QLabel, QMainWindow, QSplitter, QWidget
from PySide6.QtGui import QIcon, QPixmap

from lace.dock_manager import DockManager
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea
from lace.util import emit_top_level_event_for_widget


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


# ── util.emit_top_level_event_for_widget ──────────────────────────────────
def test_the_signal_goes_out_for_an_arealess_widget(desk, qapp):
    """A widget between containers has no area yet; the signal still matters."""
    win, dock_manager = desk
    dock_widget = _mk("Alpha")
    assert dock_widget.dock_area_widget() is None

    seen = []
    dock_widget.top_level_changed.connect(seen.append)
    emit_top_level_event_for_widget(dock_widget, True)  # must not raise

    assert seen == [True], "the guard swallowed the signal it was guarding"


def test_an_attached_widget_still_gets_its_title_bar_shown(desk, qapp):
    win, dock_manager = desk
    dock_widget = _mk("Alpha")
    area = dock_manager.add_dock_widget(DockWidgetArea.center, dock_widget)
    qapp.processEvents()
    area._title_bar.setVisible(False)

    emit_top_level_event_for_widget(dock_widget, True)

    assert area._title_bar.isVisible()


# ── FloatingDockContainer's delegators ────────────────────────────────────
def test_a_torn_down_floating_window_is_closable(desk, qapp):
    """_destroyed() clears _dock_container, and closeEvent() asks is_closable().

    The dereference raised from inside a close, which is the one place that
    cannot recover: the window neither closed nor reported why.
    """
    win, dock_manager = desk
    dock_manager.add_dock_widget(DockWidgetArea.center, _mk("Alpha"))
    floating = dock_manager.floating_container_class()(dock_manager=dock_manager)
    qapp.processEvents()

    floating._dock_container = None

    assert floating.is_closable() is True
    assert floating.has_top_level_dock_widget() is False
    assert floating.top_level_dock_widget() is None
    assert floating.dock_widgets() == []
    floating.close()  # must not raise


# ── _maximize_splitter ────────────────────────────────────────────────────
def test_maximize_zeroes_a_losing_splitter_pane_for_pane(desk, qapp, monkeypatch):
    """setSizes([0]) only reached the first pane — Qt ignores the shortfall.

    A sibling splitter holding two areas kept the second one at its old size,
    so "maximize" left a stripe of the layout it was meant to take over. The
    call is what this pins: Qt clamps the resulting sizes to each pane's
    minimum, so reading sizes() back cannot tell the two versions apart.
    """
    win, dock_manager = desk
    # Two nested splitters side by side: the target lives in one, and the
    # other holds two panes — which is where the shortfall showed.
    target = dock_manager.add_dock_widget(DockWidgetArea.center, _mk("Alpha"))
    right = dock_manager.add_dock_widget(DockWidgetArea.right, _mk("Beta"))
    dock_manager.add_dock_widget(DockWidgetArea.bottom, _mk("Gamma"), target)
    dock_manager.add_dock_widget(DockWidgetArea.bottom, _mk("Delta"), right)
    qapp.processEvents()

    calls = []
    original = QSplitter.setSizes
    monkeypatch.setattr(
        QSplitter, "setSizes",
        lambda self, sizes: (calls.append((self, list(sizes))),
                             original(self, sizes))[1])

    root = dock_manager.root_container()
    root._maximize_splitter(root._root_splitter, target)

    collapses = [(splitter, sizes) for splitter, sizes in calls if set(sizes) == {0}]
    assert collapses, "nothing was collapsed — the setup does not reproduce"
    for splitter, sizes in collapses:
        assert len(sizes) == splitter.count(), \
            f"collapsed {len(sizes)} of {splitter.count()} panes"
    assert any(splitter.count() > 1 for splitter, _ in collapses), \
        "no multi-pane splitter was collapsed, so the shortfall never showed"


# ── DockWidgetTab._set_icon_internal ──────────────────────────────────────
def _icon():
    pixmap = QPixmap(16, 16)
    pixmap.fill()
    return QIcon(pixmap)


def test_clearing_an_icon_removes_its_own_spacer(desk, qapp):
    """It removed layout.itemAt(0) — whatever happened to be first."""
    win, dock_manager = desk
    dock_widget = _mk("Alpha")
    dock_manager.add_dock_widget(DockWidgetArea.center, dock_widget)
    qapp.processEvents()

    tab = dock_widget.tab_widget()
    # The icon provider may already have given this tab one, depending on the
    # flags a previous test left behind — start from a known-bare layout.
    tab._set_icon_internal(QIcon())
    before = tab.layout().count()

    tab._set_icon_internal(_icon())
    assert tab._icon_label is not None
    assert tab._icon_spacer is not None
    assert tab.layout().count() == before + 2

    tab._set_icon_internal(QIcon())
    assert tab._icon_label is None
    assert tab._icon_spacer is None
    assert tab.layout().count() == before, "the layout did not return to its shape"


def test_the_title_survives_an_icon_round_trip(desk, qapp):
    """The positional removal could take the title label's neighbour instead."""
    win, dock_manager = desk
    dock_widget = _mk("Alpha")
    dock_manager.add_dock_widget(DockWidgetArea.center, dock_widget)
    qapp.processEvents()

    tab = dock_widget.tab_widget()
    for _ in range(3):
        tab._set_icon_internal(_icon())
        tab._set_icon_internal(QIcon())

    assert tab._title_label.text() == "Alpha"
    assert tab._title_label.parent() is tab
