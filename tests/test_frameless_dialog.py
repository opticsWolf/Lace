# -*- coding: utf-8 -*-
"""FramelessLaceDialog (docs/DIALOG_TITLEBAR_PLAN.md, phase D2).

A frameless QDialog with the main window's themed title bar: construction,
live retheme, modality, styler disposal, chrome heal and placement.
"""

import gc
import os
import sys

import pytest
from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (QApplication, QDialog, QLabel, QPushButton,
                               QWidget)

pytest.importorskip("qframelesswindow", reason="qframelesswindow is optional")

if sys.platform == "darwin" and os.environ.get("QT_QPA_PLATFORM") == "offscreen":
    pytest.skip("frameless windows segfault on macOS under QT_QPA_PLATFORM=offscreen",
                allow_module_level=True)

from lace.dock_style_manager import apply_dock_theme, get_dock_style_manager
from lace.frameless_dialog import FramelessLaceDialog
from lace.frameless_titlebar import FramelessTitleBarStyler
from lace.frameless_window import FramelessLaceMainWindow, LaceStandardTitleBar
from lace.title_bar_colors import title_bar_colors

DEFERRED_DELETE = 52


def _subscribed(styler):
    sm = get_dock_style_manager()
    return any(styler in subs for subs in sm._subscribers.values())


def _stylers():
    sm = get_dock_style_manager()
    return {s for subs in sm._subscribers.values() for s in subs
            if isinstance(s, FramelessTitleBarStyler)}


def _destroy(qapp, widget):
    widget.deleteLater()
    QApplication.sendPostedEvents(None, DEFERRED_DELETE)
    qapp.processEvents()


@pytest.fixture
def dialog(qapp):
    dlg = FramelessLaceDialog()
    yield dlg
    try:
        dlg.close()
        _destroy(qapp, dlg)
    except RuntimeError:
        pass


# -- construction -----------------------------------------------------------

def test_default_bar_and_close_only_buttons(dialog):
    bar = dialog.titleBar
    assert isinstance(bar, LaceStandardTitleBar)
    assert isinstance(dialog, QDialog)
    assert dialog.buttons() == "close"
    assert bar.minBtn.isHidden() and bar.maxBtn.isHidden()
    assert not bar.closeBtn.isHidden()
    assert not bar._isDoubleClickEnabled
    assert dialog.layout().itemAt(0).widget() is bar


@pytest.mark.parametrize("buttons, min_shown, max_shown", [
    ("min_close", True, False),
    ("all", True, True),
])
def test_button_sets(qapp, buttons, min_shown, max_shown):
    dlg = FramelessLaceDialog(buttons=buttons)
    bar = dlg.titleBar
    assert bar.minBtn.isHidden() is not min_shown
    assert bar.maxBtn.isHidden() is not max_shown
    assert bar._isDoubleClickEnabled is max_shown
    _destroy(qapp, dlg)


def test_unknown_button_set_raises(qapp):
    with pytest.raises(ValueError):
        FramelessLaceDialog(buttons="max_only")


def test_title_follows_window_title(dialog):
    dialog.setWindowTitle("Rename layer")
    assert dialog.titleBar.titleLabel.text() == "Rename layer"


def test_custom_bar_gets_current_title_and_buttons(dialog):
    dialog.setWindowTitle("Before swap")
    dialog.setTitleBar(LaceStandardTitleBar(dialog))
    bar = dialog.titleBar
    assert bar.titleLabel.text() == "Before swap"
    assert bar.maxBtn.isHidden()
    assert dialog.layout().itemAt(0).widget() is bar
    assert dialog.titlebar_styler().title_bar is bar


def test_content_layout_and_replacement(qapp, dialog):
    label = QLabel("body")
    dialog.contentLayout().addWidget(label)
    assert label.parent() is dialog.contentWidget()
    assert dialog.contentLayout() is dialog.contentWidget().layout()

    old = dialog.contentWidget()
    new = QWidget()
    dialog.setContentWidget(new)
    assert dialog.contentWidget() is new
    assert new.parent() is dialog
    assert dialog.layout().indexOf(new) == 1
    assert dialog.layout().indexOf(old) < 0


def test_sizes_to_content_not_500(qapp, dialog):
    dialog.contentLayout().addWidget(QLabel("short"))
    dialog.show()
    qapp.processEvents()
    assert dialog.size() != dialog.size().__class__(500, 500)
    assert dialog.height() < 500


def test_fixed_size_when_not_resizable(qapp):
    dlg = FramelessLaceDialog(resizable=False)
    dlg.contentLayout().addWidget(QLabel("fixed"))
    dlg.show()
    qapp.processEvents()
    assert not dlg.isResizable()
    assert not dlg._isResizeEnabled
    assert dlg.minimumSize() == dlg.maximumSize()
    dlg.setResizable(True)
    assert dlg._isResizeEnabled
    dlg.close()
    _destroy(qapp, dlg)


# -- theme --------------------------------------------------------------------

def test_retheme_matches_main_window(qapp):
    apply_dock_theme("dark")
    qapp.processEvents()
    win = FramelessLaceMainWindow()
    win._register_titlebar_theme()
    dlg = FramelessLaceDialog(win)
    apply_dock_theme("light")
    qapp.processEvents()
    qapp.processEvents()
    assert dlg.titleBar.styleSheet() == win.titleBar.styleSheet()
    bg = title_bar_colors().background
    assert f"background: {bg.name()}" in dlg.titleBar.styleSheet()
    assert (dlg.titleBar.closeBtn._normalColor
            == win.titleBar.closeBtn._normalColor)
    _destroy(qapp, dlg)
    _destroy(qapp, win)
    apply_dock_theme("dark")


# -- modality -------------------------------------------------------------------

@pytest.mark.parametrize("slot, expected", [
    ("accept", QDialog.DialogCode.Accepted),
    ("reject", QDialog.DialogCode.Rejected),
])
def test_exec_returns_on_accept_and_reject(qapp, dialog, slot, expected):
    QTimer.singleShot(0, getattr(dialog, slot))
    assert dialog.exec() == expected


def test_escape_rejects(qapp, dialog):
    def press():
        QTest.keyClick(dialog, Qt.Key.Key_Escape)
    QTimer.singleShot(0, press)
    assert dialog.exec() == QDialog.DialogCode.Rejected


def test_return_triggers_default_button(qapp, dialog):
    ok = QPushButton("OK")
    ok.setDefault(True)
    ok.clicked.connect(dialog.accept)
    dialog.contentLayout().addWidget(ok)

    def press():
        QTest.keyClick(dialog, Qt.Key.Key_Return)
    QTimer.singleShot(0, press)
    assert dialog.exec() == QDialog.DialogCode.Accepted


# -- disposal ---------------------------------------------------------------------

def test_styler_unregistered_when_dialog_deleted(qapp):
    dlg = FramelessLaceDialog()
    styler = dlg.titlebar_styler()
    assert _subscribed(styler)
    _destroy(qapp, dlg)
    assert styler.disposed
    assert not _subscribed(styler)


def test_no_styler_leak_over_twenty_dialogs(qapp):
    # Stylers of earlier tests' windows may still be awaiting collection;
    # collect them so they cannot drop out of the count mid-loop.
    gc.collect()
    baseline = len(_stylers())
    kept = []
    for _ in range(20):
        dlg = FramelessLaceDialog()
        dlg.show()
        qapp.processEvents()
        kept.append(dlg.titlebar_styler())  # outlives the dialog
        dlg.close()
        _destroy(qapp, dlg)
    assert len(_stylers()) <= baseline


def test_disposed_styler_ignores_theme_changes(qapp):
    dlg = FramelessLaceDialog()
    styler = dlg.titlebar_styler()
    _destroy(qapp, dlg)
    styler.on_style_changed(None, {})
    assert not styler._refresh_queued
    styler.refresh_style()  # no widget left; must not raise
    styler.dispose()        # idempotent


def test_main_window_reregister_disposes_old_styler(qapp):
    win = FramelessLaceMainWindow()
    win._register_titlebar_theme()
    first = win.titlebar_styler()
    win._register_titlebar_theme()
    assert first.disposed and not _subscribed(first)
    assert _subscribed(win.titlebar_styler())
    _destroy(qapp, win)


# -- heal ---------------------------------------------------------------------------

def test_winid_change_heals_once(qapp, dialog):
    dialog.show()
    qapp.processEvents()
    qapp.processEvents()
    calls = []
    orig = dialog.updateFrameless
    dialog.updateFrameless = lambda: (calls.append(1), orig())[1]
    dialog._last_healed_winid = 99999
    QApplication.sendEvent(dialog, QEvent(QEvent.Type.WinIdChange))
    QApplication.sendEvent(dialog, QEvent(QEvent.Type.WinIdChange))
    qapp.processEvents()
    assert len(calls) == 1


# -- placement ----------------------------------------------------------------------

def _parent_window(qapp, x, y, w, h):
    parent = QWidget()
    parent.setGeometry(x, y, w, h)
    parent.show()
    qapp.processEvents()
    return parent


def test_centred_on_parent_window(qapp):
    parent = _parent_window(qapp, 100, 100, 600, 400)
    dlg = FramelessLaceDialog(parent)
    dlg.contentLayout().addWidget(QLabel("centred"))
    dlg.show()
    qapp.processEvents()
    centre = dlg.frameGeometry().center()
    target = parent.frameGeometry().center()
    assert abs(centre.x() - target.x()) <= 2
    assert abs(centre.y() - target.y()) <= 2
    _destroy(qapp, dlg)
    _destroy(qapp, parent)


def test_clamped_to_screen(qapp):
    screen = QApplication.primaryScreen().availableGeometry()
    parent = _parent_window(qapp, screen.right() - 60, screen.bottom() - 60, 300, 300)
    dlg = FramelessLaceDialog(parent)
    dlg.contentLayout().addWidget(QLabel("clamped"))
    dlg.show()
    qapp.processEvents()
    assert screen.contains(dlg.frameGeometry())
    _destroy(qapp, dlg)
    _destroy(qapp, parent)
