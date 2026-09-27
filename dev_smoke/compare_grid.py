"""Before/after grid of theme screenshots (plan Phase 6, M2).

    <python> dev_smoke/compare_grid.py BEFORE_DIR AFTER_DIR [--out PNG] [--kind main]

Pairs ``<kind>_<theme>.png`` found in both folders (as written by
``screenshot_themes.py``), before on the left, after on the right, two pairs
per row, each labelled.
"""

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter

ap = argparse.ArgumentParser()
ap.add_argument("before")
ap.add_argument("after")
ap.add_argument("--out", default="screenshots/compare_grid.png")
ap.add_argument("--kind", default="main")
ap.add_argument("--width", type=int, default=560, help="width of each shot")
ap.add_argument("--per-row", type=int, default=2, help="pairs per row")
a = ap.parse_args()

app = QGuiApplication(sys.argv[:1])
before, after = Path(a.before), Path(a.after)
prefix = f"{a.kind}_"
themes = sorted(p.stem[len(prefix):] for p in after.glob(f"{prefix}*.png")
                if (before / p.name).exists())
if not themes:
    raise SystemExit("no screenshots in both folders")


def scaled(path: Path) -> QImage:
    img = QImage(str(path))
    return img.scaledToWidth(a.width, Qt.TransformationMode.SmoothTransformation)


shots = [(t, scaled(before / f"{prefix}{t}.png"), scaled(after / f"{prefix}{t}.png"))
         for t in themes]
label_h, gap = 24, 12
cell_h = max(max(b.height(), n.height()) for _, b, n in shots) + label_h
pair_w = 2 * a.width + gap
rows = (len(shots) + a.per_row - 1) // a.per_row
out = QImage(a.per_row * pair_w + (a.per_row - 1) * 3 * gap, rows * (cell_h + gap),
             QImage.Format.Format_RGB32)
out.fill(QColor("#2b2b2b"))
p = QPainter(out)
font = QFont(p.font())
font.setPixelSize(14)
p.setFont(font)
p.setPen(QColor("#e8e8e8"))
for i, (theme, b, n) in enumerate(shots):
    x = (i % a.per_row) * (pair_w + 3 * gap)
    y = (i // a.per_row) * (cell_h + gap)
    p.drawText(QRect(x, y, pair_w, label_h), Qt.AlignmentFlag.AlignVCenter,
               f"{theme}    {before.name}  |  {after.name}")
    p.drawImage(x, y + label_h, b)
    p.drawImage(x + a.width + gap, y + label_h, n)
p.end()
Path(a.out).parent.mkdir(parents=True, exist_ok=True)
out.save(a.out)
print(f"{a.out}: {len(shots)} themes, {out.width()}x{out.height()}")
