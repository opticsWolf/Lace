"""Interactive double-click diagnostic — FINAL verification.

Polls the window state LIVE while the user interacts (so maximize/restore
transitions triggered by real double-clicks are captured) and logs every
mouse event on the title bars + mouseDoubleClickEvent firing.

  Phase 1  baseline  : double-click the MAIN WINDOW title bar
  Phase 2  create    : drag the 'Standard Editor' tab out (make a float)
  Phase 3  main dbl  : double-click the MAIN WINDOW title bar again
  Phase 4  float dbl : double-click the FLOATING WINDOW's title bar

Report written to dev_smoke/dblclick_report.txt
"""
import sys, os, time, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.disable(logging.CRITICAL)

from PySide6.QtWidgets import (QApplication, QWidget, QMessageBox,
                               QVBoxLayout, QLabel, QPushButton)
from PySide6.QtCore import QTimer, QEvent, QObject, Qt
app = QApplication(sys.argv)

from demo_app_custom_titlebar import DemoMainWindow
from lace.enums import DragState

REPORT = []
def log(*parts):
    line = " ".join(str(p) for p in parts)
    print(line, flush=True)
    REPORT.append(line)

class Trace(QObject):
    def eventFilter(self, watched, event):
        t = event.type()
        if t in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease,
                 QEvent.MouseButtonDblClick):
            log(f"      [{watched.__class__.__name__}] {str(t).split('.')[-1]}")
        return super().eventFilter(watched, event)

from qframelesswindow.titlebar import StandardTitleBar
class LoggingTitleBar(StandardTitleBar):
    def mouseDoubleClickEvent(self, event):
        log(f"      >>> mouseDoubleClickEvent FIRED")
        super().mouseDoubleClickEvent(event)

win = DemoMainWindow()
win.setTitleBar(LoggingTitleBar(win))
win.move(60, 60)
win.show()
app.processEvents()

tr = Trace()
win.titleBar.installEventFilter(tr)
for ch in win.titleBar.findChildren(QWidget):
    ch.installEventFilter(tr)

class Guide(QWidget):
    def __init__(self, title, text, target):
        super().__init__()
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        lay = QVBoxLayout(self)
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        lay.addWidget(self.label)
        self.btn = QPushButton("Continue")
        lay.addWidget(self.btn)
        self.resize(440, 170)
        self.btn.clicked.connect(self._on_continue)
        self._done = False
        self.target = target
        self.transitions = []
        self._prev = None

    def _on_continue(self):
        self._done = True

    def wait(self):
        self._prev = self.target.isMaximized() if self.target else None
        self.transitions = [self._prev] if self._prev is not None else []
        while not self._done:
            app.processEvents()
            if self.target is not None:
                now = self.target.isMaximized()
                if now != self._prev:
                    self.transitions.append(now)
                    self._prev = now
            time.sleep(0.02)

def ask(title, text, target, label):
    g = Guide(title, text, target)
    g.move(win.x() + win.width() + 20, win.y())
    g.show(); g.raise_(); g.activateWindow()
    g.wait()
    g.close()
    trans = []
    prev = None
    for s in g.transitions:
        if s != prev:
            trans.append(s)
            prev = s
    ever = any(s for s in trans[1:])
    log(f"  {label}: transitions={trans} ever_maximized={ever}")
    return ever

log("=" * 60)
log("Lace double-click diagnostic (FINAL - synchronous toggle fix)")
log("=" * 60)

base = ask("Phase 1 - baseline",
           "Double-click the MAIN WINDOW's title bar (maximize, restore).\n"
           "Press Continue when done.", win, "Phase 1 (baseline) main")

before = len(win.dock_manager.floating_widgets())
ask("Phase 2 - create float",
    "DRAG the 'Standard Editor' tab out and release it on the desktop.\n"
    "Press Continue when done.", None)
floats = win.dock_manager.floating_widgets()
n_float = len(floats) - before
log(f"Phase 2: floats created: {n_float}")
for f in floats:
    log(f"    float {id(f)%10000}: state={f._dragging_state} "
        f"filter={f._frameless_drag_filter} grabber={QWidget.mouseGrabber()}")

main_after = ask("Phase 3 - main dblclick (float present)",
                 "Double-click the MAIN WINDOW's title bar (should "
                 "MAXIMIZE, then restore).\nPress Continue when done.",
                 win, "Phase 3 (main dblclick w/ float)")

float_ever = False
if floats:
    flt = floats[-1]
    ftr = Trace()
    flt.titleBar.installEventFilter(ftr)
    for ch in flt.titleBar.findChildren(QWidget):
        ch.installEventFilter(ftr)
    float_ever = ask("Phase 4 - float dblclick",
                     "Double-click the FLOATING WINDOW's title bar "
                     "(should MAXIMIZE, then restore).\nPress Continue "
                     "when done.", flt, f"Phase 4 (float dblclick)")
else:
    log("Phase 4 skipped: no float created")

summary = [
    f"Phase 1 baseline main dblclick : {'OK' if base else 'FAIL'}",
    f"Phase 2 float created by drag  : {'OK' if n_float >= 1 else 'FAIL'}",
    f"Phase 3 main dblclick w/ float : {'OK' if main_after else 'FAIL'}",
]
if floats:
    summary.append(f"Phase 4 float dblclick         : "
                   f"{'OK' if float_ever else 'FAIL'}")
log("")
log("-" * 60)
for s in summary:
    log("  " + s)
ok = base and n_float >= 1 and main_after and (not floats or float_ever)
log("OVERALL: " + ("PASS" if ok else "FAIL"))
log("=" * 60)

report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "dblclick_report.txt")
with open(report_path, "w", encoding="utf-8") as fh:
    fh.write("\n".join(REPORT))

msg = QMessageBox()
msg.setWindowTitle("Diagnostic finished")
msg.setText("Done.\n\n" + "\n".join(summary) +
            "\n\nFull report written to:\n" + report_path)
msg.exec()
app.quit()
