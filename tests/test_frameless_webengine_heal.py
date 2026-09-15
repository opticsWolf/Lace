# -*- coding: utf-8 -*-
"""Auto-heal frameless chrome after native-handle recreation (option E).

A GL child (QWebEngineView first setHtml, QOpenGLWidget, …) makes Qt destroy
and recreate the top-level native handle, stripping the CAPTION/THICKFRAME
bits DWM rounding and Snap depend on. See
docs/frameless-webengine-findings.md §3.

FramelessLaceMainWindow / FramelessLaceWindow watch QEvent.WinIdChange and
defer a coalesced ensure_frameless_chrome() (updateFrameless + taskbar
ex-style). updateFrameless itself does not change the winId, so healing
cannot loop; spurious events with an unchanged handle are skipped.

Nothing here touches a real HWND — offscreen winId is small/0 — so handle
change is simulated by resetting _last_healed_winid.
"""

import os
import sys

import pytest
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication, QWidget

from lace.frameless_window import ensure_frameless_chrome

frameless = pytest.importorskip(
    "lace.frameless_window",
    reason="qframelesswindow is optional")
FramelessLaceMainWindow = frameless.FramelessLaceMainWindow
FramelessLaceWindow = frameless.FramelessLaceWindow

if sys.platform == "darwin" and os.environ.get("QT_QPA_PLATFORM") == "offscreen":
    pytest.skip("frameless windows segfault on macOS under QT_QPA_PLATFORM=offscreen",
                allow_module_level=True)


@pytest.fixture
def main_win(qapp):
    w = FramelessLaceMainWindow()
    w.show()
    qapp.processEvents()
    # Drain the first-show heal so each test starts settled.
    qapp.processEvents()
    yield w
    w.close()


def test_winid_change_schedules_coalesced_heal(qapp, main_win):
    calls = []
    orig = main_win.updateFrameless
    main_win.updateFrameless = lambda: (calls.append(1), orig())[1]
    # Simulate a genuine recreation (handle differs from last healed).
    main_win._last_healed_winid = 99999
    QApplication.sendEvent(main_win, QEvent(QEvent.Type.WinIdChange))
    QApplication.sendEvent(main_win, QEvent(QEvent.Type.WinIdChange))
    assert main_win._frameless_heal_queued
    qapp.processEvents()
    assert len(calls) == 1
    assert main_win._last_healed_winid == int(main_win.winId())


def test_spurious_winid_change_same_handle_skipped(qapp, main_win):
    calls = []
    orig = main_win.updateFrameless
    main_win.updateFrameless = lambda: (calls.append(1), orig())[1]
    # Already settled: current == last, so heal must be skipped.
    assert int(main_win.winId()) == main_win._last_healed_winid
    QApplication.sendEvent(main_win, QEvent(QEvent.Type.WinIdChange))
    qapp.processEvents()
    assert calls == []


def test_manual_restore_calls_update(qapp, main_win):
    calls = []
    orig = main_win.updateFrameless
    main_win.updateFrameless = lambda: (calls.append(1), orig())[1]
    assert main_win.restore_frameless_chrome() is True
    assert len(calls) == 1


def test_ensure_returns_false_without_updater(qapp):
    assert ensure_frameless_chrome(QWidget()) is False
    assert ensure_frameless_chrome(QApplication.instance()) is False


def test_heal_reapplies_taskbar_presence(qapp):
    w = FramelessLaceWindow()
    w.show()
    qapp.processEvents()
    qapp.processEvents()
    seen = []
    w._apply_taskbar_presence = lambda: seen.append(1)  # type: ignore[attr-defined]
    w._last_healed_winid = 99999
    QApplication.sendEvent(w, QEvent(QEvent.Type.WinIdChange))
    qapp.processEvents()
    assert seen == [1]
    w.close()


def test_heal_does_not_reschedule_itself(qapp, main_win):
    # updateFrameless is idempotent (winId unchanged) — healing must settle,
    # not queue another heal.
    main_win._last_healed_winid = 99999
    QApplication.sendEvent(main_win, QEvent(QEvent.Type.WinIdChange))
    qapp.processEvents()
    qapp.processEvents()
    assert not main_win._frameless_heal_queued
