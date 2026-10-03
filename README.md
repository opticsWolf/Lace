# Lace

**Advanced docking system for PySide6** — a feature-rich, themeable widget layout framework for building professional Qt desktop applications in Python.

**Version:** 0.9.5

[![PyPI](https://img.shields.io/pypi/v/lace-dock.svg)](https://pypi.org/project/lace-dock/)
[![License](https://img.shields.io/pypi/l/lace-dock.svg)](https://pypi.org/project/lace-dock/)
[![Tests & Publish](https://github.com/opticsWolf/Lace/actions/workflows/publish.yml/badge.svg)](https://github.com/opticsWolf/Lace/actions/workflows/publish.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![Framework](https://img.shields.io/badge/framework-PySide6%20%2F%20Qt6-purple)](https://pypi.org/project/PySide6/)
[![Website](https://img.shields.io/badge/website-opticswolf.github.io%2FLace-ff3d9a)](https://opticswolf.github.io/Lace/)

---

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Screenshots](#screenshots)
- [Architecture Overview](#architecture-overview)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

---

## Features

### ⚓ Docking & Layout

- **Multi-area docking** — Dock widgets to left, right, top, bottom, or center regions within a window
- **Tabbed dock areas** — Multiple widgets share a single dock area as tabs, with full tab management (reorder, close, float)
- **Floating windows** — Detach any dock widget into its own top-level window; drag it back to dock
- **Drag-and-drop layout** — Intuitive resize, re-order, and re-dock via visual drop indicators
- **Nested splitters** — Arbitrary nesting of horizontal and vertical split panes
- **Maximize/restore** — Expand any dock area to fill its container

### 📌 Sidebars

- **Auto-hide panels** — VS Code-style slide-out sidebars that appear on hover
- **Pinned widgets** — Pin dock widgets to sidebars with visual tab buttons; pinned docks, and whether each is closed, are saved with the layout
- **Allowed sides** — Limit sidebars to the edges you want (say left and right only); pinning never creates one elsewhere
- **Pin API and signal** — `pin_dock_widget()`, `unpin_dock_widget()`, `is_dock_widget_pinned()`, `pinned_dock_widgets()`, and `signals.dock_pinned_changed` to follow pin changes
- **Notification badges** — Numerical or symbolic badges on sidebar tabs
- **Shaped tabs** — Sidebar tabs take the dock widget tabs' corner radius, flat on the window-facing or content-facing side (or rounded on all four), with an outline that closes all the way round or leaves the flat edge open
- **Per-state outlines and fills** — Inactive, hovered and active each get their own outline colour and background, so a theme can outline only the selected tab, ring one under the cursor, or tint every tab with the highlight colour
- **Configurable focus behavior** — Choose whether sidebars steal keyboard focus
- **Drag to detach** — Tear pinned widgets out of sidebars back into the main layout

### 🎨 Theming

- **37 built-in themes** — eight basics (midnight, dark, mocha, slate, caramel, neutral, cream, light), each also on a 10px neo chassis (`*_neo`), nordic, monokai, tokyo_night, catppuccin, dracula, solarized_dark/light, cyberpunk_neon, cyberpunk_edge, slate_amber, neon_dusk, violet_haze, and midnight_haze, plus light and neutral counterparts of the last four (`*_light`; `*_neutral`, a mid tone between the two and nearer the light, with the backdrop flattened to grey but the accent and focus outlines kept; plus `slate_amber_dark` and a brighter `slate_amber_light`) that keep their parent's geometry and change only the palette
- **Grouped theme menus** — `theme_groups()` returns `(group, [(label, key), ...])` in presentation order — Basics, Editor Classics, Neon, Edge Treatments — with each family kept together and ordered dark, neutral, light; `theme_choices()` is the same order flattened for a single-level menu
- **OKLCH theme engine** — Surfaces are derived in OKLCH, so equal steps look equal on any base colour. The keywords `contrast` (low/normal/high WCAG floors), `depth` (flat/subtle/raised) and `selection` (solid/tint) steer the look. Text and UI colours are held to their contrast floors automatically.
- **Complete `QPalette`** — Every role in every colour group (Active, Inactive, Disabled) is themed, so no platform colour leaks into dark themes
- **LaceStyle** — A flat, vector `QProxyStyle` over Fusion for buttons, fields, combo and spin boxes, sliders, dials, tabs, menus, item views, tooltips, frames, splitters, tool bars and scroll bars (`thin`/`expanding`/`fusion`). Menus and combo popups get rounded corners and a soft painted shadow. It follows the theme and stays sharp at any zoom, including widgets in a `QGraphicsView`.
- **Rounded content** — `corner_clip="cap"` paints an antialiased cap over square content inside rounded cards
- **Theme kit & Theme Studio** — `lace.theme_kit` makes a theme from two seed colours and a chassis, audits contrast (as a CI gate too), derives dark/neutral/light counterparts, and exports JSON. `python -m lace.theme_kit studio` edits a theme live.
- **Declarative `ThemeSpec`** — Define custom themes with color palettes and geometrical tokens (corner radius, border width, title height, tab radius, content margin, etc.)
- **Sidebar tab tokens** — A matching `sidebar_tab_*` set for the auto-hide tabs: shape, radius, outline width and per-state colours, fills, and highlight-strip width and edge
- **JSON theme files** — Ship themes as JSON (Pydantic-validated via `ThemeJson`/`load_theme_json`); colors as `[r,g,b,a]` lists or `"#rrggbb"` strings
- **Reactive borders** — Active dock area shows a vibrant focus border; inactive areas show a subtle neutral border
- **OS auto-sync** — Automatically switch between light/dark themes when the OS changes (`ThemeManager.sync_theme(force, path)`)
- **Custom QSS/stylesheet support** — Point themes to external `.qss` or `.css` files, or a directory of `<name>.json|.qss|.css` files via `default_theme_path`

### ⚙️ Configuration

- **19 global flags** — Control tab visibility, button visibility, drag behavior, floating window chrome, icon styling, and more
- **Per-widget feature flags** — Granular control over what each dock widget can do: closable, movable, floatable, pinnable
- **Insertion order** — Sort "Show View" menu items alphabetically or chronologically
- **Toggle view actions** — Integrate dock widget show/hide into menu bars or toolbars as checkable toggles or one-way show buttons

### 💾 Persistence

- **JSON layout serialization** — Save and restore complete window layouts to/from JSON files
- **Perspectives** — Save named layout presets (e.g., "Coding Mode", "Presentation Mode") and switch between them instantly
- **Atomic file I/O** — Layouts are written atomically (temp file + rename) to prevent corruption

### 🎯 Icons & Chrome

- **SVG-based icon system** — Theme-aware SVG icons with automatic color tinting
- **Custom icon provider** — Register a directory of SVG icons for use across tabs and menus
- **Painted chrome** — Custom-drawn title bars, tab buttons, splitter handles, and drop indicators with rounded corners and hover states
- **Frameless windows** — Custom (PySideSix-Frameless-Window) title bars for the main window and floating containers with a synchronous double-click-to-maximize, DWM shadow, and resize borders; GL children (`QWebEngineView`, `QOpenGLWidget`) auto-heal the native chrome via `WinIdChange` (`ensure_frameless_chrome()`)
- **Configurable custom title bars** — Set different title-bar classes for the main window and floating dock containers (`title_bar=` constructor arg, live `DockManager.main_title_bar` / `floating_title_bar`); embed menus, search fields, or any widget directly in the frameless chrome — `LaceStandardTitleBar` already vetoes drags from interactive children, paints the theme background, and anchors inserts, so subclasses only add widgets
- **Chromeless floating windows** — Optional bare floating surfaces without any title bar
- **Themed dialogs** — `FramelessLaceDialog` and the `lace.dialogs` helpers (message boxes, input, colour and file dialogs, same arguments and results as Qt's) carry the main window's title bar; dialogs that keep the system frame get the theme's caption colour on Windows 11 and its light/dark mode on Windows 10

---

## Quick Start

### Installation

```bash
pip install pyside6
# Clone Lace
git clone https://github.com/yourusername/lace.git
cd lace
```

### Minimal Example

```python
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QTextEdit
from lace import (DockManager, DockWidget, DockWidgetArea, DockWidgetFeature,
                  LaceStyle, apply_dock_theme)

app = QApplication(sys.argv)
app.setStyle(LaceStyle())

window = QMainWindow()
window.setWindowTitle("My App")
window.resize(1200, 800)

# Create the dock manager (it becomes the window's central widget)
dock_manager = DockManager(window)

# Apply a theme
apply_dock_theme("cyberpunk_neon")

# Add a dock widget
editor = DockWidget("Editor", window)
editor.set_widget(QTextEdit())
editor.set_features(DockWidgetFeature.all_features)
dock_manager.add_dock_widget(DockWidgetArea.center, editor)

window.show()
app.exec()
```

### Sidebars and Pinning

Pinning is offered once a sidebar exists. `set_sidebar_areas()` creates the
sidebars and limits pinning to those sides:

```python
dock_manager.set_sidebar_areas({DockWidgetArea.left, DockWidgetArea.right})

dock_manager.pin_dock_widget(editor)                       # closest allowed side
dock_manager.pin_dock_widget(editor, DockWidgetArea.left)
dock_manager.is_dock_widget_pinned(editor)                 # True
dock_manager.unpin_dock_widget(editor)                     # back into the layout

dock_manager.signals.dock_pinned_changed.connect(
    lambda dock, area: print(dock.objectName(), area))      # area is None once unpinned
```

- Only docks with `DockWidgetFeature.pinnable` can be pinned. A dock added with
  `add_sidebar_widget(area, dock)` without that feature is locked in its sidebar.
- For a pinned dock, `is_closed()` means its tab is hidden; an open pinned dock
  shows its tab, whether or not its panel is slid out.
- `save_state()` / `restore_state()` carry the pins. Restoring a layout puts
  every dock where the layout has it, pinned or docked.

See the [Quick Reference](docs/QUICK_REFERENCE.md) for badges, focus behaviour
and the rest of the sidebar API.

### Full Example

Run the demo application to explore all features:

```bash
python -m demos.demo_app
```

The demo includes:
- Multiple dock widgets with different feature flags (closable, movable, floatable, pinnable)
- Sidebar setup with notification badges
- Theme switching menu, grouped into Basics / Editor Classics / Neon / Edge Treatments submenus via `theme_groups()`
- Global flags menu for live configuration toggling
- Insertion order control
- Sidebar focus mode and badge position controls
- Preset configurations (Default, Minimal, Full)
- A "Dialog…" button opening a custom `FramelessLaceDialog`

For frameless/custom-title-bar examples, see:

```bash
python -m demos.demo_app_custom_titlebar          # standard custom title bar
python -m demos.demo_app_custom_titlebar_menus    # menu-embedded main title bar + search bar for floats
```

The second demo shows **configurable custom title bars**: the main window
uses a title bar with a `QMenuBar` embedded directly in the frameless chrome
(no separate menu bar below it), while every floating dock container gets a
different title bar with a centered, resizable search `QLineEdit`.

Custom title bars are configured with a *title-bar descriptor* — `None` (the
standard Lace title bar), a `QWidget` instance, a `QWidget` subclass, or a
callable factory. Pass one to the window constructor or to the dock manager:

```python
from lace import DockManager, TitleBarMode
from lace.frameless_window import FramelessLaceMainWindow

class MainWindow(FramelessLaceMainWindow):
    def __init__(self):
        # Custom title bar for the main window (class or instance).
        super().__init__(title_bar=MenuEmbeddedTitleBar)
        self.dock_manager = DockManager(self)
        self.dock_manager.title_bar_mode = TitleBarMode.custom
        # Different title bar for every floating dock container.
        self.dock_manager.floating_title_bar = SearchTitleBar
```

`DockManager.main_title_bar` configures the main window (applied live when
the parent is frameless), and `DockManager.floating_title_bar` configures
new floating containers created when dock widgets are torn off.
`DockManager` also installs both theme bridges itself (dock tree + app-wide
for top-level `QMenu`s), so no manual `DockThemeBridge()` is needed. They set
colours only; pass `DockManager(window, app_style="lace")` (or `"Fusion"`, …) to
have it install the application's style too. See
[Quick Reference — Frameless Windows & the Custom Title Bar](docs/QUICK_REFERENCE.md#frameless-windows--the-custom-title-bar)
for the full API.

---

## Screenshots

![Lace frameless main window across 12 themes](https://raw.githubusercontent.com/opticsWolf/Lace/main/screenshots/main_themes_grid.png?v=0.9.0)

*The frameless main window (custom title bar, dock panels, splitters) across 12 built-in themes.*

Full-size captures of the main window, one per theme above, are in the
[`screenshots/`](https://github.com/opticsWolf/Lace/tree/main/screenshots) folder.

---

## Architecture Overview

Lace is built around a clean, modular architecture:

```
DockManager (facade)
├── DockContainerWidget (root container)
│   ├── DockSplitter (nested, orientation-aware)
│   └── DockAreaWidget (tabbed regions)
│       ├── DockAreaTitleBar
│       │   └── DockAreaTabBar → DockWidgetTab (×N)
│       └── DockWidget → user content (QTextEdit, QWidget, etc.)
├── FloatingDockContainer (×N, native or frameless; each holds a DockContainerWidget)
├── DockOverlay (drop targets: dock area + container)
├── DockSignals (internal event bus)
├── SidebarManager (auto-hide panels)
│   ├── SideTabBar → VerticalTabButton (×N)
│   └── SideBarContainer (overlay panel)
├── LayoutSerializer + LayoutPersistenceManager (JSON layouts, perspectives)
└── DockThemeBridge ×2 (QPalette → dock tree, and → application)

Application-wide
├── DockStyleManager (theme engine, singleton; notifies subscribers)
├── ThemeManager (OS-aware auto light/dark)
├── LaceStyle (QStyle drawing the basic widgets)
├── NativeFrameTheme (OS title bars of dialogs; DockManager installs it)
└── Frameless chrome: FramelessLaceMainWindow, FramelessLaceDialog
    and the lace.dialogs helpers (themed title bar via FramelessTitleBarStyler)
```

See the [Architecture Documentation](docs/ARCHITECTURE.md) for a complete module-by-module reference with class hierarchies, signals, and method tables.

---

## Documentation

| Document | Description |
|---|---|
| [**Quick Reference**](docs/QUICK_REFERENCE.md) | 5-minute guide — installation, common patterns, API lookup |
| [**Architecture**](docs/ARCHITECTURE.md) | Complete system architecture — all modules, classes, signals, and data flow |
| [**Theming & Geometry**](docs/theming_and_geometry.md) | ThemeSpec tokens, titlebar flushness, reactive borders, content margin |
| [**Enum Mapping**](docs/enum_mapping.md) | Comprehensive mapping of all enumerations and flags with wiring status |

---

## Project Structure

```
lace/
├── lace/                          # Main package
│   ├── dock_manager.py            # Central orchestrator (facade)
│   ├── dock_widget.py             # User-facing dock widget wrapper
│   ├── dock_widget_tab.py         # Painted-chrome tab button
│   ├── dock_container_widget.py   # Dock container (root, or inside a floating window)
│   ├── dock_area_widget.py        # Single tabbed region
│   ├── dock_area_layout.py        # Stacked layout behind a dock area's tabs
│   ├── dock_area_tab_bar.py       # Scrollable tab strip of a dock area
│   ├── dock_area_title_bar.py     # Dock area title bar (tabs + buttons)
│   ├── dock_splitter.py           # Nested splitters + resize handles
│   ├── floating_dock_container.py # Top-level floating window
│   ├── floating_dock_container_frameless.py  # Frameless floating window
│   ├── floating_behaviour.py      # Behaviour shared by both floating containers
│   ├── frameless_window.py        # Frameless main/window + LaceStandardTitleBar
│   ├── frameless_titlebar.py      # Dock-theme styling for the custom title bar
│   ├── frameless_dialog.py        # FramelessLaceDialog
│   ├── dialogs.py                 # Themed drop-ins for Qt's static dialogs
│   ├── native_frame.py            # Theme colours for OS title bars (dialogs, tool windows)
│   ├── title_bar_colors.py        # One source for title-bar colours
│   ├── dock_overlay.py            # Drop-target visual overlays
│   ├── dock_chrome.py             # Drag detector, chrome buttons, frames
│   ├── dock_paint.py              # Painting primitives
│   ├── dock_menu.py               # Unified context menu system
│   ├── dock_menu_bar.py           # Theme styling for plain QMainWindow menu bars
│   ├── lace_style.py              # LaceStyle: a modern, flat Fusion
│   ├── style/                     # LaceStyle's painters (buttons, inputs, popups, …)
│   ├── dock_theme.py              # Theme schemas, ThemeSpec, color math
│   ├── dock_custom_theme.py       # 37 built-in theme presets
│   ├── color_science.py           # Perceptual colour maths for theme derivation
│   ├── theme_contrast.py          # Contrast rules for each theme token
│   ├── theme_models.py            # ThemeJson — Pydantic JSON theme loading
│   ├── theme_kit/                 # Theme Studio and theme tooling (python -m lace.theme_kit)
│   ├── dock_style_manager.py      # Singleton style manager (subscriber model)
│   ├── dock_theme_bridge.py       # QPalette push to Qt children
│   ├── dock_styled.py             # DockStyled mixin (auto-style registration)
│   ├── theme_manager.py           # OS-aware auto dark/light switching
│   ├── layout_serializer.py       # JSON save/restore, perspectives
│   ├── dock_container_state.py    # Low-level tree state save/restore
│   ├── dock_signals.py            # Internal event bus
│   ├── dock_icon_provider.py      # SVG icon provider with tinting
│   ├── sidebar_manager.py         # Auto-hide sidebar controller
│   ├── sidebar_tab.py             # Vertical tab button
│   ├── sidebar_tab_bar.py         # Vertical tab strip
│   ├── sidebar_container.py       # Animated overlay panel
│   ├── sidebar_title_bar.py       # Title bar inside overlay panel
│   ├── eliding_label.py           # QLabel with text elision
│   ├── enums.py                   # All enumerations and flags
│   ├── util.py                    # Utility functions
│   ├── _trace.py                  # Optional debug tracing
│   └── resources/lace_icons/      # SVG icons (close, dock, float, pin, etc.)
├── demos/                         # Demo applications (python -m demos.demo_app)
│   ├── demo_app.py                # Full-featured demo application
│   ├── demo_app_custom_titlebar.py        # Custom title-bar demo
│   ├── demo_app_custom_titlebar_menus.py  # Menu-embedded title-bar demo
│   ├── demo_panels.py             # Panel contents shared by the demos
│   └── demo_dialog.py             # The custom "New layer" FramelessLaceDialog
├── dev_smoke/                     # Smoke checks (run_all.py) and screenshot tools
├── tests/                         # pytest suite
├── docs/                          # Documentation
├── screenshots/                   # Theme screenshots used by this README
├── CHANGELOG.md
├── LICENSE                        # Apache-2.0
├── NOTICE
├── pyproject.toml
└── README.md                      # This file
```

---

## Testing

Two complementary test layers:

- **`tests/` (pytest)** — fast logic/contract tests for the theme engine,
  `ThemeJson` loading, `DockStyleManager`, enums/config masks, paint
  primitives, layout-serializer errors, and an AST-based circular-import
  detector that fails if a real module-level import cycle is introduced.

  ```bash
  pytest tests/
  ```

- **`dev_smoke/` (offscreen Qt)** — each check builds its own `QApplication`
  and drives real widgets offscreen (theme switching, sidebar chrome,
  save/restore round-trips, dock flags, JSON theme application):

  ```bash
  python dev_smoke/run_all.py
  ```

---

## Contributing

Contributions are welcome! Please:

1. Open an issue to discuss significant changes before starting work
2. Follow the existing code style and naming conventions
3. Add smoke tests in `dev_smoke/` for new features
4. Update documentation (`docs/`) for user-facing changes

---

## License

Lace is licensed under the **Apache License 2.0**. See [LICENSE](LICENSE) for details.

This project incorporates components from [qtpydocking](https://github.com/PySide6/qtpydocking) under the BSD 3-Clause License. See [LICENSE](LICENSE) for full attribution.

---

**Author:** opticsWolf  
**Contact:** opticswolf@protonmail.com
