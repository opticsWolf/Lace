# Lace — Code Review & Improvement Plan

**Reviewed:** `lace/` package at commit `cb41357` (v0.5.0)
**Environment:** PySide6 6.11.1, pydantic 2.13.4, Python venv `developenv`, `QT_QPA_PLATFORM=offscreen`
**Method:** full read of all 40 modules in `lace/`, plus five runtime probe scripts that exercise
save/restore round-trips, theme-token resolution, and `refresh_style()` call counts. Every finding
marked **[verified]** was reproduced by running code, not inferred from reading it.

Line numbers refer to the reviewed commit.

---

## 0. Summary

| # | Severity | Area | Finding | Effort |
|---|----------|------|---------|--------|
| 1.1 | **Critical** | Persistence | `restore_state()` returns `True` but orphans every dock widget **[verified]** | 1 line |
| 1.2 | **Critical** | Persistence | `ensure_active_dock_area()` raises `AttributeError` **[verified]** | 5 lines |
| 1.3 | High | Persistence | Failed restores are ignored and leave a half-mutated container | ~40 lines |
| 1.4 | High | Persistence | Container maximize state survives restore as a dangling pointer **[verified]** | 4 lines |
| 2.1 | High | State model | `locked_name` / `locked_to_area` never serialized **[verified]** | ~15 lines |
| 2.2 | High | State model | Pinned widgets come back `closed=True` **[verified]** | ~20 lines |
| 2.3 | Medium | State model | `widget_states` block is written but never read | ~30 lines |
| 2.4 | Medium | State model | Floating geometry stored twice, in conflicting formats | ~20 lines |
| 2.5 | Medium | State model | No schema version; `SYSTEM_TYPE` is the C++ ADS string | ~10 lines |
| 3.1 | High | Theming | "Ghost tokens": schema is `fields ∪ whatever the default theme seeds` **[verified]** | ~30 lines |
| 3.2 | High | Theming | `title_border_bottom` is fully dead across three call sites **[verified]** | ~6 lines |
| 3.3 | Medium | Theming | Sidebar panel border/focus colours silently fall back to CORE **[verified]** | covered by 3.1 |
| 3.4 | Medium | Theming | Any 3–4 element numeric token is coerced to `QColor` **[verified]** | ~20 lines |
| 3.5 | Medium | Theming | Global `setColorScheme` toggle can flip the whole app's theme | ~25 lines |
| 4.1 | High | Performance | Focus change restyles every tab: 2.05 ms/click, 10 full restyles **[verified]** | ~40 lines |
| 4.2 | Medium | Performance | `DockWidget.refresh_style()` runs 3× per theme switch **[verified]** | ~10 lines |
| 4.3 | Medium | Performance | Splitter hover does `findChildren()` over the whole container | ~20 lines |
| 4.4 | Medium | Correctness | Drop geometry is a side effect of `paintEvent` | ~15 lines |
| 5.1 | High | Maintainability | 34 byte-identical methods duplicated across two 1000+ line files **[verified]** | ~2 days |
| 5.2 | Medium | Fragility | `_last_added_area_cache` retains deleted dock areas | 1 line |
| 5.3 | Medium | Cleanup | Stub methods that read as implemented (`reset()`, `update_title_bar_visibility()`) | ~30 lines |
| 6.x | High | Process | CI never runs pytest; no round-trip test exists **[verified]** | ~1 hour |

---

## 1. Critical — layout persistence is non-functional

### 1.1 The restore marker is written under one name and cleared under another

**Where:** [`lace/layout_serializer.py:376-386`](../lace/layout_serializer.py) and
[`lace/dock_container_state.py:174`](../lace/dock_container_state.py)

The engine marks every widget before rebuilding the tree:

```python
# layout_serializer.py:376
def _mark_dock_widgets_dirty(self) -> None:
    for dock_widget in self._manager.dock_widgets_map().values():
        dock_widget.setProperty("_lace_unassigned_marker", True)
```

…and then decides each widget's fate by that marker:

```python
# layout_serializer.py:380
def _restore_dock_widgets_open_state(self) -> None:
    for dock_widget in self._manager.dock_widgets_map().values():
        if dock_widget.property("_lace_unassigned_marker"):
            dock_widget.flag_as_unassigned()
        else:
            dock_widget.toggle_view_internal(not dock_widget.property("closed"))
        dock_widget.setProperty("_lace_unassigned_marker", None)
```

But the tree restorer clears a **different**, legacy property inherited from the qtpydocking port:

```python
# dock_container_state.py:170-174
dock_area.add_dock_widget(dock_widget)
dock_widget.set_toggle_view_action_checked(not closed)
dock_widget.set_closed_state(closed)
dock_widget.setProperty("closed", closed)
dock_widget.setProperty("dirty", False)          # <-- wrong name
```

Nothing ever clears `_lace_unassigned_marker`, so **every** widget takes the `flag_as_unassigned()`
branch — including the ones just successfully re-docked. `flag_as_unassigned()`
([`dock_widget.py:229`](../lace/dock_widget.py)) sets `_closed = True`, reparents the widget to the
root container, hides it, and clears its dock area.

**Verified:**

```
--- BEFORE restore ---
  Alpha: closed=False area=yes visible=True parent=DockAreaWidget
  Beta:  closed=False area=yes visible=True parent=DockAreaWidget
  Gamma: closed=False area=yes visible=True parent=DockAreaWidget
restore_state -> True
--- AFTER restore ---
  Alpha: closed=True  area=NONE visible=False parent=DockContainerWidget
  Beta:  closed=True  area=NONE visible=False parent=DockContainerWidget
  Gamma: closed=True  area=NONE visible=False parent=DockContainerWidget
```

The dock areas are rebuilt correctly (`dock_area_count=3`) — they are just emptied immediately
afterwards. `README.md:64` advertises "Save and restore complete window layouts to/from JSON files";
that feature does not currently work.

#### Minimal fix

```python
# lace/dock_container_state.py:174
-            dock_widget.setProperty("dirty", False)
+            dock_widget.setProperty("_lace_unassigned_marker", None)
```

Verified: with this single change the round-trip is correct (all three widgets return with
`closed=False`, `area=yes`, `visible=True`).

#### Structural fix (recommended — do this instead)

Qt dynamic properties are being used as cross-module control flow between two files that don't
import each other. That is exactly how these two names drifted apart, and the same pattern is used
for `"closed"` and `"currentDockWidget"`. Replace it with an explicit return value.

In `lace/dock_container_state.py`, thread an "assigned" set through the restore:

```python
def restore_container_state(c, state: dict, testing: bool = False,
                            assigned: set | None = None) -> bool:
    ...
    res, new_root_splitter = _restore_child_nodes(c, root_splitter_state, testing, assigned)
```

`_restore_dock_area` adds each widget it actually places:

```python
        if dock_widget and dock_area:
            dock_area.hide()
            dock_area.add_dock_widget(dock_widget)
            dock_widget.set_toggle_view_action_checked(not closed)
            dock_widget.set_closed_state(closed)
            if assigned is not None:
                assigned.add(dock_widget)
```

and `LayoutEngine.apply_state` owns the set:

```python
        assigned: set = set()
        for c_info in state_dict["containers"]:
            ...
            restore_container_state(root, c_data, testing=False, assigned=assigned)
```

This removes `_mark_dock_widgets_dirty()`, both `setProperty` calls, and the whole class of bug.
While you are there: `flag_as_unassigned()` writes `self._closed = True` directly instead of calling
`set_closed_state()` — route it through the setter so the state has one write path.

---

### 1.2 `ensure_active_dock_area()` calls a method that does not exist

**Where:** [`lace/dock_manager.py:766-780`](../lace/dock_manager.py), called from
[`dock_manager.py:368`](../lace/dock_manager.py)

```python
        from lace.dock_area_widget import DockAreaWidget
        for area in self.find_children(DockAreaWidget):    # <-- AttributeError
```

`DockManager` is a `QObject`; the Qt method is `findChildren`. The module-level `find_children`
helper in `lace/util.py` is not imported here. Even with the right name it would find nothing:
`_root` is parented to the application window, not to the manager.

**Verified:** `ensure_active_dock_area -> AttributeError: 'DockManager' object has no attribute 'find_children'`

It is latent only because the early-return at line 767 usually short-circuits. It fires whenever the
active area is `None`, hidden, or deleted — and the call site is **outside** the
`try/except LayoutError` in `restore_state()`, so it escapes the public API as an unhandled
`AttributeError` after a restore that already "succeeded".

#### Fix

Use the model you already maintain rather than a widget-tree search:

```python
    def ensure_active_dock_area(self):
        current = getattr(self, '_active_dock_area', None)
        if current is not None and _is_widget_alive(current):
            try:
                if not current.isHidden():
                    return
            except RuntimeError:
                pass

        for container in self.dock_containers():
            for area in container.opened_dock_areas():
                try:
                    if area.open_dock_widgets_count() > 0:
                        self.set_active_dock_area(area)
                        return
                except RuntimeError:
                    continue
```

Also move the call inside the `try` block in `restore_state()` (or wrap it), so a failure here can
never turn a successful restore into an exception.

---

### 1.3 A failed restore leaves the container half-mutated and reports success

**Where:** [`lace/layout_serializer.py:267-282`](../lace/layout_serializer.py),
[`lace/dock_container_state.py:55-94`](../lace/dock_container_state.py)

`apply_state` discards both return values:

```python
            if c_info.get("is_main"):
                restore_container_state(root, c_data, testing=False)     # bool ignored
            else:
                fw.restore_state(c_data, testing=False)                  # bool ignored
```

Meanwhile `restore_container_state` destroys the container's internal model **before** any of the
paths that can `return False`:

```python
    if not testing:
        c._visible_dock_area_count = -1
        c._dock_areas.clear()                # <-- destructive
        c._last_added_area_cache.clear()

    if is_floating:
        geometry_string = state.get("geometry", "")
        if not geometry_string:
            return False                     # <-- model already cleared
```

There are four such early returns (empty geometry, empty hex, `widget_count == 0`,
`len(sizes) != widget_count`, missing widget name). Any of them leaves `_dock_areas == []` while the
old splitter tree is still installed in the layout — the model and the widget tree disagree
permanently, and `DockManager.restore_state()` returns `True`.

#### Fix

Two changes, in order of value:

**(a) Validate the whole payload before touching anything.** `_validate_can_restore` already exists
and is documented as "Validates the state tree against reality BEFORE any mutations occur" — extend
it to actually walk the container tree using the existing `testing=True` dry-run mode, which was
built for exactly this and is currently never used from the engine:

```python
    def _validate_can_restore(self, state_dict):
        ...existing checks...

        # Dry-run the tree: testing=True builds nothing and mutates nothing.
        for c_info in state_dict["containers"]:
            if not restore_container_state(self._manager.root_container(),
                                           c_info.get("data", {}), testing=True):
                raise RestoreFailureError(
                    f"Container {c_info.get('id')!r} failed structural pre-validation.")
```

This finally gives `RestoreFailureError` (currently defined, exported, unit-tested for its class
hierarchy, and never raised) a purpose.

**(b) Honour the return values** so a mid-flight failure is loud:

```python
            if c_info.get("is_main"):
                if not restore_container_state(root, c_data, testing=False):
                    raise RestoreFailureError("Main container restore failed mid-flight.")
```

Note that a mid-flight failure is *still* unrecoverable at that point — which is why (a) matters
more than (b). If you want true atomicity later, build the new splitter tree detached and swap it in
one `replaceWidget` call at the end.

---

### 1.4 Maximize state survives a restore as a dangling pointer

**Where:** [`lace/dock_container_widget.py:282-283`](../lace/dock_container_widget.py) and
[`lace/dock_container_state.py:60-63`](../lace/dock_container_state.py)

`restore_container_state` resets `_dock_areas`, `_last_added_area_cache` and
`_visible_dock_area_count`, but not `_maximized_dock_area`, `_pre_maximize_splitter_sizes` or
`_top_level_dock_area`.

**Verified** — saving while a dock area is maximized and restoring:

```
BEFORE:  maximized area set=True   siblings hidden=[True, False]
AFTER:   maximized area set=True   siblings hidden=[False, False]
```

All areas are visible (the maximize is visually lost), but the container still believes an area is
maximized — and `_maximized_dock_area` now points at a `DockAreaWidget` that was destroyed with the
old splitter tree. The next `toggle_maximize_dock_area()` call routes into
`_restore_maximized_area()` and touches a deleted C++ object.

#### Fix

```python
# lace/dock_container_state.py, in restore_container_state()
    if not testing:
        c._visible_dock_area_count = -1
        c._dock_areas.clear()
        c._last_added_area_cache.clear()
+       c._maximized_dock_area = None
+       c._pre_maximize_splitter_sizes = None
+       c._top_level_dock_area = None
```

Then decide whether maximize should round-trip at all (see §2.3).

---

## 2. Is the JSON state complete? — measured answer

With 1.1 patched out, I round-tripped a layout containing: two tabs in one area, a second area with
a runtime feature change and an area lock, a pinned auto-hide widget, a floating window, and a
maximized dock area.

### Preserved correctly

Splitter tree, orientations and sizes · dock-area composition · tab order · **current tab index**
(`current_index=1` survived) · per-widget `closed` flag · floating-window membership · floating
geometry (exact: `302,202,500,400`) · which widgets are pinned and to which edge · sidebar overlay
sizes · sidebar settings (`auto_show_on_hover`, `animations_enabled`, `keep_open`).

That is a solid core. The gaps below are all additive.

### Lost or corrupted

| State | Before | After | Cause |
|---|---|---|---|
| `DockAreaWidget.locked_name` | `"locked-bottom"` | `None` | not serialized |
| `DockWidget.locked_to_area` | set | `None` | not serialized |
| Pinned widget `closed` | `False` | **`True`** | ordering bug, see 2.2 |
| Pinned widget `widget_state` | `pinned_hidden` | inconsistent with `closed` | same |
| Maximized dock area | maximized | lost + dangling ref | see 1.4 |
| `DockWidgetFeature` flags | runtime-modified | not serialized | by design? see 2.6 |
| Sidebar button hidden state | `hide_widget()` applied | not serialized | not serialized |

---

### 2.1 Area and widget locks are not serialized

**Where:** [`lace/dock_area_widget.py:329-340`](../lace/dock_area_widget.py),
[`lace/dock_widget.py:221-227`](../lace/dock_widget.py)

`locked_name` gates `features()` (it strips `pinnable` and forces `floatable`), so losing it on
restore silently changes what the user can do with a panel.

#### Fix

```python
# dock_area_widget.py — save_state()
         return {
             "type": "Area",
             "tabs": self._contents_layout.count(),
             "current": name,
+            "locked_name": self._locked_name,
             "widgets": [self.dock_widget(i).save_state()
                         for i in range(self._contents_layout.count())]
         }
```

```python
# dock_widget.py — save_state()
         return {
             "type": "Widget",
             "name": self.objectName(),
-            "closed": self._closed
+            "closed": self._closed,
+            "locked_to_area": self._locked_to_area,
         }
```

```python
# dock_container_state.py — _restore_dock_area(), before _append_dock_areas
     else:
         dock_area.setProperty("currentDockWidget", current_dock_widget)
+        if state.get("locked_name") is not None:
+            dock_area.locked_name = state["locked_name"]
         c._append_dock_areas(dock_area)
```

and inside the per-widget loop:

```python
+            if widget_state.get("locked_to_area") is not None:
+                dock_widget.locked_to_area = widget_state["locked_to_area"]
```

Both are property setters that call `_update_title_bar_button_states()`, so button state follows
automatically. Guard with `is not None` so old files (which omit the key) don't clear a lock the
application set at construction time.

---

### 2.2 Pinned widgets come back closed

**Where:** [`lace/layout_serializer.py:289-291`](../lace/layout_serializer.py)

```python
        self._restore_dock_widgets_open_state()
        self._restore_sidebar_state(state_dict.get("sidebars", {}))
```

A pinned widget lives in the sidebar, not in any container, so it is absent from the saved container
tree. `_restore_dock_widgets_open_state` therefore flags it unassigned (`_closed = True`) — and only
*afterwards* does `_restore_sidebar_state` re-pin it. **Verified:** `before save: closed=False` →
`after restore: closed=True`, with the trace showing `pin_widget` running at
`layout_serializer.py:290`, i.e. after the damage.

Visible consequence: every pinned panel's entry in the View menu unchecks itself on every restore,
and `is_closed()` returns `True` for a panel that is sitting visibly in the sidebar.

#### Fix

Swap the order and give `widget_states` a real job (see 2.3):

```python
-        self._restore_dock_widgets_open_state()
-        self._restore_sidebar_state(state_dict.get("sidebars", {}))
-        self._restore_dock_areas_indices(state_dict.get("widget_states", {}))
+        self._restore_sidebar_state(state_dict.get("sidebars", {}))
+        self._restore_dock_widgets_open_state(state_dict.get("widget_states", {}))
+        self._restore_dock_areas_indices()
         self._emit_top_level_events()
```

`layout_serializer.py` does not currently import `WidgetState` — add
`from lace.enums import WidgetState` at the top.

```python
    def _restore_dock_widgets_open_state(self, widget_states: Dict[str, Dict[str, Any]]) -> None:
        sidebar_mgr = getattr(self._manager, 'sidebar_manager', None)

        for name, dock_widget in self._manager.dock_widgets_map().items():
            saved = widget_states.get(name, {})

            if sidebar_mgr is not None and sidebar_mgr.is_pinned(dock_widget):
                # Pinned widgets are owned by the sidebar, not the container tree:
                # restore their open flag from widget_states instead of the tree.
                closed = bool(saved.get("closed", False))
                dock_widget.set_closed_state(closed)
                dock_widget.set_toggle_view_action_checked(not closed)
                dock_widget.set_widget_state(
                    WidgetState.pinned_hidden if closed else dock_widget.widget_state())
            elif not dock_widget.property("_lace_unassigned_marker"):
                dock_widget.toggle_view_internal(not dock_widget.property("closed"))
            else:
                dock_widget.flag_as_unassigned()

            dock_widget.setProperty("_lace_unassigned_marker", None)
```

**Watch out when reordering:** `SidebarManager.pin_widget` calls
`dock_area.remove_dock_widget(dock_widget)` if the widget currently has an area. Previously
`flag_as_unassigned()` had already cleared the area, so this was a no-op; now it can run for real
and may delete a newly-created empty dock area mid-restore. That is the correct precedence (a widget
cannot be both docked and pinned), but it must be covered by the new round-trip test (§6) before you
ship it.

---

### 2.3 The `widget_states` block is written but never read

**Where:** [`lace/layout_serializer.py:215-242`](../lace/layout_serializer.py) (writer),
[`:403-416`](../lace/layout_serializer.py) (supposed reader)

`_save_widget_states()` emits `closed`, `state`, `container_id`, `in_dock_area`, `tab_index` and
`pinned` for every widget. The only consumer is the missing-widget prune at line 324. The method
that takes it as a parameter ignores it entirely:

```python
    def _restore_dock_areas_indices(self, widget_states: Dict[str, Dict[str, Any]]) -> None:
        for dock_container in self._manager.dock_containers():
            for i in range(dock_container.dock_area_count()):
                dock_area = dock_container.dock_area(i)
                dock_widget_name = dock_area.property("currentDockWidget")   # reads a property instead
```

In my 5-widget probe this dead block was ~40% of the JSON. Worse, it is a second, divergent
representation of state the container tree already owns — exactly the condition that produced
finding 1.1.

#### Fix — pick one, don't leave it as is

- **Option A (recommended):** keep only what nothing else stores. After 2.2, `closed` is genuinely
  needed for pinned widgets. Reduce the writer to that, plus anything else you decide to persist:

  ```python
      def _save_widget_states(self) -> Dict[str, Dict[str, Any]]:
          """Per-widget state that the container tree does NOT already carry.

          Widgets inside a dock area are fully described by the tree; only
          sidebar-pinned widgets (which live outside it) need an entry here.
          """
          states = {}
          sidebar_mgr = getattr(self._manager, 'sidebar_manager', None)
          for name, dock_widget in self._manager.dock_widgets_map().items():
              if sidebar_mgr is not None and sidebar_mgr.is_pinned(dock_widget):
                  states[name] = {
                      "closed": dock_widget.is_closed(),
                      "pinned": True,
                  }
          return states
      ```

  Then drop the unused parameter from `_restore_dock_areas_indices`, and adjust the
  `_validate_can_restore` prune (it currently uses `widget_states` keys as the reality check — move
  that check onto the container tree's widget names, which is where the real references live).

- **Option B:** make it authoritative and delete the `currentDockWidget` dynamic property, restoring
  the active tab from `tab_index` instead. More work, but it removes another dynamic property.

---

### 2.4 Floating geometry is stored twice in conflicting formats

**Where:** [`dock_container_state.py:31-35`](../lace/dock_container_state.py) writes a hex
`saveGeometry()` blob; [`layout_serializer.py:191-204`](../lace/layout_serializer.py) writes
`{x, y, width, height, is_maximized}` for the same window.

On restore, `restore_container_state` applies `restoreGeometry(blob)`
([`dock_container_state.py:77`](../lace/dock_container_state.py)) and then
`_apply_container_geometry` immediately overwrites it with `setGeometry(x, y, w, h)`
([`layout_serializer.py:371`](../lace/layout_serializer.py)) — discarding the screen assignment,
DPI context and window state that `saveGeometry()` encodes. Then `is_maximized` is re-applied by hand
via a deferred `showMaximized()`.

#### Fix

Keep the Qt blob (it handles multi-monitor and DPI correctly, which the hand-rolled path at
`layout_serializer.py:333-374` re-implements approximately) and reduce `container_geometries` to the
one thing the blob cannot express across machines: an off-screen rescue check.

```python
    def _apply_container_geometry(self, fw, geo):
        """Sanity-check geometry that restoreGeometry() already applied.

        Only intervenes when the window would land entirely off-screen
        (e.g. a monitor was unplugged since the layout was saved).
        """
        target = fw.geometry()
        if any(s.availableGeometry().intersects(target) for s in QGuiApplication.screens()):
            return
        primary = QGuiApplication.primaryScreen()
        ...centre on primary...
```

If you'd rather drop the blob instead, then also persist `screen().name()` and the logical DPI so
the x/y values can be interpreted on the target machine.

---

### 2.5 No schema version, and the format identifier is wrong

**Where:** [`layout_serializer.py:155`](../lace/layout_serializer.py),
[`:464-472`](../lace/layout_serializer.py)

```python
    SYSTEM_TYPE: str = "QtAdvancedDockingSystem"
```

Two problems:

1. A layout file written by the actual C++ Qt-Advanced-Docking-System passes the type gate and then
   fails structurally deep inside the restore.
2. The `version` field is the **caller's** application data version
   (`save_state(version=N)`), not the Lace format version. There is no way to tell a v0 file written
   by Lace 0.3 from one written by Lace 0.9. When you next change the tree format — and 2.1–2.4 all
   change it — every old file will pass validation and then misbehave.

#### Fix

```python
class LayoutStateBuilder:
    SYSTEM_TYPE: str = "LaceDockingSystem"
    SCHEMA_VERSION: int = 1          # bump on every layout-format change

    def build_state_dict(self, version: int) -> Dict[str, Any]:
        state_dict = {
            "type": self.SYSTEM_TYPE,
            "schema": self.SCHEMA_VERSION,
            "version": version,       # application data version, caller-owned
            ...
        }
```

```python
    def deserialize(self, state_json: str, target_version: int) -> None:
        ...
        if state_dict.get("type") not in (self.SYSTEM_TYPE, "QtAdvancedDockingSystem"):
            raise InvalidFormatError(...)

        schema = state_dict.get("schema", 0)
        if schema > LayoutStateBuilder.SCHEMA_VERSION:
            raise InvalidFormatError(
                f"Layout was written by a newer Lace (schema v{schema}; "
                f"this build understands up to v{LayoutStateBuilder.SCHEMA_VERSION}).")
```

Accepting the old string keeps existing user files loadable. Document in `ARCHITECTURE.md` that
`version` is application-owned and `schema` is Lace-owned.

---

### 2.6 Smaller persistence items

- **`DockWidgetFeature` flags are not serialized.** Defensible (the app usually sets them at
  construction), but `set_features()` is public and runtime-callable, so this needs a sentence in
  the docs: *"Features are not persisted; re-apply them when you recreate your dock widgets."*
  Alternatively persist them next to `locked_to_area` in `DockWidget.save_state()`.
- **`RestoreFailureError` is never raised** — [`layout_serializer.py:50`](../lace/layout_serializer.py).
  Fixed by 1.3.
- **File-descriptor leak on a rare path** — [`layout_serializer.py:85-89`](../lace/layout_serializer.py):
  if `os.fdopen(fd, ...)` raises, `fd` is never closed. Move `mkstemp` inside the `try`, or wrap:

  ```python
      fd, temp_file_str = tempfile.mkstemp(dir=filepath.parent, prefix="layout_tmp_",
                                           suffix=".json", text=True)
      temp_path = Path(temp_file_str)
      try:
          with os.fdopen(fd, 'w', encoding='utf-8') as f:
              f.write(state_json)
              f.flush()
              os.fsync(f.fileno())
      except BaseException:
          os.close(fd)          # only if fdopen itself failed
          raise
  ```

- **The directory is never fsynced**, so on POSIX the atomic rename is not durable across power
  loss. Add an `os.open(dir, O_DIRECTORY)` + `os.fsync` after `_safe_replace` if that matters to you.
- **`sidebar_state` key space is mixed** — [`layout_serializer.py:506-512`](../lace/layout_serializer.py):
  `SidebarStateManager` is keyed by widget `objectName()` in
  [`sidebar_manager.py:218`](../lace/sidebar_manager.py) and by `DockWidgetArea.name` in
  [`sidebar_manager.py:171`](../lace/sidebar_manager.py). A dock widget named `"left"` collides with
  the left sidebar's default size. Use two dicts, or prefix the keys (`"w:Explorer"` / `"a:left"`).

---

## 3. Theming engine

The architecture is good — one source of truth, generation-counter caching, painted chrome instead
of stylesheets. The problems are all in the token plumbing.

### 3.1 "Ghost tokens": the effective schema is not the dataclass

**Where:** [`lace/dock_style_manager.py:40-47`](../lace/dock_style_manager.py)

```python
def _create_default_schema(category: DockStyleCategory) -> Any:
    schema = _SCHEMA_MAP[category]()
    if category in BASE_DOCK_DEFAULTS:
        for key, val in copy.deepcopy(BASE_DOCK_DEFAULTS[category]).items():
            setattr(schema, key, deep_to_qcolor(val))    # no hasattr check
```

A bare `setattr` on a non-slotted dataclass instance *creates* attributes that aren't fields. So the
live schema is `declared fields ∪ whatever BASE_DOCK_DEFAULTS happens to seed`. The two read paths
then disagree:

- `get()` uses `hasattr` → **sees** ghost tokens ([`:134-141`](../lace/dock_style_manager.py))
- `get_all()` iterates `dataclasses.fields()` → **cannot see** them ([`:143-147`](../lace/dock_style_manager.py))

**Verified:**

```
tokens emitted by build_theme that are NOT dataclass fields:
  PANEL:     ['content_margin']
  SIDEPANEL: ['border_color', 'border_width', 'focus_border_color']
  TAB:       ['title_text_color']
  TITLE_BAR: ['border_bottom']

which survive into the manager?
  PANEL.content_margin        = 12                    (seeded by BASE_DOCK_DEFAULTS -> works)
  SIDEPANEL.border_color      = QColor(...)           (seeded -> works)
  SIDEPANEL.border_width      = 2.0                   (seeded -> works)
  SIDEPANEL.focus_border_color= QColor(...)           (seeded -> works)
  TAB.title_text_color        = QColor(...)           (seeded -> works)
  TITLE_BAR.border_bottom     = <<DROPPED>>           (NOT seeded -> silently discarded)

get_all() exposes: PANEL [] · TAB [] · SIDEPANEL []   <- invisible to every get_all() consumer
```

`get_all()` is used by 20 call sites including `DockAreaWidget.refresh_style`,
`DockAreaTitleBar.refresh_style`, `DockWidgetTab.refresh_style`, `SideBarContainer.refresh_style`
and the full-theme broadcast at [`:118-120`](../lace/dock_style_manager.py). Anything read through
`get_all()` that happens to be a ghost is permanently `None`.

#### Fix — three parts

**(a) Declare every token `build_theme` can emit.**

```python
# lace/dock_theme.py

@dataclass
class DockPanelStyleSchema:
    ...
    margin: int = 0
+   # Content inset applied by DockWidget to its own layout. Scalar, or
+   # (horizontal, top) / 4-tuple. NOT a colour — see _COLOR_FIELDS.
+   content_margin: Union[int, float, List[int], Tuple[int, ...]] = 6


@dataclass
class DockTitleBarStyleSchema(_ActionButtonFields, _FontFields):
    ...
    border_width: float = 0.0
+   border_bottom: float = 0.0     # bottom-edge rule; falls back to border_width when 0


@dataclass
class DockSidePanelStyleSchema(_ActionButtonFields):
    ...
    corner_radius: int = 0
+   border_width: float = 1.0
+   border_color: Optional[List[int]] = None
+   focus_border_color: Optional[List[int]] = None
```

For `TAB.title_text_color` there is no consumer at all — delete it from `_build_tab`
([`dock_theme.py:620`](../lace/dock_theme.py)) rather than adding a field.

**(b) Make unknown tokens loud instead of silent.**

```python
# dock_style_manager.py
def _create_default_schema(category):
    schema = _SCHEMA_MAP[category]()
    if category in BASE_DOCK_DEFAULTS:
        for key, val in copy.deepcopy(BASE_DOCK_DEFAULTS[category]).items():
            if not hasattr(schema, key):
                logger.warning("Default theme sets unknown token %s.%s — ignored. "
                               "Declare it on %s.", category.name, key, type(schema).__name__)
                continue
            setattr(schema, key, _coerce(schema, key, val))
    return schema
```

```python
    def _set_field(self, schema, key, value, changed):
        if not hasattr(schema, key):
            logger.warning("Theme sets unknown token %s on %s — ignored.",
                           key, type(schema).__name__)
            return
```

With (a) applied, these warnings should be silent at import; if they aren't, you have another ghost.

**(c) Add a regression test** so this cannot recur — see §6.

---

### 3.2 `title_border_bottom` is dead end-to-end

This is the one ghost that isn't rescued by `BASE_DOCK_DEFAULTS`, and it fails at **three**
independent points:

1. `ThemeSpec.title_border_bottom` → `build_theme` writes it as `TITLE_BAR["border_bottom"]`
   ([`dock_theme.py:524-525`](../lace/dock_theme.py)) → dropped by `_set_field` (3.1).
2. [`dock_area_title_bar.py:445`](../lace/dock_area_title_bar.py) reads
   `styles.get("border_bottom", self._border_width)` through `get_all()` → always the fallback.
3. [`sidebar_title_bar.py:300-301`](../lace/sidebar_title_bar.py) reads the **wrong key names**
   from the TITLE_BAR dict:

   ```python
   self._title_border_bottom = title_styles.get("title_border_bottom")   # key is "border_bottom"
   self._title_border_color  = title_styles.get("title_border_color")    # key is "border_color"
   ```

   Both always `None`, so the paint guard at [`:363`](../lace/sidebar_title_bar.py) never fires.

It is also a documented, pydantic-validated field on `ThemeJson`
([`theme_models.py:131`](../lace/theme_models.py)), and
[`dock_custom_theme.py:261`](../lace/dock_custom_theme.py) ships a theme with
`title_border_bottom = 1.5  # 1.5px glowing cyan dividing line below title bar` that draws nothing.

#### Fix

Apply 3.1(a) to add `border_bottom`, then:

```python
# lace/sidebar_title_bar.py:300-301
-        self._title_border_bottom = title_styles.get("title_border_bottom")
-        self._title_border_color = title_styles.get("title_border_color")
+        self._title_border_bottom = title_styles.get("border_bottom")
+        self._title_border_color = title_styles.get("border_color")
```

Then visually confirm with the `dock_custom_theme` entry that ships the cyan rule.

---

### 3.3 Sidebar panel border/focus colours can never be themed

Consequence of 3.1. [`sidebar_container.py:702-717`](../lace/sidebar_container.py):

```python
        card_border = s.get("border_width")          # ghost -> None
        if card_border is None or card_border <= 0.0:
            card_border = core_styles.get("border_width", 0.0)

        bcolor = s.get("border_color")               # ghost -> None
        if bcolor is None:
            bcolor = core_styles.get("border_color")

        fcolor = s.get("focus_border_color")         # ghost -> None
        if fcolor is None:
            fcolor = core_styles.get("focus_border_color")
```

Every branch takes the CORE fallback, so `_build_sidepanel`'s explicit `"border_width": 1.0` and its
dedicated border colours are unreachable and the sidebar panel can never be styled differently from
the dock cards. Fixed by 3.1(a); no change needed here once the fields exist. Worth re-checking the
fallback chain afterwards — several of these `if x is None` ladders exist only to paper over the
ghost problem and can be simplified once the tokens are real.

---

### 3.4 Any 3–4 element numeric token is silently converted to a `QColor`

**Where:** [`dock_style_manager.py:175-183`](../lace/dock_style_manager.py) →
[`dock_theme.py:744-765`](../lace/dock_theme.py)

`_set_field` calls `deep_to_qcolor(value)` unconditionally, and `is_color_list()` decides purely by
*shape*: "a list/tuple of 3–4 numbers". So a CSS-style margin becomes a colour.

**Verified:**

```
content_margin=6              -> stored as 6
content_margin=(8, 2)         -> stored as (8, 2)
content_margin=[6, 4, 6]      -> stored as QColor(0.023529, 0.015686, 0.023529, 1.0)
content_margin=[6, 4, 6, 4]   -> stored as QColor(0.023529, 0.015686, 0.023529, 0.015686)
```

`DockWidget.refresh_style` ([`dock_widget.py:533-543`](../lace/dock_widget.py)) then matches neither
the numeric nor the list branch and silently falls through to `6, 6, 6, 6`. A user writing a
four-sided content margin gets no error and no effect.

#### Fix

Decide colour-ness by the *field*, not the value. Cheapest version, using the declared annotations:

```python
# lace/dock_style_manager.py
from functools import lru_cache

@lru_cache(maxsize=None)
def _color_fields(schema_type: type) -> frozenset[str]:
    """Field names whose declared type is a colour (Optional[List[int]])."""
    return frozenset(
        f.name for f in fields(schema_type)
        if "List[int]" in str(f.type)
    )

def _coerce(schema, key, value):
    if key in _color_fields(type(schema)):
        return deep_to_qcolor(value)
    return value          # geometry / typography passes through untouched
```

and use `_coerce` in both `_set_field` and `_create_default_schema`.

The more explicit alternative (worth it if the theme schema keeps growing) is to tag the fields:

```python
def color(default=None):
    return field(default=default, metadata={"kind": "color"})

@dataclass
class DockCoreStyleSchema(_FontFields):
    canvas_bg: Optional[List[int]] = color()
    border_color: Optional[List[int]] = color()
```

Then `_color_fields` reads `f.metadata.get("kind") == "color"` — unambiguous and self-documenting.
Either way, keep `to_qcolor()` accepting hex strings so `"#rrggbb"` themes keep working.

---

### 3.5 A floating window can flip the whole application's theme

**Where:** [`floating_dock_container.py:419-457`](../lace/floating_dock_container.py)

```python
        qapp.setPalette(palette)          # application-wide
        ...
        hints.setColorScheme(opposite)    # global
        hints.setColorScheme(target)      # global
```

This runs from `_do_restore_geometry()` after `setWindowFlags()`, i.e. whenever the
`chromeless_float` config flag changes. Three separate problems:

1. `qapp.setPalette()` re-polishes every widget in the process to fix one window's native frame.
2. [`:403`](../lace/floating_dock_container.py) also calls `qapp.setStyle(qapp.style().objectName())`
   — a second full application re-polish.
3. The `setColorScheme` toggle emits `colorSchemeChanged` **twice, once with the wrong scheme**. If
   the application installed `ThemeManager.install_listener()`
   ([`theme_manager.py:272-288`](../lace/theme_manager.py)), that fires `sync_theme()` → the app
   flips to the light theme and back. Toggling one dock flag visibly strobes the whole UI.

#### Fix

Scope the DWM nudge to the window that needs it, and never touch global style hints:

```python
    def _apply_dock_palette_to_window(self) -> None:
        """Re-push the dock palette onto this window's new native handle."""
        try:
            colors = resolve_dock_colors()
            self.setPalette(build_dock_palette(is_panel=False, colors=colors))
        except Exception:
            logger.debug("Dock theme unavailable; keeping default palette", exc_info=True)

        # Windows: ask DWM to re-evaluate this window only.
        handle = self.windowHandle()
        if handle is not None:
            handle.requestUpdate()
```

If the DWM dark-frame update genuinely requires a scheme change on your Qt version, gate it behind
`sys.platform == "win32"`, do it once at startup, and add a re-entrancy guard in
`ThemeManager._on_color_scheme_changed` so a programmatic toggle cannot recurse into `sync_theme()`.
Also drop the `qapp.setStyle()` call at line 403 — `DockThemeBridge` already owns style application.

---

### 3.6 Smaller theming items

- **`QStyle` ownership** — [`dock_theme_bridge.py:91-103`](../lace/dock_theme_bridge.py):
  `QWidget.setStyle()` does not take ownership of the `QStyle` returned by `QStyleFactory.create()`.
  Keep a reference: `self._style = style` before `setStyle(style)`. (The `isinstance(QApplication)`
  branch there is also dead — both arms call `self._target.setStyle(style)`.)
- **`get_all()` returns shared `QColor` objects** — [`:143-147`](../lace/dock_style_manager.py)
  copies the dict but not the values. A caller doing `c = styles.get("bg_normal"); c.setAlpha(200)`
  corrupts the theme process-wide. Either return `QColor(v)` copies or document the dict as
  read-only.
- **`ThemeManager` mixes QSS and the palette engine** — [`theme_manager.py:220-235`](../lace/theme_manager.py)
  applies raw `.qss` files with `setStyleSheet()`, which overrides palette colours on styled widgets
  and will half-override the dock chrome. Either document the precedence explicitly or drop the QSS
  path in favour of JSON themes.
- **Redundant exception tuple** — [`theme_manager.py:86`](../lace/theme_manager.py):
  `except (ValueError, TypeError, Exception)` is just `except Exception`.
- **`ThemeJson` type drift** — [`theme_models.py:129,137`](../lace/theme_models.py) declares
  `title_margin: Optional[float]` and `indicator_width: Optional[float]` where `ThemeSpec` declares
  `int`. Harmless today; align them so the JSON schema and the dataclass can't diverge further.

---

## 4. Performance

Measured on a 4-area × 5-tab layout (20 dock widgets), offscreen — so these are Python + Qt object
costs only; real painting adds more.

```
20 dock-area focus switches:  41.0 ms  (2.05 ms each)  — 190 DockWidgetTab.refresh_style calls
20 tab switches in one area:  29.0 ms                  —  50 DockWidgetTab.refresh_style calls
6 full theme switches:       157.5 ms  (26.3 ms each)
   per switch: DockWidget×12, DockAreaTitleBar×4, DockWidgetTab×20
```

### 4.1 Every focus change fully restyles every visible tab

**Where:** [`dock_area_widget.py:96-101`](../lace/dock_area_widget.py)

```python
    def set_chrome_focused(self, focused: bool):
        super().set_chrome_focused(focused)
        for widget in self.opened_dock_widgets():
            tab = widget.tab_widget()
            if tab:
                tab.refresh_style()
```

`DockManager.set_active_dock_area()` calls this on the losing *and* gaining area, so a single click
triggers ~10 full restyles here (190 for 20 switches, verified). And
[`DockWidgetTab.refresh_style`](../lace/dock_widget_tab.py) is expensive — per call it:

- builds and applies a stylesheet on the close button ([`:610`](../lace/dock_widget_tab.py))
- applies a second stylesheet on the title label ([`:597`](../lace/dock_widget_tab.py))
- re-creates the close icon via the provider ([`:631`](../lace/dock_widget_tab.py))
- builds and sets a `QFont` twice ([`:636-643`](../lace/dock_widget_tab.py))
- calls `update_icon()`, which hits the provider again ([`:644`](../lace/dock_widget_tab.py))

`setStyleSheet` forces a full unpolish/repolish of the widget subtree — the most expensive routine
operation in Qt, and it is running on every click. `set_active_tab()`
([`:392-399`](../lace/dock_widget_tab.py)) does the same on every tab switch.

#### Fix — split focus repaint from full restyle

Only two values actually depend on focus (and only when `tab_dimming` is on): `self._indicator` and
the label text colour.

```python
# lace/dock_widget_tab.py

    def refresh_focus_tint(self) -> None:
        """Cheap path: recompute only the focus-dependent colours and repaint.

        Called on focus/active-tab changes, which happen on every click.  The
        expensive work in refresh_style() (stylesheets, icon re-render, fonts)
        is theme-dependent, not focus-dependent, so it must not run here.
        """
        styles = self._style_mgr.get_all(DockStyleCategory.TAB)
        indicator, text_color = self._resolve_focus_colors(styles)

        self._indicator = indicator
        if text_color is not None and text_color != self._applied_text_color:
            self._applied_text_color = text_color
            pal = self._title_label.palette()
            pal.setColor(QPalette.WindowText, text_color)
            self._title_label.setPalette(pal)
            self._title_label.setStyleSheet(f"color: {text_color.name()};")
        self.update()
```

Factor the existing focus/dimming block ([`:541-591`](../lace/dock_widget_tab.py)) into
`_resolve_focus_colors(styles)` and call it from both paths. Then:

```python
# dock_area_widget.py:96
     def set_chrome_focused(self, focused: bool):
         super().set_chrome_focused(focused)
         for widget in self.opened_dock_widgets():
             tab = widget.tab_widget()
             if tab:
-                tab.refresh_style()
+                tab.refresh_focus_tint()
```

```python
# dock_widget_tab.py:392
     def set_active_tab(self, active: bool):
         if self._is_active_tab == active:
             self.update_close_button_visibility()
             return
         self._is_active_tab = active
         self.update_close_button_visibility()
-        self.refresh_style()
+        self.refresh_focus_tint()
+        if self._font_weight_differs_when_active():
+            self._apply_font()          # only if the theme sets active_font_weight
         self.active_tab_changed.emit()
```

Note the `_applied_text_color` guard: **make every expensive setter conditional on the value
actually changing.** That principle applies to `refresh_style()` too — cache the last-applied
stylesheet string, icon key and font, and skip the call when they match. That alone will cut the
theme-switch cost materially.

Expected: focus switches drop from ~2.05 ms to well under 0.1 ms.

### 4.2 `DockWidget.refresh_style()` runs three times per theme switch

**Where:** [`dock_widget.py:615-623`](../lace/dock_widget.py) and
[`dock_theme_bridge.py:152-160`](../lace/dock_theme_bridge.py)

`DockWidget` overrides `DockStyled.on_style_changed` and calls `refresh_style()` **directly**,
bypassing the `QTimer.singleShot(0)` coalescing that every other widget class gets from
[`dock_styled.py:42-47`](../lace/dock_styled.py). It is subscribed to both `PANEL` and `CORE`, so a
full theme apply calls it twice — then `DockThemeBridge.refresh_dock_palette()` sweeps
`findChildren(DockWidget)` and calls it a third time. (Verified: `DockWidget×12` for 4 visible
widgets.)

#### Fix

Keep the "defer while hidden" behaviour, delegate the rest to the base class:

```python
# lace/dock_widget.py
     def on_style_changed(self, category, changes):
         if category not in (DockStyleCategory.PANEL, DockStyleCategory.CORE):
             return
         if not self.isVisible():
             self._style_dirty = True       # flushed by showEvent()
             return
-        self.refresh_style()
+        super().on_style_changed(category, changes)   # debounced to one refresh per frame
```

Then delete the redundant sweep in the bridge:

```python
# lace/dock_theme_bridge.py:152-160
-        from lace.dock_widget import DockWidget
-        if isinstance(self._target, QApplication):
-            for window in self._target.topLevelWidgets():
-                for dw in window.findChildren(DockWidget):
-                    dw.refresh_style()
-        elif isinstance(self._target, QWidget):
-            for dw in self._target.findChildren(DockWidget):
-                dw.refresh_style()
```

Every `DockWidget` registers itself with the style manager in `_init_dock_style()`, so it will get
the callback anyway. Verify with `dev_smoke/smoke_themeswitch.py` and `smoke_theme_palette.py` after
removing it — if a widget stops updating, the real bug is a missing registration, not a missing
sweep.

### 4.3 Splitter junction detection walks the widget tree on every hover event

**Where:** [`dock_splitter.py:74-100`](../lace/dock_splitter.py), called from
[`:203`](../lace/dock_splitter.py) (`HoverMove`/`HoverEnter`) and [`:181`](../lace/dock_splitter.py)
(press)

```python
        for h in container.findChildren(DockSplitterHandle):
            ...
            top_left = h.mapToGlobal(rect.topLeft())
            bottom_right = h.mapToGlobal(rect.bottomRight())
```

A full recursive tree search plus two `mapToGlobal` calls per handle, on every mouse-move over any
handle.

#### Fix

Cache the handle list on the container and invalidate it when the layout changes:

```python
    def _all_handles(self):
        container = find_parent(DockContainerWidget, self) or self.window()
        if container is None:
            return []
        cache = getattr(container, "_handle_cache", None)
        if cache is None:
            cache = container.findChildren(DockSplitterHandle)
            container._handle_cache = cache
        return cache
```

and in `DockContainerWidget`, clear it from `_emit_dock_areas_added` / `_emit_dock_areas_removed`
(both already exist as the single choke points for layout changes):

```python
    def _emit_dock_areas_added(self):
        self._visible_dock_area_count = -1
+       self._handle_cache = None
        ...
```

Also note `DockSplitterHandle.active_drag_handles` ([`:48`](../lace/dock_splitter.py)) is a
**class-level** mutable set, shared across every `DockManager` in the process. Move it to an instance
or container-scoped owner if multi-manager applications are supported.

### 4.4 Drop geometry is computed as a side effect of painting

**Where:** [`dock_overlay.py:138-176`](../lace/dock_overlay.py)

```python
    def paintEvent(self, e):
        if not self._drop_preview_enabled:
            self._drop_area_rect = QRect()
            return
        ...
        self._drop_area_rect = r          # <-- the drop target is set here
```

`FloatingDockContainer._finalize_drag` depends on `overlay.drop_overlay_rect().isValid()`
([`floating_dock_container.py:228-246`](../lace/floating_dock_container.py)) — so where a window
lands is a function of whether a repaint happened to run. If the overlay is obscured, or the
compositor coalesces the paint, the drop uses a stale or empty rect.

Related: `show_overlay()` calls `self.repaint()` ([`:101`](../lace/dock_overlay.py)) — a
*synchronous* forced repaint — from inside a mouse-move path.

#### Fix

Extract the geometry calculation and call it from both places:

```python
    def _compute_drop_rect(self) -> QRect:
        """Pure geometry: the preview rect for the area under the cursor."""
        if not self._drop_preview_enabled:
            return QRect()
        r = self.rect()
        da = self.drop_area_under_cursor()
        factor = 3 if OverlayMode.container == self._mode else 2
        ...
        return r

    def drop_overlay_rect(self) -> QRect:
        return self._compute_drop_rect()      # never stale

    def paintEvent(self, e):
        r = self._compute_drop_rect()
        if r.isNull():
            return
        ...draw...
```

and change `self.repaint()` at line 101 to `self.update()`.

---

## 5. Fragility & cleanup

### 5.1 Two near-identical 1000+ line floating containers

**Where:** [`lace/floating_dock_container.py`](../lace/floating_dock_container.py) (1008 lines) and
[`lace/floating_dock_container_frameless.py`](../lace/floating_dock_container_frameless.py) (1481 lines)

Measured with a method-by-method diff:

```
shared methods: 46   (native-only 1, frameless-only 8)
byte-identical: 34
  __repr__, _activate_window, _apply_resize, _child_has_grab_mouse,
  _clear_synthetic_release_flag, _cursor_for_edge, _destroyed,
  _end_programmatic_drag, _finalize_drag, _handle_resize_event,
  _hit_test_edges, _is_movable, _is_our_widget, _set_state,
  _set_window_title, _test_config_flag, _update_chromeless_mask,
  _update_drop_overlays, closeEvent, deleteLater, dock_container,
  dock_widgets, has_top_level_dock_widget, hideEvent,
  init_floating_geometry, is_closable, move_floating,
  on_dock_area_current_changed, refresh_style, resizeEvent,
  restore_state, start_dragging, top_level_dock_widget, update_window_title
>80% similar: 1     (on_dock_areas_added_or_removed, 0.95)
substantially different: 11
  __init__ (0.60), event (0.42), eventFilter (0.68), moveEvent (0.63),
  start_floating (0.72), update_window_flags_from_config (0.63),
  _do_restore_geometry (0.29), _install_permanent_filter (0.16),
  _remove_permanent_filter (0.35), _end_swallowed_release (0.79),
  changeEvent (0.69)
```

~900 lines duplicated verbatim. Both classes are named `FloatingDockContainer`. Every drag, drop,
resize or lifecycle fix must land twice or the two window modes silently diverge — and only one of
them is exported from `lace/__init__.py`, so `isinstance(x, lace.FloatingDockContainer)` is wrong in
custom-titlebar mode.

#### Fix — extract a mixin

The 11 genuinely-different methods are the real subclass surface; the other 35 are shared behaviour.

```python
# lace/floating_behaviour.py  (new)

class FloatingContainerBehaviour:
    """Window-chrome-independent behaviour shared by both FloatingDockContainer
    implementations: drag lifecycle, drop-overlay tracking, chromeless resize,
    title bookkeeping and state persistence.

    Subclasses provide the window-chrome specifics: __init__, event(),
    eventFilter(), moveEvent(), changeEvent(), start_floating(),
    update_window_flags_from_config(), _do_restore_geometry() and the
    permanent-filter install/remove pair.
    """
    # the 34 byte-identical methods move here verbatim
```

```python
# lace/floating_dock_container.py
class FloatingDockContainer(QWidget, FloatingContainerBehaviour, DockStyled):
    ...only the native-chrome specifics...

# lace/floating_dock_container_frameless.py
class FramelessFloatingDockContainer(FramelessLaceWindow, FloatingContainerBehaviour, DockStyled):
    ...only the frameless specifics...
```

Rename the frameless class so the two are distinguishable, export both from `__init__.py`, and
export `util.is_floating_dock_container` as the supported isinstance check.

Do this **after** the correctness fixes in §1 — it is a large mechanical change and you want the new
round-trip test green before and after.

### 5.2 `_last_added_area_cache` retains deleted dock areas

**Where:** [`dock_container_widget.py:513-515`](../lace/dock_container_widget.py)

```python
        for _area, _widget in self._last_added_area_cache.items():
            if _widget is splitter:            # cache holds DockAreaWidget; splitter is a DockSplitter
                self._last_added_area_cache[_area] = None
```

The comparison is never true — the cache maps `DockWidgetArea -> DockAreaWidget`
([`:353`](../lace/dock_container_widget.py)) and `splitter` is a `DockSplitter`. Upstream ADS
compares against the removed *area*. So the cache keeps a strong reference to a removed (and shortly
deleted) dock area, and `last_added_dock_area_widget()` — public API, delegated from
`DockManager` — can hand back a deleted C++ object.

```python
-            if _widget is splitter:
+            if _widget is area:
```

Two lines below, `splitter` can be `None` if the area isn't inside a `DockSplitter`, and
`splitter.count()` at [`:517`](../lace/dock_container_widget.py) is unguarded — add an early return.

### 5.3 Stub methods that read as implemented

- **`DockOverlayCross.reset()` is `pass`** — [`dock_overlay.py:363-369`](../lace/dock_overlay.py),
  with a comment saying so. Consequence: `set_allowed_areas()` has **no visual effect**. Drop
  indicators for disallowed areas stay on screen and simply do nothing when hovered, because only
  `cursor_location()` ([`:325-336`](../lace/dock_overlay.py)) consults `allowed_areas`. Implement it:

  ```python
      def reset(self):
          allowed = self._dock_overlay.allowed_areas()
          for area, widget in self._drop_indicator_widgets.items():
              widget.setVisible(area in allowed)
  ```

- **`DockOverlay.drop_area_under_cursor()` has dead code** —
  [`:89-95`](../lace/dock_overlay.py): computes `pos`, discards it, guarded by a stringly-typed
  `'DockAreaWidget' in str(type(...))` check. Delete the block.
- **`update_title_bar_visibility()` unconditionally shows** —
  [`dock_area_widget.py:256-262`](../lace/dock_area_widget.py) is `setVisible(True)` with no
  condition. Either implement the hide case (upstream hides the bar when the area has no open
  widgets) or rename it to `ensure_title_bar_visible()` so the name stops promising logic.
- **Stale enum docs** — [`enums.py:82-135`](../lace/enums.py): `opaque_splitter_resize`,
  `opaque_undocking` and `custom_tab_icons` all say *"Currently not in proper use - requires
  implementation"*, but all three are used
  ([`dock_container_widget.py:696`](../lace/dock_container_widget.py),
  [`floating_dock_container.py:467`](../lace/floating_dock_container.py),
  [`dock_widget_tab.py:454`](../lace/dock_widget_tab.py)). Delete the disclaimers.

### 5.4 The `__init__.py` lazy loader should go

**Where:** [`lace/__init__.py:104-243`](../lace/__init__.py)

The file eagerly imports everything worth exporting at the top, and then adds a PEP 562
`__getattr__` that, on the first miss, imports **every** module in the package and registers **every**
public callable into a flat registry. Problems:

- It isn't lazy — a single missed attribute imports the whole package.
- It leaks internals into the public namespace (`lace.<any internal helper>` resolves).
- It swallows `ImportError` with a warning, so a genuinely broken module degrades silently.
- `_SKIP_MODULES` is hand-maintained and already lists `dock_colors`, a module that no longer exists.

Delete `_discover_models`, `__getattr__`, `__dir__` and `get_model_registry`, and let the explicit
imports at the top be the public API. Add `__all__` while you're there.

### 5.5 Defensive-coding density signals uncertain invariants

Counts across `lace/`:

| Pattern | Count |
|---|---|
| `except RuntimeError` | 46 |
| `except Exception` / bare `except` | 25 |
| `getattr(self, ...)` with a default | 55 |
| `hasattr(self, ...)` guards | 21 |
| cross-module private access (`._overlay._current_widgets`, `._buttons`, `._root_splitter`, `._dock_areas`, `._title_bar.`) | 132 |

These aren't bugs individually, but together they mean object lifetime and initialisation order are
not trusted anywhere. Two cheap, high-value cleanups:

1. **`getattr(self, "_bg_color", None)` in `paintEvent`s** exists because `refresh_style()` may not
   have run yet. Initialise every painted-chrome attribute in `__init__` (several classes already do
   this — `DockWidgetTab` at [`:72-80`](../lace/dock_widget_tab.py) is the model) and then read them
   directly. Affects `DockAreaTitleBar.paintEvent`, `SideBarTitleBar.paintEvent`,
   `SideBarContainer.paintEvent`.
2. **`getattr(manager, '_root', None) or manager`** appears 13 times. `root_container()` already
   exists as the public accessor — use it, and make `SidebarManager`/`FloatingDockContainer` take
   the container explicitly rather than reaching into `_root`.

### 5.6 Null-safety spots worth a guard

- [`util.py:39`](../lace/util.py) — `emit_top_level_event_for_widget` calls
  `widget.dock_area_widget().update_title_bar_visibility()` with no `None` check on the area.
- [`floating_dock_container.py:1000`](../lace/floating_dock_container.py) — `is_closable()`
  dereferences `self._dock_container`, which `_destroyed()` sets to `None`; `closeEvent` calls it.
- [`dock_container_widget.py:767,777`](../lace/dock_container_widget.py) — `_maximize_splitter`
  calls `sib.setSizes([0])` on splitters that may have more than one child; Qt only applies as many
  values as given, so only the first pane is zeroed.
- [`dock_widget_tab.py:505-509`](../lace/dock_widget_tab.py) — `_set_icon_internal` removes the icon
  label and then `layout.removeItem(layout.itemAt(0))`, relying on positional layout knowledge. Hold
  the spacer item in an attribute instead.

---

## 6. Test & CI gaps

**CI does not run the test suite.** [`.github/workflows/publish.yml`](../.github/workflows/publish.yml)
has a job named "Test (Python …)" whose only verification step is:

```yaml
      - name: Smoke import test
        run: python -c "import lace; print(f'Lace v{lace.__version__} OK')"
```

pytest is never installed or invoked. The 100 local tests pass but never gate a release.

**No test covers save/restore.** [`tests/test_layout_exceptions.py`](../tests/test_layout_exceptions.py)
asserts only the exception class hierarchy. [`dev_smoke/smoke_roundtrip.py`](../dev_smoke/smoke_roundtrip.py)
asserts `ok is True` and that the sidebar sub-dict is stable — **verified** to print
`ROUNDTRIP OK` on the currently-broken build.

### Fix

**(a) Run the tests in CI:**

```yaml
      - name: Install dependencies
        run: pip install . pyside6 pytest

      - name: Run test suite
        env:
          QT_QPA_PLATFORM: offscreen
        run: python -m pytest tests/ -q
```

**(b) Add a real round-trip test.** This is the single highest-value file in the plan — it would have
caught 1.1, 1.4, 2.1 and 2.2.

The file below was extracted from this document and run against the reviewed commit; it executes
cleanly and fails for the intended reasons, so it can be pasted in as-is:

```
FAILED test_docked_widgets_survive_roundtrip   - widgets orphaned (§1.1)
FAILED test_area_lock_survives_roundtrip       - AttributeError from §1.2
FAILED test_pinned_widget_stays_open           - AttributeError from §1.2
FAILED test_maximize_state_is_not_left_dangling- dangling _maximized_dock_area (§1.4)
PASSED test_active_tab_survives_roundtrip
4 failed, 1 passed
```

`test_active_tab_survives_roundtrip` already passes — keep it as a regression guard for Phase 2,
which changes the restore ordering.

```python
# tests/test_layout_roundtrip.py
import pytest
from PySide6.QtWidgets import QMainWindow, QLabel

from lace.dock_manager import DockManager
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea


@pytest.fixture
def manager(qapp):
    win = QMainWindow()
    dm = DockManager(win)
    win.resize(1000, 700)
    win.show()
    qapp.processEvents()
    yield dm
    win.close()


def _mk(name):
    dw = DockWidget(name)
    dw.set_widget(QLabel(name))
    return dw


def _snapshot(dm):
    """Placement facts a restore must reproduce."""
    return {
        name: (
            dw.is_closed(),
            dw.dock_area_widget() is not None,
            dw.dock_area_widget().index(dw) if dw.dock_area_widget() else -1,
            dw.is_pinned(),
        )
        for name, dw in dm.dock_widgets_map().items()
    }


def test_docked_widgets_survive_roundtrip(manager, qapp):
    area = manager.add_dock_widget(DockWidgetArea.left, _mk("Alpha"))
    manager.add_dock_widget(DockWidgetArea.center, _mk("Beta"), area)
    manager.add_dock_widget(DockWidgetArea.bottom, _mk("Gamma"))
    qapp.processEvents()

    before = _snapshot(manager)
    assert manager.restore_state(manager.save_state()) is True
    qapp.processEvents()

    assert _snapshot(manager) == before, "widgets were not restored to their dock areas"
    for dw in manager.dock_widgets_map().values():
        assert dw.dock_area_widget() is not None, f"{dw.objectName()} was orphaned"
        assert not dw.is_closed()


def test_active_tab_survives_roundtrip(manager, qapp):
    area = manager.add_dock_widget(DockWidgetArea.left, _mk("Alpha"))
    manager.add_dock_widget(DockWidgetArea.center, _mk("Beta"), area)
    area.set_current_index(1)
    qapp.processEvents()

    manager.restore_state(manager.save_state())
    qapp.processEvents()
    assert manager.root_container().dock_area(0).current_index() == 1


def test_area_lock_survives_roundtrip(manager, qapp):
    area = manager.add_dock_widget(DockWidgetArea.left, _mk("Alpha"))
    area.locked_name = "pinned-left"
    qapp.processEvents()

    manager.restore_state(manager.save_state())
    qapp.processEvents()
    assert manager.root_container().dock_area(0).locked_name == "pinned-left"


def test_pinned_widget_stays_open(manager, qapp):
    manager.add_dock_widget(DockWidgetArea.left, _mk("Alpha"))
    pinned = _mk("Pinned")
    manager.add_dock_widget(DockWidgetArea.right, pinned)
    manager.sidebar_manager.pin_widget(pinned, area=DockWidgetArea.left)
    qapp.processEvents()
    assert not pinned.is_closed()

    manager.restore_state(manager.save_state())
    qapp.processEvents()
    assert pinned.is_pinned()
    assert not pinned.is_closed(), "pinned widget was marked closed by restore"


def test_maximize_state_is_not_left_dangling(manager, qapp):
    manager.add_dock_widget(DockWidgetArea.left, _mk("Alpha"))
    area = manager.add_dock_widget(DockWidgetArea.bottom, _mk("Gamma"))
    area.toggle_maximize()
    qapp.processEvents()

    manager.restore_state(manager.save_state())
    qapp.processEvents()
    container = manager.root_container()
    maximized = container._maximized_dock_area
    assert maximized is None or maximized in [
        container.dock_area(i) for i in range(container.dock_area_count())
    ], "restore left _maximized_dock_area pointing at a destroyed area"
```

**(c) Add a theme-schema guard** so ghost tokens can't come back:

```python
# tests/test_theme_schema.py
from dataclasses import fields
from lace.dock_theme import ThemeSpec, build_theme
from lace.dock_style_manager import _SCHEMA_MAP


def test_every_generated_token_is_a_declared_field():
    """build_theme() must not emit tokens the schemas cannot store."""
    spec = ThemeSpec(
        base=[10, 10, 10, 255], accent=[200, 0, 0, 255], text=[240, 240, 240, 255],
        # exercise every optional knob so no token is missed
        title_border_bottom=3.0, title_border_width=1.0, content_margin=12,
        corner_radius=9, border_width=2.0, tab_radius=4, tab_margin=2,
        indicator_width=3, indicator_position="top",
    )
    ghosts = {}
    for category, tokens in build_theme(spec).items():
        declared = {f.name for f in fields(_SCHEMA_MAP[category])}
        extra = sorted(set(tokens) - declared)
        if extra:
            ghosts[category.name] = extra
    assert not ghosts, f"tokens emitted with no schema field: {ghosts}"


def test_non_colour_tokens_are_not_coerced_to_qcolor():
    from PySide6.QtGui import QColor
    from lace.dock_theme import DockStyleCategory
    from lace.dock_style_manager import get_dock_style_manager

    sm = get_dock_style_manager()
    for margin in (6, (8, 2), [6, 4, 6], [6, 4, 6, 4]):
        sm.apply_theme_dict(build_theme(ThemeSpec(
            base=[24, 24, 24, 255], accent=[0, 120, 212, 255],
            text=[204, 204, 204, 255], content_margin=margin)))
        stored = sm.get(DockStyleCategory.PANEL, "content_margin")
        assert not isinstance(stored, QColor), f"{margin!r} was coerced to a colour"
```

**(d) Tighten `smoke_roundtrip.py`** to assert placement, not just the boolean — or delete it in
favour of the pytest file above.

---

## 7. Improvement plan

Ordered so that each phase is independently shippable and the risky refactors land on top of a
green test suite.

### Phase 1 — Make persistence work (half a day)

| | Task | Files |
|---|---|---|
| ☑ | Fix the restore-marker mismatch (§1.1, minimal fix first) | `dock_container_state.py` |
| ☑ | Fix `ensure_active_dock_area` and move the call inside the `try` (§1.2) | `dock_manager.py` |
| ☑ | Reset maximize state in `restore_container_state` (§1.4) | `dock_container_state.py` |
| ☑ | Add `tests/test_layout_roundtrip.py` (§6b) | new |
| ☑ | Wire pytest into CI (§6a) | `.github/workflows/publish.yml` |

Ship this as **0.5.1**. `README.md:64` currently advertises a feature that does not work.

### Phase 2 — Close the state gaps (1–2 days)

| | Task | Files |
|---|---|---|
| ☑ | Serialize `locked_name` / `locked_to_area` (§2.1) | `dock_area_widget.py`, `dock_widget.py`, `dock_container_state.py` |
| ☑ | Reorder sidebar restore; fix pinned `closed` (§2.2) | `layout_serializer.py` |
| ☑ | Reduce `widget_states` to what is actually read (§2.3) | `layout_serializer.py` |
| ☑ | Collapse duplicated floating geometry (§2.4) | `layout_serializer.py`, `dock_container_state.py` |
| ☑ | Add `schema` version; fix `SYSTEM_TYPE` with back-compat (§2.5) | `layout_serializer.py` |
| ☑ | Pre-validate with `testing=True`; raise `RestoreFailureError` (§1.3) | `layout_serializer.py` |
| ☑ | Replace the dynamic-property marker with an explicit set (§1.1 structural) | `dock_container_state.py`, `layout_serializer.py` |
| ☑ | Document what is *not* persisted (features, icons, toolbars) | `docs/ARCHITECTURE.md` |

Extend the round-trip test with each item as you go.

### Phase 3 — Theming correctness (1 day)

| | Task | Files |
|---|---|---|
| ☑ | Declare all five ghost tokens as real fields (§3.1a) | `dock_theme.py` |
| ☑ | Warn on unknown tokens in both write paths (§3.1b) | `dock_style_manager.py` |
| ☑ | Fix the `border_bottom` / `border_color` key names (§3.2) | `sidebar_title_bar.py` |
| ☑ | Coerce colours by field, not by value shape (§3.4) | `dock_style_manager.py` |
| ☑ | Scope the DWM nudge to one window (§3.5) | `floating_dock_container.py` ×2 |
| ☑ | Retain the `QStyle` reference (§3.6) | `dock_theme_bridge.py` |
| ☑ | Add `tests/test_theme_schema.py` (§6c) | new |

### Phase 4 — Performance (1 day)

| | Task | Files |
|---|---|---|
| ☑ | Split `refresh_focus_tint()` out of `refresh_style()` (§4.1) | `dock_widget_tab.py`, `dock_area_widget.py` |
| ☑ | Guard expensive setters on value change (§4.1) | `dock_widget_tab.py`, `dock_area_title_bar.py`, `dock_chrome.py` |
| ☑ | Debounce `DockWidget.on_style_changed`; drop the bridge sweep (§4.2) | `dock_widget.py`, `dock_theme_bridge.py` |
| ☑ | Cache splitter handles (§4.3) | `dock_splitter.py`, `dock_container_widget.py` |
| ☑ | Make the drop rect a pure function; `repaint` → `update` (§4.4) | `dock_overlay.py` |

Re-run the probe afterwards; target < 0.5 ms per focus switch and < 10 ms per theme switch.

**Result** (same 4-area × 5-tab layout, offscreen, `0.5.25`):

| Probe | Before | After |
|---|---|---|
| Focus switch (restyle work alone) | 3.572 ms | **0.086 ms** |
| Focus switch (incl. repaint + `processEvents`) | 6.11 ms | 1.41 ms |
| Junction lookup per hover-move | 39.8 µs | 21.4 µs |
| Theme switch | 30.6 ms | 14.5 ms |
| `setStyleSheet` calls per 12 theme switches | 545 | 209 |
| `DockWidget.refresh_style` per theme switch | 3 × per widget | 1 × per widget |

The focus target is met with room to spare. The theme switch does not reach 10 ms: what is left is
icon SVG re-rendering (~14 per switch, which is real work for a new palette) and Qt's own layout and
paint inside `processEvents`, not redundant Python. Getting further means caching tinted pixmaps
across themes, which is a separate change.

### Phase 5 — Structural cleanup (2–3 days)

| | Task | Files |
|---|---|---|
| ☐ | Extract `FloatingContainerBehaviour`; rename the frameless class (§5.1) | new + both floating containers |
| ☑ | Fix `_last_added_area_cache`; guard the `None` splitter (§5.2) | `dock_container_widget.py` |
| ☐ | Implement `DockOverlayCross.reset()`; delete dead branches (§5.3) | `dock_overlay.py` |
| ☐ | Fix stale enum docstrings (§5.3) | `enums.py` |
| ☐ | Delete the `__init__.py` lazy loader; add `__all__` (§5.4) | `__init__.py` |
| ☐ | Initialise painted-chrome attrs in `__init__`; drop `getattr` defaults (§5.5) | several |
| ☐ | Replace `getattr(mgr, '_root', ...)` with `root_container()` (§5.5) | 13 sites |
| ☐ | Add the null guards in §5.6 | several |

---

## Appendix — reproducing the measurements

The probes used for this review:

| Probe | Establishes |
|---|---|
| `probe_restore.py` | 1.1 — widget placement before/after a round-trip |
| `probe2.py` | 1.1 fix confirmation + 1.2 `AttributeError` |
| `probe_state_completeness.py` | §2 — the preserved/lost table |
| `probe_pinned.py` | 2.2 — stack trace showing `pin_widget` running after `flag_as_unassigned` |
| `probe_theme.py` | 3.1 — ghost-token enumeration and `get_all()` visibility |
| `probe_perf.py` | §4 — `refresh_style()` call counts and timings |

Pattern for reproducing any of them:

```python
import os, sys
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, r"<repo root>")
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
# ... build a DockManager, exercise, assert ...
```

Run with the project venv:

```bash
QT_QPA_PLATFORM=offscreen python probe_restore.py
```
