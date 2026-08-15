# -*- coding: utf-8 -*-
"""Core enums & configuration tests — ARCHITECTURE.md §8 (enums.py).

Verifies the bit-mask invariants that the docking math relies on
(DockWidgetArea zones, DockFlags defaults, DockWidgetFeature masks) and the
insertion helpers used by the layout code.
"""

import ast
import pathlib

import pytest
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


@pytest.fixture(scope="module")
def flag_docstrings():
    """``{member_name: doc}`` for DockFlags, read out of the source.

    Enum members do not keep the string literal that follows them, so the
    only way to assert anything about those doc comments is to parse them.
    """
    path = pathlib.Path(__file__).resolve().parent.parent / "lace" / "enums.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(n for n in ast.walk(tree)
               if isinstance(n, ast.ClassDef) and n.name == "DockFlags")

    docs, pending = {}, None
    for node in cls.body:
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name):
            pending = node.targets[0].id
            docs[pending] = ""
        elif (isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str) and pending):
            docs[pending] = node.value.value
            pending = None
    assert "opaque_undocking" in docs, "the parse found no flags at all"
    return docs


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
                 DockFlags.chromeless_float,
                 DockFlags.floating_taskbar_button):
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


def test_no_flag_claims_to_be_unimplemented(flag_docstrings):
    """§5.3 — three flags carried that disclaimer while being read in anger.

    A doc comment is the only thing a caller has to go on. Rather than pin the
    three, forbid the phrase: the next flag to be finished must have its
    docstring updated with it.
    """
    stale = [name for name, doc in flag_docstrings.items()
             if "requires implementation" in doc.lower()
             or "not in use" in doc.lower()]
    assert not stale, f"docstring says unimplemented: {stale}"


def test_every_flag_is_actually_consulted(flag_docstrings):
    """A flag nothing reads is a setting that silently does nothing."""
    import pathlib

    source = "\n".join(
        p.read_text(encoding="utf-8")
        for p in pathlib.Path(__file__).resolve().parent.parent.glob("lace/*.py")
        if p.name != "enums.py")

    for name in flag_docstrings:
        if name in ("none_", "default_config"):
            continue
        assert f"DockFlags.{name}" in source, f"{name} is never read"


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
