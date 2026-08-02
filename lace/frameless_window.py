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

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenuBar, QWidget
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

    Uses ``setMenuWidget(titleBar)`` to integrate the title bar into
    QMainWindow's layout so the central widget is positioned below it.

    Overrides ``menuBar()`` to embed a ``QMenuBar`` into the title bar
    layout (matching the qframelesswindow ``main_window.py`` example),
    so existing code that calls ``self.menuBar()`` works correctly
    without replacing the title bar with a default menu bar.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._embedded_menu_bar: Optional[QMenuBar] = None
        # Integrate title bar into QMainWindow layout so the central
        # widget is positioned below it.
        self.setMenuWidget(self.titleBar)

    def setTitleBar(self, titleBar) -> None:
        """Replace the title bar and update the QMainWindow menu widget."""
        # Re-embed menu bar into the new title bar
        old_menu_bar = self._embedded_menu_bar
        super().setTitleBar(titleBar)
        self.setMenuWidget(self.titleBar)
        self._embedded_menu_bar = None
        if old_menu_bar is not None:
            # Re-create menu bar in new title bar
            new_menu_bar = self._ensure_menu_bar()
            # Transfer actions from old menu bar
            for action in old_menu_bar.actions():
                new_menu_bar.addAction(action)
            old_menu_bar.deleteLater()

    def _ensure_menu_bar(self) -> QMenuBar:
        """Create or return the embedded menu bar."""
        if hasattr(self, '_embedded_menu_bar') and self._embedded_menu_bar is not None:
            return self._embedded_menu_bar

        # Create a new menu bar parented to the title bar
        menu_bar = QMenuBar(self.titleBar)
        self._embedded_menu_bar = menu_bar
        # Insert at the left of the title bar layout (before the stretch)
        self.titleBar.layout().insertWidget(0, menu_bar, 0, Qt.AlignLeft)
        # Add stretch after menu bar to push buttons to the right
        self.titleBar.layout().insertStretch(1, 1)
        return menu_bar

    def menuBar(self) -> QMenuBar:
        """Return a menu bar embedded in the title bar layout.

        QMainWindow.menuBar() auto-creates a default QMenuBar and sets
        it as the menu widget, which would replace our custom title bar.
        Instead, we create a QMenuBar and embed it into the title bar's
        layout (matching the qframelesswindow main_window.py example).
        """
        return self._ensure_menu_bar()

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
