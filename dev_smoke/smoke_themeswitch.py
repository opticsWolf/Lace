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
from lace.dock_style_manager import apply_dock_theme
from lace.dock_custom_theme import DOCK_THEMES
win = DemoMainWindow()
win.show()
for name in DOCK_THEMES:
    ok = apply_dock_theme(name)
    app.processEvents()
    assert ok, name
print("THEME SWITCH OK across", len(DOCK_THEMES), "themes")
