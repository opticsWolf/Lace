"""Smoke test for TitleBarButton.pin wiring and pin button behavior.
"""
import sys
import os
import logging

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

logging.disable(logging.CRITICAL)
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
from demos.demo_app import DemoMainWindow
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea, DockWidgetFeature, TitleBarButton, DockFlags

win = DemoMainWindow()
win.show()
app.processEvents()

dm = win.dock_manager
dm.config_flags |= DockFlags.dock_area_has_pin_button | DockFlags.pinnable_tabs

# 1. Add a pinnable widget and check TitleBarButton.pin
w_pinnable = DockWidget("Pinnable Smoke Widget")
w_pinnable.set_features(DockWidgetFeature.all_features)
area_p = dm.add_dock_widget(DockWidgetArea.left, w_pinnable)
app.processEvents()

pin_btn = area_p.title_bar_button(TitleBarButton.pin)
assert pin_btn is not None, "pin_btn should exist on area title bar"
assert pin_btn.isEnabled() is True, "pin_btn should be enabled for a pinnable widget"

# 2. Test non-pinnable widget disables or hides pin button depending on active tab
w_unpinnable = DockWidget("Unpinnable Smoke Widget")
w_unpinnable.set_features(DockWidgetFeature.all_features & ~DockWidgetFeature.pinnable)
area_u = dm.add_dock_widget(DockWidgetArea.right, w_unpinnable)
app.processEvents()

pin_btn_u = area_u.title_bar_button(TitleBarButton.pin)
assert pin_btn_u is not None, "pin_btn_u should exist"
assert pin_btn_u.isEnabled() is False, "pin_btn_u should be disabled when current widget is not pinnable"

# 3. Test pin button clicked triggers pinning via sidebar manager
# Switch back to pinnable widget area
area_p._title_bar.on_pin_button_clicked()
app.processEvents()

assert dm.sidebar_manager.is_pinned(w_pinnable) is True, "w_pinnable should be pinned after clicking pin button"

# 4. Verify unpinning brings the widget back out of the sidebar
from lace.dock_menu import menu_default_unpin
menu_default_unpin(w_pinnable, area=None, manager=dm)
app.processEvents()
assert dm.sidebar_manager.is_pinned(w_pinnable) is False, "w_pinnable should be unpinned after calling menu_default_unpin"

print("SMOKE PIN BUTTON OK")
