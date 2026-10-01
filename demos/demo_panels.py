# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.

"""Panel contents for the demos: each dock carries its feature note plus a
set of everyday widgets, so a theme's look is easy to judge at a glance.

Content is deterministic (no random data) so screenshots compare like for
like across runs and themes.
"""

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCalendarWidget, QCheckBox, QComboBox, QDateEdit, QDial,
    QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMenu, QProgressBar, QPushButton, QRadioButton, QSlider,
    QSpinBox, QSplitter, QStyle, QTableWidget, QTableWidgetItem, QTabWidget, QTextEdit,
    QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)


# ── building blocks ────────────────────────────────────────────────────

def note(text: str) -> QLabel:
    """The panel's feature note: what the dock can and cannot do."""
    label = QLabel(text)
    label.setWordWrap(True)
    label.setObjectName("featureNote")
    return label


def panel(note_text: str, *items, stretch_last: bool = True) -> QWidget:
    """A column: the feature note, then ``items`` (widgets or layouts)."""
    w = QWidget()
    col = QVBoxLayout(w)
    col.setContentsMargins(8, 8, 8, 8)
    col.setSpacing(8)
    col.addWidget(note(note_text))
    for i, item in enumerate(items):
        stretch = 1 if stretch_last and i == len(items) - 1 else 0
        if isinstance(item, QWidget):
            col.addWidget(item, stretch)
        else:
            col.addLayout(item, stretch)
    if not stretch_last:
        col.addStretch(1)
    return w


def _icon(name: str):
    return QApplication.style().standardIcon(getattr(QStyle.StandardPixmap, name))


def _check(text: str, state=Qt.CheckState.Unchecked, enabled: bool = True,
           tristate: bool = False) -> QCheckBox:
    box = QCheckBox(text)
    box.setTristate(tristate)
    box.setCheckState(state)
    box.setEnabled(enabled)
    return box


# ── widget groups ──────────────────────────────────────────────────────

def options_group() -> QGroupBox:
    """Check boxes in every state."""
    box = QGroupBox("Options")
    col = QVBoxLayout(box)
    col.addWidget(_check("Auto-save", Qt.CheckState.Checked))
    col.addWidget(_check("Show hidden files"))
    col.addWidget(_check("Partially selected", Qt.CheckState.PartiallyChecked, tristate=True))
    col.addWidget(_check("Disabled (on)", Qt.CheckState.Checked, enabled=False))
    return box


def mode_group() -> QGroupBox:
    """Radio buttons, one disabled, in a checkable group box."""
    box = QGroupBox("Render mode")
    box.setCheckable(True)
    col = QVBoxLayout(box)
    for i, text in enumerate(("Solid", "Wireframe", "Points (unavailable)")):
        radio = QRadioButton(text)
        radio.setChecked(i == 0)
        radio.setEnabled(i < 2)
        col.addWidget(radio)
    return box


def level_group() -> QGroupBox:
    """A flat group box: slider, spin box and progress bar."""
    box = QGroupBox("Level")
    box.setFlat(True)
    col = QVBoxLayout(box)
    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setRange(0, 100)
    slider.setValue(60)
    spin = QSpinBox()
    spin.setRange(0, 100)
    spin.setValue(60)
    spin.setSuffix(" %")
    bar = QProgressBar()
    bar.setValue(60)
    slider.valueChanged.connect(spin.setValue)
    slider.valueChanged.connect(bar.setValue)
    spin.valueChanged.connect(slider.setValue)
    row = QHBoxLayout()
    row.addWidget(slider, 1)
    row.addWidget(spin)
    col.addLayout(row)
    col.addWidget(bar)
    return box


def button_row(on_dialog=None) -> QVBoxLayout:
    """Two rows: push buttons (default, plain, checkable, disabled) and flat
    buttons; then a tool button with a menu, a combo box and a search field.

    With *on_dialog*, a "Dialog…" button after the toggle calls it.
    """
    rows = QVBoxLayout()
    row = QHBoxLayout()
    rows.addLayout(row)
    default = QPushButton("Default")
    default.setDefault(True)
    row.addWidget(default)
    row.addWidget(QPushButton("Apply"))
    toggle = QPushButton("Toggle")
    toggle.setCheckable(True)
    toggle.setChecked(True)
    row.addWidget(toggle)
    if on_dialog is not None:
        dialog = QPushButton("Dialog…")
        dialog.setToolTip("Open a custom FramelessLaceDialog")
        dialog.clicked.connect(lambda: on_dialog())
        row.addWidget(dialog)
    disabled = QPushButton("Disabled")
    disabled.setEnabled(False)
    row.addWidget(disabled)
    for text in ("Flat", "Flat link"):
        flat = QPushButton(text)
        flat.setFlat(True)
        row.addWidget(flat)
    row.addStretch(1)
    row = QHBoxLayout()
    rows.addLayout(row)
    tool = QToolButton()
    tool.setText("Tools")
    tool.setIcon(_icon("SP_FileDialogDetailedView"))
    tool.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    tool.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
    tool.setAutoRaise(True)
    menu = QMenu(tool)
    for text in ("Cut", "Copy", "Paste"):
        menu.addAction(text)
    tool.setMenu(menu)
    row.addWidget(tool)
    combo = QComboBox()
    combo.addItems(["Release", "Debug", "Profile"])
    row.addWidget(combo)
    search = QLineEdit()
    search.setPlaceholderText("Search…")
    search.setClearButtonEnabled(True)
    row.addWidget(search, 1)
    return rows


def project_tree() -> QTreeWidget:
    tree = QTreeWidget()
    tree.setHeaderLabels(["Name", "Size"])
    tree.setAlternatingRowColors(True)
    folder, doc = _icon("SP_DirIcon"), _icon("SP_FileIcon")
    for name, files in (("src", ("main.py", "window.py", "theme.py")),
                        ("assets", ("icon.svg", "splash.png")),
                        ("docs", ("README.md",))):
        parent = QTreeWidgetItem(tree, [name, ""])
        parent.setIcon(0, folder)
        for i, f in enumerate(files):
            child = QTreeWidgetItem(parent, [f, f"{(i + 1) * 3.2:.1f} KB"])
            child.setIcon(0, doc)
            child.setCheckState(0, Qt.CheckState.Checked if i % 2 == 0 else Qt.CheckState.Unchecked)
    tree.expandAll()
    tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    tree.setCurrentItem(tree.topLevelItem(0).child(1))
    return tree


def data_table(rows: int = 8) -> QTableWidget:
    headers = ["Sample", "Value", "Unit", "Status"]
    table = QTableWidget(rows, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSortingEnabled(True)
    status = ("ok", "ok", "warn", "ok", "fail", "ok", "warn", "ok")
    for r in range(rows):
        table.setItem(r, 0, QTableWidgetItem(f"S-{r + 1:03d}"))
        table.setItem(r, 1, QTableWidgetItem(f"{12.5 + r * 3.75:.2f}"))
        table.setItem(r, 2, QTableWidgetItem("mV"))
        table.setItem(r, 3, QTableWidgetItem(status[r % len(status)]))
    table.horizontalHeader().setStretchLastSection(True)
    table.verticalHeader().setVisible(False)
    table.selectRow(2)
    return table


def item_list() -> QListWidget:
    lst = QListWidget()
    lst.setAlternatingRowColors(True)
    icons = ("SP_DriveHDIcon", "SP_DirHomeIcon", "SP_DesktopIcon", "SP_TrashIcon",
             "SP_ComputerIcon", "SP_DriveNetIcon")
    for i, name in enumerate(("Local disk", "Home", "Desktop", "Trash", "This computer", "Network")):
        item = QListWidgetItem(_icon(icons[i]), name)
        if i == 4:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
        lst.addItem(item)
    lst.setCurrentRow(1)
    return lst


def properties_form() -> QGroupBox:
    box = QGroupBox("Properties")
    form = QFormLayout(box)
    name = QLineEdit("Canvas A")
    form.addRow("Name:", name)
    width = QDoubleSpinBox()
    width.setRange(0, 10000)
    width.setValue(1920)
    width.setSuffix(" px")
    form.addRow("Width:", width)
    date = QDateEdit(QDate(2026, 9, 28))
    date.setCalendarPopup(True)
    form.addRow("Created:", date)
    blend = QComboBox()
    blend.addItems(["Normal", "Multiply", "Screen", "Overlay"])
    form.addRow("Blend:", blend)
    locked = QLineEdit("read-only value")
    locked.setReadOnly(True)
    form.addRow("Id:", locked)
    off = QLineEdit("disabled field")
    off.setEnabled(False)
    form.addRow("Legacy:", off)
    return box


def dial_row() -> QHBoxLayout:
    row = QHBoxLayout()
    for value in (25, 70):
        dial = QDial()
        dial.setRange(0, 100)
        dial.setValue(value)
        dial.setNotchesVisible(True)
        dial.setFixedSize(64, 64)
        row.addWidget(dial)
    vslider = QSlider(Qt.Orientation.Vertical)
    vslider.setValue(40)
    vslider.setFixedHeight(64)
    row.addWidget(vslider)
    row.addStretch(1)
    return row


# ── panels, one per demo dock ──────────────────────────────────────────

def controls_panel(note_text: str) -> QWidget:
    """Check boxes, radio buttons and a flat group box."""
    return panel(note_text, options_group(), mode_group(), level_group(), stretch_last=False)


def note_panel(note_text: str) -> QLabel:
    """Just the note, centred: for short areas where nothing else fits."""
    label = note(note_text)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


def editor_panel(editor: QWidget, on_dialog=None) -> QWidget:
    """An editor under a toolbar row of buttons and inputs.

    *on_dialog* adds a "Dialog…" button to the row (see :func:`button_row`).
    """
    w = QWidget()
    col = QVBoxLayout(w)
    col.setContentsMargins(6, 6, 6, 6)
    col.setSpacing(6)
    col.addLayout(button_row(on_dialog))
    col.addWidget(editor, 1)
    return w


def data_panel(note_text: str) -> QWidget:
    """A tree and a table in a vertical splitter."""
    split = QSplitter(Qt.Orientation.Vertical)
    split.addWidget(project_tree())
    split.addWidget(data_table())
    split.setChildrenCollapsible(False)
    split.setStretchFactor(1, 1)
    return panel(note_text, split)


def tabs_panel(note_text: str) -> QWidget:
    """Tabs: a list, a form and a read-only log."""
    tabs = QTabWidget()
    tabs.addTab(item_list(), _icon("SP_DirIcon"), "Places")
    tabs.addTab(properties_form(), "Form")
    log = QTextEdit()
    log.setReadOnly(True)
    log.setPlainText("\n".join(f"[{i:02d}] step {i} done" for i in range(1, 16)))
    tabs.addTab(log, "Log")
    return panel(note_text, tabs)


def design_panel(note_text: str) -> QWidget:
    """A list and a properties form side by side in a splitter."""
    split = QSplitter(Qt.Orientation.Horizontal)
    split.addWidget(item_list())
    right = QWidget()
    col = QVBoxLayout(right)
    col.setContentsMargins(0, 0, 0, 0)
    col.addWidget(properties_form())
    col.addLayout(dial_row())
    col.addStretch(1)
    split.addWidget(right)
    split.setStretchFactor(1, 1)
    return panel(note_text, split)


def calendar_panel(note_text: str) -> QWidget:
    cal = QCalendarWidget()
    cal.setSelectedDate(QDate(2026, 9, 28))
    cal.setGridVisible(True)
    return panel(note_text, cal)


def logger_panel(text: str) -> QWidget:
    """A read-only log with a filter row under it."""
    log = QTextEdit()
    log.setReadOnly(True)
    log.setText(text)
    row = QHBoxLayout()
    level = QComboBox()
    level.addItems(["Info", "Warning", "Error"])
    row.addWidget(level)
    flt = QLineEdit()
    flt.setPlaceholderText("Filter…")
    row.addWidget(flt, 1)
    clear = QPushButton("Clear")
    clear.setFlat(True)
    clear.clicked.connect(log.clear)
    row.addWidget(clear)
    w = QWidget()
    col = QVBoxLayout(w)
    col.setContentsMargins(0, 0, 0, 0)
    col.setSpacing(4)
    col.addWidget(log, 1)
    col.addLayout(row)
    return w


def sidebar_layers_panel(note_text: str) -> QWidget:
    layers = QWidget()
    col = QVBoxLayout(layers)
    col.setContentsMargins(0, 0, 0, 0)
    for i, name in enumerate(("Background", "Grid", "Guides", "Annotations")):
        col.addWidget(_check(name, Qt.CheckState.Checked if i != 2 else Qt.CheckState.Unchecked))
    return panel(note_text, layers, level_group(), stretch_last=False)


def sidebar_tree_panel(note_text: str) -> QWidget:
    return panel(note_text, project_tree())


__all__ = [
    "calendar_panel", "controls_panel", "data_panel", "design_panel", "logger_panel",
    "editor_panel", "note", "note_panel", "panel", "sidebar_layers_panel",
    "sidebar_tree_panel", "tabs_panel",
]
