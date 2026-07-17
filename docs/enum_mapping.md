# Lace System: Enumerations & Flags Comprehensive Mapping (`enump_mapping.md`)

This document provides a comprehensive, structured mapping of all **13 enumerations and flag classes** across the **Lace** docking and sidebar architecture (`lace/enums.py`, `lace/sidebar_tab.py`, and `lace/dock_theme.py`). It documents the architectural responsibility of every enumeration, provides member-by-member descriptions with exact clickable file paths and line links, and highlights which enumerations or flags are **currently unwired or inactive** in the codebase.

*(Note: A canonical copy of this documentation is also maintained under [docs/enum_mapping.md](file:///d:/User/Documents/Python/Lace/Lace/docs/enum_mapping.md)).*

---

## 1. Executive Summary & Quick Reference Table

| Enum / Flag Class | Type | Location | Total Members | Wiring Status | Primary Responsibility |
| :--- | :--- | :--- | :---: | :---: | :--- |
| **`DockWidgetArea`** | `IntFlag` | [lace/enums.py:42](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L42) | 9 | ✅ **Fully Wired** | Physical regions within a window (`left`, `right`, `top`, `bottom`, `center`) where widgets can dock. |
| **`DockFlags`** | `IntFlag` | [lace/enums.py:77](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L77) | 16 | ⚠️ **Partially Wired** | Global system configuration flags controlling features, appearance, and drag-and-drop behavior. |
| **`TitleBarButton`** | `Enum` | [lace/enums.py:148](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L148) | 4 | ✅ **Fully Wired** | Identifiers for standard interactive buttons (`tabs_menu`, `undock`, `close`, `pin`) on dock area title bars. |
| **`OverlayMode`** | `Enum` | [lace/enums.py:158](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L158) | 2 | ✅ **Fully Wired** | Dictates whether drop-zone overlays target a specific dock area (`dock_area`) or the root container (`container`). |
| **`DragState`** | `Enum` | [lace/enums.py:166](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L166) | 4 | ✅ **Fully Wired** | Tracks the active mouse interaction and dragging state (`inactive`, `mouse_pressed`, `tab`, `floating_widget`). |
| **`InsertionOrder`** | `Enum` | [lace/enums.py:176](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L176) | 2 | ✅ **Fully Wired** | Specifies sorting order (`by_spelling`, `by_insertion`) when populating dynamic view menus (`DockManager.view_menu`). |
| **`DockWidgetFeature`** | `IntFlag` | [lace/enums.py:184](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L184) | 6 | ✅ **Fully Wired** | Per-widget capabilities gating interactions (`closable`, `movable`, `floatable`, `pinnable`). |
| **`WidgetState`** | `Enum` | [lace/enums.py:207](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L207) | 4 | ✅ **Fully Wired** | Current placement and attachment mode of a `DockWidget` (`docked`, `floating`, `pinned_shown`, `pinned_hidden`). |
| **`InsertMode`** | `Enum` | [lace/enums.py:227](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L227) | 3 | ✅ **Fully Wired** | Rules for wrapping child content inside a `QScrollArea` during widget insertion. |
| **`ToggleViewActionMode`** | `Enum` | [lace/enums.py:240](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L240) | 2 | ✅ **Fully Wired** | Controls whether a `DockWidget`'s menu action acts as a checkable toggle or a one-way show trigger. |
| **`SideBarFocusBehavior`** | `Enum` | [lace/enums.py:251](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L251) | 3 | ✅ **Fully Wired** | Configures keyboard focus transfer when sliding sidebar overlays out and in. |
| **`TabBadgePosition`** | `Enum` | [lace/sidebar_tab.py:23](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_tab.py#L23) | 4 | ✅ **Fully Wired** | Specifies the corner positioning of numerical notification badges on vertical sidebar tabs (`top_left`, `top_right`, `bottom_left`, `bottom_right`). |
| **`DockStyleCategory`** | `Enum` | [lace/dock_theme.py:15](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_theme.py#L15) | 8 | ✅ **Fully Wired** | Design system component categories (`CORE`, `PANEL`, `TAB`, `TITLE_BAR`, `SIDEBAR`, `SIDEPANEL`, `SPLITTER`, `OVERLAY`) for token and icon lookups. |

---

## 2. Summary of Unwired & Inactive Enums / Members

The following table categorizes all enum definitions or specific members that exist in the source code but are **not wired up to any method or function** across the Lace system.

| Enum / Member | Location | Status | Current Behavior in Codebase | Recommended Resolution / Missing Connection |
| :--- | :--- | :--- | :--- | :--- |
| **`InsertionOrder`** *(All members)* | [lace/enums.py:176](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L176) | ✅ **Resolved & Fully Wired** | Wired via `DockManager.menu_insertion_order` property ([lace/dock_manager.py:346](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_manager.py#L346)), `add_toggle_view_action_to_menu()`, and `_rebuild_view_menu()`. When `by_spelling` is active, menu items are sorted alphabetically by title (`action.text().lower()`). When `by_insertion` is selected, actions are ordered chronologically by widget registration. | Verified across `smoke_insertion_order.py` dev smoke tests. |
| **`TabBadgePosition`** *(All members)* | [lace/sidebar_tab.py:23](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_tab.py#L23) | ✅ **Resolved & Fully Wired** | Wired in `VerticalTabButton.__init__()` via `badge_position: TabBadgePosition = TabBadgePosition.top_right` ([lace/sidebar_tab.py:38](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_tab.py#L38)), exposed via `badge_position` property and `set_badge_position()` setter, and dynamically read by `VerticalTabButton._draw_badge()` to position `badge_rect` across all four corners (`top_left`, `top_right`, `bottom_left`, `bottom_right`). Also wired to `refresh_style()` and `DockSidebarStyleSchema` for style-driven corner placement. | Verified across `smoke_sidebar.py` dev smoke tests. |
| **`DockFlags.opaque_undocking`** | [lace/enums.py:88](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L88) | ✅ **Resolved & Fully Wired** | Included in `DockFlags.default_config` ([lace/enums.py:139](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L139)) and checked inside `FloatingDockContainer._set_state()` ([lace/floating_dock_container.py:270](file:///d:/User/Documents/Python/Lace/Lace/lace/floating_dock_container.py#L270)) and during `start_floating()` when dragging floating containers or tearing off tabs (`DockWidgetTab._start_floating` and `DockAreaTitleBar._start_floating`). When enabled, the floating window maintains 100% opacity (`1.0`) during undocking and dragging; when disabled, it renders semi-transparently (`0.6`). | Verified across `smoke_flags.py` dev smoke tests. |
| **`DockFlags.custom_tab_icons`** | [lace/enums.py:126](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L126) | ✅ **Resolved & Fully Wired** | Checked in `DockWidgetTab.update_icon()` ([lace/dock_widget_tab.py:437](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget_tab.py#L437)) to switch dynamically between user-configured custom icons (`set_custom_icon_name()` / `set_custom_icon()`) versus default widget icons (`set_default_icon_name()` / `set_icon()`) via `DockIconProvider.get()`. Also hooked into `DockManager.notify_config_flags_changed()` ([lace/dock_manager.py:309](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_manager.py#L309)) to refresh all tab icons instantly upon runtime flag updates. | Verified across `smoke_tab_icons.py` dev smoke tests. |
| **`DockFlags.chromeless_float`** | [lace/enums.py:135](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L135) | ✅ **Resolved & Fully Wired** | Checked inside `FloatingDockContainer.__init__()` ([lace/floating_dock_container.py:79](file:///d:/User/Documents/Python/Lace/Lace/lace/floating_dock_container.py#L79)) and dynamically updated via `update_window_flags_from_config()` inside `DockManager.notify_config_flags_changed()` ([lace/dock_manager.py:308](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_manager.py#L308)). When enabled (`Qt.FramelessWindowHint`), floating windows are rendered chromeless without native OS titlebars/borders, relying cleanly on Lace's custom `DockAreaTitleBar` for window dragging and manipulation. | Verified across `smoke_flags.py` dev smoke tests. |
| **`DockWidgetFeature.movable`** | [lace/enums.py:194](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L194) | ✅ **Resolved & Fully Wired** | Checked in `DockWidgetTab.mouseMoveEvent` ([lace/dock_widget_tab.py:212](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget_tab.py#L212)) and `DockAreaTitleBar.mouseMoveEvent` ([lace/dock_area_title_bar.py:576](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_area_title_bar.py#L576)) before initiating tab or floating window drags. Checked in `FloatingDockContainer._finalize_drag` ([lace/floating_dock_container.py:128](file:///d:/User/Documents/Python/Lace/Lace/lace/floating_dock_container.py#L128)) to prevent dropping immovable floating windows into containers, in `SidebarManager.move_widget_to_area` ([lace/sidebar_manager.py:548](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_manager.py#L548)) to block transferring pinned immovable tabs between sidebars, and in `SidebarManager.on_tab_drag_started` ([lace/sidebar_manager.py:228](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_manager.py#L228)) & `SideBarTitleBar._on_drag_started` ([lace/sidebar_title_bar.py:126](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_title_bar.py#L126)) to block dragging tabs/panels out of sidebars (`while allowing unpin/float/close via menus and buttons`). | Verified across `smoke_movable.py` dev smoke tests. |
| **`TitleBarButton.tabs_menu` & `.pin`** | [lace/enums.py:152, 155](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L152) | ✅ **Resolved & Fully Wired** (`.pin`) / ⚠️ **Internal** (`.tabs_menu`) | `TitleBarButton.pin` is mapped inside `DockAreaTitleBar.button(which)` ([lace/dock_area_title_bar.py:516](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_area_title_bar.py#L516)) and externally queried by `DockContainerWidget` ([lace/dock_container_widget.py:654](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_container_widget.py#L654)) when updating top-level window button visibility and state transitions (`_update_title_bar_button_states`). `TitleBarButton.tabs_menu` is internally managed by `DockAreaTitleBar` for popup tab menus. | Verified across `smoke_pin_button.py` dev smoke tests. |

---

## 3. Detailed Breakdown of Each Enumeration

### 3.1 `DockWidgetArea` (`IntFlag`)
* **File Location:** [lace/enums.py:42-75](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L42-L75)
* **Type & Bitwise Behavior:** `enum.IntFlag`. Uses `enum.auto()` (powers of two) to assign individual cardinal directions, allowing bitwise OR (`|`) combinations (e.g., `DockWidgetArea.left | DockWidgetArea.right`) and bitwise AND (`&`) testing.
* **Primary Responsibility:** Represents the physical layout zones within a `DockContainerWidget` ([lace/dock_container_widget.py](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_container_widget.py)) or `SideBarContainer` ([lace/sidebar_container.py](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_container.py)) where a `DockWidget` can be dropped, split, or docked.

#### Members Table
| Member | Value | Description | Exact Wiring Location / Code Path |
| :--- | :---: | :--- | :--- |
| `no_area` | `0` | State with no defined docking area. | ✅ **Wired** across `DockAreaLayout` ([lace/dock_area_layout.py](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_area_layout.py)) & drop checks |
| `left` | `1` | The leftmost docking region / left sidebar area. | ✅ **Wired** in `SideBarContainer` ([lace/sidebar_container.py:108](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_container.py#L108)) & layout splitting |
| `right` | `2` | The rightmost docking region / right sidebar area. | ✅ **Wired** in `SideBarContainer` ([lace/sidebar_container.py:108](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_container.py#L108)) & layout splitting |
| `top` | `4` | The uppermost docking region / top sidebar area. | ✅ **Wired** in `SideBarContainer` ([lace/sidebar_container.py:108](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_container.py#L108)) & layout splitting |
| `bottom` | `8` | The lowermost docking region / bottom sidebar area. | ✅ **Wired** in `SideBarContainer` ([lace/sidebar_container.py:108](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_container.py#L108)) & layout splitting |
| `center` | `16` | The central area, reserved for main workspace tabs. | ✅ **Wired** in `DockPaint.paint_overlay()` ([lace/dock_paint.py:246](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_paint.py#L246)) |
| `invalid` | `0` | Alias for `no_area`, indicating an invalid dock operation. | ✅ **Wired** in `DockOverlay` geometry checks ([lace/dock_overlay.py:276](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_overlay.py#L276)) |
| `outer_dock_areas` | `15` | Mask (`left \| right \| top \| bottom`) for all edge areas. | ✅ **Wired** across overlay masks & sidebar area validation |
| `all_dock_areas` | `31` | Mask (`outer_dock_areas \| center`) for all areas. | ✅ **Wired** across `DockContainerWidget` ([lace/dock_container_widget.py](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_container_widget.py)) |

#### Architectural Usage across Codebase
* **`DockAreaLayout` & `DockContainerWidget` ([lace/dock_container_widget.py](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_container_widget.py))**: Determines splitter insertion direction (`Qt.Horizontal` for `left`/`right`, `Qt.Vertical` for `top`/`bottom`).
* **`SideBarManager` ([lace/sidebar_manager.py:38](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_manager.py#L38)) & `SideBarContainer` ([lace/sidebar_container.py:108](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_container.py#L108))**: Maps `DockWidgetArea.left`, `right`, `top`, `bottom` directly to the four peripheral sidebar overlays (`SidebarManager._sidebars[area]`).
* **`DockOverlay` ([lace/dock_overlay.py:276](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_overlay.py#L276)) & `dock_paint.py` ([lace/dock_paint.py:192](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_paint.py#L192))**: Computes mouse drop-zone hitboxes and paints translucent drop indicator overlays (`paint_overlay(...)`).

---

### 3.2 `DockFlags` (`IntFlag`)
* **File Location:** [lace/enums.py:77-146](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L77-L146)
* **Type & Bitwise Behavior:** `enum.IntFlag`. Uses `enum.auto()` to assign bit flags. Stored on `DockManager.config_flags` via `set_config_flags()` ([lace/dock_manager.py](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_manager.py)).
* **Primary Responsibility:** Global configuration switches controlling tab rendering, button visibility, dragging permissions, and system visuals.

#### Members Table
| Member | Description | Exact Wiring Location / Code Path |
| :--- | :--- | :--- |
| `none_` | Base zero flag (`0`). | ✅ **Wired** across flag initializations ([lace/enums.py:81](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L81)) |
| `opaque_splitter_resize` | Splitters instantly resize content instead of rubber-banding. | ✅ **Wired** inside `DockContainerWidget._new_splitter()` ([lace/dock_container_widget.py:648](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_container_widget.py#L648)) |
| `opaque_undocking` | Floating windows maintain 100% opacity (`1.0`) while dragging instead of semi-transparent (`0.6`). | ✅ **Wired** inside `FloatingDockContainer._set_state()` ([lace/floating_dock_container.py:278](file:///d:/User/Documents/Python/Lace/Lace/lace/floating_dock_container.py#L278)) |
| `always_show_tabs` | Tabs always shown, even with only 1 widget in the area. | ✅ **Wired** in `DockAreaTabBar.update_tab_bar_visibility()` ([lace/dock_area_tab_bar.py:84](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_area_tab_bar.py#L84)) |
| `show_tab_close_button` | Tabs display their own individual close button. | ✅ **Wired** in `DockWidgetTab.update_close_button_visibility()` ([lace/dock_widget_tab.py:361](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget_tab.py#L361)) |
| `active_tab_has_close_button` | Only the currently active tab displays a close button. | ✅ **Wired** in `DockWidgetTab.update_close_button_visibility()` ([lace/dock_widget_tab.py:362](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget_tab.py#L362)) |
| `dock_area_has_close_button` | Dock area title bar displays a close button. | ✅ **Wired** in `DockAreaTitleBar.update_title_bar_button_visibility()` ([lace/dock_area_title_bar.py:327](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_area_title_bar.py#L327)) |
| `dock_area_close_button_closes_tab` | Title bar close button closes active tab, not entire area. | ✅ **Wired** in `DockAreaTitleBar.on_close_clicked()` ([lace/dock_area_title_bar.py:140, 474](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_area_title_bar.py#L140)) |
| `dock_area_has_undock_button` | Title bar displays an undock (detach to float) button. | ✅ **Wired** in `DockAreaTitleBar.update_title_bar_button_visibility()` ([lace/dock_area_title_bar.py:340](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_area_title_bar.py#L340)) |
| `dock_area_has_pin_button` | Title bar displays a pin/unpin button for sidebar docking. | ✅ **Wired** in `DockAreaTitleBar.update_title_bar_button_visibility()` ([lace/dock_area_title_bar.py:362](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_area_title_bar.py#L362)) |
| `dock_area_has_tabs_menu_button` | Title bar displays a menu button listing all open tabs. | ✅ **Wired** in `DockAreaTitleBar` ([lace/dock_area_title_bar.py:106, 313](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_area_title_bar.py#L106)) |
| `middle_mouse_button_closes_tab` | Middle-clicking a tab closes it. | ✅ **Wired** in `DockWidgetTab.mouseReleaseEvent()` ([lace/dock_widget_tab.py:191](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget_tab.py#L191)) |
| `floatable_tabs` | Tabs can be dragged out to float in top-level windows. | ✅ **Wired** across `DockAreaTitleBar` ([lace/dock_area_title_bar.py:209](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_area_title_bar.py#L209)) & `DockWidgetTab` ([lace/dock_widget_tab.py:168](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget_tab.py#L168)) |
| `pinnable_tabs` | Tabs can be pinned into sidebars. | ✅ **Wired** across `DockAreaTitleBar` ([lace/dock_area_title_bar.py:210](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_area_title_bar.py#L210)), `DockWidgetTab` ([lace/dock_widget_tab.py:174](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget_tab.py#L174)), & `SidebarManager` ([lace/sidebar_manager.py:405](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_manager.py#L405)) |
| `custom_tab_icons` | Use custom icons via user config instead of widget defaults. | ✅ **Wired** in `DockWidgetTab.update_icon()` ([lace/dock_widget_tab.py:437](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget_tab.py#L437)) & `DockManager.notify_config_flags_changed()` ([lace/dock_manager.py:309](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_manager.py#L309)) |
| `hide_disabled_title_bar_icons` | Hides disabled icons in the title bar instead of graying. | ✅ **Wired** in `DockAreaTitleBar.update_title_bar_button_visibility()` ([lace/dock_area_title_bar.py:293](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_area_title_bar.py#L293)) |
| `chromeless_float` | Floating container windows are created without native OS title bars or borders (`FramelessWindowHint`). | ✅ **Wired** in `FloatingDockContainer.__init__()` ([lace/floating_dock_container.py:79](file:///d:/User/Documents/Python/Lace/Lace/lace/floating_dock_container.py#L79)) & `update_window_flags_from_config()` |
| `default_config` | Combined bitmask of all standard default flags. | ✅ **Wired** as default argument on `DockManager.__init__()` ([lace/enums.py:138](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L138)) |

---

### 3.3 `TitleBarButton` (`Enum`)
* **File Location:** [lace/enums.py:148-156](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L148-L156)
* **Type & Bitwise Behavior:** `enum.Enum`. Sequential identifiers for buttons located on dock area title bars.
* **Primary Responsibility:** Provides a unified enum key to retrieve specific `QAbstractButton` instances (`QToolButton`) from `DockAreaTitleBar.button(which)` ([lace/dock_area_title_bar.py:509](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_area_title_bar.py#L509)) or `DockAreaWidget.title_bar_button(which)` ([lace/dock_area_widget.py:333](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_area_widget.py#L333)).

#### Members Table
| Member | Description | Exact Wiring Location / Code Path |
| :--- | :--- | :--- |
| `tabs_menu` | The dropdown button listing all tabs in the dock area. | ⚠️ **Internal Only** (Mapped inside `DockAreaTitleBar.button()` in [lace/dock_area_title_bar.py:510](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_area_title_bar.py#L510), never looked up externally) |
| `undock` | The detach button (`float`) that moves the area to a floating window. | ✅ **Fully Wired** (Looked up externally in `DockContainerWidget` ([lace/dock_container_widget.py:431, 614, 631](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_container_widget.py#L431))) |
| `close` | The close button that closes the active tab or dock area. | ✅ **Fully Wired** (Looked up externally in `DockContainerWidget` ([lace/dock_container_widget.py:433, 624, 627, 633](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_container_widget.py#L433))) |
| `pin` | The pin button (`pin`/`unpin`) that pins the area to a sidebar. | ✅ **Fully Wired** (Looked up externally in `DockContainerWidget` ([lace/dock_container_widget.py:437, 626, 633](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_container_widget.py#L437)) & toggled in `DockAreaTitleBar.on_pin_button_clicked` ([lace/dock_area_title_bar.py:488](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_area_title_bar.py#L488))) |

#### Architectural Usage across Codebase
* **`DockAreaTitleBar.button(which)` ([lace/dock_area_title_bar.py:509](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_area_title_bar.py#L509))**: Returns `self._tabs_menu_button`, `self._undock_button`, `self._close_button`, or `self._pin_button` based on the enum argument.
* **`DockContainerWidget.update_top_level_button_states()` & `_on_visible_dock_area_count_changed()` ([lace/dock_container_widget.py:431-438, 654](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_container_widget.py#L431))**: Calls `top_level_dock_area.title_bar_button(TitleBarButton.undock)`, `TitleBarButton.close`, and `TitleBarButton.pin` to dynamically update button visibility and state when floating container layouts change.

---

### 3.4 `OverlayMode` (`Enum`)
* **File Location:** [lace/enums.py:158-164](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L158-L164)
* **Type & Bitwise Behavior:** `enum.Enum`.
* **Primary Responsibility:** Controls how translucent drop indicator crosses (`DockOverlay` in [lace/dock_overlay.py](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_overlay.py)) and drop-zone hitboxes are rendered when a widget is dragged over the window.

#### Members Table
| Member | Description | Exact Wiring Location / Code Path |
| :--- | :--- | :--- |
| `dock_area` | Overlay cross targets a specific target `DockAreaWidget` (center/tab split). | ✅ **Fully Wired** in `DockManager.__init__()` ([lace/dock_manager.py:81](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_manager.py#L81)) & `DockOverlay` ([lace/dock_overlay.py:276](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_overlay.py#L276)) |
| `container` | Overlay cross targets the outer margins of the `DockContainerWidget` (global edge split). | ✅ **Fully Wired** in `DockManager.__init__()` ([lace/dock_manager.py:82](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_manager.py#L82)) & `DockPaint` ([lace/dock_paint.py:246](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_paint.py#L246)) |

#### Architectural Usage across Codebase
* **`DockManager.__init__()` ([lace/dock_manager.py:81-82](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_manager.py#L81))**: Instantiates `self._dock_area_overlay = DockOverlay(self._root, OverlayMode.dock_area)` and `self._container_overlay = DockOverlay(self._root, OverlayMode.container)`.
* **`DockOverlay.setup_overlay_cross()` ([lace/dock_overlay.py:339](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_overlay.py#L339))**: Adjusts the scale factor and position of the 5-way drop indicator cross based on whether `mode == OverlayMode.container` (outer edge cross) vs `OverlayMode.dock_area` (local card cross).
* **`dock_paint.py.paint_overlay()` ([lace/dock_paint.py:192](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_paint.py#L192))**: Draws either the container-wide perimeter drop indicator (`OverlayMode.container`) or card-local split indicator (`OverlayMode.dock_area`).

---

### 3.5 `DragState` (`Enum`)
* **File Location:** [lace/enums.py:166-174](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L166-L174)
* **Type & Bitwise Behavior:** `enum.Enum`.
* **Primary Responsibility:** State machine state tracking the current drag-and-drop interaction context across `DockWidgetTab` ([lace/dock_widget_tab.py](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget_tab.py)), `DockAreaTitleBar` ([lace/dock_area_title_bar.py](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_area_title_bar.py)), and `FloatingDockContainer` ([lace/floating_dock_container.py](file:///d:/User/Documents/Python/Lace/Lace/lace/floating_dock_container.py)).

#### Members Table
| Member | Description | Exact Wiring Location / Code Path |
| :--- | :--- | :--- |
| `inactive` | No drag operation is currently occurring. | ✅ **Fully Wired** across tabs ([lace/dock_widget_tab.py:62](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget_tab.py#L62)) & floating containers ([lace/floating_dock_container.py:54](file:///d:/User/Documents/Python/Lace/Lace/lace/floating_dock_container.py#L54)) |
| `mouse_pressed` | Mouse pressed down, waiting to exceed start drag distance threshold. | ✅ **Fully Wired** in `DockWidgetTab` ([lace/dock_widget_tab.py:187](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget_tab.py#L187)) & `FloatingDockContainer` ([lace/floating_dock_container.py:416](file:///d:/User/Documents/Python/Lace/Lace/lace/floating_dock_container.py#L416)) |
| `tab` | Actively dragging a tab within its parent `DockAreaTabBar`. | ✅ **Fully Wired** inside `DockWidgetTab.mouseMoveEvent()` ([lace/dock_widget_tab.py:201, 250](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget_tab.py#L201)) |
| `floating_widget` | Actively dragging a detached floating window (`FloatingDockContainer`). | ✅ **Fully Wired** across `FloatingDockContainer.moveEvent()` ([lace/floating_dock_container.py:346](file:///d:/User/Documents/Python/Lace/Lace/lace/floating_dock_container.py#L346)) |

#### Architectural Usage across Codebase
* **`DockWidgetTab` & `DockAreaTitleBar` ([lace/dock_widget_tab.py:187](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget_tab.py#L187))**: In `mousePressEvent()`, `_drag_state = DragState.mouse_pressed`. When dragging exceeds `start_drag_distance()`, if floating is permitted, transitions to `DragState.floating_widget` (`_start_floating()`) or `DragState.tab`. On mouse release, transitions back to `DragState.inactive`.
* **`FloatingDockContainer.moveEvent()` & `mouseReleaseEvent()` ([lace/floating_dock_container.py:346](file:///d:/User/Documents/Python/Lace/Lace/lace/floating_dock_container.py#L346))**: Tracks `_dragging_state`. When `DragState.floating_widget` is active, signals `DockManager` to update drop-zone overlays (`signals.request_overlay_show`). When dropped (`mouseReleaseEvent`), emits `signals.floating_widget_dropped` and resets to `DragState.inactive`.

---

### 3.6 `InsertionOrder` (`Enum`)
* **File Location:** [lace/enums.py:176-182](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L176-L182)
* **Type & Bitwise Behavior:** `enum.Enum`.
* **Primary Responsibility:** Intended to govern the sorting order of dock widget items when inserted into dynamic "Show View" dropdown menus (`DockManager._view_menu`).

#### Members Table
| Member | Description | Exact Wiring Location / Code Path |
| :--- | :--- | :--- |
| `by_spelling` | Sort menu items alphabetically by their title string. | ✅ **Fully Wired** ([lace/dock_manager.py:346](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_manager.py#L346) via `add_toggle_view_action_to_menu` and `_rebuild_view_menu`) |
| `by_insertion` | Sort menu items in the exact chronological order they were registered. | ✅ **Fully Wired** ([lace/dock_manager.py:346](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_manager.py#L346) via `add_toggle_view_action_to_menu` and `_rebuild_view_menu`) |

#### Architectural Usage across Codebase
* **`DockManager.menu_insertion_order` ([lace/dock_manager.py:346](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_manager.py#L346))**: Property getter and setter controlling whether actions inserted into `DockManager.view_menu` or group submenus (`add_toggle_view_action_to_menu()`) are ordered alphabetically (`by_spelling`) or chronologically (`by_insertion`). When the property is changed at runtime, `_rebuild_view_menu()` dynamically re-sorts all registered `toggle_view_action()` items.
* **`DockManager.add_dock_widget()` & `add_sidebar_widget()` ([lace/dock_manager.py:110, 131](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_manager.py#L110))**: Automatically registers each dock widget's `toggle_view_action()` into `self.view_menu` respecting the active sorting rule (`add_toggle_view_action_to_menu`). Conversely, `remove_dock_widget()` removes the action from the menu.

---

### 3.7 `DockWidgetFeature` (`IntFlag`)
* **File Location:** [lace/enums.py:184-205](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L184-L205)
* **Type & Bitwise Behavior:** `enum.IntFlag`. Uses `enum.auto()` (powers of two) to assign individual capabilities (`closable`, `movable`, `floatable`, `pinnable`) per `DockWidget` (`dock_widget.features()`). Can be tested with bitwise AND (`widget.features() & DockWidgetFeature.closable`).
* **Primary Responsibility:** Fine-grained permission gating defining what actions a user can perform on a specific `DockWidget`.

#### Members Table
| Member | Value | Description | Exact Wiring Location / Code Path |
| :--- | :---: | :--- | :--- |
| `no_features` | `0` | Widget cannot be moved, closed, floated, or pinned. | ✅ **Wired** in `SideBarTitleBar.update_buttons()` ([lace/sidebar_title_bar.py:134](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_title_bar.py#L134)) |
| `closable` | `1` | Widget can be closed (via close buttons or context menu). | ✅ **Wired** across `DockWidgetTab` ([lace/dock_widget_tab.py:360](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget_tab.py#L360)) & `DockContainerWidget` ([lace/dock_container_widget.py:621](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_container_widget.py#L621)) |
| `movable` | `2` | Widget can be dragged and moved between dock areas. | ✅ **Wired** across `DockWidgetTab._movable` ([lace/dock_widget_tab.py:167](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget_tab.py#L167)), `DockAreaWidget.movable` ([lace/dock_area_widget.py:322](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_area_widget.py#L322)), `DockAreaTitleBar` ([lace/dock_area_title_bar.py:531, 575](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_area_title_bar.py#L531)), `FloatingDockContainer._is_movable` ([lace/floating_dock_container.py:188](file:///d:/User/Documents/Python/Lace/Lace/lace/floating_dock_container.py#L188)), & `SidebarManager.move_widget_to_area` ([lace/sidebar_manager.py:548](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_manager.py#L548)) |
| `floatable` | `4` | Widget can be detached into its own top-level floating window. | ✅ **Wired** in `DockWidgetTab._start_floating()` ([lace/dock_widget_tab.py:170](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget_tab.py#L170)) & `SidebarManager` ([lace/sidebar_manager.py:231](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_manager.py#L231)) |
| `pinnable` | `8` | Widget can be pinned to or unpinned from a sidebar. | ✅ **Wired** inside `DockWidgetTab` ([lace/dock_widget_tab.py:176](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget_tab.py#L176)) & `SidebarManager.pin_widget()` ([lace/sidebar_manager.py:474](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_manager.py#L474)) |
| `all_features` | `15` | Combined mask enabling all interaction capabilities (`closable \| movable \| floatable \| pinnable`). | ✅ **Wired** inside `DockWidget.__init__()` ([lace/dock_widget.py:50](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget.py#L50)) |

#### Architectural Usage across Codebase
* **`DockWidgetTab.update_close_button_visibility()` ([lace/dock_widget_tab.py:360](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget_tab.py#L360)) & `DockAreaTitleBar.update_title_bar_button_visibility()` ([lace/dock_area_title_bar.py:301](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_area_title_bar.py#L301))**: Checks `widget.features() & DockWidgetFeature.closable`, `floatable`, and `pinnable` (`and`ed with `DockFlags`) to dynamically show or hide the close, undock (`float`), and pin buttons on the title bar and tabs.
* **`SideBarTitleBar` ([lace/sidebar_title_bar.py:111](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_title_bar.py#L111)) & `SideBarTabBar` ([lace/sidebar_tab_bar.py:245](file:///d:/User/Documents/Python/Lace/Lace/sidebar_tab_bar.py#L245))**: Evaluates `features & DockWidgetFeature.closable`, `floatable`, and `pinnable` when rendering slide-out sidebar panel buttons and context menu options.
* **`SidebarManager.pin_widget()`, `unpin_widget()`, & `move_widget_to_area()` ([lace/sidebar_manager.py:474, 548, 619](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_manager.py#L474))**: Explicitly verifies `if not (dock_widget.features() & DockWidgetFeature.pinnable): return` before pinning/unpinning, and checks `if not (dock_widget.features() & DockWidgetFeature.movable): return` before moving pinned tabs between sidebars.
* **Area-Locking Dynamic Restriction (`DockWidget.features()`, [lace/dock_widget.py:334](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget.py#L334))**: When a widget is assigned to a locked area (via `locked_to_area` on the widget or `locked_name` on its parent `DockAreaWidget`), the `floatable` and `pinnable` flags are dynamically stripped from its features, preventing undocking/floating or sidebar pinning.

---

### 3.8 `WidgetState` (`Enum`)
* **File Location:** [lace/enums.py:207-225](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L207-L225)
* **Type & Bitwise Behavior:** `enum.Enum`. Stored on `DockWidget._widget_state` via `dock_widget.set_widget_state(...)` ([lace/dock_widget.py:196](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget.py#L196)).
* **Primary Responsibility:** Tracks the current structural attachment and display mode of a `DockWidget` within the window or sidebar lifecycle.

#### Members Table
| Member | Description | Exact Wiring Location / Code Path |
| :--- | :--- | :--- |
| `docked` | Attached to a standard `DockAreaWidget` within a main layout. | ✅ **Wired** in `DockWidget.__init__()` ([lace/dock_widget.py:62](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget.py#L62)) & `SidebarManager.unpin_widget()` ([lace/sidebar_manager.py:519](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_manager.py#L519)) |
| `floating` | Detached inside a top-level `FloatingDockContainer` window. | ✅ **Wired** inside `FloatingDockContainer` during detach/drop ([lace/floating_dock_container.py:94](file:///d:/User/Documents/Python/Lace/Lace/lace/floating_dock_container.py#L94)) & `DockWidget.refresh_style()` ([lace/dock_widget.py:395](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget.py#L395)) |
| `pinned_shown` | Pinned inside a peripheral sidebar container and currently slid open. | ✅ **Wired** inside `SidebarManager.slide_out()` ([lace/sidebar_manager.py:183](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_manager.py#L183)) & `DockWidget.refresh_style()` ([lace/dock_widget.py:346](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget.py#L346)) |
| `pinned_hidden` | Pinned inside a peripheral sidebar container and currently collapsed/hidden. | ✅ **Wired** inside `SidebarManager.pin_widget()` ([lace/sidebar_manager.py:194, 461](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_manager.py#L194)) & `DockWidget.refresh_style()` ([lace/dock_widget.py:346](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget.py#L346)) |

#### Architectural Usage across Codebase
* **`SidebarManager` ([lace/sidebar_manager.py:461](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_manager.py#L461))**: When a widget is pinned, calls `dock_widget.set_widget_state(WidgetState.pinned_hidden)`. When the user clicks the sidebar tab (`slide_out()` in [lace/sidebar_manager.py:183](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_manager.py#L183)), sets `WidgetState.pinned_shown`. When unpinned back to the main layout (`unpin_widget()` in [lace/sidebar_manager.py:519](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_manager.py#L519)), restores to `WidgetState.docked`.
* **`DockWidget.refresh_style()` & `on_style_changed()` ([lace/dock_widget.py:346, 395](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget.py#L346))**: Inspects `self._widget_state in (WidgetState.pinned_shown, WidgetState.pinned_hidden)` vs `WidgetState.floating` to determine which `DockStyleCategory` token overrides (`SIDEPANEL` vs `CORE`) should be applied to card corner radius, border width, and backgrounds.

---

### 3.9 `InsertMode` (`Enum`)
* **File Location:** [lace/enums.py:227-238](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L227-L238)
* **Type & Bitwise Behavior:** `enum.Enum`. Passed as an optional argument to `DockWidget.set_widget(widget, insert_mode=InsertMode.auto_scroll_area)` ([lace/dock_widget.py:272](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget.py#L272)).
* **Primary Responsibility:** Specifies whether the client widget placed inside a `DockWidget` is wrapped in a `QScrollArea`.

#### Members Table
| Member | Description | Exact Wiring Location / Code Path |
| :--- | :--- | :--- |
| `auto_scroll_area` | Automatically wraps in `QScrollArea` if `widget` is not already a scroll area. | ✅ **Wired** (Default parameter on `DockWidget.set_widget()` in [lace/dock_widget.py:272](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget.py#L272)) |
| `force_scroll_area` | Always wraps the widget inside a `QScrollArea`. | ✅ **Wired** across `DockWidget.set_widget()` `else:` branch ([lace/dock_widget.py:280](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget.py#L280)) |
| `force_no_scroll_area` | Never wraps in a scroll area (`widget` added directly to vertical layout). | ✅ **Wired** inside `DockWidget.set_widget()` ([lace/dock_widget.py:274](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget.py#L274)) |

#### Architectural Usage across Codebase
* **`DockWidget.set_widget(widget, insert_mode)` ([lace/dock_widget.py:272-283](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget.py#L272))**:
  ```python
  scroll_area = isinstance(widget, QScrollArea)
  if scroll_area or InsertMode.force_no_scroll_area == insert_mode:
      self._layout.addWidget(widget)
  else:
      self._setup_scroll_area()
      self._scroll_area.setWidget(widget)
  ```
  If `force_no_scroll_area` is specified, the content widget is added directly to `self._layout` without creating scrollbars. Otherwise (`auto_scroll_area` or `force_scroll_area`), `_setup_scroll_area()` wraps the content inside `self._scroll_area`.

---

### 3.10 `ToggleViewActionMode` (`Enum`)
* **File Location:** [lace/enums.py:240-249](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L240-L249)
* **Type & Bitwise Behavior:** `enum.Enum`. Stored and configured via `DockWidget.set_toggle_view_action_mode(mode)` ([lace/dock_widget.py:361](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget.py#L361)).
* **Primary Responsibility:** Controls the triggering behavior of `dock_widget.toggle_view_action()` when added to menu bars or toolbars.

#### Members Table
| Member | Description | Exact Wiring Location / Code Path |
| :--- | :--- | :--- |
| `toggle` | Action acts as a checkable toggle (`QAction.setCheckable(True)`): flips visibility between Show and Hide (`Show -> Hide -> Show`). | ✅ **Wired** inside `DockWidget.set_toggle_view_action_mode()` ([lace/dock_widget.py:362](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget.py#L362)) |
| `show` | Action acts as a non-checkable push trigger (`QAction.setCheckable(False)`): clicking only makes the widget visible (`open_ = True`). | ✅ **Wired** inside `DockWidget.toggle_view()` ([lace/dock_widget.py:582](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget.py#L582)) |

#### Architectural Usage across Codebase
* **`DockWidget.set_toggle_view_action_mode(mode)` ([lace/dock_widget.py:361](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget.py#L361))**: Sets `self._toggle_view_action.setCheckable(ToggleViewActionMode.toggle == mode)`.
* **`DockWidget.toggle_view(open_)` ([lace/dock_widget.py:580-584](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget.py#L580))**:
  ```python
  sender = self.sender()
  if sender is self._toggle_view_action and not self._toggle_view_action.isCheckable():
      open_ = True
  ```
  When `ToggleViewActionMode.show` is enabled (`not isCheckable()`), clicking the menu item forces `open_ = True` regardless of current visibility state, ensuring the action reveals and focuses the dock widget without toggling it closed.

---

### 3.11 `SideBarFocusBehavior` (`Enum`)
* **File Location:** [lace/enums.py:251-262](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L251-L262)
* **Type & Bitwise Behavior:** `enum.Enum`. Stored on `SideBarContainer._focus_behavior` ([lace/sidebar_container.py:54](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_container.py#L54)) and configurable globally on `DockManager.sidebar_focus_behavior()` ([lace/dock_manager.py:140](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_manager.py#L140)).
* **Primary Responsibility:** Configures keyboard focus stealing and focus restoration behavior when a sidebar overlay panel slides out (`slide_out()`) or slides in (`slide_in()`).

#### Members Table
| Member | Description | Exact Wiring Location / Code Path |
| :--- | :--- | :--- |
| `take_focus_and_restore` | Sidebar panel takes keyboard focus when sliding out, and restores focus to previous card when sliding in. | ✅ **Wired** in `SideBarContainer.slide_out()` / `slide_in()` ([lace/sidebar_container.py:54, 270](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_container.py#L54)) |
| `no_focus_transfer` | Sidebar panel does not steal focus when sliding out or transfer focus when sliding in. | ✅ **Wired** in `SideBarContainer.slide_out()` ([lace/sidebar_container.py:141](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_container.py#L141)) |
| `take_focus_only` | Sidebar panel takes keyboard focus when sliding out, but does not restore focus when sliding in. | ✅ **Wired** in `SideBarContainer.slide_out()` ([lace/sidebar_container.py:141](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_container.py#L141)) |

#### Architectural Usage across Codebase
* **`SideBarContainer.slide_out()` ([lace/sidebar_container.py:141](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_container.py#L141))**:
  ```python
  if self._focus_behavior in (SideBarFocusBehavior.take_focus_and_restore, SideBarFocusBehavior.take_focus_only):
      if not self._slide_widget.hasFocus() and not self._slide_widget.isAncestorOf(QApplication.focusWidget()):
          self._focus_restore_target = QApplication.focusWidget()
          self._slide_widget.setFocus(Qt.OtherFocusReason)
  ```
  If `no_focus_transfer` is selected, `slide_out()` bypasses focus grabbing.
* **`SideBarContainer.slide_in()` & `_on_slide_out_finished()` ([lace/sidebar_container.py:270](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_container.py#L270))**: If `_focus_behavior == SideBarFocusBehavior.take_focus_and_restore`, restores keyboard focus back to `self._focus_restore_target` when the panel finishes collapsing.

---

### 3.12 `TabBadgePosition` (`Enum`)
* **File Location:** [lace/sidebar_tab.py:23-27](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_tab.py#L23-L27)
* **Type & Bitwise Behavior:** `enum.Enum` (using `auto()`).
* **Primary Responsibility:** Intended to define the corner positioning of numerical notification badges on vertical sidebar buttons (`VerticalTabButton` in [lace/sidebar_tab.py:30](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_tab.py#L30)).

#### Members Table
| Member | Description | Exact Wiring Location / Code Path |
| :--- | :--- | :--- |
| `top_left` | Position badge counter at top-left corner of vertical tab button. | ✅ **Wired** inside `VerticalTabButton._draw_badge()` ([lace/sidebar_tab.py:204](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_tab.py#L204)) |
| `top_right` | Position badge counter at top-right corner of vertical tab button. | ✅ **Wired** in `VerticalTabButton.__init__()` ([lace/sidebar_tab.py:38](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_tab.py#L38)) & `_draw_badge()` ([lace/sidebar_tab.py:210](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_tab.py#L210)) |
| `bottom_left` | Position badge counter at bottom-left corner of vertical tab button. | ✅ **Wired** inside `VerticalTabButton._draw_badge()` ([lace/sidebar_tab.py:206](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_tab.py#L206)) |
| `bottom_right` | Position badge counter at bottom-right corner of vertical tab button. | ✅ **Wired** inside `VerticalTabButton._draw_badge()` ([lace/sidebar_tab.py:208](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_tab.py#L208)) |

#### Architectural Usage across Codebase
* **`VerticalTabButton.__init__()` ([lace/sidebar_tab.py:38](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_tab.py#L38))**: Accepts `badge_position: TabBadgePosition = TabBadgePosition.top_right` and exposes it via `self.badge_position` property and `set_badge_position()` setter.
* **`VerticalTabButton.set_badge()` & `_draw_badge()` ([lace/sidebar_tab.py:200](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_tab.py#L200))**: Upgraded to support `Union[int, str]`. Accepts numerical counters (e.g., `3`, `99`) as well as string indicators (`"!"`, `"?"`, `"ERR"`) dynamically drawn into the badge pill. Inspects `self._badge_position` to dynamically compute `badge_rect`:
  ```python
  if self._badge_position == TabBadgePosition.top_left:
      badge_rect = QRect(4, 4, 12, 12)
  elif self._badge_position == TabBadgePosition.bottom_left:
      badge_rect = QRect(4, rect.height() - 16, 12, 12)
  elif self._badge_position == TabBadgePosition.bottom_right:
      badge_rect = QRect(rect.width() - 16, rect.height() - 16, 12, 12)
  else:  # TabBadgePosition.top_right
      badge_rect = QRect(rect.width() - 16, 4, 12, 12)
  ```
* **Manager Forwarding**: `SidebarManager.badge_position` and `DockManager.tab_badge_position` properties actively cascade `TabBadgePosition` changes live across all `SideTabBar` instances.
* **`VerticalTabButton.refresh_style()` ([lace/sidebar_tab.py:238](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_tab.py#L238))**: Reads `badge_position` token (`TabBadgePosition` or string `"top_right"`, `"bottom_left"`, etc.) from `DockStyleCategory.SIDEBAR` to allow theme-driven badge corner overrides.

---

### 3.13 `DockStyleCategory` (`Enum`)
* **File Location:** [lace/dock_theme.py:15-25](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_theme.py#L15-L25)
* **Type & Bitwise Behavior:** `enum.Enum`.
* **Primary Responsibility:** Namespaces component categories (`STYLE_CATEGORIES`) for hierarchical style token lookups (`StyleManager.get_all(...)`) and SVG icon color generation (`dock_icon(...)` in [lace/dock_context_menu.py](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_context_menu.py)).

#### Members Table
| Member | Description | Exact Wiring Location / Code Path |
| :--- | :--- | :--- |
| `CORE` | Global fallback tokens (`font_family`, `accent`, `border_width`). | ✅ **Wired** across `DockThemeBridge` ([lace/dock_theme_bridge.py:111](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_theme_bridge.py#L111)) & `FloatingDockContainer` ([lace/floating_dock_container.py:38](file:///d:/User/Documents/Python/Lace/Lace/lace/floating_dock_container.py#L38)) |
| `PANEL` | Main dock card panels (`content_margin`, `corner_radius`). | ✅ **Wired** inside `DockWidget` ([lace/dock_widget.py:36](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget.py#L36)) & `DockContainerWidget` |
| `TAB` | Standard horizontal tabs (`tab_height`, `tab_radius`, `icon_size`). | ✅ **Wired** inside `DockWidgetTab` ([lace/dock_widget_tab.py:42](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget_tab.py#L42)) & `DockAreaTabBar` |
| `TITLE_BAR` | Dock area title bars (`title_bar_height`, button sizes/colors). | ✅ **Wired** inside `DockAreaTitleBar` ([lace/dock_area_title_bar.py:418](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_area_title_bar.py#L418)) & `ChromeToolButton` |
| `SIDEBAR` | Peripheral vertical sidebar strips (`tab_width`, counter badges). | ✅ **Wired** inside `SideBarTabBar` ([lace/sidebar_tab_bar.py:74](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_tab_bar.py#L74)) & `VerticalTabButton` ([lace/sidebar_tab.py:32](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_tab.py#L32)) |
| `SIDEPANEL` | Slide-out overlay cards (`sidepanel_radius`, `reattach` buttons). | ✅ **Wired** inside `SideBarTitleBar` ([lace/sidebar_title_bar.py:37](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_title_bar.py#L37)) & `SideBarContainer` ([lace/sidebar_container.py:36](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_container.py#L36)) |
| `SPLITTER` | Layout splitters (`splitter_width`, handle hover feedback colors). | ✅ **Wired** inside `DockSplitter` ([lace/dock_splitter.py](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_splitter.py)) & schema tokens ([lace/dock_theme.py:23](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_theme.py#L23)) |
| `OVERLAY` | Translucent drag/drop target indicators and cross split buttons. | ✅ **Wired** inside `DockOverlay` ([lace/dock_overlay.py](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_overlay.py)) & `DockPaint` ([lace/dock_theme.py:24](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_theme.py#L24)) |

#### Architectural Usage across Codebase
* **`DockStyled.STYLE_CATEGORIES`**: Every UI component registers its relevant categories (e.g., `VerticalTabButton.STYLE_CATEGORIES = (DockStyleCategory.SIDEBAR,)` in [lace/sidebar_tab.py:32](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_tab.py#L32)).
* **`StyleManager.get_all(category)`**: Fetches category-specific design tokens from active JSON/QSS schemas (`dock_theme.py`).
* **`dock_icon(name, category)` ([lace/dock_context_menu.py](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_context_menu.py))**: Dynamically tints SVG chrome icons (`close`, `undock`, `pin`, `float`) to match the text or icon foreground colors configured for that specific `DockStyleCategory`.

---

## 4. Verification & Recommendations Checklist

To achieve 100% enum utilization across the Lace architecture, the following code refactoring actions are recommended:

1. [x] **`InsertionOrder` ([lace/enums.py:176](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L176))**: Wired via `DockManager.menu_insertion_order` property ([lace/dock_manager.py:346](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_manager.py#L346)), `add_toggle_view_action_to_menu()`, and `_rebuild_view_menu()`. Inserts `toggle_view_action()` items sorted alphabetically (`by_spelling`) or chronologically (`by_insertion`) when registering or unregistering dock widgets (`add_dock_widget`, `add_sidebar_widget`, `remove_dock_widget`). *(Completed & Verified via `smoke_insertion_order.py`)*
2. [x] **`TabBadgePosition` ([lace/sidebar_tab.py:23](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_tab.py#L23))**: Added `badge_position: TabBadgePosition = TabBadgePosition.top_right` to `VerticalTabButton.__init__()` ([lace/sidebar_tab.py:38](file:///d:/User/Documents/Python/Lace/Lace/lace/sidebar_tab.py#L38)), exposed property/setter `badge_position`/`set_badge_position()`, and updated `VerticalTabButton._draw_badge()` to compute `badge_rect` dynamically across all 4 enum positions (`top_left`, `top_right`, `bottom_left`, `bottom_right`). Also integrated into `refresh_style()` and `DockSidebarStyleSchema` for theme-driven placement. *(Completed & Verified via `smoke_sidebar.py`)*
3. [x] **`DockFlags.opaque_undocking` ([lace/enums.py:88](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L88))**: Checked via `_test_config_flag(DockFlags.opaque_undocking)` inside `FloatingDockContainer._set_state()` ([lace/floating_dock_container.py:270](file:///d:/User/Documents/Python/Lace/Lace/lace/floating_dock_container.py#L270)) whenever tear-off operations or dragging (`DragState.floating_widget`) occur, maintaining 1.0 opacity when enabled vs 0.6 opacity when disabled. *(Completed & Verified via `smoke_flags.py`)*
4. [x] **`DockFlags.custom_tab_icons` ([lace/enums.py:126](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L126))**: Checked inside `DockWidgetTab.update_icon()` ([lace/dock_widget_tab.py:437](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_widget_tab.py#L437)) to gate between user-configured custom icons versus default widget icons using `DockIconProvider.get()`, and hooked into `DockManager.notify_config_flags_changed()` ([lace/dock_manager.py:309](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_manager.py#L309)). *(Completed & Verified via `smoke_tab_icons.py`)*
5. [x] **`DockFlags.chromeless_float` ([lace/enums.py:135](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L135))**: Checked inside `FloatingDockContainer.__init__()` ([lace/floating_dock_container.py:79](file:///d:/User/Documents/Python/Lace/Lace/lace/floating_dock_container.py#L79)) and `update_window_flags_from_config()` hooked into `DockManager.notify_config_flags_changed()` ([lace/dock_manager.py:308](file:///d:/User/Documents/Python/Lace/Lace/lace/dock_manager.py#L308)) to dynamically apply `Qt.FramelessWindowHint` onto floating windows. *(Completed & Verified via `smoke_flags.py`)*
6. [x] **`DockWidgetFeature.movable` ([lace/enums.py:194](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L194))**: Checked across `DockWidgetTab.mouseMoveEvent()`, `DockAreaTitleBar.mouseMoveEvent()`, `FloatingDockContainer._finalize_drag()`, `SidebarManager.move_widget_to_area()`, `SidebarManager.on_tab_drag_started()`, and `SideBarTitleBar._on_drag_started()` to ensure dragging and moving between dock areas/sidebars or dragging out of sidebars is properly gated, while preserving unpin/float/close functionality via menus and buttons. *(Completed & Verified via `smoke_movable.py`)*
7. [x] **`TitleBarButton.pin` ([lace/enums.py:155](file:///d:/User/Documents/Python/Lace/Lace/lace/enums.py#L155))**: Externally queried inside `DockContainerWidget.update_top_level_button_states()` and `_on_visible_dock_area_count_changed()` to manage pin button visibility/state, and wired to `DockAreaTitleBar.on_pin_button_clicked()`. *(Completed & Verified via `smoke_pin_button.py`)*

---

### Architectural Design & Cleanup Notes
* **`WidgetState.hidden` (Removed)**: Removed to enforce a clean single-source-of-truth model where `dock_widget.is_closed()` dictates hidden status, avoiding state divergence between `docked`/`floating` geometries.
* **`DockFlags.content_drop_preview` / `drag_preview_shows_content_pixmap` (Removed)**: Removed because drawing static scaled screenshots inside drop zones (`DockOverlay`) distorts aspect ratios and creates visual clutter alongside the live moving `FloatingDockContainer` window (`opaque_undocking`). `DockOverlay` now cleanly and exclusively renders the high-performance translucent drop target highlight.
