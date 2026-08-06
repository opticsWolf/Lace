# -*- coding: utf-8 -*-
"""Core enums & configuration tests — ARCHITECTURE.md §8 (enums.py).

Verifies the bit-mask invariants that the docking math relies on
(DockWidgetArea zones, DockFlags defaults, DockWidgetFeature masks) and the
insertion helpers used by the layout code.
"""

from PySide6.QtCore import Qt

from lace.enums import (
    DockInsertParam,
    DockWidgetArea,
    DockFlags,
    TitleBarButton,
    OverlayMode,
    DragState,
    InsertionOrder,
    DockWidgetFeature,
    WidgetState,
    InsertMode,
    ToggleViewActionMode,
    SideBarFocusBehavior,
)
from lace.dock_theme import DockStyleCategory
from lace.sidebar_tab import TabBadgePosition


# ---------------------------------------------------------------------------
# DockWidgetArea zones
# ---------------------------------------------------------------------------
def test_dock_widget_area_power_of_two_zones():
    assert DockWidgetArea.no_area == 0
    assert DockWidgetArea.left == 1
    assert DockWidgetArea.right == 2
    assert DockWidgetArea.top == 4
    assert DockWidgetArea.bottom == 8
    assert DockWidgetArea.center == 16


def test_dock_widget_area_masks():
    assert DockWidgetArea.outer_dock_areas == 15  # left|right|top|bottom
    assert DockWidgetArea.all_dock_areas == 31    # outer|center
    assert DockWidgetArea.invalid == DockWidgetArea.no_area
    assert (DockWidgetArea.left | DockWidgetArea.right) in DockWidgetArea.outer_dock_areas
    assert DockWidgetArea.center not in DockWidgetArea.outer_dock_areas


# ---------------------------------------------------------------------------
# DockFlags configuration
# ---------------------------------------------------------------------------
def test_dock_flags_none_is_zero():
    assert DockFlags.none_ == 0


def test_default_config_contains_core_flags():
    for flag in (
        DockFlags.opaque_splitter_resize,
        DockFlags.opaque_undocking,
        DockFlags.always_show_tabs,
        DockFlags.show_tab_close_button,
        DockFlags.active_tab_has_close_button,
        DockFlags.dock_area_has_close_button,
        DockFlags.dock_area_has_pin_button,
        DockFlags.dock_area_has_maximize_button,
        DockFlags.dock_area_has_tabs_menu_button,
        DockFlags.middle_mouse_button_closes_tab,
        DockFlags.floatable_tabs,
        DockFlags.pinnable_tabs,
        DockFlags.hide_disabled_title_bar_icons,
    ):
        assert flag in DockFlags.default_config, flag.name
    # Opt-in flags are NOT enabled by default
    for flag in (DockFlags.custom_tab_icons,
                 DockFlags.dock_area_close_button_closes_tab,
                 DockFlags.chromeless_float):
        assert flag not in DockFlags.default_config, flag.name


def test_default_config_matches_architecture_doc():
    # The combined default mask from dock_custom/dock config (ARCHITECTURE.md §8.1).
    expected = (
        DockFlags.opaque_splitter_resize | DockFlags.opaque_undocking
        | DockFlags.always_show_tabs | DockFlags.show_tab_close_button
        | DockFlags.active_tab_has_close_button | DockFlags.dock_area_has_close_button
        | DockFlags.dock_area_has_undock_button | DockFlags.dock_area_has_pin_button
        | DockFlags.dock_area_has_maximize_button | DockFlags.dock_area_has_tabs_menu_button
        | DockFlags.middle_mouse_button_closes_tab | DockFlags.floatable_tabs
        | DockFlags.pinnable_tabs | DockFlags.hide_disabled_title_bar_icons
        | DockFlags.sidebar_area_has_maximize_button
    )
    assert DockFlags.default_config == expected


# ---------------------------------------------------------------------------
# DockWidgetFeature
# ---------------------------------------------------------------------------
def test_dock_widget_feature_all_features_mask():
    combined = (DockWidgetFeature.closable | DockWidgetFeature.movable
                | DockWidgetFeature.floatable | DockWidgetFeature.pinnable)
    assert DockWidgetFeature.all_features == combined == 15


def test_dock_widget_feature_composition():
    flags = DockWidgetFeature.closable | DockWidgetFeature.floatable
    assert flags & DockWidgetFeature.closable
    assert not flags & DockWidgetFeature.pinnable


# ---------------------------------------------------------------------------
# DockInsertParam
# ---------------------------------------------------------------------------
def test_insert_param_offsets():
    assert DockInsertParam(Qt.Orientation.Horizontal, append=True).insert_offset == 1
    assert DockInsertParam(Qt.Orientation.Horizontal, append=False).insert_offset == 0
    assert DockInsertParam(Qt.Orientation.Vertical, True).orientation == Qt.Orientation.Vertical


# ---------------------------------------------------------------------------
# Enum member inventories
# ---------------------------------------------------------------------------
def test_member_inventories_match_architecture_doc():
    assert {m.name for m in TitleBarButton} == {
        "tabs_menu", "undock", "close", "pin", "maximize", "minimize", "restore",
    }
    assert {m.name for m in OverlayMode} == {"dock_area", "container"}
    assert {m.name for m in DragState} == {"inactive", "mouse_pressed", "tab", "floating_widget"}
    assert {m.name for m in InsertionOrder} == {"by_spelling", "by_insertion"}
    assert {m.name for m in WidgetState} == {"docked", "floating", "pinned_shown", "pinned_hidden"}
    assert {m.name for m in InsertMode} == {
        "auto_scroll_area", "force_scroll_area", "force_no_scroll_area",
    }
    assert {m.name for m in ToggleViewActionMode} == {"toggle", "show"}
    assert {m.name for m in SideBarFocusBehavior} == {
        "take_focus_and_restore", "no_focus_transfer", "take_focus_only",
    }
    assert {m.name for m in TabBadgePosition} == {
        "top_left", "top_right", "bottom_left", "bottom_right",
    }
    assert {m.name for m in DockStyleCategory} == {
        "CORE", "PANEL", "TAB", "TITLE_BAR", "SIDEBAR", "SIDEPANEL", "SPLITTER", "OVERLAY",
    }
