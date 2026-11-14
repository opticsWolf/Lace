# -*- coding: utf-8 -*-
"""Sidebar hover delays: show is delayed, clicks are not, settings round-trip."""

import pytest
from PySide6.QtCore import QEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from lace.enums import DockWidgetArea

LEFT = DockWidgetArea.left


class HoverDesk:
    def __init__(self, qapp, make_desk):
        self.qapp = qapp
        self.desk = make_desk(1000, 700)
        self.manager = self.desk.manager
        self.sm = self.manager.sidebar_manager
        self.sm.set_animations_enabled(False)
        self.sm.add_sidebar(LEFT)
        self.dock = self.desk.widget("Panel")
        self.desk.add(DockWidgetArea.center, self.dock)
        self.desk.show()
        assert self.sm.pin_widget(self.dock, area=LEFT)
        self.qapp.processEvents()
        self.button = self.sm._pinned[self.dock].button_for(self.dock)

    @property
    def overlay(self):
        return self.sm.overlay


@pytest.fixture
def hover_desk(qapp, make_desk):
    return HoverDesk(qapp, make_desk)


def test_default_delays(hover_desk):
    assert hover_desk.sm.hover_delay_ms == 150
    assert hover_desk.sm.hide_delay_ms == 400
    assert hover_desk.sm.switch_delay_ms == 150


def test_hover_waits_for_the_delay(hover_desk):
    hover_desk.sm.hover_delay_ms = 100
    hover_desk.sm._on_tab_hover_enter(hover_desk.button)
    hover_desk.qapp.processEvents()
    assert not hover_desk.overlay.isVisible()

    QTest.qWait(60)
    assert not hover_desk.overlay.isVisible()

    QTest.qWait(80)
    hover_desk.qapp.processEvents()
    assert hover_desk.overlay.isVisible()


def test_zero_hover_delay_shows_immediately(hover_desk):
    hover_desk.sm.hover_delay_ms = 0
    hover_desk.sm._on_tab_hover_enter(hover_desk.button)
    hover_desk.qapp.processEvents()
    assert hover_desk.overlay.isVisible()


def test_leaving_before_the_delay_cancels_the_show(hover_desk):
    hover_desk.sm.hover_delay_ms = 200
    hover_desk.sm._on_tab_hover_enter(hover_desk.button)
    hover_desk.sm._on_tab_hover_leave(hover_desk.button)

    QTest.qWait(260)
    hover_desk.qapp.processEvents()
    assert not hover_desk.overlay.isVisible()
    assert not hover_desk.button.isChecked()


def test_entering_the_open_overlay_stops_the_hide_timer(hover_desk):
    hover_desk.sm.hide_delay_ms = 120
    hover_desk.sm.hover_delay_ms = 0
    hover_desk.sm._on_tab_hover_enter(hover_desk.button)
    hover_desk.qapp.processEvents()
    assert hover_desk.overlay.isVisible()

    # Moving from the tab into the pane starts the hide delay...
    hover_desk.sm._on_tab_hover_leave(hover_desk.button)
    assert hover_desk.sm._hide_timer.isActive()

    # ...but entering the pane cancels it, so it cannot expire while the
    # pointer is still inside.
    QApplication.sendEvent(hover_desk.overlay, QEvent(QEvent.Type.Enter))
    assert not hover_desk.sm._hide_timer.isActive()

    QTest.qWait(160)
    hover_desk.qapp.processEvents()
    assert hover_desk.overlay.isVisible()


def test_a_timeout_while_inside_does_not_close_the_overlay(hover_desk):
    """Even if the hide timer starts while the pointer is already inside.

    Event ordering can start the delay after the overlay's Enter event; the
    timeout must not close the pane, and leaving must still hide it later.
    """
    hover_desk.sm.hide_delay_ms = 80
    hover_desk.sm.hover_delay_ms = 0
    hover_desk.sm._on_tab_hover_enter(hover_desk.button)
    hover_desk.qapp.processEvents()

    QApplication.sendEvent(hover_desk.overlay, QEvent(QEvent.Type.Enter))
    hover_desk.sm._on_tab_hover_leave(hover_desk.button)
    assert hover_desk.sm._hide_timer.isActive()

    QTest.qWait(120)
    hover_desk.qapp.processEvents()
    assert hover_desk.overlay.isVisible()

    QApplication.sendEvent(hover_desk.overlay, QEvent(QEvent.Type.Leave))
    assert hover_desk.sm._hide_timer.isActive()
    QTest.qWait(120)
    hover_desk.qapp.processEvents()
    assert not hover_desk.overlay.isVisible()


def test_leaving_the_open_overlay_starts_the_hide_timer(hover_desk):
    hover_desk.sm.hide_delay_ms = 100
    hover_desk.sm.hover_delay_ms = 0
    hover_desk.sm._on_tab_hover_enter(hover_desk.button)
    hover_desk.qapp.processEvents()
    assert hover_desk.overlay.isVisible()

    QApplication.sendEvent(hover_desk.overlay, QEvent(QEvent.Type.Enter))
    assert not hover_desk.sm._hide_timer.isActive()

    QApplication.sendEvent(hover_desk.overlay, QEvent(QEvent.Type.Leave))
    assert hover_desk.sm._hide_timer.isActive()

    QTest.qWait(140)
    hover_desk.qapp.processEvents()
    assert not hover_desk.overlay.isVisible()


def test_leaving_the_overlay_hides_after_an_earlier_inside_timeout(hover_desk):
    """Regression: an expired timer must not leave the overlay stuck open.

    Previously the timeout returned while the pointer was inside the pane and
    stopped watching; leaving later never started a new timer.
    """
    hover_desk.sm.hide_delay_ms = 80
    hover_desk.sm.hover_delay_ms = 0
    hover_desk.sm._on_tab_hover_enter(hover_desk.button)
    hover_desk.qapp.processEvents()

    hover_desk.sm._on_tab_hover_leave(hover_desk.button)
    QApplication.sendEvent(hover_desk.overlay, QEvent(QEvent.Type.Enter))
    QTest.qWait(120)
    hover_desk.qapp.processEvents()
    assert hover_desk.overlay.isVisible()
    assert not hover_desk.sm._hide_timer.isActive()

    QApplication.sendEvent(hover_desk.overlay, QEvent(QEvent.Type.Leave))
    assert hover_desk.sm._hide_timer.isActive()
    QTest.qWait(120)
    hover_desk.qapp.processEvents()
    assert not hover_desk.overlay.isVisible()


def test_overlay_enter_leave_is_ignored_when_kept_open(hover_desk):
    hover_desk.sm.hide_delay_ms = 60
    hover_desk.sm.hover_delay_ms = 0
    hover_desk.sm._on_tab_hover_enter(hover_desk.button)
    hover_desk.qapp.processEvents()
    assert hover_desk.overlay.isVisible()

    hover_desk.sm.set_keep_open(True)
    QApplication.sendEvent(hover_desk.overlay, QEvent(QEvent.Type.Leave))
    assert not hover_desk.sm._hide_timer.isActive()

    QTest.qWait(100)
    hover_desk.qapp.processEvents()
    assert hover_desk.overlay.isVisible()


def test_a_click_is_never_delayed(hover_desk):
    hover_desk.sm.hover_delay_ms = 500
    hover_desk.sm._on_tab_clicked(hover_desk.button)
    hover_desk.qapp.processEvents()
    assert hover_desk.overlay.isVisible()


def test_delays_are_clamped(hover_desk):
    hover_desk.sm.hover_delay_ms = -10
    assert hover_desk.sm.hover_delay_ms == 0

    hover_desk.sm.hide_delay_ms = 999999
    assert hover_desk.sm.hide_delay_ms == 5000

    hover_desk.sm.switch_delay_ms = "not a number"
    assert hover_desk.sm.switch_delay_ms == 0
    assert hover_desk.sm._hide_timer.interval() == 5000
    assert hover_desk.sm._switch_timer.interval() == 0


def test_delays_round_trip_through_sidebar_state(hover_desk):
    hover_desk.sm.hover_delay_ms = 75
    hover_desk.sm.hide_delay_ms = 250
    hover_desk.sm.switch_delay_ms = 90
    state = hover_desk.sm.save_state()

    assert state["settings"]["hover_delay_ms"] == 75
    assert state["settings"]["hide_delay_ms"] == 250
    assert state["settings"]["switch_delay_ms"] == 90

    hover_desk.sm.hover_delay_ms = 0
    hover_desk.sm.hide_delay_ms = 0
    hover_desk.sm.switch_delay_ms = 0
    assert hover_desk.sm.restore_state(state)

    assert hover_desk.sm.hover_delay_ms == 75
    assert hover_desk.sm.hide_delay_ms == 250
    assert hover_desk.sm.switch_delay_ms == 90
    assert hover_desk.sm._hide_timer.interval() == 250
    assert hover_desk.sm._switch_timer.interval() == 90


def test_hover_enter_from_the_tab_bar_still_shows(hover_desk):
    """The bar emits sidebar_activated right after tab_hover_enter.

    sidebar_activated must not cancel the show timer the hover just queued.
    """
    hover_desk.sm.hover_delay_ms = 50
    bar = hover_desk.sm._sidebars[LEFT]

    bar.eventFilter(hover_desk.button, QEvent(QEvent.Type.HoverEnter))
    assert hover_desk.sm._show_timer.isActive()

    QTest.qWait(80)
    QApplication.instance().processEvents()
    assert hover_desk.overlay.isVisible()


def test_dock_manager_facade(hover_desk):
    hover_desk.manager.sidebar_hover_delay = 85
    hover_desk.manager.sidebar_hide_delay = 360
    hover_desk.manager.sidebar_switch_delay = 110
    assert hover_desk.sm.hover_delay_ms == 85
    assert hover_desk.sm.hide_delay_ms == 360
    assert hover_desk.sm.switch_delay_ms == 110
    assert hover_desk.manager.sidebar_hover_delay == 85
    assert hover_desk.manager.sidebar_hide_delay == 360
    assert hover_desk.manager.sidebar_switch_delay == 110
