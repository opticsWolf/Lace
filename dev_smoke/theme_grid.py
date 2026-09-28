"""The README theme grid: ``main_<theme>.png`` shots, captioned, N per row.

    <python> dev_smoke/theme_grid.py SHOTS_DIR [--out PNG] [--themes a,b,...]

Reads the captures ``screenshot_themes.py`` writes. The default theme list is
the README's twelve.
"""

import argparse
import sys
from pathlib import Path

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter

README = ("catppuccin,cyberpunk_neon,dark,dracula,light,midnight,"
          "neutral,nordic,solarized_dark,tokyo_night,violet_haze,warm")

ap = argparse.ArgumentParser()
ap.add_argument("shots")
ap.add_argument("--out", default="screenshots/main_themes_grid.png")
ap.add_argument("--themes", default=README)
ap.add_argument("--width", type=int, default=450, help="width of each shot")
ap.add_argument("--per-row", type=int, default=3)
a = ap.parse_args()

app = QGuiApplication(sys.argv[:1])
shots = []
for theme in a.themes.split(","):
    img = QImage(str(Path(a.shots) / f"main_{theme}.png"))
    if img.isNull():
        raise SystemExit(f"missing main_{theme}.png in {a.shots}")
    shots.append((theme, img.scaledToWidth(a.width, Qt.TransformationMode.SmoothTransformation)))

label_h, gap = 48, 14
cell_h = max(img.height() for _, img in shots) + label_h
rows = (len(shots) + a.per_row - 1) // a.per_row
out = QImage(a.per_row * a.width + (a.per_row - 1) * gap, rows * cell_h,
             QImage.Format.Format_RGB32)
out.fill(QColor("#000000"))
p = QPainter(out)
font = QFont(p.font())
font.setPixelSize(20)
p.setFont(font)
p.setPen(QColor("#e8e8e8"))
for i, (theme, img) in enumerate(shots):
    x = (i % a.per_row) * (a.width + gap)
    y = (i // a.per_row) * cell_h
    p.drawImage(x, y, img)
    p.drawText(QRect(x, y + img.height(), a.width, label_h), Qt.AlignmentFlag.AlignCenter,
               theme.replace("_", " ").title())
p.end()
Path(a.out).parent.mkdir(parents=True, exist_ok=True)
out.save(a.out)
print(f"{a.out}: {len(shots)} themes, {out.width()}x{out.height()}")
