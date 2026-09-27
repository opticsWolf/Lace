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

# REGULAR x the three contrast levels, switched live on the same window.
from dataclasses import replace
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import build_theme
from lace.theme_contrast import CONTRAST_LEVELS
from tests.theme_sets import REGULAR, FIXTURES
from lace.theme_models import ThemeJson
from lace.dock_custom_theme import THEME_SPECS
sm = get_dock_style_manager()
n = 0
for key in REGULAR:
    spec = (ThemeJson.load(FIXTURES / f"{key}.json").to_theme_spec() if key.startswith("kilim_")
            else THEME_SPECS[key])
    for level in CONTRAST_LEVELS:
        assert sm.apply_theme_dict(build_theme(replace(spec, contrast=level))), (key, level)
        app.processEvents()
        n += 1
print("CONTRAST SWITCH OK across", n, "theme x level combinations")
