# Rust workspace (`lace-core` / `lace-qt` / `lace-py`)

Port plan: `docs/RUST_CXXQT_QML_PORT_PLAN.md`.

## Prerequisites (Windows)

- Rust stable (MSVC) + Visual Studio C++ tools — `cargo build` must link.
- CMake + Ninja: `uv pip install cmake ninja` (done in `.venv`).
- Qt 6.8.3 `msvc2022_64` via aqtinstall (outside the repo, no admin needed):
  ```powershell
  .\.venv\Scripts\python.exe -m aqt install-qt windows desktop 6.8.3 `
      win64_msvc2022_64 -O C:\Users\Main\Qt `
      --archives qtbase qtdeclarative qtshadertools qtsvg qtimageformats
  ```
- Tell CXX-Qt where Qt is (per shell, or set persistently):
  ```powershell
  $env:QMAKE = "C:\Users\Main\Qt\6.8.3\msvc2022_64\bin\qmake.exe"
  ```
  (Git Bash: `export QMAKE=/c/Users/Main/Qt/6.8.3/msvc2022_64/bin/qmake.exe`)
- Put the Qt DLLs on `PATH` for *running* anything Qt-linked
  (`cargo run`, `cargo test`, the smoke check):
  ```powershell
  $env:PATH = "C:\Users\Main\Qt\6.8.3\msvc2022_64\bin;$env:PATH"
  ```

## Commands (repo root)

```bash
cargo test -p lace-core                                  # pure-Rust suite, no Qt
QMAKE=... cargo build -p lace-qt                         # bridges + QML module
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
  cargo run -p lace-qt --bin qml_minimal -- --smoke      # headless QML hello
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
  cargo run -p lace-qt --bin dock_demo -- --smoke        # Tier-0 dock shell
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
  cargo run -p lace-qt --bin widget_host -- --smoke      # QWidget beside QML
./.venv/Scripts/maturin develop -m rust/lace-py/Cargo.toml  # build _lace_rs into .venv
./.venv/Scripts/python.exe -c "import _lace_rs; print(_lace_rs.split_share(900, 6, 2))"
```

`dock_demo` also honors `LACE_QML_FILE=<path>` (iterate on `qml/Shell.qml`
without rebuilding). Its `--smoke` is a real self-test — seed, add-tab,
remove-tab with an exit-code verdict — because QML `console.log` is not
captured reliably on every platform.

> **QML iteration rule:** `cxx-qt-build` does not re-embed changed QML
> files on incremental builds (no `rcc`/`qmlcachegen` rerun — verified).
> After editing anything under `rust/lace-qt/qml/`, run
> `cargo clean -p lace-qt` before trusting a smoke run, or stale UI passes
> silently. `LACE_QML_FILE` bypasses resources for the top file during
> iteration. Related: QML properties keep their Rust `snake_case` names
> unless the bridge sets `cxx_name` (all multi-word `LaceManager`
> properties carry one) — `manager.layoutJson` is `undefined` otherwise,
> with no error anywhere.

## Shell architecture (Phase 3)

Rust owns a `LayoutDoc`; QML renders the `LaceManager.layoutJson` snapshot
(`Shell/DockManagerView/ContainerBuilder/SplitterView/AreaView/WidgetCard`,
floating containers as plain `Window`s in `FloatingView`). Structural ops
re-emit `layoutJsonChanged` (full rebuild); `setCurrentTab` only syncs the
document silently so tab-local state (typed text) survives switches.

Two hard-won rules live here:

- No QML import cycles: `ContainerBuilder` creates `FloatingView`s, so a
  `FloatingView` must never statically contain a `ContainerBuilder` (the
  loader deadlocks with no error). It receives the builder as a property.
- Build-script `-l` directives only reach targets with a dependency edge to
  the lib: bins that merely `use cxx_qt_lib` miss them. Raw
  `rustc-link-arg` paths (used for the widget-host Qt libs) reach every bin
  unconditionally — same reason the `/WHOLEARCHIVE` args below work.

> **Windows/MSVC linking note:** MSVC discards unreferenced static-archive
> members (`/OPT:REF`), which would drop the static QML plugin, the type
> registrations and the QML resources. `rust/lace-qt/build.rs` therefore
> re-links every cxx-qt-build archive with `/WHOLEARCHIVE` (raw
> `rustc-link-arg`, MSVC only in effect for bins/examples/tests). The
> `links = "lace-qt"` key mirrors upstream `cxx-qt`/`cxx-qt-lib`.

CI (`.github/workflows/rust-port.yml`) runs the same matrix on
windows-latest + ubuntu-latest with Qt installed via `install-qt-action`.
