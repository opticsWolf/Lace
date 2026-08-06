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

    widget.dock_area_widget().update_title_bar_visibility()
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


def _floating_container_types() -> tuple:
    """Return the tuple of all :class:`FloatingDockContainer` implementations.

    Includes the native-title-bar container and, when qframelesswindow is
    available, the frameless (custom title bar) variant.
    """
    from lace.floating_dock_container import FloatingDockContainer
    types = [FloatingDockContainer]
    try:
        from lace.floating_dock_container_frameless import (
            FloatingDockContainer as FramelessFloatingDockContainer)
        types.append(FramelessFloatingDockContainer)
    except ImportError:
        pass
    return tuple(types)


def is_floating_dock_container(widget: Any) -> bool:
    """True if *widget* is either floating-container implementation."""
    return isinstance(widget, _floating_container_types())


def find_floating_dock_container(widget: QWidget) -> Optional[QWidget]:
    """Search up the widget tree for any floating-container implementation."""
    return find_parent(_floating_container_types(), widget)


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