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

from PySide6.QtWidgets import QWidget
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
    - ``resizeEvent`` that resizes the title bar

    The only addition here is an override of ``setCentralWidget`` to
    keep the title bar above the central widget (QMainWindow can
    reorder child z-order).
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

    def setCentralWidget(self, widget: QWidget) -> None:
        """Override to keep the title bar above the central widget.

        ``QMainWindow.setCentralWidget()`` can reorder child z-order,
        pushing the central widget above the title bar.  Calling
        ``titleBar.raise_()`` after setting the widget fixes this.
        """
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
