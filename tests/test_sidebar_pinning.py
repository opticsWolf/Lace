# -*- coding: utf-8 -*-
"""Pinning docks to sidebars: removal, restores, features, allowed sides.

Each desk has a center dock and docks A (left) and B (right), with left and
right sidebars. Animations are off so the overlay opens and closes at once.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QEvent

from lace.enums import DockWidgetArea, DockWidgetFeature, WidgetState

LEFT, RIGHT, BOTTOM = DockWidgetArea.left, DockWidgetArea.right, DockWidgetArea.bottom


class Pins:
    """A desk with docks to pin, and the counts the tests check."""

    def __init__(self, qapp, make_desk, sides=(LEFT, RIGHT)):
        self.qapp = qapp
        self.desk = make_desk(1000, 700)
        self.manager = self.desk.manager
        self.sm = self.manager.sidebar_manager
        self.sm.set_animations_enabled(False)
        self.docks = {}
        for name, area in (("Center", DockWidgetArea.center), ("A", LEFT), ("B", RIGHT)):
            dock = self.desk.widget(name)
            dock.set_features(DockWidgetFeature.all_features)
            self.desk.add(area, dock)
            self.docks[name] = dock
        for side in sides:
            self.sm.add_sidebar(side)
        self.desk.show()

    def __getitem__(self, name):
        return self.docks[name]

    def pump(self):
        self.qapp.processEvents()
        self.qapp.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        self.qapp.processEvents()

    def buttons(self):
        return {area: len(bar._buttons) for area, bar in self.sm._sidebars.items() if bar._buttons}

    def button(self, dock):
        return self.sm._pinned[dock].button_for(dock)

    def save(self):
        self.pump()
        return self.manager.save_state()

    def restore(self, saved):
        assert self.manager.restore_state(saved)
        self.pump()


@pytest.fixture
def pins(qapp, make_desk):
    return Pins(qapp, make_desk)


# ── §1 a removed or deleted pinned dock leaves nothing behind ───────────────

def test_removing_a_pinned_dock_drops_its_tab(pins):
    a = pins["A"]
    pins.sm.pin_widget(a, area=LEFT)
    pins.manager.remove_dock_widget(a)
    a.deleteLater()
    pins.pump()
    assert not pins.sm._pinned
    assert pins.buttons() == {}
    assert not pins.sm._destroyed_hooks


def test_deleting_a_pinned_dock_directly_cleans_up(pins):
    a = pins["A"]
    pins.sm.pin_widget(a, area=LEFT)
    a.deleteLater()
    pins.pump()
    assert not pins.sm._pinned
    assert pins.buttons() == {}


def test_a_tab_whose_dock_was_deleted_reads_none(pins):
    from lace.sidebar_tab import VerticalTabButton

    a = pins["A"]
    button = VerticalTabButton("A")
    button.set_dock_widget(a)
    assert button.dock_widget() is a
    pins.manager.remove_dock_widget(a)
    a.deleteLater()
    pins.pump()
    assert button.dock_widget() is None


_RESTORE_AFTER_REMOVE = """
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow
from lace import DockManager, DockWidget, DockWidgetArea

app = QApplication([])
win = QMainWindow()
manager = DockManager(win)
docks = {}
for name, area in (("Center", DockWidgetArea.center), ("A", DockWidgetArea.left),
                   ("B", DockWidgetArea.right)):
    docks[name] = DockWidget(name)
    docks[name].set_widget(QLabel(name))
    manager.add_dock_widget(area, docks[name])
sm = manager.sidebar_manager
sm.add_sidebar(DockWidgetArea.left)
sm.add_sidebar(DockWidgetArea.right)
win.show()
app.processEvents()
docked = manager.save_state()
sm.pin_widget(docks["A"], area=DockWidgetArea.left)
app.processEvents()
manager.remove_dock_widget(docks["A"])
docks["A"].deleteLater()
app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
app.processEvents()
manager.restore_state(docked)
app.processEvents()
for bar in sm._sidebars.values():
    for button in list(bar._buttons):
        bar.tab_hover_enter.emit(button)
        bar.tab_hover_leave.emit(button)
app.processEvents()
print("ok")
"""


def test_restore_after_removing_a_pinned_dock_does_not_crash():
    # In a child process: the crash this guards against is an access violation.
    # It depended on freed memory, so it didn't happen on every run; the tests
    # above, that nothing is left behind, are the deterministic guard.
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    out = subprocess.run([sys.executable, "-c", _RESTORE_AFTER_REMOVE], capture_output=True,
                         text=True, cwd=str(Path(__file__).resolve().parents[1]), env=env,
                         timeout=120)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip().endswith("ok")


# ── §3 pinning is idempotent ────────────────────────────────────────────────

def test_pin_widget_twice_keeps_one_tab(pins):
    a = pins["A"]
    assert pins.sm.pin_widget(a, area=LEFT)
    assert pins.sm.pin_widget(a, area=LEFT)
    assert pins.sm.pin_widget(a)
    assert pins.buttons() == {LEFT: 1}


def test_pin_widget_to_the_other_side_moves_the_tab(pins):
    a = pins["A"]
    pins.sm.pin_widget(a, area=LEFT)
    pins.sm.pin_widget(a, area=RIGHT)
    pins.pump()
    assert pins.buttons() == {RIGHT: 1}
    assert pins.sm._pinned[a].area is RIGHT
    assert len(pins.sm._sidebars[LEFT]._widget_map) == 0


def test_add_tab_returns_the_existing_tab(pins):
    bar = pins.sm._sidebars[LEFT]
    assert bar.add_tab(pins["A"]) is bar.add_tab(pins["A"])
    assert len(bar._buttons) == 1


# ── §2 / §4 the saved sidebar state is authoritative on restore ─────────────

def test_restoring_a_docked_layout_unpins(pins):
    a = pins["A"]
    docked = pins.save()
    pins.sm.pin_widget(a, area=LEFT)
    pins.restore(docked)
    assert not pins.sm.is_pinned(a)
    assert a.dock_area_widget() is not None
    assert a.widget_state() is WidgetState.docked
    assert not a.is_closed()
    assert pins.buttons() == {}


def test_restoring_a_layout_moves_a_pin_to_the_saved_side(pins):
    a = pins["A"]
    pins.sm.pin_widget(a, area=LEFT)
    pinned_left = pins.save()
    pins.sm.pin_widget(a, area=RIGHT)
    pins.restore(pinned_left)
    assert pins.buttons() == {LEFT: 1}
    assert pins.sm._pinned[a].area is LEFT


def test_restoring_the_same_pinned_layout_twice_keeps_one_tab(pins):
    a = pins["A"]
    pins.sm.pin_widget(a, area=LEFT)
    pinned = pins.save()
    pins.restore(pinned)
    pins.restore(pinned)
    assert pins.buttons() == {LEFT: 1}
    assert len(pins.sm._sidebars[LEFT]._widget_map) == 1


def test_a_pinned_dock_state_matches_the_overlay_after_restore(pins):
    a = pins["A"]
    pins.sm.pin_widget(a, area=LEFT)
    pinned = pins.save()
    pins.restore(pinned)
    shown = pins.sm.overlay.isVisible() and a in pins.sm.overlay._current_widgets
    assert (a.widget_state() is WidgetState.pinned_shown) is shown


# ── §5 a pinned dock's closed flag ──────────────────────────────────────────

def test_a_closed_pinned_dock_stays_closed_after_restore(pins):
    a = pins["A"]
    pins.sm.pin_widget(a, area=LEFT)
    a.toggle_view(False)
    closed = pins.save()
    assert json.loads(closed)["widget_states"]["A"]["closed"] is True
    a.toggle_view(True)
    pins.sm.close_overlay()
    pins.pump()
    pins.restore(closed)
    assert a.is_closed()
    assert pins.button(a).isHidden()
    assert a.widget_state() is WidgetState.pinned_hidden


def test_an_open_pinned_dock_stays_open_after_restore(pins):
    a = pins["A"]
    pins.sm.pin_widget(a, area=LEFT)
    opened = pins.save()
    a.toggle_view(False)
    pins.pump()
    pins.restore(opened)
    assert not a.is_closed()
    assert not pins.button(a).isHidden()
    assert not pins.sm.overlay.isVisible()       # its tab shows; the overlay stays shut


def test_pinning_a_closed_dock_keeps_its_tab_hidden(pins):
    a = pins["A"]
    a.toggle_view(False)
    pins.sm.pin_widget(a, area=LEFT)
    pins.pump()
    assert pins.button(a).isHidden()
    assert not pins.sm._sidebars[LEFT].isVisible()


# ── §6 pinnable: only pinnable docks are pinned; the rest stay put ──────────
# A pinned dock without pinnable is locked in its sidebar. Only the host puts
# one there: add_sidebar_widget(), or dropping the feature from a pinned dock.

UNPINNABLE = DockWidgetFeature.movable | DockWidgetFeature.floatable


def test_pin_widget_refuses_a_non_pinnable_dock(pins):
    b = pins["B"]
    b.set_features(UNPINNABLE)
    assert not pins.sm.pin_widget(b, area=RIGHT)
    pins.sm.pin_to_closest_sidebar(b)
    assert not pins.sm.is_pinned(b)
    assert b.dock_area_widget() is not None


def test_dropping_pinnable_locks_a_pinned_dock_in_its_sidebar(pins):
    b = pins["B"]
    pins.sm.pin_widget(b, area=RIGHT)
    b.set_features(UNPINNABLE)
    pins.sm.unpin_widget(b)
    assert pins.sm.is_pinned(b)
    b.set_features(DockWidgetFeature.all_features)
    pins.sm.unpin_widget(b)
    pins.pump()
    assert not pins.sm.is_pinned(b)
    assert b.dock_area_widget() is not None


def test_the_host_can_pin_a_non_pinnable_dock(pins):
    locked = pins.desk.widget("Locked")
    locked.set_features(UNPINNABLE)
    pins.manager.add_sidebar_widget(LEFT, locked)
    assert pins.sm.is_pinned(locked)


def test_restore_puts_a_locked_dock_back_in_its_sidebar(pins):
    b = pins["B"]
    pins.sm.pin_widget(b, area=RIGHT)
    b.set_features(UNPINNABLE)
    pinned = pins.save()
    pins.restore(pinned)
    assert pins.sm._pinned[b].area is RIGHT
    assert pins.buttons() == {RIGHT: 1}


# ── §7 / §8 allowed sides and the DockManager facade ────────────────────────

@pytest.fixture
def bottom_dock(pins):
    dock = pins.desk.widget("Bottom")
    dock.set_features(DockWidgetFeature.all_features)
    pins.desk.add(BOTTOM, dock)
    pins.pump()
    return dock


def test_default_allows_all_sides(pins, bottom_dock):
    assert pins.manager.sidebar_areas() == {LEFT, RIGHT, DockWidgetArea.top, BOTTOM}
    pins.sm.pin_widget(bottom_dock)
    assert pins.sm._pinned[bottom_dock].area is BOTTOM


def test_auto_pin_uses_only_allowed_sides(pins, bottom_dock):
    pins.manager.set_sidebar_areas({LEFT, RIGHT})
    assert pins.manager.pin_dock_widget(bottom_dock)
    assert pins.sm._pinned[bottom_dock].area in (LEFT, RIGHT)
    assert BOTTOM not in pins.sm._sidebars
    pins.sm.unpin_widget(bottom_dock)
    pins.sm.pin_to_closest_sidebar(bottom_dock)
    assert pins.sm._pinned[bottom_dock].area in (LEFT, RIGHT)


def test_an_explicit_disallowed_side_falls_back(pins):
    pins.manager.set_sidebar_areas({RIGHT})
    assert pins.manager.pin_dock_widget(pins["A"], LEFT)
    assert pins.sm._pinned[pins["A"]].area is RIGHT


def test_disallowing_a_side_moves_its_pins(pins):
    pins.sm.pin_widget(pins["A"], area=LEFT)
    pins.manager.set_sidebar_areas({RIGHT})
    assert pins.sm._pinned[pins["A"]].area is RIGHT
    assert pins.buttons() == {RIGHT: 1}


def test_restore_maps_a_disallowed_pin(pins):
    a = pins["A"]
    pins.sm.pin_widget(a, area=LEFT)
    saved = json.loads(pins.save())
    saved["sidebars"]["pinned_widgets"] = {"A": "bottom"}
    saved["sidebars"]["sidebar_areas"].append("bottom")
    pins.manager.set_sidebar_areas({LEFT, RIGHT})
    pins.restore(json.dumps(saved))
    assert pins.sm._pinned[a].area in (LEFT, RIGHT)
    assert BOTTOM not in pins.sm._sidebars


def test_set_sidebar_areas_turns_pinning_on(qapp, make_desk):
    desk = make_desk()
    desk.add(LEFT, "A")
    desk.show()
    manager = desk.manager
    assert not manager.sidebar_manager.has_sidebars
    manager.set_sidebar_areas([LEFT, RIGHT])
    assert manager.sidebar_manager.has_sidebars
    assert set(manager.sidebar_manager._sidebars) == {LEFT, RIGHT}


def test_set_sidebar_areas_needs_a_side(pins):
    with pytest.raises(ValueError):
        pins.manager.set_sidebar_areas([DockWidgetArea.center])


def test_facade(pins):
    a = pins["A"]
    m = pins.manager
    assert m.pin_dock_widget(a, LEFT)
    assert m.is_dock_widget_pinned(a)
    assert m.pinned_dock_widgets() == {a: LEFT}
    m.unpin_dock_widget(a)
    pins.pump()
    assert not m.is_dock_widget_pinned(a)
    assert m.pinned_dock_widgets() == {}


# ── §9 dock_pinned_changed ──────────────────────────────────────────────────

@pytest.fixture
def changes(pins):
    seen = []
    pins.manager.signals.dock_pinned_changed.connect(
        lambda dock, area: seen.append((dock.objectName(), area)))
    return seen


def test_pin_move_and_unpin_are_reported(pins, changes):
    a = pins["A"]
    pins.sm.pin_widget(a, area=LEFT)
    pins.sm.pin_widget(a, area=LEFT)              # no change, no signal
    pins.sm.pin_widget(a, area=RIGHT)
    pins.sm.unpin_widget(a)
    assert changes == [("A", LEFT), ("A", RIGHT), ("A", None)]


def test_the_signal_sees_consistent_bookkeeping(pins):
    a = pins["A"]
    seen = []
    pins.manager.signals.dock_pinned_changed.connect(
        lambda dock, area: seen.append((pins.manager.is_dock_widget_pinned(dock), area)))
    pins.sm.pin_widget(a, area=LEFT)
    pins.sm.unpin_widget(a)
    assert seen == [(True, LEFT), (False, None)]


def test_removing_a_pinned_dock_is_reported(pins, changes):
    pins.sm.pin_widget(pins["A"], area=LEFT)
    pins.manager.remove_dock_widget(pins["A"])
    assert changes[-1] == ("A", None)


def test_restore_reports_each_changed_dock_once(pins, changes):
    a, b = pins["A"], pins["B"]
    pins.sm.pin_widget(a, area=LEFT)
    saved = pins.save()                            # A pinned left, B docked
    pins.sm.pin_widget(b, area=RIGHT)
    del changes[:]
    pins.restore(saved)
    assert changes == [("B", None)]                # A was pinned left before and after
    del changes[:]
    pins.restore(saved)
    assert changes == []
