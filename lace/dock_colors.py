# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0

dock_colors — Canonical colour conversion for the docking system
================================================================

Single source of truth for turning theme tokens into ``QColor`` and back.
Every module (style manager, palette bridge, widgets) imports ``to_qcolor``
from here so there is exactly one parsing implementation.

Storage model
-------------
The :class:`DockStyleManager` stores colours natively as ``QColor`` (converted
once on write via :func:`deep_to_qcolor`).  Serialization back to JSON-safe
``[r, g, b, a]`` lists happens only at theme export boundaries via
:func:`deep_to_serializable`.
"""

from typing import Any, List

from PySide6.QtGui import QColor


def to_qcolor(val: Any) -> QColor:
    """Canonical converter: ``QColor`` | ``'#hex'`` / colour name | ``[r,g,b(,a)]`` -> ``QColor``."""
    if isinstance(val, QColor):
        return QColor(val)
    if isinstance(val, str):
        return QColor(val)  # handles '#rgb', '#rrggbb', '#aarrggbb', SVG names
    if isinstance(val, (list, tuple)) and len(val) >= 3:
        return QColor(
            int(val[0]), int(val[1]), int(val[2]),
            int(val[3]) if len(val) > 3 else 255,
        )
    return QColor(0, 0, 0)


def qcolor_to_list(c: QColor) -> List[int]:
    """Inverse of :func:`to_qcolor` for the list form (JSON-safe)."""
    return [c.red(), c.green(), c.blue(), c.alpha()]


def is_color_list(val: Any) -> bool:
    """True for a 3- or 4-element list/tuple of numbers (an ``[r,g,b(,a)]`` colour)."""
    return (
        isinstance(val, (list, tuple))
        and 3 <= len(val) <= 4
        and all(isinstance(c, (int, float)) for c in val)
    )


def deep_to_qcolor(value: Any) -> Any:
    """Recursively convert colour lists / hex strings to ``QColor``.

    Non-colour scalars (ints for geometry, strings for fonts, bools) pass
    through unchanged.  Used when writing values into the style schemas.
    """
    if isinstance(value, QColor):
        return value
    if is_color_list(value):
        return to_qcolor(value)
    # Hex strings are colours; other strings (font families, enum-ish tokens
    # like "normal"/"bottom") must pass through untouched.
    if isinstance(value, str):
        return to_qcolor(value) if value.startswith("#") else value
    if isinstance(value, dict):
        return {k: deep_to_qcolor(v) for k, v in value.items()}
    if isinstance(value, list):
        return [deep_to_qcolor(v) for v in value]
    return value


def deep_to_serializable(value: Any) -> Any:
    """Recursively convert ``QColor`` back to JSON-safe ``[r,g,b,a]`` lists.

    Used only at export boundaries (e.g. writing a theme to disk); the
    in-memory schemas keep ``QColor`` instances.
    """
    if isinstance(value, QColor):
        return qcolor_to_list(value)
    if isinstance(value, dict):
        return {k: deep_to_serializable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [deep_to_serializable(v) for v in value]
    return value
