# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2019 Ken Lauer
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace, adapted from qtpydocking.
# Original code Copyright (c) 2019 Ken Lauer (BSD-3-Clause).
# Modifications Copyright (c) 2026 opticsWolf (Apache-2.0).

import logging
import sys
from typing import TYPE_CHECKING, Any, Optional, Type, TypeVar, List

from PySide6.QtCore import Qt, QObject
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtWidgets import QApplication, QWidget, QStyle, QAbstractButton, QSplitter

if TYPE_CHECKING:
    from lace.dock_splitter import DockSplitter
    from lace.dock_widget import DockWidget

logger = logging.getLogger(__name__)

DEBUG_LEVEL = 0

# Modern Generics for precise Type Hinting and IDE auto-completion
T = TypeVar('T', bound=QObject)
W = TypeVar('W', bound=QWidget)


def emit_top_level_event_for_widget(widget: Optional['DockWidget'], floating: bool):
    """
    Emits a topLevelChanged() signal and updates the dock area tool bar visibility.
    """
    if widget is None:
        return

    # A widget between areas has no area yet; the signal still has to go out.
    dock_area = widget.dock_area_widget()
    if dock_area is not None:
        dock_area.ensure_title_bar_visible()
    widget.emit_top_level_changed(floating)


def start_drag_distance() -> int:
    """
    The distance the user needs to move the mouse with the left button held
    down before a dock widget starts floating.
    """
    return int(QApplication.startDragDistance() * 1.5)


def create_transparent_pixmap(source: QPixmap, opacity: float) -> QPixmap:
    """
    Creates a semi-transparent pixmap from the given source pixmap.
    """
    transparent_pixmap = QPixmap(source.size())
    transparent_pixmap.fill(Qt.transparent)
    
    painter = QPainter(transparent_pixmap)
    painter.setOpacity(opacity)
    painter.drawPixmap(0, 0, source)
    painter.end()
    
    return transparent_pixmap


def set_button_icon(style: QStyle, button: QAbstractButton, icon_type: QStyle.StandardPixmap):
    """
    Applies a standard OS icon to a button using the application's current style.
    """
    button.setIcon(style.standardIcon(icon_type))


def hide_empty_parent_splitters(splitter: Optional['DockSplitter']):
    """
    Walks up the widget tree and hides all splitters that do not have visible content.
    """
    from lace.dock_splitter import DockSplitter
    while splitter and splitter.isVisible():
        if not splitter.has_visible_content():
            splitter.hide()

        splitter = find_parent(DockSplitter, splitter)


def find_parent(parent_type: Type[W], widget: QWidget) -> Optional[W]:
    """
    Searches up the widget tree for the parent widget of the given type.
    Utilizes TypeVar so the return type matches the requested parent_type.
    """
    parent_widget = widget.parentWidget()
    while parent_widget:
        if isinstance(parent_widget, parent_type):
            return parent_widget
        parent_widget = parent_widget.parentWidget()
    return None


def _floating_container_type() -> type:
    """The one thing both floating-container implementations have in common.

    Testing against the shared behaviour mixin rather than the two concrete
    classes: it costs no import of qframelesswindow, and it cannot go stale
    the way a hand-listed tuple of implementations does.
    """
    from lace.floating_behaviour import FloatingContainerBehaviour
    return FloatingContainerBehaviour


def is_floating_dock_container(widget: Any) -> bool:
    """True if *widget* is a floating dock container of either kind.

    The supported check — ``isinstance(x, lace.FloatingDockContainer)`` is
    wrong in custom-titlebar mode, where the float is a
    :class:`~lace.floating_dock_container_frameless.FramelessFloatingDockContainer`.
    """
    return isinstance(widget, _floating_container_type())


def find_floating_dock_container(widget: QWidget) -> Optional[QWidget]:
    """Search up the widget tree for any floating-container implementation."""
    return find_parent(_floating_container_type(), widget)


# ── window maximize state ────────────────────────────────────────────────
#
# Qt and Win32 can hold different opinions about whether a *frameless* window
# is maximized, and undoing one with the other does not work. Qt's
# showMaximized() on a frameless window is a pure geometry change that leaves
# the Win32 placement at SW_NORMAL; a native maximize (Aero Snap, Win+Up, a
# WM_SYSCOMMAND SC_MAXIMIZE) sets SW_MAXIMIZED and Qt only observes it.
#
# showNormal() cannot undo the native one: the first call is a no-op and the
# second clears Qt's flag while the window stays maximized, which is
# unrecoverable from the Qt side and leaves the window unmovable as well,
# because Windows refuses SC_MOVE for a zoomed window.
#
# So: ask the OS whether the window is maximized, and restore it the way it
# was maximized. See docs/FRAMELESS_WINDOW_STATE.md.
_SW_MAXIMIZE = 3
_SW_RESTORE = 9


def _natively_maximized(window: QWidget) -> Optional[bool]:
    """The OS's own answer, or ``None`` when it cannot be asked."""
    if sys.platform != "win32":
        return None
    if window.windowHandle() is None:
        return None
    try:
        import win32gui

        placement = win32gui.GetWindowPlacement(int(window.winId()))
    except Exception:
        logger.debug("Window placement unavailable", exc_info=True)
        return None
    if not placement:
        return None
    return placement[1] == _SW_MAXIMIZE


def is_window_maximized(widget: QWidget) -> bool:
    """Whether *widget*'s window is maximized, preferring the OS's answer.

    The OS answer is the one that decides whether the window can still be
    moved, and it stays right when Qt's has gone stale.
    """
    window = widget.window()
    return bool(_natively_maximized(window)) or window.isMaximized()


def restore_window(widget: QWidget) -> None:
    """Un-maximize *widget*'s window through whichever mechanism maximized it."""
    window = widget.window()
    if _natively_maximized(window):
        try:
            import win32gui

            # ShowWindow rather than a posted WM_SYSCOMMAND SC_RESTORE: it is
            # synchronous, and Windows ignores SC_* while a mouse button is
            # still held — which is exactly the state a double-click is in.
            win32gui.ShowWindow(int(window.winId()), _SW_RESTORE)
            return
        except Exception:
            logger.debug("Native restore unavailable; falling back to Qt",
                         exc_info=True)
    window.showNormal()


def toggle_window_maximized(widget: QWidget) -> None:
    """Maximize *widget*'s window, or restore it — synchronously either way."""
    window = widget.window()
    if is_window_maximized(window):
        restore_window(window)
    else:
        window.showMaximized()


def find_child(parent: QObject, type_: Type[T], name: str = '',
               options: Qt.FindChildOptions = Qt.FindChildrenRecursively) -> Optional[T]:
    """
    Strongly-typed wrapper around QObject.findChild().
    Returns the child of this object that can be cast into the given type.
    """
    return parent.findChild(type_, name, options)


def find_children(parent: QObject, type_: Type[T], name: str = '',
                  options: Qt.FindChildOptions = Qt.FindChildrenRecursively) -> List[T]:
    """
    Strongly-typed wrapper around QObject.findChildren().
    Returns all children of this object that can be cast to the given type.
    """
    return parent.findChildren(type_, name, options)


def _dump_recursive(level: int, widget: QWidget) -> None:
    indent = ' ' * level * 4
    if isinstance(widget, QSplitter):
        logger.debug(
            "%sSplitter %s v: %s c: %s", indent,
            ('|' if widget.orientation() == Qt.Vertical else '--'),
            (' ' if widget.isHidden() else 'v'), widget.count(),
        )
        for i in range(widget.count()):
            _dump_recursive(level + 1, widget.widget(i))
    elif hasattr(widget, 'dock_widgets'):  # DockAreaWidget (duck-typed to avoid a cycle)
        logger.debug('%sDockArea', indent)
        logger.debug('%s%s %s DockArea', indent,
                     ' ' if widget.isHidden() else 'v',
                     ' ' if widget.open_dock_widgets_count() > 0 else 'c')
        indent = ' ' * (level + 1) * 4
        for i, dock_widget in enumerate(widget.dock_widgets()):
            logger.debug('%s%s%s%s %s', indent,
                         '*' if i == widget.current_index() else ' ',
                         ' ' if i == dock_widget.isHidden() else 'v',
                         'c' if i == dock_widget.is_closed() else ' ',
                         dock_widget.windowTitle())


def dump_layout(container) -> None:
    """Debug-log the splitter / dock-area tree under ``container`` (no-op unless
    DEBUG logging is enabled)."""
    if not logger.isEnabledFor(logging.DEBUG):
        return
    logger.debug("--------------------------")
    _dump_recursive(0, container.root_splitter())
    logger.debug("--------------------------\n\n")