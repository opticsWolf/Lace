"""Corner clip smoke: the demo under each ``corner_clip`` mode, one frame each.

Checks per mode: every docked DockWidget's margins (grown under ``inset``,
the theme's own otherwise), that ``cap`` alone paints a cap, and that no
docked content carries a mask. Fails on any Qt warning.
"""
import json
import logging
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
logging.disable(logging.CRITICAL)

from PySide6.QtCore import QtMsgType, qInstallMessageHandler
from PySide6.QtWidgets import QApplication

warnings = []
OFFSCREEN_NOISE = ("This plugin does not support", "QFontDatabase: Cannot find font directory")


def _handler(kind, context, message):
    if kind in (QtMsgType.QtDebugMsg, QtMsgType.QtInfoMsg):
        return
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen" and message.startswith(OFFSCREEN_NOISE):
        return
    warnings.append(message)


qInstallMessageHandler(_handler)
app = QApplication(sys.argv)

from demos.demo_app import DemoMainWindow
from lace.dock_paint import chrome_content_margin
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_widget import DockWidget
from lace.theme_models import ThemeJson
from tests.theme_sets import FIXTURES

RADIUS, BORDER = 12, 1

demo = DemoMainWindow()
demo.resize(1100, 750)
demo.show()
app.processEvents()

raw = json.loads((FIXTURES / "kilim_midnight_neo.json").read_text(encoding="utf-8"))
raw.update(content_margin=0, corner_radius=RADIUS, border_width=BORDER)
need = chrome_content_margin(BORDER, RADIUS) - BORDER

for mode in ("cap", "inset", "none", "cap"):
    raw["corner_clip"] = mode
    get_dock_style_manager().apply_theme_dict(ThemeJson.model_validate(raw).build_theme_dict())
    for _ in range(4):
        app.processEvents()
    docked = [dw for dw in demo.findChildren(DockWidget)
              if dw.isVisible() and dw.dock_area_widget() is not None and not dw.is_floating()]
    assert docked, "no docked widgets in the demo"
    capped = 0
    for dw in docked:
        m = dw._layout.contentsMargins()
        sides = (m.left(), m.right(), m.bottom())
        if mode == "inset":
            assert min(sides) >= need, (mode, dw, sides, need)
        else:
            assert sides == (0, 0, 0), (mode, dw, sides)
        target = dw._scroll_area or dw.widget()
        assert target is None or target.mask().isEmpty(), (mode, dw, "masked")
        capped += dw._cap_shape() is not None
    assert (capped > 0) == (mode == "cap"), (mode, capped)
    img = demo.grab().toImage()
    assert not img.isNull(), mode
    print(f"CORNER CLIP {mode:5} OK: {len(docked)} docked widgets, {capped} capped")

assert not warnings, "Qt warnings:\n  " + "\n  ".join(dict.fromkeys(warnings))
print("CORNER CLIP SMOKE OK")
