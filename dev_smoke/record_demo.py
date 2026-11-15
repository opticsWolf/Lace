"""Record the feature-tour GIF/WebP of the frameless demo (Windows only).

Drives the REAL mouse, so drags, drop previews and sidebars behave exactly
as for a user: hands off the mouse for the ~70 s it runs.  Frames are screen
grabs of the main window with a painted cursor.

The tour: widen the right pane, drag a tab into it (drop preview), cycle
themes, pull the left sidebar panel out by its title bar and dock it, then
pin the editor into the emptied sidebar and slide it out.

Writes, next to --out (default screenshots/lace_tour.gif):
  lace_tour.gif / .webp              - the full tour
  lace_tour_short.gif / .webp        - a ~30 s cut (faster, shorter pauses)
"""
import sys, os, time, logging, ctypes, math, argparse, atexit
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
os.chdir(REPO)
logging.disable(logging.CRITICAL)

parser = argparse.ArgumentParser()
parser.add_argument("--out", default=os.path.join("screenshots", "lace_tour.gif"),
                    help="full-tour GIF path; the other files go next to it")
parser.add_argument("--width", type=int, default=960, help="output width in px")
parser.add_argument("--short-speed", type=float, default=2.2,
                    help="playback speed-up of the short cut")
args, qt_args = parser.parse_known_args()
OUT, OUT_W = args.out, args.width
if sys.platform != "win32":
    sys.exit("record_demo drives the mouse through user32; Windows only")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QPoint, QPointF, QRect
from PySide6.QtGui import QCursor, QImage, QPainter, QPolygonF, QColor, QPen

app = QApplication(sys.argv[:1])
from lace import LaceStyle
app.setStyle(LaceStyle())
from demos.demo_app_custom_titlebar import DemoMainWindow
from lace.dock_style_manager import get_dock_style_manager
from lace.enums import DockWidgetArea
from tests import theme_sets
from PIL import Image

user32 = ctypes.windll.user32
LDOWN, LUP = 0x0002, 0x0004
atexit.register(lambda: user32.mouse_event(LUP, 0, 0, 0, 0))

START_THEME = "dark_neo"
TOUR = ["cyberpunk_neon", "catppuccin", "cream_neo", "nordic", "violet_haze",
        "slate_amber", START_THEME]
FRAME_MS = 80

win = DemoMainWindow()
win.resize(1200, 800)
win.move(60, 60)
win.show()
dm = win.dock_manager
sm = dm.sidebar_manager
widgets = {w.windowTitle(): w for w in dm.dock_widgets_map().values()}

class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


frames = []          # (PIL image, capture timestamp)
CURSOR = [QPoint()]  # where the script last put the pointer (logical px)
_last_grab = [0.0]
region = [None]


def grab(force=False):
    now = time.perf_counter()
    if not force and (now - _last_grab[0]) * 1000 < FRAME_MS:
        return
    _last_grab[0] = now
    g = region[0]
    screen = QApplication.primaryScreen()
    pm = screen.grabWindow(0, g.x(), g.y(), g.width(), g.height())
    img = pm.toImage().convertToFormat(QImage.Format_RGB888)
    grab_w = img.width()                      # device pixels
    dpr = grab_w / g.width()
    img = img.scaledToWidth(OUT_W, Qt.SmoothTransformation)
    # The grab carries the screen's devicePixelRatio, and scaling keeps it,
    # so a QPainter would treat our pixel coordinates as logical ones and
    # draw the arrow DPR times too far from the corner.  Paint in pixels.
    img.setDevicePixelRatio(1.0)
    # Paint the cursor (screen grabs leave it out), read from Windows in
    # device pixels -- the same space as the grab.
    pt = _POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    px, py = pt.x - g.x() * dpr, pt.y - g.y() * dpr
    cx, cy = px * OUT_W / grab_w, py * OUT_W / grab_w
    if 0 <= cx < img.width() and 0 <= cy < img.height():
        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing)
        s = 1.05
        pts = [(0, 0), (0, 17), (4.2, 13.2), (7, 19.5), (9.6, 18.4),
               (6.9, 12.3), (12.3, 12.3)]
        poly = QPolygonF([QPointF(cx + x * s, cy + y * s) for x, y in pts])
        p.setPen(QPen(QColor(0, 0, 0), 1.3))
        p.setBrush(QColor(255, 255, 255))
        p.drawPolygon(poly)
        p.end()
    b = bytes(img.constBits())
    pil = Image.frombuffer("RGB", (img.width(), img.height()), b, "raw",
                           "RGB", img.bytesPerLine(), 1).copy()
    frames.append((pil, now))


def tick(ms):
    end = time.perf_counter() + ms / 1000
    while time.perf_counter() < end:
        app.processEvents()
        grab()
        time.sleep(0.008)


def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * t)


def set_cursor(pt):
    CURSOR[0] = QPoint(pt)
    QCursor.setPos(pt)


def move_to(pt, ms=600):
    start = CURSOR[0]
    n = max(2, ms // 16)
    for i in range(1, n + 1):
        t = ease(i / n)
        set_cursor(QPoint(round(start.x() + (pt.x() - start.x()) * t),
                          round(start.y() + (pt.y() - start.y()) * t)))
        app.processEvents()
        grab()
        time.sleep(ms / 1000 / n)


def down():
    user32.mouse_event(LDOWN, 0, 0, 0, 0); tick(60)


def up():
    user32.mouse_event(LUP, 0, 0, 0, 0); tick(60)


def click(pt, ms=500):
    move_to(pt, ms); tick(120); down(); up()


def center_of(w):
    return w.mapToGlobal(w.rect().center())


def set_theme(name):
    get_dock_style_manager().apply_theme_dict(theme_sets.load(name))
    app.processEvents()


def floating_windows():
    return [w for w in QApplication.topLevelWidgets()
            if w is not win and w.isVisible() and w.isWindow()
            and type(w).__name__.startswith(("Floating", "Frameless"))]


from lace.enums import TitleBarButton, DockWidgetFeature
from lace.dock_overlay import DockOverlayCross


def indicator(area):
    """Global centre of a visible dock-area drop indicator for *area*."""
    found = None
    for c in QApplication.allWidgets():
        if isinstance(c, DockOverlayCross) and c.isVisible():
            w = c._drop_indicator_widgets.get(area)
            ok = w is not None and w.isVisible()
            if ok and c._mode.name != "container" and found is None:
                found = w.mapToGlobal(w.rect().center())
    return found


def drag_to_drop(target_widget, area, label):
    """With the button held: hover *target_widget*, aim at its *area* indicator, release."""
    move_to(center_of(target_widget) + QPoint(0, 25), 1200)
    tick(600)
    ind = indicator(area)
    print(f"{label}: indicator", ind, flush=True)
    if ind is not None:
        move_to(ind, 700)
    tick(1100)          # let the drop preview sit on screen
    up()                # release = drop
    tick(1100)


def sidebar_button_for(dw):
    for sb in sm._sidebars.values():
        for b in sb._buttons:
            if b.dock_widget() is dw:
                return b
    return None


def hover_sidebar(btn, hold=2200):
    """Hover a sidebar tab, let the panel slide out, rest the pointer inside."""
    move_to(center_of(btn), 1000)
    tick(800)
    ov = sm._overlay
    if ov.isVisible():
        inside = ov.mapToGlobal(QPoint(ov.width() // 2, ov.height() // 3))
        move_to(inside, 900)
    tick(hold)


# The testbed's left sidebar panel is locked; for the tour it may move.
layers = widgets["Locked Sidebar Tool"]
layers.setWindowTitle("Layers")
layers.set_features(DockWidgetFeature.closable | DockWidgetFeature.movable
                    | DockWidgetFeature.floatable | DockWidgetFeature.pinnable)

# ── set up ───────────────────────────────────────────────────────────
set_theme(START_THEME)
for _ in range(30):
    app.processEvents(); time.sleep(0.02)
win.raise_(); win.activateWindow()
for _ in range(20):
    app.processEvents(); time.sleep(0.02)
region[0] = win.frameGeometry()
print("region", region[0], flush=True)
HOME = win.mapToGlobal(QPoint(640, 430))
set_cursor(HOME)

logger = widgets["Unclosable Logger"]
editor = widgets["Standard Editor"]
right = widgets["Unfloatable Tool"]
tick(1300)

# ── 1. widen the narrow right pane ───────────────────────────────────
ra = right.dock_area_widget()
sp, child = ra.parentWidget(), ra
while sp is not None and not hasattr(sp, "handle"):
    child, sp = sp, sp.parentWidget()
idx = sp.indexOf(child)
handle = sp.handle(idx)
print("splitter", sp.orientation(), "index", idx, "sizes", sp.sizes(), flush=True)
h = center_of(handle)
move_to(h, 1000); tick(300)
down()
move_to(h + QPoint(-230, 0), 1300)
tick(250)
up()
tick(900)
print("sizes after", sp.sizes(), flush=True)

# ── 2. drag the logger tab into the widened pane ─────────────────────
press = center_of(logger.tab_widget())
move_to(press, 1000); tick(300)
down()
for dx, dy in [(12, -10), (40, -60), (110, -140)]:
    move_to(press + QPoint(dx, dy), 220)
drag_to_drop(ra, DockWidgetArea.center, "logger->right pane")

# ── 3. themes ─────────────────────────────────────────────────────────
move_to(HOME, 900)
for name in TOUR:
    set_theme(name)
    tick(1150)

# ── 4. open the left sidebar panel, pull it out, dock it elsewhere ───
lb = sidebar_button_for(layers)
print("layers button:", lb, flush=True)
hover_sidebar(lb, 2000)
from lace.sidebar_title_bar import SideBarTitleBar
tbs = [t for t in sm._overlay.findChildren(SideBarTitleBar) if t.isVisible()]
print("sidebar title bars:", len(tbs), flush=True)
tb = tbs[0]
press = tb.mapToGlobal(QPoint(int(tb.width() * 0.35), tb.height() // 2))
move_to(press, 800); tick(400)
down()
for dx, dy in ((10, 8), (40, 30), (120, 80)):
    move_to(press + QPoint(dx, dy), 220)
drag_to_drop(ra, DockWidgetArea.bottom, "layers->right pane")

# ── 5. pin a dock panel into the now-empty left sidebar ──────────────
move_to(HOME, 900); tick(500)
pa = editor.dock_area_widget()
pin_btn = pa.title_bar_button(TitleBarButton.pin)
move_to(center_of(pin_btn), 1200)
tick(900)                       # hover the pin button
down(); up()
tick(1600)                      # the dock collapses into a sidebar tab
eb = sidebar_button_for(editor)
side = next((a for a, s in sm._sidebars.items() if eb in s._buttons), None)
print("editor pinned to:", side, flush=True)
if eb is not None:
    hover_sidebar(eb, 2400)

move_to(HOME, 1000)
tick(1800)
grab(force=True)
win.close()
print("frames:", len(frames), flush=True)


# ── encode ────────────────────────────────────────────────────────────
def timed_frames():
    """(image, duration ms) per frame, identical neighbours merged."""
    out = []
    for i, (im, t) in enumerate(frames):
        nxt = frames[i + 1][1] if i + 1 < len(frames) else t + 1.2
        d = (nxt - t) * 1000
        if out and im.tobytes() == out[-1][0].tobytes():
            out[-1][1] += d
        else:
            out.append([im, d])
    return out


def shorten(seq, speed, max_hold=700, min_frame=90):
    """Faster motion, capped pauses, and no frame shorter than *min_frame*."""
    out = []
    for im, d in seq:
        nd = min(d / speed, max_hold)
        if out and out[-1][1] < min_frame:
            out[-1] = [im, out[-1][1] + nd]   # keep the newer picture
        else:
            out.append([im, nd])
    return out


def write(seq, stem):
    ims = [im for im, _ in seq]
    durs = [max(20, int(round(d / 10)) * 10) for _, d in seq]
    durs[-1] = max(durs[-1], 1200)            # rest a moment before looping
    # One palette for every frame (sampled across all themes), so frames
    # only differ where pixels changed and the GIF stays small.
    picks = ims[:: max(1, len(ims) // 36)]
    w, h = ims[0].size
    cols = 6
    mont = Image.new("RGB", (w * cols, h * ((len(picks) + cols - 1) // cols)))
    for k, im in enumerate(picks):
        mont.paste(im, ((k % cols) * w, (k // cols) * h))
    pal = mont.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    q = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in ims]
    q[0].save(stem + ".gif", save_all=True, append_images=q[1:],
              duration=durs, loop=0, disposal=1)
    ims[0].save(stem + ".webp", save_all=True, append_images=ims[1:],
                duration=durs, loop=0, quality=80, method=4)
    for ext in (".gif", ".webp"):
        print(f"saved {stem}{ext}: {len(ims)} frames, {sum(durs) / 1000:.1f} s, "
              f"{os.path.getsize(stem + ext) // 1024} KB", flush=True)


stem = os.path.splitext(OUT)[0]
os.makedirs(os.path.dirname(stem) or ".", exist_ok=True)
full = timed_frames()
write(full, stem)
write(shorten(full, args.short_speed), stem + "_short")
