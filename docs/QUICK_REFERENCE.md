# Lace Quick Reference

**Advanced PySide6 Docking System** — your 5-minute guide to getting started.

**Version:** 0.5.0

---

## 1. Installation & Setup

### Minimal Window

```python
import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from lace import DockManager, apply_dock_theme

app = QApplication(sys.argv)
app.setStyle("Fusion")

window = QMainWindow()
window.setWindowTitle("My App")
window.resize(1200, 800)

# 1. Create the dock manager and set it as the central widget
dock_manager = DockManager(window)
window.setCentralWidget(dock_manager._root)

# 2. Apply a theme
apply_dock_theme("cyberpunk_neon")

window.show()
app.exec()
```

### With Theming Bridge (recommended)

```python
from lace import DockManager, DockThemeBridge, ThemeManager, apply_dock_theme

# ... after creating window ...
dock_manager = DockManager(window)
window.setCentralWidget(dock_manager._root)

# Optional: bridge pushes QPalette to Qt children so they match the dock theme
theme_bridge = DockThemeBridge(parent=window)

# Optional: auto-switch with OS dark/light mode
theme_manager = ThemeManager(QApplication.instance())
theme_manager.auto_mode_enabled = True  # default is True
```

---

## 2. Adding Dock Widgets

### Basic Widget

```python
from lace import DockWidget, DockWidgetArea, DockWidgetFeature
from PySide6.QtWidgets import QTextEdit

editor = DockWidget("Editor", window)
editor.set_default_icon_name("dock")  # or set_custom_icon_name("pin")
editor.set_features(DockWidgetFeature.all_features)  # closable | movable | floatable | pinnable

content = QTextEdit()
content.setPlaceholderText("Type here...")
editor.set_widget(content)

# Dock to a specific area
dock_manager.add_dock_widget(DockWidgetArea.center, editor)
```

### Widget Feature Flags

| Flag | Effect |
|---|---|
| `DockWidgetFeature.closable` | Shows close button on tab & title bar |
| `DockWidgetFeature.movable` | Tab can be dragged to reorder or move between areas |
| `DockWidgetFeature.floatable` | Tab can be dragged out into a floating window |
| `DockWidgetFeature.pinnable` | Tab can be pinned to a sidebar |
| `DockWidgetFeature.no_features` | Widget is locked in place |
| `DockWidgetFeature.all_features` | All of the above combined |

```python
# Example: unclosable but movable/floatable
widget = DockWidget("Logger", window)
widget.set_features(DockWidgetFeature.movable | DockWidgetFeature.floatable)
dock_manager.add_dock_widget(DockWidgetArea.bottom, widget)
```

### Named Area Locking

Restrict widgets to a specific dock area, preventing them from being floated individually or pinned to sidebars:

```python
# 1. Name the target dock area widget
design_area = widget_a.dock_area_widget()
design_area.locked_name = "DesignArea"

# 2. Lock widgets to this specific dock area name
widget_a.locked_to_area = "DesignArea"
widget_b.locked_to_area = "DesignArea"
```

* **Effects of locking:**
  * The widgets' `floatable` and `pinnable` capabilities are dynamically stripped.
  * Dragging tabs out to float or right-clicking to Pin/Float is disabled.
  * Tabs can still be dragged horizontally to reorder within the tab bar.
  * The entire dock area can still be undocked/floated as a single container.

### Insert Mode (Scroll Area Wrapping)

```python
# Default: auto-wraps content in QScrollArea if not already one
editor.set_widget(content)  # insert_mode=InsertMode.auto_scroll_area

# Force no scroll area
editor.set_widget(content, InsertMode.force_no_scroll_area)

# Force wrap in scroll area
editor.set_widget(content, InsertMode.force_scroll_area)
```

---

## 3. Layout & Docking Areas

### Dock Areas

| Area | Description |
|---|---|
| `DockWidgetArea.left` | Left edge of window |
| `DockWidgetArea.right` | Right edge of window |
| `DockWidgetArea.top` | Top edge of window |
| `DockWidgetArea.bottom` | Bottom edge of window |
| `DockWidgetArea.center` | Central workspace (default) |

### Adding Widgets to Areas

```python
# Add to center (default target area)
dock_manager.add_dock_widget(DockWidgetArea.center, editor)

# Add to bottom, docked alongside existing widgets
dock_manager.add_dock_widget(DockWidgetArea.bottom, logger)

# Add to a specific area within an existing container
dock_manager.add_dock_widget(DockWidgetArea.right, tool_panel)
```

### Tabbed Dock Areas

Multiple `DockWidget`s can share a single `DockAreaWidget` as tabs. The first widget added to an area creates the area; subsequent widgets are added as tabs.

```python
# These two widgets share the same dock area as tabs
dock_manager.add_dock_widget(DockWidgetArea.center, editor)
dock_manager.add_dock_widget(DockWidgetArea.center, console)  # becomes a tab
```

---

## 4. Sidebars (Auto-Hide Panels)

### Setup Sidebars

```python
from lace import DockWidgetArea

# Add sidebar overlays to left and right edges
sm = dock_manager.sidebar_manager
sm.add_sidebar(DockWidgetArea.left)
sm.add_sidebar(DockWidgetArea.right)
```

### Adding Sidebar Widgets

```python
from lace import DockWidget, DockWidgetFeature

sidebar_widget = DockWidget("Sidebar Tool", window)
sidebar_widget.set_features(DockWidgetFeature.closable)  # only closable
content = QLabel("Pinned sidebar content")
sidebar_widget.set_widget(content)

# Pin to a specific sidebar
dock_manager.add_sidebar_widget(DockWidgetArea.left, sidebar_widget)
```

### Sidebar Badges

```python
sm = dock_manager.sidebar_manager
sm.update_badge(sidebar_widget, 3)       # numeric badge
sm.update_badge(sidebar_widget, "!")     # string badge
sm.update_badge(sidebar_widget, 0)       # clear badge
sm.clear_badge(sidebar_widget)           # clear badge (alias)
```

### Sidebar Focus Behavior

```python
from lace import SideBarFocusBehavior

# Options:
#   SideBarFocusBehavior.take_focus_and_restore  (default)
#   SideBarFocusBehavior.take_focus_only
#   SideBarFocusBehavior.no_focus_transfer

dock_manager.sidebar_focus_behavior = SideBarFocusBehavior.no_focus_transfer
```

### Badge Position

```python
from lace import TabBadgePosition

dock_manager.tab_badge_position = TabBadgePosition.bottom_left
# Options: top_right (default), top_left, bottom_left, bottom_right
```

---

## 5. Theming

### Apply Built-in Theme

```python
from lace import apply_dock_theme

apply_dock_theme("cyberpunk_neon")
# Themes: default, dark, light, midnight, warm, nordic, monokai,
#         neutral, tokyo_night, catppuccin, dracula, solarized_dark,
#         solarized_light, cyberpunk_neon
```

### Auto Theme (OS Sync)

```python
from lace import ThemeManager

# default_theme_path: single theme file, or a directory of
# <theme_name>.json|.qss|.css files used when no explicit path is given
theme_manager = ThemeManager(QApplication.instance(), default_theme_path="themes/")
theme_manager.auto_mode_enabled = True  # enables OS dark/light detection

# Override light/dark theme preferences
theme_manager.user_light_theme = "light"
theme_manager.user_dark_theme = "dark"

# Or point to a custom .qss/.css/.json file
theme_manager.user_light_theme = "/path/to/my_theme.qss"

# Sync now; optionally force a re-apply or pin an explicit theme file:
theme_manager.sync_theme()                    # resolve from user prefs / default path
theme_manager.sync_theme(force=True)          # re-apply even if unchanged
theme_manager.sync_theme(path="themes/nordic.json")  # explicit file wins
```

### JSON Theme File (Pydantic-validated)

```python
from lace import load_theme_json, get_dock_style_manager

# theme.json mirrors ThemeSpec; colors accept [r,g,b,a] lists or "#rrggbb"
# strings; unknown keys are ignored; violations raise ValidationError.
theme = load_theme_json("my_theme.json")
get_dock_style_manager().apply_theme_dict(theme)
```

### Custom Theme with ThemeSpec

```python
from lace import ThemeSpec, apply_dock_theme, build_theme

# Define a custom theme
my_theme = ThemeSpec(
    base       = [30, 30, 40, 255],     # Dark purple canvas
    accent     = [255, 100, 0, 255],    # Orange accent
    text       = [240, 240, 240, 255],  # Light text
    surface    = [40, 40, 55, 255],     # Inner panel
    border     = [100, 100, 150, 255],  # Subtle border
    tooltip_bg = [60, 60, 80, 255],     # Tooltip background (optional)
    tooltip_text = [240, 240, 240, 255],# Tooltip text (optional)
    corner_radius = 8,
    border_width = 1.0,
    title_height = 30,
    tab_radius = 6,
    content_margin = (8, 4),            # left/right/bottom=8, top=4
)

# Build and apply
build_theme(my_theme)  # registers under the theme's name
apply_dock_theme(my_theme)  # or apply directly
```

### ThemeSpec Geometrical Tokens

| Token | Description |
|---|---|
| `corner_radius` | Rounded corner radius for dock cards |
| `border_width` | Stroke width for card outlines |
| `title_height` | Height of the title bar |
| `title_padding_left` / `title_padding_right` | Horizontal padding in title bar |
| `title_button_spacing` | Spacing between action buttons |
| `title_margin` | Inset around title bar (0 = flush against card edges) |
| `title_border_width` | Full outline stroke around title bar |
| `title_border_bottom` | Divider line under title bar |
| `title_border_color` | Color for title bar borders |
| `tab_radius` | Rounded corner radius for tabs |
| `tab_margin` | Gap between adjacent tabs |
| `content_margin` | Margin around widget content (single value or `(h, v)`) |
| `tab_dimming` | Enable dimming for active tabs in unfocused dock areas |
| `indicator_width` | Thickness (in pixels) of the tab selection highlight stripe |
| `indicator_position` | Active tab highlight stripe edge(s) (`"none"`, `"top"`, `"bottom"`, `"left"`, `"right"`, or combination e.g. `"top, bottom"`) |

---

## 6. Configuration Flags

### Global Flags

Control appearance and behavior globally via `DockManager.config_flags`:

```python
from lace import DockFlags

# Toggle individual flags
dock_manager.config_flags |= DockFlags.always_show_tabs
dock_manager.config_flags &= ~DockFlags.show_tab_close_button

# Check a flag
if DockFlags.floatable_tabs in dock_manager.config_flags:
    print("Tabs can be dragged to float")

# Apply preset configurations
dock_manager.config_flags = DockFlags.default_config  # restore defaults
```

### Key Flags

| Flag | Effect |
|---|---|
| `opaque_splitter_resize` | Splitters resize instantly (no rubber band) |
| `opaque_undocking` | Floating windows stay 100% opaque during drag (vs 60%) |
| `chromeless_float` | Floating windows have no OS title bar/border |
| `always_show_tabs` | Tabs always visible, even with 1 widget |
| `show_tab_close_button` | Individual close button on each tab |
| `active_tab_has_close_button` | Only active tab shows close button |
| `dock_area_has_close_button` | Close button on title bar |
| `dock_area_has_undock_button` | Undock (float) button on title bar |
| `dock_area_has_pin_button` | Pin button on title bar |
| `dock_area_has_maximize_button` | Maximize/restore button on title bar |
| `dock_area_has_tabs_menu_button` | Tabs list menu button on title bar |
| `middle_mouse_button_closes_tab` | Middle-click on tab closes it |
| `floatable_tabs` | Tabs can be dragged to float |
| `pinnable_tabs` | Tabs can be pinned to sidebars |
| `custom_tab_icons` | Use custom icons instead of defaults |
| `hide_disabled_title_bar_icons` | Hide disabled icons (vs gray them out) |

### Refresh UI After Flag Changes

```python
# After toggling flags, refresh all areas to update button visibility
from lace.dock_splitter import DockSplitter
for container in dock_manager.dock_containers():
    for splitter in container.findChildren(DockSplitter):
        splitter.setOpaqueResize(DockFlags.opaque_splitter_resize in dock_manager.config_flags)
    for area in container.opened_dock_areas():
        area._update_title_bar_button_states()
```

---

## 7. Programmatic Dock Widget Control

### Show/Hide Widget

```python
widget.toggle_view(True)   # show
widget.toggle_view(False)  # hide
widget.is_closed()         # check visibility
```

### Close Widget

```python
# Via the widget itself
widget.toggle_view(False)

# Via the dock manager
dock_manager.remove_dock_widget(widget)
```

### Find Widget

```python
found = dock_manager.find_dock_widget("Editor")
if found:
    print(f"Found: {found.title()}")
```

### Get All Widgets

```python
for widget in dock_manager.dock_widgets():
    print(widget.title())
```

### Maximize/Restore Area

Maximize expands a dock area to fill its parent container by hiding sibling areas and redistributing splitter space.

```python
# Via the container (recommended)
container = dock_manager.root_container()
container.toggle_maximize_dock_area(area)  # maximize
container.toggle_maximize_dock_area(area)  # restore (toggle)

# Via the dock area (delegates to container)
area.toggle_maximize()  # maximize
area.toggle_maximize()  # restore (toggle)

# Check state
area.is_maximized()           # True if this area is maximized
container.is_area_maximized(area)  # same check on container
```

**How it works:** Lace recursively walks the nested splitter tree to find the maximized area at its actual nesting level, zeroes sibling splitters, and gives the maximized area's parent splitter all available space. On restore, all splitter sizes are restored from the saved state dict `{id(splitter): sizes_list}`.

---

## 8. Layout Persistence

### Save Layout to File

```python
# Save current layout state
dock_manager.save_layout_to_file("my_layout.json")

# Save with custom version
dock_manager.save_layout_to_file("my_layout.json", version="1.0")
```

### Load Layout from File

```python
# Restore layout
dock_manager.load_layout_from_file("my_layout.json")

# Restore with version check
dock_manager.load_layout_from_file("my_layout.json", version="1.0")
```

### Save/Restore State (In-Memory)

```python
import json

# Serialize to JSON string
state_json = dock_manager.save_state(version="1.0")

# Restore from JSON string
dock_manager.restore_state(state_json, version="1.0")
```

### Perspectives (Named Layout Presets)

```python
# Create a named perspective
dock_manager.add_perspective("Default Layout")
dock_manager.add_perspective("Coding Mode")

# List perspectives
for name in dock_manager.perspective_names():
    print(name)

# Open a perspective
dock_manager.open_perspective("Coding Mode")

# Remove a perspective
dock_manager.remove_perspective("Default Layout")
```

---

## 9. Floating Windows

### Floating a Widget (Automatic)

Drag a tab beyond the drag threshold — Lace automatically creates a `FloatingDockContainer` window.

### Floating a Widget (Programmatic)

```python
# Detach a widget into a floating window
widget.toggle_view(True)  # ensure visible
# Lace handles the rest when the user drags the tab
```

### Accessing Floating Containers

```python
for fw in dock_manager.floating_widgets():
    print(f"Floating window: {fw.windowTitle()}")
    print(f"  Geometry: {fw.geometry()}")
```

### Dedicated Floating-Window Icon

Give floating dock windows (native **and** frameless) an icon separate from
the main window / application icon:

```python
from PySide6.QtGui import QIcon

# From a file, the icon provider, or any QIcon
icon = QIcon("path/to/float_icon.png")
dock_manager.set_floating_window_icon(icon)
```

The icon applies immediately to every currently-open floating window and to
all future ones.  Resolution priority: dedicated icon → application icon →
root window icon.  Pass `None` (or an empty `QIcon`) to revert to the
fallback.

### Frameless Windows & the Custom Title Bar

Frameless chrome (custom title bar, resize borders, DWM shadow) is driven by
[PySideSix-Frameless-Window](https://github.com/zhiyiYo/PyQt-Frameless-Window)
when `TitleBarMode.custom` is active:

```python
from lace.enums import TitleBarMode

dock_manager.title_bar_mode = TitleBarMode.custom
```

For a frameless **main window**, subclass `FramelessLaceMainWindow`.  By
default it installs `LaceStandardTitleBar`; to use a different title bar,
pass a *title-bar descriptor* to the constructor:

```python
from lace.frameless_window import FramelessLaceMainWindow, LaceStandardTitleBar

class MainWindow(FramelessLaceMainWindow):
    def __init__(self):
        super().__init__(title_bar=MyCustomTitleBar)  # class, instance, or callable
        self.dock_manager = DockManager(self)
        self.dock_manager.title_bar_mode = TitleBarMode.custom
        self.setCentralWidget(self.dock_manager._root)
```

`FramelessLaceWindow` (the frameless floating-container base) accepts the
same `title_bar=` argument.

#### Title-bar descriptors

A *title-bar descriptor* is one of:

| Form | Behaviour |
|---|---|
| `None` | Use the standard `LaceStandardTitleBar` (default). |
| `QWidget` instance | Used as-is (re-parented to the window). |
| `QWidget` subclass | Instantiated as `cls(window)`. |
| callable | Called as `factory(window)`; must return a `QWidget`. |

Use a class or callable for floating containers, because every floating
window needs its own title-bar widget instance.

#### Per-window title bars via `DockManager`

Configure custom title bars from one place with the dock manager:

```python
from lace import DockManager, TitleBarMode

class MainWindow(FramelessLaceMainWindow):
    def __init__(self):
        super().__init__(title_bar=MenuEmbeddedTitleBar)
        self.dock_manager = DockManager(self)
        self.dock_manager.title_bar_mode = TitleBarMode.custom
        # Every floating dock container gets a different title bar.
        self.dock_manager.floating_title_bar = SearchTitleBar
        self.setCentralWidget(self.dock_manager._root)
```

- `DockManager.main_title_bar` — descriptor for the main window (consumed
  by callers that build a `FramelessLaceMainWindow`).
- `DockManager.floating_title_bar` — descriptor used by every new floating
  container created after it is set (see `floating_dock_container_frameless.py`).
- `DockManager.create_main_title_bar(parent)` /
  `create_floating_title_bar(parent)` — resolve the descriptors into
  concrete `QWidget` instances.

#### Custom title-bar examples

See `demos/demo_app_custom_titlebar_menus.py` for a complete, runnable example:

```bash
python -m demos.demo_app_custom_titlebar_menus
```

It defines two custom title bars:

- `MenuEmbeddedTitleBar` — embeds a `QMenuBar` in the title-bar layout
  (VS Code / browser style).  The menu bar is transparent and the title bar
  paints its own themed background, so the chrome is one continuous colour;
  the menu bar is kept the same height as the title bar so items stay
  vertically centered, and it styles itself via `DockStyled` so popup/menu
  colours follow theme switches.
- `SearchTitleBar` — embeds a centered `QLineEdit` in the chrome with
  min/max width and equal stretches on both sides, so it stays centered
  while resizing with the window.

Both title bars override `canDrag()` so pressing on the embedded widget
(menu bar items, the search field) never starts a window drag.

`LaceStandardTitleBar` toggles maximization **synchronously** (via
`showMaximized()` / `showNormal()`).  This matters because qframelesswindow's
default double-click handler posts an async `WM_SYSCOMMAND SC_MAXIMIZE`, which
Windows ignores while the mouse button is still held down — a real
double-click dispatches `MouseButtonDblClick` while the second click's button
is still pressed, so the maximize silently failed (the "stale" double-click).
The synchronous toggle works regardless of the button state, and is also used
automatically on every frameless floating container.

Right-clicking the window **icon** opens the standard system menu
(Restore / Move / Size / Minimize / Maximize / Close).  On Windows this uses
the real system menu via `TrackPopupMenu` (so items are localized and
automatically enabled/disabled for the current window state); other platforms
fall back to an equivalent `QMenu`.  Creating a Lace frameless window also
calls `SetPreferredAppMode(AllowDark)` (uxtheme) so native menus follow the
system light/dark theme — dark when the OS is in dark mode, light when it is
in light mode.

### Chromeless Floating Windows

```python
# Enable frameless floating windows
# (DockFlags.chromeless_float hides the custom title bar entirely)
dock_manager.config_flags |= DockFlags.chromeless_float
```

---

## 10. Icons

### Setting Tab Icons

```python
from lace import get_icon_provider

# Initialize icon provider (once, with path to SVG icon directory)
get_icon_provider("/path/to/lace_icons")

# Set default icon (used when not using custom icons)
widget.set_default_icon_name("dock")

# Set custom icon (used when DockFlags.custom_tab_icons is enabled)
widget.set_custom_icon_name("pin")
widget.set_custom_icon(QIcon.fromTheme("my-icon"))  # or from file
```

### Available Icon Names

Look in your `lace/resources/lace_icons/` directory for available SVG icon names. Common ones: `dock`, `tab_list`, `pin`, `unpin`, `float`, `close`, `undock`, `maximize`, `minimize`, `restore`, etc.

---

## 11. Common Patterns

### Pattern 1: Standard IDE Layout

```python
# Center: code editor
editor = DockWidget("Code Editor", window)
editor.set_widget(QTextEdit())
dock_manager.add_dock_widget(DockWidgetArea.center, editor)

# Bottom: console/output as tab alongside editor
console = DockWidget("Console", window)
console.set_widget(QTextEdit())
dock_manager.add_dock_widget(DockWidgetArea.center, console)  # becomes tab

# Right: file explorer sidebar
explorer = DockWidget("Files", window)
explorer.set_features(DockWidgetFeature.pinnable)
dock_manager.add_sidebar_widget(DockWidgetArea.right, explorer)
```

### Pattern 2: Locked Dashboard

```python
# Create widgets that cannot be moved or closed
status_panel = DockWidget("Status", window)
status_panel.set_features(DockWidgetFeature.no_features)
status_panel.set_widget(QLabel("Permanently docked here"))
dock_manager.add_dock_widget(DockWidgetArea.left, status_panel)
```

### Pattern 3: Dynamic Widget Creation

```python
def create_new_tab(name, content_widget):
    widget = DockWidget(name, window)
    widget.set_features(DockWidgetFeature.all_features)
    widget.set_widget(content_widget)
    dock_manager.add_dock_widget(DockWidgetArea.center, widget)
    return widget

# Usage
create_new_tab("New File", QTextEdit())
```

### Pattern 4: Theme Switcher

```python
from lace import apply_dock_theme, ThemeManager

class ThemeSwitcher:
    def __init__(self, dock_manager):
        self.dock_manager = dock_manager
        self.theme_manager = ThemeManager(QApplication.instance())
        self.themes = [
            "default", "dark", "light", "midnight", "warm", "nordic",
            "monokai", "neutral", "tokyo_night", "catppuccin",
            "dracula", "solarized_dark", "solarized_light", "cyberpunk_neon"
        ]
        self.current = 0

    def next_theme(self):
        self.current = (self.current + 1) % len(self.themes)
        apply_dock_theme(self.themes[self.current])
        return self.themes[self.current]

    def toggle_auto(self):
        self.theme_manager.auto_mode_enabled = not self.theme_manager.auto_mode_enabled
```

---

## 12. API Quick Lookup

### DockManager

| Method | Description |
|---|---|
| `add_dock_widget(area, widget, target_area?)` | Add widget to a dock area |
| `add_sidebar_widget(area, widget)` | Pin widget to a sidebar |
| `remove_dock_widget(widget)` | Close/remove a dock widget |
| `find_dock_widget(name)` | Find widget by title |
| `dock_widgets()` | List all dock widgets |
| `dock_containers()` | List all container widgets (root + floating) |
| `save_layout_to_file(path, version?)` | Save layout to JSON file |
| `load_layout_from_file(path, version?)` | Load layout from JSON file |
| `save_state(version?)` | Serialize layout to JSON string |
| `restore_state(json, version)` | Restore layout from JSON string |
| `add_perspective(name)` | Save current layout as named perspective |
| `open_perspective(name)` | Load a named perspective |
| `remove_perspective(name)` | Delete a perspective |
| `perspective_names()` | List all perspective names |
| `view_menu` | QMenu with toggle actions for all dock widgets |
| `config_flags` | Get/set global configuration flags |
| `sidebar_focus_behavior` | Get/set sidebar focus behavior |
| `tab_badge_position` | Get/set default badge position |
| `set_active_dock_area(area)` | Set which dock area is visually focused |

### DockWidget

| Method | Description |
|---|---|
| `set_widget(widget, insert_mode?)` | Set the user content widget |
| `set_features(flags)` | Set interaction capabilities |
| `set_default_icon_name(name)` | Set default tab icon |
| `set_custom_icon_name(name)` | Set custom tab icon |
| `set_tab_tool_tip(text)` | Set tab tooltip |
| `toggle_view(open_)` | Show/hide widget |
| `is_closed()` | Check if widget is hidden |
| `dock_area_widget()` | Get parent dock area |
| `dock_container()` | Get parent container |
| `dock_manager()` | Get the DockManager instance |
| `widget_state()` | Get current state (docked/floating/pinned) |
| `set_widget_state(state)` | Set state manually |
| `toggle_view_action()` | Get QAction for menu/toolbar integration |
| `set_toggle_view_action_mode(mode)` | Set action mode (toggle/show) |
| `tool_bar()` | Get/set the dock widget's QToolBar |
| `set_toolbar_floating_style(floating)` | Style toolbar for floating vs docked |
| `save_state()` | Serialize widget state to dict |

### SidebarManager

| Method | Description |
|---|---|
| `add_sidebar(area)` | Create sidebar overlay at edge |
| `pin_widget(widget, sidebar?, area?)` | Pin widget to sidebar |
| `unpin_widget(widget, area?)` | Unpin widget back to main layout |
| `toggle_sidebar(area)` | Slide sidebar in/out |
| `focus_sidebar(area)` | Focus sidebar overlay |
| `update_badge(widget, value)` | Set badge on sidebar tab |
| `clear_badge(widget)` | Clear badge from sidebar tab |
| `save_state()` | Serialize sidebar state |
| `restore_state(dict)` | Restore sidebar state |

---

## 13. Signals

### DockManager Signals

| Signal | Args | Description |
|---|---|---|
| `perspective_list_changed` | — | Perspectives list was modified |
| `restoring_state` | — | Layout restore began |
| `state_restored` | — | Layout restore completed |
| `opening_perspective` | `(name)` | Opening a named perspective |
| `perspective_opened` | `(name)` | Perspective fully loaded |

### DockWidget Signals

| Signal | Args | Description |
|---|---|---|
| `view_toggled` | `(bool)` | Widget show/hide changed |
| `closed` | — | Widget was closed |
| `title_changed` | `(str)` | Tab title changed |
| `top_level_changed` | `(bool)` | Widget became/is no longer floating |
| `features_changed` | `(DockWidgetFeature)` | Widget features changed |

### SidebarManager Signals

| Signal | Args | Description |
|---|---|---|
| `sidebar_toggled` | `(area, bool)` | Sidebar slide in/out |
| `widget_unpinned` | — | Widget unpinned from sidebar |

---

## 14. Full Working Example

See `demos/demo_app.py` for a comprehensive example demonstrating:
- Multiple dock widgets with different feature flags
- Sidebar setup with badges
- Theme switching menu
- Global flags menu with live toggling
- Insertion order control
- Sidebar focus mode and badge position controls
- Preset configurations (Default, Minimal, Full)

```bash
python -m demos.demo_app
```

Frameless / custom-title-bar demos (see [§5 Frameless Windows & the Custom
Title Bar](#frameless-windows--the-custom-title-bar)):

```bash
python -m demos.demo_app_custom_titlebar.py          # standard custom title bar
python -m demos.demo_app_custom_titlebar_menus.py      # menu-embedded main title bar + search bar for floats
```
