# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


"""Export: a ThemeSpec as a JSON theme file or a Python literal, and a
token-by-token diff of two specs for reviews."""

import json
from dataclasses import fields
from pathlib import Path
from typing import Any, Dict, Optional, Union

from lace import color_science as cs
from lace.dock_theme import ThemeSpec, build_theme, deep_to_serializable
from lace.theme_kit.derive import to_rgba

#: Written even when they equal the default, so a file reads on its own.
_ALWAYS = ("base", "accent", "text")


def _is_colour_field(name: str, value: Any) -> bool:
    if value is None:
        return False
    try:
        from PySide6.QtGui import QColor
        if isinstance(value, QColor):
            return True
    except ImportError:  # pragma: no cover - PySide6 is a hard dependency
        pass
    return (isinstance(value, (list, tuple)) and len(value) in (3, 4)
            and all(isinstance(x, int) for x in value)
            and name != "content_margin")


def _changed(spec: ThemeSpec) -> Dict[str, Any]:
    """The fields ``spec`` sets away from the ThemeSpec default."""
    out = {}
    for f in fields(ThemeSpec):
        value = getattr(spec, f.name)
        if _is_colour_field(f.name, value):
            value = to_rgba(value)
        default = f.default
        if f.name in _ALWAYS or not _equal(value, default):
            out[f.name] = value
    return out


def _equal(a, b) -> bool:
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return list(a) == list(b)
    return a == b


def _json_colour(c):
    return "#%02x%02x%02x" % tuple(c[:3]) if len(c) < 4 or c[3] == 255 else list(c)


def to_dict(spec: ThemeSpec, name: Optional[str] = None) -> Dict[str, Any]:
    """The JSON form: only fields away from their default; opaque colours as
    ``"#rrggbb"``, translucent ones as ``[r, g, b, a]`` lists."""
    out: Dict[str, Any] = {"name": name} if name else {}
    for key, value in _changed(spec).items():
        if _is_colour_field(key, value):
            value = _json_colour(value)
        elif isinstance(value, tuple):
            value = list(value)
        out[key] = value
    return out


def to_json(spec: ThemeSpec, path: Union[str, Path, None] = None,
            name: Optional[str] = None) -> str:
    """Write ``spec`` as a JSON theme (loads with ``load_theme_json``) and
    return the text; with no ``path``, only return it."""
    text = json.dumps(to_dict(spec, name), indent=4) + "\n"
    if path is not None:
        Path(path).write_text(text, encoding="utf-8")
    return text


def to_python(spec: ThemeSpec, name: Optional[str] = None) -> str:
    """A ``ThemeSpec(...)`` literal; with ``name``, as a ``"name": ThemeSpec(...),``
    entry ready to paste into ``THEME_SPECS``."""
    items = _changed(spec)
    width = max(len(k) for k in items)
    pad = "        " if name else "    "
    body = "".join(f"{pad}{k:<{width}} = {v!r},\n" for k, v in items.items())
    if name:
        return f'    "{name}": ThemeSpec(\n{body}    ),'
    return f"ThemeSpec(\n{body})"


def diff(a: ThemeSpec, b: ThemeSpec) -> Dict[str, Optional[float]]:
    """Every built token that differs: ``"CATEGORY.key" -> ΔE`` (OKLab) for
    colours, None for anything else. Largest ΔE first."""
    ta = deep_to_serializable(build_theme(a))
    tb = deep_to_serializable(build_theme(b))
    out: Dict[str, Optional[float]] = {}
    for cat in sorted(set(ta) | set(tb), key=str):
        va, vb = ta.get(cat, {}), tb.get(cat, {})
        cname = getattr(cat, "name", str(cat))
        for key in sorted(set(va) | set(vb)):
            x, y = va.get(key), vb.get(key)
            if _equal(x, y):
                continue
            if _is_colour_field(key, x) and _is_colour_field(key, y):
                out[f"{cname}.{key}"] = round(cs.delta_e(x, y), 4)
            else:
                out[f"{cname}.{key}"] = None
    return dict(sorted(out.items(), key=lambda kv: -(kv[1] if kv[1] is not None else -1)))


__all__ = ["diff", "to_dict", "to_json", "to_python"]
