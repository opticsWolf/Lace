# -*- coding: utf-8 -*-
"""lace.dialogs helpers (docs/DIALOG_TITLEBAR_PLAN.md, phase D3).

Each helper is driven through a QTimer while its modal loop runs: the host
must be a FramelessLaceDialog with the Qt dialog embedded (not a window),
and the return value must match the Qt static's for accept and cancel.
"""

import os
import sys

import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (QApplication, QColorDialog, QDialogButtonBox,
                               QFileDialog, QInputDialog, QLabel, QMessageBox)

pytest.importorskip("qframelesswindow", reason="qframelesswindow is optional")

if sys.platform == "darwin" and os.environ.get("QT_QPA_PLATFORM") == "offscreen":
    pytest.skip("frameless windows segfault on macOS under QT_QPA_PLATFORM=offscreen",
                allow_module_level=True)

from lace import dialogs
from lace.frameless_dialog import FramelessLaceDialog

SB = QMessageBox.StandardButton


def drive(action):
    """Run *action(host)* on the modal dialog once its loop is running."""
    seen = {}

    def go():
        host = QApplication.activeModalWidget()
        seen["host"] = host
        action(host)

    QTimer.singleShot(0, go)
    return seen


def _inner(host, cls):
    found = host.findChildren(cls)
    assert len(found) == 1
    return found[0]


def _button(host, which):
    box = _inner(host, QDialogButtonBox)
    return box.button(QDialogButtonBox.StandardButton(which.value))


@pytest.fixture(autouse=True)
def _frameless(qapp):
    dialogs.set_default_frameless(True)
    yield
    dialogs.set_default_frameless(True)
    QApplication.sendPostedEvents(None, 52)


# -- message boxes -------------------------------------------------------------

def test_information_host_and_ok(qapp):
    seen = drive(lambda h: _button(h, SB.Ok).click())
    assert dialogs.information(None, "Info", "Saved.") == SB.Ok
    host = seen["host"]
    assert isinstance(host, FramelessLaceDialog)
    assert host.windowTitle() == "Info"


def test_question_returns_clicked_button(qapp):
    drive(lambda h: _button(h, SB.No).click())
    assert dialogs.question(None, "Q", "Discard?") == SB.No
    drive(lambda h: _button(h, SB.Yes).click())
    assert dialogs.question(None, "Q", "Discard?") == SB.Yes


def test_return_answers_with_default(qapp):
    drive(lambda h: QTest.keyClick(h.focusWidget() or h, Qt.Key.Key_Return))
    assert dialogs.question(None, "Q", "Go?", SB.Yes | SB.No, SB.No) == SB.No


@pytest.mark.parametrize("buttons, expected", [
    (SB.Ok, SB.Ok),                          # the only button
    (SB.Yes | SB.No, SB.No),                 # the only NoRole button
    (SB.Save | SB.Discard | SB.Cancel, SB.Cancel),  # the only RejectRole one
    (SB.Yes | SB.YesToAll, SB.NoButton),     # nothing to escape to
])
def test_escape_follows_qmessagebox_rules(qapp, buttons, expected):
    drive(lambda h: QTest.keyClick(h, Qt.Key.Key_Escape))
    assert dialogs.message(None, "M", "text", "warning", buttons) == expected


def test_title_bar_close_is_escape(qapp):
    drive(lambda h: h.titleBar.closeBtn.click())
    assert dialogs.question(None, "Q", "Close?",
                            SB.Ok | SB.Cancel) == SB.Cancel


def test_message_body_icon_and_selectable_text(qapp):
    def check(h):
        text = h.findChild(QLabel, "laceMessageText")
        assert text.text() == "Disk <b>full</b>"
        assert text.textInteractionFlags() & Qt.TextInteractionFlag.TextSelectableByMouse
        assert h.findChild(QLabel, "laceMessageIcon") is not None
        h.reject()

    drive(check)
    dialogs.critical(None, "Error", "Disk <b>full</b>")


def test_no_icon_label_for_icon_none(qapp):
    def check(h):
        assert h.findChild(QLabel, "laceMessageIcon") is None
        h.reject()

    drive(check)
    dialogs.message(None, "M", "plain", icon="none")


def test_unknown_icon_raises(qapp):
    with pytest.raises(ValueError):
        dialogs.message(None, "M", "text", icon="fancy")


def test_about_closes_with_ok(qapp):
    drive(lambda h: _button(h, SB.Ok).click())
    assert dialogs.about(None, "About", "<b>Lace</b>") is None


def test_parented_host_is_modal_over_parent(qapp):
    from PySide6.QtWidgets import QWidget
    parent = QWidget()
    parent.show()
    seen = drive(lambda h: h.reject())
    dialogs.information(parent, "I", "x")
    assert seen["host"].parentWidget() is parent
    parent.close()


# -- input ------------------------------------------------------------------------

def test_get_text_accept_and_cancel(qapp):
    def accept(h):
        inner = _inner(h, QInputDialog)
        assert not inner.isWindow()
        inner.setTextValue("Layer 4")
        inner.accept()

    drive(accept)
    assert dialogs.get_text(None, "Rename", "Name:", text="Layer 3") == ("Layer 4", True)
    drive(lambda h: QTest.keyClick(h.focusWidget() or h, Qt.Key.Key_Escape))
    value, ok = dialogs.get_text(None, "Rename", "Name:", text="Layer 3")
    assert ok is False


def test_get_text_label_and_echo(qapp):
    def check(h):
        inner = _inner(h, QInputDialog)
        assert inner.labelText() == "Password:"
        assert inner.textEchoMode() == dialogs.QLineEdit.EchoMode.Password
        inner.reject()

    drive(check)
    dialogs.get_text(None, "Login", "Password:", dialogs.QLineEdit.EchoMode.Password)


def test_get_item(qapp):
    def accept(h):
        inner = _inner(h, QInputDialog)
        inner.setTextValue("green")
        inner.accept()

    drive(accept)
    assert dialogs.get_item(None, "Pick", "Colour:", ["red", "green"], 0, False) == ("green", True)
    drive(lambda h: _inner(h, QInputDialog).reject())
    assert dialogs.get_item(None, "Pick", "Colour:", ["red", "green"], 1) == ("green", False)


def test_get_int_and_double(qapp):
    def accept_int(h):
        inner = _inner(h, QInputDialog)
        assert (inner.intMinimum(), inner.intMaximum()) == (0, 10)
        inner.setIntValue(7)
        inner.accept()

    drive(accept_int)
    assert dialogs.get_int(None, "N", "Count:", 3, 0, 10) == (7, True)

    def accept_double(h):
        inner = _inner(h, QInputDialog)
        assert inner.doubleDecimals() == 2
        inner.setDoubleValue(1.25)
        inner.accept()

    drive(accept_double)
    assert dialogs.get_double(None, "X", "Scale:", 1.0, 0.0, 5.0, 2) == (1.25, True)


def test_get_multi_line_text(qapp):
    def accept(h):
        inner = _inner(h, QInputDialog)
        inner.setTextValue("a\nb")
        inner.accept()

    drive(accept)
    assert dialogs.get_multi_line_text(None, "Notes", "Text:") == ("a\nb", True)


# -- colour -------------------------------------------------------------------------

def test_get_color_accept_and_cancel(qapp):
    def accept(h):
        inner = _inner(h, QColorDialog)
        assert not inner.isWindow()
        assert inner.testOption(QColorDialog.ColorDialogOption.ShowAlphaChannel)
        inner.setCurrentColor(QColor(10, 20, 30, 40))
        inner.accept()

    drive(accept)
    c = dialogs.get_color(QColor("red"), None, "Seed",
                          QColorDialog.ColorDialogOption.ShowAlphaChannel)
    assert c.getRgb() == (10, 20, 30, 40)

    drive(lambda h: _inner(h, QColorDialog).reject())
    assert not dialogs.get_color(QColor("red")).isValid()


def test_get_color_keeps_buttons_even_if_asked_not_to(qapp):
    def check(h):
        inner = _inner(h, QColorDialog)
        assert not inner.testOption(QColorDialog.ColorDialogOption.NoButtons)
        inner.reject()

    drive(check)
    dialogs.get_color(QColor("red"), None, "",
                      QColorDialog.ColorDialogOption.NoButtons)


# -- files ----------------------------------------------------------------------------

def test_file_dialog_embedded_when_not_native(qapp, tmp_path):
    target = tmp_path / "theme.json"
    target.write_text("{}")

    def accept(h):
        inner = _inner(h, QFileDialog)
        assert not inner.isWindow()
        assert inner.testOption(QFileDialog.Option.DontUseNativeDialog)
        inner.selectFile(str(target))
        inner.accept()

    drive(accept)
    path, chosen = dialogs.get_open_file_name(
        None, "Open theme", str(tmp_path), "Theme JSON (*.json)", native=False)
    assert os.path.normcase(os.path.abspath(path)) == os.path.normcase(str(target))
    assert chosen == "Theme JSON (*.json)"

    drive(lambda h: _inner(h, QFileDialog).reject())
    assert dialogs.get_save_file_name(None, "Save", str(tmp_path), native=False) == ("", "")
    drive(lambda h: _inner(h, QFileDialog).reject())
    assert dialogs.get_open_file_names(None, "Open", str(tmp_path), native=False) == ([], "")
    drive(lambda h: _inner(h, QFileDialog).reject())
    assert dialogs.get_existing_directory(None, "Dir", str(tmp_path), native=False) == ""


def test_native_files_call_qt_static(qapp, monkeypatch):
    calls = []
    monkeypatch.setattr(QFileDialog, "getOpenFileName",
                        lambda *a: calls.append(a) or ("x.json", "f"))
    assert dialogs.get_open_file_name(None, "Open", "", "f") == ("x.json", "f")
    assert calls and calls[0][:4] == (None, "Open", "", "f")


def test_set_default_frameless_false_calls_qt(qapp, monkeypatch):
    dialogs.set_default_frameless(False)
    assert not dialogs.default_frameless()
    monkeypatch.setattr(QInputDialog, "getInt", lambda *a: (5, True))
    assert dialogs.get_int(None, "N", "n") == (5, True)
    monkeypatch.setattr(QColorDialog, "getColor", lambda *a: QColor("blue"))
    assert dialogs.get_color(QColor("red")) == QColor("blue")
    # QMessageBox falls back to a real QMessageBox, not a frameless host.
    seen = drive(lambda h: h.reject())
    dialogs.information(None, "I", "x")
    assert isinstance(seen["host"], QMessageBox)
    assert not isinstance(seen["host"], FramelessLaceDialog)
