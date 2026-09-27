"""Screenshots of the frameless demo across themes and UI states.

Standard set (--themes stage, default full; see tests/theme_sets.py): for each theme a FRESH main window is built
and a RANDOMLY SELECTED dock widget is floated:
  main_<theme>.png   - main window (custom title bar, menu bar, splitters)
                       with a random widget floated out
  float_<theme>.png  - that random widget as a frameless floating container

Special states (screen grabs show real desktop layering/shadows):
  composite_<theme>.png - floating window in FRONT of the main window
  sidebar_<theme>.png   - right sidebar expanded (a widget pinned to it)
  hover_<theme>.png     - a dock area actively hovered (drop overlay + preview)
"""
import sys, os, time, random, logging, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.disable(logging.CRITICAL)

parser = argparse.ArgumentParser()
parser.add_argument("--themes", default="full",
                    choices=("quick", "regular", "full", "all", "auto"))
parser.add_argument("--out", default=None,
                    help="output directory (default: screenshots/)")
parser.add_argument("--standard-only", action="store_true",
                    help="skip the screen-grab special states")
args, qt_args = parser.parse_known_args()
# Same widget floated on every run, so before/after sets compare like for like.
random.seed(0)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QPoint, Qt
from PySide6.QtGui import QCursor
app = QApplication(sys.argv[:1] + qt_args)

from demos.demo_app_custom_titlebar import DemoMainWindow
from lace.floating_dock_container_frameless import (
    FramelessFloatingDockContainer)
from lace.dock_style_manager import get_dock_style_manager
from tests import theme_sets
from lace.enums import DockWidgetArea, DockWidgetFeature

THEMES = theme_sets.resolve(args.themes)
COMPOSITE_THEMES = ["cyberpunk_neon", "kilim_light_neo"]
SIDEBAR_THEMES = ["kilim_dark", "slate_amber"]
HOVER_THEMES = ["cyberpunk_neon", "kilim_midnight"]

OUT = args.out or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "screenshots")
os.makedirs(OUT, exist_ok=True)

def settle(ms=450):
    for _ in range(ms // 30):
        app.processEvents()
        time.sleep(0.03)

def set_theme(name):
    get_dock_style_manager().apply_theme_dict(theme_sets.load(name))
    app.processEvents()
    settle(450)

def screen_grab(widgets, margin=10):
    """Grab the desktop region covered by *widgets* (real layering, shadows)."""
    screen = QApplication.primaryScreen()
    img = screen.grabWindow(0)
    dpr = win.devicePixelRatioF()
    union = None
    for w in widgets:
        g = w.frameGeometry()
        union = g if union is None else union.united(g)
    x = max(0, int((union.x() - margin) * dpr))
    y = max(0, int((union.y() - margin) * dpr))
    w = min(img.width() - x, int((union.width() + 2 * margin) * dpr))
    h = min(img.height() - y, int((union.height() + 2 * margin) * dpr))
    return img.copy(x, y, w, h)

def pick_widget(win, pool_filter=None, exclude=()):
    from lace.enums import DockWidgetFeature
    ws = [w for w in win.dock_manager.dock_widgets_map().values()
          if w not in exclude]
    if pool_filter:
        ws = [w for w in ws if pool_filter(w)]
    return random.choice(ws) if ws else None

def save(img, name):
    path = os.path.join(OUT, name)
    img.save(path)
    print(f"  saved {name} ({img.width()}x{img.height()})", flush=True)

# ═══ Part A: fresh window per theme + a RANDOM widget floated ═════════
for theme in THEMES:
    print(f"[standard] {theme}", flush=True)
    w = DemoMainWindow()
    w.move(40, 40)
    w.show()
    app.processEvents()
    set_theme(theme)
    dw = pick_widget(
        w, lambda x: bool(x.features() & DockWidgetFeature.floatable))
    print(f"  floating random widget: {dw.windowTitle()}", flush=True)
    flt = FramelessFloatingDockContainer(dock_widget=dw)
    flt.move(w.x() + w.width() + 40, w.y() + 60)
    flt.show()
    app.processEvents()
    settle(500)
    save(w.grab(), f"main_{theme}.png")
    save(flt.grab(), f"float_{theme}.png")
    flt.close()
    w.close()
    app.processEvents()
    settle(150)

if args.standard_only:
    print("DONE ->", OUT, flush=True)
    sys.exit(0)

# ═══ special states: one dedicated window ═════════════════════════════
win = DemoMainWindow()
win.move(40, 40)
win.show()
app.processEvents()

# ═══ Part B: floating window in FRONT of the main window ═════════════
floated_widget = pick_widget(
    win, lambda x: bool(x.features() & DockWidgetFeature.floatable))
flt = FramelessFloatingDockContainer(dock_widget=floated_widget)
flt.move(win.x() + win.width() + 40, win.y() + 60)
flt.show()
app.processEvents()
settle()
for theme in COMPOSITE_THEMES:
    print(f"[composite] {theme}", flush=True)
    set_theme(theme)
    flt.move(win.x() + win.width() // 2 - 60, win.y() + 90)
    flt.raise_()
    flt.activateWindow()
    app.processEvents()
    settle(600)
    save(screen_grab([win, flt]), f"composite_{theme}.png")

# ═══ Part C: sidebar expanded ════════════════════════════════════════
sm = win.dock_manager.sidebar_manager
pinned = None
for theme in SIDEBAR_THEMES:
    print(f"[sidebar] {theme}", flush=True)
    set_theme(theme)
    if pinned is None:
        pinned = pick_widget(
            win,
            lambda x: bool(x.features() & DockWidgetFeature.pinnable),
            exclude=(floated_widget,))
        if pinned:
            sm.pin_widget(pinned, area=DockWidgetArea.right)
            app.processEvents()
            settle(300)
    sm.toggle_sidebar(DockWidgetArea.right)
    app.processEvents()
    settle(500)
    save(screen_grab([win]), f"sidebar_{theme}.png")
    sm.close_overlay()
    app.processEvents()
    settle(200)

if pinned is not None:
    try:
        sm.unpin_widget(pinned, area=DockWidgetArea.right)
    except Exception:
        pass
    app.processEvents()
    settle(300)

# ═══ Part D: actively hovered dock (drop overlay + preview) ══════════
dm = win.dock_manager
root = dm._root
for theme in HOVER_THEMES:
    print(f"[hover] {theme}", flush=True)
    set_theme(theme)
    overlay = dm.container_overlay()
    overlay.set_allowed_areas(DockWidgetArea.all_dock_areas)
    QCursor.setPos(root.mapToGlobal(
        QPoint(root.width() - 80, root.height() // 2)))
    app.processEvents()
    overlay.show_overlay(root)
    overlay.enable_drop_preview(True)
    app.processEvents()
    settle(400)
    save(screen_grab([win]), f"hover_{theme}.png")
    overlay.hide_overlay()
    app.processEvents()
    settle(200)

print("DONE ->", OUT, flush=True)
app.quit()
