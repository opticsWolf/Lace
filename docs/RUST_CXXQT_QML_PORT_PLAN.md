# Lace → Rust + CXX-Qt + QtQuick Port — Implementation Plan (rev 2)

**Goal:** move Lace from Python/PySide6-QWidgets (`lace-dock 0.7.6`, ~19.8k LOC, 40 modules) to **Rust-first** with **CXX-Qt + QML/QtQuick** UI and **thin Python bindings via `maturin` (PyO3)**.
**Primary target:** Rust. Python stays a compat shim, never a second implementation.
**Rev 2 changes:** frameless-window research completed (§4) — custom chrome is now **deferred to Phase 7**, after the critical infrastructure (core crates, bridges, QML shell, DnD, floats, Python bindings) is green. Early phases run on native OS window frames.

Toolchain already staged in-repo: `uv` venv with `maturin 1.15 / PySide6 6.11.2 / pytest 9.1`.

---

## 1. Architecture: three layers, so 80% of logic never touches Qt

```
lace-core  (pure Rust, no Qt, no Python)    ← layout tree, theme math, serializer, enums, config
lace-qt    (Rust + CXX-Qt, Qt only)         ← QObject bridges; exposes lace-core to QML
qml/       (QML/QtQuick only)               ← visual chrome, DnD, sidebars, floats, theme singleton
lace-py    (Rust + PyO3, built by maturin)  ← thin Python wrapper over lace-core (+ QML host helper)
```

Why: every piece of Lace that is pure logic — theme derivation (1230 LOC), the 27 presets (1214 LOC), the layout tree and serializer (611 + state), `split_share()`, `allowed_areas_for()` — becomes unit-testable with `cargo test` alone, bindable to both QML and Python for free, and immune to Qt version churn. Qt-side code shrinks to model QObjects + QML.

---

## 2. Target workspace layout

```
Cargo.toml                  # workspace: lace-core, lace-qt, lace-py
rust/
  lace-core/                # pure Rust
    src/{lib,layout,theme,theme_presets,icons,config,persist,error}.rs
    tests/                  # ported theme/layout tests (Qt-free)
  lace-qt/                  # CXX-Qt bridges
    src/{lib,manager,container,area,widget,sidebar,overlay,theme_bridge,floating}.rs
    build.rs                # cxx-qt-build + qml_module (uri com.lace.dock 1.0)
    cmake/                  # optional QWindowKit integration (Phase 7 only)
  lace-py/                  # PyO3 / maturin
    src/lib.rs              # #[pymodule] _lace_rs
qml/
  qmldir  Main.qml  LaceTheme.qml  DockManager.qml  DockContainer.qml
  DockArea.qml  DockTabBar.qml  DockSplitter.qml  Sidebar.qml
  OverlayCross.qml  FloatingWindow.qml  TitleBar.qml  icons/
py/
  lace/                     # thin shim, keeps `import lace` working
  │  __init__.py            # re-exports _lace_rs + QML host helpers
  │  qml_host.py            # QQuickWidget wrapper for QWidget apps
  │  compat.py              # deprecation map: Python class → Rust/QML
pyproject.toml              # maturin build-backend, mixed rust/python layout
```

Commands (repo root, inside `uv` venv):

```bash
cargo test -p lace-core
cargo test -p lace-qt                       # needs Qt 6 dev + CXX-Qt
uv run maturin develop                      # builds _lace_rs into .venv
uv run pytest tests/                        # Python parity suite
```

MSRV: stable ≥1.77. Qt: **6.6.2+** (QWindowKit-recommended minimum; we also want Quick's newer fixes). CXX-Qt: track latest 0.7.x book. Drop Qt 5.15 — QML APIs diverged and QWK recommends 6.6.2+.

Feature flags keep Qt out of pure-core builds and Python out of pure-Qt builds:

```toml
[features] default = ["qt"]; qt = ["cxx-qt", "cxx-qt-lib"]; python = ["pyo3"]; frameless-qwk = []
```

---

## 3. Module migration map (Python → Rust/QML)

| Python module (LOC) | Rust / QML home | Notes |
|---|---|---|
| `enums.py` | `lace-core::config` (bitflags + serde) | Canonical enums; QML + Python both consume. |
| `dock_theme.py` (1230), `dock_custom_theme.py` (1214), `theme_models.py` | `lace-core::theme` + `theme_presets` | `ThemeSpec`, `build_theme()`, 27 presets, `ThemeJson` (serde + validation), HSL color math. Port exactly; parity-test every preset field-by-field. |
| `dock_style_manager.py` (326), `theme_manager.py` (315) | `lace-core::theme::manager` + `lace-qt::theme_bridge` | Core: `ThemeStore` (subscribers + generation counter, no Qt). Qt: `LaceTheme : QObject` with `Q_PROPERTY`s + OS dark/light notifier. QML `LaceTheme.qml` singleton binds it. |
| `dock_container_state.py`, `layout_serializer.py` (611) | `lace-core::layout` + `::persist` | Serde tree `Container{Splitter{Area{widgets}}}`, save/restore, atomic I/O (temp+rename), perspectives. Must read 0.7.x JSON byte-for-byte; version field; refuse newer majors with a `RestoreFailure` equivalent. |
| `dock_manager.py` (843, facade) | `lace-qt::manager` (`LaceManager : QObject`) | `add/remove/find`, `save/restore`, `openPerspective`, `setTheme`, `registerFloating`, view-menu model. Same method names → QML `Q_INVOKABLE`s, Python calls the same via PyO3. |
| `dock_container_widget.py` (1082), `dock_splitter.py` (395) | `DockContainer.qml` + `DockSplitter.qml` + `lace-qt::container` | Nested `SplitView`s driven by Rust model. `split_share()` = pure fn in core. Maximize = saved `SplitView` sizes in Rust — never hidden widgets (this structurally fixes v0.7 Phase-4 defect class). |
| `dock_area_widget.py` (529), `dock_area_layout.py`, `dock_area_tab_bar.py` (400), `dock_area_title_bar.py` (716), `dock_widget_tab.py` (863), `dock_widget.py` (657) | `DockArea.qml` + `DockTabBar.qml` + `lace-qt::area`/`widget` | `DockArea`/`DockWidget` QObjects: tab list model, current index, features, `reorder()`. Tab chrome = QML `TabButton` + `Shape` (port `tab_path()`); icon tint via `ColorOverlay` with `(name,color,size,dpr,generation)` cache key (v0.7 Phase-6 fix baked in). |
| `dock_overlay.py` (436), `dock_chrome.py` DragDetector | `OverlayCross.qml` + `lace-qt::overlay` | `allowed_areas_for()` pure Rust (v0.7 Phase-2 extraction), `DropArea`s per edge + center, `Drag` attached property for previews. No `QPixmap` drop icons. |
| `floating_behaviour.py` (749), `floating_dock_container*.py` (440+1031) | `FloatingWindow.qml` + `lace-qt::floating` | **One** QML `Window` replaces both native + frameless variants + the 750-LOC mixin. Drag lifecycle = Rust state machine (`Idle/Dragging/Dropping`), geometry via Qt. No swallowed-release discrimination, no `id(splitter)` keys. |
| `sidebar_manager.py` (965), `sidebar_container.py` (792), `sidebar_tab*.py` (635+466), `sidebar_title_bar.py` (423) | `Sidebar.qml` + `lace-qt::sidebar` | `Drawer`-style overlay per edge; rotated `TabButton` + badge; `flat_edge/radius/border_closed` tokens → `Shape`. Pin/unpin = model move, not widget reparent. Escape-gating (0.7.6 fix) re-ported as QML `Shortcut` on overlay visibility. |
| `dock_paint.py` (513) | QML `Shape`/`Rectangle` + `lace-core::theme::geometry` | `tab_path/top_rounded/bottom_rounded/chrome_content_margin` → QML path helpers + geometry tokens; one Rust `geometry()` fn so QML + Python agree on margins. |
| `dock_icon_provider.py` (298), `resources/lace_icons/*.svg` | `lace-core::icons` + QML | Icon key → SVG path + tint + size + DPR; QML renders+tints; cache key includes generation. SVGs ship as Qt resources. |
| `dock_menu*.py` (468), `eliding_label.py` | QML `Menu` + `Text.elide` | Context menus bound to `MenuActionTarget` model. |
| `frameless_window.py` (700), `frameless_titlebar.py` (318), `floating_dock_container_frameless.py` (1031), `qframelesswindow` dep | **Deferred to Phase 7** — see §4 | Tier 0/1/2 frameless strategy. None of this blocks the critical path. |
| `dock_signals.py`, `dock_styled.py`, `dock_theme_bridge.py`, `util.py`, `_trace.py` | Deleted / folded | Event bus → Qt signals on QObjects; palette bridge → gone (QML binds theme); trace → `tracing` + `RUST_LOG`. |
| `demos/` (3 files) | `examples/qml_minimal` + `py/demos/demo_qml.py` | Rust/QML demo canonical; Python demo hosts same QML. |
| `tests/` (8.7k), `dev_smoke/` | cargo tests + `tests/test_rs_parity.py` + QML `TestCase` | See §6. |

**Not ported** (deleted by design): `qframelesswindow`, QSS/stylesheet path (replaced by QML theme JSON + component overrides), `WA_WState_ExplicitShowHide` workarounds, DWM dark-frame code (QWK `dark-mode` attribute does it), `WinIdChange` auto-heal (Quick owns the surface).

---

## 4. Frameless windows — research results & strategy (Phase 7 scope, deliberately last)

### 4.1 Options surveyed (Sep 2026)

| Option | Platform | Quick/QML support | Windows Snap Layout | Dark mode / Mica / DWM attrs | Verdict |
|---|---|---|---|---|---|
| **`qframelesswindow` (zhiyiYo/PyQt-Frameless-Window)** | Win/mac/Linux | ✗ (widgets only; Python) | ✅ via `WM_NCHITTEST` in `nativeEvent` | partial | **Not portable**: Python-only, QWidget-based. Its techniques are what we replace, not bring. |
| **`framelesshelper` (wangwenx190)** | Win/mac/Linux | ✅ | ✅ | ✅ | **Moved** — repo redirects to QWindowKit. Do not adopt. |
| **`QWindowKit` (stdware/qwindowkit)** — successor of the above | Win/mac/Linux, Qt ≥5.12, recommends **6.6.2+** | ✅ dedicated `QWindowKit::Quick` module: `QWK::registerTypes(&engine)`, QML `WindowAgent { setup(window); setTitleBar(bar) }` | ✅ `setSystemButton(Window/Minimize/Maximize/Close, item)` restores Snap Layout | ✅ `setWindowAttribute("dark-mode"/"mica"/"mica-alt"/"acrylic-material"/"dwm-blur"/"dwm-border-color")` | **Chosen (Tier 2).** MIT, CMake install, uses Qt private APIs → pin Qt version. Replaces qframelesswindow *and* Lace's hand-rolled DWM dark-frame code in one dependency. |
| **Pure Qt: `FramelessWindowHint` + `startSystemMove()` / `startSystemResize(edges)`** (Qt 5.15+ blog: "custom client-side window decorations") | all | ✅ callable from QML on `Window` | ⚠ **QTBUG-84466: no Aero Snap on frameless Windows windows** (open as of 2024-06) | ✗ | **Chosen (Tier 1)** interim: zero deps, cross-platform native move/resize loops; accept missing Snap/shadows until Phase 7. |
| **KDDockWidgets (KDAB)** | all | ✅ QtQuick backend | — | — | Rejected as dependency: GPL/commercial (Lace is Apache-2.0), no Rust bindings, and it *is* a docking framework — we'd be rewriting Lace on top of another one. Its QML theme/styling source remains useful reference reading. |

### 4.2 Tiered strategy

* **Tier 0 — native frames (Phases 0–6, the whole critical path).** Floating containers are plain `Window`s with the OS title bar. Everything else (docking, DnD, sidebars, themes) works. `FramelessMode` is a Rust enum, not an assumption.
* **Tier 1 — pure-Qt frameless (Phase 7a).** `Window { flags: Qt.FramelessWindowHint | Qt.WindowMinMaxButtonsHint }` + shared `TitleBar.qml` (drag via `startSystemMove()`, edges via `startSystemResize(edges)`, double-click maximize synchronous via `showMaximized()/showNormal()` — same lesson as Lace 0.5.x). Works everywhere; no Snap Layouts on Windows, self-drawn shadow (or none).
* **Tier 2 — QWindowKit Quick (Phase 7b, Windows-first).** Vendor QWK via CMake (`QWINDOWKIT_BUILD_QUICK=ON`), drive `qt-build-utils`/corrosion link step; QML registers `import QWindowKit`; `FloatingWindow.qml`/main window attach `WindowAgent`, set title bar + system buttons, set `dark-mode` from the theme's `is_light` (replaces `_apply_dwm_dark_frame`). Behind cargo feature `frameless-qwk`; if QWK is absent at build time we degrade to Tier 1 automatically. CXX-Qt never bridges QWK directly — QWK is used from QML + a ~20-line C++ shim for `registerTypes`, keeping the Rust/Qt boundary clean.
* Custom title bars as *components*: the `title_bar=` descriptor concept becomes `titleBar: Component { ... }` on `FloatingWindow.qml` / `Main.qml`. `LaceStandardTitleBar`'s drag-veto list (menu/buttons/line-edits) maps to `WindowAgent.setHitTestVisible()` at Tier 2 and to child `TapHandler` gesture-acceptance at Tier 1.

### 4.3 Why this ordering is safe

Frameless chrome touches zero core logic: drag state machine, drop overlays, layout tree, themes, and serialization are chrome-agnostic. Every v0.7 frameless bug class (double-click maximize swallowing, DWM dark frame loss after `setWindowFlags`, `WinIdChange` heal for GL children) exists because of native-handle poking that Tier 0/1 simply never does; Tier 2 reintroduces hit-test handling inside a maintained C++ library instead of our Python. Deferring QWK also de-risks CI: no submodule/CMake extra until the day it's needed.

---

## 5. CXX-Qt bridge sketch

```rust
// rust/lace-qt/src/manager.rs
#[cxx_qt::bridge(namespace = "lace")]
mod ffi {
    extern "RustQt" {
        #[qobject]
        #[qml_element]
        #[qproperty(QObject*, rootContainer)]
        #[qproperty(QString, currentTheme)]
        type LaceManager = super::LaceManagerRust;

        #[qinvokable]
        fn add_dock_widget(self: Pin<&mut Self>, area: i32, widget_id: QString, index: i32) -> bool;
        #[qinvokable]
        fn save_state(self: &Self) -> QString;       // serde JSON from lace-core
        #[qinvokable]
        fn restore_state(self: Pin<&mut Self>, json: QString) -> bool;
        #[qinvokable]
        fn set_theme(self: Pin<&mut Self>, name: QString);
        #[qsignal]
        fn layout_changed(self: Pin<&mut Self>);
        #[qsignal]
        fn theme_changed(self: Pin<&mut Self>, name: QString);
    }
}
```

```rust
// rust/lace-core/src/layout.rs — pure, Qt-free, PyO3-friendly
#[derive(Serialize, Deserialize, Clone)]
pub struct LayoutTree { pub root: ContainerNode, pub version: u32 }
pub fn split_share(target: u32, handle: u32, n: usize) -> u32 { /* (t - h*(n-1)) / n */ }
pub fn allowed_areas_for(visible_areas: usize, maximized: bool) -> DockAreas { /* v0.7 Phase-2+3 rules */ }
```

```qml
// qml/Main.qml
import QtQuick; import QtQuick.Controls; import com.lace.dock 1.0
ApplicationWindow {
  LaceManager { id: manager }
  DockContainer { anchors.fill: parent; model: manager.rootContainer }
  // Phase 7: FloatingWindow instances per floating-container model
}
```

QML module via `cxx_qt_build::QmlModule { uri: "com.lace.dock" }` in `build.rs` (book flow: QObjects in Rust → QML GUI → Cargo executable → CMake integration).

---

## 6. Python thin bindings (maturin + PyO3)

```toml
[build-system] requires = ["maturin>=1.0"], build-backend = "maturin"
[tool.maturin] module-name = "_lace_rs", bindings = "pyo3", features = ["pyo3/extension-module"]
```

```rust
#[pymodule] fn _lace_rs(m) { m.add_class::<PyThemeSpec>()?; m.add_class::<PyLayoutTree>()?;
  m.add_function(wrap_pyfunction!(load_layout))??; ... }   // wrappers over lace-core ONLY
```

```python
# py/lace/__init__.py — compat shim
from ._lace_rs import ThemeSpec, LayoutTree, load_layout, save_layout, __version__
from .qml_host import LaceQmlHost      # QQuickWidget hosting qml/Main.qml
from .compat import DockManager        # old method names → _lace_rs + host
```

Two documented modes: **A. Embedded** (PySide6 `QMainWindow` + `LaceQmlHost` central widget; user `QWidget`s hosted inside QML dock areas — migration default), **B. Pure QML** (Python just launches `QQmlApplicationEngine`).

**Linkage rule (critical):** `lace-qt` and `lace-py` are separate crates sharing `lace-core`; `lace-py` never links Qt. CXX-Qt and PyO3 in one `.so` fight over linkage — never merge them. Python reaches QML at runtime through PySide6.

---

## 7. Testing strategy

| Layer | Runner | What |
|---|---|---|
| `lace-core` | `cargo test` | All 27 presets parity (ported `test_theme_*` expectations as fixtures), `split_share`, `allowed_areas_for`, serializer roundtrips, atomic I/O, perspectives. v0.7 phase tests (`area_insertion`, `centre_drop`, `maximize_drop`, `splitter_handle_cache`) ported Qt-free. |
| `lace-qt` | `cargo test` + offscreen Qt | Property/signal behavior, save→restore→save stability, floating lifecycle. |
| QML | Qt `TestCase`, `QT_QPA_PLATFORM=offscreen` | Tab append order, centre-drop tabs-vs-splits, maximize sizes, sidebar open/close, overlay allowed areas. |
| Python parity | `pytest tests/test_rs_parity.py` | Golden files: every 0.7.6 layout/theme JSON loaded in old Python and `_lace_rs` → identical output. Existing `tests/` run against the shim until cutover. |
| Frameless (Phase 7) | `dev_smoke_qml/frameless/` | Tier 1 vs Tier 2 matrix: drag, edge resize, double-click maximize (synchronous), Snap Layout presence (Win, Tier 2), `dark-mode` attr applied on theme switch, GL child (`WebEngineView`) smoke. |

Rule carried from v0.7 plan: **every phase adds a test that fails before and passes after.**

---

## 8. Phased delivery — frameless last, infrastructure first

**Phase 0 — Workspace + toolchain + hello (0.5–1 wk).**
Cargo workspace, three crates, `py/` shim, maturin wired; CI matrix (win/linux × cargo + maturin + pytest); `examples/qml_minimal` (one `DockWidget`-style QObject in QML via `QQmlApplicationEngine`); `maturin develop` + `import _lace_rs` green. Exit: all three runners green on Windows.

**Phase 1 — `lace-core::theme` + `::config` (1–2 wks).**
`enums.py` → bitflags; theme engine + presets + `ThemeJson`. Parity harness: 27 themes × focused/unfocused vs Python `build_theme()`. Exit: zero Qt dependency, cargo tests green.

**Phase 2 — `lace-core::layout` + `::persist` (1–2 wks).**
Serializer tree, `split_share`, insertion post-conditions, cache-invalidation semantics as pure fns; atomic write; perspectives. Golden roundtrips against 0.7.6 JSONs. Exit: layout save/restore Qt-free.

**Phase 3 — `lace-qt` bridges + QML shell, native frames (2–3 wks).**
`LaceManager/DockContainer/DockArea/DockWidget` QObjects; `Main/DockManager/DockContainer/DockArea` QML with `SplitView` + `TabBar`; **floating containers = plain OS-framed `Window`s (Tier 0)** so the DnD path is exercised end-to-end early. Include one `QWidget` hosted via `QQuickWidget`/`WidgetHost` (prove with `QTextEdit` + `QWebEngineView` now, not Phase 6). Exit: demo docks/tabs/splits/floats.

**Phase 4 — QML chrome parity (2–3 wks).**
Tab/area chrome, sidebar, overlay cross, `LaceTheme` singleton, icons + tint cache, geometry tokens from `dock_paint`. Re-shoot theme screenshots. Exit: 27 themes render; visual diff accepted. Still Tier 0 frames.

**Phase 5 — DnD + focus + maximize + floats (2 wks).**
`allowed_areas_for` → `DropArea`s, `Drag` lifecycle state machine, focus-coordinated borders, maximize via saved sizes, sidebar badges/focus modes, Escape-gating. Port v0.7 drop-path tests to QML. Exit: float→drag→dock roundtrip green.

**Phase 6 — `lace-py` bindings + compat (1–2 wks).**
`_lace_rs` over `lace-core`; `py/lace` shim + `LaceQmlHost`; `test_rs_parity.py`; embedded + pure-QML demos; migration table. Exit: `uv run pytest` green over Rust core; Python API compat documented.

**Phase 7 — Frameless windows (2–3 wks) ← deferred, per §4.**
7a: Tier 1 pure-Qt frameless (`TitleBar.qml`, `startSystemMove/Resize`, synchronous maximize) behind `FramelessMode.QmlFrameless`. 7b: Tier 2 QWindowKit Quick behind `frameless-qwk` (CMake vendor, `WindowAgent`, system buttons for Snap, `dark-mode` attr wired to theme). Fallback chain automatic. Full smoke matrix of §7 row 5. Exit: frameless parity with 0.7.6 custom-title-bar feature set; DWM dark frame reproduced via QWK attrs; screenshots re-shot.

**Phase 8 — Cutover + release (1 wk).**
`1.0.0-alpha`; `CHANGELOG` records QWidget removal + JSON compat; `docs/MIGRATION_0x_TO_1x.md`; publish `lace-rs` crate + `_lace_rs` wheel; archive Python impl behind `LEGACY_QWIDGETS`, then remove. Exit: Rust demo + Python demo + all tests green; screenshots refreshed.

Total: **~10–16 weeks** single-track. 1+2 parallel; 3→4→5 ordered (same QML files); 6 independent of 7; 7 after 4 (needs theme attrs) and before 8.

---

## 9. Risks & mitigations

| Risk | Mitigation |
|---|---|
| CXX-Qt + PyO3 linkage | Separate crates sharing `lace-core`; never one `.so`. |
| QWidget content inside Quick | `QQuickWidget`/`WidgetHost` proven in Phase 3 with `QWebEngineView`, not Phase 6. |
| Frameless regressions (0.7's bug family) | Tier 0 avoids native-handle poking entirely; Tier 2 pushes hit-test into maintained QWK; feature-flagged fallback chain. |
| QWK + Qt private APIs | Pin Qt 6.6.2–6.8 in CI; cargo feature off by default; degrade to Tier 1. |
| QML theming drift vs 27 presets | QML only binds `ThemeStore`; parity gates Phase 4 exit. |
| Layout JSON break | Version field + golden files; refuse newer majors. |
| CXX-Qt/Qt drift | Pin versions; test 6.6 LTS-ish + latest. |
| Team knows Python not Rust/QML | `import lace` alive through Phase 8; Rust API mirrors Python names; migration doc with side-by-side snippets. |

---

## 10. Immediate next actions (if approved)

1. Scaffold workspace; `lace-core` with `enums` + `split_share()` + test (proves toolchain).
2. Copy `tests/test_theme_*.py` expectations → `lace-core/tests/fixtures/` (parity oracle).
3. Minimal CXX-Qt `LaceManager` + `Main.qml` hello, offscreen CI.
4. Decide names: crate `lace-rs` / wheel `_lace_rs` / QML uri `com.lace.dock`.
5. **No QWK/qframelesswindow decisions needed until Phase 7** — record §4 as the decision log; revisit QWK's Qt-version matrix at that time.

---

*Companion reading: `docs/ARCHITECTURE.md`, `docs/IMPROVEMENT_PLAN_v0.7.md` (pure-logic fixes to bake in), CXX-Qt book Ch.2, stdware/qwindowkit README (Quick module), qt.io blog "Custom client-side window decorations", QTBUG-84466.*
