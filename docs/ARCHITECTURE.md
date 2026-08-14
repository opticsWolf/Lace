# Lace Architecture Overview

**Advanced Docking System for PySide6** — a comprehensive, themeable, multi-window docking framework built on top of PySide6 (Qt6 via Python).

**Version:** 0.5.0

---

## 1. System Overview

Lace provides a complete docking system supporting:

- **Dock areas** — regions within a parent window where dock widgets can be placed (left, right, top, bottom, center)
- **Tabbed dock widgets** — multiple widgets can share a single dock area as tabs
- **Floating windows** — dock widgets can be detached into independent top-level windows
- **Auto-hide sidebars** — VS Code-style slide-out panels with tab buttons
- **Drag-and-drop layout** — intuitive resizing, reordering, and re-docking via overlays
- **Perspectives** — save/restore complete layout configurations
- **JSON serialization** — full layout persistence with atomic file I/O
- **Theming engine** — 14+ built-in themes with dynamic color computation and live switching
- **JSON theme files** — validated via Pydantic (`ThemeJson`), applied through the same engine as built-ins
- **Custom icon provider** — SVG-based icon system with theme-aware tinting

### High-Level Component Map

```
DockManager (facade)
├── DockContainerWidget (root + floating)
│   ├── DockSplitter (nested, orientation-aware)
│   │   └── DockSplitterHandle (themed resize handles)
│   └── DockAreaWidget (×N)
│       ├── DockAreaTitleBar
│       │   ├── DockAreaTabBar (scrollable tab strip)
│       │   │   └── DockWidgetTab (×N, painted chrome)
│       │   └── ChromeToolButton (×5: tabs menu, pin, maximize, undock, close)
│       └── DockAreaLayout (stacked widget container)
│           └── DockWidget (×N, one visible at a time)
│               ├── QToolBar (optional)
│               └── QScrollArea + user content widget
├── FloatingDockContainer (top-level window)
│   └── DockContainerWidget (nested)
│       └── (same structure as root)
├── SidebarManager
│   ├── SideTabBar (vertical tab strip per edge)
│   │   └── VerticalTabButton (×N, rotated text, badges)
│   └── SideBarContainer (auto-hide overlay panel)
│       └── SideBarTitleBar + user widget
├── LayoutSerializer
│   ├── LayoutStateBuilder (UI → dict)
│   ├── LayoutEngine (dict → UI)
│   └── LayoutPersistenceManager (atomic file I/O)
├── DockStyleManager (singleton, event-driven theme system)
├── DockThemeBridge (QPalette push to Qt children)
├── DockOverlay (×2: container + dock-area drop targets)
├── DockSignals (internal event bus)
├── ThemeJson / load_theme_json (Pydantic-validated JSON theme loading)
└── ThemeManager (OS-aware auto dark/light switching)
```

---

## 2. Core Module Reference

### 2.1 `dock_manager.py` — `DockManager` (Main Facade)

The central orchestrator. All public API flows through this class.

| Category | Members |
|---|---|
| **Signals** | `perspective_list_changed`, `perspectives_removed`, `restoring_state`, `state_restored`, `opening_perspective`, `perspective_opened` |
| **Core Docking** | `add_dock_widget(area, widget, target_area)`, `remove_dock_widget(widget)`, `find_dock_widget(name)` |
| **Sidebars** | `add_sidebar_widget(area, widget)`, `sidebar_focus_behavior` (prop), `tab_badge_position` (prop) |
| **State** | `save_state(version)`, `restore_state(json, version)`, `save_layout_to_file(path)`, `load_layout_from_file(path)` |
| **Themes** | `set_theme(name)` |
| **Perspectives** | `add_perspective(name)`, `remove_perspective(name)`, `perspective_names()`, `open_perspective(name)` |
| **Config** | `config_flags` (prop), `notify_config_flags_changed()` |
| **Overlays** | `container_overlay()`, `dock_area_overlay()` |
| **Containers** | `dock_containers()`, `register_floating_widget()`, `remove_floating_widget()` |
| **Floating icon** | `floating_window_icon` (prop), `set_floating_window_icon(icon)`, `resolve_floating_window_icon()` |
| **View Menu** | `view_menu`, `menu_insertion_order`, `add_toggle_view_action_to_menu(action, group)`, `_rebuild_view_menu()` |
| **Delegated (root)** | `root_container()`, `add_dock_area()`, `remove_dock_area()`, `dock_area(i)`, `dock_area_count()`, `opened_dock_areas()`, `dock_area_at(pos)`, `is_floating()`, `top_level_dock_area()`, `top_level_dock_widget()`, `dock_widgets()`, `features()`, `floating_widget()`, `close_other_areas(area)`, `refresh_style()`, `dump_layout()`, `root_splitter()`, `drop_floating_widget(fw, pos)` |
| **Internal** | `_handle_request_overlay_show()`, `_handle_request_overlay_hide()`, `_handle_floating_widget_dropped()`, `_on_app_focus_changed()`, `set_active_dock_area(area)`, `ensure_active_dock_area()` |

**Key private state:** `_floating_widgets`, `_containers`, `_dock_widgets_map`, `_perspectives`, `_config_flags`, `_root` (DockContainerWidget), `_serializer`, `_persistence`, `sidebar_manager`, `_theme_bridge`, `_view_menu`, `_dock_area_overlay`, `_container_overlay`, `signals` (DockSignals).

---

### 2.2 `dock_widget.py` — `DockWidget`

The user-facing widget wrapper. Each `DockWidget` owns a user `QWidget` and a `DockWidgetTab`.

| Category | Members |
|---|---|
| **Signals** | `view_toggled(bool)`, `closed()`, `title_changed(str)`, `top_level_changed(bool)`, `features_changed(DockWidgetFeature)` |
| **Content** | `set_widget(widget, insert_mode)`, `take_widget()`, `widget() → QWidget` |
| **Tab** | `tab_widget() → DockWidgetTab`, `set_icon(icon)`, `icon()`, `set_default_icon_name(name)`, `default_icon_name()`, `set_custom_icon(icon)`, `custom_icon()`, `set_custom_icon_name(name)`, `custom_icon_name()`, `set_tab_tool_tip(text)` |
| **Toolbar** | `tool_bar() → QToolBar`, `create_default_tool_bar()`, `set_tool_bar(toolbar)`, `set_tool_bar_style(style, state)`, `tool_bar_style(state)`, `set_tool_bar_icon_size(size, state)`, `tool_bar_icon_size(state)`, `set_toolbar_floating_style(floating)` |
| **Features** | `set_features(flags)`, `set_feature(flag, on)`, `features() → DockWidgetFeature`, `locked_to_area` (property to assign a named lock area) |
| **State** | `widget_state() → WidgetState`, `set_widget_state(state)`, `is_floating()`, `is_in_floating_container()`, `is_in_sidebar()`, `is_pinned()`, `is_closed()`, `toggle_view(open_)`, `toggle_view_internal(open_)` |
| **References** | `dock_manager()`, `dock_container() → DockContainerWidget`, `dock_area_widget() → DockAreaWidget` |
| **Toggle Action** | `toggle_view_action() → QAction`, `set_toggle_view_action_checked(checked)`, `set_toggle_view_action_mode(mode)` |
| **Styling** | `refresh_style()`, `paintEvent(event)`, `_update_bottom_mask()`, `_apply_bottom_mask()`, `on_style_changed(category, changes)`, `showEvent(event)` |
| **State Save** | `save_state() → dict` |
| **Assignment** | `flag_as_unassigned()` |
| **Top-level** | `emit_top_level_changed(floating)` |
| **Internal** | `_show_dock_widget()`, `_hide_dock_widget()`, `_update_parent_dock_area()`, `_setup_tool_bar()`, `_setup_scroll_area()` |

---

### 2.3 `dock_widget_tab.py` — `DockWidgetTab`

The painted-chrome tab button displayed in `DockAreaTabBar`.

| Category | Members |
|---|---|
| **Signals** | `active_tab_changed()`, `clicked()`, `close_requested()`, `close_other_tabs_requested()`, `moved(QPoint)` |
| **Icon/Text** | `set_icon(icon)`, `set_default_icon_name(name)`, `default_icon_name()`, `set_custom_icon(icon)`, `custom_icon()`, `set_custom_icon_name(name)`, `custom_icon_name()`, `update_icon()`, `icon() → QIcon`, `text()`, `set_text(title)` |
| **Active State** | `is_active_tab()`, `set_active_tab(active)`, `update_close_button_visibility()` |
| **Float** | `_floatable`, `on_detach_action_triggered()`, `_start_floating(drag_state)` |
| **Pin** | `_pinnable`, `_menu_is_pinned()` |
| **Movable** | `_movable` |
| **Config** | `_test_config_flag(flag)` |
| **Mouse** | `mousePressEvent()`, `mouseMoveEvent()`, `mouseReleaseEvent()`, `mouseDoubleClickEvent()` |
| **Menu** | `contextMenuEvent()`, `build_dock_menu(menu, tab_bar)`, `dispatch_dock_action(action)`, `_gather_menu_context(tab_bar)`, `_menu_is_floating()`, `_menu_has_sidebars()` |
| **MenuActionTarget** | `menu_target_widget()`, `menu_pin_target()`, `menu_unpin_target()`, `menu_pin_all_target()`, `menu_float_target()`, `menu_dock_target()`, `menu_close_target()`, `menu_close_others_target()`, `menu_maximize_target()` |
| **Styling** | `refresh_style()`, `paintEvent(event)`, `enterEvent()`, `leaveEvent()` |
| **References** | `dock_widget() → DockWidget`, `set_dock_area_widget(area)`, `dock_area_widget() → DockAreaWidget` |
| **Closable** | `is_closable()` |

---

### 2.4 `dock_container_widget.py` — `DockContainerWidget`

Represents a layout container — either the root (embedded in QMainWindow) or a floating window.

| Category | Members |
|---|---|
| **Signals** | `dock_areas_added()`, `dock_areas_removed()`, `dock_area_view_toggled(DockAreaWidget, bool)` |
| **Root** | `create_root_splitter()`, `root_splitter() → DockSplitter` |
| **Docking** | `add_dock_widget(area, widget, target_area)`, `remove_dock_widget(widget)`, `add_dock_area(area_widget, area, target_area)`, `remove_dock_area(area)` — clears maximized state if removed area was the maximized one |
| **Drop** | `drop_floating_widget(floating_widget, pos)`, `_drop_into_container()`, `_drop_into_section()`, `_drop_into_center_of_section()` |
| **Areas** | `dock_area(i)`, `dock_area_count()`, `opened_dock_areas()`, `dock_area_at(pos)`, `visible_dock_area_count()`, `last_added_dock_area_widget(area)` |
| **Top-level** | `has_top_level_dock_widget()`, `top_level_dock_widget()`, `top_level_dock_area()`, `is_floating()`, `floating_widget() → FloatingDockContainer` |
| **Widgets** | `dock_widgets() → list`, `features() → DockWidgetFeature` |
| **Maximize** | `is_area_maximized(area)`, `toggle_maximize_dock_area(area)`, `_restore_maximized_area()`, `_maximize_splitter(splitter, area) → bool`, `_collect_splitter_sizes(splitter)`, `_all_splitters() → generator` (recursive helpers for nested-splitter tree) |
| **State** | `_maximized_dock_area`, `_pre_maximize_splitter_sizes` (dict: `{id(splitter): sizes_list}`) |
| **Z-order** | `z_order_index()`, `is_in_front_of(other)` |
| **Splitter** | `_new_splitter(orientation)` |
| **Styling** | `refresh_style()` |
| **Debug** | `dump_layout()` |
| **Internal** | `_append_dock_areas()`, `_add_dock_area()`, `_emit_dock_areas_added()`, `_emit_dock_areas_removed()`, `_on_dock_area_view_toggled()` |

**DropController** (inner class): `drop_floating_widget()`, `_drop_into_container()`, `_drop_into_section()`, `_drop_into_center_of_section()`, `_resolve_section_insertion()`, `_insert_into_section_splitter()`.

---

### 2.5 `dock_area_widget.py` — `DockAreaWidget`

A single tabbed region within a `DockContainerWidget`.

| Category | Members |
|---|---|
| **Signals** | `tab_bar_clicked(int)`, `current_changing(int)`, `current_changed(int)`, `view_toggled(bool)` |
| **Tabs** | `dock_widgets()`, `dock_widgets_count()`, `open_dock_widgets_count()`, `opened_dock_widgets()`, `dock_widget(i)`, `current_index()`, `current_dock_widget()`, `set_current_index(i)`, `set_current_dock_widget(widget)`, `internal_set_current_dock_widget(widget)`, `index(widget)`, `index_of_first_open_dock_widget()`, `next_open_dock_widget(widget)`, `reorder_dock_widget(from, to)` |
| **Insertion** | `insert_dock_widget(index, widget, activate)`, `add_dock_widget(widget)`, `remove_dock_widget(widget)`, `toggle_dock_widget_view(widget, open_)` |
| **View** | `toggle_view(open_)`, `hide_area_with_no_visible_content()`, `ensure_title_bar_visible()` |
| **Title bar** | `title_bar_geometry()`, `content_area_geometry()`, `title_bar_button(which) → QAbstractButton`, `update_title_bar_button_states()`, `_update_title_bar_button_states()`, `mark_title_bar_menu_outdated()` |
| **Features** | `closable`, `movable`, `floatable`, `pinnable`, `features() → DockWidgetFeature`, `locked_name` (property to assign a named lock) |
| **Maximize** | `is_maximized()`, `toggle_maximize()` |
| **Close** | `close_area()`, `close_other_areas()`, `on_tab_close_requested(index)` |
| **State** | `save_state() → dict` |
| **Reference** | `dock_manager() → DockManager`, `dock_container() → DockContainerWidget` |
| **Styling** | `refresh_style()` |
| **Focus** | `set_chrome_focused(focused)`, `_on_app_focus_changed(old, new)`, `mousePressEvent()` |

---

### 2.6 `dock_splitter.py` — `DockSplitter` + `DockSplitterHandle`

| Class | Members |
|---|---|
| **DockSplitter** | `createHandle() → DockSplitterHandle`, `has_visible_content() → bool` |
| **DockSplitterHandle** | `refresh_style()`, `enterEvent()`, `leaveEvent()`, `sizeHint() → QSize`, `paintEvent(event)` — properties: `_c_handle`, `_c_hover`, `_handle_width`, `_total_width`, `_handle_margin`, `_is_hovered` |

---

### 2.7 Floating containers — `floating_behaviour.py`, `floating_dock_container.py`

Top-level windows for detached dock content. There are two, differing only in
window chrome: `FloatingDockContainer` on a native OS frame, and
`FramelessFloatingDockContainer` (§2.11) with a custom title bar. Everything
downstream of the chrome is shared, in `FloatingContainerBehaviour`.

Until 0.5.50 both classes were called `FloatingDockContainer` and carried ~900
duplicated lines, so every drag/drop/resize/lifecycle fix had to land twice —
and when one didn't, the two window modes diverged silently.

#### `FloatingContainerBehaviour` (`floating_behaviour.py`)

A plain mixin, listed **before** the Qt base in both subclasses: it overrides
`closeEvent`, `resizeEvent`, `hideEvent` and `deleteLater`, which QWidget also
defines, so listed after the Qt base Qt's versions would win. It defines no
`__init__`, so `super().__init__(parent)` in a subclass still reaches Qt.

| Category | Members |
|---|---|
| **Drag lifecycle** | `start_dragging(pos, size, handler)`, `init_floating_geometry(pos, size)`, `move_floating()`, `_end_programmatic_drag()`, `_finalize_drag()`, `_activate_window()`, `_is_movable()`, `_update_drop_overlays(pos)`, `_set_state(state)`, `_clear_synthetic_release_flag()` |
| **Chromeless resize** | `_handle_resize_event(obj, event)`, `_hit_test_edges(pos)`, `_cursor_for_edge(edge)`, `_apply_resize(pos)`, `_child_has_grab_mouse()`, `_is_our_widget(obj)`, `_update_chromeless_mask()` |
| **State** | `restore_state(state, testing)`, `update_window_title()`, `dock_container() → DockContainerWidget`, `has_top_level_dock_widget()`, `top_level_dock_widget()`, `dock_widgets()`, `is_closable()` — all four accessors return a neutral value once `_destroyed()` has cleared the container |
| **Title** | `on_dock_areas_added_or_removed()`, `on_dock_area_current_changed(index)`, `_set_window_title(text)` |
| **Qt events** | `closeEvent()`, `hideEvent()`, `resizeEvent()`, `deleteLater()` |
| **Styling** | `refresh_style()` |
| **Subclass hook** | `_on_dock_areas_changed()` — no-op by default; the frameless container re-evaluates its custom close button here |

Subclasses supply the chrome-dependent half: `__init__`, `event()`,
`eventFilter()`, `moveEvent()`, `changeEvent()`, `start_floating()`,
`update_window_flags_from_config()`, `_do_restore_geometry()`,
`_end_swallowed_release()` and the permanent-filter install/remove pair.

#### `FloatingDockContainer` (`floating_dock_container.py`)

The native-frame variant. Adds `_apply_dock_palette_to_window()` and
`_apply_dwm_dark_frame(is_dark)`: `setWindowFlags()` recreates the native
handle without the DWM dark-mode attribute, so the title bar would come back
light on a dark theme.

| Category | Members |
|---|---|
| **Icon** | Window icon resolved at construction via `DockManager.resolve_floating_window_icon()` — dedicated `set_floating_window_icon()` icon, else application / root-window icon (shared by the frameless variant) |

#### Identifying a float

`isinstance(x, lace.FloatingDockContainer)` is **wrong** — it is False for
every float in custom-titlebar mode. Use `lace.is_floating_dock_container(x)`
or `lace.find_floating_dock_container(widget)`, which test against the mixin
and cost no import of the optional `qframelesswindow`.

---

### 2.8 `dock_overlay.py` — `DockOverlay` + `DockOverlayCross`

Visual drop-target overlays during drag-and-drop.

| Class | Members |
|---|---|
| **DockOverlay** | `show_overlay(target) → DockWidgetArea`, `hide_overlay()`, `set_allowed_areas(areas)`, `allowed_areas() → DockWidgetArea`, `drop_area_under_cursor() → DockWidgetArea`, `enable_drop_preview(enable)`, `drop_overlay_rect() → QRect`, `mode → OverlayMode`, `cross → DockOverlayCross`, `refresh_style()`, `paintEvent(e)` |
| **DockOverlayCross** | `setup_overlay_cross(mode)`, `update_overlay_icons()`, `reset()`, `update_position()`, `cursor_location() → DockWidgetArea`, `set_area_widgets(widgets)`, `reset()` |

---

### 2.9 `dock_chrome.py` — Chrome primitives

| Class/Function | Description |
|---|---|
| **DragDetector** | QObject event filter that emits `drag_started` when mouse moves past threshold without consuming events |
| **ChromeToolButton** | QToolButton with painted rounded hover background; `set_hover_chrome(bg, radius)`, `set_hovered(on)`, `paintEvent()` |
| **ChromeFrame** | QFrame with painted rounded/outlined panel; `set_chrome(tokens)`, `set_chrome_focused(on)`, `chrome() → ChromeTokens`, `paintEvent()` |
| **style_title_bar_buttons(buttons, …)** | Applies shared sizing + painted hover to a list of QAbstractButton instances |
| **_contrast_step(color, amount)** | Shifts color lightness in the contrasting direction |

---

### 2.10 `dock_paint.py` — Painting primitives

| Function | Description |
|---|---|
| `chrome_content_margin(border_width, radius) → int` | Inset to keep children clear of border + corner arcs |
| `tab_path(rect, radius, flat_edge, closed) → QPainterPath` | General tab shape: the two corners on `flat_edge` stay square, the rest follow `radius`; `flat_edge=None` rounds all four, `closed=False` omits the segment along the flat edge |
| `top_rounded_path(rect, radius) → QPainterPath` | Path with only top corners rounded (`tab_path` with a flat bottom) |
| `top_open_path(rect, radius) → QPainterPath` | The same, minus its bottom segment (`closed=False`) |
| `bottom_rounded_path(rect, radius) → QPainterPath` | Path with only bottom corners rounded (`tab_path` with a flat top) |
| `ChromeTokens(bg, border, border_width, radius, focus_border)` | Frozen dataclass; `content_margin()` method |
| `paint_panel(p, rect, c, focused)` | Core panel painter: fill + outline + focus swap, driven by a `ChromeTokens` bundle (`paint_panel_bg` / `paint_panel_border` split) |
| `paint_tab(p, rect, *, bg, bg_gradient, radius, indicator, indicator_width, indicator_edge, border, border_width, flat_edge, border_closed)` | Tab painter (keyword-only) with optional indicator strip and outline; `indicator_edge` / `flat_edge` are `Qt.Edge` values. The outline skips the flat edge unless `border_closed` |
| `create_high_dpi_drop_indicator_pixmap(size, area, mode, colors, dpr) → QPixmap` | Drop-zone icon painter |

---

### 2.11 Frameless windows (`frameless_window.py`, `frameless_titlebar.py`, `floating_dock_container_frameless.py`)

When `TitleBarMode.custom` is active, the main window and every floating
container are driven by [PySideSix-Frameless-Window](https://github.com/zhiyiYo/PyQt-Frameless-Window)
(`qframelesswindow`), which provides the frameless chrome (custom title bar,
resize borders, DWM shadow) on Windows, macOS and Linux.

| Class / Module | Description |
|---|---|
| **`FramelessLaceMainWindow`** (`frameless_window.py`) | Frameless `QMainWindow` subclass; integrates the custom title bar into the `QMainWindow` layout (`setMenuWidget`) so the central widget sits below it, with an optional stacked menu bar (`menuBar()`). Accepts a `title_bar=` descriptor (`None`, a `QWidget` instance, a subclass, or a callable factory) so applications can swap in custom title-bar chrome; `TitleBarDescriptor` / `_resolve_title_bar()` implement the resolution. |
| **`FramelessLaceWindow`** (`frameless_window.py`) | Frameless top-level `QWidget` base for floating dock containers. Accepts the same `title_bar=` descriptor as the main window. |
| **`DockManager`** (`dock_manager.py`) | Exposes `main_title_bar` / `floating_title_bar` descriptors plus `create_main_title_bar(parent)` / `create_floating_title_bar(parent)` factories, so the main window and every floating container can use different custom title-bar classes. `floating_title_bar` is consumed by `FramelessFloatingDockContainer` when no explicit title bar is passed. |
| **`LaceStandardTitleBar`** (`frameless_window.py`) | `StandardTitleBar` whose double-click-to-maximize is **synchronous**. qframelesswindow's default handler posts an async `WM_SYSCOMMAND SC_MAXIMIZE/SC_RESTORE`, which Windows ignores while a mouse button is still held down — and a real double-click dispatches `MouseButtonDblClick` while the second click's button is still pressed — so the maximize silently failed (the "stale" double-click). Using `showMaximized()`/`showNormal()` directly takes effect regardless of the button state. Right-clicking the window icon opens the standard system menu (native `TrackPopupMenu` on Windows, `QMenu` fallback elsewhere); creating a Lace frameless window opts the process into system dark mode (`SetPreferredAppMode(AllowDark)`) so native menus follow the OS light/dark theme. Installed automatically on every frameless floating container; the frameless demo main window uses it too. |
| **`FramelessTitleBarStyler`** (`frameless_titlebar.py`) | Theme bridge for the custom title bar: subscribes to `DockStyleManager` and applies dock-theme colours (background, title text, min/max/close button colours) to the title bar and optional menu bar(s). Supports multiple menu bars via `add_menu_bar()` / `remove_menu_bar()` — e.g. a menu bar embedded inside a custom title-bar layout plus a separate stacked `menuBar()`. |
| **`FramelessFloatingDockContainer`** (`floating_dock_container_frameless.py`) | Frameless floating container. Routes title-bar drags through `_handle_titlebar_drag()` so the drop overlay / re-dock machinery works with the custom title bar: on Windows the press is let through to the title bar (the native move loop starts only once the drag threshold is exceeded), `MouseButtonDblClick` cancels any pending drag, and the dock-drag state machine is kept free of stale grabs/filters. Uses `DockManager.floating_title_bar` to resolve its title bar when no explicit one is passed, so floating windows can have different chrome than the main window. |
| **`FloatingDockContainer`** (`floating_dock_container.py`) | Native (OS title-bar) floating container. Both variants share `FloatingContainerBehaviour` (§2.7), so the drag-state machinery — including the swallowed-release discrimination — has one implementation. The module keeps `FloatingDockContainer` as a deprecated alias for the frameless class, which bore that name until 0.5.50. |

---

## 3. Theming System

### 3.1 `dock_theme.py` — Theme definitions & color math

| Class | Description |
|---|---|
| **DockStyleCategory** (enum) | `CORE`, `PANEL`, `TAB`, `TITLE_BAR`, `SIDEBAR`, `SIDEPANEL`, `SPLITTER`, `OVERLAY` |
| **_FontFields** (dataclass) | Shared typography: `font_family`, `font_size`, `font_weight`, `font_italic`, `font_underline` |
| **DockCoreStyleSchema** | canvas_bg, border_color, accent_color, focus_border_color, status colors, geometry (border_width, corner_radius, margin, padding), text colors |
| **DockPanelStyleSchema** | bg_normal, text_color, input_bg, alternate_base, button_bg, 3D colors (light/mid/dark/shadow), geometry |
| **DockTabStyleSchema** | bg_normal/hover/active, border, geometry, text_normal/active, active_font_weight, indicator_color/width/position, close_btn_* |
| **_ActionButtonFields** | button_color/disabled/hover_bg, corner_radius, padding, expand_vertical, size, icon_size |
| **DockTitleBarStyleSchema** | Inherits _ActionButtonFields + _FontFields; bg_normal/active, active_edge, geometry, text, button_spacing |
| **DockSidebarStyleSchema** | width, bg/border, tab backgrounds, tab geometry/typography, indicator, badge |
| **DockSidePanelStyleSchema** | bg_normal, geometry, title text/font, button settings, shadow |
| **DockSplitterStyleSchema** | handle_color/h_hover_color, handle_width, total_width, handle_margin |
| **DockOverlayStyleSchema** | frame_color, background_color, overlay_color, arrow_color, shadow_color |
| **ThemeSpec** (frozen dataclass) | Declarative 3-5 color theme with geometrical tokens; see §3.2 below |
| **build_theme(spec) → dict** | Public API: builds full theme dict from ThemeSpec |
| **_build_theme(…)** | Internal: derives all category dicts from base/accent/text + status colors |
| **_adjust_color(col, l_off, s_off, h_off, a_off)** | HSL color manipulation |
| **_contrasting_hover(col, amount)** | Hover color that always contrasts with container |
| **BASE_DOCK_DEFAULTS** | Default "VS Code 2026 Dark" theme |
| **to_qcolor(val) → QColor** | Converts list/hex/string to QColor |
| **qcolor_to_list(c) → list** | Inverse |
| **is_color_list(val) → bool** | Type guard |
| **deep_to_qcolor(value)** | Recursive list→QColor conversion |
| **deep_to_serializable(value)** | Recursive QColor→list conversion |
| **DockThemeColors** (frozen dataclass) | All resolved colors for palette construction |
| **resolve_dock_colors() → DockThemeColors** | Cached resolution from DockStyleManager |
| **_resolve_uncached(sm) → DockThemeColors** | Full resolution logic |
| **_apply_shared_roles(pal, c)** | Applies shared palette roles |
| **build_dock_palette(is_panel, base_palette, colors) → QPalette** | Constructs QPalette from resolved colors |
| **_get_contrasting_text_color(col) → QColor** | Luminance-based white/dark text |

### 3.2 `dock_theme.py` — ThemeSpec & Geometrical Tokens

`ThemeSpec` is a frozen dataclass that accepts color palettes (list or `QColor`) alongside optional geometrical and status tokens:

| Field | Type | Description |
|---|---|---|
| `base` | `QColor` / `List[int]` | Primary canvas/background color |
| `accent` | `QColor` / `List[int]` | Accent/highlight color |
| `text` | `QColor` / `List[int]` | Default text color |
| `surface` | `QColor` / `List[int]` | Inner panel/card surface color |
| `border` | `QColor` / `List[int]` | Card outline color (used as `_focus_border` when set) |
| `is_light` | `bool` | Light-mode flag; controls unfocused border derivation |
| `title_mode` | `str` | `"darker"` or `"lighter"` — title bar mode relative to panel |
| `hover_mode` | `str` | `"darker"` or `"lighter"` — tab hover mode relative to panel |
| `success_color` | `QColor` / `List[int]` | Status: success/green |
| `warning_color` | `QColor` / `List[int]` | Status: warning/yellow |
| `error_color` | `QColor` / `List[int]` | Status: error/red |
| `info_color` | `QColor` / `List[int]` | Status: info/cyan |
| `tooltip_bg` | `QColor` / `List[int]` | Tooltip background (`QToolTip` palette); derived from panel when unset |
| `tooltip_text` | `QColor` / `List[int]` | Tooltip text color; defaults to full-strength `text` |
| `corner_radius` | `int` | Rounded corner radius for dock cards |
| `border_width` | `float` | Stroke width for card outlines |
| `title_height` | `int` | Height of the title bar |
| `title_padding_left` | `int` | Left padding of title bar content |
| `title_padding_right` | `int` | Right padding of title bar content |
| `title_button_spacing` | `int` | Spacing between title bar action buttons |
| `title_margin` | `int` | Inset around title bar (0 = flush against outer card edges) |
| `title_border_width` | `float` | Full outline stroke around title bar |
| `title_border_bottom` | `float` | Divider stroke underneath title bar |
| `title_border_color` | `QColor` / `List[int]` | Color for title bar borders |
| `tab_radius` | `int` | Rounded corner radius for tabs |
| `tab_margin` | `int` | Gap between adjacent tabs |
| `content_margin` | `int` / `float` / `List[int]` / `Tuple[int, ...]` | Margin around widget content; single value = all sides, two values = `(left/right/bottom, top)` |
| `tab_dimming` | `bool` | Enable dimming for active tabs in unfocused/inactive dock areas |
| `indicator_width` | `int` | Thickness (in pixels) of the tab selection highlight stripe |
| `indicator_position` | `str` / `List[str]` / `Tuple[str, ...]` | Active tab highlight stripe edge(s) (`"none"`, `"top"`, `"bottom"`, `"left"`, `"right"`, or combination/list) |
| `sidebar_tab_flat_edge` | `str` | Which edge of a sidebar tab stays square: `"outward"` (the window edge its bar runs along), `"inward"` (facing the docked content), `"none"` (all four corners rounded), or `"all"` (the default — a plain rectangle) |
| `sidebar_tab_radius` | `int` | Radius for those rounded corners; omitted, sidebar tabs take `tab_radius` |
| `sidebar_tab_bg_normal` | `QColor` / `List[int]` | Fill behind an **inactive** sidebar tab. Transparent in every shipped theme, which is why an idle tab shows only its label; set it and every tab carries a background, not just the active and hovered ones. The accent at a low alpha gives a tint of the highlight colour rather than a slab of it |
| `sidebar_tab_bg_hover_start` / `_end` | `QColor` / `List[int]` | The hovered tab's horizontal gradient. Derived from the base when unset, which carries no accent — see the note under *Sidebar tabs* on why that caps `sidebar_tab_bg_normal` |
| `sidebar_tab_bg_active` | `QColor` / `List[int]` | The selected tab's fill (the panel colour when unset) |
| `sidebar_tab_border_width` | `float` | Sidebar tab outline width; 0 (default) draws none |
| `sidebar_tab_border_color` | `QColor` / `List[int]` | Outline colour for inactive sidebar tabs; transparent outlines only the active one |
| `sidebar_tab_border_active_color` | `QColor` / `List[int]` | Outline colour for the active sidebar tab (defaults to the accent) |
| `sidebar_tab_border_hover_color` | `QColor` / `List[int]` | Outline colour for a hovered, inactive tab. *Unset* — unlike the pair above, which are seeded — means hover is not a state of its own and keeps the inactive outline; set it, with the inactive one transparent, and the outline becomes the hover cue |
| `sidebar_tab_border_closed` | `bool` | Close the outline across the flat edge instead of leaving it open |
| `sidebar_indicator_width` | `float` | Thickness of the sidebar tab's highlight stripe. Give it the outline's width: the strip sits *on* one of the outline's edges and is painted under it, so a wider one sticks out inside the tab and steps that edge |
| `sidebar_indicator_position` | `str` | Which edge it hugs: `"left"` (window-facing) or `"right"` (content-facing), mirrored per sidebar |

### 3.3 Titlebar Flushness & Borders

When a dock card (`DockAreaWidget`) has rounded corners (`corner_radius`) and an outer `border_width`, the outer card layout applies an inset (`chrome_content_margin`) to its children by default (`4px` in Cyberpunk Neon, `1px` in standard themes) so that square inner children stay inside the curve. This produces a `1-4px` ring of the panel background (`surface`) surrounding the title bar (`DockAreaTitleBar`).

`ThemeSpec` provides full control:
- **`title_margin`**: Inset around top, left, right of `DockAreaTitleBar`. Set `title_margin = 0` for a **100% flush** title bar — `DockAreaTitleBar` automatically takes the outer `corner_radius` for its top corners, perfectly following the outer card contour without double-padding. Set `title_margin = 2` (or `3`) to create a concentric border.
- **`title_border_bottom`**: Draws a crisp divider line (`QPen`) across the bottom edge of `DockAreaTitleBar` (`title_border_color` controls its color).
- **`title_border_width`**: Draws a full outline stroke around `DockAreaTitleBar`.

### 3.4 Titlebar Spacing

By default, `DockTitleBarStyleSchema.padding_left` is `0` (with fallback to `0` in `DockAreaTitleBar.refresh_style()`). This ensures the leftmost tab (`DockWidgetTab`) aligns flush against the inner card border. Because `DockAreaTitleBar` is nested inside `DockAreaWidget` with a `chrome_content_margin` inset (`2px`), `pad_left = 0` eliminates double-padding and produces a clean visual hierarchy.

### 3.5 Dynamic Content Margin

`DockWidget.refresh_style()` parses `content_margin` from `DockStyleCategory.PANEL` using two modes:
1. **Single Value** (e.g. `content_margin = 6`): Applies equally to all four sides (`left=6, top=6, right=6, bottom=6`).
2. **Two Values** (e.g. `content_margin = (8, 2)`): The first value (`8`) applies to `left`, `right`, and `bottom`. The second value (`2`) controls the `top` margin immediately beneath the titlebar, enabling tight integration without visual gaps or double borders.

### 3.6 Reactive Border Colors

Card borders (`border_width`) on `DockAreaWidget` panels (`ChromeFrame`) are **reactive to focus**:

1. **Focused** (`_chrome_focused = True`): Only the active dock area displays the vibrant `focus_border_color` (`_focus_border`). If `ThemeSpec.border` is explicitly defined it is used as the high-visibility active outline; otherwise `_accent_bright` is used automatically.
2. **Unfocused** (`_chrome_focused = False`): All inactive dock areas display a calm, neutral border (`border_color` → `_neutral_border`) derived automatically from the inner card surface (`_panel`) or base canvas (`base`):
   - **Dark Themes** (`is_light = False`): Stepped slightly lighter (`+0.08`) than the dark panel surface.
   - **Light Themes** (`is_light = True`): Stepped slightly darker (`-0.12`) than the light panel surface.
3. **Focus Coordination**: `DockManager.set_active_dock_area(area)` acts as the global coordinator — it calls `set_chrome_focused(True)` on the active area and `set_chrome_focused(False)` on the previously active area whenever any child widget gains keyboard focus (`qapp.focusChanged`), when a tab is selected (`set_current_index`), or upon mouse interaction (`mousePressEvent`).

### 3.7 Example Theme: Cyberpunk Neon

The `cyberpunk_neon` preset demonstrates the full range of both color and geometrical tokens:

```python
"cyberpunk_neon": ThemeSpec(
    base       = [14, 11, 28, 255],     # Deep cyber indigo
    accent     = [255, 0, 127, 255],    # Electric neon pink
    text       = [245, 245, 255, 255],  # Crisp white text
    surface    = [24, 19, 44, 255],     # Rich violet inner panel
    border     = [0, 240, 255, 255],    # Glowing cyan structural border
    title_mode = "darker",              # Recessed dark indigo header
    hover_mode = "lighter",             # Tabs highlight brightly on hover
    success_color = [57, 255, 20, 255], # Neon green
    warning_color = [255, 215, 0, 255], # Cyber gold
    error_color   = [255, 42, 109, 255],# Neon red
    info_color    = [5, 217, 232, 255], # Cyan
    corner_radius = 10,                 # Distinct rounded card corners
    border_width = 1.5,                 # Visible glowing 1.5px cyan outline
    title_height = 32,                  # Roomy 32px title bar height
    title_padding_left = 0,             # Leftmost tabs sit flush against left edge
    title_padding_right = 8,            # 8px padding on right side
    title_button_spacing = 6,           # 6px spacing between action buttons
    tab_radius = 8,                     # 8px rounded top corners on tabs
    tab_margin = 3,                     # 3px gap separating adjacent tabs
    content_margin = (8, 2),            # 8px left/right/bottom, tight 2px top gap under title bar
)
```

### 3.8 Architectural Flow

```
[ThemeSpec in dock_custom_theme.py]
              │
              ▼
   [build_theme() / _build_theme()]
   ├── _neutral_border (unfocused, derived by light/dark contrast)
   └── _focus_border   (focused, explicit spec.border or accent)
              │
              ▼
  [Dict of DockStyleCategory schemas]
   ├── CORE      ──> [ChromeTokens(border=_neutral_border, focus_border=_focus_border)]
   │                   │
   │                   ▼
   │              [DockManager.set_active_dock_area(area)]
   │              swaps outline dynamically on focus / tab selection
   │
   ├── TITLE_BAR ──> [DockAreaTitleBar (height, pad_left=0, button_spacing)]
   ├── TAB       ──> [DockWidgetTab (corner_radius, margin)]
   └── PANEL     ──> [DockWidget (content_margin -> setContentsMargins)]
```

### 3.9 `dock_custom_theme.py` — Theme presets

| Theme | Description |
|---|---|
| `dark` | Recessed headers, clean contrast |
| `light` | High clarity, professional light gray |
| `midnight` | OLED-friendly, ultra-high contrast |
| `warm` | Organic, cozy tones |
| `nordic` | Frosty and crisp |
| `monokai` | Classic dev look |
| `neutral` | Silver workstation |
| `tokyo_night` | Clean neon-accented dark |
| `catppuccin` | Soothing pastel dark |
| `dracula` | High-contrast dark with purple |
| `solarized_dark` | Teal/cyan dark palette |
| `solarized_light` | Warm cream light palette |
| `cyberpunk_neon` | Vibrant, ultra-contrasty; sidebar tabs ringed on all four corners, active only (reference preset for `sidebar_tab_flat_edge`) |
| `cyberpunk_edge` | Amber/violet "night city"; focus-reactive rule under the tab bar (reference preset for `title_border_bottom`); same sidebar ring as `cyberpunk_neon` but on **every** tab — violet inactive, amber active |
| `slate_amber` | Light industrial grey + burnt amber (`neutral` × `cyberpunk_edge`); the bottom rule on a light palette |
| `neon_dusk` | Indigo + neon pink (`dracula` × `cyberpunk_neon`); every tab outlined, no card outline (reference preset for `tab_border_width`) |
| `violet_haze` | Dracula palette, `cyberpunk_edge` geometry; both tab states outlined; area outline limited to three sides (reference preset for `border_below_title`) |
| `midnight_haze` | `violet_haze` × `midnight`: violet_haze's geometry over a near-black base. Only the focused area's active tab is outlined — everything else is drawn without a line (reference preset for `tab_border_unfocused_color`); its sidebar follows the same rule, ringing the active tab only |

All stored in `THEME_SPECS` dict and built into `DOCK_THEMES` via `build_theme()`.

#### Tab edge treatments

Two independent ways to draw a tab's edge, usable separately or together. The last three
presets above demonstrate the range.

| | Token | Where the line runs | Which tabs |
|---|---|---|---|
| Rule | `title_border_bottom` | under the whole strip, horizontally | inactive; the active tab breaks it |
| Outline | `tab_border_width` | around each tab: left, top, right — never the bottom | whichever of `tab_border_color` / `tab_border_active_color` / `tab_border_unfocused_color` applies, when opaque |

#### Sidebar tabs

The vertical auto-hide tabs take the same treatment through their own `sidebar_*` tokens,
with one difference: the edge a sidebar tab is *joined along* is not the bottom but the side
facing its bar's window edge. `sidebar_tab_flat_edge` names it — `"outward"` (window-facing,
so left in a left sidebar and right in a right one), `"inward"` (facing the docked content),
`"none"` for a tab rounded on all four corners, or `"all"`, the default, which keeps every
corner square. The radius follows `tab_radius` unless `sidebar_tab_radius` pins it, so the
two kinds of tab are rounded alike.

`sidebar_tab_border_width` outlines the tab, and by default leaves the flat edge open the way
a dock tab's open bottom joins it to the panel below; `sidebar_tab_border_closed` runs the
line the whole way round instead. With all four corners rounded there is no edge left to
open, so the outline is always closed there.

Four presets ship this treatment, all on the same geometry —
`sidebar_tab_flat_edge = "none"`, so each tab is a closed rounded ring — and differing only
in which states are ringed at all:

| Preset | Inactive | Hovered | Active |
|---|---|---|---|
| `cyberpunk_neon` | bare (`sidebar_tab_border_color` transparent) | — | focus cyan, 2.0 |
| `cyberpunk_edge` | muted violet | — | amber, 1.5 |
| `midnight_haze` | bare | — | accent, 2.0 |
| `violet_haze` | bare | accent at alpha 130 | accent, 2.0 |

`violet_haze` is the only one whose ring is a *hover* cue: the tab is bare when idle, ringed
in a half-alpha accent under the cursor, and ringed solid when selected — so the hover ring
reads as the active one previewed. `sidebar_tab_border_hover_color` is what buys that, and it
is deliberately not seeded: unset, hover keeps the inactive outline, which is what the three
presets above (and every theme predating the token) expect.

`cyberpunk_edge` is the one that rings both states, mirroring what it already does with its
card outline and its bottom rule. `midnight_haze` follows its own rule instead — one place
for the eye to land — so its sidebar rings the active tab and draws no *line* anywhere else;
it is also the one preset that fills its inactive tabs, tinting them with the accent
(`sidebar_tab_bg_normal`) so the column reads as one family while the ring alone says which
tab is selected.

That tint has a ceiling, and a lower one than it looks. A *derived* hover comes off the base
and carries no accent, so it sits at a fixed luminance however deep the tint goes: in
`midnight_haze` an idle tab crosses it just past alpha 40, and beyond that an idle tab
out-glows a hovered one. 30 keeps a clear margin.

The ceiling is the derived hover's, not the feature's. The sidebar tab's fill is a
three-state set — `sidebar_tab_bg_normal`, the `sidebar_tab_bg_hover_start` / `_end`
gradient, and `sidebar_tab_bg_active` — and all three are themeable. Give hover the accent
too and it rises with the tint, so a deeper `bg_normal` stays legible; leave it derived and
alpha ~40 is the practical limit.

All three pin `sidebar_indicator_width` to the ring's width. The strip shares the ring's
content-facing edge and is painted *under* it, so at equal widths the ring covers it and the
tab is one clean line; left at the 3px default it stuck out inside the ring — a pink sliver
against neon's cyan, and doubled amber in edge.

Together they close the inactive tabs on all four sides while the active tab keeps its open
bottom, which is what makes it read as a notch cut out of the strip. Give them the **same
width**: the active tab's outline continues the rule around it, so a mismatch steps the line
where they meet. `neon_dusk`, `violet_haze` and `midnight_haze` pair them this way.

The active tab's break in the rule is **painted**, in the tab's own background, rather than
left to the tab's fill to cover: the strip and the tab are different widgets, and at a
fractional pen width or on a scaled display they round onto slightly different pixels, leaving
a sliver of the rule along the tab's bottom edge. That line stops an outline width short at
both ends (with a flat pen cap, since Qt's default square cap would run straight back over
them) so it cannot rub out the last rows of the tab's own left and right edges — which is
exactly where the outline hands the line over to the area's frame below. An indicator on that
edge already owns those pixels, so a theme with `indicator_position = "bottom"` draws no gap
line at all.

Prefer **whole-number widths**. A 1.5px pen has to straddle a pixel boundary: it renders as one
solid row plus a half-covered one beside it, which reads as a faint second line rather than a
soft edge.

The **sidebar overlay's** title bar draws a matching stripe along its own bottom edge. That
overlay hosts a single widget and has no tab strip, so its header stands in for one, and the
stripe appears only when both halves of a dock area's equivalent edge exist: the title bar
draws a bottom rule *and* tabs draw an indicator along their bottom
(`indicator_width > 0`, an `indicator_color`, and `bottom` in `indicator_position`). It takes
the rule's width, and its colour follows the overlay's own focus state (`_sidebar_focused`,
the same flag its card outline paints by) so the stripe and the outline never disagree.
`neon_dusk`, `violet_haze` and `midnight_haze` therefore show no stripe: they have the rule but
mark the active tab with an outline instead of a bottom indicator. `resolve_sidebar_title_bar_rule()` in
`dock_chrome.py` is the single decision point.

#### Limiting the area outline — `border_below_title`

`CORE.border_below_title` (`ThemeSpec.border_below_title`) draws the dock area's outline on the
**left, right and bottom only**, running up to the underside of the title bar instead of closing
across the top. `title_border_bottom` then supplies the fourth side, so the frame closes without a
second horizontal line above the header.

* No effect when `border_width` is 0 — there is no outline to limit.
* The join is resolved on every repaint from the title bar's laid-out geometry
  (`ChromeFrame.chrome_border_top()`, overridden by `DockAreaWidget`), so it tracks the title
  height and the window size.
* With no visible title bar the outline stays closed: three sides around nothing reads as a
  broken frame, not a design.
* The background fill is unaffected and still covers the whole rounded card; only the stroke
  changes.

`violet_haze` uses it, paired with its `title_border_bottom` rule.

Two settings genuinely conflict with the outline:

- `title_border_width` — the title bar then paints a full outline and never reaches the
  bottom-rule branch, so the rule disappears.
- `indicator_position = "bottom"` — the indicator lands on exactly the edge the outline leaves
  open and fills the gap back in; `"top"` stacks it on the outline's own top edge at a
  different width. Outline presets set `"none"`.

A **transparent** colour — not a missing one — is what turns a state off: `build_theme()` seeds
both colours for every theme, so `tab_border_color = [0, 0, 0, 0]` is how `midnight_haze`
outlines only the active tab.

#### The frame as a focus indicator — `tab_border_unfocused_color`

`TAB.border_unfocused_color` (`ThemeSpec.tab_border_unfocused_color`) is the active tab's
outline **while its dock area is unfocused**. Unset, that state is the active colour dimmed
halfway into the tab's background (`tab_dimming`) or the active colour unchanged. Transparent
drops the outline entirely.

Under `border_below_title` that one token governs the whole frame, because the frame *is* the
tab's outline continued: with no outline to continue, `resolve_below_title_frame_color()`
answers transparent rather than falling back to `CORE.border_color`, and
`resolve_title_bar_bottom_rule()` reads a transparent colour as "no rule" rather than stroking
something invisible. An unfocused area then has no frame, no rule and no tab outline — every
line on screen belongs to the area you are working in. `midnight_haze` is built on this.

### 3.10 `dock_style_manager.py` — `DockStyleManager` (singleton)

| Category | Members |
|---|---|
| **Signals** | `style_changed(category, changes)` |
| **Singleton** | `instance() → DockStyleManager` |
| **Theme** | `apply_theme(name) → bool`, `apply_theme_dict(theme_data) → bool`, `_reset_to_defaults()` |
| | `apply_theme_dict()` applies a raw `{DockStyleCategory: {token: value}}` dict (e.g. from `load_theme_json`) through the same reset-to-defaults + broadcast path as named themes |
| **Subscribers** | `register(subscriber, category)`, `unregister(subscriber, category?)` |
| **Get** | `get(category, key, default)`, `get_all(category) → dict` |
| **Update** | `update(category, **kwargs) → set` (returns changed keys) |
| **Meta** | `generation` (monotonic counter), `_dict_cache`, `_suppress_signals` |
| **Convenience** | `get_dock_style_manager()`, `apply_dock_theme(name)` |

### 3.11 `dock_theme_bridge.py` — `DockThemeBridge`

Pushes QPalette to the target widget/app so Qt children match the dock theme.

| Category | Members |
|---|---|
| **Constructor** | `__init__(target, style_name, parent)` — applies Fusion style, registers for CORE/TAB/TITLE_BAR/PANEL/SIDEBAR/SIDEPANEL |
| **Callback** | `on_style_changed(category, changes)` — debounced via QTimer |
| **Refresh** | `refresh_dock_palette()` — builds palette, applies to target, re-applies to all DockWidgets |
| **Base** | `_apply_base_style(style_name)` |

### 3.12 `theme_manager.py` — `ThemeManager`

OS-aware auto dark/light theme switching.

| Category | Members |
|---|---|
| **Signals** | `theme_changed(theme_name, is_dark)` |
| **OS Detection** | `is_windows_dark_mode()` — checks Qt 6.5+ colorScheme, Windows registry, or palette fallback |
| **Sync** | `sync_theme(force, path) → bool` — applies dark/light theme from user preferences; `path` overrides the resolved source with an explicit theme file |
| **Events** | `eventFilter(obj, event)`, `_on_color_scheme_changed()`, `install_listener(target)`, `remove_listener(target)` |
| **User prefs** | `user_light_theme`, `user_dark_theme`, `auto_mode_enabled`, `default_theme_path` |

**Theme source resolution** (`sync_theme` with `path=None`):

1. `user_dark_theme` / `user_light_theme` if the value is itself an existing file path (JSON / QSS / CSS),
2. `default_theme_path` — a single theme file, or a directory of `<theme_name>.json|.qss|.css` files,
3. a registered Lace theme name (e.g. `"dark"`), or a raw QSS string.

`.json` files are loaded through `ThemeJson` (Pydantic validation) and applied via `DockStyleManager.apply_theme_dict()`; QSS/CSS files are applied via `setStyleSheet()`.

### 3.13 `theme_models.py` — `ThemeJson` (JSON theme loading)

Pydantic-validated loading of declarative themes from JSON files. The JSON schema mirrors `ThemeSpec` (see §3.2): the same 3–5 seed colors plus geometry/status overrides, so a JSON theme derives its full token set through `build_theme()` exactly like the built-in presets.

| Member | Description |
|---|---|
| **`ThemeJson`** | Pydantic `BaseModel`; fields match `ThemeSpec`; unknown keys are ignored; colors accept `[r, g, b(, a)]` lists or `"#rrggbb"` / SVG-name strings |
| **`ThemeJson.load(path)`** | Parse + validate a JSON file; raises `JSONDecodeError` / `ValidationError` |
| **`to_theme_spec()`** | Convert the validated model into a `ThemeSpec` (hex strings resolved via `to_qcolor`) |
| **`build_theme_dict()`** | Derive the full `{DockStyleCategory: {token: value}}` theme dict |
| **`load_theme_json(path)`** | One-shot helper: `ThemeJson.load(path).build_theme_dict()` |

Example `theme.json`:

```json
{
    "name": "MyTheme",
    "base": [14, 11, 28, 255],
    "accent": "#ff007f",
    "text": [245, 245, 255, 255],
    "surface": [24, 19, 44, 255],
    "corner_radius": 8,
    "tab_dimming": true
}
```

Apply with `get_dock_style_manager().apply_theme_dict(load_theme_json("theme.json"))` or through `ThemeManager.sync_theme(path="theme.json")`.

---

## 4. Sidebar System

### 4.1 `sidebar_manager.py` — `SidebarManager`

VS Code-style auto-hide sidebar with hover, animations, badges, and drag-to-float.

| Category | Members |
|---|---|
| **Signals** | `sidebar_toggled(area, bool)`, `widget_unpinned` |
| **Setup** | `setup_shortcuts(window)`, `add_sidebar(area) → SideTabBar` |
| **Pin/Unpin** | `pin_widget(widget, sidebar?, area?)`, `unpin_widget(widget, area?)`, `unpin_widget_floating(widget)`, `pin_to_closest_sidebar(widget)`, `move_widget_to_area(widget, area)` |
| **Toggle** | `toggle_sidebar(area)`, `focus_sidebar(area)` |
| **Overlay** | `close_overlay()`, `raise_overlays()`, `show_widget(widget)`, `hide_widget(widget)` |
| **Badges** | `update_badge(widget, value)`, `badge_position` (prop), `set_badge_position(position)` |
| **Toggles** | `set_auto_show_on_hover(enable)`, `set_animations_enabled(enable)`, `set_keep_open(keep)` |
| **State** | `save_state() → dict`, `restore_state(dict) → bool` |
| **Props** | `overlay → SideBarContainer`, `focus_behavior → SideBarFocusBehavior`, `has_sidebars → bool` |
| **Internal** | `_uncheck_all()`, `_on_tab_hover_enter/leave()`, `_process_pending_switch()`, `_on_hide_timeout()`, `_on_tab_clicked()`, `_show_for_button()`, `_on_overlay_pin_back/drag_unpin/resized()`, `_on_tab_drag_started()`, `_on_sidebar_activated()` |

**Inner controllers:**
- **SidebarKeyboardHandler** — shortcut registration (Escape), signals: `toggle_sidebar`, `focus_sidebar`, `close_current`
- **SidebarHoverController** — hover timers (400ms hide, 150ms switch), pending tab switching
- **SidebarOverlayController** — show/hide/resizing overlay, detach from overlay
- **SidebarDragController** — drag tab off sidebar → floating window
- **ClickOutsideFilter** — closes overlay when clicking outside
- **FloatingDragTracker** — tracks mouse during sidebar tear-off floating

### 4.2 `sidebar_tab.py` — `VerticalTabButton`

Rotated tab button for the sidebar.

| Category | Members |
|---|---|
| **Signals** | `drag_started`, `context_menu_requested`, `close_requested` |
| **Badge** | `set_badge(value, color?, position?)`, `clear_badge()`, `badge_position` (prop), `set_badge_position(position)` |
| **Paint** | `paintEvent(event)` — rotated icon+text, shape/indicator edge mirroring, outline, badge drawing |
| **Shape** | `_tab_shape() → (radius, flat_edge, border_closed)` — resolves `SIDEBAR.tab_flat_edge` against the tab's own sidebar; `_border_color(checked) → QColor?` (transparent = no outline in that state) |
| **Size** | `sizeHint()`, `minimumSizeHint()` |
| **Area** | `set_area(area)`, `_indicator_edge() → Qt.Edge` |
| **Mouse** | `enterEvent()`, `leaveEvent()`, `mousePressEvent()` (middle-click closes) |
| **Context** | `_on_context_menu(pos)` |
| **Styling** | `refresh_style()` |

### 4.3 `sidebar_tab_bar.py` — `SideTabBar`

Vertical tab strip with scroll, overflow counter, drag-drop reordering.

| Category | Members |
|---|---|
| **Signals** | `tab_hover_enter/leave/clicked/drag_started/moved`, `sidebar_activated` |
| **Tabs** | `add_tab(widget) → VerticalTabButton`, `remove_tab(widget)`, `count()`, `current_index()`, `is_tab_open(i)`, `tab(i)`, `button_for(widget)`, `uncheck_all()`, `tab_count()` |
| **Scroll** | `_scroll_by(delta)`, `wheelEvent()`, `_update_scroll_visibility()` |
| **Drop** | `dragEnterEvent()`, `dragMoveEvent()`, `dragLeaveEvent()`, `dropEvent()`, `_show/update/hide_drop_indicator()` |
| **Menu** | `build_dock_menu(menu, tab_bar?)`, `dispatch_dock_action(action)`, `_on_tab_context_menu(btn, pos)` |
| **MenuActionTarget** | `menu_target_widget()`, `menu_switch_tab_target(i)`, `menu_unpin_target()`, `menu_float_target()`, `menu_close_target()`, `menu_close_others_target()` |
| **Actions** | `_close_dock_widget(widget)`, `_close_tab_button(btn)`, `_close_others(keep_btn)`, `_close_all()`, `_move_to_area(widget, area)`, `_unpin_tab(btn)` |
| **Style** | `refresh_style()`, `paintEvent(event)` |
| **Filter** | `eventFilter(obj, event)` — hover enter/leave |

### 4.4 `sidebar_container.py` — `SideBarContainer`

Animated overlay panel hosting a pinned widget.

| Category | Members |
|---|---|
| **Signals** | `pin_back_requested`, `drag_unpin_requested`, `close_requested`, `resize_started/finished` |
| **Show/Hide** | `show_widget(widget, area, animate, size)`, `hide_widget(animate)`, `_on_anim_finished()`, `_on_hide_finished()` |
| **Geometry** | `_get_visible_geometry()`, `_get_hidden_geometry()`, `_update_geometry()`, `_get_max_width()`, `_get_max_height()` |
| **Resize** | `mousePressEvent()`, `mouseMoveEvent()`, `mouseReleaseEvent()`, `_is_in_resize_zone(pos)`, `_do_resize(global_pos)`, `resizeEvent()` |
| **Focus** | `focus_behavior` (prop), `_focus_inner_widget()`, `_restore_previous_focus()`, `_on_app_focus_changed(old, new)` |
| **Shadow** | `_update_shadow_direction()` |
| **Layout** | `_update_layout_margins()`, `_update_resize_margins()`, `eventFilter(obj, event)` — parent resize clamping |
| **Style** | `refresh_style()`, `paintEvent(event)` |
| **Focus behavior** | `SideBarFocusBehavior.take_focus_and_restore`, `no_focus_transfer`, `take_focus_only` |

### 4.5 `sidebar_title_bar.py` — `SideBarTitleBar`

Title bar inside the overlay panel.

| Category | Members |
|---|---|
| **Signals** | `close_requested`, `reattach_requested`, `detach_requested` |
| **UI** | `set_widget(widget?)` — updates title + button visibility |
| **Drag** | `_on_drag_started(pos)` — drag to detach |
| **Menu** | `build_dock_menu(menu, tab_bar?)`, `dispatch_dock_action(action)`, `_show_context_menu(pos)` |
| **Buttons** | `_on_reattach_clicked()`, `_on_close_clicked()` |
| **MenuActionTarget** | `menu_target_widget()`, `menu_unpin_target()`, `menu_float_target()`, `menu_close_target()` |
| **Style** | `refresh_style()`, `paintEvent(event)` |

---

## 5. Layout Serialization

### 5.1 `layout_serializer.py`

| Class | Description |
|---|---|
| **LayoutSerializer** (facade) | `serialize(version, formatted) → str`, `deserialize(json, version)` — validates system type and version |
| **LayoutStateBuilder** | `build_state_dict(version) → dict` — iterates containers, saves geometries, sidebar state, widget states |
| **LayoutEngine** | `apply_state(dict)` — validates, hides floating widgets, restores containers/areas/widgets, applies geometries, restores sidebar state |
| **LayoutPersistenceManager** | `save_layout(serializer, filename, version, formatted)` — atomic write (temp file + rename), `load_layout(serializer, filename, version)` |

**Exceptions:** `LayoutError`, `LayoutIOError`, `InvalidFormatError`, `RestoreFailureError`.

**LayoutEngine internals:** `_validate_can_restore()`, `_dry_run_containers()`, `_hide_floating_widgets()`, `_restore_dock_widgets_open_state(assigned)`, `_restore_sidebar_state()`, `_restore_dock_areas_indices()`, `_emit_top_level_events()`, `_apply_container_geometry(fw)` — rescues off-screen windows.

**Restore is validated before it mutates anything.** `_validate_can_restore()` checks the root
keys, geometry bounds and the widget roster; `_dry_run_containers()` then replays every container
tree with `testing=True`, which allocates nothing, and raises `RestoreFailureError` on a
structural fault. Only after both pass is the live layout torn down.

### 5.1.1 Format identity and versioning

Two independent numbers live in a saved layout:

| Field | Owner | Meaning |
|---|---|---|
| `type` | Lace | `"LaceDockingSystem"`. The legacy value `"QtAdvancedDockingSystem"` is still accepted on read. |
| `schema` | Lace | `LayoutStateBuilder.SCHEMA_VERSION`. **Bump on every change to the layout format.** A newer schema is refused; an older one warns and falls back to defaults. |
| `version` | The application | Whatever integer the caller passes to `save_state(version=N)`. Lace only checks it round-trips. |

### 5.1.2 What is *not* persisted

A layout records **placement**, not configuration. The following are properties of the widgets
the application constructs, and are expected to be re-applied in code on every startup *before*
`restore_state()` runs:

| Not saved | Where it comes from instead |
|---|---|
| `DockWidget` features (`closable`, `movable`, `floatable`, `pinnable`, …) | Set by the application via `set_feature()` |
| Widget titles, icons and tab icons | Constructor arguments / `set_icon()` |
| The content widget itself | `set_widget()` — restore matches by `objectName()` only |
| Toolbars added with `set_toolbar()`, and their actions | Application code |
| Badges and badge positions | Runtime state, reset on restore |
| `DockManager` config flags, the floating-window icon, title-bar descriptors | `DockManager` setup |
| The active theme | `ThemeManager` / `DockStyleManager`, which have their own persistence |
| Scroll positions, selections, and any state inside the content widget | Application code |

A widget the layout names but the application has not registered is dropped with a warning; a
widget the application registers but the layout does not name is left closed and unassigned.

### 5.2 `dock_container_state.py`

Low-level container state save/restore (used by LayoutEngine).

| Function | Description |
|---|---|
| `save_container_state(c) → dict` | Serializes floating state, geometry, root splitter tree |
| `restore_container_state(c, state, testing, assigned) → bool` | Restores tree structure, splitter orientations, dock areas |
| `_save_child_nodes_state(c, widget)` | Recursive: QSplitter → orientation/sizes/children, DockAreaWidget → area state |
| `_restore_child_nodes(c, state, testing, assigned)` | Dispatches to `_restore_splitter()` or `_restore_dock_area()` |
| `_restore_splitter(c, state, testing, assigned)` | Rebuilds splitter hierarchy with sizes |
| `_restore_dock_area(c, state, testing, assigned)` | Rebuilds dock area with widgets, closed states, locking, current index |

The optional `assigned` dict is filled with `{dock_widget: closed_flag}` for every widget the
rebuild re-docked. `LayoutEngine` uses membership in it to decide which widgets the layout did
not mention and must therefore be flagged unassigned — previously communicated through Qt dynamic
properties written in one module and read in another.

---

## 6. Signals & Menus

### 6.1 `dock_signals.py` — `DockSignals` (internal event bus)

| Signal | Args |
|---|---|
| `request_overlay_show` | `(target_container)` |
| `request_overlay_hide` | `()` |
| `floating_widget_dropped` | `(floating_widget, target_pos)` |

### 6.2 `dock_menu.py` — Unified context menu system

| Class/Enum | Description |
|---|---|
| **MenuSection** (Flag) | `TAB_LIST`, `PIN`, `UNPIN`, `DETACH`, `MAXIMIZE`, `CLOSE`, `CLOSE_OTHERS`; presets: `TITLE_BAR`, `TAB`, `SIDEBAR_TAB` |
| **MenuContext** (dataclass) | widget_type, sections, category, widget, area, tab_bar, count, is_closable/floatable/pinnable/pinned/floating/has_sidebars/show_close_others, icon/label overrides |
| **MenuActionTarget** (Protocol) | Interface: `menu_target_widget()`, `menu_close_target()`, `menu_float_target()`, `menu_dock_target()`, `menu_pin_target()`, `menu_unpin_target()`, `menu_pin_all_target()`, `menu_close_others_target()`, `menu_maximize_target()`, `menu_switch_tab_target(i)` |
| **dock_icon(key, category) → QIcon** | Resolves from SVG provider → theme icon → standard icon; tints for Normal/Disabled states |
| **build_dock_context_menu(context, menu)** | Stateless menu builder populates QMenu from context |
| **dispatch_dock_context_menu(action, target, fallback)** | Routes triggered QAction to target's MenuActionTarget methods |
| **find_closest_dock_area(global_center, manager) → DockWidgetArea** | Finds nearest outer edge |
| **menu_default_pin/unpin/pin_all/reattach(area)** | Default action implementations |

---

## 7. Styling Infrastructure

### 7.1 `dock_styled.py` — `DockStyled` mixin

| Method | Description |
|---|---|
| `_init_dock_style(refresh=True)` | Registers widget as subscriber for `STYLE_CATEGORIES`, applies initial style |
| `on_style_changed(category, changes)` | Debounced refresh (single-shot timer) |
| `_do_refresh()` | Calls `refresh_style()`, catches RuntimeError for deleted widgets |
| `refresh_style()` | Abstract — must be overridden by subclass |

### 7.2 `dock_icon_provider.py` — `DockIconProvider`

Theme-aware SVG icon provider. Preloads SVGs from a filesystem path or `importlib.resources` package (`lace.resources.lace_icons`), tints them dynamically based on `DockStyleManager` categories, and caches by (name, color, active, disabled, size).

| Category | Members |
|---|---|
| **Resource Resolution** | `_resolve_icon_path(directory) → Path | Traversable` — tries filesystem first, falls back to `resources.files("lace.resources.lace_icons")`, uses `resources.as_file()` for wheel compatibility |
| **Loading** | `__init__(directory)` — resolves path, subscribes to `DockStyleCategory.CORE`, calls `_preload()` |
| **Preload** | `_preload()` — reads all `*.svg` files into `self._svg_cache` (dict: `stem.lower() → svg_string`) |
| **Get** | `get(name, category, active=False, disabled=False, size=16) → QIcon` — resolves tint color, checks `self._icon_cache` by `(key, color, active, disabled, size)`, returns `QIcon()` if SVG missing |
| **Tinting** | `_tint_svg(svg, color) → str` — replaces `currentColor` or all `fill`/`stroke` attributes with tint color via regex `_COLOR_PATTERN` |
| **Rendering** | `_render_svg(svg_data, size) → QPixmap` — `QSvgRenderer` with 4× supersample + `Qt.SmoothTransformation` downscale for HiDPI; accounts for `QApplication.devicePixelRatio()`; renders to viewBox-filling rect to keep glyphs centred |
| **Color Resolution** | `_resolve_color(category, active, disabled) → str` — dispatcher; `_resolve_normal_color()` — per-category lookup (`TAB` → `text_active`/`text_normal`, `SIDEBAR` → `tab_text_active`/`tab_text_normal`, `TITLE_BAR`/`SIDEPANEL` → `button_color`, else `text_color`); `_resolve_disabled_color()` — per-category lookup (`TAB` → `close_btn_bg_disable`, `TITLE_BAR`/`SIDEPANEL` → `button_disable_clr`, `SIDEBAR` → `tab_text_disabled`, else `disabled_text_color`); fallback: `"#C8CDD7"` |
| **Callback** | `on_style_changed(category, changes)` — clears `self._icon_cache` on theme switch |
| **Singleton** | `get_icon_provider(directory) → DockIconProvider` — global singleton; raises `ValueError` if no icon directory found |

**Constants:**
| Constant | Value |
|---|---|
| `_ICON_PACKAGE` | `"lace.resources.lace_icons"` |
| `_FALLBACK_COLOR` | `"#C8CDD7"` |
| `_COLOR_PATTERN` | `re.compile(r'(fill|stroke)="(?!none\b)([^\"]*)"')` |

**Minimize key remap:** `"minimize"` SVG name is internally remapped to `"restore"` (the actual SVG filename).

---

## 8. Enums & Configuration

### 8.1 `enums.py` — Core System Enums

| Enum | Type | Purpose |
|---|---|---|
| **DockInsertParam** (NamedTuple) | `orientation`, `append` | Helper for splitter insertion direction; exposes `insert_offset` property |
| **DockWidgetArea** (`IntFlag`) | Bitwise flags: `no_area`, `left`, `right`, `top`, `bottom`, `center`, `invalid`; masks: `outer_dock_areas` (15), `all_dock_areas` (31) | Physical layout zones within a `DockContainerWidget` or `SideBarContainer` where widgets can be dropped, split, or docked. Used by `DockContainerWidget` to determine splitter orientation (Horizontal for left/right, Vertical for top/bottom), by `SideBarManager` to map to sidebar overlays, and by `DockOverlay` / `DockPaint` to compute drop-zone hitboxes and paint translucent indicators |
| **DockFlags** (`IntFlag`) | 19 global config bits: `opaque_splitter_resize`, `opaque_undocking`, `always_show_tabs`, `show_tab_close_button`, `active_tab_has_close_button`, `dock_area_has_close_button`, `dock_area_close_button_closes_tab`, `dock_area_has_undock_button`, `dock_area_has_pin_button`, `dock_area_has_maximize_button`, `sidebar_area_has_maximize_button`, `dock_area_has_tabs_menu_button`, `middle_mouse_button_closes_tab`, `floatable_tabs`, `pinnable_tabs`, `custom_tab_icons`, `hide_disabled_title_bar_icons`, `chromeless_float`, `floating_taskbar_button`; plus `none_` (0) and `default_config` (combined mask) | Global system configuration controlling tab rendering, button visibility, drag-and-drop behavior, and floating window appearance. Stored on `DockManager.config_flags`. For example: `opaque_undocking` keeps floating windows at 100% opacity during drag (vs 0.6); `chromeless_float` creates frameless top-level windows; `floating_taskbar_button` gives each float its own taskbar button (`WS_EX_APPWINDOW`) plus a minimize button — without it a float is an owned window, so minimizing would put it somewhere the user cannot click; `custom_tab_icons` switches between user-configured and default tab icons; `floatable_tabs` / `pinnable_tabs` gate whether tabs can be dragged to float or pinned to sidebars |
| **TitleBarButton** (Enum) | `tabs_menu`, `undock`, `close`, `pin`, `maximize`, `minimize`, `restore` | Identifiers for standard interactive buttons on dock area title bars. Used by `DockAreaTitleBar.button(which)` to retrieve specific `QToolButton` instances, and by `DockContainerWidget` to dynamically update button visibility/state for floating windows |
| **OverlayMode** (Enum) | `dock_area`, `container` | Controls how translucent drop indicator crosses (`DockOverlay`) are rendered: `dock_area` targets a specific `DockAreaWidget` (local card split), `container` targets outer margins of `DockContainerWidget` (global edge split). Instantiated in `DockManager.__init__()` as two separate overlays |
| **DragState** (Enum) | `inactive`, `mouse_pressed`, `tab`, `floating_widget` | State machine tracking drag-and-drop context across `DockWidgetTab`, `DockAreaTitleBar`, and `FloatingDockContainer`. Transitions: `mouse_pressed` → (distance exceeded?) → `tab` (reorder within tab bar) or `floating_widget` (detach to new window) → `inactive` on release |
| **InsertionOrder** (Enum) | `by_spelling`, `by_insertion` | Governs sorting order of dock widget items in dynamic "Show View" dropdown menus (`DockManager.view_menu`). `by_spelling` = alphabetical by title; `by_insertion` = chronological by widget registration. Runtime-changeable via `DockManager.menu_insertion_order` |
| **DockWidgetFeature** (`IntFlag`) | Bitwise per-widget: `closable`, `movable`, `floatable`, `pinnable`; mask `all_features` (15) | Fine-grained permission gating defining what actions a user can perform on a specific `DockWidget`. Checked by `DockWidgetTab` / `DockAreaTitleBar` to show/hide close, undock, and pin buttons; by `SidebarManager` to block pin/unpin/move operations on non-pinnable/immovable widgets |
| **WidgetState** (Enum) | `docked`, `floating`, `pinned_shown`, `pinned_hidden` | Tracks current structural attachment and display mode of a `DockWidget`. Set by `SidebarManager` (pin → `pinned_hidden`, slide_out → `pinned_shown`, unpin → `docked`, detach → `floating`). Inspected by `DockWidget.refresh_style()` to apply correct `DockStyleCategory` token overrides (`SIDEPANEL` vs `CORE`) |
| **InsertMode** (Enum) | `auto_scroll_area`, `force_scroll_area`, `force_no_scroll_area` | Specifies whether client content inside a `DockWidget` is wrapped in a `QScrollArea`. Default `auto_scroll_area` wraps if widget is not already a scroll area; `force_scroll_area` always wraps; `force_no_scroll_area` adds directly to layout without scrollbars |
| **ToggleViewActionMode** (Enum) | `toggle`, `show` | Controls behavior of `dock_widget.toggle_view_action()` in menu bars/toolbars. `toggle` = checkable QAction that flips Show/Hide; `show` = non-checkable push that only reveals the widget |
| **SideBarFocusBehavior** (Enum) | `take_focus_and_restore`, `no_focus_transfer`, `take_focus_only` | Configures keyboard focus stealing when sidebar overlays slide out/in. `take_focus_and_restore` = sidebar takes focus on open, restores previous focus on close; `no_focus_transfer` = no focus change; `take_focus_only` = takes focus on open but does not restore on close. Global setting via `DockManager.sidebar_focus_behavior` |

### 8.2 `sidebar_tab.py` — `TabBadgePosition` (Enum)

| Enum | Values | Purpose |
|---|---|---|
| **TabBadgePosition** | `top_left`, `top_right`, `bottom_left`, `bottom_right` | Corner positioning of numerical notification badges on vertical sidebar tabs (`VerticalTabButton`). Default is `top_right`. Exposed via `badge_position` property / `set_badge_position()` setter on both `VerticalTabButton` and `SidebarManager`. Also theme-drivable via `DockSidebarStyleSchema` for per-theme corner overrides |

### 8.3 `dock_theme.py` — `DockStyleCategory` (Enum)

| Enum | Values | Purpose |
|---|---|---|
| **DockStyleCategory** | `CORE`, `PANEL`, `TAB`, `TITLE_BAR`, `SIDEBAR`, `SIDEPANEL`, `SPLITTER`, `OVERLAY` | Namespaces component categories for hierarchical style token lookups (`StyleManager.get_all(category)`) and SVG icon color generation (`dock_icon(name, category)`). Every UI component registers its relevant categories via `DockStyled.STYLE_CATEGORIES` (e.g., `VerticalTabButton` → `SIDEBAR`, `DockWidget` → `PANEL`). Used by `DockThemeBridge` to push correct QPalette roles to Qt children |

---

## 9. Utility Modules

| Module | Contents |
|---|---|
| **`util.py`** | `emit_top_level_event_for_widget()`, `start_drag_distance()`, `create_transparent_pixmap()`, `set_button_icon()`, `hide_empty_parent_splitters()`, `find_parent()`, `find_child()`, `find_children()`, `_dump_recursive()`, `dump_layout()` |
| **`eliding_label.py`** | `ElidingLabel` — QLabel with text elision, resize-aware, click/double-click signals |
| **`_trace.py`** | `trace(event, **fields)` — optional debug tracing (off by default, enabled via `LACE_TRACE=1`) |

---

## 10. Widget Hierarchy (Runtime)

```
QMainWindow (user's main window)
└── DockManager
    └── DockContainerWidget (root)          ← set as central widget
        ├── SideTabBar (left)                ← sidebar tab strip
        ├── SideTabBar (right)               ← sidebar tab strip
        ├── QGridLayout
        │   ├── cell(0,1): SideTabBar(top)   ← optional top sidebar
        │   ├── cell(1,0): SideTabBar(left)  ← optional left sidebar
        │   ├── cell(1,1): DockSplitter      ← main content area
        │   │   └── DockAreaWidget ×N
        │   │       ├── DockAreaTitleBar
        │   │       │   └── DockAreaTabBar
        │   │       │       └── DockWidgetTab ×N
        │   │       └── DockAreaLayout
        │   │           └── DockWidget (visible)
        │   │               └── QScrollArea
        │   │                   └── user widget
        │   ├── cell(1,2): SideTabBar(right) ← optional right sidebar
        │   ├── cell(2,1): SideTabBar(bottom)← optional bottom sidebar
        │   └── cell(0,0) / cell(2,0) etc.  ← empty corners
        └── SideBarContainer (overlay)       ← auto-hide sidebar panel
            ├── SideBarTitleBar
            └── QSplitter
                └── DockWidget (pinned)
```

Floating windows replace the root `DockContainerWidget` with a `FloatingDockContainer` (top-level Qt window) that wraps its own `DockContainerWidget` with identical internal structure.

---

## 11. Data Flow Summary

### Adding a dock widget:
```
DockManager.add_dock_widget(area, widget)
  → widget.set_dock_manager(self)
  → widget added to _dock_widgets_map
  → toggle_view_action added to _view_menu
  → root.add_dock_widget(area, widget, target_area)
    → DockContainerWidget._dock_widget_into_container() or _dock_widget_into_dock_area()
      → Creates DockAreaWidget if needed
      → Inserts into QGridLayout / DockSplitter hierarchy
      → Updates title bar visibility
```

### Floating a widget:
```
DockWidgetTab/DockAreaTitleBar mouse drag → start_drag_distance exceeded
  → FloatingDockContainer(dock_widget=widget)
    → Creates new DockContainerWidget(parent=floating_window)
    → Sets widget_state = floating
    → Shows as top-level window
  → FloatingDockContainer.start_dragging(pos, size, handler)
    → Grab mouse, install event filter
    → move_floating() tracks cursor
    → _update_drop_overlays() shows drop zones on other containers
  → Mouse release → _finalize_drag()
    → drop_floating_widget() → DockContainerWidget.drop_floating_widget()
      → DropController resolves target area
      → Inserts widgets into target splitter hierarchy
      → Deletes floating window
```

### Maximizing a dock area:
```
DockContainerWidget.toggle_maximize_dock_area(area)
  → If area already maximized → _restore_maximized_area()
  → If another area maximized → _restore_maximized_area() first
  → Floating single-area → OS showMaximized()/showNormal()
  → Multi-area:
    → _collect_splitter_sizes(root_splitter) → {id(splitter): sizes_list}
    → Hide all sibling dock areas (setVisible(False))
    → _maximize_splitter(root_splitter, area)
      → Recursively walks nested splitter tree
      → Finds area at its actual nesting level
      → Zeroes sibling splitters (setSizes([0]))
      → Hides sibling dock areas
      → Gives maximized area's parent splitter all available space
```

### Restoring a maximized dock area:
```
DockContainerWidget._restore_maximized_area()
  → Hide maximized area, show all sibling dock areas
  → For each splitter in _all_splitters():
      → setSizes(_pre_maximize_splitter_sizes[id(splitter)])
  → Clear _pre_maximize_splitter_sizes
```

### Removing a dock area (maximized state cleanup):
```
DockContainerWidget.remove_dock_area(area)
  → If area is _maximized_dock_area:
      → Show all sibling dock areas
      → Clear _maximized_dock_area and _pre_maximize_splitter_sizes
      → Invalidate visible count cache
      → Update title bar button states
  → Proceed with normal removal (disconnect signals, setParent(None), etc.)
```

### Theme change:
```
DockManager.set_theme(name)
  → DockStyleManager.apply_theme(name)
    → _reset_to_defaults()
    → update(category, **theme_data) for each category
      → _set_field() converts colors to QColor, records changes
      → _notify_subscribers(category, changes)
        → style_changed.emit(category, changes)
        → For each subscriber: on_style_changed(category, changes) or refresh_style()
  → DockThemeBridge.on_style_changed()
    → Debounced QTimer.singleShot(0, refresh_dock_palette)
    → resolve_dock_colors() → build_dock_palette() → target.setPalette(palette)
    → Refresh all DockWidget instances
```

### Layout save/restore:
```
DockManager.save_state(version)
  → LayoutSerializer.serialize(version)
    → LayoutStateBuilder.build_state_dict(version)
      → Iterates dock_containers() → save_container_state()
      → Saves sidebar state, geometries, widget closed states
      → json.dumps()
  → LayoutPersistenceManager.save_layout() → atomic file write

DockManager.restore_state(json, version)
  → LayoutSerializer.deserialize(json, version)
    → json.loads() → validates type / schema / version
    → LayoutEngine.apply_state(state_dict)
      → _validate_can_restore()      ─┐ nothing is mutated until
      → _dry_run_containers()        ─┘ both of these pass
      → Hides floating widgets
      → Restores containers (root + floating), collecting `assigned`
      → Restores sidebar state (pinned widgets first — they own no dock area)
      → Restores widget open/closed states from `assigned`
      → Sets current indices
      → Emits top_level_changed events
```
