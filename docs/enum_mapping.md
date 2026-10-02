# Lace: Enumerations & Flags

**Version:** 0.9.1

Every enumeration and flag class in Lace: what it is for, each member, and where the
code reads it. References name the function (`Class.method()`) rather than a line
number, so they stay valid as files change; search for the name to find the spot.

---

## 1. Overview

| Enum / Flag | Type | Module | Members | Purpose |
| :--- | :--- | :--- | :---: | :--- |
| [`DockWidgetArea`](#31-dockwidgetarea) | `IntFlag` | [`enums.py`](../lace/enums.py) | 9 | Regions of a container where widgets dock |
| [`DockFlags`](#32-dockflags) | `IntFlag` | [`enums.py`](../lace/enums.py) | 21 | Global configuration switches on `DockManager` |
| [`TitleBarButton`](#33-titlebarbutton) | `Enum` | [`enums.py`](../lace/enums.py) | 7 | Keys for the buttons of a dock area title bar |
| [`OverlayMode`](#34-overlaymode) | `Enum` | [`enums.py`](../lace/enums.py) | 2 | Drop overlay over one dock area, or over the whole container |
| [`DragState`](#35-dragstate) | `Enum` | [`enums.py`](../lace/enums.py) | 4 | Drag state machine of tabs, title bars and floats |
| [`InsertionOrder`](#36-insertionorder) | `Enum` | [`enums.py`](../lace/enums.py) | 2 | Sort order of the view menu |
| [`DockWidgetFeature`](#37-dockwidgetfeature) | `IntFlag` | [`enums.py`](../lace/enums.py) | 6 | Per-widget capabilities |
| [`WidgetState`](#38-widgetstate) | `Enum` | [`enums.py`](../lace/enums.py) | 4 | Where a dock widget currently lives |
| [`InsertMode`](#39-insertmode) | `Enum` | [`enums.py`](../lace/enums.py) | 3 | Whether content is wrapped in a scroll area |
| [`ToggleViewActionMode`](#310-toggleviewactionmode) | `Enum` | [`enums.py`](../lace/enums.py) | 2 | Toggle or show-only view actions |
| [`SideBarFocusBehavior`](#311-sidebarfocusbehavior) | `Enum` | [`enums.py`](../lace/enums.py) | 3 | Focus handling of sidebar panels |
| [`TitleBarMode`](#312-titlebarmode) | `Enum` | [`enums.py`](../lace/enums.py) | 2 | Native or custom (frameless) floating windows |
| [`TabBadgePosition`](#313-tabbadgeposition) | `Enum` | [`sidebar_tab.py`](../lace/sidebar_tab.py) | 4 | Corner of a sidebar tab's badge |
| [`DockStyleCategory`](#314-dockstylecategory) | `Enum` | [`dock_theme.py`](../lace/dock_theme.py) | 8 | Theme token groups, and the keys components subscribe with |
| [`MenuSection`](#315-menusection) | `Flag` | [`dock_menu.py`](../lace/dock_menu.py) | 11 | Sections of the unified context menu |

All fifteen are exported from `lace`, and every member is wired.

---

## 2. Members with no direct reference

A few members are never named in the code. They take effect by being *none* of the
other members:

| Member | How it takes effect |
| :--- | :--- |
| `DockFlags.none_` | The empty mask. |
| `DockWidgetFeature.no_features` | The empty mask: every `features() & …` test fails, so buttons, drags and menu entries are off. |
| `MenuSection.NONE` | The empty mask. |
| `InsertMode.force_scroll_area` | `DockWidget.set_widget()` wraps anything that isn't already a `QScrollArea` unless the mode is `force_no_scroll_area`, so this behaves as `auto_scroll_area`. |
| `ToggleViewActionMode.show` | `DockWidget.set_toggle_view_action_mode()` makes the action checkable only for `toggle`; `DockWidget.toggle_view()` forces `open_ = True` when the action isn't checkable. |
| `SideBarFocusBehavior.no_focus_transfer` | `SideBarContainer` moves focus only for the two other members. |
| `TitleBarButton.minimize`, `.restore` | `DockAreaTitleBar.button()` returns the one maximize/restore button for `maximize`, `minimize` and `restore`. |

### Removed members

- **`WidgetState.hidden`**: `DockWidget.is_closed()` is the single source for "hidden",
  so the state can't drift from the docked/floating geometry.
- **`DockFlags.content_drop_preview`, `drag_preview_shows_content_pixmap`**: a scaled
  screenshot in the drop zone distorted the aspect ratio and doubled the live floating
  window. `DockOverlay` draws only the translucent drop highlight.

---

## 3. Details

### 3.1 `DockWidgetArea`

`IntFlag` with powers of two, so areas combine with `|` and test with `&`.

| Member | Value | Meaning | Read by |
| :--- | :---: | :--- | :--- |
| `no_area` | 0 | No area | `floating_behaviour.allowed_areas_for()` |
| `left` | 1 | Left edge; left sidebar | `dock_container_widget.dock_area_insert_parameters()`, `DockOverlay._compute_drop_rect()`, `DockOverlayCross`, `DockManager._add_sidebar_to_layout()`, `dock_menu.find_closest_dock_area()` |
| `right` | 2 | Right edge; right sidebar | as `left`, plus `dock_menu.menu_default_reattach()` |
| `top` | 4 | Top edge; top sidebar | as `left` |
| `bottom` | 8 | Bottom edge; bottom sidebar | as `left` |
| `center` | 16 | Tab into the area | `DockContainerWidget.add_dock_area()`, `DropController._drop_into_section()` / `_drop_into_container()` |
| `invalid` | 0 | Alias of `no_area`: no drop target | `DockOverlay.drop_area_under_cursor()` / `show_overlay()` / `hide_overlay()`, `DropController.drop_floating_widget()`, `DockManager.add_dock_area()` |
| `outer_dock_areas` | 15 | `left \| right \| top \| bottom` | `DockWidgetTab._start_floating()`, `DockAreaTitleBar._start_floating()`, `FloatingContainerBehaviour._update_drop_overlays()` |
| `all_dock_areas` | 31 | `outer_dock_areas \| center` | `FloatingContainerBehaviour._update_drop_overlays()`, `allowed_areas_for()` |

`dock_area_insert_parameters()` turns an edge into a splitter orientation and an
insert-before/after (`DockInsertParam`). `SidebarManager` keys its four sidebars by the
edge members.

### 3.2 `DockFlags`

`IntFlag` held in `DockManager.config_flags`. A runtime change goes through
`DockManager.notify_config_flags_changed()`, which refreshes title bars, tabs and floating
windows. `default_config` holds the flags marked ●.

| Member | Default | Meaning | Read by |
| :--- | :---: | :--- | :--- |
| `none_` | | Empty mask | — |
| `opaque_splitter_resize` | ● | Splitters resize live, without a rubber band | `DockContainerWidget._new_splitter()` |
| `opaque_undocking` | ● | A torn-off widget follows the cursor at once; cleared, a preview shows until release | `FloatingContainerBehaviour._set_state()` |
| `always_show_tabs` | ● | Tabs show even for a single widget | `DockAreaTabBar._update_tab_bar_visibility()` |
| `show_tab_close_button` | ● | Each tab has a close button | `DockWidgetTab.update_close_button_visibility()` |
| `active_tab_has_close_button` | ● | Only the active tab has one | `DockWidgetTab.update_close_button_visibility()` |
| `dock_area_has_close_button` | ● | Close button in the area title bar | `DockAreaTitleBar.update_button_states()` |
| `dock_area_close_button_closes_tab` | | The area's close button closes only the active tab | `DockAreaTitleBar.on_close_button_clicked()`, `_create_buttons()`, `update_button_states()`, `_gather_menu_context()` |
| `dock_area_has_undock_button` | ● | Undock (float) button | `DockAreaTitleBar.update_button_states()` |
| `dock_area_has_pin_button` | ● | Pin-to-sidebar button | `DockAreaTitleBar.update_button_states()`, `DockContainerWidget._on_visible_dock_area_count_changed()` |
| `dock_area_has_maximize_button` | ● | Maximize/restore button | `DockAreaTitleBar._create_buttons()`, `update_button_states()`, `on_maximize_button_clicked()` |
| `sidebar_area_has_maximize_button` | ● | Maximize button on an open sidebar panel | `SideBarTitleBar.update_button_states()` |
| `dock_area_has_tabs_menu_button` | ● | Button listing the area's tabs | `DockAreaTitleBar._create_buttons()`, `update_button_states()` |
| `middle_mouse_button_closes_tab` | ● | Middle click closes a tab | `DockWidgetTab.mousePressEvent()` |
| `floatable_tabs` | ● | Tabs and areas can be floated | `DockAreaTitleBar.mouseMoveEvent()`, `_start_floating()`, `on_undock_button_clicked()`, `mouseDoubleClickEvent()`, `update_button_states()`, `_gather_menu_context()`; `DockWidgetTab` |
| `pinnable_tabs` | ● | Tabs and areas can be pinned to a sidebar | `DockAreaTitleBar.on_pin_button_clicked()`, `update_button_states()`, `_gather_menu_context()`; `DockWidgetTab._pinnable()`; `dock_menu.menu_default_pin()` / `menu_default_pin_all()` |
| `custom_tab_icons` | | Tabs show the widget's own icon, not the provider default | `DockWidgetTab.update_icon()` |
| `hide_disabled_title_bar_icons` | ● | Disabled title-bar buttons are hidden, not greyed | `DockAreaTitleBar.update_button_states()` |
| `chromeless_float` | | Floating windows have no title bar at all | `FloatingDockContainer.__init__()` / `update_window_flags_from_config()`, the same in `FramelessFloatingDockContainer`, `DockAreaTitleBar.update_button_states()` |
| `floating_taskbar_button` | | Each float gets its own taskbar button and a minimize button (Windows) | `FloatingContainerBehaviour._wants_taskbar_button()` |
| `default_config` | | The ● flags | `DockManager.__init__()` |

### 3.3 `TitleBarButton`

Keys for `DockAreaTitleBar.button(which)` and `DockAreaWidget.title_bar_button(which)`.

| Member | Returns | Looked up by |
| :--- | :--- | :--- |
| `tabs_menu` | The tabs menu button | `DockAreaTitleBar.button()` only |
| `undock` | The undock button | `DockContainerWidget._on_visible_dock_area_count_changed()` (hidden for a lone area in a float), `_add_dock_areas_to_list()` |
| `close` | The close button | as `undock` |
| `pin` | The pin button | as `undock` |
| `maximize`, `minimize`, `restore` | The one maximize/restore button | `DockAreaTitleBar.button()` only |

### 3.4 `OverlayMode`

`DockManager.__init__()` creates one `DockOverlay` of each mode.

| Member | Meaning | Read by |
| :--- | :--- | :--- |
| `dock_area` | Cross over the dock area under the cursor: split it or tab into it | `DockOverlayCross.__init__()`, `_area_grid_position()`, `set_area_widgets()` |
| `container` | Cross at the container's outer edges | `DockOverlay._compute_drop_rect()`, `DockOverlayCross._area_grid_position()`, `dock_paint.create_high_dpi_drop_indicator_pixmap()` |

### 3.5 `DragState`

| Member | Meaning | Set / read by |
| :--- | :--- | :--- |
| `inactive` | No drag | `DockWidgetTab`, `DockAreaTitleBar` and the floating containers: initial state, and after release |
| `mouse_pressed` | Pressed, not yet past the drag distance | `DockWidgetTab.mousePressEvent()`, `DockAreaTitleBar.mousePressEvent()`, `FloatingDockContainer.event()` / `moveEvent()`, `FramelessFloatingDockContainer._handle_titlebar_drag()` |
| `tab` | Reordering a tab inside its tab bar | `DockWidgetTab.mouseMoveEvent()` / `mouseReleaseEvent()` |
| `floating_widget` | Dragging a floating window; drop overlays live | `DockWidgetTab._start_floating()`, `DockAreaTitleBar._start_floating()`, `DockAreaTabBar.make_area_floating()`, `FloatingContainerBehaviour._set_state()` |

### 3.6 `InsertionOrder`

Set with `DockManager.menu_insertion_order` (default `by_spelling`); a change calls
`DockManager._rebuild_view_menu()`.

| Member | Meaning | Read by |
| :--- | :--- | :--- |
| `by_spelling` | View menu sorted by title | `DockManager.add_toggle_view_action_to_menu()` |
| `by_insertion` | View menu in registration order | `DockManager._rebuild_view_menu()` |

### 3.7 `DockWidgetFeature`

`IntFlag` on `DockWidget.features()` / `set_features()`. A dock area's features are the
intersection of its widgets' (`DockAreaWidget.features()`). A widget locked to an area
(`locked_to_area`, or a `locked_name` area) loses `floatable` and `pinnable` in
`DockWidget.features()`.

| Member | Value | Meaning | Read by |
| :--- | :---: | :--- | :--- |
| `no_features` | 0 | Nothing allowed | — |
| `closable` | 1 | Can be closed | `DockAreaTitleBar.update_button_states()` / `on_close_button_clicked()`, `DockAreaWidget.closable()` / `close_area()`, `DockContainerWidget._on_visible_dock_area_count_changed()`, tab and sidebar menus |
| `movable` | 2 | Can be dragged to another area or sidebar | `DockWidgetTab._movable()`, `DockAreaWidget.movable()`, `SidebarManager.move_widget_to_area()`, `SidebarDragController.on_tab_drag_started()`, `SideBarTitleBar._on_drag_started()` |
| `floatable` | 4 | Can be floated | `DockWidgetTab._floatable()`, `DockAreaWidget.floatable()`, `DockAreaTitleBar.update_button_states()`, `SidebarDragController.on_tab_drag_started()` |
| `pinnable` | 8 | Can be pinned to a sidebar | `DockAreaWidget.pinnable()`, `DockAreaTitleBar.update_button_states()`, `DockContainerWidget._on_visible_dock_area_count_changed()`, `dock_menu.build_dock_context_menu()`, `SidebarManager.pin_widget()` |
| `all_features` | 15 | All four | `DockWidget.__init__()` (the default), `DockAreaWidget.features()`, `DockContainerWidget.features()` |

### 3.8 `WidgetState`

Kept on the widget by `DockWidget.set_widget_state()`; `DockWidget.is_in_sidebar()` tests
for the two pinned states.

| Member | Meaning | Set by |
| :--- | :--- | :--- |
| `docked` | In a dock area | `DockWidget.__init__()`, `DockWidget.set_dock_area()`, `SidebarManager.unpin_widget()` |
| `floating` | In a floating window | `FloatingDockContainer.__init__()`; read by `DockWidget.tool_bar_style()` / `tool_bar_icon_size()` |
| `pinned_shown` | In a sidebar, panel open | `SidebarOverlayController.show_for_button()` |
| `pinned_hidden` | In a sidebar, panel closed | `SidebarManager.pin_widget()` / `hide_widget()`, `SidebarOverlayController.close_overlay()` |

The tab and title-bar menus (`_menu_is_pinned()`) read both pinned states to offer
Unpin instead of Pin.

### 3.9 `InsertMode`

Argument of `DockWidget.set_widget(widget, insert_mode=InsertMode.auto_scroll_area)`.

| Member | Meaning |
| :--- | :--- |
| `auto_scroll_area` | Wrap in a `QScrollArea` unless the widget is one already (default) |
| `force_scroll_area` | Same as `auto_scroll_area` (see §2) |
| `force_no_scroll_area` | Add the widget directly, without a scroll area |

### 3.10 `ToggleViewActionMode`

Set with `DockWidget.set_toggle_view_action_mode()`.

| Member | Meaning |
| :--- | :--- |
| `toggle` | Checkable action: show ↔ hide |
| `show` | Plain action: only shows the widget, making it the current tab |

### 3.11 `SideBarFocusBehavior`

Set with `DockManager.sidebar_focus_behavior`, which forwards to
`SidebarManager.focus_behavior` and each `SideBarContainer`.

| Member | Meaning | Read by |
| :--- | :--- | :--- |
| `take_focus_and_restore` | The panel takes focus when it opens and hands it back when it closes (default) | `SideBarContainer.show_widget()`, `_on_anim_finished()`, `_on_hide_finished()` |
| `no_focus_transfer` | Focus is left alone | — (see §2) |
| `take_focus_only` | The panel takes focus and doesn't hand it back | `SideBarContainer.show_widget()`, `_on_anim_finished()` |

### 3.12 `TitleBarMode`

Set with `DockManager.title_bar_mode` (default `native`).

| Member | Meaning | Read by |
| :--- | :--- | :--- |
| `native` | Floating windows use the OS title bar | `DockManager.__init__()` |
| `custom` | Floating windows are frameless with Lace's title bar (`qframelesswindow`) | `DockManager.floating_container_class()`, which then returns `FramelessFloatingDockContainer` |

The main window's frame is chosen by its class (`QMainWindow` or
`FramelessLaceMainWindow`), not by this mode.

### 3.13 `TabBadgePosition`

Set with `SidebarManager.badge_position` / `set_badge_position()` (default `top_right`),
which applies it to every `VerticalTabButton`.

| Member | Read by |
| :--- | :--- |
| `top_left`, `top_right`, `bottom_left`, `bottom_right` | `VerticalTabButton._draw_badge()` |

### 3.14 `DockStyleCategory`

Each member names one schema of theme tokens (`CORE` → `DockCoreStyleSchema`, and so
on) and is the key a component subscribes with: after
`DockStyleManager.register(obj, category)`, the manager calls
`obj.on_style_changed(category, changes)` when that group changes. `DockStyled`
classes list theirs in `_STYLE_CATEGORIES`.

| Member | Tokens for | Main readers |
| :--- | :--- | :--- |
| `CORE` | Card surface, borders, radius, accent, canvas | `DockAreaWidget`, `DockAreaTitleBar`, `DockWidget`, `DockWidgetTab`, sidebar panels, `FramelessTitleBarStyler`, `title_bar_colors()` |
| `PANEL` | Panel content background | `DockAreaWidget`, `DockWidget`, `FramelessTitleBarStyler` |
| `TAB` | Dock tabs | `DockWidgetTab`, `DockAreaTabBar`, `DockAreaTitleBar`, `VerticalTabButton` |
| `TITLE_BAR` | Area title bars, chrome buttons, the custom window title bar | `DockAreaTitleBar`, `DockWidgetTab`, sidebar panels, `FramelessTitleBarStyler`, `title_bar_colors()` |
| `SIDEBAR` | Sidebar strips and tabs, window title-bar background | `SideTabBar`, `VerticalTabButton`, `SideBarContainer`, `DockMenuBarStyler`, `DockIconProvider`, `title_bar_colors()` |
| `SIDEPANEL` | Open sidebar panels | `SideBarContainer`, `SideBarTitleBar`, `DockWidget` (when pinned) |
| `SPLITTER` | Splitter handles | `DockSplitterHandle` |
| `OVERLAY` | Drop overlays and their cross | `DockOverlay`, `DockOverlayCross`, `SideBarTitleBar` |

`DockThemeBridge` subscribes to CORE, TAB, TITLE_BAR, PANEL, SIDEBAR and SIDEPANEL to
rebuild the `QPalette`.

### 3.15 `MenuSection`

`Flag` choosing which sections `dock_menu.build_dock_context_menu()` builds from a
`MenuContext`.

| Member | Section |
| :--- | :--- |
| `NONE` | Empty mask |
| `TAB_LIST` | Checkable list of the area's tabs |
| `PIN` | Pin to a sidebar |
| `UNPIN` | Unpin from a sidebar |
| `DETACH` | Float, or dock back |
| `MAXIMIZE` | Maximize / restore the area |
| `CLOSE` | Close the area or tab |
| `CLOSE_OTHERS` | Close other areas / tabs |
| `TITLE_BAR` | Preset `TAB_LIST \| PIN \| MAXIMIZE \| DETACH \| CLOSE \| CLOSE_OTHERS`, used by `DockAreaTitleBar` |
| `TAB` | Preset `PIN \| MAXIMIZE \| DETACH \| CLOSE \| CLOSE_OTHERS`, used by `DockWidgetTab` |
| `SIDEBAR_TAB` | Preset `UNPIN \| DETACH \| CLOSE \| MAXIMIZE`, used by `SideBarTitleBar` |

`SideTabBar` uses its own mask: `TAB_LIST | PIN | DETACH | CLOSE | CLOSE_OTHERS`.

---

## 4. Checks

The smoke checks in `dev_smoke/` exercise the wiring:

| Check | Covers |
| :--- | :--- |
| `smoke_flags.py` | `DockFlags` |
| `smoke_movable.py` | `DockWidgetFeature.movable` |
| `smoke_pin_button.py` | `TitleBarButton.pin`, `pinnable` |
| `smoke_tab_icons.py` | `DockFlags.custom_tab_icons` |
| `smoke_insertion_order.py` | `InsertionOrder` |
| `smoke_sidebar.py` | `TabBadgePosition`, the pinned `WidgetState`s |
| `smoke_maximize.py` | the maximize flags and button |
| `smoke_frameless_winstate.py` | `TitleBarMode.custom` floats |

Run them all with `python dev_smoke/run_all.py`; `tests/` covers the enums and config
masks.
