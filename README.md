# Lace

**Advanced docking system for PySide6** — a feature-rich, themeable widget layout framework for building professional Qt desktop applications in Python.

**Version:** 0.6.5

[![PyPI](https://img.shields.io/pypi/v/lace-dock.svg)](https://pypi.org/project/lace-dock/)
[![License](https://img.shields.io/pypi/l/lace-dock.svg)](https://pypi.org/project/lace-dock/)
[![Tests & Publish](https://github.com/opticsWolf/Lace/actions/workflows/publish.yml/badge.svg)](https://github.com/opticsWolf/Lace/actions/workflows/publish.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/downloads/)
[![Framework](https://img.shields.io/badge/framework-PySide6%20%2F%20Qt6-purple)](https://pypi.org/project/PySide6/)

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

### 🪑 Docking & Layout

- **Multi-area docking** — Dock widgets to left, right, top, bottom, or center regions within a window
- **Tabbed dock areas** — Multiple widgets share a single dock area as tabs, with full tab management (reorder, close, float)
- **Floating windows** — Detach any dock widget into its own top-level window; drag it back to dock
- **Drag-and-drop layout** — Intuitive resize, re-order, and re-dock via visual drop indicators
- **Nested splitters** — Arbitrary nesting of horizontal and vertical split panes
- **Maximize/restore** — Expand any dock area to fill its container

### 📌 Sidebars

- **Auto-hide panels** — VS Code-style slide-out sidebars that appear on hover
- **Pinned widgets** — Pin dock widgets to sidebars with visual tab buttons
- **Notification badges** — Numerical or symbolic badges on sidebar tabs
- **Shaped tabs** — Sidebar tabs take the dock widget tabs' corner radius, flat on the window-facing or content-facing side (or rounded on all four), with an outline that closes all the way round or leaves the flat edge open
- **Per-state outlines and fills** — Inactive, hovered and active each get their own outline colour and background, so a theme can outline only the selected tab, ring one under the cursor, or tint every tab with the highlight colour
- **Configurable focus behavior** — Choose whether sidebars steal keyboard focus
- **Drag to detach** — Tear pinned widgets out of sidebars back into the main layout

### 🎨 Theming

- **27 built-in themes** — Dark, light, midnight, warm, nordic, monokai, neutral, tokyo_night, catppuccin, dracula, solarized_dark/light, cyberpunk_neon, cyberpunk_edge, slate_amber, neon_dusk, violet_haze, and midnight_haze, plus light and neutral counterparts of the last four (`*_light`; `*_neutral`, a mid tone between the two and nearer the light, with the backdrop flattened to grey but the accent and focus outlines kept; plus `slate_amber_dark` and a brighter `slate_amber_light`) that keep their parent's geometry and change only the palette
- **Grouped theme menus** — `theme_groups()` returns `(group, [(label, key), ...])` in presentation order — Basics, Editor Classics, Neon, Edge Treatments — with each family kept together and ordered dark, neutral, light; `theme_choices()` is the same order flattened for a single-level menu
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
- **Frameless windows** — Custom (PySideSix-Frameless-Window) title bars for the main window and floating containers with a synchronous double-click-to-maximize, DWM shadow, and resize borders
- **Configurable custom title bars** — Set different title-bar classes for the main window and floating dock containers (`title_bar=` constructor arg, `DockManager.main_title_bar` / `floating_title_bar`); embed menus, search fields, or any widget directly in the frameless chrome
- **Chromeless floating windows** — Optional bare floating surfaces without any title bar

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
from lace import DockManager, DockWidget, DockWidgetArea, apply_dock_theme

app = QApplication(sys.argv)
app.setStyle("Fusion")

window = QMainWindow()
window.setWindowTitle("My App")
window.resize(1200, 800)

# Create the dock manager
dock_manager = DockManager(window)
window.setCentralWidget(dock_manager._root)

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

For frameless/custom-title-bar examples, see:

```bash
python -m demos.demo_app_custom_titlebar.py          # standard custom title bar
python -m demos.demo_app_custom_titlebar_menus.py      # menu-embedded main title bar + search bar for floats
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

`DockManager.main_title_bar` configures the main window, and
`DockManager.floating_title_bar` configures new floating containers created
when dock widgets are torn off. See [Quick Reference — Frameless Windows
& the Custom Title Bar](docs/QUICK_REFERENCE.md#frameless-windows--the-custom-title-bar)
for the full API.
- Insertion order control
- Sidebar focus mode and badge position controls
- Preset configurations (Default, Minimal, Full)

---

## Screenshots

![Lace frameless main window across 12 themes](https://raw.githubusercontent.com/opticsWolf/Lace/main/screenshots/main_themes_grid.png)

*The frameless main window (custom title bar, dock panels, splitters) across 12 built-in themes.*

Full-size captures (main window + frameless floating containers) are in the
[`screenshots/`](https://github.com/opticsWolf/Lace/tree/main/screenshots) folder.

---

## Architecture Overview

Lace is built around a clean, modular architecture:

```
DockManager (facade)
├── DockContainerWidget (root + floating windows)
│   ├── DockSplitter (nested, orientation-aware)
│   └── DockAreaWidget (tabbed regions)
│       ├── DockAreaTitleBar
│       │   └── DockAreaTabBar → DockWidgetTab (×N)
│       └── DockWidget → user content (QTextEdit, QWidget, etc.)
├── SidebarManager (auto-hide panels)
│   ├── SideTabBar → VerticalTabButton (×N)
│   └── SideBarContainer (overlay panel)
├── LayoutSerializer (JSON persistence)
├── DockStyleManager (theme engine)
├── DockThemeBridge (QPalette → Qt children)
└── ThemeManager (OS-aware auto light/dark)
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
│   ├── dock_container_widget.py   # Root + floating container
│   ├── dock_area_widget.py        # Single tabbed region
│   ├── dock_splitter.py           # Nested splitters + resize handles
│   ├── floating_dock_container.py # Top-level floating window
│   ├── floating_dock_container_frameless.py  # Frameless floating window
│   ├── frameless_window.py       # Frameless main/window + LaceStandardTitleBar
│   ├── frameless_titlebar.py     # Dock-theme styling for the custom title bar
│   ├── dock_overlay.py            # Drop-target visual overlays
│   ├── dock_chrome.py             # Drag detector, chrome buttons, frames
│   ├── dock_paint.py              # Painting primitives
│   ├── dock_theme.py              # Theme schemas, ThemeSpec, color math
│   ├── dock_custom_theme.py       # 18 built-in theme presets
│   ├── theme_models.py            # ThemeJson — Pydantic JSON theme loading
│   ├── dock_style_manager.py      # Singleton style manager (subscriber model)
│   ├── dock_theme_bridge.py       # QPalette push to Qt children
│   ├── theme_manager.py           # OS-aware auto dark/light switching
│   ├── layout_serializer.py       # JSON save/restore, perspectives
│   ├── dock_container_state.py    # Low-level tree state save/restore
│   ├── dock_signals.py            # Internal event bus
│   ├── dock_menu.py               # Unified context menu system
│   ├── dock_styled.py             # DockStyled mixin (auto-style registration)
│   ├── dock_icon_provider.py      # SVG icon provider with tinting
│   ├── sidebar_manager.py         # Auto-hide sidebar controller
│   ├── sidebar_tab.py             # Vertical tab button
│   ├── sidebar_tab_bar.py         # Vertical tab strip
│   ├── sidebar_container.py       # Animated overlay panel
│   ├── sidebar_title_bar.py       # Title bar inside overlay panel
│   ├── sidebar_state.py           # Sidebar state compatibility shim
│   ├── eliding_label.py           # QLabel with text elision
│   ├── enums.py                   # All enumerations and flags
│   ├── util.py                    # Utility functions
│   └── _trace.py                  # Optional debug tracing
├── demos/                          # Demo applications (python -m demos.demo_app)
│   ├── demo_app.py                  # Full-featured demo application
│   ├── demo_app_custom_titlebar.py  # Custom title-bar demo
│   └── demo_app_custom_titlebar_menus.py  # Menu-embedded title-bar demo
├── dev_smoke/                     # Smoke tests for individual features
├── tests/                         # pytest suite (theme engine, JSON themes, style manager, enums, paint, layout errors, circular-import detector)
├── docs/                          # Documentation
├── lace/resources/lace_icons/     # SVG icons (close, dock, float, pin, etc.)
├── LICENSE                        # Apache-2.0
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
