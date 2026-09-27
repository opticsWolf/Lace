"""Before/after screenshot pairs for review.

    <python> dev_smoke/pair_screenshots.py [--before screenshots/m0_0.7.6]
        [--after screenshots/m1_0.8] [--out screenshots/m1_pairs]

Every image present in both folders is composed side by side, before on the
left and after on the right, under a label bar, into ``--out``. Also writes
``index.html`` there listing all pairs, for scrolling through in a browser.
"""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter

LABEL_H = 28
GAP = 8


def pair(before: Path, after: Path, out: Path, left: str, right: str) -> None:
    a, b = QImage(str(before)), QImage(str(after))
    w = a.width() + GAP + b.width()
    h = LABEL_H + max(a.height(), b.height())
    img = QImage(w, h, QImage.Format.Format_RGB32)
    img.fill(QColor(40, 40, 40))
    p = QPainter(img)
    font = QFont()
    font.setPixelSize(14)
    font.setBold(True)
    p.setFont(font)
    p.setPen(QColor(230, 230, 230))
    p.drawText(QRect(8, 0, a.width(), LABEL_H), Qt.AlignmentFlag.AlignVCenter,
               f"{left}  {before.stem}")
    p.drawText(QRect(a.width() + GAP + 8, 0, b.width(), LABEL_H), Qt.AlignmentFlag.AlignVCenter,
               f"{right}  {after.stem}")
    p.drawImage(0, LABEL_H, a)
    p.drawImage(a.width() + GAP, LABEL_H, b)
    p.end()
    img.save(str(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", default="screenshots/m0_0.7.6")
    ap.add_argument("--after", default="screenshots/m1_0.8")
    ap.add_argument("--out", default="screenshots/m1_pairs")
    args = ap.parse_args()
    QGuiApplication.instance() or QGuiApplication([])
    before, after, out = (ROOT / d for d in (args.before, args.after, args.out))
    out.mkdir(parents=True, exist_ok=True)
    names = sorted(n.name for n in before.glob("*.png") if (after / n.name).exists())
    # main_ first, then float_, each alphabetical by theme.
    names.sort(key=lambda n: (not n.startswith("main_"), n))
    left, right = before.name, after.name
    for n in names:
        pair(before / n, after / n, out / n, left, right)
        print(f"  {n}")
    rows = "\n".join(f'<h3>{n[:-4]}</h3><img src="{n}" loading="lazy">' for n in names)
    (out / "index.html").write_text(
        "<!doctype html><meta charset=utf-8><title>Theme pairs</title>"
        "<style>body{background:#222;color:#ddd;font:14px sans-serif;margin:16px}"
        "img{max-width:100%;display:block;margin-bottom:24px}</style>"
        f"<h1>{left} vs {right}</h1>\n{rows}\n", encoding="utf-8")
    print(f"{len(names)} pairs -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
