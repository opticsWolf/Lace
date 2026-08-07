"""Smoke test for DockWidgetFeature.movable wiring.
"""
import sys
import os
import logging

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

logging.disable(logging.CRITICAL)
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import QPoint
app = QApplication(sys.argv)
from demos.demo_app import DemoMainWindow
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea, DockWidgetFeature, DragState

win = DemoMainWindow()
win.show()
app.processEvents()

dm = win.dock_manager

# 1. Create a movable widget and verify property values
w_movable = DockWidget("Movable Smoke Widget")
w_movable.set_features(DockWidgetFeature.all_features)
area_m = dm.add_dock_widget(DockWidgetArea.left, w_movable)
assert w_movable.features() & DockWidgetFeature.movable, "w_movable should have movable flag"
assert area_m.movable is True, "area_m.movable should be True"

# Check tab property
tab_m = area_m._tab_bar().tab(area_m._tab_bar().count() - 1)
assert tab_m._movable is True, "tab_m._movable should be True"

# 2. Create a non-movable widget and verify property values
w_immovable = DockWidget("Immovable Smoke Widget")
features_no_move = DockWidgetFeature.all_features & ~DockWidgetFeature.movable
w_immovable.set_features(features_no_move)
area_i = dm.add_dock_widget(DockWidgetArea.right, w_immovable)
assert not (w_immovable.features() & DockWidgetFeature.movable), "w_immovable should not have movable flag"
assert area_i.movable is False, "area_i.movable should be False"

tab_i = area_i._tab_bar().tab(area_i._tab_bar().count() - 1)
assert tab_i._movable is False, "tab_i._movable should be False"

# 3. Verify title bar blocks _start_floating when dragging if not movable
title_bar_i = area_i._title_bar
assert title_bar_i._start_floating(DragState.floating_widget) is False, "_start_floating must return False when dragging an immovable area"

# 4. Verify floating container reports _is_movable properly
from lace.floating_dock_container import FloatingDockContainer
fc_i = FloatingDockContainer(dock_area=area_i)
assert fc_i._is_movable() is False, "FloatingDockContainer containing immovable area must return _is_movable() == False"

# 5. Verify moving an immovable pinned widget between sidebars is blocked
sm = dm.sidebar_manager
sm.pin_widget(w_immovable, area=DockWidgetArea.right)
app.processEvents()
assert sm.is_pinned(w_immovable), "w_immovable should be pinned to right sidebar"
sm.move_widget_to_area(w_immovable, DockWidgetArea.left)
app.processEvents()
# 6. Verify dragging an immovable tab button from the sidebar does not trigger floating/unpinning
tab_btn_immovable = sm._sidebars[DockWidgetArea.right]._widget_map[w_immovable]
sm._drag_controller.on_tab_drag_started(tab_btn_immovable)
app.processEvents()
assert sm.is_pinned(w_immovable), "w_immovable must remain pinned when tab drag is attempted without movable flag"
assert not w_immovable.is_floating(), "w_immovable must not detach to floating when dragged from sidebar tab"

# 7. Verify dragging the slide-out panel title bar for immovable widget does not trigger detach_requested
detached_emitted = []
sm._overlay._title_bar.detach_requested.connect(lambda w: detached_emitted.append(w))
sm._overlay._title_bar.set_widget(w_immovable)
sm._overlay._title_bar._on_drag_started(QPoint(10, 10))
assert len(detached_emitted) == 0, "SideBarTitleBar must not emit detach_requested on drag when widget is immovable"

print("SMOKE MOVABLE OK")
