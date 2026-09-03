# Changelog

All notable changes to Lace are recorded here.  Versions follow
[Semantic Versioning](https://semver.org/); Lace is pre-1.0, so removals from
the public API happen in minor/patch releases rather than being deprecated
through a cycle.

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
