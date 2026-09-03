# Lace 0.7 — Improvement Plan

**Baseline:** commit `2f16f8e` (v0.6.5), 443 tests green in 16.4 s
**Source:** decisions taken against [CODE_REVIEW_0.6.5.md](CODE_REVIEW_0.6.5.md); section numbers below refer to it
**Staging:** seven phases, one PR each, tests green at every boundary
**Compatibility:** pre-1.0 semantics — deprecated names are **removed outright** in 0.7 and recorded in the changelog
**Testing rule:** every phase adds at least one test that **fails on `2f16f8e` and passes after**

---

## Decisions taken

| Review § | Topic | Decision | Phase |
|---|---|---|---|
| §1.1 (a) | Programmatic split path | **Full refactor** — shared `_finish_area_insertion()` + `split_share()` | 1 |
| §2.1 | Stale `_handle_cache` after restore | **Centralise** into `_invalidate_layout_caches()` | 1 |
| §2.2 | Restored areas lack `destroyed` guard | Folded into the shared helper | 1 |
| §2.3 | `find_child(QWidget)` → root splitter | **Fix** — use `root_splitter()` | 2 |
| §2.4 | Drop policy overrides drag policy | **Fix** — shared `_allowed_areas_for()` | 2 |
| §4.2 | Triple `_drop_into_*` delegation | **Collapse** | 2 |
| §1.2 (b) | Centre drop into solo container | **Both causes + drop-order fix** | 3 |
| §1.6 (f) | Drop into a maximized area | **Restore first, then drop** — conditional on the drop reshaping the tree | 4 |
| §4.1 | `DockSignals` never emitted | **Finish the migration** | 5 |
| §1.5 (e) | Tab + sidebar icon focus tint | **Both, via shared resolver** | 6 |
| §2.5 / §2.6 | Icon-size token wiring | **Full rewire** — caller supplies size, one constant | 6 |
| §3.1 | Title-bar icon churn | **Memoise inside `dock_icon()`** | 6 |
| §3.3 | DPR missing from icon cache key | **Fix** | 6 |
| §3.2 | Per-area `focusChanged` fan-out | **Fix** — single manager-level handler | 7 |
| §4.3 | Dead `paint_panel` / `DockMenuMixin` | **Remove** | 7 |
| §4.4 | 11 unused imports | **Remove + ruff CI gate** | 7 |
| §5.1–§5.5 | Consistency pass | **Do** | 7 |
| §5.7 | Broad `except Exception` | **Partial** — narrow Qt-lifetime catches only | 7 |

### Explicitly deferred to 0.8

| Review § | Topic | Why deferred |
|---|---|---|
| §1.3 (c) | `pin` / `unpin` size mismatch | Asset work, batched with the geometry standard |
| §1.4 (d) | `close` 2 px stroke | Same |
| §4.5 | `close_others.svg` dedupe, Inkscape metadata | Same |
| §5.6 | 84 `hasattr()` guards | Wide blast radius; poor company for targeted fixes |

> **Note on the deferral.** Icon *geometry* moves to 0.8, but the icon *plumbing* (§2.5/§2.6) stays
> in 0.7 deliberately. Today `dock_icon(key, TAB)` renders at 14 px and the tab close button
> displays at `close_btn_icon_size` — they match only by coincidence. Fixing the SVGs first, on top
> of a pipeline that can silently render-then-rescale, would waste the work: a supersampled 14 px
> pixmap scaled up to 16 produces exactly the blurred, thickened stroke that (c) and (d) are about.
> **Phase 6 is prerequisite groundwork for the 0.8 icon pass**, not unrelated to it.

---

## Phase dependency graph

```
Phase 1  Layout insertion & cache      ── independent, start here
Phase 2  Drop path unification         ── independent
Phase 3  Centre drop (b)               ── needs Phase 2's _allowed_areas_for()
Phase 4  Maximize-aware drops          ── needs Phase 2; interacts with Phase 3
Phase 5  DockSignals migration         ── needs Phases 2-4 (same code)
Phase 6  Icon colour & size            ── independent
Phase 7  Cleanup & hygiene             ── last: touches files every other phase edits
```

Phases 1, 2 and 6 can proceed in parallel. **Phases 2 → 3 → 4 → 5 are strictly ordered** — all four
rewrite the same drop code, and doing them out of order means writing `_drop_into_container()`'s
centre branch twice. Phase 4 in particular must land *after* Phase 3, because its restore guard
keys off `drop_area != center` and Phase 3 is what makes a centre drop reachable in the first
place.

---

# Phase 1 — Layout insertion & cache invalidation

**Implements:** §1.1 (a), §2.1, §2.2
**Files:** `lace/dock_container_widget.py`, `lace/dock_container_state.py`, `lace/util.py`
**Risk:** Medium — touches the two hottest insertion paths. Well covered by the existing 443.

## Goal

There are currently two spellings of "insert a dock area" with different post-conditions, and three
places that reset layout caches with different coverage. Collapse each to one.

## Changes

### 1.1 — `split_share()` free function

Lift the share arithmetic out of `_insert_into_section_splitter()`
([dock_container_widget.py:165](../lace/dock_container_widget.py)) into `lace/util.py`:

```python
def split_share(target_size: int, handle_width: int, n_total: int) -> int:
    """Even split of `target_size` across `n_total` panes, minus handle gutters."""
    return (target_size - handle_width * (n_total - 1)) // n_total
```

Call it from both the drop path and the programmatic path, so "insert a sibling next to this area"
means the same thing regardless of origin.

### 1.2 — `_finish_area_insertion()` helper

One owner for everything a freshly created dock area is owed:

```python
def _finish_area_insertion(self, new_dock_area, area, splitter=None):
    """Every post-condition a newly created dock area requires.

    Called by _add_dock_area, _dock_widget_into_dock_area and _restore_dock_area
    so the three paths cannot drift apart again.
    """
    self._append_dock_areas(new_dock_area)
    new_dock_area.ensure_title_bar_visible()
    new_dock_area.destroyed.connect(self.remove_dock_area)
    self._last_added_area_cache[area] = new_dock_area
    if splitter is not None and not splitter.isVisible():
        splitter.show()
    self._emit_dock_areas_added()
```

Rewire all three call sites. The two ad-hoc `if not splitter.isVisible(): splitter.show()` lines
(`_add_dock_area` :410, `_drop_into_container` :145) collapse into the helper — they exist only
because `hide_empty_parent_splitters()` ([util.py:76](../lace/util.py)) sets
`WA_WState_ExplicitShowHide`, which suppresses Qt's `ChildPolished` auto-show. That workaround gets
exactly one home instead of two-and-a-gap. Add a comment saying so.

### 1.3 — `_invalidate_layout_caches()`

```python
def _invalidate_layout_caches(self):
    """Reset every cache derived from the splitter tree's shape."""
    self._visible_dock_area_count = -1
    self._handle_cache = None
    self._last_added_area_cache.clear()
```

Call from `_emit_dock_areas_added()`, `_emit_dock_areas_removed()`, and — the missing third choke
point — `restore_container_state()` ([dock_container_state.py:69-79](../lace/dock_container_state.py)).

This makes the `_all_handles()` docstring ("cleared from its two layout-change choke points") true
by construction. **Update that docstring** to name the invalidator rather than enumerate callers.

## Tests

`tests/test_splitter_handle_cache.py` already covers add/remove invalidation but **not restore** —
that is precisely the gap. Extend it:

| Test | Asserts | Fails on 2f16f8e |
|---|---|---|
| `test_restoring_a_layout_invalidates_the_cache` | `container._handle_cache is None` after `restore_state()` | ✅ (holds 4 stale handles against 8 live) |

New file `tests/test_area_insertion.py`:

| Test | Asserts | Fails on 2f16f8e |
|---|---|---|
| `test_a_targeted_split_divides_the_target_evenly` | left-split of a 900 px area → both panes within 1 px of `split_share()` | ✅ (currently 178 px) |
| `test_a_targeted_split_records_the_last_added_area` | `last_added_dock_area_widget(area)` is the new area | ✅ (currently `None`) |
| `test_every_insertion_path_wires_the_destroyed_guard` | all three paths connect `destroyed` | ✅ |
| `test_restored_areas_carry_the_destroyed_guard` | after `restore_state()`, areas are guarded | ✅ |

## Exit criteria

- 443 + 5 green
- `_last_added_area_cache`, `_handle_cache` and `_visible_dock_area_count` are written in exactly
  one place each
- `grep -c "isVisible(): splitter.show()"` → 1

---

# Phase 2 — Drop path unification

**Implements:** §2.3, §2.4, §4.2
**Files:** `lace/dock_container_widget.py`, `lace/floating_behaviour.py`, `lace/dock_manager.py`, `dev_smoke/interactive/generate_baselines.py`
**Risk:** Low-Medium — no behavioural change intended; this is the groundwork Phase 3 stands on.

## Goal

Make the drag preview and the drop outcome be computed by the same code, and stop locating the
floating root splitter by type-scan.

## Changes

### 2.1 — Use `root_splitter()`

[dock_container_widget.py:230-231](../lace/dock_container_widget.py):

```python
# before
floating_splitter = find_child(
    floating_widget.dock_container(), QWidget, '', Qt.FindDirectChildrenOnly)
# after
floating_splitter = floating_widget.dock_container().root_splitter()
```

`_drop_into_container()` twelve lines up already does this. The root container has **eight** direct
`QWidget` children (`DockSplitter`, `QMenu`, two `DockOverlay`s, two `DockOverlayCross`es,
`SideBarContainer`, `SideTabBar`) and today's code works only because construction order happens to
put the splitter first.

While here, narrow the parameter type hint on `_insert_into_section_splitter()` from `QWidget` to
`QSplitter` — every branch already assumes `.count()`, `.orientation()` and `.widget(0)`.

### 2.2 — One allowed-areas policy

Extract the branch at
[floating_behaviour.py:534-538](../lace/floating_behaviour.py) into a module-level function:

```python
def allowed_areas_for(container, dock_area) -> DockWidgetArea:
    """The single source of truth for what a drag may target.

    Used by the drag preview and by the drop itself, so what the user
    aimed at and what actually happens cannot disagree.
    """
```

Then **delete the unconditional re-arm** at
[dock_container_widget.py:80](../lace/dock_container_widget.py):

```python
drop_overlay.set_allowed_areas(DockWidgetArea.all_dock_areas)   # ← remove
```

By the time a drop happens the overlay is already configured by the drag. Removing this also
removes a latent hit-test bug: `set_allowed_areas()` calls `_cross.reset()` when the value changes,
which un-hides indicator widgets that `QGridLayout` gave no space to — and `cursor_location()` tests
`widget.geometry().contains(pos)` **in the same call**, before any layout pass has run.

### 2.3 — Collapse the delegation

Remove the two redundant private hops:

```
DockManager._drop_into_container       (dock_manager.py:685)     ← delete
  → DockContainerWidget._drop_into_*   (dock_container_widget.py:424)  ← delete
    → DropController._drop_into_*      (dock_container_widget.py:103)  ← keep
```

Same for `_drop_into_section`, `_drop_into_center_of_section`, `drop_floating_widget`. These are
underscore-private, so removal is not an API break. The only external consumer is
`dev_smoke/interactive/generate_baselines.py` — point it at `DropController` and note the change in
that script's header.

### 2.4 — De-alias `center` from `bottom`

[dock_container_widget.py:40-48](../lace/dock_container_widget.py) currently folds them together:

```python
if area in (DockWidgetArea.center, DockWidgetArea.bottom):
    return DockInsertParam(Qt.Vertical, True)
```

Every caller that can receive `center` special-cases it first — except `_drop_into_container()`,
which is exactly the bug Phase 3 fixes. Make `dock_area_insert_parameters()` **raise** on `center`
so a missing branch fails loudly at the first drop rather than silently splitting vertically.

## Tests

| File | Test | Fails on 2f16f8e |
|---|---|---|
| `test_overlay_allowed_areas.py` | `test_the_drop_uses_the_same_policy_as_the_preview` | ✅ |
| `test_public_api.py` | update `test_all_is_accurate_in_both_directions` for removed names | n/a |
| new `test_drop_path.py` | `test_the_floating_root_splitter_is_found_by_api_not_by_scan` — insert a decoy `QMenu` as first child, assert the splitter is still found | ✅ |
| new `test_drop_path.py` | `test_center_is_not_silently_treated_as_bottom` — `pytest.raises` on `dock_area_insert_parameters(center)` | ✅ |

## Exit criteria

- 448 + 4 green
- `grep -rn "find_child.*QWidget" lace/` returns nothing in the drop path
- One `set_allowed_areas()` policy call site per overlay

---

# Phase 3 — Centre drop into a single-area container

**Implements:** §1.2 (b), including the drop-order fix
**Depends on:** Phase 2
**Files:** `lace/floating_behaviour.py`, `lace/dock_container_widget.py`
**Risk:** Medium — this is a user-visible behavioural change.

## Goal

A floating dock widget dropped on the centre of a container tabs into it, including when that
container has exactly one dock area.

## Changes

### 3.1 — Allow centre on a solo area

[floating_behaviour.py:534-538](../lace/floating_behaviour.py), inside the `allowed_areas_for()`
function extracted in Phase 2:

```python
# before — no_area is 0, so DockOverlayCross.reset() hides *every*
# indicator, centre included, and cursor_location() can only return invalid.
DockWidgetArea.no_area if visible_dock_areas == 1 else DockWidgetArea.all_dock_areas

# after — a lone area still accepts tabs; the outer four stay suppressed
# because the container overlay owns them in that case.
DockWidgetArea.center if visible_dock_areas == 1 else DockWidgetArea.all_dock_areas
```

The `area == center and container_area != invalid` disambiguation immediately below (:540-546)
already handles the resulting overlap correctly — it hands the preview to the container overlay,
which is the right visual for "this will fill the area". No change needed there.

### 3.2 — Give `_drop_into_container()` a centre branch

When `area == center`:

- **single top-level dock area** → delegate to `_drop_into_center_of_section(floating_widget, that_area)`
- **several areas** → "centre of container" is genuinely ambiguous. Keep the current split as the
  documented fallback, **with a comment stating that this is a decision**, not the accidental
  `center, bottom` aliasing it inherits today. Phase 2's `raise` forces this branch to exist.

### 3.3 — Append, don't prepend

[dock_container_widget.py:249-253](../lace/dock_container_widget.py) inserts dropped widgets at
`i = 0, 1, 2…`, so they land *before* the existing tabs. Upstream ADS appends. Change to append.

### 3.4 — Guard `set_current_index(-1)`

If every incoming widget is closed, `new_current_index` stays `-1` and
`DockAreaWidget.set_current_index()` logs `Invalid index -1`. Skip the call when negative.

## Tests

New `tests/test_centre_drop.py`:

| Test | Asserts | Fails on 2f16f8e |
|---|---|---|
| `test_a_solo_area_offers_the_centre_indicator` | `allowed_areas_for(...) & center` is truthy at `visible_dock_area_count == 1` | ✅ |
| `test_dropping_on_centre_of_a_solo_container_tabs` | one dock area, two tabs — **not** two areas | ✅ |
| `test_dropped_tabs_are_appended_not_prepended` | pre-existing tab keeps index 0 | ✅ |
| `test_an_all_closed_drop_does_not_log_an_invalid_index` | `caplog` clean | ✅ |
| `test_multi_area_centre_drop_still_splits` | documents the deliberate fallback | ❌ (guards the decision) |

## Exit criteria

- 452 + 5 green
- Manual check in `dev_smoke/`: float a widget out of a one-area layout, drop it back on centre,
  get two tabs

---

# Phase 4 — Maximize-aware drops

**Implements:** §1.6 (f)
**Depends on:** Phase 2 (shared drop policy); must land after Phase 3
**Files:** `lace/dock_container_widget.py`
**Risk:** Medium — changes what a drop does, but only in a state that is currently incoherent.

## Goal

A drop that reshapes the splitter tree must restore the maximize state **before** mutating the
tree. A drop that only adds a tab may stay maximized.

## The defect

`_restore_maximized_area()` ([dock_container_widget.py:876](../lace/dock_container_widget.py)) has
three callers — `close_other_areas()` and the two guards inside `toggle_maximize_dock_area()`
itself. **No drop path calls it**, and `DropController` never reads `_maximized_dock_area` at all.
Dropping a floating widget onto a maximized area therefore leaves four things wrong at once:

| # | Symptom | Verified |
|---|---|---|
| 1 | `_maximized_dock_area` still points at an area now occupying half the container, so `is_area_maximized()` lies and the title bar keeps showing *Restore* | ✅ |
| 2 | Siblings hidden by maximize stay hidden — **two dock widgets vanish with no route back**. `setVisible(False)` is an explicit hide, so Qt's `ChildPolished` auto-show cannot rescue them | ✅ |
| 3 | `_pre_maximize_splitter_sizes` was captured against the old shape; the inner splitter now has 3 children against 2 saved entries. `setSizes()` applies a short list partially — the exact Qt behaviour the `collapse()` docstring at :765 already documents. Clicking Restore yields `[404, 404, 178]`, squeezing a 496 px pane to 178 px | ✅ |
| 4 | The dict is keyed by `id(splitter)`. Destroying a splitter while maximized leaves an entry keyed on a freed address that CPython can recycle | ✅ |

Symptom 2 is the user-facing damage and is worse than the missing relayout in the original report.

## Changes

### 4.1 — Restore before a tree-reshaping drop

`drop_floating_widget()` ([dock_container_widget.py:70](../lace/dock_container_widget.py)) already
resolves both `dock_area` and `drop_area` before dispatching, so the guard has one natural home:

```python
# A drop that reshapes the splitter tree invalidates the maximize state:
# _pre_maximize_splitter_sizes was captured against the old shape, and the
# hidden siblings would stay hidden with no route back. Restore first, then
# let the drop divide the target's real (un-maximized) geometry.
# A centre drop only adds a tab, leaves the tree alone, and may stay maximized.
if self._c._maximized_dock_area is not None and drop_area != DockWidgetArea.center:
    self._c._restore_maximized_area()
```

This mirrors `close_other_areas()` (:747-748), which already restores before mutating the layout.
The precedent exists in the codebase; the drop path never adopted it.

**Restore-then-drop is the correct order**, not drop-then-restore. Verified:

```
Splitter count=2 sizes=[346, 345]
  Splitter count=3 sizes=[246, 245, 495]
    Area ['D'] vis=True geom=246x346
    Area ['A'] vis=True geom=245x346
    Area ['B'] vis=True geom=495x346
  Area ['C'] vis=True geom=1000x345
all areas visible? True    maximize cleared? True
```

D and A split A's former half evenly while B keeps its own — exactly what "insert a sibling next to
this area" should mean. Dropping first would compute the split against A's maximized 1000 px
geometry, and the restore would then stomp it.

### 4.2 — Centre drops stay maximized

Verified that tabbing into the maximized area leaves the tree untouched:

```
splitter tree changed?     False  {root: 2, inner: 2} -> {root: 2, inner: 2}
A tabs now                 ['D', 'A']
A still fills container?   1000 of 1000
maximize state preserved?  True
```

This is desirable — the user maximized an area and dropped a widget *into* it. The `!= center`
condition in 4.1 is what preserves it, which is why this phase must follow Phase 3: before Phase 3,
`center` is not reliably reachable as a drop area.

### 4.3 — Stop keying pre-maximize sizes by `id()`

Replace the `{id(splitter): sizes}` dict with the sizes stored **on the splitter**, set by
`_collect_splitter_sizes()` (:811) and consumed by `_restore_maximized_area()` (:876). The value
then dies with the widget: no dangling keys, no inheritance by an unrelated splitter at a recycled
address, and no separate structure to keep in sync.

`_invalidate_layout_caches()` from Phase 1 does **not** cover this — pre-maximize sizes are
deliberately meant to survive layout changes, which is precisely why they need a lifetime tied to
the splitter rather than to a reset call.

### 4.4 — Validate before applying

`_restore_maximized_area()` should skip (or renormalise) when the saved list length no longer
matches `sp.count()`, instead of handing Qt a short list and getting a partial application.
Defence in depth: with 4.3 in place the mismatch should not arise, but the `collapse()` docstring
shows this Qt behaviour has already bitten once in this file.

### 4.5 — Un-strand siblings on maximized-area removal

`remove_dock_area()` (:501-507) clears `_maximized_dock_area` and `_pre_maximize_splitter_sizes`
when the removed area was the maximized one, but does not un-hide the siblings that maximize hid.
Route it through `_restore_maximized_area()` instead of clearing the fields by hand.

## Tests

New `tests/test_maximize_drop.py`:

| Test | Asserts | Fails on 2f16f8e |
|---|---|---|
| `test_a_split_drop_restores_the_maximized_area_first` | after the drop, `_maximized_dock_area is None` | ✅ |
| `test_no_area_is_stranded_by_a_drop` | every area with open widgets is visible after the drop | ✅ |
| `test_a_centre_drop_stays_maximized` | tabbing preserves maximize and the tree shape | ❌ (guards the nuance) |
| `test_restore_after_a_drop_keeps_saved_proportions` | no pane collapses to a leftover size | ✅ |
| `test_pre_maximize_sizes_do_not_outlive_their_splitter` | destroying a splitter while maximized leaves no dangling entry | ✅ |
| `test_removing_the_maximized_area_unhides_its_siblings` | §4.5 | ✅ |

## Exit criteria

- 457 + 6 green
- `grep -n "id(splitter)" lace/dock_container_widget.py` returns nothing
- Manual: maximize an area, drag a floating widget onto its left edge — the layout un-maximizes,
  every area reappears, and the dropped widget takes half the target's space

---

# Phase 5 — Finish the DockSignals migration

**Implements:** §4.1
**Depends on:** Phases 2, 3 and 4
**Files:** `lace/dock_signals.py`, `lace/dock_manager.py`, `lace/floating_dock_container.py`, `lace/__init__.py`
**Risk:** Medium-High — replaces a working direct-call path with an indirect one.

## Goal

`dock_signals.py` describes itself as the "Phase 5 global event bus" replacing "tight coupling
(where deep widgets call manager methods directly)". Today `DockManager.__init__`
([dock_manager.py:81-84](../lace/dock_manager.py)) constructs the bus and connects all three
signals to handlers (:438-446), and **nothing in the package ever emits them** — a full-package
grep returns only the three `connect()` lines. The direct path
(`FloatingDockContainer` → `container.drop_floating_widget()`) is what actually runs.

Make the bus real.

## Changes

1. **Emit** `request_overlay_show` / `request_overlay_hide` from the floating drag path instead of
   calling the manager's overlay methods directly.
2. **Emit** `floating_widget_dropped` at the end of the drag, and let
   `_handle_floating_widget_dropped` route into `DropController`.
3. Remove the now-dead direct calls.
4. Keep `DockSignals` exported — it becomes a genuine extension point rather than decoration.

## Why this is sequenced last of the drop-path work

All three of Phases 2, 3 and 4 rewrite `drop_floating_widget()` and its callers. Migrating to the
bus **before** the centre branch and the maximize guard exist means writing both twice, once on each
side of the indirection. Migrating after means the bus carries already-correct behaviour.

## Risk note

This is the one phase whose payoff is architectural rather than user-visible. If it proves to
destabilise the drag path under review, the fallback position is §4.1's alternative — **delete**
`DockSignals`, the three unreachable handlers and the public export. A half-wired bus reads as a
supported extension point that silently does nothing, which is worse than either end state. Either
outcome is acceptable for 0.7; leaving it as it stands is not.

## Tests

New `tests/test_dock_signals.py`:

| Test | Asserts |
|---|---|
| `test_a_drop_emits_floating_widget_dropped` | signal fires exactly once with the right payload |
| `test_overlay_show_and_hide_are_emitted_in_pairs` | no orphaned show |
| `test_a_subscriber_can_observe_a_drop_without_patching` | the extension point works |

## Exit criteria

- 462 + 3 green
- `grep -rn "\.emit()" lace/dock_signals.py` and the emit sites are non-empty
- No direct `container.drop_floating_widget()` calls remain in `floating_dock_container.py`

---

# Phase 6 — Icon colour and size correctness

**Implements:** §1.5 (e), §2.5, §2.6, §3.1, §3.3
**Files:** `lace/dock_widget_tab.py`, `lace/sidebar_tab.py`, `lace/dock_menu.py`, `lace/dock_icon_provider.py`, `lace/dock_theme.py`, `lace/dock_area_title_bar.py`
**Risk:** Low-Medium — visible on 10 of 19 themes, so easy to verify.

## Goal

One colour-resolution family instead of two, one icon-size source instead of four, and one QIcon
build per `(icon, size, theme generation)` instead of one per tab click.

## Changes

### 6.1 — Icons join the focus-colour family

The label goes through `_resolve_focus_colors()`
([dock_widget_tab.py:582](../lace/dock_widget_tab.py)), which honours `TAB.tab_dimming`. The icon
goes through `DockIconProvider._resolve_normal_color()`
([dock_icon_provider.py:173](../lace/dock_icon_provider.py)), which knows `active` and nothing about
focus. They disagree exactly when the area loses focus:

```
theme=dark  tab_dimming=True
  focused=True   label=#ffffff  icon=#ffffff  match
  focused=False  label=#d4d8e0  icon=#ffffff  *** MISMATCH ***
```

**10 of 19 built-in themes enable `tab_dimming`**: `dark`, `light`, `midnight`, `neutral`,
`cyberpunk_neon`, `cyberpunk_edge`, `slate_amber`, `neon_dusk`, `violet_haze`, `midnight_haze`.

Fix:

1. Extend `_resolve_focus_colors()` to also return the icon tint — it already computes the dimmed
   value the icon wants.
2. Pass that colour into `update_icon()` → `provider.get()` via the existing `token=` / explicit-colour
   override. This mechanism already exists and is already used by the tab close button
   (`token="close_btn_color"`); the tab icon is the same shape of problem.
3. Add `self._is_area_focused()` to `icon_key`
   ([dock_widget_tab.py:483](../lace/dock_widget_tab.py)) — without this the memo short-circuits
   the fix.
4. Call `update_icon()` from `refresh_focus_tint()`
   ([dock_widget_tab.py:656](../lace/dock_widget_tab.py)). With the memo key correct, this is free
   on the 9 themes without `tab_dimming`.

### 6.2 — Sidebar icons re-tint too

`VerticalTabButton.refresh_style()` ([sidebar_tab.py:343](../lace/sidebar_tab.py)) re-reads every
SIDEBAR token — backgrounds, text, borders, badges, typography — and **not the icon**. `self._icon`
is captured once in `__init__` (:64) and painted verbatim (:237), so the text switches on
`isChecked()` and follows the theme while the icon does neither.

Route it through the provider with the resolved state colour, and re-tint in `refresh_style()`.
While in that file, replace the hardcoded `icon_size = 16` (:223) and `gap = 8` (:224) with theme
tokens — every other metric in that method already comes from the theme.

### 6.3 — Fix the two `elif` fallback chains

[dock_widget_tab.py:508-521](../lace/dock_widget_tab.py): if `_default_icon_name` is set but the
provider returns a null icon (missing SVG), the `elif not self._default_icon.isNull()` and
`elif … windowIcon()` branches are unreachable, so the tab ends up with **no** icon rather than
falling back. Same shape at :492-505. Convert both to `if icon_to_use.isNull():` checks.

Also fix the memo bypass at :486 — the guard requires a *name*, so a tab whose icon comes from
`windowIcon()` re-runs `_set_icon_internal()` (including `icon.pixmap()` and `setPixmap()`) on
**every** tab switch.

### 6.4 — Icon-size token rewire

Two mis-wirings:

- `sm.get(DockStyleCategory.TAB, "tab_icon_size", 16)`
  ([dock_widget_tab.py:476](../lace/dock_widget_tab.py)) — **no schema declares `tab_icon_size`**.
  `DockStyleManager.get()` returns the default when the field is absent, so tab icon size is not
  themeable, and a theme that tries gets `Theme sets unknown token tab_icon_size … ignored` while
  the code reads as though it works.
- `sm.get(category, "button_icon_size", 14)` ([dock_menu.py:83](../lace/dock_menu.py)) —
  `button_icon_size` lives on `_ActionButtonFields`, which `DockTitleBarStyleSchema` and
  `DockSidePanelStyleSchema` inherit but **`DockTabStyleSchema` does not**. So `dock_icon(key, TAB)`
  always renders at the literal `14`, matching `close_btn_icon_size`'s default of 14 **by
  coincidence**.

Fix:

1. Declare `tab_icon_size: int = 16` on `DockTabStyleSchema`, next to `close_btn_icon_size`.
2. Change `dock_icon()` to **take the display size from the caller** instead of guessing a category
   token. Every caller already knows it: `close_btn_icon_size` for tab close, `button_icon_size` for
   title-bar buttons, `tab_icon_size` for tab icons.
3. Collapse the four scattered fallback literals — `14` at `dock_menu.py:83` and
   `dock_area_title_bar.py:321`, `16` at `dock_theme.py:182`, `dock_area_title_bar.py:501`,
   `sidebar_title_bar.py:342`, `frameless_titlebar.py:177`, `dock_chrome.py:328` — to one module
   constant.

No shipped theme currently overrides these, so **this phase should be visually a no-op**. That is
the point: it removes the render-then-rescale trap before the 0.8 icon pass walks into it.

### 6.5 — Memoise `dock_icon()`

`dock_icon()` ([dock_menu.py:70](../lace/dock_menu.py)) allocates a fresh `QIcon`, calls
`provider.get()` twice and `addPixmap()` four times on **every** invocation.
`DockAreaTitleBar.update_button_states()` ([dock_area_title_bar.py:306](../lace/dock_area_title_bar.py))
calls it for all five buttons unconditionally, on every tab click:

| Operation | wall time | `dock_icon()` | `provider.get()` |
|---|---|---|---|
| 1 theme switch | 18.5 ms | 18 | 44 |
| 20 tab switches | 56.3 ms | 100 | 200 |

That is ~2.8 ms per tab click, for five icons of which only three can even change (`undock`↔`dock`,
`maximize`↔`restore`, `pin`↔`unpin`); `tabs_menu` and `close` are constant for the theme's lifetime.

Memoise inside `dock_icon()` on `(key, category, token, size, sm.generation)`. The provider already
invalidates on theme change via `on_style_changed()`, so the outer memo only needs the generation
counter. Every call site benefits at once.

> Sequenced with §5.4 deliberately — the token rewire changes `dock_icon()`'s signature, so the
> memo key must be designed against the new one.

### 6.6 — DPR in the icon cache key

`_icon_cache` is keyed `(name, color, active, disabled, size)`
([dock_icon_provider.py:226](../lace/dock_icon_provider.py)) with no device pixel ratio, while
`_render_svg()` bakes `QApplication.instance().devicePixelRatio()` into the pixmap (:129).
`QGuiApplication::devicePixelRatio()` is documented as returning the **highest** ratio across all
screens, so icons over-render on the low-DPI monitor and a window moved between monitors of
different DPR keeps its stale pixmap.

Add DPR to the key. Drop `active` and `disabled` — both are already folded into `color`.

## Tests

New `tests/test_tab_icon_state.py`:

| Test | Asserts | Fails on 2f16f8e |
|---|---|---|
| `test_icon_and_label_agree_across_every_theme` | parametrised over all 19 themes × focused/unfocused | ✅ (10 themes) |
| `test_losing_focus_retints_the_icon` | `update_icon()` runs from `refresh_focus_tint()` | ✅ |
| `test_a_missing_svg_falls_back_to_the_window_icon` | fallback chain reachable | ✅ |
| `test_sidebar_icons_follow_the_theme` | re-tint on `refresh_style()` | ✅ |
| `test_tab_icon_size_is_themeable` | a theme setting `tab_icon_size` takes effect, no warning logged | ✅ |
| `test_a_tab_switch_builds_no_new_icons` | `dock_icon()` call count is 0 on the second switch | ✅ (currently 5) |

## Exit criteria

- 465 + 6 green
- Icon and label colour agree on all 19 themes in both focus states
- 20 tab switches produce **0** `dock_icon()` calls after the first
- One module constant for icon size; `grep -c '"button_icon_size", 1[46]'` → 0

---

# Phase 7 — Cleanup and hygiene

**Implements:** §3.2, §4.3, §4.4, §5.1–§5.5, §5.7 (partial)
**Files:** wide but shallow
**Risk:** Low — mechanical, but sequenced last because it touches files every other phase edits.

## Changes

### 7.1 — Focus fan-out (§3.2)

`DockAreaWidget.__init__` ([dock_area_widget.py:65-68](../lace/dock_area_widget.py)) connects
`QApplication.focusChanged` once per dock area and never disconnects. Qt auto-disconnects on
destruction so this is not a leak — it is a linear-in-areas cost on a very hot signal, each slot
doing an `isAncestorOf()` walk. `DockManager.__init__` adds one more (:118-121).

Replace with a single manager-level handler resolving the area via
`find_parent(DockAreaWidget, new_widget)`.

### 7.2 — Dead code removal (§4.3)

Pre-1.0 semantics: **remove outright**, changelog entry for each.

| Item | Location | Action |
|---|---|---|
| `paint_panel` import | [dock_chrome.py:17](../lace/dock_chrome.py) | Delete the import; production uses `paint_panel_bg` + `paint_panel_border` separately. Keep the function — `tests/test_dock_paint.py:159` covers it |
| `DockMenuMixin` | [dock_context_menu.py:20](../lace/dock_context_menu.py) | Empty class, docstring says "Deprecated legacy mixin". Remove, plus its exports at `__init__.py:58, 166` |
| `dock_context_menu.py` | whole module | Pure re-export shim over `dock_menu.py`. Remove |
| stale docstring | [sidebar_tab_bar.py:420](../lace/sidebar_tab_bar.py) | Mentions `DockMenuMixin` for a method that doesn't use it |

`tests/test_public_api.py::test_all_is_accurate_in_both_directions` and `test_star_import_matches_all`
will need updating — that is the test doing its job.

### 7.3 — Unused imports + ruff gate (§4.4)

| File | Line | Name |
|---|---|---|
| `dock_chrome.py` | 17 | `paint_panel` |
| `dock_manager.py` | 15 | `Any`, `Union` |
| `dock_menu.py` | 14, 20 | `List`, `WidgetState` |
| `dock_overlay.py` | 15, 16 | `QPointF`, `QRectF`, `QLineF`, `QPolygonF` |
| `dock_widget_tab.py` | 19 | `QPushButton` |
| `sidebar_tab.py` | 11 | `Union` |
| `sidebar_title_bar.py` | 13 | `QToolButton` |

Then add a lint job to `.github/workflows/publish.yml` — the repo has no linting today, and the
existing workflow already runs tests on every branch push, so it is the natural home:

```yaml
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pipx install ruff
      - run: ruff check --select F401,F811 lace/
```

Start deliberately narrow (`F401` unused imports, `F811` redefinitions). A broad ruleset on an
existing codebase produces a wall of findings nobody acts on; these two are the ones that actually
re-accumulated.

### 7.4 — Consistency pass (§5.1–§5.5)

| Item | Location | Action |
|---|---|---|
| Vestigial `setIconSize(QSize(16, 16))` | [dock_area_title_bar.py:168](../lace/dock_area_title_bar.py) | Set on the close button only, out of five, and overwritten by `refresh_style()` moments later. Delete |
| Dead params on `style_title_bar_buttons()` | [dock_chrome.py:338](../lace/dock_chrome.py) | `color` and `disabled` documented as "accepted for call-site compatibility but unused". Remove from the signature and both call sites |

### 7.5 — Narrow Qt-lifetime exception handling (§5.7, partial)

34 `except Exception` sites. Several are correct (`_notify_subscribers`, file I/O in
`layout_serializer`) and stay. The ones guarding **Qt object lifetimes** should narrow to
`RuntimeError` — the pattern already used correctly in `dock_splitter.py` and `dock_area_widget.py`.

Highest-value single change: [dock_style_manager.py:261](../lace/dock_style_manager.py) logs and
continues when a subscriber's `refresh_style()` raises. That is how a broken `refresh_style()`
becomes an invisible styling failure instead of a traceback. Narrow it to `RuntimeError` (the
deleted-C++-object case it legitimately guards) and let genuine bugs propagate.

**The 84 `hasattr()` guards (§5.6) are explicitly out of scope** — deferred to 0.8.

## Tests

| Test | Asserts |
|---|---|
| `test_public_api.py` (updated) | `__all__` accurate after removals |
| new `test_focus_dispatch.py` | N areas ⇒ 1 slot invocation per focus change, not N |
| new `test_style_refresh_surfaces_bugs.py` | a subscriber raising `ValueError` propagates rather than being swallowed |

## Exit criteria

- 471 + 3 green on all 12 matrix cells (3 OS × 4 Python)
- `ruff check --select F401,F811 lace/` clean
- Lint job green in CI

---

# Release checklist

- [ ] Phases 1–6 merged, 443 → ~474 tests green across the full matrix
- [ ] `__version__` bumped in [lace/__init__.py:17](../lace/__init__.py) **and** `pyproject.toml:3`
- [ ] `CHANGELOG` records the removals: `DockMenuMixin`, `dock_context_menu`, the private
      `_drop_into_*` delegation, and `style_title_bar_buttons()`'s two dead parameters
- [ ] `dev_smoke/interactive/generate_baselines.py` regenerated and re-pointed at `DropController`
- [ ] Manual smoke on Windows: centre-drop tabbing, targeted splits sizing evenly, tab icons dimming
      with their labels, junction co-drag working **after a perspective restore**, and a split drop
      onto a maximized area un-maximizing instead of stranding its siblings

---

# Deferred to 0.8

## Icon geometry standard (§1.3, §1.4, §4.5)

Measured through Lace's own `DockIconProvider._render_svg()` at 320 px:

| icon | declared | measured | ink % | content box (24-unit) |
|---|---|---|---|---|
| close.svg | **2** | **1.95** | 12.2 | **14.03 × 14.03** |
| close_others.svg | **2** | **1.95** | 12.2 | **14.03 × 14.03** |
| close_tab.svg | 1.5 | 1.50 | 22.4 | 19.43 × 19.43 |
| dock.svg | 1.5 | 1.50 | 20.7 | 18.45 × 18.45 |
| float.svg | 1.5 | 1.50 | 20.7 | 18.45 × 18.45 |
| maximize.svg | 1.5 | **1.43** | 15.8 | 17.47 × 17.47 |
| **pin.svg** | 1.5 | 1.57 | 12.4 | **16.95 × 16.95** |
| pin_all.svg | 1.5 | 1.50 | 18.5 | 17.40 × 19.43 |
| restore.svg | 1.5 | **1.43** | 18.5 | 17.62 × 17.70 |
| tab_list.svg | 1.5 | 1.50 | 19.4 | 17.47 × 17.47 |
| tabs_menu.svg | 1.5 | **1.35** | 9.0 | 17.47 × 9.53 |
| **unpin.svg** | 1.5 | 1.57 | 17.6 | **19.43 × 19.43** |

Work items: pick one content-box extent and one stroke width for all 12; redraw `close`,
`close_others`, `pin`, `maximize`, `restore`; dedupe `close_others.svg` (currently **byte-identical**
to `close.svg`, md5 `65e7f573a3a842714ca798ddba12d5bc`) or give "Close Others" its own glyph; strip
~2.5 KB of Inkscape round-trip metadata from `maximize.svg` and `restore.svg`; write
`lace/resources/lace_icons/README.md` recording the invariants (24×24 viewBox,
`stroke="currentColor"`, `stroke-width="1.5"`, round caps and joins, content box N→24−N).

A five-line README would have caught both (c) and (d) at authoring time.

**Note:** `pin` is *not* thicker than its siblings — its 1.57 measurement is shared with `unpin` and
comes from round caps on acute diagonal joins, not a wrong `stroke-width`. Its real defect is being
13 % smaller than `unpin`, so the glyph visibly grows when you pin. Its load path is byte-for-byte
identical to every other title-bar icon and needs no change.

## `hasattr()` audit (§5.6)

84 calls across 18 modules. Several are load-bearing where they shouldn't be — e.g.
`dock_container_widget.py:723` guards `hasattr(self, '_dock_manager')` and
`hasattr(self._dock_manager, 'sidebar_manager')`, both of which are plain attributes set in
`__init__`. These hide ordering bugs rather than preventing them.
