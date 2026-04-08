import sys
import logging
from typing import TYPE_CHECKING, Optional, Type, TypeVar, List

from PySide6.QtCore import Qt, QObject
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtWidgets import QApplication, QWidget, QStyle, QAbstractButton

if TYPE_CHECKING:
    from .dock_splitter import DockSplitter
    from .dock_widget import DockWidget

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
    from .dock_splitter import DockSplitter
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