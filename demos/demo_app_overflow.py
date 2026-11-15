# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.

"""Tab overflow testbed.

Exercises the cramped tab minimum, the automatic ``‹ ›`` arrows, wheel
scrolling and the title/description tooltips. Resize the window to move
between the roomy, cramped and genuinely overflowing states.
"""

import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QPushButton, QStyle, QVBoxLayout, QWidget,
)

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lace import (  # noqa: E402
    DockFlags, DockManager, DockWidget, DockWidgetArea, LaceStyle,
    apply_dock_theme, theme_choices,
)


class OverflowDemoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lace — Tab Overflow Testbed")
        self.resize(1280, 800)

        self.manager = DockManager(self)
        self.setCentralWidget(self.manager.root_container())
        self.docks = []
        self.sidebar_docks = []
        self._next = 0
        self.area = None

        first = self._make_dock(
            "Build Output",
            description="Compiler and linker output",
            body="The first tab. It has a description, so its tooltip shows even when the title fits.",
        )
        self.area = self.manager.add_dock_widget(DockWidgetArea.center, first)
        self.docks.append(first)

        for title, description in (
            ("A very long diagnostics panel title", ""),
            ("Log", "Runtime log messages"),
            ("Explorer", "Project files"),
            ("Search Results", "Matches from the current workspace"),
            ("Problems", "Errors and warnings"),
            ("Terminal", "Interactive shell"),
            ("Outline", "Symbols in the active document"),
            ("Timeline", "Recent activity"),
            ("Testing", "Test runs and results"),
            ("Extensions", "Installed extensions"),
            ("References", "Find all references"),
        ):
            self._add_tab(title, description)

        self.controls = DockWidget("Controls", self)
        self.controls.set_widget(self._build_controls())
        self.manager.add_dock_widget(DockWidgetArea.right, self.controls)
        self.area.current_changed.connect(self._sync_editor)
        self._build_sidebar_tabs()

        self._apply_theme()
        self._sync_editor()
        self._timer = QTimer(self)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._refresh_status)
        self._timer.start()
        self._refresh_status()

    def _build_sidebar_tabs(self):
        """Fill the left sidebar past its height so its own arrows appear."""
        sidebar = self.manager.sidebar_manager
        sidebar.set_animations_enabled(False)
        sidebar.add_sidebar(DockWidgetArea.left)
        for i in range(14):
            dock = self._make_dock(
                f"Sidebar {i + 1:02d}",
                description=f"Pinned panel {i + 1}",
                body=f"Sidebar panel {i + 1}. Scroll with the wheel or the bar's arrows.",
            )
            self.manager.add_dock_widget(
                DockWidgetArea.center, dock, target_area=self.area)
            sidebar.pin_widget(dock, area=DockWidgetArea.left)
            self.sidebar_docks.append(dock)

    def _make_dock(self, title, *, description="", body="", icon_only=False):
        dock = DockWidget(title, description=description)
        if icon_only:
            dock.setObjectName(f"icon-only-{self._next}")
            dock.set_icon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon))
        dock.set_widget(QLabel(body or f"Content for {title or 'the icon-only tab'}."))
        return dock

    def _add_tab(self, title=None, description="", icon_only=False):
        self._next += 1
        if title is None:
            title = f"Tab {self._next}"
        dock = self._make_dock(title, description=description, icon_only=icon_only)
        self.area = self.manager.add_dock_widget(
            DockWidgetArea.center, dock, target_area=self.area)
        self.docks.append(dock)
        QTimer.singleShot(0, self._refresh_status)

    def _build_controls(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        intro = QLabel(
            "The center tabs stop at twice their eliding width, so the ‹ › "
            "arrows appear before the two-character minimum. The left sidebar "
            "is deliberately overfilled so its own up/down overflow arrows "
            "show. Try the wheel over a tab, the strip, and the arrows."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.flag_check = QCheckBox("Automatic tab scroll arrows")
        self.flag_check.setChecked(
            DockFlags.dock_area_has_tab_scroll_buttons in self.manager.config_flags)
        self.flag_check.toggled.connect(self._set_scroll_flag)
        layout.addWidget(self.flag_check)

        buttons = QHBoxLayout()
        for text, slot in (
            ("Add tab", self._add_short),
            ("Add long title", self._add_long),
            ("Add icon-only", self._add_icon_only),
            ("Remove active", self._remove_active),
        ):
            button = QPushButton(text)
            button.clicked.connect(slot)
            buttons.addWidget(button)
        layout.addLayout(buttons)

        edit_group = QGroupBox("Active tab")
        form = QFormLayout(edit_group)
        self.title_edit = QLineEdit()
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText(
            "Optional description; forces the composed tooltip")
        form.addRow("Title", self.title_edit)
        form.addRow("Description", self.description_edit)
        apply_button = QPushButton("Apply to active tab")
        apply_button.clicked.connect(self._apply_editor)
        form.addRow(apply_button)
        layout.addWidget(edit_group)

        theme_group = QGroupBox("Appearance")
        theme_form = QFormLayout(theme_group)
        self.theme_combo = QComboBox()
        for label, key in theme_choices():
            self.theme_combo.addItem(label, key)
        index = self.theme_combo.findData("dark_neo")
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        self.theme_combo.currentIndexChanged.connect(self._apply_theme)
        theme_form.addRow("Theme", self.theme_combo)
        layout.addWidget(theme_group)

        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        layout.addStretch(1)
        return panel

    def _current_dock(self):
        return self.area.current_dock_widget() if self.area else None

    def _sync_editor(self, *_args):
        dock = self._current_dock()
        if dock is None:
            self.title_edit.clear()
            self.description_edit.clear()
            return
        self.title_edit.setText(dock.windowTitle())
        self.description_edit.setText(dock.description())

    def _apply_editor(self):
        dock = self._current_dock()
        if dock is None:
            return
        dock.setWindowTitle(self.title_edit.text())
        dock.set_description(self.description_edit.text())
        self._refresh_status()

    def _add_short(self):
        self._add_tab(description="" if self._next % 3 else "Short tab description")

    def _add_long(self):
        self._add_tab(
            f"A long tab title number {self._next} that will elide gracefully",
            description="A description survives even when the title is long")

    def _add_icon_only(self):
        self._add_tab("", icon_only=True)

    def _remove_active(self):
        dock = self._current_dock()
        if dock is None or len(self.docks) <= 1:
            return
        self.docks.remove(dock)
        self.manager.remove_dock_widget(dock)
        self._sync_editor()
        QTimer.singleShot(0, self._refresh_status)

    def _set_scroll_flag(self, enabled: bool):
        flags = self.manager.config_flags
        if enabled:
            flags |= DockFlags.dock_area_has_tab_scroll_buttons
        else:
            flags &= ~DockFlags.dock_area_has_tab_scroll_buttons
        self.manager.config_flags = flags
        QTimer.singleShot(0, self._refresh_status)

    def _apply_theme(self):
        key = self.theme_combo.currentData()
        if key:
            apply_dock_theme(key)

    def _refresh_status(self):
        if not self.area:
            self.status.setText("No dock area")
            return
        bar = self.area._title_bar.tab_bar()
        if bar is None:
            return
        tab = bar.current_tab()
        if tab is None:
            self.status.setText("No active tab")
            return
        arrows = self.area._title_bar._tab_scroll_left
        self.status.setText(
            f"Tabs: {bar.count()}   |   Range: {bar.horizontalScrollBar().minimum()}-"
            f"{bar.horizontalScrollBar().maximum()}   |   Overflow: "
            f"{'yes' if bar.is_overflowing() else 'no'}\n"
            f"Arrows: {'visible' if arrows.isVisible() else 'hidden'}   |   "
            f"Cramped minimum: {tab.minimumWidth()} px "
            f"(layout minimum {tab.layout().minimumSize().width()} px)\n"
            f"Active tooltip: {tab.toolTip()!r}")


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle(LaceStyle())
    window = OverflowDemoWindow()
    window.show()
    sys.exit(app.exec())
