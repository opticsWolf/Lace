#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Emit `src/presets_generated.rs` from `lace/dock_custom_theme.py`.

Reads the 26 shipped `ThemeSpec`s plus `THEME_GROUPS` and writes them as Rust
literals, so the presets can never drift from Python by transcription. Fails
loudly on any unclassified field, colour, or value shape.

Usage (from repo root):
    .venv/Scripts/python.exe rust/lace-core/codegen/emit_presets.py
"""

import dataclasses
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from lace.dock_custom_theme import THEME_SPECS, THEME_GROUPS  # noqa: E402
from lace.dock_theme import ThemeSpec  # noqa: E402

OUT = REPO / "rust" / "lace-core" / "src" / "presets_generated.rs"

COLOR_FIELDS = {
    "base", "accent", "text", "surface", "title_bg", "border",
    "focus_border_color", "success_color", "warning_color", "error_color",
    "info_color", "title_border_color", "title_border_focus_color",
    "tab_border_color", "tab_border_active_color", "tab_border_unfocused_color",
    "sidebar_tab_bg_normal", "sidebar_tab_bg_hover_start",
    "sidebar_tab_bg_hover_end", "sidebar_tab_bg_active",
    "sidebar_tab_border_color", "sidebar_tab_border_active_color",
    "sidebar_tab_border_hover_color", "tooltip_bg", "tooltip_text",
}
BOOL_FIELDS = {
    "is_light", "border_below_title", "tab_dimming", "sidebar_tab_border_closed",
}
STR_FIELDS = {
    "title_mode", "hover_mode", "sidebar_tab_flat_edge",
    "sidebar_indicator_position",
}
NUM_FIELDS = {
    "corner_radius", "border_width", "title_height", "title_padding_left",
    "title_padding_right", "title_button_spacing", "title_margin",
    "title_border_width", "title_border_bottom", "tab_radius", "tab_margin",
    "tab_border_width", "indicator_width", "sidebar_tab_radius",
    "sidebar_tab_border_width", "sidebar_indicator_width",
}
SPECIAL_FIELDS = {"content_margin", "indicator_position"}

_ALL = COLOR_FIELDS | BOOL_FIELDS | STR_FIELDS | NUM_FIELDS | SPECIAL_FIELDS
_DECLARED = {f.name for f in dataclasses.fields(ThemeSpec)}
assert _ALL == _DECLARED, f"emitter field classification drifted: {_ALL ^ _DECLARED}"


def rust_str(s: str) -> str:
    assert '"' not in s and '\\' not in s, f"unescapable string: {s!r}"
    return f'"{s}"'


def rust_color(value) -> str:
    assert isinstance(value, (list, tuple)) and len(value) == 4, \
        f"preset colour must be [r,g,b,a], got {value!r}"
    assert all(isinstance(c, int) and 0 <= c <= 255 for c in value), \
        f"bad channels: {value!r}"
    r, g, b, a = value
    return f"Rgba::new({r}, {g}, {b}, {a})"


def rust_num(value) -> str:
    if isinstance(value, bool):
        raise TypeError(f"bool is not numeric: {value!r}")
    if isinstance(value, int):
        return f"Num::Int({value})"
    if isinstance(value, float):
        return f"Num::Float({value!r})"
    raise TypeError(f"not numeric: {value!r}")


def rust_margin(value) -> str:
    if isinstance(value, bool):
        raise TypeError(f"bool is not a margin: {value!r}")
    if isinstance(value, (int, float)):
        return f"MarginSpec::Scalar({rust_num(value)})"
    if isinstance(value, (list, tuple)):
        items = ", ".join(rust_num(v) for v in value)
        return f"MarginSpec::List(vec![{items}])"
    raise TypeError(f"not a margin: {value!r}")


def emit_field(name: str, value) -> str:
    """Render one set field as `name: <expr>,` (required) or `name: Some(...),`."""
    if name in COLOR_FIELDS:
        expr: str = rust_color(value)
    elif name in BOOL_FIELDS:
        assert isinstance(value, bool), f"{name} must be bool, got {value!r}"
        expr = "true" if value else "false"
    elif name in STR_FIELDS:
        assert isinstance(value, str), f"{name} must be str, got {value!r}"
        expr = f"{rust_str(value)}.to_string()"
    elif name in NUM_FIELDS:
        expr = rust_num(value)
    elif name == "content_margin":
        expr = rust_margin(value)
    elif name == "indicator_position":
        if isinstance(value, str):
            expr = f"IndicatorPosition::Single({rust_str(value)}.to_string())"
        else:
            assert isinstance(value, (list, tuple)) and all(
                isinstance(v, str) for v in value), f"bad indicator_position: {value!r}"
            items = ", ".join(f"{rust_str(v)}.to_string()" for v in value)
            expr = f"IndicatorPosition::Multiple(vec![{items}])"
    else:  # pragma: no cover - guarded by the classification assert
        raise AssertionError(f"unclassified field: {name}")
    if name in ("base", "accent", "text", "is_light", "title_mode",
                "hover_mode", "tab_dimming"):
        return f"        {name}: {expr},"
    return f"        {name}: Some({expr}),"


def emit_spec(name: str, spec: ThemeSpec) -> str:
    lines = [f'    ("{name}", ThemeSpec {{']
    for f in dataclasses.fields(ThemeSpec):
        value = getattr(spec, f.name)
        if value == f.default:
            continue
        if value is None:
            continue
        lines.append(emit_field(f.name, value))
    lines.append("        ..ThemeSpec::default()")
    lines.append("    }),")
    return "\n".join(lines)


def main() -> None:
    specs = "\n".join(emit_spec(name, spec) for name, spec in THEME_SPECS.items())
    groups = ",\n".join(
        f'    ("{title}", &[{", ".join(rust_str(k) for k in keys)}])'
        for title, keys in THEME_GROUPS.items()
    )
    names = ", ".join(f'"{n}"' for n in ["default", *THEME_SPECS])
    OUT.write_text(
        "//! GENERATED by `codegen/emit_presets.py` — do not edit.\n"
        "//! The 26 shipped presets plus `THEME_GROUPS`, transcribed from\n"
        "//! `lace/dock_custom_theme.py` by construction.\n\n"
        "use super::theme::{IndicatorPosition, MarginSpec, Num, Rgba, ThemeSpec};\n\n"
        "/// The stock look's seed: `BASE_DOCK_DEFAULTS`' spec from\n"
        "/// `lace/dock_theme.py`. Pinned by the `default` golden file.\n"
        "pub fn default_spec() -> ThemeSpec {\n"
        "    ThemeSpec {\n"
        "        base: Rgba::new(24, 24, 24, 255),\n"
        "        accent: Rgba::new(0, 120, 212, 255),\n"
        "        text: Rgba::new(204, 204, 204, 255),\n"
        "        surface: Some(Rgba::new(31, 31, 31, 255)),\n"
        "        border: Some(Rgba::new(24, 24, 24, 0)),\n"
        '        title_mode: "lighter".to_string(),\n'
        '        hover_mode: "lighter".to_string(),\n'
        "        corner_radius: Some(Num::Int(4)),\n"
        "        tab_radius: Some(Num::Int(4)),\n"
        "        border_width: Some(Num::Float(1.5)),\n"
        "        title_margin: Some(Num::Float(0.0)),\n"
        "        content_margin: Some(MarginSpec::Scalar(Num::Float(0.0))),\n"
        "        ..ThemeSpec::default()\n"
        "    }\n"
        "}\n\n"
        "/// All preset keys in menu order: `\"default\"` first, then the\n"
        "/// 26 specs in `THEME_SPECS` file order.\n"
        "pub fn preset_keys() -> Vec<&'static str> {\n"
        f"    vec![{names}]\n"
        "}\n\n"
        "/// `(name, spec)` for the 26 shipped presets, in file order.\n"
        "pub fn preset_specs() -> Vec<(&'static str, ThemeSpec)> {\n"
        "    vec![\n"
        f"{specs}\n"
        "    ]\n"
        "}\n\n"
        "/// `(group title, preset keys)` in presentation order.\n"
        "pub const THEME_GROUP_ORDER: &[(&str, &[&str])] = &[\n"
        f"{groups},\n"
        "];\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT} ({len(THEME_SPECS)} presets)")


if __name__ == "__main__":
    main()
