# Migrating from `lace.*` (Python) to `lace_rs` (Rust core)

Phase 6 of the Rust port (`docs/RUST_CXXQT_QML_PORT_PLAN.md`). The Python
implementation stays fully working through Phase 8; this table is for code
that wants the shared Rust core today — theme tooling, layout
import/export, headless validation — without any Qt dependency.

Install: `maturin develop -m rust/lace-py/Cargo.toml` (dev) or the
`lace-rs` wheel. `import lace_rs` for the friendly façade (dicts in/out),
`import _lace_rs` for the raw JSON-string boundary.

## API mapping

| Python (`lace.*`) | Rust (`lace_rs`) | Notes |
|---|---|---|
| `dock_theme.build_theme(THEME_SPECS[n])` | `build_theme(n)` | Identical tokens; category keys are lowercase strings, colours `[r,g,b,a]` lists. |
| `DOCK_THEMES[n]` | `build_theme(n)` | Same (the `"default"` entry is `BASE_DOCK_DEFAULTS`). |
| `sm.get_all(cat)` after `apply_theme` | `build_merged_theme(n)` | Schema defaults merged under the preset, like the manager holds them. |
| `theme_groups()` / `theme_choices()` | `theme_groups()` | Same order; `(label, key)` pairs. |
| `theme_models.load_theme_json(path)` | `load_theme_file(path)` | Same validation; hex + SVG names resolve like `QColor`. |
| `LayoutSerializer.serialize/deserialize` guards | `validate_layout(doc, version, available)` | Returns `{"warnings", "pruned", "doc"}`; raises on invalid. Never touches widgets. |
| `DockManager.save_state()` shape | `blank_layout(v)` + `dock_widget/move_*` ops | Build/modify documents headlessly; `validate_layout` checks them. |
| `DockManager.add_dock_widget(area, w)` | `dock_widget(doc, name, edge, target)` | `edge` in `left/right/top/bottom/center/float`; `target` is `(container, [path])` or `None`. Unknown edges raise `ValueError` (never aliased). |
| drop-controller centre/edge drops | `move_widget`, `move_container_center`, `drop_container_edge` | Solo containers tab in; multi-area container centres take the bottom-style fallback; `drop_edges(doc, ci)` reports the offered zones. |
| `toggle_view` closed flag | `set_closed` | Returns `(doc, found)`. |
| `pin_widget` / sidebar restore | `pin_widget` / `unpin_widget` | Roster entry kept while pinned. |
| floating save/restore | `float_widget` / `dock_floating` / `gc_empty_floats` | Fresh floats carry placeholder geometry blobs; QML uses the plain copy. |
| `LayoutError` + subclasses | same names from either module | `except LayoutError` guards transfer verbatim. |
| `pydantic.ValidationError` (themes) | `_lace_rs.ValidationError` | Not a `LayoutError`, like the original. |
| malformed theme JSON | `ValueError` | Approximates `json.JSONDecodeError` (its parent). |
| missing theme file | `FileNotFoundError` | Exact match. |

## Semantics that intentionally differ

- **Numbers keep int-ness.** `corner_radius: 10` stays `10`, `border_width: 1.5`
  stays `1.5`, round-tripping golden files byte-for-byte at the value level.
- **Colours are always 4-channel** in engine output; 3-channel JSON inputs
  gain opaque alpha (like `QColor(r, g, b)`).
- **Unknown SVG names resolve to black** (`[0, 0, 0, 255]`), mirroring what
  an invalid `QColor` reports — instead of raising.
- **`validate_layout` prunes unknown widgets** (with a warning) rather than
  failing; the pruned document comes back in the report.
- **Legacy layouts** (pre-schema, `QtAdvancedDockingSystem` tag) validate
  with one warning and normalize `schema` to `0` on re-save.
- **Applying a layout to live widgets** (`LayoutEngine`) and **QSS/palette
  painting** stay Python/Qt-side until cutover; `lace_rs` covers data only.

## What is NOT here (yet)

- **Hosting the Rust QML shell from Python** (`LaceQmlHost` as a live view)
  needs the `com.lace.dock` module as a *dynamic* QML plugin, which
  `cxx-qt-build` only lays out via CMake (explicitly discouraged with pure
  Cargo). Until packaging (Phase 8) wires that, embed the UI by launching
  the `dock_demo` binary, and drive Python-side Qt views with
  `build_merged_theme` data — see `demos/demo_rs_theme_panel.py`.
- **The stateful style manager** (signals, subscribers, `update()`) stays in
  `lace.dock_style_manager`; `build_merged_theme` is its read-only snapshot.
