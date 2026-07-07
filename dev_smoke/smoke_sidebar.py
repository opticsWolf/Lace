import sys, logging
logging.disable(logging.CRITICAL)
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
from demo_app import DemoMainWindow
from lace.enums import DockWidgetArea

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

print("SIDEBAR SMOKE OK")
