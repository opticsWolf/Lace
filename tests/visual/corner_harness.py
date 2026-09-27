# -*- coding: utf-8 -*-
"""Corner harness: does a rounded dock area round its content cleanly?

A docked DockWidget holds a pure-magenta QFrame (no theme uses magenta), next
to a second area so every corner has backdrop behind it. The window is
grabbed and each bottom corner of the magenta content is checked:

- **leak**: magenta outside the dock area's rounded outline.
- **staircase**: each pixel of the content's corner is compared with how much
  of it the ideal rounded corner actually covers (4x4 supersampled). A QRegion
  mask clips on whole pixels, so some arc pixels are fully magenta where the
  circle covers only part of them. Anti-aliased clipping tracks the circle,
  and the border stroke painted on top only ever removes magenta, so neither
  can fake a pass (counting blended pixels could: the border's own AA over
  aliased content produced blends).

    <python> tests/visual/corner_harness.py [theme...]   # prints the table
"""

import math
import os
import sys
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication, QFrame, QMainWindow

#: The regular-set themes with a non-zero corner radius.
THEMES = ("kilim_dark", "kilim_midnight_neo", "kilim_light_neo",
          "cyberpunk_neon", "slate_amber", "solarized_light")

#: Synthetic cases no preset covers: ``name -> (fixture, overrides)``.
#: flush_r10 is a large radius with the content flush against the outline --
#: the hardest case for clipping, since the whole arc cuts through content.
VARIANTS = {
    "flush_r10": ("kilim_midnight_neo", {"content_margin": 0}),
}

MAGENTA = QColor(255, 0, 255)

#: A stair step: a corner pixel that is fully magenta (above SOLID) although
#: the ideal corner covers less than PARTIAL of it. AA clipping never yields
#: one; whole-pixel clipping does wherever the polygon rounds outward.
SOLID = 0.9
PARTIAL = 0.75


def magentaness(c: QColor) -> float:
    """1.0 for pure magenta, 0.0 for anything without a magenta cast."""
    return max(0.0, min(1.0, ((c.red() + c.blue()) / 2 - c.green()) / 255))


def _coverage(x: int, y: int, cx: float, cy: float, r: float, sx: int, sy: int) -> float:
    """Fraction of pixel (x, y) inside the rounded corner (arc centre cx, cy)."""
    inside = 0
    for i in range(4):
        for j in range(4):
            px, py = x + (i + 0.5) / 4, y + (j + 0.5) / 4
            if ((px - cx) * sx <= 0 or (py - cy) * sy <= 0
                    or math.hypot(px - cx, py - cy) <= r):
                inside += 1
    return inside / 16


def _corner_stats(img: QImage, cx: float, cy: float, r: float,
                  sx: int, sy: int, outline_r: float,
                  ox: float, oy: float) -> Dict[str, int]:
    """Scan the r x r square whose rounded corner has its arc centre at (cx, cy).

    (sx, sy) point from the arc centre towards the corner. (ox, oy) is the
    arc centre of the area's own outline, radius outline_r.
    """
    leak = steps = 0
    size = int(math.ceil(max(r, outline_r))) + 2
    for dy in range(size):
        for dx in range(size):
            x = int(cx) + sx * dx
            y = int(cy) + sy * dy
            if not (0 <= x < img.width() and 0 <= y < img.height()):
                continue
            m = magentaness(img.pixelColor(x, y))
            # Outside the area outline, beyond half a pixel of AA fringe.
            d_out = math.hypot(x + 0.5 - ox, y + 0.5 - oy)
            outside = ((x + 0.5 - ox) * sx > 0 and (y + 0.5 - oy) * sy > 0
                       and d_out > outline_r + 0.75)
            if outside and m > 0.5:
                leak += 1
            # Solid magenta the ideal corner does not cover. Anywhere in the
            # square, not just on the arc: the aliased mask's notches sit a
            # pixel or two outside it, under the border's AA ring.
            if m > SOLID and _coverage(x, y, cx, cy, r, sx, sy) < PARTIAL:
                steps += 1
    return {"leak": leak, "steps": steps}


def _theme_dict(theme_key: str):
    """A theme set key, or a VARIANTS name (a Kilim fixture with overrides)."""
    if theme_key not in VARIANTS:
        from tests.theme_sets import load
        return load(theme_key)
    import json
    from lace.theme_models import ThemeJson
    from tests.theme_sets import FIXTURES
    fixture, overrides = VARIANTS[theme_key]
    raw = json.loads((FIXTURES / f"{fixture}.json").read_text(encoding="utf-8"))
    raw.update(overrides)
    return ThemeJson.model_validate(raw).build_theme_dict()


def measure(theme_key: str) -> Dict[str, Dict[str, int]]:
    from lace import DockManager, DockWidget
    from lace.dock_style_manager import get_dock_style_manager
    from lace.dock_theme import DockStyleCategory
    from lace.enums import DockWidgetArea

    sm = get_dock_style_manager()
    sm.apply_theme_dict(_theme_dict(theme_key))

    win = QMainWindow()
    win.resize(640, 420)
    dm = DockManager(win)
    win.setCentralWidget(getattr(dm, "_root", None) or dm)

    frame = QFrame()
    frame.setAutoFillBackground(True)
    frame.setStyleSheet("background: #ff00ff; border: none;")
    probe = DockWidget("Probe", win)
    probe.set_widget(frame)
    dm.add_dock_widget(DockWidgetArea.center, probe)
    other = DockWidget("Other", win)
    other.set_widget(QFrame())
    dm.add_dock_widget(DockWidgetArea.left, other)

    win.show()
    for _ in range(5):
        QApplication.processEvents()

    img = win.grab().toImage()
    ratio = img.devicePixelRatio()
    area = probe.dock_area_widget()
    a_tl = area.mapTo(win, QPoint(0, 0))
    f_tl = frame.mapTo(win, QPoint(0, 0))
    ax, ay, aw, ah = a_tl.x(), a_tl.y(), area.width(), area.height()
    fx, fy, fw, fh = f_tl.x(), f_tl.y(), frame.width(), frame.height()

    outline_r = float(sm.get(DockStyleCategory.CORE, "corner_radius") or 0)
    # The content's own arc: the mask radius DockWidget uses.
    inset = (ay + ah) - (fy + fh)
    content_r = max(0.0, outline_r - inset)

    out = {}
    for name, sx, px, opx in (("bottom_left", -1, fx, ax), ("bottom_right", 1, fx + fw, ax + aw)):
        cx = (px + (content_r if sx < 0 else -content_r)) * ratio
        cy = (fy + fh - content_r) * ratio
        ox = (opx + (outline_r if sx < 0 else -outline_r)) * ratio
        oy = (ay + ah - outline_r) * ratio
        out[name] = _corner_stats(img, cx, cy, content_r * ratio, sx, 1,
                                  outline_r * ratio, ox, oy)
    out["radius"] = {"outline": outline_r, "content": content_r}

    win.close()
    win.deleteLater()
    QApplication.processEvents()
    return out


def corners_ok(result: Dict[str, Dict[str, int]]) -> List[str]:
    """Failures for one theme, empty when both corners are clean."""
    problems = []
    for corner in ("bottom_left", "bottom_right"):
        s = result[corner]
        if s["leak"]:
            problems.append(f"{corner}: {s['leak']} magenta px outside the outline")
        if s["steps"]:
            problems.append(f"{corner}: staircase ({s['steps']} px beyond the arc)")
    return problems


if __name__ == "__main__":
    app = QApplication.instance() or QApplication([])
    for theme in sys.argv[1:] or THEMES + tuple(VARIANTS):
        r = measure(theme)
        print(f"{theme:22} r={r['radius']['outline']:>4} content_r={r['radius']['content']:>4} "
              f"BL leak={r['bottom_left']['leak']:>3} steps={r['bottom_left']['steps']:>3}  "
              f"BR leak={r['bottom_right']['leak']:>3} steps={r['bottom_right']['steps']:>3}  "
              f"{'OK' if not corners_ok(r) else 'FAIL'}")
