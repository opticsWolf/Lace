# -*- coding: utf-8 -*-
"""Control gallery sheets for a few themes, LaceStyle | Fusion side by side.

The gallery itself lives in ``lace.style.gallery``.

    <python> tests/visual/gallery.py [theme...] [--out DIR]
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QApplication, QStyleFactory

from lace.style.gallery import CELL, ROWS, STATES, render  # noqa: F401  (re-exported)


def side_by_side(theme_key: str) -> QImage:
    """LaceStyle and stock Fusion galleries for one theme, left to right."""
    from lace.dock_style_manager import get_dock_style_manager
    from lace.dock_theme import build_dock_palette, resolve_dock_colors
    from lace.lace_style import LaceStyle
    from tests.theme_sets import load

    get_dock_style_manager().apply_theme_dict(load(theme_key))
    palette = build_dock_palette(is_panel=False, colors=resolve_dock_colors())
    lace = render(LaceStyle(), palette, f"{theme_key} - LaceStyle")
    fusion = render(QStyleFactory.create("Fusion"), palette, f"{theme_key} - Fusion")
    out = QImage(lace.width() + fusion.width() + 12, max(lace.height(), fusion.height()),
                 QImage.Format.Format_ARGB32_Premultiplied)
    out.fill(QColor("#808080"))
    p = QPainter(out)
    p.drawImage(0, 0, lace)
    p.drawImage(lace.width() + 12, 0, fusion)
    p.end()
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    out_dir = Path("screenshots/gallery")
    if "--out" in args:
        i = args.index("--out")
        out_dir = Path(args[i + 1])
        del args[i:i + 2]
    themes = args or ["kilim_dark", "kilim_light_neo"]
    app = QApplication.instance() or QApplication([])
    os.makedirs(out_dir, exist_ok=True)
    for key in themes:
        path = out_dir / f"{key}.png"
        side_by_side(key).save(str(path))
        print(path)
