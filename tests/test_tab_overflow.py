# -*- coding: utf-8 -*-
"""Auto scroll arrows, the cramped tab minimum, and wheel scrolling."""

from PySide6.QtCore import QPoint
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QStyle

from lace.dock_widget import DockWidget
from lace.enums import DockFlags, DockWidgetArea, TitleBarButton


CENTER = DockWidgetArea.center


class _Wheel:
    def __init__(self, *, pixels=(0, 0), angle=(0, 0)):
        self._pixels = QPoint(*pixels)
        self._angle = QPoint(*angle)
        self.accepted = True

    def pixelDelta(self):
        return self._pixels

    def angleDelta(self):
        return self._angle

    def accept(self):
        self.accepted = True

    def ignore(self):
        self.accepted = False

    def isAccepted(self):
        return self.accepted


def _add_tabs(desk, count=15):
    first = desk.widget("Tab 0")
    area = desk.add(CENTER, first)
    docks = [first]
    for i in range(1, count):
        dock = desk.widget(f"Tab {i}")
        desk.add(CENTER, dock, target=area)
        docks.append(dock)
    desk.show()
    QTest.qWait(40)
    return area, docks


def _bar(area):
    return area._title_bar.tab_bar()


def test_arrows_appear_only_when_the_tabs_overflow(qapp, make_desk):
    desk = make_desk(400, 300)
    area, _docks = _add_tabs(desk)
    bar, title_bar = _bar(area), area._title_bar

    assert bar.is_overflowing()
    assert title_bar._tab_scroll_left.isVisible()
    assert title_bar._tab_scroll_right.isVisible()
    assert title_bar.button(TitleBarButton.tab_scroll_left) is title_bar._tab_scroll_left
    assert title_bar.button(TitleBarButton.tab_scroll_right) is title_bar._tab_scroll_right

    # Show the first tab without the deferred reveal moving the scroll bar.
    area.set_current_index(0)
    QTest.qWait(30)
    assert bar.horizontalScrollBar().value() == 0
    assert title_bar._tab_scroll_left.isEnabled() is False
    assert title_bar._tab_scroll_right.isEnabled() is True


def test_clicking_an_arrow_scrolls_to_the_next_hidden_tab(qapp, make_desk):
    desk = make_desk(400, 300)
    area, _docks = _add_tabs(desk)
    bar, title_bar = _bar(area), area._title_bar
    area.set_current_index(0)
    QTest.qWait(30)

    title_bar._tab_scroll_right.click()
    QTest.qWait(30)

    assert bar.horizontalScrollBar().value() > 0
    assert title_bar._tab_scroll_left.isEnabled() is True


def test_selecting_the_last_tab_reveals_it_after_the_layout(qapp, make_desk):
    desk = make_desk(400, 300)
    area, _docks = _add_tabs(desk)
    bar = _bar(area)
    area.set_current_index(bar.count() - 1)
    QTest.qWait(40)

    value = bar.horizontalScrollBar().value()
    viewport = bar.viewport().width()
    tab = bar.tab(bar.count() - 1)
    assert tab.geometry().left() >= value - 1
    assert tab.geometry().right() <= value + viewport + 1


def test_the_cramped_threshold_starts_before_the_layout_minimum(qapp, make_desk):
    desk = make_desk(480, 300)
    # Keep every tab's chrome identical: the active close button would add a
    # second minimum width and make the comparison depend on which tab is open.
    desk.manager.config_flags &= ~DockFlags.active_tab_has_close_button
    area, _docks = _add_tabs(desk, count=4)
    bar, title_bar = _bar(area), area._title_bar
    area.set_current_index(0)
    QTest.qWait(30)

    layout_total = sum(bar.tab(i).layout().minimumSize().width()
                       for i in range(bar.count()))
    cramped_total = sum(bar.tab(i).minimumWidth() for i in range(bar.count()))
    target = (layout_total + cramped_total) // 2

    # Fonts and themes change both totals.  Put the viewport between them
    # instead of relying on a fixed window width.
    for _ in range(5):
        viewport = bar.viewport().width()
        if layout_total <= viewport < cramped_total:
            break
        desk.win.resize(desk.win.width() + target - viewport, 300)
        QTest.qWait(30)

    assert layout_total <= bar.viewport().width()
    assert cramped_total > bar.viewport().width()
    assert bar.is_overflowing()
    assert title_bar._tab_scroll_right.isVisible()


def test_the_flag_off_hides_the_arrows_and_restores_the_old_minimum(qapp, make_desk):
    desk = make_desk(400, 300)
    area, docks = _add_tabs(desk)
    bar, title_bar = _bar(area), area._title_bar
    assert title_bar._tab_scroll_left.isVisible()
    assert docks[0]._tab_widget.minimumWidth() > 0

    desk.manager.config_flags &= ~DockFlags.dock_area_has_tab_scroll_buttons
    QTest.qWait(40)

    assert not title_bar._tab_scroll_left.isVisible()
    assert not title_bar._tab_scroll_right.isVisible()
    assert docks[0]._tab_widget.minimumWidth() == 0


def test_closing_tabs_removes_the_arrows(qapp, make_desk):
    desk = make_desk(900, 300)
    area, docks = _add_tabs(desk)
    bar, title_bar = _bar(area), area._title_bar
    assert title_bar._tab_scroll_left.isVisible()

    for dock in docks[:-2]:
        desk.manager.remove_dock_widget(dock)
    QTest.qWait(50)

    assert bar.count() == 2
    assert not bar.is_overflowing()
    assert not title_bar._tab_scroll_left.isVisible()
    assert not title_bar._tab_scroll_right.isVisible()


def test_cramped_minimum_is_a_multiple_of_the_elide_minimum(qapp, make_desk):
    desk = make_desk(900, 300)
    dock, _area = _tab_dock(desk, "A long title that is allowed to elide")
    tab = dock._tab_widget
    QTest.qWait(30)

    base = tab.layout().minimumSize().width()
    title_min = tab._title_label.minimumSizeHint().width()
    preferred = tab.layout().sizeHint().width()
    expected = max(base, min(preferred,
                             base - title_min
                             + round(tab.CRAMPED_FACTOR * title_min)))
    assert tab.minimumWidth() == expected
    assert tab.minimumWidth() > base


def test_an_icon_only_tab_keeps_its_chrome_width(qapp, make_desk):
    desk = make_desk(500, 300)
    dock = DockWidget("")
    dock.setObjectName("icon-only")
    dock.set_widget(QLabel("icon only"))
    dock.set_icon(QApplication.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
    area = desk.add(CENTER, dock)
    desk.show()
    QTest.qWait(30)
    tab = dock._tab_widget

    assert tab.text() == ""
    assert tab.minimumWidth() == tab.layout().minimumSize().width()
    assert tab.toolTip() == ""


def test_wheel_scrolls_only_when_the_tabs_overflow(qapp, make_desk):
    desk = make_desk(400, 300)
    area, _docks = _add_tabs(desk)
    bar = _bar(area)
    area.set_current_index(0)
    QTest.qWait(30)
    bar.horizontalScrollBar().setValue(0)

    wheel = _Wheel(angle=(0, -120))
    bar.wheelEvent(wheel)

    assert wheel.isAccepted()
    assert bar.horizontalScrollBar().value() > 0

    desk2 = make_desk(900, 300)
    dock = desk2.widget("One")
    desk2.add(CENTER, dock)
    desk2.show()
    QTest.qWait(30)
    bar2 = desk2.manager.root_container().findChild(type(bar))
    assert bar2 is not None
    no_overflow = _Wheel(angle=(0, -120))
    bar2.wheelEvent(no_overflow)
    assert not no_overflow.isAccepted()


def test_wheel_over_the_empty_title_bar_reaches_the_tabs(qapp, make_desk):
    desk = make_desk(400, 300)
    area, _docks = _add_tabs(desk)
    bar, title_bar = _bar(area), area._title_bar
    area.set_current_index(0)
    QTest.qWait(30)
    bar.horizontalScrollBar().setValue(0)

    wheel = _Wheel(angle=(0, -120))
    title_bar.wheelEvent(wheel)

    assert wheel.isAccepted()
    assert bar.horizontalScrollBar().value() > 0


def _tab_dock(desk, title):
    dock = desk.widget(title)
    area = desk.add(CENTER, dock)
    desk.show()
    QTest.qWait(20)
    return dock, area
