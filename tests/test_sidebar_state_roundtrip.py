# -*- coding: utf-8 -*-
"""Sidebar state travels with the dock layout.

DockManager.save_state() stores the sidebars under "sidebars": which widget
is pinned where, each overlay's size, and the sidebar settings.
restore_state() must bring all of that back in a fresh manager.
"""

import json

import pytest
from PySide6.QtWidgets import QLabel, QMainWindow

from lace.dock_manager import DockManager
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea, DockWidgetFeature
from lace.layout_serializer import SidebarState


@pytest.fixture
def build(qapp):
    windows = []

    def _build():
        win = QMainWindow()
        win.resize(1000, 700)
        manager = DockManager(win)
        widgets = {}
        for name, area in (("A", DockWidgetArea.center),
                           ("B", DockWidgetArea.right),
                           ("C", DockWidgetArea.bottom)):
            widget = DockWidget(name, win)
            widget.setObjectName(name)
            widget.set_widget(QLabel(name))
            widget.set_features(DockWidgetFeature.all_features)
            manager.add_dock_widget(area, widget)
            widgets[name] = widget
        win.show()
        qapp.processEvents()
        windows.append(win)
        return manager, widgets

    yield _build
    for win in windows:
        win.close()
        win.deleteLater()
    qapp.processEvents()


def test_sidebar_state_survives_save_and_restore(qapp, build):
    manager, widgets = build()
    sidebars = manager.sidebar_manager
    sidebars.pin_widget(widgets["B"], area=DockWidgetArea.left)
    sidebars._state_manager.save_state("B", SidebarState(width=333, height=222))
    sidebars._keep_open = True
    qapp.processEvents()

    saved = manager.save_state()
    state = json.loads(saved)["sidebars"]
    assert state["pinned_widgets"] == {"B": "left"}
    assert state["overlay_sizes"]["B"]["width"] == 333
    assert state["settings"]["keep_open"] is True

    manager2, widgets2 = build()
    assert manager2.restore_state(saved)
    qapp.processEvents()

    sidebars2 = manager2.sidebar_manager
    assert widgets2["B"] in sidebars2._pinned
    assert sidebars2._pinned[widgets2["B"]].area == DockWidgetArea.left
    restored = sidebars2._state_manager.load_state("B")
    assert (restored.width, restored.height) == (333, 222)
    assert sidebars2._keep_open is True
