"""Regression test: frameless title-bar double-click-to-maximize.

The frameless title-bar drag routing must NOT break double-click-to-maximize:
- the main window title bar keeps working when a frameless float exists,
- a frameless float's own title bar keeps working (maximize AND restore),
- even when the OS delivers the second press as a PLAIN WM_LBUTTONDOWN
  (what happens after the first click was consumed by the SC_MOVE move loop),
- and the title-bar drag state machine still runs cleanly (no stuck state /
  stale app filter / stale mouse grab after a drag).

Run:  python dev_smoke/smoke_dblclick.py
"""
import sys, os, time, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.disable(logging.CRITICAL)

from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import QTimer, QPoint, QEvent, Qt
from PySide6.QtGui import QMouseEvent
app = QApplication(sys.argv)

from demos.demo_app_custom_titlebar import DemoMainWindow
from lace.floating_dock_container_frameless import (
    FloatingDockContainer as FramelessFloatingDockContainer)

import win32gui, win32con

WM_LBUTTONDOWN, WM_LBUTTONUP, WM_LBUTTONDBLCLK = 0x201, 0x202, 0x203

def post_seq(hwnd, pt, second_as_dblclk=True):
    """Post press/up then press/up to the real HWND (the exact message
    sequence the OS delivers on a double-click)."""
    lparam = ((int(pt.y()) & 0xFFFF) << 16) | (int(pt.x()) & 0xFFFF)
    win32gui.PostMessage(hwnd, WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    time.sleep(0.03)
    win32gui.PostMessage(hwnd, WM_LBUTTONUP, 0, lparam)
    time.sleep(0.03)
    if second_as_dblclk:
        win32gui.PostMessage(hwnd, WM_LBUTTONDBLCLK, win32con.MK_LBUTTON, lparam)
    else:
        win32gui.PostMessage(hwnd, WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    time.sleep(0.03)
    win32gui.PostMessage(hwnd, WM_LBUTTONUP, 0, lparam)

def tb_point(win):
    tb = win.titleBar
    return QPoint(tb.rect().left() + tb.width() // 4,
                  tb.rect().top() + tb.height() // 2)

def fail(msg):
    print("RESULT: FAIL -", msg)
    app.exit(1)

results = {}
win = DemoMainWindow()
win.show()
win.move(60, 60)
app.processEvents()

def step_create():
    widgets = list(win.dock_manager.dock_widgets_map().values())
    results["A"] = FramelessFloatingDockContainer(dock_widget=widgets[0])
    results["A"].move(480, 480)
    results["A"].show()
    results["B"] = FramelessFloatingDockContainer(dock_widget=widgets[1])
    results["B"].move(900, 300)
    results["B"].show()
    QTimer.singleShot(500, flick_create)

def flick_create():
    """Create a float via a fast flick-drag (release lands inside the
    synthetic-release guard window).  The swallowed release must be recognised
    as the REAL release (button already up) and finalised, so no stale mouse
    grab / drag state survives to eat the main window's next click."""
    from lace.dock_widget_tab import DockWidgetTab
    from lace.enums import DragState
    tab = None
    for t in win.findChildren(DockWidgetTab):
        if t.text() == "Standard Editor":
            tab = t
            break
    if tab is None:
        return dbl_float_plain()
    c = QPoint(tab.rect().center().x(), tab.rect().center().y())
    def send(widget, etype, local, buttons):
        gp = widget.mapToGlobal(local)
        ev = QMouseEvent(etype, local, gp, Qt.LeftButton, buttons, Qt.NoModifier)
        QApplication.sendEvent(widget, ev)
        app.processEvents()
    send(tab, QEvent.MouseButtonPress, c, Qt.LeftButton)
    send(tab, QEvent.MouseMove, c + QPoint(0, 200), Qt.LeftButton)
    flt = win.dock_manager.floating_widgets()[-1]
    results["fltC"] = flt
    flt._ignore_synthetic_release = True  # inside the guard window
    send(tab, QEvent.MouseButtonRelease, c + QPoint(0, 200), Qt.NoButton)
    time.sleep(0.12)
    stale = (flt._dragging_state != DragState.inactive
             or QWidget.mouseGrabber() is tab)
    print("after flick-created float: state:", flt._dragging_state,
          "grabber:", QWidget.mouseGrabber())
    if stale:
        return fail("flick-created float left a stale grab/drag state")
    QTimer.singleShot(200, dbl_float_plain)

def dbl_float_plain():
    fltA = results["A"]
    post_seq(int(fltA.winId()), tb_point(fltA), second_as_dblclk=False)
    QTimer.singleShot(400, check_float_max)

def check_float_max():
    fltA = results["A"]
    results["A_maxed"] = fltA.isMaximized()
    print("FLOAT A maximized (plain 2nd press, 2 floats):", results["A_maxed"],
          "state:", fltA._dragging_state, "filter:", fltA._frameless_drag_filter)
    if not results["A_maxed"]:
        return fail("float double-click did not maximize")
    QTimer.singleShot(100, dbl_float_restore)

def dbl_float_restore():
    fltA = results["A"]
    post_seq(int(fltA.winId()), tb_point(fltA), second_as_dblclk=False)
    QTimer.singleShot(400, check_float_restore)

def check_float_restore():
    fltA = results["A"]
    results["A_restored"] = not fltA.isMaximized()
    print("FLOAT A restored (plain 2nd press):", results["A_restored"])
    if not results["A_restored"]:
        return fail("float double-click did not restore")
    QTimer.singleShot(100, dbl_main)

def dbl_main():
    post_seq(int(win.winId()), tb_point(win), second_as_dblclk=False)
    QTimer.singleShot(400, check_main)

def check_main():
    results["main_maxed"] = win.isMaximized()
    print("MAIN maximized (2 floats present):", results["main_maxed"])
    if not results["main_maxed"]:
        return fail("main-window double-click did not maximize")
    # No stuck drag state anywhere after all interactions
    from lace.enums import DragState
    stuck = [f for f in win.dock_manager.floating_widgets()
             if f._dragging_state != DragState.inactive]
    if stuck:
        return fail("floating container left in a drag state")
    # A real double-click dispatches the DblClick while the button is still
    # held — the async WM_SYSCOMMAND SC_MAXIMIZE is ignored by Windows in
    # that state (the "stale" double-click).  The title bars must use the
    # synchronous LaceStandardTitleBar toggle instead:
    from lace.frameless_window import LaceStandardTitleBar
    if not isinstance(win.titleBar, LaceStandardTitleBar):
        return fail("main title bar is not LaceStandardTitleBar")
    for f in win.dock_manager.floating_widgets():
        if not isinstance(f.titleBar, LaceStandardTitleBar):
            return fail("float title bar is not LaceStandardTitleBar")
    print("RESULT: PASS")
    app.exit(0)

QTimer.singleShot(400, step_create)
app.exec()
sys.exit(0 if results.get("main_maxed") else 1)
