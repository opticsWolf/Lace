"""lace.dialogs smoke: every helper under each theme, one grab each.

For each theme (LACE_TEST_THEMES, see tests/theme_sets.py) every helper is
opened over a LaceStyle app, grabbed while its modal loop runs, then
cancelled. Checks: the host is a FramelessLaceDialog, its title bar paints
title_bar_colors().background (composited over the dialog), and the helper
returns its cancel value. Fails on any Qt warning.
"""
import logging
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
logging.disable(logging.CRITICAL)

from PySide6.QtCore import QtMsgType, QTimer, qInstallMessageHandler
from PySide6.QtGui import QColor
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

from lace import LaceStyle, dialogs
from lace.dock_style_manager import get_dock_style_manager
from lace.frameless_dialog import FramelessLaceDialog
from lace.title_bar_colors import title_bar_colors
from tests import theme_sets

app.setStyle(LaceStyle())
SB = dialogs.StandardButton

HELPERS = {
    "information": (lambda: dialogs.information(None, "Info", "Saved."), SB.Ok),
    "question": (lambda: dialogs.question(None, "Close", "Discard changes?"), SB.No),
    "warning": (lambda: dialogs.warning(None, "Warn", "Low disk.",
                                        SB.Ok | SB.Cancel), SB.Cancel),
    "critical": (lambda: dialogs.critical(None, "Error", "Failed."), SB.Ok),
    "about": (lambda: dialogs.about(None, "About", "<b>Lace</b>"), None),
    "get_text": (lambda: dialogs.get_text(None, "Rename", "Name:", text="x")[1], False),
    "get_item": (lambda: dialogs.get_item(None, "Pick", "Item:", ["a", "b"])[1], False),
    "get_int": (lambda: dialogs.get_int(None, "Count", "N:", 3)[1], False),
    "get_double": (lambda: dialogs.get_double(None, "Scale", "X:", 1.5)[1], False),
    "get_color": (lambda: dialogs.get_color(QColor("red"), None, "Colour").isValid(), False),
    "get_open_file_name": (lambda: dialogs.get_open_file_name(
        None, "Open", ROOT, native=False), ("", "")),
}

failures = []


def _close_enough(a: QColor, b: QColor, tol: int = 2) -> bool:
    return all(abs(x - y) <= tol for x, y in zip(a.getRgb()[:3], b.getRgb()[:3]))


def check(theme, name):
    seen = {}

    def inspect():
        host = QApplication.activeModalWidget()
        seen["host"] = host
        if not isinstance(host, FramelessLaceDialog):
            host.close()
            return
        app.processEvents()
        bar = host.titleBar
        img = host.grab().toImage()
        # Empty bar between the title and the close button.
        x = bar.x() + bar.width() - bar.closeBtn.width() - 6
        y = bar.y() + 2
        seen["pixel"] = img.pixelColor(int(x * img.devicePixelRatio()),
                                       int(y * img.devicePixelRatio()))
        seen["expected"] = title_bar_colors().opaque_background(
            host.palette().window().color())
        host.reject()

    QTimer.singleShot(0, inspect)
    fn, cancelled = HELPERS[name]
    result = fn()
    host = seen.get("host")
    if not isinstance(host, FramelessLaceDialog):
        failures.append(f"{theme}/{name}: host is {type(host).__name__}")
        return
    if result != cancelled:
        failures.append(f"{theme}/{name}: cancel returned {result!r}, want {cancelled!r}")
    if not _close_enough(seen["pixel"], seen["expected"]):
        failures.append(f"{theme}/{name}: title bar {seen['pixel'].name()}, "
                        f"want {seen['expected'].name()}")


themes = theme_sets.from_env()
for theme in themes:
    get_dock_style_manager().apply_theme_dict(theme_sets.load(theme))
    app.processEvents()
    for name in HELPERS:
        check(theme, name)
    QApplication.sendPostedEvents(None, 52)

print(f"{len(themes)} themes x {len(HELPERS)} helpers")
if warnings:
    failures.extend(f"Qt warning: {w}" for w in warnings)
if failures:
    for f in failures:
        print("FAIL", f)
    sys.exit(1)
print("lace.dialogs smoke OK")
