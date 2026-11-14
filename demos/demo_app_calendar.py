# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.

"""Calendar popup testbed.

A small dock layout for checking the rounded calendar popups of QDateEdit and
QDateTimeEdit, next to an inline QCalendarWidget. The theme switcher makes it
easy to compare the popup on the classic and neo chassis.
"""

import sys
from pathlib import Path

from PySide6.QtCore import QDate, QDateTime, Qt
from PySide6.QtWidgets import (
    QApplication, QCalendarWidget, QComboBox, QDateEdit, QDateTimeEdit,
    QFormLayout, QGroupBox, QLabel, QMainWindow, QVBoxLayout, QWidget,
)

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from lace import (  # noqa: E402
    DockManager, DockWidget, DockWidgetArea, LaceStyle, apply_dock_theme,
    theme_choices,
)


class CalendarDemoWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Lace — Calendar Popup Testbed")
        self.resize(1100, 800)

        self.dock_manager = DockManager(self)
        self.setCentralWidget(self.dock_manager.root_container())

        calendar_dock = DockWidget("Calendar Popups", self)
        calendar_dock.set_widget(self._build_calendar_panel())
        self.dock_manager.add_dock_widget(DockWidgetArea.center, calendar_dock)

        appearance_dock = DockWidget("Appearance", self)
        appearance_dock.set_widget(self._build_appearance_panel())
        self.dock_manager.add_dock_widget(DockWidgetArea.right, appearance_dock)

        notes_dock = DockWidget("Notes", self)
        notes_dock.set_widget(self._build_notes())
        self.dock_manager.add_dock_widget(DockWidgetArea.bottom, notes_dock)

        self._apply_theme()

    def _build_calendar_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        intro = QLabel(
            "Click the drop-down arrow at the right of either field. The calendar "
            "popup should have a rounded panel, a soft shadow and rounded "
            "navigation-bar corners. The inline calendar below is not a popup."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()
        form.setSpacing(8)

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("dddd, d MMMM yyyy")
        self.date_edit.setMinimumWidth(280)
        form.addRow("QDateEdit:", self.date_edit)

        self.datetime_edit = QDateTimeEdit(QDateTime.currentDateTime())
        self.datetime_edit.setCalendarPopup(True)
        self.datetime_edit.setDisplayFormat("dddd, d MMMM yyyy  HH:mm")
        self.datetime_edit.setMinimumWidth(280)
        form.addRow("QDateTimeEdit:", self.datetime_edit)
        layout.addLayout(form)

        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.date_edit.dateChanged.connect(self._sync_status)
        self.datetime_edit.dateTimeChanged.connect(self._sync_status)
        self._sync_status()

        group = QGroupBox("Inline QCalendarWidget (not rounded as a popup)")
        group_layout = QVBoxLayout(group)
        self.inline_calendar = QCalendarWidget()
        self.inline_calendar.setGridVisible(False)
        self.inline_calendar.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        group_layout.addWidget(self.inline_calendar)
        layout.addWidget(group, 1)

        return panel

    def _build_appearance_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(QLabel("Theme"))
        self.theme_combo = QComboBox()
        for label, key in theme_choices():
            self.theme_combo.addItem(label, key)
        index = self.theme_combo.findData("dark_neo")
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
        self.theme_combo.currentIndexChanged.connect(self._apply_theme)
        layout.addWidget(self.theme_combo)
        layout.addWidget(QLabel(
            "Try a classic theme and its neo counterpart: the popup radius follows "
            "control_radius / corner_radius."
        ))
        layout.addStretch(1)
        return panel

    def _build_notes(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 8, 12, 8)
        note = QLabel(
            "Expected: the popup is inset from its window edge, with a shadow in "
            "the margin; the calendar is masked to the rounded panel. It opens "
            "below the field, and above it when there is no room below. Selecting "
            "a date closes the popup and updates the status line."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        return panel

    def _sync_status(self) -> None:
        self.status.setText(
            f"Date: {self.date_edit.date().toString(Qt.DateFormat.ISODate)}   |   "
            f"Date/time: {self.datetime_edit.dateTime().toString('yyyy-MM-dd HH:mm')}"
        )

    def _apply_theme(self) -> None:
        key = self.theme_combo.currentData()
        if key:
            apply_dock_theme(key)


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle(LaceStyle())
    window = CalendarDemoWindow()
    window.show()
    sys.exit(app.exec())
