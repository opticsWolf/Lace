# Changelog

All notable changes to Lace are recorded here.  Versions follow
[Semantic Versioning](https://semver.org/); Lace is pre-1.0, so removals from
the public API happen in minor/patch releases rather than being deprecated
through a cycle.

## [0.7.0] — 2026-09-03

The release the 0.6.6 – 0.6.18 patches roll up into: the seven phases of
`docs/IMPROVEMENT_PLAN_v0.7.md`, one bug found while testing them, and the
theme work that followed.  Nothing new lands here that is not already in an
entry below — this is the version number catching up with the work.

Every phase shipped with at least one test that fails on the 0.6.5 baseline
(`2f16f8e`) and passes after, checked by stashing the source and running the
new tests against the old package.  The suite went from 443 tests to 613.

### Highlights

- **Docking** — one insertion path and one cache invalidator (0.6.6); one drop
  policy, one root-splitter lookup, one delegation (0.6.7); a floating widget
  can be dropped into the centre to tab (0.6.8); a drop onto a maximized area
  restores it first (0.6.9); one centre indicator rather than two over a
  solo-area float (0.6.13).
- **Signals** — `DockSignals` is a real bus reachable as `dock_manager.signals`,
  carrying `request_overlay_hide` and `floating_widget_dropped` (0.6.10).
- **Icons** — tabs tint and size their icons from the theme, sidebar tabs
  included (0.6.11).
- **Hygiene** — one focus handler on the manager instead of one connect per
  area, the `dock_context_menu` shim removed, and a `ruff` gate for F401/F811
  in CI (0.6.12).
- **Themes** — 14 presets became 27.  Light, neutral and dark counterparts for
  the four edge-treatment designs (0.6.14, 0.6.15), the neutrals corrected
  twice as what "neutral" should mean got pinned down (0.6.16, 0.6.18), and
  the whole set grouped so a menu can show it in four submenus (0.6.17).

### Breaking

- **`lace.dock_context_menu` is gone** (0.6.12).  Import `MenuSection`,
  `MenuContext` and `MenuActionTarget` from `lace` or `lace.dock_menu`.
  `DockMenuMixin` is no longer in `lace.__all__`.
- **`DockSignals.request_overlay_show` was removed** (0.6.10).  It was never
  emitted in any released version; its only would-be call site needs
  `show_overlay()`'s return value, which a signal cannot carry.
- **`style_title_bar_buttons()` lost its `color` and `disabled` parameters**
  (0.6.12).  Both were dead — the buttons take their colours from the theme.
- **`floating_widget_dropped` carries three arguments now** (0.6.10), the
  target container having been added between the widget and the position.
- **`cyberpunk_edge_neutral`, `violet_haze_neutral` and
  `midnight_haze_neutral` look substantially different** from their 0.6.14
  debut, and all three are now `is_light = True` (0.6.16, 0.6.18).  Anything
  reading that flag to sort themes into dark and light — OS auto-sync
  overrides included — will classify them the other way now.
- **`theme_choices()` returns a different order** (0.6.17): the grouped order
  flattened, rather than definition order.  Same pairs, same shape.

### Added

- `tests/test_version_is_consistent.py` — the package version, `pyproject`,
  the three doc headers and the newest CHANGELOG heading must agree.  At this
  bump the headers read 0.6.5, 0.5.0 and 0.5.0 against a package at 0.6.18.

### Known gaps

Five behaviours cannot be exercised headless and want a manual pass on
Windows: centre-drop tabbing, targeted splits sizing evenly, tab icons
dimming with their labels, junction co-drag after a perspective restore, and
a split drop onto a maximized area.

## [0.6.18] — 2026-09-03

### Changed

- **`cyberpunk_edge_neutral`, `violet_haze_neutral` and `midnight_haze_neutral`
  are now mid-tone**, sitting between their parent and their light counterpart
  and nearer the light — panel lightness 0.73 against 0.12 and 0.98 on
  `cyberpunk_edge`, 0.74 against 0.27 and 0.98 on `violet_haze`, 0.74 against
  0.17 and 0.98 on `midnight_haze`.  0.6.16 flattened the grounds without
  moving them, which left three near-blacks sitting beside their parents:
  close enough that a menu offered two entries hard to tell apart, and each
  family had a hole where its middle tier should be.  Flatness is unchanged
  and so is the rule that nothing meaning-bearing gets drained — the accent,
  the focus outlines and the four status tokens are all still kept.
- **All three carry `is_light = True` now**, which reverses every derived
  adjustment: body text, hover fills, shadow alphas and the default status
  colours.  Anything that read the flag to decide dark-versus-light — OS
  auto-sync overrides included — will now classify these three as light.
- **Their accents were re-solved rather than interpolated.**  A mid ground is
  the hardest of the three: a dark accent loses contrast as the ground darkens
  and a pale one loses it as the ground lightens.  `cyberpunk_edge_neutral`'s
  amber lands at `148,72,0` — *below* the light counterpart's `186,98,0`, not
  between it and the parent's `255,154,0`, because that colour measures 1.9:1
  here against 4.5:1 on near-white.  Its violet moves the other way, up from
  the parent's.
- **`midnight_haze_neutral`'s sidebar wash goes to alpha 34** (from 30).  The
  crossover it is capped against is mirrored rather than gone: the wash is a
  dark accent over a light bar now, so an idle tab reads darker than the bar
  and the hover it must not cross is darker still — bar `163,163,168`, idle
  `150,150,171`, hover `132,132,138`, ceiling at alpha 81.
- **Each family is now a real ordering by lightness**, so
  `test_theme_grouping.py` asserts the monotonic run it could only assert the
  end of before.

## [0.6.17] — 2026-09-03

### Added

- **`theme_groups()`** (`lace.theme_groups`) — `(group label, [(label, key), ...])`
  for building a themes menu as submenus.  Twenty-seven entries in one flat
  column is a scroll, and it hid the thing a reader most needs to see: that
  `violet_haze_neutral` is not a preset of its own but one key of a design that
  ships in three.
- **`THEME_GROUPS`** (`lace.dock_custom_theme`) — the grouping itself, in
  presentation order: **Basics** (5), **Editor Classics** (7), **Neon** (2) and
  **Edge Treatments** (12, the four families).  Full coverage of `THEME_SPECS`
  is asserted at import, not just in the tests — an ungrouped preset vanishes
  from every grouped menu, and by the time a test run catches it the wrong file
  has already been pushed.

### Changed

- **`THEME_SPECS` is now written in those four sections**, and each family runs
  dark, neutral, light — with `slate_amber`'s dark, light, lighter as the
  documented exception.  Source reordering only; no palette or geometry moved.
- **`theme_choices()` returns the grouped order flattened** rather than
  definition order.  Same twenty-seven pairs, same shape, so existing callers
  need no change; a flat menu now keeps each family together.
- **The three demos build submenus** from `theme_groups()`.  In
  `demo_app_custom_titlebar_menus` the flat column ran off the bottom of the
  short title bar; `add_themes_menu()` there now takes groups rather than
  choices.

## [0.6.16] — 2026-09-03

### Changed

- **`cyberpunk_edge_neutral`, `violet_haze_neutral` and `midnight_haze_neutral`
  were rebuilt.**  As shipped in 0.6.14 they drained the hue from everything,
  accent included, which cost each preset the thing that identified it.
  "Neutral" now means the *grounds* only: `base`, `surface` and `title_bg`
  flatten toward grey while keeping a trace of the parent's cast, and every
  colour that carries meaning stays — the accent (nudged, not drained),
  `cyberpunk_edge`'s violet/amber focus pair, `violet_haze`'s "comment"
  outline, and the four status tokens.  The effect is subtractive: the backdrop
  stops competing with the accent in front of it.

## [0.6.15] — 2026-09-03

### Added

- `slate_amber_light`, a brighter tier of `slate_amber` — not a counterpart in
  the sense of the seven added in 0.6.14, but the same light design with the
  greys lifted ~35 points.  `slate_amber` itself is unchanged.  The amber moves
  the other way (186,98,0 to 176,92,0): it draws 1.5px lines, and every point
  the ground gains is a point of separation they lose.  The family now runs
  `slate_amber_dark` / `slate_amber` / `slate_amber_light`.
- README and ARCHITECTURE now document the counterparts (both were still
  claiming 19 themes after 0.6.14 added seven).

## [0.6.14] — 2026-09-03

### Added

- Seven theme presets, each a counterpart of one of the four edge-treatment
  presets, keeping its parent's geometry exactly and changing only the palette:
  `cyberpunk_edge_light`, `violet_haze_light`, `midnight_haze_light`,
  `cyberpunk_edge_neutral`, `violet_haze_neutral`, `midnight_haze_neutral`,
  and `slate_amber_dark`.  25 presets ship now.
- `SIDEBAR.tab_icon_size` and `SIDEBAR.tab_icon_gap` were added in 0.6.11; the
  counterparts inherit them like every other token.

## [0.6.13] — 2026-09-03

### Fixed

- Dragging a dock onto a floating window holding a single tab drew **two**
  centre indicators.  The container cross was armed with all five areas
  whenever the container had one visible area or fewer, which was only right
  while a lone area was armed with `no_area` and so drew nothing; once a lone
  area got its own centre back in 0.6.8, the two collided.  Whichever cross
  the cursor is actually over owns the centre now — the dock area when one is
  under the cursor, the container otherwise.

## [0.6.12] — 2026-09-03

Phase 7 of `docs/IMPROVEMENT_PLAN_v0.7.md`: cleanup and hygiene.

### Removed

- **`DockMenuMixin`** — an empty class whose own docstring called it a
  deprecated legacy mixin.  Gone from `lace.__all__` too.
- **`lace.dock_context_menu`** — a pure re-export shim over `lace.dock_menu`.
  Import the same names from `lace` or from `lace.dock_menu` instead; every
  one of them is still exported.
- **`style_title_bar_buttons()`'s `color` and `disabled` parameters** — both
  were accepted and dropped on the floor.  The icons are pre-coloured pixmaps
  and Qt greys them for the disabled state itself.
- **`DockContainerWidget._drop_into_container/_section/_center_of_section`
  delegation from `DockManager`** (0.6.7) — call
  `container.drop_controller()` and use `DropController` directly.
- The unused `paint_panel` import in `dock_chrome.py` (the function itself
  stays), a vestigial `setIconSize(QSize(16, 16))` on one title bar button out
  of five, eleven unused imports, and two sets of shadowed duplicate methods.

### Changed

- Focus dispatch is one manager-level `focusChanged` handler resolving the
  area from the focused widget, rather than one connection per open dock area
  each doing an `isAncestorOf()` walk on one of Qt's hottest signals.
- `DockStyleManager` no longer swallows every exception a subscriber's
  `refresh_style()` raises: only `RuntimeError` (the deleted-C++-object case)
  is caught, so a genuine bug is a traceback rather than an invisible styling
  failure.

### Added

- A `lint` job in CI running `ruff check --select F401,F811 lace/`.

## [0.6.11] — 2026-09-03

Phase 6: icon colour and size.

### Fixed

- Tab icons now dim with their labels.  They were tinted by
  `DockIconProvider`, which knows `active` and nothing about focus, so on the
  ten built-in themes with `tab_dimming` the label dimmed on focus loss and
  the icon beside it stayed bright.
- A tab icon named after a missing SVG falls back to the default icon and
  then to `windowIcon()`.  The fallback chain was a run of `elif`s, so an
  unresolvable name suppressed every later fallback and the tab painted no
  icon at all.
- Sidebar tabs re-render their icon in their own text colour instead of
  painting whatever `QIcon` they were handed, which left dark icons dark next
  to light text on a dark theme.
- The icon cache key carries the device pixel ratio that `_render_svg()` bakes
  into the pixmap, so a window dragged between monitors of different DPR no
  longer keeps a stale one.
- A tab whose icon comes from `windowIcon()` is memoised like any other; it
  used to re-run the full pixmap render on every tab switch.

### Added

- `DockIconProvider.get(color=...)`, for callers whose tint depends on
  something the provider cannot see.
- `TAB.tab_icon_size`, `SIDEBAR.tab_icon_size` and `SIDEBAR.tab_icon_gap`
  theme tokens, replacing hardcoded 16s and 8s, so a theme that scales its
  fonts can scale its icons with them.
- `VerticalTabButton.set_icon_name()`.

## [0.6.10] — 2026-09-03

Phase 5: the `DockSignals` bus carries the drag-and-drop lifecycle.

### Changed

- `floating_widget_dropped` carries the target container as well as the
  floating widget and the drop position; the old handler always routed to the
  root container, which is wrong for a drop onto another floating window.

### Removed

- `request_overlay_show` — its only call site consumes
  `DockOverlay.show_overlay()`'s return value inside the drag's mouse-move
  path, and a signal cannot return anything.

## [0.6.9] — 2026-09-03

Phase 4: maximize-aware drops.

### Fixed

- A split drop onto a maximized area restores it first.  The drop reshapes the
  splitter tree the pre-maximize sizes were captured against, so the hidden
  siblings were stranded with no route back.  A centre drop only adds a tab
  and stays maximized.
- Pre-maximize sizes are held on the splitter itself rather than in a dict
  keyed by `id()`, which CPython reuses after a splitter is freed.
- A saved size list that no longer matches its splitter's child count is
  discarded rather than partially applied — `setSizes()` applies as many
  values as it is given and silently leaves the rest.

## [0.6.8] — 2026-09-03

Phase 3: a floating widget can be dropped into the centre of a container
holding a single dock area, tabbing into it.  Previously the centre indicator
could not resolve, so the only way to tab into a lone area was to aim at its
title bar.

## [0.6.7] — 2026-09-03

Phase 2: one drop path.

### Changed

- One allowed-areas policy (`floating_behaviour.allowed_areas_for()`) instead
  of two that disagreed.
- One root-splitter lookup, via `root_splitter()`, instead of a `findChild()`
  that could pick up an unrelated splitter.
- `center` no longer aliases `bottom` in `dock_area_insert_parameters()`,
  which now raises `ValueError` for it.

## [0.6.6] — 2026-09-03

Phase 1: one insertion path (`_finish_area_insertion()`), one cache
invalidator (`_invalidate_layout_caches()`), and shared even-split arithmetic
(`util.split_share()`).

### Fixed

- Restoring a layout invalidates the splitter handle cache, which could
  otherwise serve handles belonging to a torn-down tree.

## [0.6.5] — earlier

The baseline this plan was written against.  See the git history for releases
up to and including it.
