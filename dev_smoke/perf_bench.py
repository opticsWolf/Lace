"""Performance check (plan Phase 6): theme switching and a resize paint loop.

    <python> dev_smoke/perf_bench.py [--root TREE] [--repeat N]

Imports Lace from ``--root`` (default: this checkout), so the same script
times an older tree checked out elsewhere, e.g. the 0.7.6 baseline:

    git worktree add ../lace-076 f8f5358
    <python> dev_smoke/perf_bench.py --root ../lace-076

Measures, best of ``--repeat`` runs (the minimum is the least noisy):
- **switch**: apply every preset once, each followed by one event pass, so
  every subscribed widget restyles and repaints;
- **resize**: a 12-area layout resized 100 times, painting each frame.
Uses only API that 0.7.6 already had.
"""

import argparse
import os
import sys
import time

ap = argparse.ArgumentParser()
ap.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ap.add_argument("--repeat", type=int, default=5)
ap.add_argument("--lace-style", action="store_true",
                help="paint with LaceStyle (0.8+) instead of the platform style")
args = ap.parse_args()
sys.path.insert(0, os.path.abspath(args.root))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import logging  # noqa: E402

logging.disable(logging.CRITICAL)

from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QTextEdit  # noqa: E402

app = QApplication(sys.argv)

import lace  # noqa: E402
from lace import DockManager, DockWidget  # noqa: E402
from lace.dock_custom_theme import DOCK_THEMES  # noqa: E402
from lace.dock_style_manager import get_dock_style_manager  # noqa: E402
from lace.enums import DockWidgetArea  # noqa: E402

AREAS = 12


def build():
    win = QMainWindow()
    win.resize(1200, 800)
    dm = DockManager(win)
    placements = [DockWidgetArea.left, DockWidgetArea.right, DockWidgetArea.top,
                  DockWidgetArea.bottom]
    area = None
    for i in range(AREAS):
        dw = DockWidget(f"Panel {i}", win)
        dw.setObjectName(f"panel_{i}")
        dw.set_widget(QTextEdit(f"panel {i}\n" * 30) if i % 2 else QLabel(f"panel {i}"))
        area = dm.add_dock_widget(placements[i % 4] if i else DockWidgetArea.center, dw,
                                  area if i % 3 == 0 and i else None)
    win.show()
    for _ in range(5):
        app.processEvents()
    return win


def switch(win):
    sm = get_dock_style_manager()
    names = list(DOCK_THEMES)
    t0 = time.perf_counter()
    for name in names:
        sm.apply_theme_dict(DOCK_THEMES[name])
        app.processEvents()
        win.repaint()
    return time.perf_counter() - t0, len(names)


def resize(win):
    t0 = time.perf_counter()
    for i in range(100):
        win.resize(1000 + (i % 20) * 10, 700 + (i % 10) * 10)
        app.processEvents()
        win.repaint()
    return time.perf_counter() - t0


if args.lace_style:
    from lace.dock_theme_bridge import DockThemeBridge  # noqa: E402
    bridge = DockThemeBridge()                           # LaceStyle on the app
win = build()
get_dock_style_manager().apply_theme_dict(DOCK_THEMES["dark"])
app.processEvents()
switch(win)                                    # warm caches and imports
s = min(switch(win)[0] for _ in range(args.repeat))
n = switch(win)[1]
r = min(resize(win) for _ in range(args.repeat))
print(f"lace {lace.__version__} from {os.path.abspath(args.root)}"
      + (" (LaceStyle)" if args.lace_style else ""))
print(f"switch  {n} themes  {s * 1000:8.1f} ms  ({s * 1000 / n:.2f} ms per theme)")
print(f"resize  100 frames  {r * 1000:8.1f} ms  ({r * 10:.2f} ms per frame)")
win.close()
