# Lace — Code Review 0.6.5

**Reviewed:** `lace/` at commit `2f16f8e` (v0.6.5, branch `main`, clean tree)
**Environment:** PySide6 6.11.1, Python 3.13.14 (`developenv`), `QT_QPA_PLATFORM=offscreen`
**Baseline:** `pytest tests -q` → **443 passed** in 16.4 s. Every proposal below is written against
that green baseline; nothing in this document has been applied to the code.

**Method:** full read of the 40 modules in `lace/`, plus six runtime probe scripts that drive a real
`DockManager` (splits, drops, tab switches, theme switches, save/restore round-trips) and one
offscreen SVG rasteriser that measures the shipped icon set through Lace's own
`DockIconProvider._render_svg`. Findings marked **[verified]** were reproduced by running code.

Line numbers refer to the reviewed commit.

---

## 0. Summary

### Your reported issues

| # | Your report | Verdict | Root cause |
|---|-------------|---------|------------|
| **a** | Split created synchronously, no forced relayout; refresh missing when an area is created/tabbed | **Confirmed, but not as a repaint bug** — Qt's auto-show covers the visual side. The real defect is that `_dock_widget_into_dock_area()` skips **four** of the five things every sibling insertion path does **[verified]** | [§1.1](#11-a--the-programmatic-split-path-is-missing-four-of-its-five-post-insert-steps) |
| **b** | Floating dock widget cannot drop into centre to get tabs | **Confirmed, two independent causes** **[verified]** | [§1.2](#12-b--a-floating-window-cannot-be-dropped-into-the-centre-of-a-single-area-container) |
| **c** | Pin icon line thickness wrong / loaded differently | **Partly confirmed** — the *load path* is identical to its siblings; the *geometry* is not. `pin` is 13 % smaller than `unpin`, so the glyph jumps on toggle **[verified]** | [§1.3](#13-c--the-pin-icon-is-not-loaded-differently--but-pin-and-unpin-are-not-the-same-size) |
| **d** | Close icon thickness might be wrong at 2 px | **Confirmed** — `close.svg` / `close_others.svg` are the only two icons at `stroke-width="2"`; everything else is `1.5` **[verified]** | [§1.4](#14-d--close-icon-is-the-only-2-px-stroke-in-the-set) |
| **e** | Small bug with tab icons inactive/active/focused | **Confirmed** — on an unfocused area the active tab's *label* dims but its *icon* does not. Affects 10 of 19 built-in themes **[verified]** | [§1.5](#15-e--tab-icons-do-not-follow-the-focus-dimming-that-tab-labels-do) |
| **f** | Dropping into a maximized area creates a splitter instead of restoring first | **Confirmed** — no drop path restores the maximize state; the container is left internally contradictory and two areas become invisible with no route back **[verified]** | [§1.6](#16-f--a-drop-into-a-maximized-area-leaves-the-container-in-a-contradictory-state) |

### Additional findings

| # | Severity | Area | Finding | Effort |
|---|----------|------|---------|--------|
| 2.1 | **High** | Layout state | `restore_container_state()` never clears `_handle_cache` → splitter junction detection sees a stale handle set after every layout restore **[verified]** | 1 line |
| 2.2 | Medium | Layout state | Restored dock areas never get the `destroyed → remove_dock_area` safety net that `_add_dock_area()` installs | 1 line |
| 2.3 | Medium | Drop path | `_drop_into_section()` finds the floating root splitter with `find_child(QWidget, …)` instead of `root_splitter()` **[verified: 7 non-splitter direct children exist on the root container]** | 1 line |
| 2.4 | Medium | Drop path | Drop-time policy overrides drag-time policy: `drop_floating_widget()` re-arms the overlay with `all_dock_areas` regardless of what the drag showed | ~5 lines |
| 2.5 | Medium | Theming | `TAB.tab_icon_size` does not exist on any schema — tab icons are hard-locked at 16 px and a theme setting it is silently warned away **[verified]** | ~3 lines |
| 2.6 | Medium | Theming | `dock_icon(key, TAB)` reads `button_icon_size`, which `DockTabStyleSchema` does not declare → always the literal `14` **[verified]** | ~5 lines |
| 2.7 | Medium | Sidebar | `VerticalTabButton` re-reads every SIDEBAR token on theme change **except its icon**, which is captured once at construction and never re-tinted or state-switched | ~15 lines |
| 3.1 | Medium | Performance | Every tab switch rebuilds all five title-bar `QIcon`s: 20 switches → 100 `dock_icon()` / 200 `provider.get()` calls, ≈2.8 ms each **[verified]** | ~10 lines |
| 3.2 | Low | Performance | Each `DockAreaWidget` connects to the application-wide `focusChanged`; N areas ⇒ N slots per focus change | ~10 lines |
| 3.3 | Low | Performance | Icon cache key omits device pixel ratio; `QGuiApplication.devicePixelRatio()` returns the *highest* screen's DPR | ~5 lines |
| 4.1 | Low | Dead code | `DockSignals` bus is constructed and connected but **never emitted** — three unreachable handlers **[verified]** | ~15 lines |
| 4.2 | Low | Dead code | Three-layer private delegation for `_drop_into_*` (`DockManager` → `DockContainerWidget` → `DropController`) | ~15 lines |
| 4.3 | Low | Dead code | `paint_panel()` is referenced only by its own test; `DockMenuMixin` is an empty deprecated class in the public API | ~10 lines |
| 4.4 | Low | Cleanup | 11 unused imports across 8 modules **[verified]** | trivial |
| 4.5 | Low | Assets | `close_others.svg` is byte-identical to `close.svg`; `maximize.svg` / `restore.svg` carry ~1.3 KB of Inkscape editor metadata each | trivial |

---

# Part 1 — The six reported issues

## 1.1 (a) — The programmatic split path is missing four of its five post-insert steps

### What I found

The premise needs one correction before the finding lands. **Qt does re-lay-out and re-show after
`QSplitter.insertWidget()`** — `QSplitter::childEvent()` shows a newly parented child on
`ChildPolished` unless that child was *explicitly* hidden. I verified this: a
`add_dock_widget(left, w, target_area)` that goes down the new-splitter branch produces a correct,
visible tree with correct geometry, with no `show()` anywhere in the path:

```
Splitter V  sizes=[296, 295]
  Splitter H  sizes=[178, 715]        ← created by _dock_widget_into_dock_area
    Area vis=True  178x296  ['C']
    Area vis=True  715x296  ['A']
  Area vis=True  900x295  ['B']
A titlebar visible: True   C titlebar: True
```

So there is no missing repaint. What *is* missing is everything else. Compare the two sibling
insertion paths in [dock_container_widget.py](../lace/dock_container_widget.py):

| Post-insert step | `_add_dock_area()` (:387) | `_dock_widget_into_dock_area()` (:361) |
|---|---|---|
| `new_dock_area.ensure_title_bar_visible()` | ✅ | ❌ |
| `destroyed.connect(self.remove_dock_area)` | ✅ | ❌ |
| `_last_added_area_cache[area] = new_dock_area` | ✅ (via `_dock_widget_into_container`) | ❌ |
| `if not splitter.isVisible(): splitter.show()` | ✅ | ❌ |
| `_emit_dock_areas_added()` | ✅ | ✅ |

**[verified]** by introspecting the two method bodies and by behaviour:

```
new area connected to remove_dock_area on destroy?  False
new area ensure_title_bar_visible() called?         False
_last_added_area_cache updated?                     False
splitter.show() / relayout forced?                  False
_add_dock_area does:  ['show()', 'ensure_title_bar_visible', 'destroyed.connect']

last_added_dock_area_widget(bottom) -> None      ← after a targeted split
```

The user-visible consequences:

1. **`last_added_dock_area_widget()` lies.** After `add_dock_widget(area, w, target)` the cache is
   never populated, so the documented "give me the area I last created here" accessor returns
   `None`. Applications that use it to stack a second widget into the same new area get a second
   *area* instead.
2. **No destroyed-signal safety net.** Areas created by splitting are removed from `_dock_areas`
   only by the explicit `remove_dock_widget()` path. `_add_dock_area()` installs
   `destroyed → remove_dock_area` precisely because that explicit path can be bypassed (C++-side
   deletion, parent teardown). The split path has no such guard, so a stale `DockAreaWidget` can
   survive in `_dock_areas` and later raise `RuntimeError` in `opened_dock_areas()` /
   `visible_dock_area_count()`.
3. **No size redistribution.** This is the one with a visible symptom, and it is the real
   counterpart of "a refresh is missing". The *drop* path deliberately splits the target's space:

   `_insert_into_section_splitter()` (:165) computes
   `share = (target_area_size - handleWidth * (total - 1)) / total` and calls `setSizes()`.

   The *programmatic* path does not call `setSizes()` at all **[verified]**, so Qt falls back to
   size-hint distribution. In the probe above, splitting a 900 px area left gave the new area
   **178 px**, not 450 px — an arbitrary width driven by whatever the content's size hint happens
   to be. To an application author this reads exactly as "the layout did not refresh".

### Proposal

Fold the shared tail into one helper so the two paths cannot drift again:

```python
def _finish_area_insertion(self, new_dock_area, area, splitter=None):
    """Everything both insertion paths owe a freshly created dock area."""
    self._append_dock_areas(new_dock_area)
    new_dock_area.ensure_title_bar_visible()
    new_dock_area.destroyed.connect(self.remove_dock_area)
    self._last_added_area_cache[area] = new_dock_area
    if splitter is not None and not splitter.isVisible():
        splitter.show()
    self._emit_dock_areas_added()
```

and have `_dock_widget_into_dock_area()` additionally mirror the drop path's size split. The
cleanest version is to lift the share arithmetic out of `_insert_into_section_splitter()` into a
free function — `split_share(target_size, handle_width, n_new)` — and call it from both, so
"insert a sibling next to this area" means the same thing whether it came from a drag or from
`add_dock_widget()`.

> **Note on `hide_empty_parent_splitters()`** ([util.py:76](../lace/util.py)): it calls
> `splitter.hide()`, which sets `WA_WState_ExplicitShowHide`. That is the flag that suppresses
> Qt's `ChildPolished` auto-show. The two ad-hoc `if not splitter.isVisible(): splitter.show()`
> lines in `_add_dock_area()` (:410) and `_drop_into_container()` (:145) exist because of it. If
> you centralise as above, that workaround gets exactly one home instead of two-and-a-gap.

---

## 1.2 (b) — A floating window cannot be dropped into the centre of a single-area container

Confirmed, and there are **two independent causes**. Fixing either one alone leaves the feature
half-broken, so both need addressing.

### Cause 1 — the centre indicator is switched off in exactly the case you want it

[floating_behaviour.py:534-538](../lace/floating_behaviour.py):

```python
dock_area_overlay.set_allowed_areas(
    DockWidgetArea.no_area          # ← when visible_dock_areas == 1
    if visible_dock_areas == 1
    else DockWidgetArea.all_dock_areas)
```

`no_area` is `0`. `DockOverlayCross.reset()` ([dock_overlay.py:379](../lace/dock_overlay.py)) then
hides **every** indicator widget, and `cursor_location()` (:341) requires `widget.isVisible()`, so
it can only return `invalid`. **[verified]:**

```
visible_dock_area_count=1 -> dock_area_overlay allowed = DockWidgetArea.no_area  (center reachable: False)
visible_dock_area_count=2 -> dock_area_overlay allowed = DockWidgetArea.all_dock_areas  (center reachable: True)
```

So with one dock area — the ordinary "one central widget" layout — the dock-area cross shows
nothing at all, centre included. With two or more areas, centre tabbing works fine. That matches
your symptom precisely.

The intent behind `no_area` was presumably "a lone area has no meaningful left/right/top/bottom,
the container overlay owns those". That reasoning is right for the four outer areas and wrong for
centre: centre is the *only* target that means something for a solo area.

### Cause 2 — a container-level centre drop splits instead of tabbing

Because the dock-area cross is dark, the only reachable centre indicator is the **container**
overlay's (`_area_grid_position` gives container mode a `center` cell at `QPoint(2, 2)`, and the
container overlay *is* given `all_dock_areas` for a solo area, :523-527). Dropping there lands in
`_drop_into_container()`.

`_drop_into_container()` has no centre special case, so it goes through
`dock_area_insert_parameters()` ([dock_container_widget.py:40](../lace/dock_container_widget.py)),
where centre is folded in with bottom:

```python
if area in (DockWidgetArea.center, DockWidgetArea.bottom):
    return DockInsertParam(Qt.Vertical, True)
```

**[verified]:**

```
dock_area_insert_parameters(center) = DockInsertParam(orientation=Vertical, append=True)
... same as bottom?  True
_drop_into_container has a 'center' special case?  False
_drop_into_section  has a 'center' special case?  True
```

`_drop_into_section()` (:217) *does* branch to `_drop_into_center_of_section()`. `_drop_into_container()`
never got the equivalent. So even when the user does hit a centre indicator, the result is a
vertical split, not a tab.

### Proposal

Two changes, both small:

1. **Allow centre on a solo area.** Replace the `no_area` branch with `DockWidgetArea.center`:

   ```python
   dock_area_overlay.set_allowed_areas(
       DockWidgetArea.center            # a lone area still accepts tabs
       if visible_dock_areas == 1
       else DockWidgetArea.all_dock_areas)
   ```

   The outer four stay suppressed (the container overlay owns them for a solo area), and the
   `area == center and container_area != invalid` disambiguation immediately below (:540-546)
   already handles the overlap correctly — it hands the preview to the container overlay, which is
   the right visual for "this will fill the area".

2. **Give `_drop_into_container()` a centre case.** When `area == center` and the container has a
   single top-level dock area, delegate to `_drop_into_center_of_section(floating_widget,
   that_area)`. When it has several, "centre of container" is genuinely ambiguous and falling
   through to the current split is a defensible default — but that decision should be written down
   in the code rather than inherited by accident from the `center, bottom` tuple.

### Related — worth fixing in the same pass

- **`dock_area_insert_parameters()` should not answer for centre at all.** Every caller that can
  receive `center` special-cases it first (`_drop_into_section`, `_dock_widget_into_dock_area`).
  The one that doesn't (`_drop_into_container`) is the bug. Making centre return an explicit
  sentinel — or raising — would have surfaced this at the first drop instead of silently aliasing
  to bottom.
- **`_drop_into_center_of_section()` inserts at the front.** :249-253 does
  `target_area.insert_dock_widget(i, dock_widget, False)` for `i = 0, 1, 2…`, so dropped tabs land
  *before* the existing ones. Upstream ADS appends. Minor, but it is a visible ordering surprise.
- **`set_current_index(-1)` warning.** If every incoming widget is closed, `new_current_index`
  stays `-1` and `DockAreaWidget.set_current_index()` logs `Invalid index -1`. Guard the call.

---

## 1.3 (c) — The pin icon is *not* loaded differently — but `pin` and `unpin` are not the same size

### Load path: identical to its siblings

I traced it end to end. `pin` is created and updated exactly like `close`, `float`, `maximize` and
`tabs_menu`:

- construction — `dock_icon("pin", DockStyleCategory.TITLE_BAR)`
  ([dock_area_title_bar.py:124](../lace/dock_area_title_bar.py))
- refresh — `dock_icon(pin_key, DockStyleCategory.TITLE_BAR)` where `pin_key = "unpin" if is_pinned
  else "pin"` (:387)
- sizing — the same `icon_size` as every other button (:388), and the same
  `style_title_bar_buttons(...)` sweep (:494)

There is no special case for pin anywhere in `DockIconProvider`, `dock_icon()` or
`style_title_bar_buttons()`. **The load path is not the problem.**

### Geometry: the problem is real, and it is in the SVGs

I rasterised all 12 icons through Lace's own `DockIconProvider._render_svg()` (4× supersample,
smooth downscale) at 320 px and measured effective stroke width as `2 × p90(distance-to-background)`
over the ink, plus the ink bounding box in viewBox units:

| icon | declared | **measured** | ink % | content box (24-unit grid) |
|---|---|---|---|---|
| close.svg | **2** | **1.95** | 12.2 | **14.03 × 14.03** |
| close_others.svg | **2** | **1.95** | 12.2 | **14.03 × 14.03** |
| close_tab.svg | 1.5 | 1.50 | 22.4 | 19.43 × 19.43 |
| dock.svg | 1.5 | 1.50 | 20.7 | 18.45 × 18.45 |
| float.svg | 1.5 | 1.50 | 20.7 | 18.45 × 18.45 |
| maximize.svg | 1.5 | 1.43 | 15.8 | 17.47 × 17.47 |
| **pin.svg** | 1.5 | **1.57** | 12.4 | **16.95 × 16.95** |
| pin_all.svg | 1.5 | 1.50 | 18.5 | 17.40 × 19.43 |
| restore.svg | 1.5 | 1.43 | 18.5 | 17.62 × 17.70 |
| tab_list.svg | 1.5 | 1.50 | 19.4 | 17.47 × 17.47 |
| tabs_menu.svg | 1.5 | 1.35 | 9.0 | 17.47 × 9.53 |
| **unpin.svg** | 1.5 | **1.57** | 17.6 | **19.43 × 19.43** |

Reading this:

- **`pin` is not thicker.** Its 1.57 measurement is shared with `unpin` and comes from the round
  caps and the acute joins in the Tabler pin outline, not from a wrong `stroke-width`. Both files
  declare `1.5` and both render `1.5`.
- **`pin` is 13 % smaller than `unpin`.** 16.95 vs 19.43 units of content box, and 12.4 % vs 17.6 %
  ink. `unpin` adds the corner-to-corner slash `M3 3l18 18`, which pushes it out to the full
  3→21 Tabler extent, while `pin` only reaches 4.0→20.0. **Clicking pin makes the glyph visibly
  grow.** That is a real toggle-pair inconsistency, and I suspect it is what you were seeing —
  "thicker" and "bigger at the same stroke width" look very similar at 16 px.
- **`pin` is also the lightest non-`close` glyph in the set** (12.4 % ink, against 18–22 % for the
  window/box icons). Next to `float` at 20.7 % it reads thin even though its stroke is identical —
  a diagonal 1.5 px stroke simply lays down less ink than an axis-aligned one at the same width.

### Proposal

1. **Normalise the toggle pair.** Either scale `pin.svg`'s path to the 3→21 extent that `unpin`
   uses, or trim `unpin`'s slash to `M4.5 4.5l15 15` so both sit in the same box. The former keeps
   both consistent with `close_tab`; the latter keeps both consistent with `maximize`/`tab_list`.
   Pick one target extent for the whole set and state it in a short `lace/resources/lace_icons/README.md`.
2. **If pin still reads thin after that**, the honest fix is optical compensation — bump `pin.svg`
   (and only pin) to `stroke-width="1.6"`. Do it explicitly with a comment, not by accident.
3. Do **not** change the load path. It is correct and uniform.

---

## 1.4 (d) — Close icon is the only 2 px stroke in the set

Confirmed outright. `close.svg` and `close_others.svg` are the **only** two files in
`lace/resources/lace_icons/` that declare `stroke-width="2"`. The other ten all declare `1.5`, and
all ten measure 1.35–1.57 while close measures **1.95** — a 30 % heavier stroke sitting next to
pin, maximize and float in the same title bar.

It is also the **smallest** glyph in the set: 14.03 units of content box against 17–19 for its
neighbours. Tabler's plain `x` is drawn 6→18; every other icon Lace uses is drawn 3→21 or 4→20.
So the close button reads as a small, heavy X while its four siblings read as large, light
outlines. Those two errors partly mask each other at 16 px, which is probably why it survived.

**Proposal:** set `stroke-width="1.5"` on both files, and scale the two paths from the 6→18 box out
to whichever extent you standardise on in §1.3 (`M18 6l-12 12` → `M19.5 4.5l-15 15` for the 4.5→19.5
box, or `M21 3l-18 18` for the full Tabler extent). Then re-check the tab close button
(`close_tab.svg`, already 1.5 and already 3→21) against it — that one is correct today and should
stay the reference.

> `close_others.svg` is **byte-identical** to `close.svg` (`md5 65e7f573…` for both). Either give
> the context-menu entry its own glyph or delete the file and point the menu at `close`. Right now
> a fix has to be applied twice. See §4.5.

---

## 1.5 (e) — Tab icons do not follow the focus dimming that tab labels do

### The bug

`DockWidgetTab` resolves its **label** colour through `_resolve_focus_colors()`
([dock_widget_tab.py:582](../lace/dock_widget_tab.py)), which honours `TAB.tab_dimming`: when the
dock area is unfocused, the active tab's text is blended halfway back toward `text_normal`.

Its **icon** is resolved through a completely separate path —
`DockIconProvider._resolve_normal_color(TAB, styles, active)`
([dock_icon_provider.py:173](../lace/dock_icon_provider.py)) — which knows about `active` and
nothing about focus. It returns raw `text_active` / `text_normal`.

The two therefore disagree exactly when the area loses focus. **[verified]** on two themes:

```
--- theme=dark  tab_dimming=True ---
  A focused=True   active=True  label=#ffffff  icon=#ffffff  match
  A focused=False  active=True  label=#d4d8e0  icon=#ffffff  *** MISMATCH ***
   text_active=#ffffff  text_normal=#aab2c2

--- theme=cyberpunk_neon  tab_dimming=True ---
  A focused=True   active=True  label=#ffffff  icon=#ffffff  match
  A focused=False  active=True  label=#e0e0ff  icon=#ffffff  *** MISMATCH ***
```

**10 of the 19 built-in themes enable `tab_dimming`**: `dark`, `light`, `midnight`, `neutral`,
`cyberpunk_neon`, `cyberpunk_edge`, `slate_amber`, `neon_dusk`, `violet_haze`, `midnight_haze`.
On all ten, an unfocused active tab shows a dimmed title next to a full-brightness icon.

### Why it never self-corrects

Two reinforcing reasons:

1. **`refresh_focus_tint()` does not call `update_icon()`** ([dock_widget_tab.py:656](../lace/dock_widget_tab.py)).
   That is the cheap path taken on every focus change, and it deliberately excludes icon work —
   correct as long as icons don't depend on focus, which is precisely the assumption that is
   wrong. **[verified]:** `"update_icon" in getsource(refresh_focus_tint)` → `False`.
2. **The icon memo key omits focus** ([dock_widget_tab.py:483](../lace/dock_widget_tab.py)):

   ```python
   icon_key = (self._custom_icon_name, self._default_icon_name, use_custom,
               self.is_active_tab(), self.isEnabled(), icon_size, sm.generation)
   ```

   So even if `refresh_focus_tint()` did call `update_icon()`, the memo would short-circuit it.

### Proposal

Give the icon the same colour resolution the label already has, rather than a parallel one:

1. Extend `_resolve_focus_colors()` to also return the icon tint (it already computes the dimmed
   `text_color`; the icon wants the same value).
2. Add a `token=` / explicit-colour override to the `update_icon()` → `provider.get()` call so the
   tab can pass that resolved colour instead of letting the provider re-derive it. `dock_icon()`
   and `DockIconProvider.get()` already support `token=` for exactly this reason — the tab close
   button uses it (`token="close_btn_color"`). The active/inactive tab icon is the same shape of
   problem.
3. Add `self._is_area_focused()` to `icon_key`, and call `update_icon()` from
   `refresh_focus_tint()`. With the memo key correct, that call is free whenever focus did not
   actually change the tint (i.e. on the 9 themes without `tab_dimming`).

### Two smaller issues in the same area

- **`elif` chain swallows the QIcon fallback** ([dock_widget_tab.py:508-521](../lace/dock_widget_tab.py)).
  If `_default_icon_name` is set but the provider returns a null icon (missing SVG), the `elif not
  self._default_icon.isNull()` and `elif … windowIcon()` branches are unreachable, so the tab ends
  up with no icon rather than falling back. Same shape in the `use_custom` block at :492-505.
  Convert both to `if icon_to_use.isNull():` checks.
- **The memo is bypassed for QIcon-valued icons.** The guard at :486 requires a *name*:

  ```python
  if (self._custom_icon_name or self._default_icon_name) and icon_key == self._applied_icon_key:
      return
  ```

  A tab whose icon comes from `windowIcon()` therefore re-runs `_set_icon_internal()` — including
  `icon.pixmap(...)` and `setPixmap()` — on every single tab switch. Feeds directly into §3.1.

### Sidebar counterpart — same family, worse

`VerticalTabButton.refresh_style()` ([sidebar_tab.py:343](../lace/sidebar_tab.py)) re-reads every
SIDEBAR token — `tab_bg_active`, `tab_text_active`, `tab_text_normal`, borders, badge colours,
typography — and **not the icon**. `self._icon` is captured once in `__init__` (:64) from
`dock_widget.icon()` ([sidebar_tab_bar.py:325](../lace/sidebar_tab_bar.py)) and painted verbatim at
:237.

So a sidebar tab's text switches between `tab_text_active` and `tab_text_normal` on
`isChecked()` and follows theme changes, while its icon does neither. Same fix shape: route the
icon through the provider with the resolved state colour, and re-tint in `refresh_style()`.

While you are in that file: `paintEvent` hardcodes `icon_size = 16` (:223) and `gap = 8` (:224)
in a method where every other metric comes from the theme.

---

---

## 1.6 (f) — A drop into a maximized area leaves the container in a contradictory state

### What I found

Confirmed, and the consequences run deeper than the missing splitter restore.

`_restore_maximized_area()` ([dock_container_widget.py:876](../lace/dock_container_widget.py)) has
exactly **three** callers: `close_other_areas()` (:748) and the two guard clauses inside
`toggle_maximize_dock_area()` itself (:834, :839). **No drop path calls it.** `DropController`
never consults `_maximized_dock_area` at all.

So a drop onto a maximized area mutates the splitter tree underneath a maximize state that still
believes it owns the whole container. **[verified]** — three areas A/B/C, A maximized, then a
floating D dropped on A's left edge:

```
--- A maximized ---
  _maximized_dock_area = A
  _pre_maximize sizes  = {root: [346, 345], inner: [497, 496]}
    Splitter root  count=2 sizes=[698, 0]
      Splitter inner count=2 sizes=[1000, 0]
        Area ['A'] vis=True  geom=1000x698     <- fills the container, correct
        Area ['B'] vis=False geom=0x698
      Area ['C'] vis=False geom=1000x0

--- after dropping D into maximized A (left) ---
  _maximized_dock_area = A                     <- still set
  _pre_maximize sizes  = {root: [346, 345], inner: [497, 496]}   <- never updated
    Splitter root  count=2 sizes=[698, 0]
      Splitter inner count=3 sizes=[497, 496, 0]
        Area ['D'] vis=True  geom=497x698
        Area ['A'] vis=True  geom=496x698      <- "maximized" but occupies half
        Area ['B'] vis=False geom=0x698
      Area ['C'] vis=False geom=1000x0
```

Four distinct defects fall out of this:

**1. The maximize invariant is broken.** `_maximized_dock_area is A` while A occupies 496 of 1000
px. Every consumer of that state is now wrong: `is_area_maximized(A)` returns `True`, so the title
bar keeps showing the *Restore* icon and tooltip for an area that is plainly not maximized.

**2. B and C are stranded.** They were hidden by `setVisible(False)` during maximize
([dock_container_widget.py:865-867](../lace/dock_container_widget.py)) and nothing in the drop path
shows them again. The user sees a two-pane layout (D | A) and has **silently lost two dock
widgets** — with no visual affordance suggesting they still exist. This is the most damaging part
of the bug, and it is worse than the missing relayout you described. Note that `setVisible(False)`
is an *explicit* hide, so it sets `WA_WState_ExplicitShowHide` and Qt's `ChildPolished` auto-show
(the mechanism that rescues the ordinary insertion path, see §1.1) will **not** bring them back.

**3. `_pre_maximize_splitter_sizes` goes stale in a way that corrupts the eventual restore.**
The dict is captured at maximize time and never updated. After the drop, the inner splitter has
three children but its saved entry still has two. **[verified]:**

```
*** LENGTH MISMATCH splitter <inner>: saved 2 entries, now 3 children
```

`_restore_maximized_area()` then calls `sp.setSizes([497, 496])` on a 3-pane splitter. Qt applies as
many values as it is given and leaves the rest — **precisely the failure mode the `collapse()`
docstring at :765 already documents** ("setSizes([0]) only reached the *first* pane"). The result is
a garbage layout: clicking Restore afterwards yields `[404, 404, 178]`, squeezing B from its
original 496 px down to 178 px.

**4. The dict is keyed by `id()`, which dangles.** `_collect_splitter_sizes()` (:811) uses
`self._pre_maximize_splitter_sizes[id(splitter)] = ...`. If a splitter is destroyed while a
maximize is active, the entry survives as a key referencing a freed object, and CPython readily
recycles addresses. **[verified]** — removing a hidden sibling's area while A is maximized:

```
saved ids: [2845206993344, 2845206999488]
live ids after removing B's area: [2845206993344]
saved ids now DEAD: [2845206999488]
```

A future `QSplitter` allocated at that address would silently inherit the dead one's sizes. Latent
today, but it is a genuine use-after-free-by-proxy.

### An important nuance: not every drop should restore

A **centre** drop (tabbing into the maximized area) does not reshape the splitter tree at all, and
maximize survives it perfectly well. **[verified]:**

```
=== drop on CENTER (tab into maximized area) ===
  splitter tree changed?      False  {root: 2, inner: 2} -> {root: 2, inner: 2}
  A tabs now                  ['D', 'A']
  A still fills container?    1000 of 1000
  maximize state preserved?   True
```

That is correct and desirable behaviour — the user maximized an area and dropped a widget *into*
it; staying maximized is the least surprising outcome. So the fix must be conditional on whether
the drop reshapes the tree, not a blanket restore on every drop.

### The proposed order works

Your suggested sequence — restore the splitter first, then let the dropped widget take its own
place — is the correct one, and it produces a coherent result. **[verified]:**

```
=== restore, then drop ===
    Splitter count=2 sizes=[346, 345]
      Splitter count=3 sizes=[246, 245, 495]
        Area ['D'] vis=True geom=246x346
        Area ['A'] vis=True geom=245x346
        Area ['B'] vis=True geom=495x346
      Area ['C'] vis=True geom=1000x345
  all areas visible? True
  maximize cleared?  True
```

D and A split A's former half evenly (246/245) while B keeps its own half (495) — which is exactly
what "insert a sibling next to this area" should mean. The ordering matters: dropping *first* would
compute the split against A's maximized 1000 px geometry, and the subsequent restore would then
stomp it.

### Proposal

Add a single guard at the top of `DropController.drop_floating_widget()`
([dock_container_widget.py:70](../lace/dock_container_widget.py)), where `dock_area` and `drop_area`
are both already resolved before dispatch:

```python
# A drop that reshapes the splitter tree invalidates the maximize state:
# _pre_maximize_splitter_sizes was captured against the old shape, and the
# hidden siblings would stay hidden with no route back. Restore first, then
# let the drop divide the target's real (un-maximized) geometry.
# A centre drop only adds a tab, leaves the tree alone, and may stay maximized.
if self._c._maximized_dock_area is not None and drop_area != DockWidgetArea.center:
    self._c._restore_maximized_area()
```

This mirrors `close_other_areas()` (:747-748), which already restores before mutating the layout —
the precedent is in the codebase; the drop path simply never adopted it.

Two supporting fixes belong with it:

1. **Stop keying by `id()`.** Store the pre-maximize sizes *on the splitter* (e.g. a
   `_pre_maximize_sizes` attribute set by `_collect_splitter_sizes()` and consumed by
   `_restore_maximized_area()`). The value then dies with the widget, cannot dangle, and cannot be
   inherited by an unrelated splitter at a recycled address.
2. **Validate before applying.** `_restore_maximized_area()` should skip (or renormalise) when
   `len(saved) != sp.count()`, rather than handing Qt a short list and getting a partial
   application. This is defence in depth: with fix (1) in place the mismatch should not arise, but
   the existing `collapse()` docstring shows this Qt behaviour has already bitten once.

Optionally also restore when the maximized area is *removed* while hidden siblings exist — the
`remove_dock_area` path at :501-507 clears the maximize state but does not un-hide the siblings it
stranded.


# Part 2 — Additional correctness findings

## 2.1 `_handle_cache` is never invalidated by a layout restore  **[High]**

`DockSplitterHandle._all_handles()` ([dock_splitter.py:74](../lace/dock_splitter.py)) caches the
container's handle list because it runs on every hover-move. Its docstring says the cache "is
cleared from its two layout-change choke points (`_emit_dock_areas_added`/`_removed`), which is
where handles come and go."

**A layout restore is a third choke point, and it clears nothing.**
`restore_container_state()` ([dock_container_state.py:69-79](../lace/dock_container_state.py))
resets `_visible_dock_area_count`, `_dock_areas`, `_last_added_area_cache`, `_maximized_dock_area`,
`_pre_maximize_splitter_sizes` and `_top_level_dock_area` — but not `_handle_cache`. It then
replaces the entire splitter tree at :106-109.

**[verified]:**

```
cache primed with 4 handles      live handles in tree: 4
after restore_state():
  _handle_cache is None (invalidated)?  False
  cached handles: 4, live handles now in tree: 8
  -> junction detection sees 4 of 8 handles
  after a later add_dock_widget, cache is None? True
```

The consequence is silent: `_find_intersecting_handles()` catches `RuntimeError` per stale handle
and skips it, so multi-junction resize simply stops finding its perpendicular partners until the
next add/remove happens to invalidate the cache. No error, no log line — the feature just quietly
doesn't work after loading a perspective.

**Proposal:** add `c._handle_cache = None` to the reset block at
[dock_container_state.py:69-79](../lace/dock_container_state.py). One line. Better still, replace
the three scattered reset sites with a single `DockContainerWidget._invalidate_layout_caches()`
that owns `_visible_dock_area_count`, `_handle_cache` and `_last_added_area_cache` together — the
docstring on `_all_handles()` will then be true by construction rather than by vigilance.

## 2.2 Restored dock areas get no `destroyed` safety net  **[Medium]**

`_restore_dock_area()` ([dock_container_state.py:211](../lace/dock_container_state.py)) registers
new areas with `c._append_dock_areas(dock_area)`, which connects only `view_toggled`.
`_add_dock_area()` additionally connects `destroyed → remove_dock_area` (:421).

So after a layout restore, **no** dock area in the container has that guard — the same asymmetry as
§1.1 but affecting the whole tree at once. The `_finish_area_insertion()` helper proposed in §1.1
should be the single place that wires a new area up, and `_restore_dock_area()` should use it too.

## 2.3 `_drop_into_section()` locates the floating root splitter by type-scan  **[Medium]**

[dock_container_widget.py:230-231](../lace/dock_container_widget.py):

```python
floating_splitter = find_child(
    floating_widget.dock_container(), QWidget, '', Qt.FindDirectChildrenOnly)
```

This asks for *the first direct `QWidget` child of the container* and assumes it is the root
splitter. `_drop_into_container()` twelve lines up does the correct thing —
`floating_dock_container.root_splitter()`.

It happens to work because `create_root_splitter()` runs first in `__init__`. But a
`DockContainerWidget` parents plenty of other widgets. **[verified]** on the root container:

```
root container direct QWidget children (creation order):
    DockSplitter        ← what find_child returns today
    QMenu
    DockOverlay
    DockOverlayCross
    DockOverlay
    DockOverlayCross
    SideBarContainer (autoHideOverlay)
    SideTabBar (sideTabBar)
```

Any future change to construction order — or a subclass that creates a child before calling
`super().__init__()` — silently reparents a `QMenu` or an overlay into the drop target.

**Proposal:** `floating_splitter = floating_widget.dock_container().root_splitter()`. One line, and
it makes the two drop paths agree. Also narrow the `QWidget` type hint on the parameter of
`_insert_into_section_splitter()` to `QSplitter`, which is what every branch of it assumes
(`.count()`, `.orientation()`, `.widget(0)`).

## 2.4 Drop-time policy silently overrides drag-time policy  **[Medium]**

During the drag, `_update_drop_overlays()` decides what is allowed based on
`visible_dock_area_count`. At the moment of the drop,
[dock_container_widget.py:79-81](../lace/dock_container_widget.py) throws that away:

```python
drop_overlay = self._c._dock_manager.dock_area_overlay()
drop_overlay.set_allowed_areas(DockWidgetArea.all_dock_areas)   # ← unconditional
drop_area = drop_overlay.show_overlay(dock_area)
```

Two problems:

1. **WYSIWYG is broken.** The overlay the user aimed at and the overlay that decides the outcome
   are configured by different rules. Today the mismatch is masked by cause 2 of §1.2; fixing
   §1.2 without fixing this would expose it.
2. **The re-arm reads stale geometry.** `set_allowed_areas()` only acts when the value *changed*
   ([dock_overlay.py:75](../lace/dock_overlay.py)), and when it does it calls `_cross.reset()`,
   which flips indicator widgets from hidden to visible. `QGridLayout` gives hidden widgets no
   space, so the newly shown indicators keep their stale geometry until the next layout pass —
   and `cursor_location()` tests `widget.geometry().contains(pos)` **immediately**, in the same
   call. A drop that re-arms the overlay is therefore hit-testing against the pre-reset layout.

**Proposal:** have the drag path and the drop path call one shared
`_allowed_areas_for(container, dock_area)` policy function, and delete the re-arm at :80 entirely —
by the time a drop happens the overlay is already configured correctly by the drag.

## 2.5 `TAB.tab_icon_size` does not exist  **[Medium]**

[dock_widget_tab.py:476](../lace/dock_widget_tab.py):

```python
icon_size = sm.get(DockStyleCategory.TAB, "tab_icon_size", 16)
```

`DockStyleManager.get()` returns the default when `hasattr(schema, key)` is false
([dock_style_manager.py:192](../lace/dock_style_manager.py)), and `DockTabStyleSchema` declares no
such field. **[verified]:**

```
tab_icon_size   TAB=False  TITLE_BAR=False  SIDEPANEL=False
update_icon() renders at 16 (hardcoded: token does not exist)
```

So tab icon size is **not themeable**, and a theme that tries gets
`Theme sets unknown token tab_icon_size on DockTabStyleSchema — ignored.` in the log while the code
reads like it is supported.

**Proposal:** declare `tab_icon_size: int = 16` on `DockTabStyleSchema` (next to
`close_btn_icon_size`), which makes the existing call site correct with no other change.

## 2.6 `dock_icon(key, TAB)` reads a token TAB doesn't have  **[Medium]**

[dock_menu.py:83](../lace/dock_menu.py):

```python
icon_dim = sm.get(category, "button_icon_size", 14)
```

`button_icon_size` lives on `_ActionButtonFields`, which `DockTitleBarStyleSchema` and
`DockSidePanelStyleSchema` inherit — but **`DockTabStyleSchema` does not**. **[verified]:**

```
button_icon_size   TAB=False  TITLE_BAR=True  SIDEPANEL=True
dock_icon(TAB)      renders at 14
tab close displayed at        14      ← close_btn_icon_size, default 14
dock_icon(TITLE_BAR) renders  16
```

The tab close button is rendered at 14 px by `dock_icon()` and displayed at `close_btn_icon_size`
(also 14). **Today they match by coincidence**, and no shipped theme overrides either **[verified:
`themes overriding icon-size tokens: none`]** — so this is latent, not a live visual defect. But
any theme that sets `close_btn_icon_size` to 16 gets a 14 px pixmap scaled up to 16, which is
exactly the blurred-and-thickened stroke symptom you were chasing in §1.3/§1.4.

There is also a **default mismatch**: `dock_icon()` falls back to `14`, `_ActionButtonFields`
declares `16`, and `style_title_bar_buttons()` /
[dock_area_title_bar.py:501](../lace/dock_area_title_bar.py) fall back to `16`, while
[dock_area_title_bar.py:321](../lace/dock_area_title_bar.py) falls back to `14`. Four fallbacks,
two values, for the same concept.

**Proposal:** have `dock_icon()` take the display size from the caller rather than guessing a
category token — the caller always knows it (`close_btn_icon_size` for tab close,
`button_icon_size` for title-bar buttons, `tab_icon_size` for tab icons). Then collapse the four
literal fallbacks to one module constant. See also §1.3: the whole point of the supersampled
renderer in `_render_svg()` is defeated if the pixmap is subsequently rescaled by Qt.

## 2.7 Sidebar tab icons are never re-tinted

Covered in §1.5 under "Sidebar counterpart".

---

# Part 3 — Performance

## 3.1 Every tab switch rebuilds all five title-bar icons  **[Medium]**

`DockAreaTitleBar.update_button_states()` ([dock_area_title_bar.py:306](../lace/dock_area_title_bar.py))
unconditionally calls `setIcon(dock_icon(...))` for all five buttons. `dock_icon()`
([dock_menu.py:70](../lace/dock_menu.py)) allocates a fresh `QIcon`, calls `provider.get()` twice
and `addPixmap()` four times, every time.

Measured on a 2-area × 4-tab layout **[verified]**:

| Operation | wall time | `dock_icon()` | `provider.get()` | `update_button_states()` |
|---|---|---|---|---|
| 1 theme switch | 18.5 ms | 18 | 44 | 2 |
| 20 tab switches | 56.3 ms | 100 | 200 | 20 |

That is **5 `dock_icon()` calls and ~2.8 ms per tab click**, in a code path that runs on every
single click in the UI. `DockIconProvider._icon_cache` saves the SVG rasterisation, but not the
`QIcon` allocation, the two `.pixmap()` round-trips, the four `addPixmap()` calls, or the repaint
that `setIcon()` schedules on each button.

Only three of the five icons can even change between calls (`undock` ↔ `dock`, `maximize` ↔
`restore`, `pin` ↔ `unpin`); `tabs_menu` and `close` are constant for the lifetime of the theme.

**Proposal:** the codebase already has the right pattern — `DockWidgetTab.refresh_style()` guards
its close icon with

```python
icon_key = (self._style_mgr.generation, icon_size_val)
if icon_key != self._applied_close_icon_key:
    ...setIcon(...)
```

Apply the same guard in `update_button_states()`, keyed on `(icon_key_name, generation, icon_dim)`
per button. Better still, memoise inside `dock_icon()` on `(key, category, token, size,
sm.generation)` so every call site benefits at once — the provider already invalidates on theme
change via `on_style_changed()`, so the outer memo only needs the generation counter.

Secondary: `update_button_states()` returns early when `area.current_dock_widget()` is `None`
(:310-312), so an area that is momentarily empty keeps whatever button state it had. Worth a look
separately.

## 3.2 Per-area application-wide focus connections  **[Low]**

`DockAreaWidget.__init__` ([dock_area_widget.py:65-68](../lace/dock_area_widget.py)) connects
`QApplication.focusChanged` to `self._on_app_focus_changed`, once per dock area, and never
disconnects. With N areas, every focus change in the entire application invokes N Python slots,
each of which does an `isAncestorOf()` walk. `DockManager.__init__` adds one more (:118-121).

Qt auto-disconnects on `QObject` destruction, so this is not a leak — it is a linear-in-areas cost
on a very hot signal. A single manager-level handler that resolves the area via
`find_parent(DockAreaWidget, new_widget)` would do the same job in one slot.

## 3.3 Icon cache key omits device pixel ratio  **[Low]**

`DockIconProvider._icon_cache` is keyed on `(name, color, active, disabled, size)`
([dock_icon_provider.py:226](../lace/dock_icon_provider.py)) — no DPR. `_render_svg()` bakes
`QApplication.instance().devicePixelRatio()` into the pixmap at :129.

Two consequences on multi-monitor setups: `QGuiApplication::devicePixelRatio()` is documented as
returning the **highest** ratio across all screens, so icons are over-rendered on the low-DPI
monitor; and a window moved between monitors of different DPR keeps the cached pixmap.

Also note `active` and `disabled` are redundant in the key — both are already folded into `color`,
which is derived from them.

---

# Part 4 — Dead code and cleanup

## 4.1 The `DockSignals` bus is connected but never emitted  **[verified]**

`DockManager.__init__` ([dock_manager.py:81-84](../lace/dock_manager.py)) constructs `DockSignals`
and connects all three signals to handlers (`_handle_request_overlay_show`,
`_handle_request_overlay_hide`, `_handle_floating_widget_dropped`, :438-446). **No `.emit()` exists
anywhere in the package** — a full grep returns only the three `connect()` lines.

The "Phase 5 global event bus" that `dock_signals.py` describes as replacing "tight coupling (where
deep widgets call manager methods directly)" was never wired up; the direct-call path
(`FloatingDockContainer` → `container.drop_floating_widget()`) is what actually runs. So Lace ships
a class, a public export (`lace/__init__.py:59, 135`), and three unreachable handlers.

**Proposal:** either finish the migration or delete `DockSignals`, the three handlers and the
public export. Half-wired indirection is worse than either end state — it reads as a supported
extension point that silently does nothing.

## 4.2 Three layers of `_drop_into_*` delegation

```
DockManager._drop_into_container      (dock_manager.py:685)
  → DockContainerWidget._drop_into_container   (dock_container_widget.py:424)
    → DropController._drop_into_container      (dock_container_widget.py:103)
```

Same for `_drop_into_section`, `_drop_into_center_of_section` and `drop_floating_widget`. The only
consumer outside the library is `dev_smoke/interactive/generate_baselines.py`, which calls the
manager-level pass-throughs. Since these are underscore-private, keeping two extra hops for one
dev script is a poor trade — point the script at `DropController` (or expose one public
`drop_floating_widget()`) and drop the middle layers.

## 4.3 Miscellaneous dead code

- **`paint_panel()`** ([dock_paint.py:274](../lace/dock_paint.py)) — imported by `dock_chrome.py`
  but never called there; the only caller is `tests/test_dock_paint.py:159`. Production code uses
  `paint_panel_bg` + `paint_panel_border` separately.
- **`DockMenuMixin`** ([dock_context_menu.py:20](../lace/dock_context_menu.py)) — an empty class
  whose docstring says "Deprecated legacy mixin", exported from `lace/__init__.py` (:58, :166).
  `sidebar_tab_bar.py:420` still *mentions* it in a docstring for a method that doesn't use it.
- **`dock_context_menu.py`** is otherwise a pure re-export shim over `dock_menu.py`. Worth an
  explicit deprecation note with a removal version, or removal.
- **`DockAreaWidget.update_title_bar_visibility()`** ([dock_area_widget.py:323](../lace/dock_area_widget.py))
  is already a documented deprecated alias with a `DeprecationWarning` — good pattern; the two
  above should follow it.

## 4.4 Unused imports  **[verified by AST scan]**

| file | line | name |
|---|---|---|
| `dock_chrome.py` | 17 | `paint_panel` |
| `dock_manager.py` | 15 | `Any`, `Union` |
| `dock_menu.py` | 14, 20 | `List`, `WidgetState` |
| `dock_overlay.py` | 15, 16 | `QPointF`, `QRectF`, `QLineF`, `QPolygonF` |
| `dock_widget_tab.py` | 19 | `QPushButton` |
| `sidebar_tab.py` | 11 | `Union` |
| `sidebar_title_bar.py` | 13 | `QToolButton` |

(`from __future__ import annotations` hits were excluded as false positives.)

Worth wiring `ruff check --select F401,F811` into `.github/workflows` so this does not re-accumulate.

## 4.5 Icon assets

- **`close_others.svg` is byte-identical to `close.svg`** (`md5 65e7f573a3a842714ca798ddba12d5bc`).
  Deduplicate — or give "Close Others" its own glyph, which is arguably the better UX anyway.
- **`maximize.svg` (1680 B) and `restore.svg` (1905 B)** carry full Inkscape round-trip metadata:
  `sodipodi:namedview`, window geometry, zoom level, `inkscape:current-layer`. The hand-authored
  icons in the same directory are 347–616 B. Running them through `svgo` (or hand-stripping the
  `sodipodi`/`inkscape` namespaces) cuts ~2.5 KB and removes the `style="stroke-width:1.5"`
  per-path overrides that duplicate the root attribute.
- Both files also measure **1.43** effective stroke where their siblings measure 1.50, and sit in a
  17.5-unit box against `close_tab`/`unpin`'s 19.4 — consistent with having been redrawn by hand
  rather than taken from the Tabler grid. Fold into the §1.3 normalisation pass.
- Consider adding `lace/resources/lace_icons/README.md` recording the invariants: 24×24 viewBox,
  `stroke="currentColor"`, `stroke-width="1.5"`, `stroke-linecap/linejoin="round"`, content box
  N→24−N. A five-line file would have caught (c) and (d) at authoring time.

---

# Part 5 — Consistency observations

These are not bugs, but they are the conditions that produced several of the bugs above.

1. **Two spellings of "insert a dock area".** `_add_dock_area()` and `_dock_widget_into_dock_area()`
   do the same job with different post-conditions (§1.1); `_drop_into_container()` and
   `_drop_into_section()` do the same job with different centre handling (§1.2). Each pair should
   converge on one helper.

2. **Two spellings of "what colour is this element in this state".** `_resolve_focus_colors()`,
   `resolve_tab_outline_color()`, `resolve_title_bar_border_color()` and
   `resolve_below_title_frame_color()` are a well-factored family with good docstrings explaining
   *why* the resolution is centralised — and then `DockIconProvider._resolve_normal_color()` sits
   outside it and re-derives the same concept without focus (§1.5). Icons should join that family.

3. **Four fallback values for one icon size** (§2.6): `14` in `dock_menu.py:83` and
   `dock_area_title_bar.py:321`, `16` in `dock_theme.py:182`, `dock_area_title_bar.py:501`,
   `sidebar_title_bar.py:342`, `frameless_titlebar.py:177`, and `dock_chrome.py:328`. One constant.

4. **`style_title_bar_buttons()` accepts dead parameters.** `color` and `disabled` are documented as
   "accepted for call-site compatibility but unused" ([dock_chrome.py:338](../lace/dock_chrome.py)).
   Both call sites pass them. Removing them from both is a two-line change that stops the next
   reader wondering whether button tinting flows through there.

5. **`DockAreaTitleBar._create_buttons()` sets `setIconSize(QSize(16, 16))` on the close button
   only** ([dock_area_title_bar.py:168](../lace/dock_area_title_bar.py)), out of five buttons, and
   it is overwritten moments later by `refresh_style()`. Vestigial; delete.

6. **Defensive `hasattr()` is load-bearing in places it shouldn't be.** e.g.
   `dock_container_widget.py:723`: `if visible and hasattr(self, '_dock_manager') and
   self._dock_manager and hasattr(self._dock_manager, 'sidebar_manager')`. `_dock_manager` is set
   in `__init__` and `sidebar_manager` is a plain attribute on `DockManager`; the guards hide
   ordering bugs rather than preventing them. 84 `hasattr()` calls across 18 modules is worth a
   pass.

7. **34 `except Exception` sites.** Several are correct (`_notify_subscribers`, file I/O in
   `layout_serializer`). Several swallow programming errors — e.g. `dock_style_manager.py:261`
   logs and continues when a subscriber's `refresh_style()` raises, which is how a broken
   `refresh_style()` becomes an invisible styling failure rather than a traceback. Narrowing the
   ones around Qt object lifetimes to `RuntimeError` (the pattern already used correctly in
   `dock_splitter.py` and `dock_area_widget.py`) would make the remaining broad catches meaningful.

---

# Appendix — Reproduction

All probes ran against commit `2f16f8e` with:

```bash
QT_QPA_PLATFORM=offscreen "C:/Users/Main/AppData/Local/Python/developenv/Scripts/python.exe" <script>
```

| Probe | What it establishes |
|---|---|
| `inkmeasure.py` | Renders each SVG through `DockIconProvider._render_svg` at 320 px, measures effective stroke as `2 × p90(chamfer distance-to-background)` and the ink bounding box → §1.3, §1.4 tables |
| `tokencheck.py` | Field-presence check on the style schemas + live `DockStyleManager.get()` resolution → §2.5, §2.6 |
| `verify2.py` | Two dock areas, focus moved between them, compares `tab._applied_text_color` against `DockIconProvider._resolve_normal_color()` → §1.5 |
| `verify3/4.py` | Programmatic splits down both branches of `_dock_widget_into_dock_area`, dumps the splitter tree and geometry, introspects both insertion methods → §1.1 |
| `verify5.py` | Enumerates direct `QWidget` children of the root container → §2.3 |
| `verify6.py` | Primes `_handle_cache`, runs `save_state()`/`restore_state()`, compares cached vs live handle counts → §2.1 |
| `perf.py` | Wraps `dock_icon`, `DockIconProvider.get` and `update_button_states` with counters; times a theme switch and 20 tab switches → §3.1 |

Scripts are in the session scratchpad; none of them touch the repository.

---

## Suggested order of work

1. **§2.1** — one line, silent feature breakage after every perspective load.
2. **§1.4 + §4.5** — icon assets, no code risk, immediately visible.
3. **§1.2** — two small changes, restores a feature users expect.
4. **§1.5** — visible on 10 of 19 themes.
5. **§1.1 + §2.2** — the `_finish_area_insertion()` refactor; fixes three defects at once.
6. **§3.1** — measurable, and the guard pattern already exists in the codebase.
7. **§1.3, §2.3–2.6** — correctness/robustness with no current user-visible symptom.
8. **§4.x** — cleanup, ideally behind a `ruff` CI gate so it stays clean.
