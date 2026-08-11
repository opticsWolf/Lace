# -*- coding: utf-8 -*-
"""A floating window must not re-theme the whole application — §3.5.

_apply_dock_palette_to_window() used to call qapp.setPalette() and toggle the
global QStyleHints.colorScheme to the opposite scheme and back, which emitted
colorSchemeChanged twice — once with the wrong scheme. An application using
ThemeManager.install_listener() saw that as "the OS switched to light mode" and
flipped its whole theme, so toggling one dock flag strobed the entire UI.
"""

import pytest
from PySide6.QtWidgets import QLabel, QMainWindow

from lace.dock_manager import DockManager
from lace.dock_widget import DockWidget
from lace.floating_dock_container import FloatingDockContainer


@pytest.fixture
def floating(qapp):
    win = QMainWindow()
    dock_manager = DockManager(win)
    dock_widget = DockWidget("Alpha")
    dock_widget.set_widget(QLabel("x"))
    dock_widget.set_dock_manager(dock_manager)
    dock_manager.dock_widgets_map()[dock_widget.objectName()] = dock_widget
    container = FloatingDockContainer(dock_widget=dock_widget)
    container.show()
    qapp.processEvents()
    yield container
    container.close()
    win.close()


def test_palette_push_does_not_touch_the_application(floating, qapp):
    before = qapp.palette()
    floating._apply_dock_palette_to_window()
    qapp.processEvents()
    assert qapp.palette() == before, \
        "a floating window re-themed the whole application"


def test_palette_push_does_not_change_the_global_colour_scheme(floating, qapp):
    hints = qapp.styleHints()
    if not hasattr(hints, "colorScheme"):
        pytest.skip("QStyleHints.colorScheme is unavailable on this Qt build")

    emissions = []
    hints.colorSchemeChanged.connect(emissions.append)
    try:
        before = hints.colorScheme()
        floating._apply_dock_palette_to_window()
        qapp.processEvents()
        assert hints.colorScheme() == before
        assert emissions == [], \
            f"the global colour scheme was changed {len(emissions)} time(s)"
    finally:
        hints.colorSchemeChanged.disconnect(emissions.append)


def test_palette_push_still_sets_the_windows_own_palette(floating, qapp):
    from lace.dock_theme import build_dock_palette, resolve_dock_colors

    floating._apply_dock_palette_to_window()
    qapp.processEvents()
    expected = build_dock_palette(is_panel=False, colors=resolve_dock_colors())
    assert floating.palette().color(floating.backgroundRole()) == \
        expected.color(floating.backgroundRole())
