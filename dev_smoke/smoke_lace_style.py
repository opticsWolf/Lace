"""LaceStyle smoke: the demo and the style showcase under every theme of the
selected stage, one frame each, failing on any Qt warning.

Also switches the style tokens live (scrollbar modes, contrast levels, radius,
focus width) and opens the paths only a running app takes: a menu popup, a
tooltip, the busy progress animation and keyboard focus.
"""
import logging
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "dev_smoke", "interactive"))
logging.disable(logging.CRITICAL)

from PySide6.QtCore import QDeadlineTimer, QPoint, Qt, QtMsgType, qInstallMessageHandler
from PySide6.QtWidgets import QApplication, QProgressBar, QPushButton, QToolTip

warnings = []

#: Messages the offscreen platform itself emits, with the reason; anything
#: else fails the check.
OFFSCREEN_NOISE = (
    "This plugin does not support",       # masks, raise, keyboard grab, size hints
    "QFontDatabase: Cannot find font directory",
    # No fonts offscreen, so QFontInfo reports point size -1 and Fusion's menu
    # item scales it; stock Fusion does the same, and native runs are clean.
    "QFont::setPointSizeF: Point size <= 0",
)


def _handler(kind, context, message):
    if kind in (QtMsgType.QtDebugMsg, QtMsgType.QtInfoMsg):
        return
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen" and message.startswith(OFFSCREEN_NOISE):
        return
    warnings.append(message)


qInstallMessageHandler(_handler)
app = QApplication(sys.argv)

from demos.demo_app import DemoMainWindow
from lace.lace_style import CONTRAST_LEVELS, SCROLLBAR_MODES, LaceStyle
from style_showcase import Showcase, apply_theme
from tests.theme_sets import from_env

style = LaceStyle()
app.setStyle(style)
demo = DemoMainWindow()
demo.show()
show = Showcase(style)
show.show()
zoomed = Showcase(style, zoom=True)
zoomed.show()
zoomed._zoom(4.0)
app.processEvents()


def _frame(label):
    for win in (demo, show, zoomed):
        img = win.grab().toImage()
        assert not img.isNull(), label
        # A painted window has more than a couple of colours.
        colours = {img.pixel(x, y) for x in range(0, img.width(), 7) for y in range(0, img.height(), 7)}
        assert len(colours) > 4, (label, win.windowTitle(), len(colours))


themes = from_env()
for key in themes:
    apply_theme(app, key)
    app.processEvents()
    _frame(key)
print("LACE STYLE FRAMES OK across", len(themes), "themes")

# Tokens, switched live on one theme.
apply_theme(app, themes[0])
n = 0
for mode in SCROLLBAR_MODES:
    for level in CONTRAST_LEVELS:
        show._set("scrollbar", mode)
        show._set("contrast", level)
        app.processEvents()
        _frame(f"{mode}/{level}")
        n += 1
for radius, width in ((0, 0.0), (8, 3.0), (4, 2.0)):
    style.set_tokens(control_radius=radius, focus_width=width)
    app.processEvents()
    _frame(f"radius {radius} / focus {width}")
    n += 1
show._set("scrollbar", "thin")
show._set("contrast", "normal")
print("LACE STYLE TOKENS OK across", n, "combinations")

# Paths only a running app takes.
file_menu = show.menuBar().actions()[0].menu()
file_menu.popup(show.mapToGlobal(QPoint(40, 40)))
app.processEvents()
file_menu.setActiveAction(file_menu.actions()[0])
app.processEvents()
assert not file_menu.grab().toImage().isNull()
file_menu.hide()

QToolTip.showText(show.mapToGlobal(QPoint(60, 60)), "A tooltip", show)
# Native tips fade in and take their mask on first paint: give them a moment.
deadline = QDeadlineTimer(2000)
tips = []
while not deadline.hasExpired():
    app.processEvents()
    tips = [w for w in app.allWidgets() if w.metaObject().className() == "QTipLabel" and w.isVisible()]
    if tips and not tips[0].mask().isEmpty():
        break
assert tips, "no tooltip shown"
assert not tips[0].mask().isEmpty(), "tooltip not masked to its rounded shape"
QToolTip.hideText()

busy = next(b for b in show.findChildren(QProgressBar) if b.maximum() == 0)
for _ in range(3):
    busy.repaint()
    app.processEvents()

button = show.findChildren(QPushButton)[0]
button.setFocus(Qt.FocusReason.TabFocusReason)
app.processEvents()
_frame("keyboard focus")
print("LACE STYLE LIVE PATHS OK (menu, tooltip, busy progress, focus)")

assert not warnings, "Qt warnings:\n  " + "\n  ".join(dict.fromkeys(warnings))
print("LACE STYLE SMOKE OK")
