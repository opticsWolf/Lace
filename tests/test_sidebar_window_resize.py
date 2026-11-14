# -*- coding: utf-8 -*-
"""The sidebar strip must not swallow the window-edge resize gesture.

Each SideTabBar carries a transparent grip on its window-facing edge. The
grip answers the press and hands it to QWindow.startSystemResize(); without
it the tab bar (or a tab button) receives the press and the window cannot be
resized from that edge.
"""

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from lace.enums import DockWidgetArea


class FakeWindowHandle:
    def __init__(self):
        self.calls = []

    def startSystemResize(self, edges):
        self.calls.append(edges)
        return True


def _sidebar(desk, side):
    desk.add(DockWidgetArea.center, "Center")
    desk.show()
    dock = desk.widget("Pinned")
    assert desk.manager.pin_dock_widget(dock, side)
    QApplication.instance().processEvents()
    bar = desk.manager.sidebar_manager._sidebars[side]
    return bar, bar._resize_grip


def _press(grip, local_pos, qapp):
    global_pos = grip.mapToGlobal(local_pos)
    event = QMouseEvent(
        QEvent.Type.MouseButtonPress, local_pos, global_pos,
        Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier)
    QApplication.sendEvent(grip, event)
    qapp.processEvents()


def test_left_grip_covers_the_window_edge(qapp, make_desk):
    desk = make_desk(900, 600)
    bar, grip = _sidebar(desk, DockWidgetArea.left)

    assert grip.isVisible()
    assert grip.geometry().left() == 0
    assert grip.width() == grip.THICKNESS
    assert grip.height() == bar.height()

    assert bar.childAt(QPoint(1, bar.height() // 2)) is grip


def test_right_grip_covers_the_window_edge(qapp, make_desk):
    desk = make_desk(900, 600)
    bar, grip = _sidebar(desk, DockWidgetArea.right)

    assert grip.isVisible()
    assert grip.geometry().right() == bar.width() - 1
    assert grip.width() == grip.THICKNESS

    assert bar.childAt(QPoint(bar.width() - 1, bar.height() // 2)) is grip


def test_left_grip_starts_a_left_resize(qapp, make_desk, monkeypatch):
    desk = make_desk(900, 600)
    _, grip = _sidebar(desk, DockWidgetArea.left)
    handle = FakeWindowHandle()
    monkeypatch.setattr(desk.win, "windowHandle", lambda: handle)

    _press(grip, QPoint(1, grip.height() // 2), qapp)

    assert handle.calls
    assert handle.calls[0] & Qt.Edge.LeftEdge


def test_right_grip_starts_a_right_resize(qapp, make_desk, monkeypatch):
    desk = make_desk(900, 600)
    _, grip = _sidebar(desk, DockWidgetArea.right)
    handle = FakeWindowHandle()
    monkeypatch.setattr(desk.win, "windowHandle", lambda: handle)

    _press(grip, QPoint(grip.width() - 1, grip.height() // 2), qapp)

    assert handle.calls
    assert handle.calls[0] & Qt.Edge.RightEdge


def test_grip_cursor_follows_the_edge(qapp, make_desk):
    desk = make_desk(900, 600)
    _, grip = _sidebar(desk, DockWidgetArea.left)
    edge = grip.mapToGlobal(QPoint(1, grip.height() // 2))

    assert grip._cursor_for(grip._edges_for(edge)) == Qt.CursorShape.SizeHorCursor


def test_grip_still_works_while_the_overlay_is_open(qapp, make_desk, monkeypatch):
    desk = make_desk(900, 600)
    bar, grip = _sidebar(desk, DockWidgetArea.left)
    sm = desk.manager.sidebar_manager
    sm.set_animations_enabled(False)
    sm.hover_delay_ms = 0
    dock = next(iter(sm._pinned))
    sm._show_for_button(sm._pinned[dock].button_for(dock))
    qapp.processEvents()
    assert sm.overlay.isVisible()

    handle = FakeWindowHandle()
    monkeypatch.setattr(desk.win, "windowHandle", lambda: handle)
    _press(grip, QPoint(1, grip.height() // 2), qapp)

    assert handle.calls
    assert handle.calls[0] & Qt.Edge.LeftEdge
