# Lace

**Advanced docking system for PySide6** — a feature-rich, themeable widget layout framework for building professional Qt desktop applications in Python.

**Version:** 0.2.5

![License](https://img.shields.io/badge/license-Apache--2.0-blue)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Framework](https://img.shields.io/badge/framework-PySide6%20%2F%20Qt6-purple)

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
- **Configurable focus behavior** — Choose whether sidebars steal keyboard focus
- **Drag to detach** — Tear pinned widgets out of sidebars back into the main layout

### 🎨 Theming

- **14 built-in themes** — Dark, light, midnight, warm, nordic, monokai, neutral, tokyo_night, catppuccin, dracula, solarized_dark/light, and cyberpunk_neon
- **Declarative `ThemeSpec`** — Define custom themes with color palettes and geometrical tokens (corner radius, border width, title height, tab radius, content margin, etc.)
- **Reactive borders** — Active dock area shows a vibrant focus border; inactive areas show a subtle neutral border
- **OS auto-sync** — Automatically switch between light/dark themes when the OS changes
- **Custom QSS/stylesheet support** — Point themes to external `.qss` or `.css` files

### ⚙️ Configuration

- **16 global flags** — Control tab visibility, button visibility, drag behavior, floating window chrome, icon styling, and more
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
- **Chromeless floating windows** — Optional frameless floating windows that rely entirely on Lace's custom title bar

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
python demo_app.py
```

The demo includes:
- Multiple dock widgets with different feature flags (closable, movable, floatable, pinnable)
- Sidebar setup with notification badges
- Theme switching menu with 14 built-in themes
- Global flags menu for live configuration toggling
- Insertion order control
- Sidebar focus mode and badge position controls
- Preset configurations (Default, Minimal, Full)

---

## Screenshots

> *Screenshots coming soon — add images of your application running with different themes.*

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
│   ├── dock_overlay.py            # Drop-target visual overlays
│   ├── dock_chrome.py             # Drag detector, chrome buttons, frames
│   ├── dock_paint.py              # Painting primitives
│   ├── dock_theme.py              # Theme schemas, ThemeSpec, color math
│   ├── dock_custom_theme.py       # 14 built-in theme presets
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
├── demo_app.py                    # Full-featured demo application
├── dev_smoke/                     # Smoke tests for individual features
├── docs/                          # Documentation
├── lace/resources/lace_icons/     # SVG icons (close, dock, float, pin, etc.)
├── LICENSE                        # Apache-2.0
└── README.md                      # This file
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
