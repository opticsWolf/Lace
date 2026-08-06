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

import sys
from typing import Optional, Union

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QMenu, QMenuBar, QVBoxLayout, QWidget
from qframelesswindow import FramelessMainWindow, FramelessWindow
from qframelesswindow.titlebar import StandardTitleBar


_DARK_MODE_OPTED_IN = False


def _enable_system_dark_mode_menus() -> None:
    """Opt the process into Windows dark mode so native menus follow the
    system theme.

    Without this, Win32 popup menus opened via ``TrackPopupMenu`` always
    render with the classic light theme, even when the system Apps theme
    is dark (the ``AppsUseLightTheme`` setting).  Calling
    ``SetPreferredAppMode(AllowDark)`` tells Windows the process accepts
    dark mode, so its native menus follow the OS light/dark mode — dark
    when the system is dark, light when it is light.

    The call is process-wide and idempotent; it only needs to happen once
    per process.  ``SetPreferredAppMode`` is an undocumented export of
    ``uxtheme.dll`` (ordinal 135), so it is resolved by ordinal inside a
    try/except and silently skipped on platforms/versions where it is
    unavailable.
    """
    global _DARK_MODE_OPTED_IN
    if _DARK_MODE_OPTED_IN or sys.platform != "win32":
        return
    _DARK_MODE_OPTED_IN = True
    try:
        import ctypes

        # PreferredAppMode.AllowDark = 1: menus/chrome may follow the
        # system light/dark theme instead of forcing light.
        uxtheme = ctypes.WinDLL("uxtheme")
        set_preferred_app_mode = uxtheme[135]
        set_preferred_app_mode.argtypes = [ctypes.c_int]
        set_preferred_app_mode.restype = ctypes.c_int
        set_preferred_app_mode(1)
    except Exception:
        pass


# Type alias for the flexible title-bar descriptor accepted by Lace frameless
# windows: ``None`` selects :class:`LaceStandardTitleBar`, a :class:`QWidget`
# instance is used as-is, a class is instantiated as ``class(parent)``, and a
# callable is invoked as ``callable(parent)``.
TitleBarDescriptor = Union[
    None,
    QWidget,
    type[QWidget],
    "callable",
]


def _resolve_title_bar(title_bar: TitleBarDescriptor, parent: QWidget) -> QWidget:
    """Resolve a title-bar descriptor into a :class:`QWidget` instance.

    Parameters
    ----------
    title_bar:
        One of ``None`` (default :class:`LaceStandardTitleBar`), a
        :class:`QWidget` instance, a QWidget subclass, or a callable that
        returns a QWidget when called with *parent*.
    parent:
        The window that will own the title bar.

    Returns
    -------
    QWidget
        The resolved title-bar widget.
    """
    if title_bar is None:
        return LaceStandardTitleBar(parent)

    if isinstance(title_bar, QWidget):
        title_bar.setParent(parent)
        return title_bar

    if isinstance(title_bar, type):
        return title_bar(parent)

    if callable(title_bar):
        result = title_bar(parent)
        if not isinstance(result, QWidget):
            raise TypeError(
                f"title_bar callable must return a QWidget, got {type(result)}"
            )
        return result

    raise TypeError(
        f"title_bar must be None, QWidget, class, or callable, got {type(title_bar)}"
    )


class LaceStandardTitleBar(StandardTitleBar):
    """StandardTitleBar whose double-click-to-maximize is synchronous.

    qframelesswindow's default handler posts an async ``WM_SYSCOMMAND``
    ``SC_MAXIMIZE`` / ``SC_RESTORE`` (``toggleMaxState``).  On Windows that
    command is ignored while a mouse button is still held down — and a real
    double-click dispatches ``MouseButtonDblClick`` (and therefore the
    maximize request) while the second click's button is still pressed — so
    the maximize silently fails.  Depending on how quickly the button is
    released versus when the queued system command is processed, the
    double-click works or does nothing (the "stale" double-click).

    Using :meth:`QWidget.showMaximized` / :meth:`QWidget.showNormal`
    directly takes effect regardless of the button state, so the toggle is
    deterministic.

    Right-clicking the window icon opens the standard system menu
    (Restore / Move / Size / Minimize / Maximize / Close).  On Windows the
    native ``TrackPopupMenu`` system menu is used so items are localized
    and enabled/disabled automatically; on other platforms a ``QMenu``
    fallback with the same actions is shown.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.iconLabel.setContextMenuPolicy(Qt.CustomContextMenu)
        self.iconLabel.customContextMenuRequested.connect(self._show_system_menu)

    # -- system menu -----------------------------------------------------

    def _show_system_menu(self, pos: QPoint) -> None:
        """Show the window's system menu for a right-click on the icon."""
        global_pos = self.iconLabel.mapToGlobal(pos)
        if sys.platform == "win32":
            self._show_native_system_menu(global_pos)
        else:
            self._show_qt_system_menu(global_pos)

    def _show_native_system_menu(self, global_pos: QPoint) -> None:
        """Show the real Windows system menu via ``TrackPopupMenu``.

        The menu is owned by the window (``GetSystemMenu``) so it is
        localized and its items are enabled/disabled to match the current
        window state.  Selecting an item returns its ``SC_*`` command id,
        which is then posted back to the window as ``WM_SYSCOMMAND`` — the
        same mechanism the native title bar uses.
        """
        try:
            import win32con
            import win32gui
        except ImportError:
            self._show_qt_system_menu(global_pos)
            return

        hwnd = int(self.window().winId())
        hmenu = win32gui.GetSystemMenu(hwnd, False)
        if not hmenu:
            return
        flags = (
            win32con.TPM_RETURNCMD
            | win32con.TPM_NONOTIFY
            | win32con.TPM_LEFTALIGN
            | win32con.TPM_TOPALIGN
        )
        # Qt global coordinates are device-independent (logical) pixels,
        # but TrackPopupMenu positions the menu on the Win32 virtual
        # desktop, which is in physical device pixels.  On scaled displays
        # (e.g. 125% / 150%) the two differ, so convert before showing or
        # the menu appears offset from the cursor.
        dpr = self.window().devicePixelRatioF()
        x = round(global_pos.x() * dpr)
        y = round(global_pos.y() * dpr)
        cmd = win32gui.TrackPopupMenu(
            hmenu, flags, x, y, 0, hwnd, None
        )
        if cmd:
            win32gui.PostMessage(hwnd, win32con.WM_SYSCOMMAND, cmd, 0)

    def _show_qt_system_menu(self, global_pos: QPoint) -> None:
        """Fallback system menu for non-Windows platforms."""
        window = self.window()
        maximized = window.isMaximized()
        minimized = window.isMinimized()

        menu = QMenu(self)
        if maximized or minimized:
            menu.addAction("Restore", window.showNormal)
        menu.addAction("Move", self._start_system_move).setEnabled(not maximized)
        menu.addAction("Size", self._start_system_resize).setEnabled(not maximized)
        menu.addSeparator()
        menu.addAction("Minimize", window.showMinimized)
        menu.addAction("Maximize", window.showMaximized).setEnabled(not maximized)
        menu.addSeparator()
        menu.addAction("Close", window.close)
        menu.exec(global_pos)

    def _start_system_move(self) -> None:
        """Start an OS move loop for the parent window (cross-platform)."""
        handle = self.window().windowHandle()
        if handle is not None:
            handle.startSystemMove()

    def _start_system_resize(self) -> None:
        """Start an OS resize loop for the parent window (cross-platform)."""
        handle = self.window().windowHandle()
        if handle is not None:
            handle.startSystemResize(
                Qt.Edges(
                    Qt.Edge.LeftEdge
                    | Qt.Edge.RightEdge
                    | Qt.Edge.TopEdge
                    | Qt.Edge.BottomEdge
                )
            )

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() != Qt.LeftButton or not self._isDoubleClickEnabled:
            return
        window = self.window()
        if window.isMaximized():
            window.showNormal()
        else:
            window.showMaximized()


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
    both.  A :class:`.frameless_titlebar.FramelessTitleBarStyler` handles
    automatic theme colour updates.

    Parameters
    ----------
    parent:
        Optional parent widget.
    title_bar:
        Optional title-bar descriptor.  ``None`` uses the standard Lace
        title bar.  May also be a QWidget instance, a QWidget subclass, or
        a callable that returns a QWidget for this window.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title_bar: TitleBarDescriptor = None,
    ):
        super().__init__(parent)
        # Let native Win32 popup menus follow the system light/dark theme.
        _enable_system_dark_mode_menus()
        self._menu_bar: Optional[QMenuBar] = None
        self._menu_bar_container: Optional[QWidget] = None
        self._titlebar_styler: Optional["FramelessTitleBarStyler"] = None
        # Apply a custom title bar before integrating it into the main-window
        # layout.  When none is requested the base class already created a
        # default StandardTitleBar.
        if title_bar is not None:
            self.setTitleBar(_resolve_title_bar(title_bar, self))
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

        # Notify the styler about the new title bar.
        if self._titlebar_styler is not None:
            self._titlebar_styler.title_bar = self.titleBar

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

        # Notify the styler about the new menu bar.  Use add_menu_bar() so
        # any menu bars already registered by a custom title bar are kept.
        if self._titlebar_styler is not None:
            self._titlebar_styler.add_menu_bar(menu_bar)

        return menu_bar

    def setCentralWidget(self, widget: QWidget) -> None:
        """Override to keep the title bar above the central widget."""
        super().setCentralWidget(widget)
        self.titleBar.raise_()

    # -- theme integration ------------------------------------------------

    def titlebar_styler(self) -> Optional["FramelessTitleBarStyler"]:
        """Return the active :class:`.frameless_titlebar.FramelessTitleBarStyler`,
        or ``None`` if the window has not been registered with the dock style
        manager yet.

        Custom title bars can use this to register additional menu bars (for
        example an embedded menu bar) so they receive dock-theme colour
        updates.
        """
        return self._titlebar_styler

    def register_menu_bar_with_styler(self, menu_bar: QMenuBar) -> None:
        """Register an additional menu bar with the dock-theme styler.

        This is useful for custom title bars that embed a ``QMenuBar``
        directly inside the title-bar layout: the styler will apply the same
        background colour and palette to it as the rest of the chrome.
        """
        styler = self._titlebar_styler
        if styler is not None:
            styler.add_menu_bar(menu_bar)

    def _register_titlebar_theme(self) -> None:
        """Create a :class:`.frameless_titlebar.FramelessTitleBarStyler` that
        subscribes to ``DockStyleManager`` and applies theme colours to the
        title bar and menu bar.

        Call this once from DockManager or the application's setup code.
        """
        try:
            from lace.frameless_titlebar import FramelessTitleBarStyler
        except ImportError:
            return

        self._titlebar_styler = FramelessTitleBarStyler(
            title_bar=self.titleBar,
            menu_bar=self._menu_bar,
            parent=self,
        )


# ── Frameless Floating Window ──────────────────────────────────────────

class FramelessLaceWindow(FramelessWindow):
    """A frameless floating window that uses PySideSix-Frameless-Window
    for custom title bars on floating dock containers.

    Inherits from the platform-specific ``FramelessWindow`` which
    provides the same frameless infrastructure as
    ``FramelessLaceMainWindow`` but for plain ``QWidget`` windows.

    Parameters
    ----------
    parent:
        Optional parent widget.
    title_bar:
        Optional title-bar descriptor.  ``None`` keeps the default title bar
        created by the base class.  May also be a QWidget instance, a
        QWidget subclass, or a callable that returns a QWidget for this
        window.
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        title_bar: TitleBarDescriptor = None,
    ):
        super().__init__(parent)
        # Let native Win32 popup menus follow the system light/dark theme.
        _enable_system_dark_mode_menus()
        if title_bar is not None:
            self.setTitleBar(_resolve_title_bar(title_bar, self))


__all__ = [
    "FramelessLaceMainWindow",
    "FramelessLaceWindow",
    "LaceStandardTitleBar",
]
