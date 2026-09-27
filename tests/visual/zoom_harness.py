# -*- coding: utf-8 -*-
"""Zoom harness: are the style's glyphs still sharp when a canvas zooms in?

Weave hosts Lace widgets on a zoomable QGraphicsView. A glyph the style paints
as vectors stays crisp at any scale; one it paints from a cached 1x pixmap is
stretched, and its edges blur by roughly the zoom factor.

The widgets are laid out in one container, styled and coloured exactly as
DockThemeBridge does it, embedded with QGraphicsProxyWidget and rendered
through a scaled painter. For each glyph the harness crops its rect and
measures the **edge width**: the mean 10-90 % rise distance, in device pixels,
of the monotonic intensity ramps that make up its edges, taken across each
edge (see :func:`edge_width`). A vector edge stays about 1-2 px wide at any
zoom; a stretched bitmap edge grows with it.

    <python> tests/visual/zoom_harness.py [theme] [zoom...]   # prints the table
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QGraphicsScene,
    QGridLayout, QMenu, QRadioButton, QScrollBar, QSlider, QSpinBox, QStyle,
    QStyleOptionComboBox, QStyleOptionSlider, QStyleOptionSpinBox, QTreeView,
    QWidget,
)

#: Largest acceptable mean edge width at 4x, in device pixels. A perfectly
#: sharp edge reads 1 on the pixel grid and 2 off it (one partly covered
#: pixel inside the 10-90 % rise), so vector glyphs with diagonals average
#: 1.8-2.2; a 1x pixmap stretched 4x reads 3.5 and up. 2.5 splits the two.
SHARP_LIMIT = 2.5

#: A ramp must change intensity by this much in total to count as an edge.
_EDGE_MIN = 48
#: Steps smaller than this end a ramp (flat or noise).
_STEP_MIN = 3


def _gray(img: QImage) -> List[List[int]]:
    img = img.convertToFormat(QImage.Format_Grayscale8)
    w, h, bpl = img.width(), img.height(), img.bytesPerLine()
    raw = bytes(img.constBits())
    return [list(raw[y * bpl:y * bpl + w]) for y in range(h)]


#: Rise distance: a ramp is measured between 10 % and 90 % of its swing, so a
#: faint antialiasing tail (a few percent coverage) doesn't count as blur.
_RISE = 0.10


def _trim(line: List[int], i: int, j: int) -> Tuple[int, int]:
    """Narrow ramp ``i..j`` to its 10-90 % rise."""
    lo, hi = line[i], line[j]
    tol = abs(hi - lo) * _RISE
    while i < j - 1 and abs(line[i + 1] - lo) <= tol:
        i += 1
    while j > i + 1 and abs(hi - line[j - 1]) <= tol:
        j -= 1
    return i, j


def _ramp_spans(line: List[int]) -> List[Tuple[int, int]]:
    """``(start, end)`` of each monotonic ramp along one line, at 10-90 % rise."""
    spans = []
    i, n = 0, len(line)
    while i < n - 1:
        step = line[i + 1] - line[i]
        if abs(step) < _STEP_MIN:
            i += 1
            continue
        sign = 1 if step > 0 else -1
        j = i
        while j < n - 1 and (line[j + 1] - line[j]) * sign >= _STEP_MIN:
            j += 1
        if abs(line[j] - line[i]) >= _EDGE_MIN:
            spans.append(_trim(line, i, j))
        i = j
    return spans


def _ramps(line: List[int]) -> List[int]:
    """Widths of the monotonic ramps along one line of pixels."""
    return [j - i for i, j in _ramp_spans(line)]


def edge_width(img: QImage) -> float:
    """Mean edge width, measured across each edge; 0.0 when there are no edges.

    A row or column crosses a slanted edge obliquely, so a perfectly sharp
    diagonal or curve reads several pixels wide along it. Each ramp therefore
    counts as the shorter of its own width and that of the ramp crossing its
    midpoint on the other axis, which is the one nearer the edge normal. Blur
    from a stretched bitmap widens the edge in every direction, so it still
    reads wide.
    """
    px = _gray(img)
    if not px:
        return 0.0
    h, w = len(px), len(px[0])
    across_rows = [[0] * w for _ in range(h)]   # ramp width through (y, x), along x
    across_cols = [[0] * w for _ in range(h)]   # ... along y
    row_ramps, col_ramps = [], []
    for y, row in enumerate(px):
        for i, j in _ramp_spans(row):
            row_ramps.append((y, (i + j) // 2, j - i))
            for x in range(i, j + 1):
                across_rows[y][x] = j - i
    for x in range(w):
        for i, j in _ramp_spans([row[x] for row in px]):
            col_ramps.append(((i + j) // 2, x, j - i))
            for y in range(i, j + 1):
                across_cols[y][x] = j - i
    widths = [min(n, across_cols[y][x] or n) for y, x, n in row_ramps]
    widths += [min(n, across_rows[y][x] or n) for y, x, n in col_ramps]
    return sum(widths) / len(widths) if widths else 0.0


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------
class ZoomBench:
    """The glyph-bearing widgets, themed the way Lace themes an app."""

    def __init__(self, theme_key: str):
        from lace.dock_style_manager import get_dock_style_manager
        from lace.dock_theme_bridge import DockThemeBridge
        from tests.theme_sets import load

        get_dock_style_manager().apply_theme_dict(load(theme_key))

        self.root = QWidget()
        self.root.setAttribute(Qt.WA_DontShowOnScreen)
        grid = QGridLayout(self.root)

        self.combo = QComboBox(); self.combo.addItems(["Alpha", "Beta"])
        self.spin = QSpinBox(); self.spin.setValue(5)
        self.dspin = QDoubleSpinBox(); self.dspin.setValue(0.5)
        self.check = QCheckBox("Check"); self.check.setChecked(True)
        self.radio = QRadioButton("Radio"); self.radio.setChecked(True)
        self.hbar = QScrollBar(Qt.Horizontal); self.hbar.setRange(0, 100); self.hbar.setFixedWidth(160)
        self.vbar = QScrollBar(Qt.Vertical); self.vbar.setRange(0, 100); self.vbar.setFixedHeight(160)
        self.slider = QSlider(Qt.Horizontal); self.slider.setValue(40)

        self.tree = QTreeView(); self.tree.setHeaderHidden(True)
        model = QStandardItemModel(self.tree)
        for name, expand in (("Open", True), ("Shut", False)):
            parent = QStandardItem(name)
            parent.appendRow(QStandardItem("child"))
            model.appendRow(parent)
        self.tree.setModel(model)
        self.tree.expand(model.index(0, 0))
        self.tree.setFixedSize(160, 90)

        for i, w in enumerate((self.combo, self.spin, self.dspin, self.check,
                               self.radio, self.slider, self.hbar)):
            grid.addWidget(w, i, 0)
        grid.addWidget(self.vbar, 0, 1, 4, 1)
        grid.addWidget(self.tree, 4, 1, 3, 1)

        self.menu = QMenu()
        self.menu.addAction("Plain")
        self.menu.addMenu("Submenu").addAction("inner")

        # What DockThemeBridge does to an app, applied to our two top levels
        # (QWidget.setStyle does not reach existing children, so walk them).
        self._bridges = [DockThemeBridge(target=top) for top in (self.root, self.menu)]
        for top in (self.root, self.menu):
            for child in top.findChildren(QWidget):
                child.setStyle(top.style())
        QApplication.processEvents()
        QApplication.processEvents()

        self.scene = QGraphicsScene()
        self.root_proxy = self.scene.addWidget(self.root)
        self.menu_proxy = self.scene.addWidget(self.menu)
        self.menu_proxy.setPos(self.root.sizeHint().width() + 20, 0)
        self.root.adjustSize(); self.menu.adjustSize()
        QApplication.processEvents()

    # -- glyph rects, in scene coordinates ------------------------------------
    def _in_root(self, widget: QWidget, rect: QRect) -> QRectF:
        top_left = widget.mapTo(self.root, rect.topLeft())
        return QRectF(QRect(top_left, rect.size())).translated(self.root_proxy.pos())

    def glyph_rects(self) -> Dict[str, QRectF]:
        rects = {}

        opt = QStyleOptionComboBox(); opt.initFrom(self.combo)
        opt.subControls = QStyle.SC_All
        rects["combo_arrow"] = self._in_root(self.combo, self.combo.style().subControlRect(
            QStyle.CC_ComboBox, opt, QStyle.SC_ComboBoxArrow, self.combo))

        for name, box in (("spin_arrows", self.spin), ("dspin_arrows", self.dspin)):
            sopt = QStyleOptionSpinBox(); sopt.initFrom(box)
            sopt.subControls = QStyle.SC_All
            sopt.stepEnabled = QSpinBox.StepUpEnabled | QSpinBox.StepDownEnabled
            up = box.style().subControlRect(QStyle.CC_SpinBox, sopt, QStyle.SC_SpinBoxUp, box)
            down = box.style().subControlRect(QStyle.CC_SpinBox, sopt, QStyle.SC_SpinBoxDown, box)
            rects[name] = self._in_root(box, up.united(down))

        for name, btn, element in (("check_indicator", self.check, QStyle.SE_CheckBoxIndicator),
                                   ("radio_indicator", self.radio, QStyle.SE_RadioButtonIndicator)):
            from PySide6.QtWidgets import QStyleOptionButton
            bopt = QStyleOptionButton(); bopt.initFrom(btn)
            rects[name] = self._in_root(btn, btn.style().subElementRect(element, bopt, btn))

        rects["hscrollbar"] = self._in_root(self.hbar, self.hbar.rect())
        rects["vscrollbar"] = self._in_root(self.vbar, self.vbar.rect())

        sl = QStyleOptionSlider(); sl.initFrom(self.slider)
        sl.minimum, sl.maximum = self.slider.minimum(), self.slider.maximum()
        sl.sliderPosition = sl.sliderValue = self.slider.value()
        sl.orientation = Qt.Horizontal; sl.subControls = QStyle.SC_All
        rects["slider_handle"] = self._in_root(self.slider, self.slider.style().subControlRect(
            QStyle.CC_Slider, sl, QStyle.SC_SliderHandle, self.slider))

        vp = self.tree.viewport()
        indent = self.tree.indentation()
        for name, row in (("tree_branch_open", 0), ("tree_branch_shut", 1)):
            index = self.tree.model().index(row, 0)
            r = self.tree.visualRect(index)
            rects[name] = self._in_root(vp, QRect(0, r.top(), indent, r.height()))

        action = self.menu.actions()[1]
        ar = self.menu.actionGeometry(action)
        arrow = QRect(ar.right() - ar.height(), ar.top(), ar.height(), ar.height())
        rects["menu_submenu_arrow"] = QRectF(arrow).translated(self.menu_proxy.pos())
        return rects

    def render(self, zoom: float) -> QImage:
        src = self.scene.itemsBoundingRect()
        img = QImage(int(src.width() * zoom) + 1, int(src.height() * zoom) + 1,
                     QImage.Format_ARGB32_Premultiplied)
        img.fill(QColor("white"))
        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        # Exactly ``zoom``: the image is a pixel larger than src * zoom, and
        # stretching into all of it would put every edge on a fractional pixel.
        self.scene.render(p, QRectF(0, 0, src.width() * zoom, src.height() * zoom), src)
        p.end()
        self._origin = src.topLeft()
        return img

    def measure(self, zoom: float) -> Dict[str, float]:
        img = self.render(zoom)
        out = {}
        for name, rect in self.glyph_rects().items():
            r = rect.translated(-self._origin)
            crop = QRect(int(r.x() * zoom), int(r.y() * zoom),
                         int(r.width() * zoom), int(r.height() * zoom))
            out[name] = round(edge_width(img.copy(crop)), 2)
        return out

    def close(self):
        self.scene.clear()  # deletes the proxies and the widgets they hold


def measure(theme_key: str, zooms: Tuple[float, ...] = (1, 2, 4)) -> Dict[float, Dict[str, float]]:
    bench = ZoomBench(theme_key)
    try:
        return {z: bench.measure(z) for z in zooms}
    finally:
        bench.close()


if __name__ == "__main__":
    app = QApplication.instance() or QApplication([])
    theme = sys.argv[1] if len(sys.argv) > 1 else "kilim_dark"
    zooms = tuple(float(z) for z in sys.argv[2:]) or (1, 2, 4)
    table = measure(theme, zooms)
    names = list(next(iter(table.values())))
    print(f"{theme}: mean edge width (device px)")
    print(f"{'glyph':22}" + "".join(f"{z:>7}x" for z in zooms))
    for n in names:
        print(f"{n:22}" + "".join(f"{table[z][n]:8.2f}" for z in zooms))
