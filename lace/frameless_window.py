# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.

"""Frameless window wrappers around PySideSix-Frameless-Window.

Provides ``FramelessLaceMainWindow`` and ``FramelessLaceWindow`` that use
the platform-specific frameless infrastructure from ``qframelesswindow``
(custom title bar with min/max/close, resize borders, DWM shadow, window
animation) whenever :class:`.enums.TitleBarMode.custom` is selected.

``TitleBarMode.native`` is the default and makes both classes behave like
a plain ``QMainWindow`` / ``QWidget`` with the OS-provided title bar; only
``TitleBarMode.custom`` enables the frameless chrome::

    win = FramelessLaceMainWindow(title_bar_mode=TitleBarMode.custom)

Floating dock containers inherit the mode from their ``DockManager``, so
with a custom-mode main window the floating dock containers become
frameless windows with the ``qframelesswindow`` title bar as well.
"""

from __future__ import annotations

import sys
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QMenuBar, QVBoxLayout, QWidget

from .enums import TitleBarMode

if sys.platform == "win32":
    from qframelesswindow.windows import WindowsFramelessWindowBase as _FramelessBase
elif sys.platform == "darwin":
    from qframelesswindow.mac import MacFramelessWindowBase as _FramelessBase
else:
    from qframelesswindow.linux import LinuxFramelessWindowBase as _FramelessBase


class _FramelessModeMixin:
    """Gate the platform frameless mixin behind ``TitleBarMode``.

    Sits before the platform frameless mixin in the MRO.  Every operation
    that only makes sense for a frameless window (custom title bar, resize
    borders, DWM effects, window flags) is routed through the current mode:
    in native mode these become no-ops so the window behaves exactly like
    a plain Qt widget.
    """

    def _is_frameless_custom(self) -> bool:
        return getattr(
            self, "_title_bar_mode", TitleBarMode.native
        ) is TitleBarMode.custom

    def _init_frameless_chrome(self) -> None:
        """Run the platform frameless setup and install a standard title bar.

        Only called for ``TitleBarMode.custom`` windows.
        """
        self._isSystemButtonVisible = False
        self._initFrameless()

        # StandardTitleBar shows the window icon + title (kept in sync via
        # windowTitleChanged) next to the min/max/close buttons.
        from qframelesswindow.titlebar import StandardTitleBar

        self.setTitleBar(StandardTitleBar(self))

    # -- platform mixin operations, gated on mode ------------------------

    def setTitleBar(self, titleBar: QWidget) -> None:
        if self._is_frameless_custom():
            super().setTitleBar(titleBar)

    def setStayOnTop(self, isTop: bool) -> None:
        if self._is_frameless_custom():
            super().setStayOnTop(isTop)

    def toggleStayOnTop(self) -> None:
        if self._is_frameless_custom():
            super().toggleStayOnTop()

    def updateFrameless(self) -> None:
        if self._is_frameless_custom():
            super().updateFrameless()

    def resizeEvent(self, e) -> None:
        if isinstance(self, QMainWindow):
            QMainWindow.resizeEvent(self, e)
        else:
            QWidget.resizeEvent(self, e)
        if self._is_frameless_custom():
            # Platform mixin: keep the custom title bar full-width.
            _FramelessBase.resizeEvent(self, e)

    def nativeEvent(self, eventType, message):
        if self._is_frameless_custom():
            return super().nativeEvent(eventType, message)
        return False, 0


# ── Frameless MainWindow ───────────────────────────────────────────────

class FramelessLaceMainWindow(_FramelessModeMixin, _FramelessBase, QMainWindow):
    """A main window that uses PySideSix-Frameless-Window for custom
    title bars and non-client area handling when ``TitleBarMode.custom``
    is selected.

    Custom mode inherits from the platform-specific ``FramelessWindowBase``
    which provides:
    - ``Qt.FramelessWindowHint`` window flag
    - Custom ``titleBar`` widget with min/max/close buttons
    - ``nativeEvent`` handler for resize borders (WM_NCHITTEST)
    - DWM shadow and window animation effects (Windows)

    The title bar is used as the QMainWindow menu widget so the central
    widget is positioned below it; a menu bar, when requested, is stacked
    below the title bar in a container widget.  A
    :class:`.frameless_titlebar.FramelessTitleBarStyler` handles automatic
    theme colour updates.

    Native mode (the default) behaves like a plain ``QMainWindow``.
    """

    def __init__(self, parent: Optional[QWidget] = None,
                 title_bar_mode: TitleBarMode = TitleBarMode.native):
        QMainWindow.__init__(self, parent)
        self._title_bar_mode = title_bar_mode
        self._menu_bar: Optional[QMenuBar] = None
        self._menu_bar_container: Optional[QWidget] = None
        self._titlebar_styler: Optional["FramelessTitleBarStyler"] = None

        if title_bar_mode is TitleBarMode.custom:
            self._init_frameless_chrome()
            # Integrate title bar into the QMainWindow layout so the
            # central widget is positioned below it.
            self.setMenuWidget(self.titleBar)

    # -- title bar --------------------------------------------------------

    def setTitleBar(self, titleBar: QWidget) -> None:
        """Replace the title bar and update the QMainWindow menu widget.

        If a menu bar has already been created, rebuild the stacked
        container so the new title bar sits above the existing menu bar.
        No-op in native mode.
        """
        if self._title_bar_mode is not TitleBarMode.custom:
            return

        # Preserve existing menu bar before super() potentially resets
        # references.
        saved_menu_bar = self._menu_bar
        super().setTitleBar(titleBar)

        if saved_menu_bar is not None:
            # Rebuild stacked container with the new title bar.
            self._build_stacked_container(saved_menu_bar)
        else:
            self.setMenuWidget(self.titleBar)

        # Notify the styler about the new title bar.
        if self._titlebar_styler is not None:
            self._titlebar_styler.title_bar = self.titleBar

    # -- menu bar ---------------------------------------------------------

    def menuBar(self) -> QMenuBar:
        """Return a separate menu bar positioned below the title bar.

        QMainWindow.menuBar() auto-creates a default QMenuBar and sets
        it as the menu widget, which would replace our custom title bar.
        Instead, we create a stacked container (title bar + menu bar)
        and set it as the menu widget so both remain visible.

        In native mode this is the standard QMainWindow behaviour.
        """
        if self._title_bar_mode is not TitleBarMode.custom:
            return super().menuBar()

        if self._menu_bar is not None:
            return self._menu_bar

        menu_bar = QMenuBar(self)
        self._menu_bar = menu_bar
        self._build_stacked_container(menu_bar)

        # Notify the styler about the new menu bar.
        if self._titlebar_styler is not None:
            self._titlebar_styler.menu_bar = menu_bar

        return menu_bar

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

    def setCentralWidget(self, widget: QWidget) -> None:
        """Override to keep the title bar above the central widget."""
        super().setCentralWidget(widget)
        if self._title_bar_mode is TitleBarMode.custom:
            self.titleBar.raise_()

    # -- theme integration ------------------------------------------------

    def _register_titlebar_theme(self) -> None:
        """Create a :class:`.frameless_titlebar.FramelessTitleBarStyler` that
        subscribes to ``DockStyleManager`` and applies theme colours to the
        title bar and menu bar.

        Call this once from DockManager or the application's setup code.
        No-op in native mode.
        """
        if self._title_bar_mode is not TitleBarMode.custom:
            return

        try:
            from .frameless_titlebar import FramelessTitleBarStyler
        except ImportError:
            return

        self._titlebar_styler = FramelessTitleBarStyler(
            title_bar=self.titleBar,
            menu_bar=self._menu_bar,
            parent=self,
        )


# ── Frameless Floating Window ──────────────────────────────────────────

class FramelessLaceWindow(_FramelessModeMixin, _FramelessBase, QWidget):
    """A frameless top-level window (used for floating dock containers).

    With ``TitleBarMode.custom`` the platform-specific frameless
    infrastructure from ``qframelesswindow`` is active: custom title bar,
    resize borders and DWM shadow.  With the default ``TitleBarMode.native``
    this is a plain ``QWidget``.
    """

    def __init__(self, parent: Optional[QWidget] = None,
                 title_bar_mode: TitleBarMode = TitleBarMode.native):
        QWidget.__init__(self, parent)
        self._title_bar_mode = title_bar_mode

        if title_bar_mode is TitleBarMode.custom:
            # Ensure a real top-level window exists before the platform
            # setup touches windowHandle()/winId().
            self.setWindowFlags(self.windowFlags() | Qt.Window)
            self._init_frameless_chrome()


__all__ = [
    "FramelessLaceMainWindow",
    "FramelessLaceWindow",
]
