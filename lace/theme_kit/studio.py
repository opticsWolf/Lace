# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


"""Theme Studio: build a theme by eye.

    python -m lace.theme_kit studio [theme.json | --preset NAME]

Seeds, keywords, chassis and neutral tint on the left; a live dock layout
and the control gallery (zoomable) in the middle; audit, family and diff
below. Clicking *Fix* on an audit row applies its suggestion.

Lace's style manager is process-wide, so the Studio themes every Lace
widget in its process. From inside a Lace app, open it with :func:`launch`,
which starts it in a process of its own; the host app is never touched.
Within the Studio, only the preview follows the theme: the Studio's own
controls keep the palette the application had when it opened.
"""

import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QComboBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QMenu, QPlainTextEdit, QProgressBar, QPushButton,
    QScrollArea, QSlider, QSpinBox, QSplitter, QTabWidget, QTextEdit, QToolButton,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from lace.dock_theme import ThemeSpec, build_theme
from lace.theme_contrast import CONTRAST_LEVELS, DEPTH_LEVELS
from lace.theme_kit import export
from lace.theme_kit.audit import AuditReport, Suggestion, apply_fix, audit
from lace.theme_kit.chassis import CHASSIS, chassis_of, compose, palette_of
from lace.theme_kit.derive import PALETTE_FIELDS, Palette, derive, to_rgba
from lace.theme_kit.family import VARIANTS, family, variant_of

#: Seed colours, in panel order; the last three are optional (derived when unset).
SEEDS = ("base", "accent", "text", "surface", "border")
OPTIONAL_SEEDS = ("text", "surface", "border")
KEYWORDS: Dict[str, Sequence[str]] = {
    "contrast": CONTRAST_LEVELS,
    "depth": DEPTH_LEVELS,
    "selection": ("solid", "tint"),
    "title_mode": ("darker", "lighter"),
    "hover_mode": ("darker", "lighter"),
}
ZOOMS = (100, 400)


def _hex(c) -> str:
    return "#{:02x}{:02x}{:02x}".format(*to_rgba(c)[:3])


# ----------------------------------------------------------------------------------
# Model
# ----------------------------------------------------------------------------------
class StudioModel(QObject):
    """What the Studio edits, without any widgets.

    ``spec()`` is ``compose(derive(seeds, keywords, tint) + extras, chassis,
    overrides)`` with the applied audit fixes laid over it. ``extras`` holds
    the palette colours a loaded theme set that ``derive`` does not make
    (focus ring, title, status, tooltip). Setting a seed drops any fix made
    to that colour.
    """

    changed = Signal()

    def __init__(self, spec: Optional[ThemeSpec] = None, name: str = "my_theme"):
        super().__init__()
        self.load(spec or compose(derive("#1b1d23", "#4f8cff"), "classic"), name)

    # --- state ---------------------------------------------------------------
    def load(self, spec: ThemeSpec, name: Optional[str] = None) -> None:
        """Start from ``spec``: its palette as seeds, its chassis and overrides."""
        pal = palette_of(spec)
        self.seeds: Dict[str, Optional[List[int]]] = {s: getattr(pal, s) for s in SEEDS}
        self.keywords: Dict[str, str] = {k: getattr(pal, k) for k in KEYWORDS}
        self.extras: Dict[str, Any] = {f: getattr(pal, f) for f in PALETTE_FIELDS
                                       if f not in SEEDS and f not in KEYWORDS}
        self.chassis, self.overrides = chassis_of(spec)
        self.tint = 0.0
        self.fixes: Dict[str, List[int]] = {}
        self.origin = spec
        if name:
            self.name = name
        self.changed.emit()

    def set_seed(self, name: str, value) -> None:
        if name not in SEEDS:
            raise KeyError(name)
        if value is None and name not in OPTIONAL_SEEDS:
            raise ValueError(f"{name} is required")
        self.seeds[name] = to_rgba(value)
        self.fixes.pop(name, None)
        self.changed.emit()

    def set_keyword(self, name: str, value: str) -> None:
        if value not in KEYWORDS[name]:
            raise ValueError(f"{name} must be one of {KEYWORDS[name]}")
        self.keywords[name] = value
        self.changed.emit()

    def set_chassis(self, name: str) -> None:
        """Another chassis; its overrides from a loaded theme are dropped."""
        if name not in CHASSIS:
            raise KeyError(name)
        self.chassis, self.overrides = name, {}
        self.changed.emit()

    def set_tint(self, tint: float) -> None:
        self.tint = float(tint)
        self.changed.emit()

    def apply_fix(self, suggestion: Suggestion) -> Optional[str]:
        """Apply an audit suggestion; the spec field it changed, or None."""
        result = apply_fix(self.spec(), suggestion)
        if result is None:
            return None
        spec, field_name = result
        self.fixes[field_name] = list(getattr(spec, field_name))
        self.changed.emit()
        return field_name

    # --- results -------------------------------------------------------------
    def palette(self) -> Palette:
        extras = dict(self.extras)
        pal = derive(self.seeds["base"], self.seeds["accent"], self.seeds["text"],
                     surface=self.seeds["surface"], border=self.seeds["border"],
                     focus_border_color=extras.pop("focus_border_color", None),
                     title_bg=extras.pop("title_bg", None),
                     neutral_tint=self.tint, **self.keywords)
        return replace(pal, **{k: v for k, v in extras.items() if v is not None})

    def spec(self) -> ThemeSpec:
        spec = compose(self.palette(), self.chassis, **self.overrides)
        return replace(spec, **self.fixes) if self.fixes else spec

    def report(self) -> AuditReport:
        return audit(self.spec(), clipped=self.palette().clipped)

    def family(self) -> Dict[str, ThemeSpec]:
        return family(self.spec())

    def diff(self) -> Dict[str, Optional[float]]:
        return export.diff(self.origin, self.spec())

    def to_json(self, path=None) -> str:
        return export.to_json(self.spec(), path, name=self.name)

    def to_python(self) -> str:
        return export.to_python(self.spec(), name=self.name)


# ----------------------------------------------------------------------------------
# Widgets
# ----------------------------------------------------------------------------------
def _swatch(colours: Sequence, w: int = 18, h: int = 14) -> QIcon:
    pm = QPixmap(w * len(colours), h)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    for i, c in enumerate(colours):
        if c is None:
            p.setPen(QColor(128, 128, 128))
            p.drawLine(i * w, h - 1, i * w + w - 1, 0)
        else:
            p.fillRect(i * w, 0, w, h, QColor(*to_rgba(c)))
    p.end()
    return QIcon(pm)


def _pinned(source: QPalette) -> QPalette:
    """A copy of ``source`` with every role set explicitly. A plain copy has
    an empty resolve mask, so a widget given it still follows the app palette."""
    pal = QPalette()
    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive,
                  QPalette.ColorGroup.Disabled):
        for role in QPalette.ColorRole:
            if role in (QPalette.ColorRole.NColorRoles,):
                continue
            pal.setBrush(group, role, source.brush(group, role))
    return pal


class _SeedRow(QWidget):
    def __init__(self, model: StudioModel, name: str, parent=None):
        super().__init__(parent)
        self.model, self.name = model, name
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.button = QPushButton()
        self.button.clicked.connect(self._pick)
        lay.addWidget(self.button, 1)
        if name in OPTIONAL_SEEDS:
            self.auto = QToolButton()
            self.auto.setText("auto")
            self.auto.setToolTip("Derive this colour instead")
            self.auto.clicked.connect(lambda: model.set_seed(name, None))
            lay.addWidget(self.auto)

    def sync(self) -> None:
        value = self.model.seeds[self.name]
        self.button.setIcon(_swatch([value]))
        self.button.setText(_hex(value) if value is not None else "derived")

    def _pick(self) -> None:
        start = QColor(*to_rgba(self.model.seeds[self.name] or self.model.palette().text))
        c = QColorDialog.getColor(start, self, self.name,
                                  QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if c.isValid():
            self.model.set_seed(self.name, [c.red(), c.green(), c.blue(), c.alpha()])


def _live_controls() -> QWidget:
    """Real widgets for the preview's second tab."""
    w = QWidget()
    form = QFormLayout(w)
    form.addRow("Line edit", QLineEdit("Some text"))
    combo = QComboBox()
    combo.addItems(["First", "Second", "Third"])
    form.addRow("Combo", combo)
    form.addRow("Spin", QSpinBox())
    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setValue(40)
    form.addRow("Slider", slider)
    bar = QProgressBar()
    bar.setValue(62)
    form.addRow("Progress", bar)
    check = QCheckBox("Check me")
    check.setChecked(True)
    form.addRow("", check)
    row = QHBoxLayout()
    ok = QPushButton("OK")
    ok.setDefault(True)
    row.addWidget(ok)
    row.addWidget(QPushButton("Cancel"))
    form.addRow("", row)
    disabled = QLineEdit("Disabled")
    disabled.setEnabled(False)
    form.addRow("Disabled", disabled)
    return w


class StudioWindow(QMainWindow):
    """The Studio. See the module docstring for what it themes."""

    def __init__(self, spec: Optional[ThemeSpec] = None, name: str = "my_theme",
                 parent: Optional[QWidget] = None):
        super().__init__(parent)
        # The Studio's own controls keep the palette the app has now; set
        # explicitly, it no longer follows the app palette the preview's
        # DockManager rewrites.
        self._chrome_palette = _pinned(QApplication.palette())
        self.model = StudioModel(spec, name)
        self.setWindowTitle("Lace Theme Studio")
        self.resize(1400, 900)

        split = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(split)
        self.controls = self._build_controls()
        split.addWidget(self.controls)
        right = QSplitter(Qt.Orientation.Vertical)
        split.addWidget(right)
        right.addWidget(self._build_preview())
        self.panels = self._build_panels()
        right.addWidget(self.panels)
        split.setSizes([320, 1080])
        right.setSizes([600, 300])
        # The preview host's own palette (set by its bridge) wins below it.
        self.setPalette(self._chrome_palette)

        self._timer = QTimer(self, singleShot=True, interval=40)
        self._timer.timeout.connect(self.refresh)
        self.model.changed.connect(self._timer.start)
        self.refresh()

    # --- building ------------------------------------------------------------
    def _build_controls(self) -> QWidget:
        panel = QWidget()
        outer = QVBoxLayout(panel)
        top = QHBoxLayout()
        self.name_edit = QLineEdit(self.model.name)
        self.name_edit.textEdited.connect(lambda t: setattr(self.model, "name", t or "my_theme"))
        top.addWidget(self.name_edit, 1)
        open_btn = QToolButton()
        open_btn.setText("Open")
        open_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(open_btn)
        presets = menu.addMenu("Preset")
        from lace.dock_custom_theme import THEME_SPECS
        for key in THEME_SPECS:
            presets.addAction(key, lambda k=key: self.open_spec(THEME_SPECS[k], k))
        menu.addAction("JSON file...", self._open_json)
        open_btn.setMenu(menu)
        top.addWidget(open_btn)
        outer.addLayout(top)

        form = QFormLayout()
        self.seed_rows = {s: _SeedRow(self.model, s) for s in SEEDS}
        for s, row in self.seed_rows.items():
            form.addRow(s, row)
        self.keyword_boxes: Dict[str, QComboBox] = {}
        for k, values in KEYWORDS.items():
            box = QComboBox()
            box.addItems(list(values))
            box.textActivated.connect(lambda v, k=k: self.model.set_keyword(k, v))
            self.keyword_boxes[k] = box
            form.addRow(k, box)
        self.chassis_box = QComboBox()
        self.chassis_box.addItems(list(CHASSIS))
        self.chassis_box.textActivated.connect(self.model.set_chassis)
        form.addRow("chassis", self.chassis_box)
        self.tint_slider = QSlider(Qt.Orientation.Horizontal)
        self.tint_slider.setRange(0, 100)
        self.tint_slider.valueChanged.connect(lambda v: self.model.set_tint(v / 100))
        form.addRow("neutral tint", self.tint_slider)
        outer.addLayout(form)

        for text, slot in (("Save JSON...", self._save_json),
                           ("Copy ThemeSpec", self.copy_python)):
            b = QPushButton(text)
            b.clicked.connect(slot)
            outer.addWidget(b)
        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        outer.addWidget(self.status_label)
        outer.addStretch(1)
        return panel

    def _build_preview(self) -> QWidget:
        from lace.dock_manager import DockManager
        from lace.dock_theme_bridge import DockThemeBridge
        from lace.dock_widget import DockWidget
        from lace.enums import DockWidgetArea

        self.preview_tabs = QTabWidget()
        self.preview_host = QWidget()
        lay = QVBoxLayout(self.preview_host)
        lay.setContentsMargins(0, 0, 0, 0)
        self.dock_manager = DockManager(self.preview_host)
        lay.addWidget(self.dock_manager._root)
        # LaceStyle and the theme palette on the preview only.
        self.preview_bridge = DockThemeBridge(target=self.preview_host, parent=self)

        dm = self.dock_manager
        editor = DockWidget("Editor", self.preview_host)
        text = QTextEdit()
        text.setPlainText("The quick brown fox jumps over the lazy dog.\n" * 12)
        editor.set_widget(text)
        area = dm.add_dock_widget(DockWidgetArea.center, editor)
        controls = DockWidget("Controls", self.preview_host)
        controls.set_widget(_live_controls())
        dm.add_dock_widget(DockWidgetArea.center, controls, area)
        inspector = DockWidget("Inspector", self.preview_host)
        tree = QTreeWidget()
        tree.setHeaderLabels(["Name", "Value"])
        for i in range(8):
            item = QTreeWidgetItem(tree, [f"item {i}", str(i * 7)])
            QTreeWidgetItem(item, ["child", "-"])
        tree.expandToDepth(0)
        inspector.set_widget(tree)
        dm.add_dock_widget(DockWidgetArea.right, inspector)
        side = DockWidget("Outline", self.preview_host)
        side.set_widget(QLabel("Sidebar panel"))
        dm.add_sidebar_widget(DockWidgetArea.left, side)
        floater = DockWidget("Floating", self.preview_host)
        floater.set_widget(QLabel("A floating window"))
        self.floating = dm.floating_container_class()(dock_widget=floater, dock_manager=dm)
        self.floating.resize(300, 200)
        self.preview_tabs.addTab(self.preview_host, "Dock layout")

        gallery = QWidget()
        glay = QVBoxLayout(gallery)
        glay.setContentsMargins(0, 0, 0, 0)
        self._zoom_bar = QWidget()
        zlay = QHBoxLayout(self._zoom_bar)
        zlay.setContentsMargins(4, 2, 4, 2)
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(*ZOOMS)
        self.zoom_slider.setSingleStep(25)
        self.zoom_slider.setPageStep(50)
        self.zoom_label = QLabel()
        self.zoom_slider.valueChanged.connect(self._render_gallery)
        zlay.addWidget(QLabel("Zoom"))
        zlay.addWidget(self.zoom_slider, 1)
        zlay.addWidget(self.zoom_label)
        glay.addWidget(self._zoom_bar)
        self.gallery_view = QLabel()
        self.gallery_view.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        scroll = QScrollArea()
        scroll.setWidget(self.gallery_view)
        scroll.setWidgetResizable(True)
        glay.addWidget(scroll, 1)
        self.preview_tabs.addTab(gallery, "Controls")
        return self.preview_tabs

    def _build_panels(self) -> QTabWidget:
        tabs = QTabWidget()
        self.audit_tree = QTreeWidget()
        self.audit_tree.setHeaderLabels(["", "Token", "On", "Value", "Target", "Fix"])
        self.audit_tree.setRootIsDecorated(False)
        tabs.addTab(self.audit_tree, "Audit")
        strip = QWidget()
        slay = QHBoxLayout(strip)
        self.family_buttons: Dict[str, QPushButton] = {}
        for v in VARIANTS:
            b = QPushButton(v)
            b.setIconSize(b.iconSize() * 1.5)
            b.clicked.connect(lambda _=False, v=v: self.open_member(v))
            self.family_buttons[v] = b
            slay.addWidget(b)
        tabs.addTab(strip, "Family")
        self.diff_view = QPlainTextEdit()
        self.diff_view.setReadOnly(True)
        tabs.addTab(self.diff_view, "Diff")
        return tabs

    # --- refresh -------------------------------------------------------------
    def refresh(self) -> None:
        """Push the model's theme into the preview and every panel."""
        from lace.dock_style_manager import get_dock_style_manager
        m = self.model
        spec = m.spec()
        get_dock_style_manager().apply_theme_dict(build_theme(spec))
        self.preview_bridge.refresh_dock_palette()
        for row in self.seed_rows.values():
            row.sync()
        for k, box in self.keyword_boxes.items():
            box.setCurrentText(m.keywords[k])
        self.chassis_box.setCurrentText(m.chassis)
        self.tint_slider.blockSignals(True)
        self.tint_slider.setValue(round(m.tint * 100))
        self.tint_slider.blockSignals(False)
        self.name_edit.setText(m.name)
        self._render_gallery()
        self._fill_audit(m.report())
        self._fill_family()
        diff = m.diff()
        self.diff_view.setPlainText(
            "\n".join(f"{k:48} {'' if v is None else f'dE {v:.3f}'}" for k, v in diff.items())
            or "No change from the theme it started from.")
        fixes = ", ".join(sorted(m.fixes)) or "none"
        over = ", ".join(sorted(m.overrides)) or "none"
        self.status_label.setText(f"chassis {m.chassis}; overrides: {over}; fixes: {fixes}")

    def _render_gallery(self) -> None:
        from lace.dock_theme import build_dock_palette, resolve_dock_colors
        from lace.style.gallery import render
        zoom = self.zoom_slider.value()
        self.zoom_label.setText(f"{zoom} %")
        style = self.preview_bridge._style
        palette = build_dock_palette(is_panel=False, colors=resolve_dock_colors())
        self.gallery_view.setPixmap(QPixmap.fromImage(render(style, palette, scale=zoom / 100)))

    def _fill_audit(self, report: AuditReport) -> None:
        self.audit_tree.clear()
        head = ("PASS" if report.strict_passed else
                "PASS (capped colours)" if report.passed else "FAIL")
        QTreeWidgetItem(self.audit_tree, [head, f"contrast={report.contrast}",
                                          f"depth={report.depth}"])
        fixes = {s.token: s for s in report.suggest()}
        self.fix_buttons: List[QPushButton] = []
        for title, misses in (("failure", report.failures), ("capped", report.capped),
                              ("unreachable", report.unreachable)):
            for miss in misses:
                unit = ":1" if miss.kind == "contrast" else " dL"
                item = QTreeWidgetItem(self.audit_tree, [
                    title, miss.token, miss.surface, f"{miss.value}{unit}",
                    f"{miss.target}{unit}"])
                s = fixes.get(miss.token)
                if s is not None:
                    b = QPushButton(f"{_hex(s.old)} -> {_hex(s.new)}")
                    b.setIcon(_swatch([s.old, s.new], 12, 12))
                    b.clicked.connect(lambda _=False, s=s: self.fix(s))
                    self.audit_tree.setItemWidget(item, 5, b)
                    self.fix_buttons.append(b)
        for w in report.warnings:
            QTreeWidgetItem(self.audit_tree, ["warning", w.kind, "", w.message])
        for col in range(5):
            self.audit_tree.resizeColumnToContents(col)

    def _fill_family(self) -> None:
        own = variant_of(self.model.spec())
        self._family = self.model.family()
        for v, member in self._family.items():
            b = self.family_buttons[v]
            ok = audit(member).passed
            b.setIcon(_swatch([member.base, member.surface or member.base, member.accent,
                               member.text]))
            b.setText(f"{v}{' (this)' if v == own else ''}  {'pass' if ok else 'FAIL'}")

    # --- actions -------------------------------------------------------------
    def fix(self, suggestion: Suggestion) -> Optional[str]:
        field_name = self.model.apply_fix(suggestion)
        if field_name is None:
            self.status_label.setText(f"{suggestion.token} is derived, not a colour the "
                                      "theme sets; nothing to fix here.")
        return field_name

    def open_spec(self, spec: ThemeSpec, name: str) -> None:
        self.model.load(spec, name)

    def open_member(self, variant: str) -> None:
        member = self.model.family()[variant]
        base = self.model.name
        for v in VARIANTS:
            if base.endswith("_" + v):
                base = base[:-len(v) - 1]
        self.model.load(member, base if variant == "dark" else f"{base}_{variant}")

    def _open_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open theme", "", "Theme JSON (*.json)")
        if path:
            self.open_json(path)

    def open_json(self, path) -> None:
        from lace.theme_models import ThemeJson
        model = ThemeJson.load(path)
        self.model.load(model.to_theme_spec(), model.name or Path(path).stem)

    def _save_json(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save theme", f"{self.model.name}.json",
                                              "Theme JSON (*.json)")
        if path:
            self.model.to_json(path)
            self.status_label.setText(f"Saved {path}")

    def copy_python(self) -> str:
        text = self.model.to_python()
        QGuiApplication.clipboard().setText(text)
        self.status_label.setText("ThemeSpec copied to the clipboard.")
        return text

    def closeEvent(self, event) -> None:
        self.floating.close()
        super().closeEvent(event)


# ----------------------------------------------------------------------------------
# Entry points
# ----------------------------------------------------------------------------------
def launch(file: Optional[str] = None, preset: Optional[str] = None) -> subprocess.Popen:
    """Open the Studio in a process of its own, e.g. from a menu in a Lace
    app: the Studio's theme then never reaches the host."""
    cmd = [sys.executable, "-m", "lace.theme_kit", "studio"]
    if file:
        cmd.append(str(file))
    if preset:
        cmd += ["--preset", preset]
    return subprocess.Popen(cmd)


def run(spec: Optional[ThemeSpec] = None, name: str = "my_theme",
        screenshot: Optional[str] = None, tab: int = 0, zoom: int = 100) -> int:
    """Run the Studio in this process (``python -m lace.theme_kit studio``).
    With ``screenshot``, save the window to that PNG and quit."""
    app = QApplication.instance() or QApplication(sys.argv)
    win = StudioWindow(spec, name)
    win.preview_tabs.setCurrentIndex(tab)
    win.zoom_slider.setValue(zoom)
    win.show()
    if screenshot:
        for _ in range(6):
            app.processEvents()
        win.refresh()
        app.processEvents()
        ok = win.grab().save(screenshot)
        win.close()
        return 0 if ok else 1
    return app.exec()


__all__ = ["StudioModel", "StudioWindow", "launch", "run"]
