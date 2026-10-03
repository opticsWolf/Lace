# -*- coding: utf-8 -*-
"""A frameless dialog must not make its parent window's docks native.

FramelessLaceDialog asks for its winId() while it is built. Without
AA_DontCreateNativeWidgetSiblings Qt then makes the dialog's siblings native
too, the root DockContainerWidget among them, and the docks stop taking clicks
(native-sibling-freeze.md). DockManager sets the attribute.
"""

import os
import sys

import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QTextEdit, QWidget

pytest.importorskip("qframelesswindow", reason="qframelesswindow is optional")

if sys.platform == "darwin" and os.environ.get("QT_QPA_PLATFORM") == "offscreen":
    pytest.skip("frameless windows segfault on macOS under QT_QPA_PLATFORM=offscreen",
                allow_module_level=True)

from lace import dialogs
from lace.enums import DockWidgetArea
from lace.frameless_dialog import FramelessLaceDialog

ATTR = Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings


@pytest.fixture
def desk(qapp, make_desk):
    """A shown dock window built with the attribute cleared beforehand, as in a
    fresh application."""
    was = qapp.testAttribute(ATTR)
    QApplication.setAttribute(ATTR, False)
    desk = make_desk(800, 600)
    for name, area in (("A", DockWidgetArea.left), ("B", DockWidgetArea.right)):
        dock = desk.widget(name)
        dock.set_widget(QTextEdit())
        desk.add(area, dock)
    desk.show()
    yield desk
    QApplication.setAttribute(ATTR, was)
    QApplication.sendPostedEvents(None, 52)


def native_children(window, *, besides=()):
    return [type(w).__name__ for w in window.findChildren(QWidget)
            if w.testAttribute(Qt.WidgetAttribute.WA_NativeWindow)
            and not isinstance(w, besides)]


def accept_soon():
    QTimer.singleShot(0, lambda: QApplication.activeModalWidget().accept())


@pytest.mark.parametrize("native_frames", [True, False])
def test_dock_manager_sets_the_attribute(qapp, make_desk, native_frames):
    QApplication.setAttribute(ATTR, False)
    make_desk(native_frames=native_frames)
    assert qapp.testAttribute(ATTR)


def test_a_frameless_dialog_leaves_the_docks_alien(desk):
    dialog = FramelessLaceDialog(desk.win)
    # qframelesswindow asks for the handle in the constructor on Windows only;
    # ask here so every platform takes the same path.
    dialog.winId()
    assert dialog.testAttribute(Qt.WidgetAttribute.WA_NativeWindow)
    assert native_children(desk.win, besides=FramelessLaceDialog) == []
    dialog.deleteLater()


def test_get_text_leaves_the_docks_alien(desk):
    accept_soon()
    assert dialogs.get_text(desk.win, "T", "name", text="x") == ("x", True)
    assert native_children(desk.win, besides=FramelessLaceDialog) == []


def test_information_leaves_the_docks_alien(desk):
    accept_soon()
    dialogs.information(desk.win, "T", "hello")
    assert native_children(desk.win, besides=FramelessLaceDialog) == []
