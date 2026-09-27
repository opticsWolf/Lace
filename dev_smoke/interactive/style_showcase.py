# -*- coding: utf-8 -*-
"""Every LaceStyle family on live widgets, for S5 and smoke_lace_style.

    <python> dev_smoke/interactive/style_showcase.py [theme] [--zoom]

``theme`` is a preset or Kilim fixture key (default kilim_dark). ``--zoom``
puts the showcase on a QGraphicsView (as on Weave's canvas); keys 1 / 2 / 4
set 100 / 200 / 400 %. Tokens can be switched live from the "Style" menu.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import (
    QAbstractSpinBox, QApplication, QCheckBox, QComboBox, QDoubleSpinBox, QGraphicsScene,
    QGraphicsView, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMainWindow, QMenu, QProgressBar, QPushButton, QRadioButton, QScrollArea, QSlider,
    QSpinBox, QTabWidget, QTableWidget, QTableWidgetItem, QToolBox, QToolButton,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import build_dock_palette, resolve_dock_colors
from lace.lace_style import CONTRAST_LEVELS, SCROLLBAR_MODES, LaceStyle
from tests.theme_sets import load


def _buttons() -> QGroupBox:
    box = QGroupBox("Buttons")
    g = QGridLayout(box)
    g.addWidget(QPushButton("Push"), 0, 0)
    default = QPushButton("Default")
    default.setDefault(True)
    g.addWidget(default, 0, 1)
    flat = QPushButton("Flat")
    flat.setFlat(True)
    g.addWidget(flat, 0, 2)
    toggle = QPushButton("Toggle")
    toggle.setCheckable(True)
    toggle.setChecked(True)
    g.addWidget(toggle, 0, 3)
    off = QPushButton("Disabled")
    off.setEnabled(False)
    g.addWidget(off, 0, 4)
    menu = QMenu(box)
    menu.addAction("One")
    menu.addAction("Two")
    for col, (mode, raise_) in enumerate([
            (QToolButton.ToolButtonPopupMode.DelayedPopup, False),
            (QToolButton.ToolButtonPopupMode.DelayedPopup, True),
            (QToolButton.ToolButtonPopupMode.MenuButtonPopup, False),
            (QToolButton.ToolButtonPopupMode.InstantPopup, False)]):
        t = QToolButton()
        t.setText("Tool")
        t.setPopupMode(mode)
        t.setAutoRaise(raise_)
        if mode != QToolButton.ToolButtonPopupMode.DelayedPopup:
            t.setMenu(menu)
        g.addWidget(t, 1, col)
    return box


def _inputs() -> QGroupBox:
    box = QGroupBox("Inputs")
    g = QGridLayout(box)
    g.addWidget(QLineEdit("Line edit"), 0, 0)
    ro = QLineEdit("Read-only")
    ro.setReadOnly(True)
    g.addWidget(ro, 0, 1)
    off = QLineEdit("Disabled")
    off.setEnabled(False)
    g.addWidget(off, 0, 2)
    combo = QComboBox()
    combo.addItems(["Combo", "Two", "Three"])
    g.addWidget(combo, 1, 0)
    editable = QComboBox()
    editable.setEditable(True)
    editable.addItems(["Editable", "Two"])
    g.addWidget(editable, 1, 1)
    g.addWidget(QSpinBox(), 1, 2)
    plus = QDoubleSpinBox()
    plus.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.PlusMinus)
    g.addWidget(plus, 2, 0)
    bare = QSpinBox()
    bare.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
    g.addWidget(bare, 2, 1)
    maxed = QSpinBox()
    maxed.setValue(maxed.maximum())
    g.addWidget(maxed, 2, 2)
    return box


def _checks() -> QGroupBox:
    box = QGroupBox("Checks")
    g = QGridLayout(box)
    g.addWidget(QCheckBox("Check"), 0, 0)
    on = QCheckBox("Checked")
    on.setChecked(True)
    g.addWidget(on, 0, 1)
    tri = QCheckBox("Partial")
    tri.setTristate(True)
    tri.setCheckState(Qt.CheckState.PartiallyChecked)
    g.addWidget(tri, 0, 2)
    off = QCheckBox("Disabled")
    off.setEnabled(False)
    g.addWidget(off, 0, 3)
    g.addWidget(QRadioButton("Radio"), 1, 0)
    r = QRadioButton("Selected")
    r.setChecked(True)
    g.addWidget(r, 1, 1)
    roff = QRadioButton("Disabled")
    roff.setEnabled(False)
    g.addWidget(roff, 1, 3)
    return box


def _range() -> QGroupBox:
    box = QGroupBox("Range")
    v = QVBoxLayout(box)
    s = QSlider(Qt.Orientation.Horizontal)
    s.setValue(40)
    v.addWidget(s)
    t = QSlider(Qt.Orientation.Horizontal)
    t.setTickPosition(QSlider.TickPosition.TicksBelow)
    t.setTickInterval(10)
    t.setValue(70)
    v.addWidget(t)
    d = QSlider(Qt.Orientation.Horizontal)
    d.setValue(30)
    d.setEnabled(False)
    v.addWidget(d)
    p = QProgressBar()
    p.setValue(60)
    v.addWidget(p)
    busy = QProgressBar()
    busy.setRange(0, 0)
    v.addWidget(busy)
    return box


def _containers() -> QWidget:
    tabs = QTabWidget()
    table = QTableWidget(6, 3)
    table.setHorizontalHeaderLabels(["Name", "Size", "Type"])
    for r in range(6):
        for c in range(3):
            table.setItem(r, c, QTableWidgetItem(f"{r}.{c}"))
    table.setSortingEnabled(True)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    table.setToolTip("A tooltip on the table")
    tabs.addTab(table, "Table")
    tree = QTreeWidget()
    tree.setHeaderLabels(["Tree", "Value"])
    for i in range(3):
        top = QTreeWidgetItem(tree, [f"Node {i}", str(i)])
        for j in range(3):
            child = QTreeWidgetItem(top, [f"Leaf {i}.{j}", str(j)])
            child.setCheckState(0, Qt.CheckState.Checked if j == 0 else Qt.CheckState.Unchecked)
    tree.expandAll()
    tabs.addTab(tree, "Tree")
    toolbox = QToolBox()
    toolbox.addItem(QLabel("First page"), "Page one")
    toolbox.addItem(QLabel("Second page"), "Page two")
    tabs.addTab(toolbox, "Tool box")
    tabs.addTab(QLabel("Disabled tab"), "Off")
    tabs.setTabEnabled(3, False)
    south = QTabWidget()
    south.setTabPosition(QTabWidget.TabPosition.South)
    south.addTab(QLabel("South"), "One")
    south.addTab(QLabel("South"), "Two")
    west = QTabWidget()
    west.setTabPosition(QTabWidget.TabPosition.West)
    west.addTab(QLabel("West"), "One")
    west.addTab(QLabel("West"), "Two")
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.addWidget(tabs, 3)
    row = QHBoxLayout()
    row.addWidget(south)
    row.addWidget(west)
    lay.addLayout(row, 1)
    return w


def build_content() -> QWidget:
    """The showcase body: every family, no window chrome."""
    body = QWidget()
    grid = QGridLayout(body)
    grid.addWidget(_buttons(), 0, 0)
    grid.addWidget(_inputs(), 0, 1)
    grid.addWidget(_checks(), 1, 0)
    grid.addWidget(_range(), 1, 1)
    grid.addWidget(_containers(), 2, 0, 1, 2)
    scroll = QScrollArea()
    scroll.setWidget(body)
    scroll.setWidgetResizable(True)
    return scroll


def apply_theme(app: QApplication, key: str) -> None:
    get_dock_style_manager().apply_theme_dict(load(key))
    app.setPalette(build_dock_palette(is_panel=False, colors=resolve_dock_colors()))


class Showcase(QMainWindow):
    def __init__(self, style: LaceStyle, zoom: bool = False):
        super().__init__()
        self.style_ = style
        self.setWindowTitle("LaceStyle showcase")
        content = build_content()
        if zoom:
            scene = QGraphicsScene(self)
            content.resize(900, 760)
            scene.addWidget(content)
            self.view = QGraphicsView(scene)
            self.setCentralWidget(self.view)
            for key, factor in (("1", 1.0), ("2", 2.0), ("4", 4.0)):
                act = QAction(f"Zoom {int(factor * 100)} %", self)
                act.setShortcut(QKeySequence(key))
                act.triggered.connect(lambda _=False, f=factor: self._zoom(f))
                self.addAction(act)
        else:
            self.setCentralWidget(content)
        self._menus()
        self.resize(960, 820)

    def _zoom(self, factor: float) -> None:
        self.view.resetTransform()
        self.view.scale(factor, factor)

    def _menus(self) -> None:
        file_ = self.menuBar().addMenu("&File")
        file_.addAction("&Open")
        file_.addAction("&Save").setEnabled(False)
        file_.addSeparator()
        wrap = file_.addAction("&Wrap lines")
        wrap.setCheckable(True)
        wrap.setChecked(True)
        sub = file_.addMenu("&Recent")
        sub.addAction("one.txt")
        style = self.menuBar().addMenu("&Style")
        self._choice(style, "Scrollbar", SCROLLBAR_MODES, self.style_.scrollbar, "scrollbar")
        self._choice(style, "Contrast", CONTRAST_LEVELS, self.style_.contrast, "contrast")
        self._choice(style, "Radius", (0, 2, 4, 8), self.style_.control_radius, "control_radius")

    def _choice(self, menu: QMenu, title: str, values, current, token: str) -> None:
        sub = menu.addMenu(title)
        group = QActionGroup(sub)
        for v in values:
            act = sub.addAction(str(v))
            act.setCheckable(True)
            act.setChecked(v == current)
            group.addAction(act)
            act.triggered.connect(lambda _=False, v=v: self._set(token, v))

    def _set(self, token: str, value) -> None:
        self.style_.set_tokens(**{token: value})
        # Extents change with the scrollbar mode: re-polish so layouts follow.
        for w in QApplication.allWidgets():
            w.updateGeometry()
            w.update()


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    app = QApplication(sys.argv)
    style = LaceStyle()
    app.setStyle(style)
    apply_theme(app, args[0] if args else "kilim_dark")
    win = Showcase(style, zoom="--zoom" in sys.argv)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
