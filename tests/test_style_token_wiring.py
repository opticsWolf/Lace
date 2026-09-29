# -*- coding: utf-8 -*-
"""Style tokens that were declared on the schemas but read by no widget.

Each test sets one token through the style manager and checks the widget
that should follow it, so a token cannot go back to being silently inert.
"""

import os
import sys

import pytest
from PySide6.QtWidgets import QLabel, QMainWindow

from lace.dock_manager import DockManager
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea
from lace.dock_theme import DockStyleCategory
from lace.sidebar_tab import VerticalTabButton


@pytest.fixture
def desk(qapp):
    win = QMainWindow()
    win.resize(900, 600)
    dock_manager = DockManager(win)

    def mk(name):
        dock_widget = DockWidget(name)
        dock_widget.set_widget(QLabel(name))
        return dock_widget

    area = dock_manager.add_dock_widget(DockWidgetArea.left, mk("Alpha"))
    dock_manager.add_dock_widget(DockWidgetArea.center, mk("Beta"), area)
    win.show()
    qapp.processEvents()

    yield dock_manager, area

    win.close()


def _tabs(area):
    return [area.dock_widget(i).tab_widget() for i in range(area.dock_widgets_count())]


@pytest.mark.parametrize("token, getter", [
    ("font_italic", "italic"),
    ("font_underline", "underline"),
])
def test_tab_label_font_follows_italic_and_underline(qapp, desk, token, getter):
    _, area = desk
    tabs = _tabs(area)
    assert not any(getattr(t._title_label.font(), getter)() for t in tabs)

    get_dock_style_manager().update(DockStyleCategory.TAB, **{token: True})
    qapp.processEvents()

    # Both states: the active tab's font is rebuilt on its own path.
    assert all(getattr(t._title_label.font(), getter)() for t in tabs)


def test_open_sidebar_tab_takes_the_active_font_weight(qapp):
    # Fonts rather than pixels: the offscreen platform has no font database,
    # so bold and regular text render alike there.
    button = VerticalTabButton("Panel")
    sm = get_dock_style_manager()
    try:
        assert not button._label_font(True).bold()

        sm.update(DockStyleCategory.SIDEBAR, tab_active_font_weight="bold")
        qapp.processEvents()

        assert button._label_font(True).bold(), "the open tab's label is not bold"
        assert not button._label_font(False).bold(), "the closed tab's label changed too"
        # Sized for the wider weight in either state, so opening never moves a tab.
        button.setChecked(True)
        open_length = button.sizeHint().height()
        button.setChecked(False)
        assert button.sizeHint().height() == open_length

        # Unset, the open tab keeps the closed tabs' weight: a theme that made
        # every sidebar label bold before this token was read stays bold.
        sm.update(DockStyleCategory.SIDEBAR, tab_font_weight="bold",
                  tab_active_font_weight=None)
        qapp.processEvents()
        assert button._label_font(False).bold()
        assert button._label_font(True).bold()

        sm.update(DockStyleCategory.SIDEBAR, tab_active_font_weight="normal")
        qapp.processEvents()
        assert button._label_font(False).bold()
        assert not button._label_font(True).bold()
    finally:
        button.deleteLater()


@pytest.mark.skipif(sys.platform == "darwin" and os.environ.get("QT_QPA_PLATFORM") == "offscreen",
                    reason="frameless windows segfault on macOS under offscreen")
def test_frameless_title_follows_italic_and_underline(qapp):
    from lace.frameless_window import FramelessLaceMainWindow

    win = FramelessLaceMainWindow()
    win.setWindowTitle("Title")
    DockManager(win)
    win.show()
    qapp.processEvents()
    try:
        label = win.titleBar.titleLabel
        assert not label.font().italic() and not label.font().underline()

        get_dock_style_manager().update(DockStyleCategory.TITLE_BAR,
                                        font_italic=True, font_underline=True)
        qapp.processEvents()   # the styler refreshes on a zero timer
        qapp.processEvents()
        label.ensurePolished()

        assert label.font().italic()
        assert label.font().underline()
    finally:
        win.close()
