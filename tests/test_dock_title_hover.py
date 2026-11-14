# -*- coding: utf-8 -*-
"""Dock tab tooltips: elision, descriptions, and the sidebar fallback."""

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLabel

from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea


LEFT = DockWidgetArea.left


def _add(desk, title, *, description=""):
    dock = DockWidget(title, description=description)
    dock.set_widget(QLabel(title or "icon-only"))
    area = desk.add(DockWidgetArea.center, dock)
    desk.show()
    QTest.qWait(10)
    return dock, area


def test_a_short_title_without_a_description_has_no_tooltip(qapp, make_desk):
    desk = make_desk(900, 500)
    dock, _area = _add(desk, "Short")
    tab = dock._tab_widget

    assert not tab._title_label.is_elided()
    assert tab.toolTip() == ""
    assert tab._title_label.toolTip() == ""


def test_an_elided_title_shows_its_full_text(qapp, make_desk):
    title = "A very long dock title that cannot possibly fit in this narrow window"
    desk = make_desk(320, 300)
    dock, _area = _add(desk, title)
    tab = dock._tab_widget

    assert tab._title_label.is_elided()
    assert tab.toolTip() == title
    assert tab._title_label.toolTip() == title


def test_a_title_tooltip_clears_again_when_the_title_fits(qapp, make_desk):
    title = "A very long dock title that cannot possibly fit in this narrow window"
    desk = make_desk(320, 300)
    dock, _area = _add(desk, title)
    tab = dock._tab_widget
    assert tab.toolTip() == title

    desk.win.resize(1500, 300)
    QTest.qWait(20)

    assert not tab._title_label.is_elided()
    assert tab.toolTip() == ""
    assert tab._title_label.toolTip() == ""


def test_a_description_forces_the_composed_tooltip(qapp, make_desk):
    desk = make_desk(900, 500)
    dock, _area = _add(desk, "Short")
    tab = dock._tab_widget
    assert tab.toolTip() == ""

    dock.set_description("Build output and diagnostics")

    assert tab.toolTip() == "Short\nBuild output and diagnostics"
    assert tab._title_label.toolTip() == tab.toolTip()
    assert dock.toggle_view_action().toolTip() == tab.toolTip()


def test_a_title_change_keeps_the_description(qapp, make_desk):
    desk = make_desk(900, 500)
    dock, _area = _add(desk, "Short", description="Build output")

    dock.setWindowTitle("Renamed")
    QTest.qWait(10)

    assert dock._tab_widget.toolTip() == "Renamed\nBuild output"


def test_clearing_a_description_removes_the_tooltip(qapp, make_desk):
    desk = make_desk(900, 500)
    dock, _area = _add(desk, "Short", description="Build output")
    tab = dock._tab_widget
    assert tab.toolTip()

    dock.set_description("   ")
    QTest.qWait(10)

    assert tab.toolTip() == ""
    assert tab._title_label.toolTip() == ""


def test_an_explicit_tab_tooltip_wins_and_clears_back(qapp, make_desk):
    title = "A very long dock title that cannot possibly fit in this narrow window"
    desk = make_desk(320, 300)
    dock, _area = _add(desk, title)
    tab = dock._tab_widget
    assert tab.toolTip() == title

    dock.set_tab_tool_tip("Explicit")
    assert tab.toolTip() == "Explicit"

    dock.set_tab_tool_tip("")
    assert tab.toolTip() == title


def test_an_empty_title_with_a_description_has_no_leading_newline(qapp):
    dock = DockWidget("", description="Only the description")
    tab = dock._tab_widget

    assert tab.toolTip() == "Only the description"
    assert tab._title_label.toolTip() == "Only the description"


def test_sidebar_tab_tooltip_follows_title_and_description(qapp, make_desk):
    desk = make_desk(900, 700)
    dock, _area = _add(desk, "Short")
    sm = desk.manager.sidebar_manager
    sm.set_animations_enabled(False)
    assert sm.pin_widget(dock, area=LEFT)
    QTest.qWait(150)
    button = sm._pinned[dock].button_for(dock)

    assert not button.is_text_clipped()
    assert button.toolTip() == ""

    dock.set_description("Build output")
    assert button.toolTip() == "Short\nBuild output"

    long_title = "A sidebar tab title long enough that it has to be clipped"
    dock.setWindowTitle(long_title)
    QTest.qWait(10)
    assert button.text() == long_title
    assert button.is_text_clipped()
    assert button.toolTip() == f"{long_title}\nBuild output"

    dock.set_description("")
    assert button.toolTip() == long_title
