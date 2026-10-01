# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.

"""A frameless ``QDialog`` with the main window's themed title bar.

:class:`FramelessLaceDialog` is Layer B of ``docs/DIALOG_TITLEBAR_PLAN.md``:
the same :class:`.frameless_window.LaceStandardTitleBar` and
:class:`.frameless_titlebar.FramelessTitleBarStyler` as
``FramelessLaceMainWindow``, so a dialog's bar is pixel-identical to the
main window's and follows a theme switch live. Native-framed dialogs are
covered by :mod:`lace.native_frame` instead (Layer A).
"""

from __future__ import annotations

import logging
import sys
from typing import Optional

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QLayout, QVBoxLayout, QWidget
from qframelesswindow import FramelessDialog

from lace.frameless_titlebar import FramelessTitleBarStyler
from lace.frameless_window import TitleBarDescriptor, _FramelessChromeHealMixin


logger = logging.getLogger(__name__)

#: Title-bar button sets: ``"close"`` (the default for dialogs),
#: ``"min_close"`` or ``"all"`` (minimize, maximize and close).
DIALOG_BUTTONS = ("close", "min_close", "all")


def _native_hwnds() -> bool:
    """Whether ``winId()`` is a real Win32 handle (not under ``offscreen``)."""
    return (sys.platform == "win32"
            and QGuiApplication.platformName() == "windows")


class FramelessLaceDialog(_FramelessChromeHealMixin, FramelessDialog):
    """A frameless, fully themed dialog.

    It is a real :class:`QDialog`: ``exec()``, ``open()``, ``accept()``,
    ``reject()``, ``done()``, Escape to reject and default buttons all
    behave as usual. At first show Qt sizes it to its content and centres it
    on the parent's window, clamped to that screen.

    Put the dialog's content in :meth:`contentLayout` (or replace the whole
    content with :meth:`setContentWidget`). Don't call ``setLayout()`` on
    the dialog: its own layout holds the title bar above the content.

    Parameters
    ----------
    parent:
        Optional parent widget; the dialog centres on its window.
    title_bar:
        Optional title-bar descriptor, as for ``FramelessLaceMainWindow``.
        ``None`` uses :class:`.frameless_window.LaceStandardTitleBar`.
    resizable:
        ``False`` fixes the size to the content and turns off the resize
        border.
    buttons:
        Which title-bar buttons show: ``"close"`` (default),
        ``"min_close"`` or ``"all"``. Double-click-to-maximize, and on
        Windows Aero Snap's maximize, are on only with ``"all"``.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title_bar: TitleBarDescriptor = None,
        resizable: bool = True,
        buttons: str = "close",
    ):
        if buttons not in DIALOG_BUTTONS:
            raise ValueError(
                f"buttons must be one of {DIALOG_BUTTONS}, got {buttons!r}")
        super().__init__(parent)
        self._buttons = buttons
        self._resizable = True
        self._titlebar_styler: Optional[FramelessTitleBarStyler] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._content = QWidget(self)
        self._content.setObjectName("laceDialogContent")
        layout.addWidget(self._content, 1)

        # setTitleBar (below) puts the bar in row 0 of the layout.
        self._init_lace_chrome(title_bar)
        if self.titleBar.parent() is self and layout.indexOf(self.titleBar) < 0:
            self._insert_title_bar()
            self._sync_title_bar()

        self._titlebar_styler = FramelessTitleBarStyler(
            title_bar=self.titleBar, parent=self)
        self.setResizable(resizable)
        self._apply_window_boxes()
        # The frameless base resized the window to 500x500, which marks it
        # as explicitly sized; clear that so QDialog sizes to its content at
        # first show, like a native dialog.
        self.setAttribute(Qt.WidgetAttribute.WA_Resized, False)

    # -- content ------------------------------------------------------------

    def contentWidget(self) -> QWidget:
        """The widget below the title bar."""
        return self._content

    def setContentWidget(self, widget: QWidget) -> None:
        """Replace the content below the title bar with *widget*.

        The previous content widget is deleted.
        """
        layout = self.layout()
        old = self._content
        if widget is old:
            return
        widget.setParent(self)
        layout.replaceWidget(old, widget)
        layout.setStretchFactor(widget, 1)
        self._content = widget
        old.hide()
        old.deleteLater()

    def contentLayout(self) -> QLayout:
        """The content widget's layout, created as a ``QVBoxLayout`` if absent."""
        layout = self._content.layout()
        if layout is None:
            layout = QVBoxLayout(self._content)
        return layout

    # -- title bar ----------------------------------------------------------

    def buttons(self) -> str:
        """The title-bar button set: ``"close"``, ``"min_close"`` or ``"all"``."""
        return self._buttons

    def setTitleBar(self, titleBar: QWidget) -> None:
        """Replace the title bar, keeping it in row 0 above the content."""
        layout = self.layout()
        old = getattr(self, "titleBar", None)
        if layout is not None and old is not None:
            layout.removeWidget(old)
        super().setTitleBar(titleBar)
        if layout is not None:
            self._insert_title_bar()
        self._sync_title_bar()
        if self._titlebar_styler is not None:
            self._titlebar_styler.title_bar = self.titleBar

    def _insert_title_bar(self) -> None:
        self.layout().insertWidget(0, self.titleBar, 0)

    def _sync_title_bar(self) -> None:
        """Push buttons, title and icon into the current bar.

        ``StandardTitleBar`` only follows *changes* of the window title and
        icon, so a bar installed after they were set needs them pushed.
        """
        bar = self.titleBar
        show_min = self._buttons in ("min_close", "all")
        show_max = self._buttons == "all"
        for name, visible in (("minBtn", show_min), ("maxBtn", show_max)):
            button = getattr(bar, name, None)
            if button is not None:
                button.setVisible(visible)
        enable_dbl = getattr(bar, "setDoubleClickEnabled", None)
        if enable_dbl is not None:
            enable_dbl(show_max)
        set_title = getattr(bar, "setTitle", None)
        if set_title is not None:
            set_title(self.windowTitle())
        set_icon = getattr(bar, "setIcon", None)
        if set_icon is not None and not self.windowIcon().isNull():
            set_icon(self.windowIcon())

    def titlebar_styler(self) -> Optional[FramelessTitleBarStyler]:
        """The styler that keeps the title bar on the current theme."""
        return self._titlebar_styler

    # -- size -----------------------------------------------------------------

    def isResizable(self) -> bool:
        """Whether the user can resize the dialog."""
        return self._resizable

    def setResizable(self, resizable: bool) -> None:
        """Turn the resize border on or off.

        A fixed dialog takes its content's size hint and follows it when
        the content changes.
        """
        self._resizable = bool(resizable)
        set_enabled = getattr(self, "setResizeEnabled", None)
        if set_enabled is not None:
            set_enabled(self._resizable)
        self.layout().setSizeConstraint(
            QLayout.SizeConstraint.SetDefaultConstraint if self._resizable
            else QLayout.SizeConstraint.SetFixedSize)

    # -- native chrome --------------------------------------------------------

    def updateFrameless(self) -> None:
        """Re-apply the frameless chrome, then this dialog's caption boxes.

        The base turns minimize and maximize boxes back on, which would let
        Aero Snap and Win+Up maximize a dialog showing only a close button.
        """
        base = getattr(super(), "updateFrameless", None)
        if base is not None:
            base()
        if getattr(self, "_buttons", None) is not None:
            self._apply_window_boxes()

    def _apply_window_boxes(self) -> None:
        """Match the Win32 minimize/maximize boxes to :meth:`buttons`."""
        if not _native_hwnds():
            return
        try:
            import win32con
            import win32gui
            hwnd = int(self.winId())
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            new = style
            for box, wanted in (
                    (win32con.WS_MINIMIZEBOX, self._buttons in ("min_close", "all")),
                    (win32con.WS_MAXIMIZEBOX, self._buttons == "all")):
                new = new | box if wanted else new & ~box
            if new != style:
                win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, new)
        except Exception:
            logger.debug("dialog caption boxes not applied", exc_info=True)

    def event(self, e: QEvent) -> bool:
        # Same auto-heal as the main window: a recreated native handle
        # loses the DWM bits (and this dialog's caption boxes).
        if e.type() == QEvent.Type.WinIdChange:
            self._schedule_frameless_heal()
        return super().event(e)


__all__ = ["DIALOG_BUTTONS", "FramelessLaceDialog"]
