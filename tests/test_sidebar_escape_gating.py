# -*- coding: utf-8 -*-
"""The sidebar Escape shortcut must not swallow Esc for the rest of the app.

``SidebarKeyboardHandler`` binds Escape as a window-wide shortcut whose only
purpose is dismissing the hover overlay (which never takes focus, so the
binding cannot be scoped to the sidebar). It must therefore be enabled only
while an overlay is actually up: with nothing open, Esc belongs to whatever
has focus (terminals, editors, dialogs).

Covers the gate in both directions plus the functional key-press case.
"""

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow

from lace.dock_manager import DockManager
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea


@pytest.fixture
def stage(qapp):
    """Main window with a pinned widget and animations off (deterministic)."""
    win = QMainWindow()
    win.resize(900, 600)
    dock_manager = DockManager(win)
    dock_widget = DockWidget("Alpha")
    dock_widget.set_widget(QLabel("x"))
    dock_manager.add_dock_widget(DockWidgetArea.left, dock_widget)
    win.show()
    qapp.processEvents()
    sidebar = dock_manager.sidebar_manager
    sidebar.set_animations_enabled(False)
    sidebar.pin_widget(dock_widget, area=DockWidgetArea.left)
    qapp.processEvents()
    yield win, dock_manager, dock_widget
    win.close()


def _escape_shortcut(dock_manager):
    return dock_manager.sidebar_manager._keyboard._shortcuts["Escape"]


def _press_escape(window, qapp):
    QApplication.sendEvent(
        window, QKeyEvent(QEvent.KeyPress, Qt.Key_Escape, Qt.NoModifier))
    qapp.processEvents()


def test_escape_disabled_with_no_overlay(stage, qapp):
    win, dock_manager, _ = stage
    assert not dock_manager.sidebar_manager.overlay.isVisible()
    assert _escape_shortcut(dock_manager).isEnabled() is False


def test_escape_press_reaches_app_with_no_overlay(stage, qapp):
    """The regression: hidden overlay + Esc must not fire close_current."""
    win, dock_manager, _ = stage
    fired = []
    dock_manager.sidebar_manager._keyboard.close_current.connect(
        lambda: fired.append(1))
    _press_escape(win, qapp)
    assert fired == []


def test_escape_enabled_while_overlay_up(stage, qapp):
    win, dock_manager, dock_widget = stage
    sidebar = dock_manager.sidebar_manager
    fired = []
    sidebar._keyboard.close_current.connect(lambda: fired.append(1))
    sidebar.show_widget(dock_widget)
    qapp.processEvents()
    assert sidebar.overlay.isVisible()
    assert _escape_shortcut(dock_manager).isEnabled() is True
    _press_escape(win, qapp)
    assert fired == [1]


def test_escape_disabled_again_after_close(stage, qapp):
    win, dock_manager, dock_widget = stage
    sidebar = dock_manager.sidebar_manager
    sidebar.show_widget(dock_widget)
    qapp.processEvents()
    assert _escape_shortcut(dock_manager).isEnabled() is True
    sidebar.close_overlay()
    qapp.processEvents()
    assert not sidebar.overlay.isVisible()
    assert _escape_shortcut(dock_manager).isEnabled() is False
