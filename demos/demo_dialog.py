# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.

"""A custom dialog for the demos: ``FramelessLaceDialog`` with your own widgets.

The dialog gets the main window's themed title bar and follows theme
switches; everything below the bar is ordinary Qt, built in
``contentLayout()``.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QColorDialog, QComboBox, QDialogButtonBox, QFormLayout,
    QGroupBox, QHBoxLayout, QLineEdit, QPushButton, QRadioButton, QSlider, QSpinBox,
    QWidget,
)

from lace import dialogs
from lace.frameless_dialog import FramelessLaceDialog


class NewLayerDialog(FramelessLaceDialog):
    """Name, type, colour, opacity, blend mode and options for a new layer."""

    def __init__(self, parent: QWidget = None):
        super().__init__(parent, resizable=False)
        self.setWindowTitle("New layer")
        self._color = QColor("#3d8bfd")

        layout = self.contentLayout()
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        form = QFormLayout()
        self.name_edit = QLineEdit("Layer 4")
        self.name_edit.selectAll()
        form.addRow("Name:", self.name_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Raster", "Vector", "Adjustment", "Group"])
        form.addRow("Type:", self.type_combo)

        self.color_button = QPushButton()
        self.color_button.clicked.connect(self._pick_color)
        self._show_color()
        form.addRow("Colour:", self.color_button)

        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(0, 100)
        self.opacity_spin = QSpinBox()
        self.opacity_spin.setRange(0, 100)
        self.opacity_spin.setSuffix(" %")
        self.opacity_slider.valueChanged.connect(self.opacity_spin.setValue)
        self.opacity_spin.valueChanged.connect(self.opacity_slider.setValue)
        self.opacity_slider.setValue(80)
        opacity = QHBoxLayout()
        opacity.addWidget(self.opacity_slider, 1)
        opacity.addWidget(self.opacity_spin)
        form.addRow("Opacity:", opacity)
        layout.addLayout(form)

        blend_box = QGroupBox("Blend mode")
        blend_row = QHBoxLayout(blend_box)
        self.blend_group = QButtonGroup(self)
        for i, name in enumerate(("Normal", "Multiply", "Screen", "Overlay")):
            radio = QRadioButton(name)
            radio.setChecked(i == 0)
            self.blend_group.addButton(radio, i)
            blend_row.addWidget(radio)
        layout.addWidget(blend_box)

        options = QHBoxLayout()
        self.visible_check = QCheckBox("Visible")
        self.visible_check.setChecked(True)
        self.locked_check = QCheckBox("Locked")
        self.clip_check = QCheckBox("Clip to layer below")
        for check in (self.visible_check, self.locked_check, self.clip_check):
            options.addWidget(check)
        options.addStretch(1)
        layout.addLayout(options)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Create")
        buttons.accepted.connect(self._create)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # -- colour --------------------------------------------------------------

    def _show_color(self) -> None:
        swatch = QPixmap(14, 14)
        swatch.fill(self._color)
        self.color_button.setIcon(QIcon(swatch))
        self.color_button.setText(self._color.name().upper())

    def _pick_color(self) -> None:
        # The helper opens another themed dialog on top of this one.
        color = dialogs.get_color(self._color, self, "Layer colour",
                                  QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            self._color = color
            self._show_color()

    # -- result --------------------------------------------------------------

    def _create(self) -> None:
        if not self.name_edit.text().strip():
            dialogs.warning(self, "New layer", "The layer needs a name.")
            self.name_edit.setFocus()
            return
        self.accept()

    def values(self) -> dict:
        """The chosen settings."""
        return {
            "name": self.name_edit.text().strip(),
            "type": self.type_combo.currentText(),
            "colour": self._color.name(QColor.NameFormat.HexArgb),
            "opacity": self.opacity_spin.value(),
            "blend": self.blend_group.checkedButton().text(),
            "visible": self.visible_check.isChecked(),
            "locked": self.locked_check.isChecked(),
            "clip": self.clip_check.isChecked(),
        }


def open_new_layer_dialog(parent: QWidget = None) -> None:
    """Open :class:`NewLayerDialog` modally and report what was chosen."""
    dialog = NewLayerDialog(parent)
    try:
        if dialog.exec() != NewLayerDialog.DialogCode.Accepted:
            return
        summary = "<br>".join(f"<b>{k}</b>: {v}" for k, v in dialog.values().items())
    finally:
        dialog.deleteLater()
    dialogs.information(parent, "Layer created", summary)


__all__ = ["NewLayerDialog", "open_new_layer_dialog"]
