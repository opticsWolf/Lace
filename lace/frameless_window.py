# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.

"""Frameless window wrappers around PySideSix-Frameless-Window.

Provides ``FramelessMainWindow`` and ``FramelessWindow`` subclasses that
integrate the ``qframelesswindow`` library into the Lace docking system.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QWidget

from .enums import TitleBarMode

if TYPE_CHECKING:
    from qframelesswindow import (
        FramelessMainWindow,
        FramelessWindow,
        TitleBar,
        StandardTitleBar,
    )


# ── Platform-agnostic imports ──────────────────────────────────────────

def _get_frameless_classes():
    """Import platform-specific frameless window classes from qframelesswindow."""
    from qframelesswindow import FramelessMainWindow, FramelessWindow
    return FramelessMainWindow, FramelessWindow


# ── Frameless MainWindow ───────────────────────────────────────────────

class FramelessLaceMainWindow(QMainWindow):
    """A QMainWindow that uses the PySideSix-Frameless-Window library for
    custom title bars and non-client area handling.

    This class wraps ``qframelesswindow.FramelessMainWindow`` (platform-
    specific) and exposes the ``titleBar`` attribute for Lace to customise.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._titleBar: Optional[object] = None
        self._windowEffect: Optional[object] = None
        self._isResizeEnabled: bool = True
        self._init_frameless()

    def _init_frameless(self) -> None:
        """Initialise the frameless window and its title bar."""
        FramelessMainWindow, _ = _get_frameless_classes()

        # Apply FramelessWindowHint
        stay_on_top = (
            Qt.WindowStaysOnTopHint
            if self.windowFlags() & Qt.WindowStaysOnTopHint
            else 0
        )
        self.setWindowFlags(
            self.windowFlags() | Qt.FramelessWindowHint | stay_on_top
        )

        # Import platform-specific classes for effects
        if sys.platform == "win32":
            from qframelesswindow.windows import WindowsWindowEffect
            from qframelesswindow.titlebar import TitleBar

            self._windowEffect = WindowsWindowEffect(self)
            self._titleBar = TitleBar(self)
            self._windowEffect.addWindowAnimation(self.winId())
            self._windowEffect.addShadowEffect(self.winId())
        else:
            from qframelesswindow.titlebar import TitleBar
            self._titleBar = TitleBar(self)

        self._titleBar.raise_()

    @property
    def titleBar(self) -> Optional[object]:
        """Return the custom title bar widget, or ``None``."""
        return self._titleBar

    @property
    def windowEffect(self) -> Optional[object]:
        """Return the platform-specific window effect helper, or ``None``."""
        return self._windowEffect

    def setResizeEnabled(self, enabled: bool) -> None:
        """Enable or disable window resizing."""
        self._isResizeEnabled = enabled

    def setStandardTitleBar(self) -> None:
        """Replace the current title bar with a ``StandardTitleBar``
        (includes window icon and title label)."""
        from qframelesswindow.titlebar import StandardTitleBar

        self._titleBar.deleteLater()
        self._titleBar.hide()
        self._titleBar = StandardTitleBar(self)
        self._titleBar.setParent(self)
        self._titleBar.raise_()

    def resizeEvent(self, event) -> None:
        """Resize the title bar when the window is resized."""
        super().resizeEvent(event)
        if self._titleBar is not None:
            self._titleBar.resize(self.width(), self._titleBar.height())

    def setCentralWidget(self, widget: QWidget) -> None:
        """Override to keep the title bar above the central widget.

        ``QMainWindow.setCentralWidget()`` can reorder child z-order,
        pushing the central widget above the title bar.  Calling
        ``titleBar.raise_()`` after setting the widget fixes this.
        """
        super().setCentralWidget(widget)
        if self._titleBar is not None:
            self._titleBar.raise_()


# ── Frameless Floating Window ──────────────────────────────────────────

class FramelessLaceWindow(QWidget):
    """A QWidget that uses the PySideSix-Frameless-Window library for
    custom title bars on floating dock containers.

    Wraps ``qframelesswindow.FramelessWindow`` (platform-specific).
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._titleBar: Optional[object] = None
        self._windowEffect: Optional[object] = None
        self._isResizeEnabled: bool = True
        self._init_frameless()

    def _init_frameless(self) -> None:
        """Initialise the frameless window and its title bar."""
        if sys.platform == "win32":
            from qframelesswindow.windows import WindowsWindowEffect
            from qframelesswindow.titlebar import TitleBar

            stay_on_top = (
                Qt.WindowStaysOnTopHint
                if self.windowFlags() & Qt.WindowStaysOnTopHint
                else 0
            )
            self.setWindowFlags(
                self.windowFlags() | Qt.FramelessWindowHint | stay_on_top
            )

            self._windowEffect = WindowsWindowEffect(self)
            self._titleBar = TitleBar(self)
            self._windowEffect.addWindowAnimation(self.winId())
            self._windowEffect.addShadowEffect(self.winId())
        else:
            from qframelesswindow.titlebar import TitleBar
            stay_on_top = (
                Qt.WindowStaysOnTopHint
                if self.windowFlags() & Qt.WindowStaysOnTopHint
                else 0
            )
            self.setWindowFlags(
                self.windowFlags() | Qt.FramelessWindowHint | stay_on_top
            )
            self._titleBar = TitleBar(self)

        self._titleBar.raise_()

    @property
    def titleBar(self) -> Optional[object]:
        """Return the custom title bar widget, or ``None``."""
        return self._titleBar

    @property
    def windowEffect(self) -> Optional[object]:
        """Return the platform-specific window effect helper, or ``None``."""
        return self._windowEffect

    def setResizeEnabled(self, enabled: bool) -> None:
        """Enable or disable window resizing."""
        self._isResizeEnabled = enabled

    def resizeEvent(self, event) -> None:
        """Resize the title bar when the window is resized."""
        super().resizeEvent(event)
        if self._titleBar is not None:
            self._titleBar.resize(self.width(), self._titleBar.height())


__all__ = [
    "FramelessLaceMainWindow",
    "FramelessLaceWindow",
]
