# -*- coding: utf-8 -*-
"""Friendly Python façade over the `_lace_rs` extension.

`_lace_rs` speaks JSON strings at its boundary (colours as ``[r, g, b, a]``
lists); this package parses them into plain dicts/lists, accepts dicts or
JSON text as input, and documents which :mod:`lace` API each helper mirrors.

Errors mirror :mod:`lace.layout_serializer` — ``LayoutError`` with
``LayoutIOError`` / ``InvalidFormatError`` / ``RestoreFailureError`` — so
``except LayoutError`` guards keep working. Theme-file validation raises
``ValidationError`` (like pydantic's, not a ``LayoutError``).
"""

import json as _json

from _lace_rs import (
    InvalidFormatError,
    LayoutError,
    LayoutIOError,
    RestoreFailureError,
    ValidationError,
    allowed_areas,
    available_themes,
    blank_layout as _blank_layout,
    build_merged_theme as _build_merged_theme,
    build_theme as _build_theme,
    dock_floating as _dock_floating,
    dock_widget as _dock_widget,
    drop_container_edge as _drop_container_edge,
    drop_edges as _drop_edges,
    float_widget as _float_widget,
    gc_empty_floats as _gc_empty_floats,
    load_theme_file as _load_theme_file,
    move_container_center as _move_container_center,
    move_widget as _move_widget,
    pin_widget as _pin_widget,
    remove_widget as _remove_widget,
    set_closed as _set_closed,
    set_current as _set_current,
    split_share,
    theme_groups as _theme_groups,
    unpin_widget as _unpin_widget,
    validate_layout as _validate_layout,
)

__all__ = [
    "LayoutError",
    "LayoutIOError",
    "InvalidFormatError",
    "RestoreFailureError",
    "ValidationError",
    "split_share",
    "allowed_areas",
    "available_themes",
    "theme_groups",
    "build_theme",
    "build_merged_theme",
    "load_theme_file",
    "blank_layout",
    "validate_layout",
    "dock_widget",
    "move_widget",
    "move_container_center",
    "drop_container_edge",
    "remove_widget",
    "set_closed",
    "set_current",
    "float_widget",
    "dock_floating",
    "pin_widget",
    "unpin_widget",
    "drop_edges",
    "gc_empty_floats",
    "__version__",
]

try:
    from _lace_rs import __version__
except ImportError:  # pragma: no cover - always set by maturin builds
    __version__ = "0.0.0"


def _to_json(doc) -> str:
    """Accept a layout dict or JSON text, return JSON text."""
    if isinstance(doc, str):
        return doc
    return _json.dumps(doc)


def theme_groups():
    """``[[title, [[label, key], ...]], ...]`` in presentation order.

    Mirrors ``lace.dock_style_manager.theme_groups``.
    """
    return _json.loads(_theme_groups())


def build_theme(name):
    """Engine-shaped theme dict, like a ``DOCK_THEMES`` entry.

    Mirrors ``lace.dock_theme.build_theme(THEME_SPECS[name])``.
    """
    return _json.loads(_build_theme(name))


def build_merged_theme(name):
    """``get_all()``-shaped theme dict (schema defaults under the preset).

    Mirrors applying a theme on the style manager and reading every token.
    """
    return _json.loads(_build_merged_theme(name))


def load_theme_file(path):
    """Load a JSON theme file and derive the full theme dict.

    Mirrors ``lace.theme_models.load_theme_json``.
    """
    return _json.loads(_load_theme_file(str(path)))


def blank_layout(app_version=0):
    """A fresh, valid empty layout document (dict)."""
    return _json.loads(_blank_layout(app_version))


def validate_layout(doc, target_version=0, available=None):
    """Validate a layout dict; returns ``{"warnings", "pruned", "doc"}``.

    Corrupt payloads raise ``InvalidFormatError``; structurally broken trees
    raise ``RestoreFailureError``. Mirrors ``LayoutSerializer.deserialize``
    guards (without touching any widget).
    """
    if available is None:
        # Default roster, computed leniently: unparsable text yields [],
        # and the validator below reports the real InvalidFormatError.
        try:
            available = list(_json.loads(_to_json(doc)).get("widget_states", {}).keys())
        except ValueError:
            available = []
    report = _json.loads(_validate_layout(_to_json(doc), target_version, list(available)))
    report["doc"] = _json.loads(report["doc"])
    return report


def dock_widget(doc, name, edge, target=None, closed=False):
    """Dock a widget; returns the new layout dict.

    ``target`` is ``None`` (first area) or ``(container, [path])``.
    Mirrors the programmatic insertion path (centre tabs, edges split).
    """
    return _json.loads(_dock_widget(_to_json(doc), name, edge, target, closed))


def move_widget(doc, name, edge, container, path):
    """Move an existing widget; returns the new layout dict."""
    return _json.loads(_move_widget(_to_json(doc), name, edge, container, list(path)))


def move_container_center(doc, name, container):
    """Container-level centre drop (solo tabs in, multi takes the fallback)."""
    return _json.loads(_move_container_center(_to_json(doc), name, container))


def drop_container_edge(doc, name, container, edge):
    """Container-level edge drop (root split)."""
    return _json.loads(_drop_container_edge(_to_json(doc), name, container, edge))


def remove_widget(doc, name):
    """Forget a widget; returns ``(new_doc, found)``."""
    new_doc, found = _remove_widget(_to_json(doc), name)
    return _json.loads(new_doc), found


def set_closed(doc, name, closed):
    """Flip a widget's closed flag; returns ``(new_doc, found)``."""
    new_doc, found = _set_closed(_to_json(doc), name, closed)
    return _json.loads(new_doc), found


def set_current(doc, container, path, name):
    """Point an area's current tab at ``name``; returns the new layout dict."""
    return _json.loads(_set_current(_to_json(doc), container, list(path), name))


def float_widget(doc, name):
    """Tear a widget into a new float; returns ``(new_doc, container_id)``."""
    new_doc, container_id = _float_widget(_to_json(doc), name)
    return _json.loads(new_doc), container_id


def dock_floating(doc, container_id):
    """Bring a floating container's widgets home; returns the new dict."""
    return _json.loads(_dock_floating(_to_json(doc), container_id))


def pin_widget(doc, name, area):
    """Pin a widget to the auto-hide sidebar; returns the new layout dict."""
    return _json.loads(_pin_widget(_to_json(doc), name, area))


def unpin_widget(doc, name):
    """Return a pinned widget to the main container."""
    return _json.loads(_unpin_widget(_to_json(doc), name))


def drop_edges(doc, container):
    """Zones a container offers (``allowed_areas_for`` at document level)."""
    return _drop_edges(_to_json(doc), container)


def gc_empty_floats(doc):
    """Drop widget-less floating containers; returns ``(new_doc, ids)``."""
    new_doc, removed = _gc_empty_floats(_to_json(doc))
    return _json.loads(new_doc), removed
