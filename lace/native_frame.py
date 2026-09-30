# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.

"""Theme the OS frame of native-framed windows (dialogs, message boxes, tool
windows) to match Lace's custom title bar.

Lace's own windows draw their title bar themselves; every other window an app
shows has the system frame, which follows the Windows light/dark setting, not
the theme.  :func:`apply_native_frame` sets that frame's colours through DWM:

========================================  ===  ==============  ===================
Attribute                                 Id   OS              Value
========================================  ===  ==============  ===================
``DWMWA_USE_IMMERSIVE_DARK_MODE``         20   Win10 1809+     theme is dark
                                          (19 before build 19041)
``DWMWA_BORDER_COLOR``                    34   Win11 22000+    card outline, or
                                                               the system default
``DWMWA_CAPTION_COLOR``                   35   Win11 22000+    title-bar colour
``DWMWA_TEXT_COLOR``                      36   Win11 22000+    title text (dimmed
                                                               while inactive)
========================================  ===  ==============  ===================

Each attribute is best effort: an older Windows rejects the colour ones and
keeps the dark mode.  Off Windows, and for frameless windows, it does nothing.

:class:`NativeFrameTheme` applies it to every top-level window as it is shown,
again when a window gets a new native handle or changes activation, and to all
visible ones on a theme change.  :class:`DockManager` installs it; apps without
one call :func:`install_native_frame_theme`.  A window opts out with
``window.setProperty("laceNativeFrame", False)``.

Windows the OS draws itself -- the native file dialog, print dialogs -- are not
Qt widgets and stay out of reach; they follow the system light/dark mode.
"""

from __future__ import annotations

import logging
import sys
from typing import List, Optional, Tuple

from PySide6.QtCore import QEvent, QObject, Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import QApplication, QWidget

from lace.dock_theme import DockStyleCategory
from lace.title_bar_colors import TitleBarColors, title_bar_colors

logger = logging.getLogger(__name__)

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_19041 = 19
DWMWA_BORDER_COLOR = 34
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36
#: Tells DWM to use its own colour for the attribute.
DWMWA_COLOR_DEFAULT = 0xFFFFFFFF

#: Window property holding the last values applied, so repeat calls with an
#: unchanged theme leave DWM alone.
_KEY_PROPERTY = "_lace_frame_key"
#: Window property an app sets to False to keep Lace off a window's frame.
OPT_OUT_PROPERTY = "laceNativeFrame"

def _has_dwm() -> bool:
    """Whether windows have real HWNDs to call DWM on: Windows, and Qt's
    ``windows`` platform (under ``offscreen`` a winId is a counter, and
    passing it to Win32 could reach an unrelated window).  Tests replace it."""
    return (sys.platform == "win32"
            and QGuiApplication.platformName() == "windows")


def colorref(color: QColor) -> int:
    """*color* as a Win32 COLORREF (``0x00BBGGRR``)."""
    return color.red() | (color.green() << 8) | (color.blue() << 16)


# ---------------------------------------------------------------------------
# Win32 calls -- module functions so tests can replace them.
# ---------------------------------------------------------------------------
def _dwm_set(hwnd: int, attribute: int, value: int) -> bool:
    """``DwmSetWindowAttribute`` with a 4-byte value; True on success."""
    import ctypes
    data = ctypes.c_uint(value & 0xFFFFFFFF)
    try:
        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd), ctypes.c_uint(attribute),
            ctypes.byref(data), ctypes.sizeof(data))
    except Exception:
        logger.debug("DwmSetWindowAttribute unavailable", exc_info=True)
        return False
    if result != 0:
        logger.debug("DWM rejected attribute %d (HRESULT 0x%08x)",
                     attribute, result & 0xFFFFFFFF)
    return result == 0


def _frame_changed(hwnd: int) -> None:
    """Make Windows redraw the non-client area (a dark-mode flip on Win10
    does not repaint the caption by itself)."""
    import ctypes
    SWP_NOSIZE, SWP_NOMOVE, SWP_NOZORDER, SWP_NOACTIVATE, SWP_FRAMECHANGED = (
        0x1, 0x2, 0x4, 0x10, 0x20)
    try:
        ctypes.windll.user32.SetWindowPos(
            ctypes.c_void_p(hwnd), None, 0, 0, 0, 0,
            SWP_NOSIZE | SWP_NOMOVE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED)
    except Exception:
        logger.debug("SetWindowPos unavailable", exc_info=True)


# ---------------------------------------------------------------------------
# One window
# ---------------------------------------------------------------------------
def wants_native_frame(window: QWidget) -> bool:
    """Whether *window* has an OS frame Lace should theme.

    Top-level windows, dialogs and tool windows with a native frame; not
    popups, tooltips, splash screens, frameless windows, or a window whose
    ``laceNativeFrame`` property is False.
    """
    if not window.isWindow():
        return False
    if window.windowType() not in (Qt.WindowType.Window, Qt.WindowType.Dialog,
                                   Qt.WindowType.Tool):
        return False
    if window.windowFlags() & Qt.WindowType.FramelessWindowHint:
        return False
    return window.property(OPT_OUT_PROPERTY) is not False


def frame_values(window: QWidget, colors: TitleBarColors,
                 active: bool) -> Tuple[Tuple[int, int], ...]:
    """The ``(attribute, value)`` pairs :func:`apply_native_frame` sets."""
    backdrop = window.palette().color(window.backgroundRole())
    backdrop.setAlpha(255)
    caption = colors.opaque_background(backdrop)
    text = colors.text if active else colors.text_inactive
    if text.alpha() < 255:
        text = QColor.fromRgbF(*(t * text.alphaF() + c * (1 - text.alphaF())
                                 for t, c in zip(text.getRgbF()[:3], caption.getRgbF()[:3])))
    border = colorref(colors.border) if colors.border is not None else DWMWA_COLOR_DEFAULT
    return (
        (DWMWA_USE_IMMERSIVE_DARK_MODE, 1 if colors.is_dark else 0),
        (DWMWA_BORDER_COLOR, border),
        (DWMWA_CAPTION_COLOR, colorref(caption)),
        (DWMWA_TEXT_COLOR, colorref(text)),
    )


def apply_native_frame(window: QWidget, colors: Optional[TitleBarColors] = None,
                       active: Optional[bool] = None) -> bool:
    """Give *window*'s OS frame the theme's title-bar colours.

    Returns True when DWM was called, False when there was nothing to do: off
    Windows, a window without a native frame (see :func:`wants_native_frame`),
    or values unchanged since the last call for this native handle.
    *active* defaults to ``window.isActiveWindow()``.
    """
    if not _has_dwm() or not wants_native_frame(window):
        return False
    hwnd = int(window.winId())
    if not hwnd:
        return False
    if colors is None:
        colors = title_bar_colors()
    if active is None:
        active = window.isActiveWindow()

    values = frame_values(window, colors, active)
    previous = window.property(_KEY_PROPERTY)
    key = (hwnd,) + tuple(v for _, v in values)
    if previous is not None and tuple(previous) == key:
        return False

    for attribute, value in values:
        if not _dwm_set(hwnd, attribute, value) and attribute == DWMWA_USE_IMMERSIVE_DARK_MODE:
            _dwm_set(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_19041, value)
    window.setProperty(_KEY_PROPERTY, list(key))

    # A dark-mode flip on an existing handle needs a non-client repaint on
    # Win10; the colour attributes repaint by themselves.
    if previous is not None and previous[0] == hwnd and previous[1] != key[1]:
        _frame_changed(hwnd)
    return True


# ---------------------------------------------------------------------------
# Every window
# ---------------------------------------------------------------------------
class NativeFrameTheme(QObject):
    """Applies :func:`apply_native_frame` to every top-level window.

    An application event filter catches windows as they are shown, get a new
    native handle, or change activation; a style subscription re-applies to
    the visible ones on a theme change.  Install through
    :func:`install_native_frame_theme`.
    """

    _EVENTS = {
        QEvent.Type.Show: None,
        QEvent.Type.WinIdChange: None,
        QEvent.Type.WindowActivate: True,
        QEvent.Type.WindowDeactivate: False,
    }
    _STYLE_CATEGORIES = (DockStyleCategory.TITLE_BAR, DockStyleCategory.CORE,
                         DockStyleCategory.SIDEBAR)

    def __init__(self, app: QApplication) -> None:
        super().__init__(app)
        self._refresh_queued = False
        from lace.dock_style_manager import get_dock_style_manager
        self._style_mgr = get_dock_style_manager()
        for category in self._STYLE_CATEGORIES:
            self._style_mgr.register(self, category)
        app.installEventFilter(self)
        self.apply_to_all()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        kind = event.type()
        if kind in self._EVENTS and obj.isWidgetType() and obj.isWindow():
            try:
                apply_native_frame(obj, active=self._EVENTS[kind])
            except RuntimeError:
                pass    # the window is being destroyed
        return False

    def on_style_changed(self, category, changes) -> None:
        """Re-apply once per theme change, after all categories have landed."""
        if not self._refresh_queued:
            self._refresh_queued = True
            QTimer.singleShot(0, self, self._refresh)

    def _refresh(self) -> None:
        self._refresh_queued = False
        self.apply_to_all()

    def apply_to_all(self) -> List[QWidget]:
        """Apply to every visible top-level window; returns those updated."""
        colors = title_bar_colors(self._style_mgr)
        updated = []
        for window in QApplication.topLevelWidgets():
            if window.isVisible() and apply_native_frame(window, colors):
                updated.append(window)
        return updated

    def uninstall(self) -> None:
        """Stop theming frames (frames already themed keep their colours)."""
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        self._style_mgr.unregister(self)


_installed: Optional[NativeFrameTheme] = None


def install_native_frame_theme(app: Optional[QApplication] = None) -> Optional[NativeFrameTheme]:
    """Theme the native frame of every window *app* shows; idempotent.

    Returns the installed :class:`NativeFrameTheme`, or None without a
    ``QApplication``.  :class:`DockManager` calls this unless created with
    ``native_frames=False``.
    """
    global _installed
    app = app or QApplication.instance()
    if app is None:
        return None
    if _installed is not None:
        try:
            if _installed.parent() is app:
                return _installed
        except RuntimeError:
            pass    # the previous application, and this object with it, is gone
    _installed = NativeFrameTheme(app)
    return _installed


def uninstall_native_frame_theme() -> None:
    """Undo :func:`install_native_frame_theme`."""
    global _installed
    if _installed is not None:
        try:
            _installed.uninstall()
            _installed.deleteLater()
        except RuntimeError:
            pass
        _installed = None


__all__ = [
    "apply_native_frame", "wants_native_frame", "frame_values", "colorref",
    "NativeFrameTheme", "install_native_frame_theme", "uninstall_native_frame_theme",
    "OPT_OUT_PROPERTY", "DWMWA_COLOR_DEFAULT",
]
