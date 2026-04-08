# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2019 Ken Lauer
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0

This file is part of Lace, adapted from qtpydocking.
Original code Copyright (c) 2019 Ken Lauer (BSD-3-Clause).
Modifications Copyright (c) 2026 opticsWolf (Apache-2.0).
"""

import enum
from typing import NamedTuple
from PySide6.QtCore import Qt


class DockInsertParam(NamedTuple):
    """
    Parameters defining how a dock widget should be inserted into a layout.

    Attributes:
        orientation (Qt.Orientation): The horizontal or vertical direction of insertion.
        append (bool): If True, the widget is added after existing widgets; 
            otherwise, it is prepended.
    """
    orientation: Qt.Orientation
    append: bool

    @property
    def insert_offset(self) -> int:
        """
        Calculates the integer offset for layout insertion based on the append flag.
        
        Returns:
            int: 1 if appending, 0 if prepending.
        """
        return 1 if self.append else 0


class DockWidgetArea(enum.IntFlag):
    """
    Defines the physical regions within a window where widgets can be docked.
    
    Uses :class:`enum.auto` to assign powers of two, allowing multiple areas 
    to be combined using bitwise OR (e.g., ``top | bottom``).
    """
    no_area = 0
    """Represents a state with no defined docking area."""

    left = enum.auto()
    """The leftmost docking region."""
    
    right = enum.auto()
    """The rightmost docking region."""
    
    top = enum.auto()
    """The uppermost docking region."""
    
    bottom = enum.auto()
    """The lowermost docking region."""
    
    center = enum.auto()
    """The central area, usually reserved for the main workspace."""

    invalid = no_area
    """Alias for no_area, indicating an invalid docking operation."""

    outer_dock_areas = left | right | top | bottom
    """A mask for all areas except the center."""

    all_dock_areas = outer_dock_areas | center
    """A mask representing every possible docking area."""


class DockFlags(enum.IntFlag):
    """
    Configuration flags for the advanced docking system.
    """
    none_ = 0
    
    opaque_splitter_resize = enum.auto()
    """Splitters instantly resize content instead of showing a rubber band."""
    
    opaque_undocking = enum.auto()
    """Widgets instantly follow the cursor when torn off."""
       
    always_show_tabs = enum.auto()
    """Tabs are always shown, even if there is only one widget in the area."""
    
    show_tab_close_button = enum.auto()
    """Tabs display their own close button."""
    
    active_tab_has_close_button = enum.auto()
    """Only the currently active tab displays a close button."""
    
    dock_area_has_close_button = enum.auto()
    """The dock area title bar displays a close button."""
    
    dock_area_close_button_closes_tab = enum.auto()
    """Clicking the dock area close button closes the active tab, not the whole area."""
    
    dock_area_has_undock_button = enum.auto()
    """The dock area title bar displays an undock button."""
    
    dock_area_has_tabs_menu_button = enum.auto()
    """The dock area title bar displays a menu button listing all tabs."""
    
    middle_mouse_button_closes_tab = enum.auto()
    """Clicking a tab with the middle mouse button closes it."""
    
    floatable_tabs = enum.auto()
    """Tabs can be dragged out to float in their own window."""
    
    pinnable_tabs = enum.auto()
    """Tabs can be pinned into sidebar."""
    
    custom_tab_icons = enum.auto()
    """Use custom icons provided via user config instead of defaults."""
    
    drag_preview_shows_content_pixmap = enum.auto()
    """Shows a snapshot of the widget content while dragging."""

    title_bar_has_pin_button = enum.auto()

    #xml_compression = enum.auto()
    #"""(Deprecated) Compresses the XML state save files."""
    # 
    #xml_auto_formatting = enum.auto()
    #"""(Deprecated) Pretty-prints the XML state save files."""

    default_config = (
        opaque_splitter_resize | opaque_undocking | always_show_tabs |
        show_tab_close_button | active_tab_has_close_button |
        dock_area_has_close_button | dock_area_has_undock_button |
        dock_area_has_tabs_menu_button | middle_mouse_button_closes_tab |
        title_bar_has_pin_button | floatable_tabs | drag_preview_shows_content_pixmap
    )
    """The default configuration flags applied to a new DockManager."""


class TitleBarButton(enum.Enum):
    """
    Identifiers for the standard buttons in a dock area title bar.
    """
    tabs_menu = enum.auto()
    undock = enum.auto()
    close = enum.auto()
    pin = enum.auto()


class OverlayMode(enum.Enum):
    """
    Controls how the drag-and-drop drop-zone overlays are rendered.
    """
    dock_area = enum.auto()
    container = enum.auto()


class DragState(enum.Enum):
    """
    The current dragging context of a dock widget or area.
    """
    inactive = enum.auto()
    mouse_pressed = enum.auto()
    tab = enum.auto()
    floating_widget = enum.auto()


class InsertionOrder(enum.Enum):
    """
    Determines how items are sorted when inserted into menus.
    """
    by_spelling = enum.auto()
    by_insertion = enum.auto()


class DockWidgetFeature(enum.IntFlag):
    """
    Capabilities enabled for a specific Dock Widget.
    """
    no_features = 0
    """The widget cannot be moved, closed, or floated."""
    
    closable = enum.auto()
    """The widget can be closed."""
    
    movable = enum.auto()
    """The widget can be dragged to different dock areas."""
    
    floatable = enum.auto()
    """The widget can be detached into its own top-level window."""
    
    pinnable = enum.auto()
    """The widget can be pinned to a sidebar."""
    
    all_features = closable | movable | floatable | pinnable
    """Enables all interaction capabilities."""


class WidgetState(enum.Enum):
    """
    The current visibility and attachment status of a Dock Widget.
    """
    hidden = enum.auto()
    """The widget is not visible and not part of the active layout."""
    
    docked = enum.auto()
    """The widget is attached to a dock area within the main window."""
    
    floating = enum.auto()
    """The widget is detached in a separate window."""

    pinned_shown = enum.auto()
    """The widget is pinned to as sidebar and shown."""
    
    pinned_hidden = enum.auto()
    """The widget is pinned to as sidebar and hidden."""


class InsertMode(enum.Enum):
    """
    Rules for handling widget overflows and scrollbar behavior during insertion.
    """
    auto_scroll_area = enum.auto()
    """Adds scrollbars automatically only if the content exceeds available space."""
    
    force_scroll_area = enum.auto()
    """Always wraps the widget in a scroll area, regardless of size."""
    
    force_no_scroll_area = enum.auto()
    """Prevents scrollbars; content may be clipped if it exceeds space."""

class ToggleViewActionMode(enum.Enum):
    """
    Defines the behavior of menu actions linked to widget visibility.
    """
    toggle = enum.auto()
    """The action flips the current visibility state (Show -> Hide -> Show)."""
    
    show = enum.auto()
    """The action only makes the widget visible; clicking while visible does nothing."""