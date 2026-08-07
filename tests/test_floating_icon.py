# -*- coding: utf-8 -*-
"""Floating-window icon tests — DockManager.set_floating_window_icon.

Covers: dedicated icon applied to new floating windows (native + frameless),
live update of already-open windows, and the fallback when the icon is
cleared (application / root-window icon resolution).
"""

from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import QMainWindow

from lace import DockManager, DockWidget, DockWidgetArea, TitleBarMode
from lace.floating_dock_container import FloatingDockContainer


def _solid_icon(color: str) -> QIcon:
    pm = QPixmap(16, 16)
    pm.fill(QColor(color))
    return QIcon(pm)


def _top_left(icon: QIcon) -> str:
    return icon.pixmap(16, 16).toImage().pixelColor(0, 0).name()


def test_floating_window_icon_applies_to_new_windows(qapp):
    win = QMainWindow()
    dm = DockManager(win)
    dm.set_floating_window_icon(_solid_icon("#ff00ff"))
    fc = FloatingDockContainer(dock_manager=dm)
    fc.show()
    qapp.processEvents()
    assert _top_left(fc.windowIcon()) == "#ff00ff"
    fc.close()


def test_set_floating_window_icon_updates_existing_windows(qapp):
    win = QMainWindow()
    dm = DockManager(win)
    fc = FloatingDockContainer(dock_manager=dm)
    fc.show()
    qapp.processEvents()
    dm.set_floating_window_icon(_solid_icon("#00ff00"))
    assert _top_left(fc.windowIcon()) == "#00ff00"
    # Clearing reverts to the fallback (application / root icon), not the
    # dedicated magenta.
    dm.set_floating_window_icon(None)
    fc2 = FloatingDockContainer(dock_manager=dm)
    assert _top_left(fc2.windowIcon()) != "#00ff00"
    fc.close()
    fc2.close()


def test_frameless_floating_window_uses_dedicated_icon(qapp):
    from lace.floating_dock_container_frameless import (
        FloatingDockContainer as FramelessFloatingDockContainer,
    )

    win = QMainWindow()
    dm = DockManager(win)
    dm.title_bar_mode = TitleBarMode.custom
    dm.set_floating_window_icon(_solid_icon("#0000ff"))
    fc = FramelessFloatingDockContainer(dock_manager=dm)
    fc.show()
    qapp.processEvents()
    assert _top_left(fc.windowIcon()) == "#0000ff"
    fc.close()


def test_floating_icon_priority_over_app_icon(qapp):
    """The dedicated floating icon wins even when the app icon is set."""
    win = QMainWindow()
    dm = DockManager(win)
    qapp.setWindowIcon(_solid_icon("#111111"))
    dm.set_floating_window_icon(_solid_icon("#222222"))
    fc = FloatingDockContainer(dock_manager=dm)
    fc.show()
    qapp.processEvents()
    assert _top_left(fc.windowIcon()) == "#222222"
    fc.close()
