# -*- coding: utf-8 -*-
"""Custom-bar refactor from docs/frameless-webengine-findings.md §1/§2/§4.

- Anchored inserts (no hardcoded layout indices).
- canDrag veto inherited from LaceStandardTitleBar.
- Theme paint inherited from LaceStandardTitleBar.
- DockManager installs the app-wide palette bridge itself.
- DockManager.main_title_bar applies live to a frameless parent.
"""

import os
import sys

import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QLineEdit, QMainWindow, QMenuBar

from lace.dock_manager import DockManager
from lace.frameless_window import (
    FramelessLaceMainWindow,
    FramelessLaceWindow,
    LaceStandardTitleBar,
    titlebar_blocks_drag,
)

if sys.platform == "darwin" and os.environ.get("QT_QPA_PLATFORM") == "offscreen":
    pytest.skip("frameless windows segfault on macOS under QT_QPA_PLATFORM=offscreen",
                allow_module_level=True)


@pytest.fixture
def main_win(qapp):
    w = FramelessLaceMainWindow()
    w.show()
    qapp.processEvents()
    qapp.processEvents()
    yield w
    w.close()


def test_default_bar_is_lace_standard(qapp, main_win):
    assert isinstance(main_win.titleBar, LaceStandardTitleBar)
    floater = FramelessLaceWindow()
    try:
        assert isinstance(floater.titleBar, LaceStandardTitleBar)
    finally:
        floater.close()


def test_candrag_vetoes_interactive_children(qapp, main_win):
    bar = main_win.titleBar
    assert bar.canDrag(QPoint(60, 16))

    line = QLineEdit(bar)
    line.resize(100, 20)
    line.move(200, 6)
    line.show()
    menu = QMenuBar(bar)
    menu.resize(120, 20)
    menu.move(60, 6)
    menu.show()
    qapp.processEvents()

    line_pos = bar.mapFromGlobal(line.mapToGlobal(QPoint(5, 5)))
    menu_pos = bar.mapFromGlobal(menu.mapToGlobal(QPoint(5, 5)))
    assert titlebar_blocks_drag(bar, line_pos)
    assert not bar.canDrag(line_pos)
    assert titlebar_blocks_drag(bar, menu_pos)
    assert not bar.canDrag(menu_pos)


def test_anchored_insert_after_title(qapp, main_win):
    from PySide6.QtWidgets import QLabel
    bar = main_win.titleBar
    label = QLabel("x", bar)
    idx = bar.insert_content_widget(label)
    assert idx == bar.hBoxLayout.indexOf(bar.titleLabel) + 1


def test_manager_installs_app_bridge_without_style_clobber(qapp):
    style_before = QApplication.instance().style().objectName()
    win = QMainWindow()
    manager = DockManager(win)
    try:
        assert manager._app_theme_bridge is not None
        assert QApplication.instance().style().objectName() == style_before
    finally:
        win.close()


def test_main_title_bar_live_swap(qapp):
    class CustomBar(LaceStandardTitleBar):
        pass

    win = FramelessLaceMainWindow()
    win.show()
    qapp.processEvents()
    manager = DockManager(win)
    try:
        manager.main_title_bar = CustomBar
        qapp.processEvents()
        assert isinstance(win.titleBar, CustomBar)
    finally:
        win.close()
