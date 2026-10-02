# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.

"""Themed drop-ins for Qt's static dialog helpers.

Each helper opens a :class:`.frameless_dialog.FramelessLaceDialog`, so the
dialog carries the main window's themed title bar, and returns what the Qt
static it mirrors returns. Migrating is a rename::

    QMessageBox.question(self, "Close", "Discard changes?")
    lace.dialogs.question(self, "Close", "Discard changes?")

| Helper | Qt counterpart | Returns |
|---|---|---|
| :func:`message`, :func:`information`, :func:`question`, :func:`warning`, :func:`critical` | ``QMessageBox`` statics | ``QMessageBox.StandardButton`` |
| :func:`about` | ``QMessageBox.about`` | ``None`` |
| :func:`get_text`, :func:`get_item`, :func:`get_int`, :func:`get_double` | ``QInputDialog`` statics | ``(value, ok)`` |
| :func:`get_color` | ``QColorDialog.getColor`` | ``QColor``, invalid on cancel |
| :func:`get_open_file_name`, :func:`get_open_file_names`, :func:`get_save_file_name`, :func:`get_existing_directory` | ``QFileDialog`` statics | as Qt |

The message helpers build their own body (icon, text, ``QDialogButtonBox``);
the others embed the Qt dialog as a widget. The file helpers default to the
OS dialog (``native=True``), which Lace can't theme beyond light/dark (see
:mod:`lace.native_frame`); ``native=False`` embeds Qt's own file dialog.

:func:`set_default_frameless` (``False``) makes every helper call the plain
Qt static instead. So does a missing ``qframelesswindow``.
"""

from __future__ import annotations

from typing import Callable, List, Optional, Sequence, Tuple, Union

from PySide6 import QtGui
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QTextDocument
from PySide6.QtWidgets import (QApplication, QColorDialog, QDialog,
                               QDialogButtonBox, QFileDialog, QHBoxLayout,
                               QInputDialog, QLabel, QLineEdit, QMessageBox,
                               QStyle, QWidget)

_frameless_default = True

#: ``QMessageBox.StandardButton``, so callers can compare results without
#: importing it: ``dialogs.question(...) == dialogs.StandardButton.Yes``.
StandardButton = QMessageBox.StandardButton
_Buttons = Union[QMessageBox.StandardButton, QDialogButtonBox.StandardButton, int]

#: ``icon=`` names for :func:`message`, with their ``QMessageBox.Icon``.
MESSAGE_ICONS = {
    "none": QMessageBox.Icon.NoIcon,
    "information": QMessageBox.Icon.Information,
    "question": QMessageBox.Icon.Question,
    "warning": QMessageBox.Icon.Warning,
    "critical": QMessageBox.Icon.Critical,
}

_ICON_PIXMAPS = {
    QMessageBox.Icon.Information: QStyle.StandardPixmap.SP_MessageBoxInformation,
    QMessageBox.Icon.Question: QStyle.StandardPixmap.SP_MessageBoxQuestion,
    QMessageBox.Icon.Warning: QStyle.StandardPixmap.SP_MessageBoxWarning,
    QMessageBox.Icon.Critical: QStyle.StandardPixmap.SP_MessageBoxCritical,
}

# The widest a message's text grows before it wraps, in logical pixels.
_MESSAGE_TEXT_WIDTH = 420


def set_default_frameless(enabled: bool) -> None:
    """``False`` makes every helper call the plain Qt static function.

    Those dialogs keep the OS frame, which :mod:`lace.native_frame` still
    colours on Windows.
    """
    global _frameless_default
    _frameless_default = bool(enabled)


def default_frameless() -> bool:
    """Whether the helpers open frameless themed dialogs."""
    return _frameless_default


def _host_class():
    """``FramelessLaceDialog``, or ``None`` to fall back to Qt."""
    if not _frameless_default:
        return None
    try:
        from lace.frameless_dialog import FramelessLaceDialog
    except ImportError:
        return None
    return FramelessLaceDialog


def _host(parent, title: str, resizable: bool = False):
    cls = _host_class()
    dialog = cls(parent, resizable=resizable)
    dialog.setWindowTitle(title)
    return dialog


def _value(buttons: _Buttons) -> int:
    return buttons if isinstance(buttons, int) else buttons.value


def _embed(host, inner: QDialog) -> None:
    """Put Qt dialog *inner* inside *host* as a plain widget.

    The inner dialog's accept/reject (its buttons, Escape) close the host.
    """
    inner.setWindowFlags(Qt.WindowType.Widget)
    inner.setSizeGripEnabled(False)
    host.setContentWidget(inner)
    inner.accepted.connect(host.accept)
    inner.rejected.connect(host.reject)
    # A QDialog keeps itself hidden until shown, even as a child widget.
    inner.show()


def _exec(host) -> int:
    try:
        return host.exec()
    finally:
        host.deleteLater()


# -- message boxes --------------------------------------------------------------

def _escape_button(box: QDialogButtonBox):
    """The button Escape answers with, by ``QMessageBox``'s rules.

    The only button; else the only RejectRole button; else the only NoRole
    button; else none.
    """
    buttons = box.buttons()
    if len(buttons) == 1:
        return buttons[0]
    for role in (QDialogButtonBox.ButtonRole.RejectRole,
                 QDialogButtonBox.ButtonRole.NoRole):
        matches = [b for b in buttons if box.buttonRole(b) == role]
        if len(matches) == 1:
            return matches[0]
    return None


def _default_button(box: QDialogButtonBox, default: int):
    if default:
        button = box.button(QDialogButtonBox.StandardButton(default))
        if button is not None:
            return button
    for role in (QDialogButtonBox.ButtonRole.AcceptRole,
                 QDialogButtonBox.ButtonRole.YesRole):
        for button in box.buttons():
            if box.buttonRole(button) == role:
                return button
    buttons = box.buttons()
    return buttons[0] if buttons else None


def _message_icon(icon) -> QMessageBox.Icon:
    if isinstance(icon, QMessageBox.Icon):
        return icon
    try:
        return MESSAGE_ICONS[icon]
    except KeyError:
        raise ValueError(
            f"icon must be one of {tuple(MESSAGE_ICONS)} or a QMessageBox.Icon, "
            f"got {icon!r}") from None


def _text_width(label: QLabel) -> int:
    """The unwrapped width of *label*'s text as it renders.

    Rich text is laid out first, so markup and ``<br>`` don't count as
    width; plain text is measured line by line.
    """
    text = label.text()
    # PySide6 exposes mightBeRichText on QtGui's Qt namespace only.
    if QtGui.Qt.mightBeRichText(text):
        doc = QTextDocument()
        doc.setDefaultFont(label.font())
        doc.setDocumentMargin(0)
        doc.setHtml(text)
        return int(doc.idealWidth() + 0.5)
    lines = text.splitlines() or [""]
    return max(label.fontMetrics().horizontalAdvance(line) for line in lines)


def _message_body(host, text: str, icon: QMessageBox.Icon,
                  pixmap_icon: Optional[QIcon] = None) -> QLabel:
    layout = host.contentLayout()
    style = host.style()
    margin = style.pixelMetric(QStyle.PixelMetric.PM_LayoutLeftMargin)
    layout.setContentsMargins(margin * 2, margin * 2, margin * 2, margin)
    layout.setSpacing(margin * 2)
    row = QHBoxLayout()
    row.setSpacing(margin * 2)
    size = style.pixelMetric(QStyle.PixelMetric.PM_MessageBoxIconSize, None, host)
    source = pixmap_icon
    if source is None and icon in _ICON_PIXMAPS:
        source = style.standardIcon(_ICON_PIXMAPS[icon], None, host)
    if source is not None and not source.isNull():
        icon_label = QLabel()
        icon_label.setObjectName("laceMessageIcon")
        icon_label.setPixmap(source.pixmap(size, size))
        row.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)
    label = QLabel(text)
    label.setObjectName("laceMessageText")
    label.setTextFormat(Qt.TextFormat.AutoText)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse
                                  | Qt.TextInteractionFlag.LinksAccessibleByMouse)
    label.setOpenExternalLinks(True)
    label.setWordWrap(True)
    # A wrapping label's size hint is narrow; give it the text's own width,
    # up to a readable measure, so short messages stay on one line.
    label.setMinimumWidth(min(_text_width(label) + 2, _MESSAGE_TEXT_WIDTH))
    row.addWidget(label, 1)
    layout.addLayout(row)
    return label


def message(parent: Optional[QWidget], title: str, text: str,
            icon: Union[str, QMessageBox.Icon] = "information",
            buttons: _Buttons = StandardButton.Ok,
            default: _Buttons = StandardButton.NoButton) -> QMessageBox.StandardButton:
    """A message box; returns the clicked button.

    *icon* is ``"information"``, ``"question"``, ``"warning"``,
    ``"critical"``, ``"none"`` or a ``QMessageBox.Icon``. Escape and the
    title bar's close button answer with the escape button by
    ``QMessageBox``'s rules, or ``NoButton`` if there is none.
    """
    icon = _message_icon(icon)
    if _host_class() is None:
        box = QMessageBox(icon, title, text,
                          QMessageBox.StandardButton(_value(buttons)), parent)
        if _value(default):
            box.setDefaultButton(QMessageBox.StandardButton(_value(default)))
        box.exec()
        clicked = box.clickedButton()
        return (box.standardButton(clicked) if clicked is not None
                else StandardButton.NoButton)

    host = _host(parent, title)
    _message_body(host, text, icon)
    box = QDialogButtonBox(QDialogButtonBox.StandardButton(_value(buttons)))
    host.contentLayout().addWidget(box)
    result = [None]

    def clicked(button):
        result[0] = button
        host.accept()

    box.clicked.connect(clicked)
    default_btn = _default_button(box, _value(default))
    if default_btn is not None:
        default_btn.setDefault(True)
        default_btn.setFocus()
    escape = _escape_button(box)
    _exec(host)
    button = result[0] if result[0] is not None else escape
    if button is None:
        return StandardButton.NoButton
    return StandardButton(box.standardButton(button).value)


def information(parent, title: str, text: str,
                buttons: _Buttons = StandardButton.Ok,
                default: _Buttons = StandardButton.NoButton) -> QMessageBox.StandardButton:
    """``QMessageBox.information``, themed."""
    return message(parent, title, text, "information", buttons, default)


def question(parent, title: str, text: str,
             buttons: _Buttons = StandardButton.Yes | StandardButton.No,
             default: _Buttons = StandardButton.NoButton) -> QMessageBox.StandardButton:
    """``QMessageBox.question``, themed."""
    return message(parent, title, text, "question", buttons, default)


def warning(parent, title: str, text: str,
            buttons: _Buttons = StandardButton.Ok,
            default: _Buttons = StandardButton.NoButton) -> QMessageBox.StandardButton:
    """``QMessageBox.warning``, themed."""
    return message(parent, title, text, "warning", buttons, default)


def critical(parent, title: str, text: str,
             buttons: _Buttons = StandardButton.Ok,
             default: _Buttons = StandardButton.NoButton) -> QMessageBox.StandardButton:
    """``QMessageBox.critical``, themed."""
    return message(parent, title, text, "critical", buttons, default)


def about(parent, title: str, text: str) -> None:
    """``QMessageBox.about``, themed: the application icon beside *text*."""
    if _host_class() is None:
        QMessageBox.about(parent, title, text)
        return
    host = _host(parent, title)
    app_icon = QApplication.windowIcon() if QApplication.instance() else QIcon()
    _message_body(host, text, QMessageBox.Icon.NoIcon, app_icon)
    box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
    box.accepted.connect(host.accept)
    host.contentLayout().addWidget(box)
    box.button(QDialogButtonBox.StandardButton.Ok).setDefault(True)
    _exec(host)


# -- input dialogs ----------------------------------------------------------------

def _input(parent, title: str, label: str,
           setup: Callable[[QInputDialog], None],
           value: Callable[[QInputDialog], object],
           fallback: Callable[[], Tuple[object, bool]]) -> Tuple[object, bool]:
    if _host_class() is None:
        return fallback()
    host = _host(parent, title)
    inner = QInputDialog(host)
    inner.setLabelText(label)
    setup(inner)
    _embed(host, inner)
    ok = _exec(host) == QDialog.DialogCode.Accepted
    return value(inner), ok


def get_text(parent, title: str, label: str,
             echo: QLineEdit.EchoMode = QLineEdit.EchoMode.Normal,
             text: str = "",
             input_method_hints: Qt.InputMethodHint = Qt.InputMethodHint.ImhNone
             ) -> Tuple[str, bool]:
    """``QInputDialog.getText``, themed: ``(text, ok)``."""
    def setup(d):
        d.setInputMode(QInputDialog.InputMode.TextInput)
        d.setTextEchoMode(echo)
        d.setTextValue(text)
        d.setInputMethodHints(input_method_hints)

    def value(d):
        return d.textValue()

    return _input(parent, title, label, setup, value,
                  lambda: QInputDialog.getText(parent, title, label, echo, text,
                                               Qt.WindowType.Dialog, input_method_hints))


def get_multi_line_text(parent, title: str, label: str, text: str = ""
                        ) -> Tuple[str, bool]:
    """``QInputDialog.getMultiLineText``, themed: ``(text, ok)``."""
    def setup(d):
        d.setInputMode(QInputDialog.InputMode.TextInput)
        d.setOption(QInputDialog.InputDialogOption.UsePlainTextEditForTextInput)
        d.setTextValue(text)

    return _input(parent, title, label, setup, lambda d: d.textValue(),
                  lambda: QInputDialog.getMultiLineText(parent, title, label, text))


def get_item(parent, title: str, label: str, items: Sequence[str],
             current: int = 0, editable: bool = True) -> Tuple[str, bool]:
    """``QInputDialog.getItem``, themed: ``(item, ok)``.

    On cancel the item is the one that was current, as in Qt.
    """
    items = list(items)
    start = items[current] if 0 <= current < len(items) else ""

    def setup(d):
        d.setComboBoxItems(items)
        d.setComboBoxEditable(editable)
        d.setTextValue(start)

    def value(d):
        return d.textValue() if d.result() == QDialog.DialogCode.Accepted else start

    return _input(parent, title, label, setup, value,
                  lambda: QInputDialog.getItem(parent, title, label, items,
                                               current, editable))


def get_int(parent, title: str, label: str, value: int = 0,
            min_value: int = -2147483647, max_value: int = 2147483647,
            step: int = 1) -> Tuple[int, bool]:
    """``QInputDialog.getInt``, themed: ``(value, ok)``."""
    def setup(d):
        d.setInputMode(QInputDialog.InputMode.IntInput)
        d.setIntRange(min_value, max_value)
        d.setIntStep(step)
        d.setIntValue(value)

    return _input(parent, title, label, setup, lambda d: d.intValue(),
                  lambda: QInputDialog.getInt(parent, title, label, value,
                                              min_value, max_value, step))


def get_double(parent, title: str, label: str, value: float = 0.0,
               min_value: float = -2147483647.0, max_value: float = 2147483647.0,
               decimals: int = 1, step: float = 1.0) -> Tuple[float, bool]:
    """``QInputDialog.getDouble``, themed: ``(value, ok)``."""
    def setup(d):
        d.setInputMode(QInputDialog.InputMode.DoubleInput)
        d.setDoubleDecimals(decimals)
        d.setDoubleRange(min_value, max_value)
        d.setDoubleStep(step)
        d.setDoubleValue(value)

    return _input(parent, title, label, setup, lambda d: d.doubleValue(),
                  lambda: QInputDialog.getDouble(parent, title, label, value,
                                                 min_value, max_value, decimals,
                                                 Qt.WindowType.Dialog, step))


# -- colour -------------------------------------------------------------------------

def get_color(initial: QColor = QColor(Qt.GlobalColor.white),
              parent: Optional[QWidget] = None, title: str = "",
              options: QColorDialog.ColorDialogOption = QColorDialog.ColorDialogOption(0)
              ) -> QColor:
    """``QColorDialog.getColor``, themed (same argument order as Qt).

    Returns an invalid ``QColor`` on cancel.
    """
    if _host_class() is None:
        return QColorDialog.getColor(initial, parent, title, options)
    host = _host(parent, title or "Select Color")
    inner = QColorDialog(QColor(initial), host)
    inner.setOptions(options & ~QColorDialog.ColorDialogOption.NoButtons)
    _embed(host, inner)
    if _exec(host) != QDialog.DialogCode.Accepted:
        return QColor()
    return inner.selectedColor()


# -- files --------------------------------------------------------------------------

def _file_dialog(parent, caption: str, directory: str, filter: str,
                 selected_filter: str, options,
                 file_mode: QFileDialog.FileMode,
                 accept_mode: QFileDialog.AcceptMode = QFileDialog.AcceptMode.AcceptOpen
                 ) -> Optional[QFileDialog]:
    """Run Qt's file dialog in a themed frame; the dialog if accepted, else None."""
    host = _host(parent, caption, resizable=True)
    inner = QFileDialog(host, caption, directory, filter)
    inner.setOptions(options | QFileDialog.Option.DontUseNativeDialog)
    if selected_filter:
        inner.selectNameFilter(selected_filter)
    inner.setAcceptMode(accept_mode)
    inner.setFileMode(file_mode)
    _embed(host, inner)
    return inner if _exec(host) == QDialog.DialogCode.Accepted else None


def _one_file(parent, caption: str, directory: str, filter: str,
              selected_filter: str, options, file_mode: QFileDialog.FileMode,
              accept_mode: QFileDialog.AcceptMode) -> Tuple[str, str]:
    """``(path, filter)`` of a single-file dialog, ``("", "")`` on cancel."""
    inner = _file_dialog(parent, caption, directory, filter, selected_filter,
                         options, file_mode, accept_mode)
    if inner is None or not inner.selectedFiles():
        return "", ""
    return inner.selectedFiles()[0], inner.selectedNameFilter()


def _use_qt_files(native: bool) -> bool:
    return native or _host_class() is None


def get_open_file_name(parent=None, caption: str = "", dir: str = "",
                       filter: str = "", selected_filter: str = "",
                       options: QFileDialog.Option = QFileDialog.Option(0),
                       native: bool = True) -> Tuple[str, str]:
    """``QFileDialog.getOpenFileName``: ``(path, filter)``, ``("", "")`` on cancel.

    ``native=True`` (default) opens the OS dialog through Qt;
    ``native=False`` embeds Qt's own file dialog in a themed frame.
    """
    if _use_qt_files(native):
        return QFileDialog.getOpenFileName(parent, caption, dir, filter,
                                           selected_filter, options)
    return _one_file(parent, caption, dir, filter, selected_filter, options,
                     QFileDialog.FileMode.ExistingFile,
                     QFileDialog.AcceptMode.AcceptOpen)


def get_open_file_names(parent=None, caption: str = "", dir: str = "",
                        filter: str = "", selected_filter: str = "",
                        options: QFileDialog.Option = QFileDialog.Option(0),
                        native: bool = True) -> Tuple[List[str], str]:
    """``QFileDialog.getOpenFileNames``: ``(paths, filter)``, ``([], "")`` on cancel."""
    if _use_qt_files(native):
        return QFileDialog.getOpenFileNames(parent, caption, dir, filter,
                                            selected_filter, options)
    inner = _file_dialog(parent, caption, dir, filter, selected_filter, options,
                         QFileDialog.FileMode.ExistingFiles)
    if inner is None:
        return [], ""
    return list(inner.selectedFiles()), inner.selectedNameFilter()


def get_save_file_name(parent=None, caption: str = "", dir: str = "",
                       filter: str = "", selected_filter: str = "",
                       options: QFileDialog.Option = QFileDialog.Option(0),
                       native: bool = True) -> Tuple[str, str]:
    """``QFileDialog.getSaveFileName``: ``(path, filter)``, ``("", "")`` on cancel."""
    if _use_qt_files(native):
        return QFileDialog.getSaveFileName(parent, caption, dir, filter,
                                           selected_filter, options)
    return _one_file(parent, caption, dir, filter, selected_filter, options,
                     QFileDialog.FileMode.AnyFile,
                     QFileDialog.AcceptMode.AcceptSave)


def get_existing_directory(parent=None, caption: str = "", dir: str = "",
                           options: QFileDialog.Option = QFileDialog.Option.ShowDirsOnly,
                           native: bool = True) -> str:
    """``QFileDialog.getExistingDirectory``: the path, ``""`` on cancel."""
    if _use_qt_files(native):
        return QFileDialog.getExistingDirectory(parent, caption, dir, options)
    inner = _file_dialog(parent, caption, dir, "", "", options,
                         QFileDialog.FileMode.Directory)
    if inner is None or not inner.selectedFiles():
        return ""
    return inner.selectedFiles()[0]


__all__ = [
    "MESSAGE_ICONS",
    "StandardButton",
    "about",
    "critical",
    "default_frameless",
    "get_color",
    "get_double",
    "get_existing_directory",
    "get_int",
    "get_item",
    "get_multi_line_text",
    "get_open_file_name",
    "get_open_file_names",
    "get_save_file_name",
    "get_text",
    "information",
    "message",
    "question",
    "set_default_frameless",
    "warning",
]
