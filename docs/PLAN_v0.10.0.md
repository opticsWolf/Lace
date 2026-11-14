# Lace v0.10.0 — Release Plan

**Status:** draft
**Baseline:** v0.9.7 (`cb07ab6`)
**Target:** v0.10.0
**Test baseline:** `1899 passed, 2 skipped, 1 xfailed` (`pytest tests -q`, offscreen)
**Scope:** one open bug-report audit plus five new items (window-edge resize, hover delay,
dock-menu icons, cramped title bars, rare frameless overlap)

**Implementation status (branch `dev_v0.10.0`):** B, C and D implemented; E and F pending.

---

## 0. Summary

| # | Item | Type | Severity | Confidence in diagnosis | Est. |
|---|------|------|----------|--------------------------|------|
| A | Open bug reports | audit | — | verified against code, tests and GitHub | 0.5 d |
| B | Active sidebar blocks window-edge resizing | bug | high | reproduced | 1–2 d |
| C | Sidebar hover delay parameter | feature | medium | current values verified | 0.5 d |
| D | Title-bar tab menu shows the generic tab icon | bug | medium | reproduced | 0.25 d |
| E | Cramped tabs: no full tooltip, no description, no scroll controls | bug + feature | high | code verified; overflow bug reproduced | 2–3 d |
| F | Dock area occasionally shifts over the frameless title bar | bug | medium (rare) | **not reproduced yet** — needs instrumentation | 2–5 d |

Suggested order: **D → C → B → E → F → A/release**. D and C are small; B and E touch
the same sidebar/title-bar area; F is diagnostic and should not block the others.

---

## 1. (A) Open bug reports — is anything still open?

### 1.1 Inventory of the local report files

The reports live next to the checkout (`..\*.md`), not in `docs/`. Status as of v0.9.7:

| Report | Status | Evidence |
|---|---|---|
| `calendar-popup-rounding.md` | **OPEN** — polish TODO, not a crash | `lace/style/_popup.py` still has no `is_calendar_popup()` / calendar-panel path; calendars still fall through to square Fusion popups |
| `native-frame-native-child-bug.md` | **CLOSED in 0.9.2** | `apply_native_frame()` reads `internalWinId()` (`lace/native_frame.py`); `tests/test_native_frame.py` |
| `native-sibling-freeze.md` | **CLOSED in 0.9.5** | `DockManager.__init__` sets `AA_DontCreateNativeWidgetSiblings`; `tests/test_native_siblings.py` |
| `sidebar-pinning-fixes.md` (incl. §10) | **CLOSED in 0.9.3 / 0.9.4** | pin/unpin/restore, allow-list API, signal, deleted-button guard; `tests/test_sidebar_pinning.py` |
| `tab-icon-spacer-heap-corruption.md` | **CLOSED in 0.9.7** | icon gap is now a `QWidget`, not a `QSpacerItem`; `tests/test_tab_icon_lifetime.py` |
| `frameless-float-jump-bug.md` | **CLOSED before 0.9** | stale-drag cancellation, global-roundtrip mapping, release cleanup; `tests/test_frameless_window_state.py` |
| `dropin_splitter_logic.md` | **not a bug report** | design/reference document |

### 1.2 GitHub

There are **no open GitHub issues** in `opticsWolf/Lace`; the only issue-tracker entry is the
closed PR #1 (`Update NOTICE`). The bug reports above are the working set.

`docs/CODE_REVIEW_0.6.5.md`, `docs/CODE_REVIEW.md` and `docs/IMPROVEMENT_PLAN_v0.8.md` are
historical review/plan documents. They are not live issue lists; several items in them have
since been fixed or superseded.

### 1.3 Verdict

- **One open report remains:** `calendar-popup-rounding.md` (calendar popup corners/shadow).
  It is cosmetic and can be carried into 0.10.x unless we want it in this release.
- No open crash, freeze or data-loss report.
- Items **B–F in this plan are new**, opened while preparing v0.10.0. Treat them as the 0.10.0
  bug/feature set.
- v0.9.7's suite is green; any new failure during this work is ours.

---

## 2. (B) Active sidebar blocks window-edge resizing

### 2.1 Symptom

When a sidebar is present, the outer window edge it runs along can no longer be dragged to
resize the window. The sidebar's tab strip sits directly on that edge; its children (tab
buttons, the scroll area) receive the press, so the window manager never gets a resize gesture.
This is most visible with the frameless / custom title bar, where the client area reaches the
window edge.

This is **not** about dock splitters. The earlier splitter-clamp proposal was based on a
misreading and has been reverted.

### 2.2 Root cause

- `SideTabBar` is a fixed-width child of the root container and runs along the window edge.
- Its child buttons and scroll area cover almost the full strip, including the outer 5-6 px
  where a frameless window's resize border lives.
- A press in that strip is consumed by the sidebar widget tree. `QFramelessWindow`'s
  `WM_NCHITTEST` path normally answers the border before Qt client dispatch, but that is not
  guaranteed when a child owns the pointer (native-child cases, custom chrome, platform
  differences). The sidebar must not rely on the OS hit test reaching the top-level window.
- The active overlay does not have to be open for this: the tab strip alone sits on the edge.

### 2.3 Fix - a window-edge grip on `SideTabBar`

Add a transparent `_WindowResizeGrip` child to every `SideTabBar`, covering its window-facing
edge:

- left bar: `(0, 0, 6, height)`;
- right bar: `(width - 6, 0, 6, height)`;
- bottom bar: `(0, height - 6, width, 6)`;
- top bar: `(0, 0, width, 6)` (only useful if the root actually reaches the window top).

The grip is raised above the tab strip and its children, so it receives the press first. On a
left press it:

1. resolves the cursor against the client rect (`LeftEdge`, `RightEdge`, `TopEdge`, `BottomEdge`,
   including corners);
2. calls `self.window().windowHandle().startSystemResize(edges)`, which starts the native resize
   loop;
3. accepts the press when the window manager accepts the gesture.

It also sets the matching resize cursor (`SizeHorCursor`, `SizeVerCursor`, `SizeFDiagCursor`,
`SizeBDiagCursor`) while hovering. The grip does not paint anything and does not change the
bar's layout; it is a 3 px transparent hit area.

Constraints:

- no resize while the window is maximized or full screen;
- `startSystemResize` returning `False` falls back to ignoring the event, so platforms without
  support keep their previous behaviour;
- the grip must stay above tabs and the scroll area, including while the overlay is open.

### 2.4 Tests

`tests/test_sidebar_window_resize.py`:

- left and right bars carry a visible grip covering the window-facing edge;
- the grip is the top child at that edge (`bar.childAt()`), even with the overlay open;
- a press on the left/right grip calls `startSystemResize()` with the matching edge;
- the cursor shape follows the edge (horizontal, vertical, diagonal);
- no resize call for maximized/full-screen windows.

Acceptance: dragging the frameless window's left/right edge over the sidebar resizes the window,
with the sidebar open or closed; normal tab clicks away from the 3 px strip are unchanged.

---

## 3. (C) Sidebar hover delay

### 3.1 Current state — no public parameter

`SidebarHoverController` (`lace/sidebar_manager.py`) has:

| Behaviour | Current value | Where |
|---|---:|---|
| Auto-show on tab hover | **0 ms — immediate** | `on_tab_hover_enter()` calls `process_pending_switch()` directly |
| Hide after leave | **400 ms** | module constant `_HIDE_DELAY_MS = 400`; `_hide_timer` |
| Switch tab while overlay open | **150 ms** | `_switch_timer` interval, matched to the 50 ms slide animation |
| Click / toggle | immediate | `on_tab_clicked()`, `toggle_sidebar()` |

There is no setter, no property and no saved setting. `save_state()` serialises only
`auto_show_on_hover`, `animations_enabled` and `keep_open`.

**Decision: 150 ms.** The pre-change behaviour was 0 ms. Hide stays 400 ms and tab switching
stays 150 ms.

### 3.2 Proposed API

Keep the three timers separate; callers usually mean *show delay* when they say “hover delay”.

```python
# SidebarManager
@property
def hover_delay_ms(self) -> int: ...
@hover_delay_ms.setter
def hover_delay_ms(self, ms: int) -> None: ...

@property
def hide_delay_ms(self) -> int: ...
@hide_delay_ms.setter
def hide_delay_ms(self, ms: int) -> None: ...

@property
def switch_delay_ms(self) -> int: ...
@switch_delay_ms.setter
def switch_delay_ms(self, ms: int) -> None: ...
```

Facade on `DockManager`:

```python
dock_manager.sidebar_hover_delay = 150      # ms; None/0 = immediate
```

Rules:

- values are clamped to `0 .. 5000`; a negative value becomes 0;
- `hover_delay_ms` is only the delay before **auto-show on hover**; clicks and programmatic
  `show_widget()` stay immediate;
- when the overlay is already visible and the pointer moves to another tab, keep using
  `switch_delay_ms` (150 ms default) so switching still matches the animation;
- a new hover starts the show timer; leaving before it fires cancels it; clicking before it
  fires shows immediately;
- changing values while a timer is pending updates that timer's interval;
- persist all three in `save_state()["settings"]`; `restore_state()` keeps the backward-compatible
  defaults when the keys are absent.

Implementation sketch:

```python
# SidebarHoverController.__init__
self._show_timer = QTimer(self)
self._show_timer.setSingleShot(True)
self._show_timer.timeout.connect(self.process_pending_switch)

def on_tab_hover_enter(self, button):
    ...
    self._pending_button = button
    if self._manager._overlay.isVisible() and self._manager._animations_enabled:
        self._switch_timer.start()             # existing path
    elif self._manager.hover_delay_ms > 0:
        self._show_timer.start(self._manager.hover_delay_ms)
    else:
        self.process_pending_switch()

def on_tab_hover_leave(self, button):
    self._show_timer.stop()
    ...
```

### 3.3 Tests

- hover delay 0 -> overlay visible after the hover event (existing behaviour);
- hover delay 150 -> not visible before 150 ms, visible after;
- leave before the show timer fires -> never visible; hide timer behaves as before;
- click while the show timer is pending -> immediate show and no queued double show;
- `save_state()`/`restore_state()` round-trips all three settings;
- invalid values clamp, and `DockManager.sidebar_hover_delay` forwards to the manager.

---

## 4. (D) Title-bar right-click menu shows a generic icon

### 4.1 Symptom

Right-clicking the dock-area title bar (or its tabs menu) lists the tabs, but every entry uses the
same generic “tab list” glyph instead of the dock panel's own icon.

### 4.2 Root cause — verified

`build_dock_context_menu()` in `lace/dock_menu.py`:

```python
for i in range(tab_bar.count()):
    ...
    tab = tab_bar.tab(i)
    act = menu.addAction(_icon("tab_list"), tab.text())   # <-- ignores tab.icon()
```

All tab actions therefore share the result of `dock_icon("tab_list")`. A probe with three docks
carrying red/green/blue icons produced menu `QIcon.cacheKey()` values that were all identical,
while `tab.icon()` and `DockWidget.icon()` had three different keys. Both the title bar's
context menu and the tabs menu use the same builder, so one fix covers both.

### 4.3 Fix

In `build_dock_context_menu()`, use the tab's rendered icon with fallbacks:

```python
def _tab_icon(tab):
    icon = tab.icon() if hasattr(tab, "icon") else QIcon()
    if icon.isNull():
        icon = _icon("tab_list")
    if icon.isNull():
        dw = getattr(tab, "_dock_widget", None)
        if dw is not None:
            icon = dw.windowIcon()
        if icon.isNull():
            app = QApplication.instance()
            if app is not None:
                icon = app.windowIcon()
    return icon
```

```python
act = menu.addAction(_tab_icon(tab), tab.text())
```

Details:

- `tab.icon()` is already themed and tinted for the tab's active/inactive state; prefer it.
- The generic `tab_list` action glyph is the first fallback; the dock window icon and then the
  application icon are the final fallbacks.
- Set the menu's icon size from the TAB token so the tab icons are not scaled:
  `menu.setIconSize(QSize(tab_icon_size, tab_icon_size))` only when the caller has not set one.
- Keep the existing tooltip line (`act.setToolTip(tab.toolTip())`); after item E it will carry the
  full title + description.

### 4.4 Tests

`tests/test_dock_menu.py` (new or extend the existing menu tests):

- three tabs with distinct `QIcon`s -> each `switch_tab` action's icon key equals its tab's icon;
- a tab with a null icon -> action falls back to `windowIcon()`, then to `tab_list`;
- the tabs menu (`DockAreaTitleBar._tabs_menu`) and the title-bar context menu both show the
  per-tab icons;
- menu icon size follows the theme token.

---

## 5. (E) Cramped title bar: full hover text, descriptions and tab scrolling

### 5.1 Current behavior

- `DockWidgetTab` uses an `ElidingLabel`; a long title elides to `…`.
- `ElidingLabel.setText()` sets its own tooltip to the full text, but only on the **label**.
  The tab frame itself has no tooltip, so hovering the tab padding, icon gap or close-button side
  shows nothing.
- `DockWidget.set_tab_tool_tip()` can set an explicit tooltip, but nothing derives one.
- **No `description` property exists** on `DockWidget` (grep over `lace/*.py` finds none).
- `DockAreaTabBar` is a `QScrollArea` with `horizontalScrollBarPolicy = AlwaysOff`; wheel events
  scroll by 20 px, but there are no arrow buttons.
- **Additional bug found while testing:** when the current tab is changed to a tab beyond the
  viewport, `ensureWidgetVisible()` is called before the tab layout has valid geometry, so the
  current tab can stay off-screen. With 15 tabs in a 400 px window, current index 14 had
  scroll value 0 and the active tab was invisible. A manual deferred `ensureWidgetVisible()`
  fixed it.

### 5.2 `description` property

Add to `DockWidget`:

```python
description_changed = Signal(str)

def __init__(self, title: str, parent: QWidget = None, *, description: str = ""):
    self._description = ""
    self._tab_tool_tip_override: Optional[str] = None
    ...

def description(self) -> str: ...
def set_description(self, text: str) -> None: ...
```

Behavior:

- `set_description` stores the text, emits `description_changed` only when it changes, refreshes
  the tab tooltip, the toggle-view action's tooltip and the title-bar menu cache.
- The description is runtime metadata, not layout state: do **not** add it to `save_state()`.
  Applications recreate their docks and set it again. (If persistence is ever wanted, it belongs
  in the application's own model, not the layout JSON.)
- `DockWidget(title="Log", description="Build output and diagnostics")` is the concise form.
- `DockWidgetTab` and `VerticalTabButton` read it; patching only `DockWidgetTab` would leave
  sidebar tabs showing the old title-only tooltip.

### 5.3 Tooltip composition

One source of truth, on `DockWidget`:

```python
def _composed_tab_tool_tip(self) -> str:
    if self._tab_tool_tip_override is not None:
        return self._tab_tool_tip_override
    title = self.windowTitle()
    desc = self._description.strip()
    return f"{title}\n{desc}" if desc else title
```

Precedence, lowest to highest:

1. composed `title + "\n" + description`;
2. `set_tab_tool_tip(text)` — explicit override, kept for backward compatibility; setting an
   empty string clears the override and returns to the composed text;
3. a caller that deliberately calls `tab.setToolTip()` still wins for that tab.

`DockWidgetTab` gets one refresh method:

```python
def refresh_tooltip(self) -> None:
    text = self._dock_widget._composed_tab_tool_tip()
    self.setToolTip(text)              # whole tab, including padding
    self._title_label.setToolTip(text) # label under the cursor
    if self._icon_label is not None:
        self._icon_label.setToolTip(text)
```

Call it from:

- `DockWidgetTab.__init__` (replacing the label-only tooltip);
- `DockWidgetTab.set_text()` and `DockWidget.event(WindowTitleChange)`;
- `DockWidget.set_description()`;
- `DockWidget.set_tab_tool_tip()`;
- `DockWidget.event(WindowTitleChange)` after `_tab_widget.set_text(title)`.

`ElidingLabel.setText()` sets its own tooltip; refresh must run **after** it so the composed text
wins. The existing `ToolTipChange` handler in `DockWidgetTab.event()` should be kept as a safety
net for external `setToolTip()` calls.

Sidebar tabs: `VerticalTabButton` currently does `setToolTip(text)` in `__init__`. Have
`SideTabBar.add_tab()` use the same composed text and connect `dock_widget.description_changed`
(and `title_changed`) to update the button's tooltip. Disconnect on `remove_tab`/`_forget`.

Display notes:

- Qt tooltips are plain text by default; the newline gives a two-line title/description card.
- Long descriptions wrap according to `QToolTip`; no rich-text escaping is needed because the
  text is plain.
- The tooltip should show the full title even when the label is **not** elided; Qt already
  suppresses duplicate tooltips only when the text matches the widget text, which is not the
  case for the multiline composition.

### 5.4 Title-bar scroll arrows

Add two `ChromeToolButton`s to `DockAreaTitleBar`, between the tab strip and the tabs-menu
button:

```
[ tabs .... ][ ‹ ][ › ][ menu ][ pin ][ max ][ float ][ close ]
```

They are **only visible when the tab strip overflows**. No permanent width cost for normal
layouts; no new menu entries.

Icons: add `chevron_left.svg` / `chevron_right.svg` in the existing Tabler style (24 px viewBox,
1.5 px stroke), and register them in `_ICON_SPECS` with `QStyle.SP_ArrowLeft` / `SP_ArrowRight`
fallbacks, so themes without the assets still get a tinted arrow. Reuse
`style_title_bar_buttons()` so their size/hover chrome matches the other buttons.

`DockAreaTabBar` API:

```python
def can_scroll_left(self) -> bool: ...
def can_scroll_right(self) -> bool: ...
def scroll_tabs(self, direction: int) -> None:   # -1 left, +1 right
def reveal_tab(self, index: int) -> None:        # deferred ensureWidgetVisible
```

Implementation sketch:

```python
def scroll_tabs(self, direction: int) -> None:
    bar = self.horizontalScrollBar()
    if direction < 0:
        self._scroll_to_previous_hidden_tab()
    else:
        self._scroll_to_next_hidden_tab()

def _scroll_to_next_hidden_tab(self) -> None:
    bar = self.horizontalScrollBar()
    left = bar.value()
    right = left + self.viewport().width()
    for i in range(self.count()):
        tab = self.tab(i)
        if tab is None or not tab.isVisible():
            continue
        g = tab.geometry()
        if g.left() >= right:
            self.ensureWidgetVisible(tab, 0, 0)
            return
    bar.setValue(bar.maximum())

def _scroll_to_previous_hidden_tab(self) -> None:
    bar = self.horizontalScrollBar()
    left = bar.value()
    for i in reversed(range(self.count())):
        tab = self.tab(i)
        if tab is None or not tab.isVisible():
            continue
        g = tab.geometry()
        if g.right() <= left:
            self.ensureWidgetVisible(tab, 0, 0)
            return
    bar.setValue(bar.minimum())
```

`DockAreaTitleBar`:

- create the buttons after `_create_tab_bar()` and before `_create_buttons()` so the layout order
  above is explicit;
- connect `horizontalScrollBar().rangeChanged` / `valueChanged` to `_sync_tab_scroll_buttons()`;
- `_sync_tab_scroll_buttons()` shows both buttons only when
  `maximum > minimum`, enables/disables them at the ends, and calls
  `QTimer.singleShot(0, ...)` once after construction/layout;
- on `tab_inserted`, `tab_closed`, `tab_moved`, `current_changed` and title-bar resize, resync;
- set `setAutoRepeat(True)` with a ~100 ms interval so holding an arrow scrolls continuously;
- tooltips: “Scroll tabs left” / “Scroll tabs right”.

Flag: add `DockFlags.dock_area_has_tab_scroll_buttons` (default **on**, but the buttons still
appear only on overflow). Update `default_config`, `docs/enum_mapping.md`,
`docs/QUICK_REFERENCE.md`, `docs/ARCHITECTURE.md` (19 -> 20 flags) and the enum tests. If we want
zero API surface, omit the flag and always auto-show on overflow; the flag is the better
long-term choice because it gives hosts an escape hatch.

`TitleBarButton` (enum) gains `tab_scroll_left` / `tab_scroll_right` if callers need
`titleBar.button(TitleBarButton.tab_scroll_left)`.

#### Fix the auto-reveal bug while here

`_update_tabs()` currently calls `ensureWidgetVisible()` synchronously. Change it to a deferred
call:

```python
def _reveal_current(self) -> None:
    tab = self.current_tab()
    if tab is not None:
        self.ensureWidgetVisible(tab, 0, 0)

# in set_current_index / _update_tabs / insert_tab / remove_tab
QTimer.singleShot(0, self._reveal_current)
```

Also call it after the scroll area's layout has been activated
(`self.widget().adjustSize()` or `self._tabs_layout.activate()`) so the geometry is valid.

This is a real user-facing fix: without it, selecting the 15th tab in a cramped area leaves the
active tab off-screen.

### 5.5 Mouse-wheel scrolling

`DockAreaTabBar.wheelEvent()` already scrolls, but it advances a fixed 20 px regardless of the
wheel delta. Improve it:

```python
def wheelEvent(self, event):
    bar = self.horizontalScrollBar()
    pixel = event.pixelDelta()
    angle = event.angleDelta()
    if not pixel.isNull():
        delta = pixel.x() or pixel.y()
    else:
        steps = angle.y() / 120.0
        delta = -steps * self._tab_scroll_step()
    bar.setValue(bar.value() - int(delta))
    event.accept()
```

- `_tab_scroll_step()` returns the width of a typical tab (first visible tab's width), clamped to
  a sensible range, so one notch moves roughly one tab.
- Handle touchpads via `pixelDelta()`.
- `Shift+wheel` is horizontal by convention; also accept `angleDelta().x()` if non-zero.
- Add a `wheelEvent` on `DockAreaTitleBar` that forwards to the tab bar when the cursor is over
  the title bar but not over a button; this lets the wheel work over the empty title-bar area.
- Keep the tab strip's wheel behavior from stealing a global scroll when the tab bar does not
  overflow: if `maximum == minimum`, call `event.ignore()` so a parent scroll area can use it.

### 5.6 Tests

`tests/test_dock_title_hover.py`:

- tab with a long title -> tooltip equals the full title; tab and label both carry it;
- `description` set -> tooltip equals `"Title\nDescription"`; updating description updates both
  the tab and the sidebar tab;
- title change -> description survives in the tooltip;
- `set_tab_tool_tip("explicit")` wins; clearing it restores the composed text;
- empty description -> title-only tooltip;
- sidebar `VerticalTabButton` tooltip follows description changes;
- tooltip is not truncated by elision.

`tests/test_tab_overflow.py`:

- 15 tabs in a 400 px window -> scroll arrows visible, left disabled, right enabled;
- clicking right advances the scroll and reveals a previously hidden tab;
- clicking left at the start is a no-op; right at the end is a no-op;
- selecting the last tab programmatically scrolls it into view after the event loop;
- wheel up/down advances by roughly one tab; no overflow -> wheel ignored;
- flag cleared -> arrows stay hidden even on overflow;
- tab close/move updates the arrow visibility.

---

## 6. (F) Rare dock-area/title-bar overlap with the custom frameless title bar

### 6.1 Symptom

Occasionally the whole dock layout appears shifted upwards and overlaps the window's custom
title bar. Resizing or restoring the window fixes it. The reporter is unsure whether it only
happens while maximized.

### 6.2 What has been ruled out (v0.9.7, real Windows platform)

Probes on Windows 11, PySide6 6.11.2, custom `LaceStandardTitleBar`:

| Scenario | Result |
|---|---|
| normal -> `showMaximized()` -> `showNormal()` | title bar 32 px, root starts at y=32, no overlap |
| native `ShowWindow(SW_MAXIMIZE)` / posted `SC_MAXIMIZE` | same |
| native restore | same |
| window created maximized, then `DockManager` created | same |
| menu bar created after show, while maximized | menu widget grows to 64 px; root follows to y=64 |
| hide/show the menu bar while maximized | root follows |
| live `main_title_bar` swap while maximized (including a taller bar) | root follows |
| theme switch while maximized | root follows |
| `updateFrameless()`, `setWindowFlags()` + `show()` | root follows |
| fullscreen -> maximized -> normal | root follows |
| custom float: normal/maximize/restore | title bar and dock container stay separate |

So the obvious QMainWindow relayout paths are correct today. Treat F as **not yet reproduced**,
not as “fixed by inspection”.

### 6.3 Hypotheses to test

1. **Stale QMainWindow layout after a menu-widget size change.** The custom title bar (or the
   stacked title-bar + menu-bar container) changes its size hint after the window is already
   laid out. QMainWindow should relayout on `LayoutRequest`, but a race during maximize / native
   state change can leave the central widget at the old y. A resize/restore forces the layout.
2. **qframelesswindow's manual title-bar resize fights QMainWindow.** The Windows backend's
   `resizeEvent` does `self.titleBar.resize(self.width(), self.titleBar.height())` directly.
   Lace puts the title bar in the menu-widget slot, where QMainWindow owns its geometry. The
   direct resize can win momentarily during a state change.
3. **Native handle recreation / screen change.** `WinIdChange` (WebEngine/OpenGL) or a DPI /
   monitor change can trigger `updateFrameless()` and a re-layout at the wrong time. The existing
   `_schedule_frameless_heal()` path is a natural place to also re-activate the layout.
4. **Floating container with custom chrome.** `FramelessFloatingDockContainer` uses a
   `QBoxLayout` for title bar + dock container; a window-state change during a drag/drop or a
   `setWindowFlags()` cycle could leave the box layout stale until the next resize.

### 6.4 Instrumentation first

Add `dev_smoke/probe_titlebar_overlap.py` (real display, Windows):

- log a row for every `Resize`, `WindowStateChange`, `LayoutRequest`, `Show`, `ScreenChange` and
  `DevicePixelRatioChange`;
- record `win.geometry()`, `titleBar.geometry()`, `menuWidget.geometry()`,
  `centralWidget().geometry()`, `menuWidget().sizeHint()`, `layout().totalSizeHint()` and
  `win.isMaximized()`;
- assert the invariant directly:
  `centralWidget().geometry().top() >= menuWidget().geometry().bottom() + 1` and
  `titleBar.geometry()` does not intersect the root container;
- loop 100+ maximize/restore cycles, mixing Qt (`showMaximized`) and native
  (`ShowWindow(SW_MAXIMIZE)` / `SC_MAXIMIZE`), menu show/hide, theme switches, live title-bar
  swaps, `updateFrameless()`, and a WebEngine/OpenGL handle recreation if available;
- on violation, dump the last 20 event rows and the widget tree; make the script exit non-zero.

Also add a `trace("chrome.layout", ...)` event (or `LACE_TRACE=chrome`) so a user report can
capture the sequence without a special build.

### 6.5 Defensive fix (land even if the repro stays elusive)

In `FramelessLaceMainWindow`:

```python
def event(self, e):
    if e.type() == QEvent.WinIdChange:
        self._schedule_frameless_heal()
    if e.type() in (QEvent.WindowStateChange, QEvent.LayoutRequest,
                    QEvent.Show, QEvent.ScreenChangeInternal,
                    QEvent.DevicePixelRatioChange):
        self._schedule_chrome_layout()
    return super().event(e)

def _schedule_chrome_layout(self):
    if getattr(self, "_chrome_layout_queued", False):
        return
    self._chrome_layout_queued = True
    QTimer.singleShot(0, self._sync_chrome_layout)

def _sync_chrome_layout(self):
    self._chrome_layout_queued = False
    layout = self.layout()
    if layout is not None:
        layout.invalidate()
        layout.activate()
    central = self.centralWidget()
    if central is not None:
        central.updateGeometry()
    self.titleBar.raise_()
```

Additionally:

- Override `resizeEvent` in `FramelessLaceMainWindow` to call `QMainWindow.resizeEvent(self, e)`
  directly (skipping qframelesswindow's direct `titleBar.resize`) and then
  `_schedule_chrome_layout()`. Test this carefully; if any base behavior is lost, fall back to
  calling `super().resizeEvent(e)` and only adding the scheduled relayout.
- `setTitleBar()` and `setMenuWidget()` should call `_schedule_chrome_layout()` after rebuilding
  the stacked container.
- If the probe finds the native-handle path, call `_schedule_chrome_layout()` from
  `_heal_frameless_chrome()` as well.
- Do not call `setGeometry()` or otherwise resize the window from these hooks; that would fight
  the user's window manager.

### 6.6 Acceptance

- The invariant holds in the offscreen test after maximize/restore, menu show/hide, theme switch
  and title-bar swap.
- The real-platform probe passes 100+ mixed cycles on Windows at 100 %, 125 % and 150 % DPI and
  across two monitors.
- If the probe still cannot reproduce F, document the exact scenarios tried, keep the
  instrumentation, and treat the defensive relayout as insurance. A written non-repro is an
  acceptable outcome for a rare timing bug; a silent “works on my machine” is not.

---

## 7. Cross-cutting test plan

| Area | New/updated tests |
|---|---|
| Sidebar splitter | `tests/test_sidebar_splitter.py` |
| Hover delay | `tests/test_sidebar_hover_delay.py` |
| Menu icons | `tests/test_dock_menu.py` |
| Description/tooltip | `tests/test_dock_title_hover.py` |
| Tab overflow/arrows/wheel | `tests/test_tab_overflow.py` |
| Frameless overlap | `tests/test_frameless_custom_bar.py` additions + `dev_smoke/probe_titlebar_overlap.py` |
| Enum/docs | `tests/test_enums.py`, `tests/test_public_api.py`, `tests/test_version_is_consistent.py` |

Run at least:

```
pytest tests -q
pytest tests/test_frameless_window_state.py tests/test_frameless_custom_bar.py -q
python dev_smoke/run_all.py            # offscreen subset
python dev_smoke/probe_titlebar_overlap.py   # real Windows display
```

The v0.9.7 baseline is `1899 passed, 2 skipped, 1 xfailed`; no new skips without a written
reason.

---

## 8. Documentation and release checklist

- **Version:** `0.10.0` in `pyproject.toml`, `lace/__init__.py`, `README.md`,
  `docs/ARCHITECTURE.md`, `docs/QUICK_REFERENCE.md` (guarded by
  `test_version_is_consistent`).
- **CHANGELOG.md:** new `## [0.10.0]` section with:
  - Fixed: sidebar tab strip blocking window-edge resizing; current tab not scrolled into view;
  - Fixed: per-tab icons in the dock menus;
  - Added: `DockWidget.description` / `description_changed`;
  - Added: configurable sidebar hover/hide/switch delays;
  - Added: title-bar tab scroll arrows and improved wheel scrolling;
  - Fixed: frameless title-bar/dock overlap (or “hardened against”, if F remains unreproduced);
  - Changed: default `hover_delay_ms` = **150**.
- **README:** sidebar delay parameter, description property, scroll-arrow behavior; update the
  flag count if `dock_area_has_tab_scroll_buttons` is added.
- **docs/ARCHITECTURE.md:** sidebars section (hover timers), title-bar section (scroll arrows),
  dock widget API (description), `DockFlags`.
- **docs/QUICK_REFERENCE.md:** new properties/setters, tooltip composition, arrow flag.
- **docs/enum_mapping.md:** new flag and its reader.
- **docs/theming_and_geometry.md:** if the arrows need a theme token (they can reuse
  `TITLE_BAR.button_*`; only document a new token if one is added).
- **Site/screenshots:** only if the title-bar demo visibly changes; the arrows are conditionally
  visible, so no wholesale screenshot refresh is required.

---

## 9. Risk register

| Risk | Where | Mitigation |
|---|---|---|
| The edge grip steals clicks from a tab near the outer edge | B | Limit the grip to 3 px and keep normal tab hit-testing inside it |
| `startSystemResize` is unavailable or returns `False` | B | Ignore the event; the previous behaviour is unchanged |
| The grip falls under the scroll area after a relayout | B | Reposition and `raise_()` on every `SideTabBar.resizeEvent` |
| Hover delay makes the sidebar feel sluggish | C | Default 150 ms, configurable to 0; only auto-show is delayed, clicks stay instant |
| Tab arrows crowd an already cramped bar | E | Show only on overflow; hide both when not needed; reuse existing button chrome |
| Per-tab `QIcon`s bypass the theme on inactive tabs | D | Use `tab.icon()` (already state-tinted), not the raw custom icon |
| Description tooltips expose stale text after a rename | E | One composer on `DockWidget`; refresh after every title/description/tooltip change |
| Defensive relayout hides a real QMainWindow bug | F | Keep the probe and trace; assert invariants; do not "fix" by forcing geometry |
| New flag breaks enum documentation tests | E | Update `default_config`, `test_enums.py`, `enum_mapping.md`, `ARCHITECTURE.md` in the same commit |
---

## 10. Decisions

Resolved for B/C/D:

1. **Hover delay (C): 150 ms.** Hide stays 400 ms; tab switch stays 150 ms.
2. **B:** the window-edge resize is the target. The splitter-clamp proposal was reverted; the
   implemented fix is the `SideTabBar` window-edge grip.
3. **D:** keep the generic `tab_list` glyph; use the dock/application window icon only as the
   final fallback.
4. **C facade:** `DockManager.sidebar_hover_delay`, `sidebar_hide_delay` and
   `sidebar_switch_delay` all proxy the corresponding `SidebarManager` properties.

Still open for E/F:

- Add `DockFlags.dock_area_has_tab_scroll_buttons` (default on, visible on overflow) or always
  show the tab arrows on overflow with no flag?
- Carry the calendar-popup rounding item into 0.10.0, or defer it to 0.10.x?
