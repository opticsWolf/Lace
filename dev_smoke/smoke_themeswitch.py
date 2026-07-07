import sys, logging
logging.disable(logging.CRITICAL)
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
from demo_app import DemoMainWindow
from lace.dock_style_manager import apply_dock_theme
from lace.dock_custom_theme import DOCK_THEMES
win = DemoMainWindow()
win.show()
for name in DOCK_THEMES:
    ok = apply_dock_theme(name)
    app.processEvents()
    assert ok, name
print("THEME SWITCH OK across", len(DOCK_THEMES), "themes")
