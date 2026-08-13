"""Frameless float window state against the real Win32 window — Win11.

Companion to tests/test_frameless_window_state.py, which runs offscreen and
can therefore only see Qt's side of the story. Everything that actually
misbehaves does so because Qt's notion of "maximized" and the Win32 window
placement disagree, so this check reads both.

Covers:
  1. DockFlags.floating_taskbar_button: cleared, no minimize button and no
     WS_EX_APPWINDOW; set, both — and the taskbar button survives a
     minimize, so the float can be clicked back. Also toggled on a live
     float, which goes through update_window_flags_from_config(),
  2. maximize/restore round-trips the geometry for every pair of entry
     points (title-bar maximize button, title-bar double-click, dock-area
     maximize button) — the mixed pairs are the reported bug,
  3. a restored float is left at SW_NORMAL, i.e. Windows will accept
     SC_MOVE again, which is the only move mechanism the frameless title
     bar has,
  4. dragging a maximized float by its title bar restores it first.

Needs a real display and a real HWND: GetWindowPlacement and the taskbar
rules mean nothing under the offscreen plugin. Listed in run_all.py's
NEEDS_DISPLAY for that reason.

Run:  python dev_smoke/smoke_frameless_winstate.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.pop("QT_QPA_PLATFORM", None)
logging.disable(logging.CRITICAL)

import win32con
import win32gui
from PySide6.QtCore import QEvent, QPoint, Qt, QTimer
from PySide6.QtGui import QMouseEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow

app = QApplication(sys.argv)

from lace.dock_manager import DockManager
from lace.dock_widget import DockWidget
from lace.enums import DockFlags, DockWidgetArea, TitleBarMode
from lace.util import start_drag_distance

WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080
SHOWCMD = {1: "SW_NORMAL", 2: "SW_MINIMIZED", 3: "SW_MAXIMIZED"}
GRIP = QPoint(60, 16)

failures = []


def check(name, ok, detail=""):
    # ASCII only: these run in a cp1252 console.
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{'  | ' + detail if detail else ''}",
          flush=True)
    if not ok:
        failures.append(name)
    return ok


def show_cmd(widget):
    return SHOWCMD.get(win32gui.GetWindowPlacement(int(widget.winId()))[1], "?")


def has_taskbar_button(widget):
    """The Win32 rule: owned windows are excluded unless WS_EX_APPWINDOW."""
    hwnd = int(widget.winId())
    ex = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    if ex & WS_EX_APPWINDOW:
        return True
    owned = bool(win32gui.GetWindow(hwnd, win32con.GW_OWNER))
    return not owned and not (ex & WS_EX_TOOLWINDOW)


# ── the three ways a float gets maximized ─────────────────────────────────
def by_max_button(flt):
    button = flt.titleBar.maxBtn
    centre = button.rect().center()
    QTest.mousePress(button, Qt.LeftButton, Qt.NoModifier, centre)
    QTest.mouseRelease(button, Qt.LeftButton, Qt.NoModifier, centre)


def by_double_click(flt):
    QTest.mouseDClick(flt.titleBar, Qt.LeftButton, Qt.NoModifier, GRIP)


def by_area_button(flt):
    container = flt.dock_container()
    container.toggle_maximize_dock_area(container.opened_dock_areas()[0])


TOGGLES = {
    "maximize button": by_max_button,
    "double click": by_double_click,
    "dock-area button": by_area_button,
}


def new_float(dock_manager, x=200, y=200):
    dock_widget = DockWidget("Alpha")
    dock_widget.set_widget(QLabel("Alpha"))
    flt = dock_manager.floating_container_class()(dock_manager=dock_manager,
                                                  dock_widget=dock_widget)
    flt.resize(520, 400)
    flt.move(x, y)
    flt.show()
    QTest.qWait(350)
    return flt


def looks_maximized(flt):
    screen = QApplication.primaryScreen().availableGeometry()
    return flt.width() >= screen.width() * 0.9


def main(dock_manager):
    # ── 1. taskbar reachability, both states of the opt-in flag ───────────
    print("\n[1] DockFlags.floating_taskbar_button off (the default)")
    dock_manager.config_flags &= ~DockFlags.floating_taskbar_button
    flt = new_float(dock_manager)
    hwnd = int(flt.winId())
    ex = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    check("no minimize button is offered", not flt.titleBar.minBtn.isVisible())
    check("no WS_EX_APPWINDOW", not (ex & WS_EX_APPWINDOW),
          f"owner={win32gui.GetWindow(hwnd, win32con.GW_OWNER)}")
    flt.close()
    QTest.qWait(200)

    print("\n[1b] DockFlags.floating_taskbar_button on")
    dock_manager.config_flags |= DockFlags.floating_taskbar_button
    flt = new_float(dock_manager)
    hwnd = int(flt.winId())
    ex = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
    check("a minimize button is offered", flt.titleBar.minBtn.isVisible())
    check("WS_EX_APPWINDOW is set", bool(ex & WS_EX_APPWINDOW),
          f"owner={win32gui.GetWindow(hwnd, win32con.GW_OWNER)}")
    check("the float has a taskbar button", has_taskbar_button(flt))
    flt.showMinimized()
    QTest.qWait(500)
    check("minimize actually minimizes", flt.isMinimized(),
          f"IsIconic={bool(win32gui.IsIconic(hwnd))} showCmd={show_cmd(flt)}")
    check("the taskbar button survives the minimize", has_taskbar_button(flt))
    flt.showNormal()
    QTest.qWait(400)
    check("restore comes back", not flt.isMinimized() and flt.isVisible())
    flt.close()
    QTest.qWait(200)

    print("\n[1c] toggling the flag on a live float")
    dock_manager.config_flags &= ~DockFlags.floating_taskbar_button
    flt = new_float(dock_manager)
    check("starts without a taskbar button", not has_taskbar_button(flt))
    dock_manager.config_flags |= DockFlags.floating_taskbar_button
    QTest.qWait(600)
    check("gains one when the flag is set", has_taskbar_button(flt),
          f"minBtn={flt.titleBar.minBtn.isVisible()}")
    dock_manager.config_flags &= ~DockFlags.floating_taskbar_button
    QTest.qWait(600)
    check("gives it back when the flag is cleared", not has_taskbar_button(flt),
          f"minBtn={flt.titleBar.minBtn.isVisible()}")
    flt.close()
    QTest.qWait(200)

    # ── 2 & 3. the entry-point matrix ─────────────────────────────────────
    print("\n[2] maximize/restore round-trip, every pair of entry points")
    for max_name, maximize in TOGGLES.items():
        for restore_name, restore in TOGGLES.items():
            flt = new_float(dock_manager)
            start = flt.geometry()
            label = f"{max_name} -> {restore_name}"

            maximize(flt)
            QTest.qWait(500)
            grew = looks_maximized(flt)
            claims_max = flt.isMaximized()
            if not check(f"{label}: maximize took effect", grew and claims_max,
                         f"isMaximized={claims_max} geom={flt.geometry().getRect()} "
                         f"win32={show_cmd(flt)}"):
                flt.close()
                QTest.qWait(200)
                continue

            restore(flt)
            QTest.qWait(500)
            check(f"{label}: geometry restored", flt.geometry() == start,
                  f"now {flt.geometry().getRect()} vs start {start.getRect()}")
            check(f"{label}: isMaximized() cleared", not flt.isMaximized())
            check(f"{label}: still movable (SW_NORMAL)",
                  show_cmd(flt) == "SW_NORMAL", f"win32={show_cmd(flt)}")
            flt.close()
            QTest.qWait(200)

    # ── 4. rip out of maximize ────────────────────────────────────────────
    print("\n[4] dragging a maximized float restores it first")
    import qframelesswindow.utils as qf_utils

    original_move = qf_utils.startSystemMove
    moves = []
    qf_utils.startSystemMove = lambda window, pos: moves.append((window, pos))
    try:
        for name, maximize in (("maximize button", by_max_button),
                               ("double click", by_double_click)):
            flt = new_float(dock_manager)
            maximize(flt)
            QTest.qWait(500)
            if not flt.isMaximized():
                check(f"rip-out after {name}: precondition", False, "did not maximize")
                flt.close()
                QTest.qWait(200)
                continue

            moves.clear()
            title_bar = flt.titleBar
            for event_type, pos, buttons in (
                    (QEvent.MouseButtonPress, GRIP, Qt.LeftButton),
                    (QEvent.MouseMove,
                     GRIP + QPoint(start_drag_distance() + 20, 4), Qt.LeftButton)):
                QApplication.sendEvent(title_bar, QMouseEvent(
                    event_type, pos, title_bar.mapToGlobal(pos),
                    Qt.LeftButton, buttons, Qt.NoModifier))
                QTest.qWait(120)

            check(f"rip-out after {name}: restored before the move",
                  not flt.isMaximized() and show_cmd(flt) == "SW_NORMAL",
                  f"isMaximized={flt.isMaximized()} win32={show_cmd(flt)} "
                  f"startSystemMove calls={len(moves)}")

            QApplication.sendEvent(title_bar, QMouseEvent(
                QEvent.MouseButtonRelease, GRIP, title_bar.mapToGlobal(GRIP),
                Qt.LeftButton, Qt.NoButton, Qt.NoModifier))
            QTest.qWait(200)
            flt.close()
            QTest.qWait(200)
    finally:
        qf_utils.startSystemMove = original_move


def run():
    win = QMainWindow()
    win.setWindowTitle("Lace — frameless window-state smoke")
    win.resize(900, 600)
    dock_manager = DockManager(win)
    dock_manager.title_bar_mode = TitleBarMode.custom
    anchor = DockWidget("Anchor")
    anchor.set_widget(QLabel("Anchor"))
    dock_manager.add_dock_widget(DockWidgetArea.center, anchor)
    win.show()
    QTest.qWait(400)

    cls = dock_manager.floating_container_class()
    if cls.__name__ != "FramelessFloatingDockContainer":
        print("RESULT: SKIP - qframelesswindow unavailable, floats are native")
        app.exit(0)
        return

    try:
        main(dock_manager)
    finally:
        win.close()

    print()
    if failures:
        print(f"RESULT: FAIL - {len(failures)} check(s):")
        for name in failures:
            print(f"  - {name}")
        app.exit(1)
    else:
        print("RESULT: PASS")
        app.exit(0)


QTimer.singleShot(300, run)
sys.exit(app.exec())
