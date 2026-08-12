import sys, logging
import os
# Run directly (python dev_smoke/<name>.py) and sys.path[0] is dev_smoke/,
# so the demos package below would not resolve. run_all.py sets PYTHONPATH
# instead, which is why this only ever broke on direct invocation.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.disable(logging.CRITICAL)
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
from demos.demo_app import DemoMainWindow
from lace.enums import DockWidgetArea, DockWidgetFeature

win = DemoMainWindow(); win.show(); app.processEvents()
dm = win.dock_manager
sm = dm.sidebar_manager
dws = list(dm.dock_widgets_map().values())

# pin -> exercises pin_widget (+ _detach_tab_widget)
dw = dws[0]
sm.pin_widget(dw, area=DockWidgetArea.left)
app.processEvents()
assert sm.is_pinned(dw), "widget should be pinned"

# unpin back to a dock area -> exercises unpin_widget (+ both helpers)
sm.unpin_widget(dw)
app.processEvents()
assert not sm.is_pinned(dw), "widget should be unpinned"
assert dw.dock_area_widget() is not None, "unpinned widget should rejoin a dock area"

# pin another, then unpin into a floating window -> unpin_widget_floating
dw2 = dws[1]
sm.pin_widget(dw2, area=DockWidgetArea.right)
app.processEvents()
assert sm.is_pinned(dw2)
n_before = len(dm.floating_widgets())
sm.unpin_widget_floating(dw2)
app.processEvents()
assert not sm.is_pinned(dw2), "widget should be unpinned after floating"
assert len(dm.floating_widgets()) > n_before, "unpin_floating should create a floating window"

# test unfloatable widget pinned to sidebar (cannot be floated, only unpinned)
unfloatable_dw = dm.dock_widgets_map()["Unfloatable Tool"]
sm.pin_widget(unfloatable_dw, area=DockWidgetArea.left)
app.processEvents()
assert sm.is_pinned(unfloatable_dw)
n_float_before = len(dm.floating_widgets())
sm.unpin_widget_floating(unfloatable_dw)
app.processEvents()
assert sm.is_pinned(unfloatable_dw), "unfloatable widget should NOT be floated/removed from sidebar"
assert len(dm.floating_widgets()) == n_float_before, "no floating window should be created for unfloatable widget"
sm.unpin_widget(unfloatable_dw)
app.processEvents()
assert not sm.is_pinned(unfloatable_dw), "unfloatable widget SHOULD be removable via unpin"

# test permanently locked sidebar widget (created in sidebar, not floatable and not unpinnable)
locked_sidebar_dw = dm.dock_widgets_map()["Locked Sidebar Tool"]
assert sm.is_pinned(locked_sidebar_dw), "locked sidebar widget should start pinned"
sm.unpin_widget_floating(locked_sidebar_dw)
app.processEvents()
assert sm.is_pinned(locked_sidebar_dw), "permanently locked sidebar widget should NOT be floatable"
sm.unpin_widget(locked_sidebar_dw)
app.processEvents()
assert sm.is_pinned(locked_sidebar_dw), "permanently locked sidebar widget should NOT be unpinnable"

# test Right Locked Panel (neither floatable, closable, nor unpinnable)
right_locked_dw = dm.dock_widgets_map()["Right Locked Panel"]
assert sm.is_pinned(right_locked_dw), "right locked panel should start pinned"
sm.unpin_widget_floating(right_locked_dw)
app.processEvents()
assert sm.is_pinned(right_locked_dw), "right locked panel should NOT be floatable"
sm.unpin_widget(right_locked_dw)
app.processEvents()
assert sm.is_pinned(right_locked_dw), "right locked panel should NOT be unpinnable"
assert DockWidgetFeature.closable not in right_locked_dw.features(), "right locked panel should NOT be closable"

# test Right Pinnable Tool (not floatable, but pinnable/unpinnable and closable)
right_pinnable_dw = dm.dock_widgets_map()["Right Pinnable Tool"]
assert sm.is_pinned(right_pinnable_dw), "right pinnable tool should start pinned"
sm.unpin_widget_floating(right_pinnable_dw)
app.processEvents()
assert sm.is_pinned(right_pinnable_dw), "right pinnable tool should NOT be floatable"
sm.unpin_widget(right_pinnable_dw)
app.processEvents()
assert not sm.is_pinned(right_pinnable_dw), "right pinnable tool SHOULD be unpinnable"
sm.pin_widget(right_pinnable_dw, area=DockWidgetArea.right)
app.processEvents()
assert sm.is_pinned(right_pinnable_dw), "right pinnable tool should be re-pinned"

# test closing a sidebar widget hides button without unpinning
right_sidebar = sm._sidebars[DockWidgetArea.right]
pinnable_btn = right_sidebar._widget_map[right_pinnable_dw]
assert pinnable_btn.isVisible(), "tab button should be visible when open"
right_sidebar._close_dock_widget(right_pinnable_dw)
app.processEvents()
assert sm.is_pinned(right_pinnable_dw), "widget should remain pinned when closed"
assert not pinnable_btn.isVisible(), "tab button should be hidden when closed"
right_pinnable_dw.toggle_view(True)
app.processEvents()
assert pinnable_btn.isVisible(), "tab button should be visible when re-opened"

# test close others only closes closable widgets
right_sidebar._close_others(pinnable_btn)
app.processEvents()
locked_btn = right_sidebar._widget_map[right_locked_dw]
assert locked_btn.isVisible(), "non-closable widget should NOT be closed by Close Others"
assert sm.is_pinned(right_locked_dw), "non-closable widget should remain pinned"

# test TabBadgePosition wiring on VerticalTabButton
from lace.sidebar_tab import TabBadgePosition
assert pinnable_btn.badge_position == TabBadgePosition.top_right, "default badge_position should be top_right"
pinnable_btn.set_badge_position(TabBadgePosition.bottom_left)
assert pinnable_btn.badge_position == TabBadgePosition.bottom_left, "badge_position setter should update position"
pinnable_btn.set_badge(5, position=TabBadgePosition.top_left)
assert pinnable_btn.badge_position == TabBadgePosition.top_left, "set_badge should update position when passed"
# exercise _draw_badge across all 4 positions via grab()
for pos in TabBadgePosition:
    pinnable_btn.set_badge_position(pos)
    app.processEvents()
    _ = pinnable_btn.grab()  # verify no paint exceptions

# exercise string character badges
pinnable_btn.set_badge("!")
app.processEvents()
_ = pinnable_btn.grab()
pinnable_btn.set_badge("?")
app.processEvents()
_ = pinnable_btn.grab()

print("SIDEBAR SMOKE OK")


