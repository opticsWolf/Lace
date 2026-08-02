# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.

"""Frameless window wrappers around PySideSix-Frameless-Window.

Provides ``FramelessLaceMainWindow`` and ``FramelessLaceWindow`` subclasses
that inherit directly from the platform-specific frameless classes provided
by ``qframelesswindow``.

On Windows this resolves to ``WindowsFramelessMainWindow`` /
``WindowsFramelessWindow``, on macOS to ``MacFramelessMainWindow`` /
``MacFramelessWindow``, and on Linux to ``LinuxFramelessMainWindow`` /
``LinuxFramelessWindow``.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QBoxLayout, QMenuBar, QVBoxLayout, QWidget
from qframelesswindow import FramelessMainWindow, FramelessWindow


# ── Frameless MainWindow ───────────────────────────────────────────────

class FramelessLaceMainWindow(FramelessMainWindow):
    """A frameless main window that uses PySideSix-Frameless-Window for
    custom title bars and non-client area handling.

    Inherits from the platform-specific ``FramelessMainWindow`` which
    already provides:
    - ``Qt.FramelessWindowHint`` window flag
    - Custom ``titleBar`` widget with min/max/close buttons
    - ``nativeEvent`` handler for resize borders (WM_NCHITTEST)
    - DWM shadow and window animation effects (Windows)

    Uses a stacked container (title bar + optional menu bar) as the
    QMainWindow menu widget so the central widget is positioned below
    both.  Overrides ``menuBar()`` to create a separate ``QMenuBar``
    below the title bar instead of embedding it into the title bar
    layout.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._menu_bar: Optional[QMenuBar] = None
        self._menu_bar_container: Optional[QWidget] = None
        # Integrate title bar into QMainWindow layout so the central
        # widget is positioned below it.
        self.setMenuWidget(self.titleBar)

    # -- title bar --------------------------------------------------------

    def setTitleBar(self, titleBar: QWidget) -> None:
        """Replace the title bar and update the QMainWindow menu widget.

        If a menu bar has already been created, rebuild the stacked
        container so the new title bar sits above the existing menu bar.
        """
        # Preserve existing menu bar before super() potentially resets
        # references.
        saved_menu_bar = self._menu_bar
        super().setTitleBar(titleBar)

        if saved_menu_bar is not None:
            # Rebuild stacked container with the new title bar.
            self._build_stacked_container(saved_menu_bar)
        else:
            self.setMenuWidget(self.titleBar)

    # -- menu bar ---------------------------------------------------------

    def _build_stacked_container(self, menu_bar: QMenuBar) -> None:
        """Create (or recreate) a stacked widget with title bar + menu bar
        and set it as the QMainWindow menu widget."""
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.titleBar)
        layout.addWidget(menu_bar)

        self.setMenuWidget(container)
        self._menu_bar_container = container

    def menuBar(self) -> QMenuBar:
        """Return a separate menu bar positioned below the title bar.

        QMainWindow.menuBar() auto-creates a default QMenuBar and sets
        it as the menu widget, which would replace our custom title bar.
        Instead, we create a stacked container (title bar + menu bar)
        and set it as the menu widget so both remain visible.
        """
        if self._menu_bar is not None:
            return self._menu_bar

        menu_bar = QMenuBar(self)
        self._menu_bar = menu_bar
        self._build_stacked_container(menu_bar)
        return menu_bar

    def setCentralWidget(self, widget: QWidget) -> None:
        """Override to keep the title bar above the central widget."""
        super().setCentralWidget(widget)
        self.titleBar.raise_()


# ── Frameless Floating Window ──────────────────────────────────────────

class FramelessLaceWindow(FramelessWindow):
    """A frameless floating window that uses PySideSix-Frameless-Window
    for custom title bars on floating dock containers.

    Inherits from the platform-specific ``FramelessWindow`` which
    provides the same frameless infrastructure as
    ``FramelessLaceMainWindow`` but for plain ``QWidget`` windows.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)


__all__ = [
    "FramelessLaceMainWindow",
    "FramelessLaceWindow",
]
