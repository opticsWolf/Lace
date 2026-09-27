# Lace 0.8 — Theming Modernisation Plan

**Baseline:** commit `f8f5358` (v0.7.6), branch `dev_v08`
**Scope:** three improvement areas —
(a) a modernised, cleaner Fusion: every standard control redrawn flat and sharp, on Fusion's
sizes and its complete use of the palette,
(b) rounded dock areas that round their content cleanly,
(c) a perceptual colour engine with contrast guarantees, driven by a few keywords,
plus a theme kit (API, CLI and a Studio window) for deriving and checking new themes on top of it
**Staging:** eight main phases plus two theme-kit phases (K1, K2), one PR (or one reviewed merge)
each, tests green at every boundary
**Compatibility:** pre-1.0 semantics as in 0.7 — every new `ThemeSpec` field is optional, existing
presets and JSON themes load unchanged, anything removed is recorded in the changelog
**Testing rule:** every phase adds at least one test that **fails on `f8f5358` and passes after**,
plus the smoke and visual gates listed in its section


## Phase 0 baseline (recorded 2026-09-27, 0.7.6 code, Python 3.13, PySide6 6.11, Windows 11)

| Measure | Value |
|---|---|
| Unit tests | 643 passed, 24 xfailed (the two visual harnesses) |
| Runtime | 18.6 s serial, 9.6 s with `-n auto`, same count |
| Smoke checks | all 21 pass; 11.8 s serial, 1.8 s with `--jobs auto` |
| Token snapshot | `tests/baselines/theme_tokens_0.7.6.json`, 36 themes, deterministic (zero drift on re-dump) |
| Screenshots | `screenshots/m0_0.7.6/`, main + float for the 20 `FULL` themes |

Zoom harness, mean edge width at 4x in device px (limit 2.0), kilim_dark / kilim_light_neo:

| Glyph | kilim_dark | kilim_light_neo |
|---|---|---|
| combo arrow | 5.80 | 6.03 |
| spin arrows | 6.44 | 5.62 |
| double-spin arrows | 6.26 | 5.67 |
| check indicator | 2.58 | 2.66 |
| radio indicator | 3.76 | 2.80 |
| scrollbar, horizontal | 5.16 | 4.31 |
| scrollbar, vertical | 5.15 | 4.39 |
| slider handle | 2.52 | 2.18 |
| tree branch, open | 7.74 | 7.81 |
| tree branch, closed | 7.73 | 7.85 |
| menu submenu arrow | 7.15 | 4.82 |

Pixmap-painted glyphs grow with the zoom (1.6-2.9 px at 1x); the check indicator and slider
handle are vectors, but their gradient fills still widen the edges past the limit. All 22 are
strict xfails.

Corner harness (magenta content, bottom corners):

| Case | Radius (outline / content) | Result |
|---|---|---|
| kilim_dark, slate_amber | 4 / 2 | clean |
| kilim_midnight_neo, kilim_light_neo, cyberpunk_neon | 10 / 0 (content inset past the arc) | clean |
| solarized_light | 4 / 4, flush | leak 1 px + 5 stair steps per corner, xfail |
| flush_r10 (kilim_midnight_neo, `content_margin: 0`) | 10 / 8, near-flush | 3 stair steps per corner, xfail |

`flush_r10` is synthetic: no preset combines a large radius with near-zero inset, and it is the
case Phase 5 must get right. `ALL` is 36, not 37: the empty `default` preset is not counted.

---

## Goals

| Area | Today | Target |
|---|---|---|
| (a) Base style | Stock Fusion + a partial `QPalette`. Old-school scrollbars; arrow and check glyphs blur when a widget is zoomed in a `QGraphicsView` (Weave canvas) | `LaceStyle`, a `QProxyStyle` over Fusion that keeps Fusion's sizes, behaviour and palette handling but redraws the standard controls flat, rounded and vector-only: buttons, inputs, combo and spin boxes, check boxes, sliders, progress bars, tabs, menus, item views, scrollbars. Every palette role and colour group is set |
| (b) Rounded content | Content runs into the card corner; `DockWidget` clips it with an aliased `QRegion` mask ([dock_widget.py:632](../lace/dock_widget.py)), so corners staircase and child frames look cut off | An antialiased corner cap painted above the content by the existing border overlay; no masks on docked content. A `corner_clip` keyword picks cap / inset / none |
| (c) Colour logic | Additive HLS lightness steps, three different step functions, no contrast checks, `is_light` set by hand | One OKLCH-based colour module: perceptual steps, `ensure_contrast()`, `on_color()`, auto light/dark. Keywords `contrast`, `depth`, `selection` shape the whole derivation |

Visual intent for "sleek": flat surfaces separated by small, even lightness steps rather than
lines; thin, quiet borders; rounded, low-noise controls; readable text that never falls below the
contrast target; one accent used sparingly, only to show state. It is still Fusion underneath,
with the same sizes, spacing and interaction, so embedding apps don't reflow. The gradients,
bevels and dated glyphs are gone.

---

## Test theme sets

Theme checks come in **three stages**, picked by the scope of the work, plus one numbers-only
set. Each stage contains the one before it (5 ⊂ 11 ⊂ 20). All sets are defined once in
`tests/theme_sets.py` and imported by the unit tests, the smoke runner and the screenshot
script, so they can't drift apart. Every tool takes `--themes {quick,regular,full,all,auto}`.

| Stage | Set | Size | Scope of work | Screenshots reviewed |
|---|---|---|---|---|
| 1 | `QUICK` | 5 | Local change: one control family, a bug fix, a refactor that doesn't change colours or geometry. Also the inner loop while developing | no — numeric checks only |
| 2 | `REGULAR` | 11 | Change to anything shared: colour derivation, the palette, corner or dock geometry, the style's shared helpers. Also the gate at the end of every phase | no — numeric checks only |
| 3 | `FULL` | 20 | Milestones M1–M3 | yes, at milestones only |
| — | `ALL` | 36 | Token snapshot and drift report (numbers only, cheap) | never |

`ALL` = 27 Lace presets + all 10 Kilim keys (5 palettes × classic and neo chassis).

### Picking the stage

`--themes auto` picks the stage from the files the change touches (`git diff --name-only`
against the merge base with `dev_v08`), via `tests/select_theme_set.py`:

| Files touched | Stage |
|---|---|
| any of `lace/color_science.py`, `lace/dock_theme.py`, `lace/theme_models.py`, `lace/dock_custom_theme.py`, `lace/style/_paint.py`, `lace/lace_style.py`, `lace/dock_paint.py`, `lace/dock_chrome.py`, `tests/theme_sets.py`, `tests/fixtures/themes/*` | `REGULAR` |
| anything else | `QUICK` |

`FULL` is never picked automatically; it runs at milestones or by hand.

In CI: a branch push runs `auto`; a merge into `dev_v08` runs at least `REGULAR`; `FULL` runs on
a manual `workflow_dispatch` at each milestone.

### How the Kilim themes get into Lace's tests

Lace can't import Kilim: its palettes live in Kilim's Rust core
(`crates/kilim-core/src/kilim_themes.rs`) and are assembled into Lace themes by
`python/kilim/qt_themes.py`. Both parts are copied into `tests/fixtures/themes/kilim_*.json`: ten
JSON theme files, built exactly the way `qt_themes.py` builds them (palette + `KILIM_GEOMETRY` or
`KILIM_NEO_GEOMETRY`, plus the per-palette neo accents). Loading them through `load_theme_json()`
exercises the JSON path on every run as well. Each file records the Kilim source files and
commit it was copied from, so it can be refreshed when Kilim's palettes change.

Two facts shape the selection below:
- Kilim's five palettes are Lace's **Basics** tuned by hand: `kilim_warm` is `warm` colour for
  colour, `kilim_dark` is Lace's stock `default`, and the others are close relatives of `midnight`,
  `neutral` and `light`. The classic Kilim chassis is Lace's `dark` chassis (4 px, 1.5 px border).
  So the Kilim classic themes stand in for Basics in both sets.
- Kilim's neo chassis is an Edge Treatment (10 px, flush title bar, 1.5 px rule, ringed sidebar
  tabs), so two neo themes cover most of what `cyberpunk_edge*` exercise.

### Quick set (5)

The five themes of the regular set that differ most from each other. Each one stands for a
different way a theme can go wrong.

| # | Key | Light/dark | Geometry | What it stands for |
|---|---|---|---|---|
| 1 | `kilim_dark` | dark | 4 px, 1.5 px border | The reference dark theme: neutral grey, standard accent |
| 2 | `kilim_light_neo` | light | 10 px, flush title bar, rule | Light backdrop with a large radius: step direction reversed, corner cap on light |
| 3 | `slate_amber` | mid-grey | 4 px, title rule | Closest to the light/dark switchover, with a tight accent contrast |
| 4 | `cyberpunk_neon` | dark | 10 px, translucent border | Fully saturated accent and border: gamut limits, text on the accent, alpha borders |
| 5 | `solarized_light` | light | no border | Low-contrast text by design, tinted (cream) base: the `contrast` keyword's hardest case |

Coverage: 2 dark / 3 light (one mid-grey); radii 4 and 10; with and without a border; neutral,
warm-tinted and saturated palettes. Left to the regular set: warm dark hue (`kilim_warm`),
near-black base (`kilim_midnight`), pastel accent needing dark text (`dracula`).

Where a check needs only a light and a dark theme (glyph sharpness, the control gallery review),
it uses `kilim_dark` and `kilim_light_neo`.

### Regular set (11)

| # | Key | Source | Light/dark | Geometry | Why it's in the set |
|---|---|---|---|---|---|
| 1 | `kilim_dark` | Kilim classic | dark | 4 px, 1.5 px border | VS Code Dark+ grey/blue; the reference "sleek default" (same as Lace `default`) |
| 2 | `kilim_midnight` | Kilim classic | dark | 4 px | Near-black navy with a blue accent close to the base: low accent contrast |
| 3 | `kilim_warm` | Kilim classic | dark | 4 px | Warm hue: checks OKLCH steps keep the hue instead of greying it |
| 4 | `kilim_neutral` | Kilim classic | light | 4 px | Mid-grey base: closest to the light/dark switchover, so it tests auto-detection and step direction |
| 5 | `kilim_light` | Kilim classic | light | 4 px | High-clarity light; border barely darker than base |
| 6 | `kilim_midnight_neo` | Kilim neo | dark | 10 px, flush title, rule | Large radius on dark: corner cap, scrollbar near a corner |
| 7 | `kilim_light_neo` | Kilim neo | light | 10 px, flush title, rule | Large radius against a light backdrop |
| 8 | `cyberpunk_neon` | Lace, Neon | dark | 10 px, translucent cyan border | Fully saturated accent and border: gamut mapping, `on_color`, alpha borders |
| 9 | `slate_amber` | Lace, Edge Treatments | light (mid-grey) | 4 px, 1.5 px title rule, ringed sidebar tabs | The regular slate: dark amber accent on warm grey, where accent contrast is tight |
| 10 | `dracula` | Lace, Editor Classics | dark | stock | Panel much lighter than base; pastel accent that needs dark text on it |
| 11 | `solarized_light` | Lace, Editor Classics | light | stock, no border | Low-contrast text by design (≈ 3.6 : 1 on its panel): the case the `contrast` keyword must fix. No border, so corners rely on the cap alone |

Coverage: 6 dark / 5 light (one mid-grey Kilim, one mid-grey Lace); radii 4 and 10; border widths
0 and 1.5; flush and inset title bars; both `title_mode`s and `hover_mode`s; opaque and
translucent borders. Not covered, and left to the full set: radius 0, 2 px borders,
`border_below_title`, tab outlines, tinted sidebar tabs.

### Full set (20)

The 7 Kilim themes of the regular set plus 13 Lace presets, chosen so each covers something no
other member does.

| # | Key | Light/dark | Ground it covers |
|---|---|---|---|
| 1–7 | the 7 Kilim themes above | 4 dark / 3 light | see regular set |
| 8 | `cyberpunk_neon` | dark | saturated accent + translucent saturated border |
| 9 | `slate_amber` | mid-grey | tight accent contrast, title rule on the classic chassis |
| 10 | `dracula` | dark | panel far off the base, pastel accent |
| 11 | `solarized_light` | light | low-contrast text, no border |
| 12 | `midnight` | dark | **radius 0**, 0.5 px border, 4 px content margin, darkest base in the set |
| 13 | `monokai` | dark | light yellow accent (dark text on accent); panel hue differs from base hue |
| 14 | `nordic` | dark | no border on the stock chassis; desaturated accent close to text lightness |
| 15 | `catppuccin` | dark | **2 px** border at 50 % alpha, translucent focus border, 5 px content margin |
| 16 | `solarized_dark` | dark | saturated teal base; low-contrast text (≈ 4.1 : 1) on dark |
| 17 | `neon_dusk` | dark | **tab outlines**, 8 px radius with no card border, explicit title bg, sidebar flat on the outward edge |
| 18 | `cyberpunk_edge_neutral` | mid-grey | Edge chassis on the mid-grey counterpart logic, dark orange accent |
| 19 | `violet_haze_light` | light | **`border_below_title`**, 2 px frame and tab outlines on light |
| 20 | `midnight_haze` | dark | **tinted sidebar tabs** (accent at low alpha), `border_below_title` on dark |

Coverage: 13 dark / 7 light; radii 0, 4, 8 and 10; border widths 0, 0.5, 1.5 and 2; opaque and
translucent borders; every sidebar-tab flat-edge mode Lace ships (`all`, `none`, `outward`);
every indicator position used by a preset (`bottom`, `none`).

**Left out, and what covers each instead:**

| Left out | Covered by |
|---|---|
| `default`, `dark`, `light`, `neutral`, `warm` | the Kilim classic themes (same chassis, same or near-identical palettes) |
| `kilim_dark_neo`, `kilim_neutral_neo`, `kilim_warm_neo` | `kilim_midnight_neo`, `kilim_light_neo`, `cyberpunk_edge_neutral` |
| `tokyo_night` | `neon_dusk` / `midnight_haze` (indicator `none`), `dracula` (stock chassis, pastel accent) |
| `cyberpunk_edge`, `cyberpunk_edge_light` | `kilim_midnight_neo`, `kilim_light_neo` (same chassis), `cyberpunk_edge_neutral` |
| `violet_haze`, `violet_haze_neutral` | `violet_haze_light` (geometry), `dracula` (palette) |
| `midnight_haze_neutral`, `midnight_haze_light` | `midnight_haze` (tinted tabs), `violet_haze_light` (haze chassis on light) |
| `slate_amber_dark`, `slate_amber_light` | `slate_amber` (chassis), `kilim_warm` (warm dark palette) |

The dropped themes still run in `ALL` for the drift report, so a regression that only shows up in
one of them is still caught by the numbers, just not reviewed as a screenshot.

### Milestones

| Milestone | When | Set | What runs |
|---|---|---|---|
| M0 | end of Phase 0 | `ALL` (numbers), `FULL` (images) | token snapshot of all 36; 0.7.6 screenshots of the 20 |
| M1 | end of Phase 2 | `ALL` (numbers), `FULL` (images) | drift report and contrast table; screenshots reviewed |
| M2 | end of Phase 6 (tracks merged) | `FULL` | full gate, screenshots, 0.7.6 vs 0.8 comparison grid |
| M3 | release candidate | `FULL` | screenshots only, as a final visual pass |

Between milestones, `--themes full` is available by hand but isn't part of any gate.

---

## Keyword surface (end state)

New optional `ThemeSpec` / JSON fields. Anything a theme sets explicitly still wins over the
derived value.

| Keyword | Values (default **bold**) | Drives |
|---|---|---|
| `is_light` | `True` / `False` / **`None` = auto** from base luminance | step direction for every derived colour |
| `contrast` | `low` / **`normal`** / `high` | minimum WCAG ratios for text, muted text, disabled text, borders, focus ring |
| `depth` | `flat` / **`subtle`** / `raised` | OKLCH lightness gap between base, panel, title bar, input and button surfaces |
| `title_mode` | `darker` / `lighter` (unchanged) | title bar direction off the panel — now a perceptual step |
| `hover_mode` | `darker` / `lighter` (unchanged) | hover strength — now a perceptual step |
| `selection` | **`solid`** / `tint` | `Highlight` role: accent fill with `on_color()` text, or accent at low alpha with normal text |
| `corner_clip` | **`cap`** / `inset` / `none` | how content meets a rounded card (Phase 5) |
| `scrollbar` | **`thin`** / `expanding` / `fusion` | `LaceStyle` scrollbar look (Phase 4) |
| `control_radius` | int, **4** (`0` = square) | corner radius of every `LaceStyle` control (Phase 4) |

Contrast targets (WCAG 2.x ratio against the surface the text sits on):

| Token | `low` | `normal` | `high` |
|---|---|---|---|
| text | 4.5 | 7.0 | 10.0 |
| muted text | 3.0 | 4.5 | 7.0 |
| disabled text | 1.8 | 2.3 | 3.0 |
| non-text UI (focus ring, checkbox outline, scrollbar handle) | 1.5 | 3.0 | 4.5 |
| neutral card border | 1.15 | 1.3 | 1.6 |

These are floors, not targets: a colour that already passes is left alone, so existing presets
only move where they currently fail.

---

## Phase dependency graph

```
Phase 0  Baseline & test infrastructure   ── first; everything else measures against it
            │
            ├── Track A ─ Phase 1  Colour engine (pure functions)
            │                │
            │             Phase 2  Theme derivation + keywords ──┐
            │                │                                    │
            │             Phase 3  Complete QPalette              │
            │                                                     │
            ├── Track B ─ Phase 4a LaceStyle primitives & helpers │
            │                │                                    │
            │             Phase 4b Control families (4 in parallel:
            │                      buttons ∥ inputs ∥ range ∥ containers)
            │                                                     │
            ├── Track C ─ Phase 5  Rounded content (corner cap)   │
            │                                                     ▼
            └── Track D ─ Phase K1 Theme kit: library & CLI (needs Phase 2)
                             │
                          Phase K2 Theme Studio (needs K1, 4a, 5)
                             │
      Tracks A, B, C, D ─────┴──> Phase 6  Integration & preset retune
                                     │
                                  Phase 7  Docs, screenshots, release 0.8.0
```

**Parallelism.** After Phase 0, the tracks touch disjoint files and can proceed in parallel
(separate worktrees or branches off `dev_v08`):

| Track | Files owned | Reads, doesn't write |
|---|---|---|
| A | `lace/color_science.py` (new), `lace/dock_theme.py`, `lace/theme_models.py`, `lace/dock_custom_theme.py` | — |
| B | `lace/lace_style.py`, `lace/style/*` (new), `lace/dock_theme_bridge.py` — after 4a, each 4b family owns one module in `lace/style/` | `QPalette` roles only |
| C | `lace/dock_chrome.py`, `lace/dock_widget.py`, `lace/dock_area_widget.py`, `lace/floating_behaviour.py`, `lace/dock_paint.py` | `CORE.canvas_bg`, `CORE.corner_radius` |
| D | `lace/theme_kit/*` (new) | the Phase 1–2 engine, the Phase 4a gallery, the Phase 5 corner cap |

Track B depends only on `QPalette` roles, which exist today, so it doesn't wait for Track A. It
picks up Phase 3's extra roles automatically when the tracks merge. Track C needs the backdrop
colour, which `CORE.canvas_bg` already provides.

**Merge order into `dev_v08`:** A (1 → 2 → 3), then B, then C, then D (K1 can merge as soon as
Phase 2 is in; K2 last). Each later merge re-runs the full gate against the combined tree.
Phases 6 and 7 are strictly sequential.

---

## Test layers

Every phase is gated by the layers below. Layers 1–3 run in CI; layer 4 is manual.

| Layer | What | How it runs | Parallel |
|---|---|---|---|
| 1. Unit | `tests/` (pytest, offscreen) | `python -m pytest tests/ -n auto` | yes — pytest-xdist, one process per worker; the `DockStyleManager` singleton is per process and already reset per test by `conftest.py` |
| 2. Smoke | `dev_smoke/run_all.py` | new `--jobs N` flag: runs checks through a process pool (each check is already its own process with its own `QApplication`) | yes — process pool |
| 3. Visual | new `tests/visual/`: numeric sharpness and corner metrics on every run (the stage `--themes auto` picks); golden-PNG comparison with a tolerance only at milestones (`FULL`) | pytest marker `visual`; goldens pinned to one OS (Windows, the primary target); the other OSes run only the numeric metrics, which don't depend on fonts | yes — xdist; CI runs it as its own job, parallel to the test matrix |
| 4. Interactive | `dev_smoke/interactive/` checklists + a Weave canvas check | manual, once per track and once before release | per track, by whoever owns it |

CI (`.github/workflows/publish.yml`) after Phase 0: `lint` ∥ `test` matrix (3 OS × 4 Python,
`-n auto`) ∥ `smoke` (Ubuntu + Windows, `--jobs auto`) ∥ `visual` (Windows, uploads diff images
as artifacts on failure). All four run concurrently; `build` needs all of them.

---

# Phase 0 — Baseline & test infrastructure

**Files:** `pyproject.toml`, `.github/workflows/publish.yml`, `dev_smoke/run_all.py`,
`tests/conftest.py`, `tests/visual/` (new), `tests/baselines/` (new)
**Risk:** Low — no library code changes

## Deliverables

1. **Dev dependencies.** Add an optional `[project.optional-dependencies] dev` group:
   `pytest`, `pytest-xdist`, `hypothesis`, `ruff`. CI installs `.[dev]`.
2. **Parallel unit tests.** Verify `pytest -n auto` is green and gives the same count as the
   serial run. Any test that shares on-disk state (temp theme dirs, screenshots) moves to
   `tmp_path`.
3. **Parallel smoke runner.** `run_all.py --jobs N` (default: CPU count), using
   `concurrent.futures.ProcessPoolExecutor` or plain `subprocess.Popen` batches. Output is buffered
   per check and printed in `CHECKS` order, so logs stay readable. The unlisted-script guard stays.
4. **Theme sets.** `tests/theme_sets.py` with `QUICK` (5), `REGULAR` (11), `FULL` (20) and
   `ALL` (36), plus `tests/select_theme_set.py` for `--themes auto`, plus
   the ten `tests/fixtures/themes/kilim_*.json` files. Pytest gets a
   `--themes {quick,regular,full,all,auto}` option (default `auto`); `run_all.py` and
   `screenshot_themes.py` accept the same flag.
5. **Token snapshot (M0).** `tests/baselines/theme_tokens_0.7.6.json`: every derived token of
   `ALL`, dumped via `deep_to_serializable(build_theme(spec))`. Phase 2's drift report measures
   against it. Each run compares the themes of its stage (5 or 11) against it; milestones compare
   all 36.
6. **Screenshot baseline (M0).** `dev_smoke/screenshot_themes.py` reads its list from
   `theme_sets.py` instead of its own hard-coded 14. Save a 0.7.6 set for `FULL` once, as the
   before images for the milestone comparisons.
7. **Zoom harness** (`tests/visual/zoom_harness.py`). Places a `QComboBox`, `QSpinBox`,
   `QDoubleSpinBox`, `QCheckBox`, `QRadioButton`, `QScrollBar` (both orientations), `QSlider`,
   `QTreeView` branch arrows and a `QMenu` submenu arrow in a `QGraphicsScene` via
   `QGraphicsProxyWidget`. Renders the view at 1×, 2× and 4× into a `QImage` and computes a
   **sharpness metric**: the mean width, in device pixels, of the intensity transition across
   each glyph's edges. A vector glyph stays about 1–1.5 px wide at any zoom; a stretched bitmap
   grows roughly with the zoom factor. Runs under two themes only, `kilim_dark` and
   `kilim_light_neo`: sharpness doesn't depend on the palette beyond light vs dark.
8. **Corner harness** (`tests/visual/corner_harness.py`). Builds a docked `DockWidget` whose
   content is a solid-colour `QFrame` in pure magenta (no theme in either set uses it). Renders it
   under every regular theme with a non-zero radius (`kilim_dark`, `kilim_midnight_neo`,
   `kilim_light_neo`, `cyberpunk_neon`, `slate_amber`, `solarized_light`) and checks each corner:
   - **leak:** no pixel outside the rounded outline contains magenta
   - **staircase:** along the arc, alpha takes intermediate values (anti-aliasing) instead of
     jumping from 0 to 255
9. **Record the baseline.** Test count and runtime (serial and `-n auto`), smoke pass list,
   sharpness numbers for Fusion at 4×, corner-harness results. Both harnesses are *expected to
   fail* on 0.7.6; that is what Phases 4 and 5 fix. Mark those checks `xfail(strict=True)` so they
   flip visibly.

## Exit criteria
- `pytest -n auto` green, same count as serial
- `run_all.py --jobs auto` green, wall-clock time recorded
- CI runs lint ∥ test ∥ smoke ∥ visual concurrently
- Baseline numbers written to the top of this file

---

# Phase 1 — Colour engine (Track A)

**Files:** `lace/color_science.py` (new), `tests/test_color_science.py` (new)
**Risk:** Low — pure functions, nothing calls them yet

## Goal
One place that knows how to lighten, darken, mix and check colours, in a space where equal steps
look equal.

## API

```python
# All take/return [r, g, b, a] lists (0..255) — the format the theme builder already uses.
to_oklch(rgba) -> (L, C, h, a)            # L 0..1, C chroma, h degrees
from_oklch(L, C, h, a) -> rgba             # gamut-mapped: reduce chroma until in sRGB
relative_luminance(rgba) -> float          # WCAG 2.x
contrast_ratio(fg, bg) -> float            # composites fg over bg first if fg.a < 255
is_dark(rgba) -> bool                      # OKLCH L < 0.6 (replaces hand-set is_light)
step(rgba, dL, *, toward=None) -> rgba     # perceptual lightness step, hue and chroma kept
                                           # toward="contrast" picks direction away from itself
mix(a, b, t) -> rgba                       # OKLab interpolation
ensure_contrast(fg, bg, ratio) -> rgba     # smallest L shift of fg meeting ratio against bg;
                                           # falls back to the best reachable if impossible
on_color(bg, *, prefer=None) -> rgba       # readable text for bg: max contrast of the
                                           # theme's light/dark text, not a fixed 0.4 cutoff
```

## Tests (unit, parallel)
- Round-trip `rgba → oklch → rgba` within ±1 per channel for the 16.7 M sRGB cube, sampled
  (hypothesis)
- `contrast_ratio` matches the WCAG reference values for known pairs (black/white = 21, etc.)
- **Properties (hypothesis):** `ensure_contrast` output meets the ratio whenever it is reachable;
  never moves hue by more than 2°; returns `fg` unchanged if it already passes
- `step` is monotonic in `dL`; the same `dL` produces perceptually similar ΔE on grey, blue,
  yellow bases (spread < 25 %)
- `on_color` gives ≥ 4.5 : 1 on every accent in `ALL` (pure numbers, so the whole set is cheap)

## Exit criteria
Module is at 100 % line coverage; nothing outside tests imports it yet.

---

# Phase 2 — Theme derivation & keywords (Track A)

**Files:** `lace/dock_theme.py`, `lace/theme_models.py`, `lace/dock_custom_theme.py`,
`tests/test_theme_engine.py`, `tests/test_theme_contrast.py` (new),
`dev_smoke/smoke_theme_palette.py`
**Risk:** High — changes the colour of every preset. Controlled by the drift report.

## Changes
1. **One stepping function.** `_adjust_color` (HLS), `_contrasting_hover`, `_contrast_step` and
   the `QColor.lighter()/darker()` fallbacks in `_resolve_uncached` all route through
   `color_science.step` / `mix`. The HLS helper stays only as a private shim if something
   external imports it.
2. **Auto light/dark.** `ThemeSpec.is_light` becomes `Optional[bool] = None`; `None` means
   `is_dark(base)`. Presets that set it keep their value.
3. **`depth` keyword.** A table of OKLCH ΔL per surface replaces the scattered constants:

   | Surface (off base) | `flat` | `subtle` | `raised` |
   |---|---|---|---|
   | panel | 0.03 | 0.05 | 0.08 |
   | border | 0.04 | 0.06 | 0.09 |
   | title bar (off panel, sign from `title_mode`) | 0.03 | 0.05 | 0.07 |
   | tooltip (off panel) | 0.05 | 0.08 | 0.11 |
   | input (off panel, recessed) | 0.02 | 0.035 | 0.05 |
   | zebra row (off input) | 0.03 | 0.05 | 0.07 |
   | button (off panel) | 0.04 | 0.07 | 0.10 |
   | hover (toward contrast; ×0.7 for `hover_mode="darker"`) | 0.06 | 0.09 | 0.12 |
   | bevel light / mid / dark | .09/.03/.08 | .13/.045/.11 | .17/.06/.14 |

   *As built:* calibrated against the Phase 0 snapshot so `subtle` matches the median 0.7.6
   steps (`_DEPTH` in `dock_theme.py`). Derived surfaces then have to clear a lightness
   separation floor from their parent (`SEPARATION_TARGETS`: surface .012 / .02 / .035, hover
   .03 / .04 / .06), which is what lifts the crushed title bars on the darkest themes.

   *Canvas touch rule* (`TOUCH_PAIRS`, `TOUCH_TARGETS`): a derived title bar or input also
   keeps ΔL 0.008 / 0.012 / 0.02 off the canvas, since it touches it in dock gaps and at card
   edges (midnight's input sat at ΔL 0.001). It only moves *further from its own panel*, never
   flips across the panel or the canvas, and colours the theme sets itself are left alone; with
   no room, it is reported as unreachable. 16 of 36 presets move, each by ΔE ≤ 0.027.
   A stricter version (a WCAG 1.10:1 floor on every touching pair, surfaces allowed to cross the
   panel, borders up to ΔE 0.12) was tried and reverted: it separated everything, but flipped
   title bars and inputs to the wrong side of the panel on too many themes.
4. **`contrast` keyword.** After derivation, text tokens pass through
   `ensure_contrast(token, surface, target)` against the surface they are drawn on (tab text
   against tab bg, title text against title bg, etc.), using the targets table above.
5. **Accent handling.** `_accent_bright` becomes "accent stepped *toward contrast* with the
   canvas" rather than always +0.15 L, so light themes get a darker, more visible focus colour.
   The focus border is checked against the non-text UI target.
6. **`selection` keyword.** `solid`: Highlight = accent, HighlightedText = `on_color(accent)`.
   `tint`: Highlight = accent at alpha ≈ 0.28 composited over the input bg, HighlightedText =
   text, checked for contrast.
7. **Schema.** `ThemeSpec` gains `contrast`, `depth` and `selection` (Phase 4 and 5 add
   `scrollbar` and `corner_clip`); `ThemeJson` mirrors them with `Literal[...]` validation.

## Drift budget
A report script (`dev_smoke/theme_drift.py`) compares every token of every preset with the
Phase 0 snapshot, as ΔE (OKLab). Budget (revised during the phase, to fix themes that were
unreadable as authored, e.g. `kilim_midnight_neo`):
- **explicitly set colours:** ΔE ≤ 0.04 (`EXPLICIT_MAX_DE`, cumulative from the spec value), and
  only when the move improves the contrast or separation rule the colour fails. A colour that
  already passes is untouched. One that stops at the cap short of its floor is reported as
  *capped*, not failed: the author's choice wins over the rule
- **derived colours:** ΔE ≤ 0.15 (`DERIVED_MAX_DE`); the OKLCH steps replace HLS ones, so these
  move more than the original 0.02 estimate
- **text tokens:** move as far as their contrast floor needs; listed per token by `--detail`
- a floor no colour reaches on the theme's own surface (a mid-tone title bar, or a shared
  colour drawn on two surfaces that need opposite ends) is flagged *unreachable* and reported

Enforcement (`lace/theme_contrast.py`, `enforce`) separates surfaces first, then fixes
foregrounds against the final surfaces. A colour list shared by several tokens is fixed against
every surface it is drawn on.

*Status at M1:* all 36 themes within budget; 36 capped or unreachable floors reported (mostly
explicit borders and focus rings, and the Solarized text colours).

## Tests
- **Unit, parallel:** every `REGULAR` theme × every `contrast` level meets every target in the
  table (11 × 3 parametrised cases); explicit colours pass through unchanged; `is_light=None`
  agrees with the old hand-set flag for every `REGULAR` theme. The same tests run over `ALL` at
  milestone M1
- **Properties (hypothesis):** random `base`/`accent`/`text` triples always produce a theme that
  meets `normal` targets, or every miss is an explicit colour at its cap or flagged
  unreachable (`audit` names the token)
- **JSON:** a theme with the new keywords round-trips through `ThemeJson`; invalid values raise
  `ValidationError`
- **Smoke:** `smoke_theme_palette.py` extended to assert the contrast table on a live window;
  `smoke_themeswitch.py` covers `REGULAR` × the three `contrast` levels
- **Visual (M1):** `FULL` screenshots regenerated (`screenshots/m1_0.8/`) and paired with the
  0.7.6 set by `dev_smoke/pair_screenshots.py` (`screenshots/m1_pairs/index.html`) for review

## Exit criteria
Milestone M1 passed: drift report within budget over `ALL`, contrast table green over `ALL`,
`FULL` screenshots reviewed; no change to any file outside
Track A's list.

---

# Phase 3 — Complete QPalette (Track A)

**Files:** `lace/dock_theme.py` (`DockThemeColors`, `build_dock_palette`),
`tests/test_palette_complete.py` (new)
**Risk:** Low

## Changes
- Set every `QPalette.ColorRole` in every `ColorGroup` (Active, Inactive, Disabled):
  add `Midlight`, `BrightText`, `Accent` (Qt ≥ 6.6, guarded), `NoRole` left alone
- **Disabled group:** `Base`, `Button`, `Window`, `Highlight` and `Accent` get muted values
  (mixed toward the surface), not just the text roles
- **Inactive group:** `Highlight` falls back to a desaturated accent when the window loses focus,
  like native Windows 11 and macOS
- `Light` / `Mid` / `Dark` / `Shadow` derived with `depth` so Fusion's frames and
  `LaceStyle`'s borders agree

## Tests
- **Unit:** for each `REGULAR` theme, every role × group is set explicitly (compare against a
  default-constructed `QPalette`) and disabled text meets the disabled target against the
  disabled `Base`/`Button`
- **Smoke:** a disabled `QLineEdit`, `QPushButton`, `QComboBox` on a live window read the expected
  palette colours

---

# Phase 4 — LaceStyle: a modern, clean Fusion (Track B)

**Files:** `lace/lace_style.py` (new, the `QProxyStyle` and its dispatch table),
`lace/style/` (new package: `_paint.py`, `_primitives.py`, `_buttons.py`, `_inputs.py`,
`_range.py`, `_containers.py`), `lace/dock_theme_bridge.py`, `lace/__init__.py`,
`tests/test_lace_style.py`, `tests/visual/`
**Risk:** Medium-high — every standard widget in the host app changes look. Sizes don't change.

## Direction

A modernised, cleaner Fusion — not a copy of a native style. Fusion stays the base for two
reasons: it lays out identically on every OS, and it reads **every** `QPalette` role, so a
complete palette (Phase 3) reaches every control. LaceStyle keeps both properties and replaces
only the dated drawing.

| Fusion today | LaceStyle |
|---|---|
| Vertical gradients on buttons, headers, tabs, scrollbar handles, progress bars | Flat fills; state shown by a lightness step, not a gradient |
| Bevel and shadow lines (`Light` / `Dark` / `Shadow` edges) | One 1 px stroke, mixed from `Text` over the control's fill at low alpha, so it follows every theme |
| Mixed radii (2–3 px, some square) | One `control_radius` (default 4, matching the classic dock chassis) on every control |
| Dotted or pale focus rectangle | 2 px accent focus ring, drawn outside the control's stroke |
| Accent used on few states | Accent used only for state: checked, focused, selected, progress/slider fill, default button |
| Step buttons and ridged handle on scrollbars | Thin scrollbar, rounded handle, no step buttons |
| Arrows and marks drawn partly from cached pixmaps | Every glyph a vector path; nothing cached as a pixmap |
| Striped / chunked progress bar | Flat rounded track with a rounded accent fill |

## Rules
- **Sizes stay Fusion's.** `pixelMetric`, `sizeFromContents` and `subControlRect` are passed
  through, with one exception: the scrollbar extent in `thin` / `expanding` mode. Host layouts
  and Weave's canvas nodes therefore don't reflow.
- **Colours only from `option.palette`**, through a small set of helpers in `style/_paint.py`
  (`fill(role, state)`, `stroke(option)`, `focus_ring(option)`, `accent(option)`). Anything not
  overridden falls through to Fusion, which reads the same palette, so the controls LaceStyle
  doesn't touch (`QDial`, `QCalendarWidget`, MDI) still match.
- **Vector only.** Every override paints `QPainterPath`s under the painter's current transform.
  That is what keeps it sharp in a zoomed `QGraphicsProxyWidget`.
- **Theme knobs** reach the style through `LaceStyle.set_tokens(control_radius, scrollbar)`,
  which `DockThemeBridge` calls on each theme change. Standalone use (no Lace theme) gets the
  defaults.
- `DockThemeBridge(style_name=None)` installs `LaceStyle`; `style_name="Fusion"` keeps stock
  Fusion; `""` still skips. `LaceStyle` is exported, so Weave can set it on its own
  `QApplication` or a single canvas.

## Sub-phases and parallel work

4a lands first because every family uses its helpers and because it contains the Weave zoom fix.
After 4a, the four families are independent: each lives in its own module under `lace/style/`,
so they can be built in parallel worktrees and merged in any order without conflicts.

```
4a  Primitives & shared helpers ──┬── 4b-1 Buttons
                                  ├── 4b-2 Inputs
                                  ├── 4b-3 Range controls
                                  └── 4b-4 Containers, menus & item views
```

| Sub-phase | Elements | Look |
|---|---|---|
| **4a Primitives** | `PE_IndicatorArrow*`, `PE_IndicatorSpin*`, `PE_IndicatorBranch`, `PE_IndicatorCheckBox`, `PE_IndicatorRadioButton`, `PE_IndicatorItemViewItemCheck`, `PE_IndicatorMenuCheckMark`, `PE_FrameFocusRect`, `CC_ScrollBar`, `PE_Frame`, `PE_FrameLineEdit` | chevrons 1.5 px with round caps; check box rounded square filled with the accent when checked, check mark in `on_color`; radio a circle with an accent dot; focus ring; scrollbars `thin` (8 px) / `expanding` (4 → 10 px on hover, `QVariantAnimation`) / `fusion` |
| **4b-1 Buttons** | `PE_PanelButtonCommand`, `CE_PushButtonBevel`, `PE_PanelButtonTool`, `CC_ToolButton`, `PE_IndicatorButtonDropDown` | flat rounded face, 1 px stroke; hover and pressed as lightness steps; default button filled with the accent; auto-raise tool buttons show a fill only on hover |
| **4b-2 Inputs** | `PE_PanelLineEdit`, `CC_ComboBox`, `CC_SpinBox`, `PE_FrameLineEdit` (text edits, plain text edits) | recessed `Base` fill, 1 px stroke, accent stroke on focus; combo and spin boxes as one rounded field with the buttons drawn inside it, no separator bevels |
| **4b-3 Range** | `CC_Slider`, `CE_ProgressBarGroove`, `CE_ProgressBarContents`, `CE_ProgressBarLabel` | slider: 4 px rounded groove, accent fill up to the handle, round handle with a stroke; progress bar: rounded track, rounded accent fill, busy state as a sliding segment |
| **4b-4 Containers** | `CE_TabBarTabShape`, `PE_FrameTabWidget`, `PE_FrameTabBarBase`, `CC_GroupBox`, `CE_HeaderSection`, `PE_PanelMenu`, `CE_MenuItem`, `CE_MenuBarItem`, `PE_PanelItemViewItem`, `PE_PanelTipLabel`, `CE_ToolBoxTabShape` | tabs: flat, selected tab on the panel colour with an accent strip (matching Lace's dock tabs); group boxes: rounded frame, title in muted text; headers: flat with a single divider; menus: rounded, inset hover highlight; item views: rounded inset selection and hover; tooltips: rounded |

Menus are top-level popups, so rounding their outer corners needs a translucent window. 4b-4
rounds the item highlights; the outer popup corners are rounded only where the platform supports
translucent popups, and stay square otherwise.

## Tests

**Control gallery** (`tests/visual/gallery.py`, built in 4a and extended by each family): every
overridden control in every state — normal, hover, pressed, focused, checked, disabled — drawn by
calling the style directly with forced `QStyle.State` flags, so no event simulation is needed and
renders are deterministic.

Per sub-phase, all parallel under xdist:

| Check | Themes | Applies to |
|---|---|---|
| **No reflow:** `sizeHint()` of every gallery control equals stock Fusion's | one theme (metrics don't depend on colour) | all |
| **Flat:** each control face, excluding its antialiased edge, has one fill colour (no gradient) | `QUICK` per family PR; `REGULAR` at the end of Phase 4 | 4b-* |
| **Contrast:** stroke vs surface, focus ring vs surface, check mark vs accent fill, disabled text vs disabled fill, all against the Phase 2 targets | `REGULAR` for 4a (shared helpers); `QUICK` per family PR; `REGULAR` at the end of Phase 4 | all |
| **Sharpness:** every overridden glyph ≤ 1.6 px edge width at 4× zoom (Phase 0 xfails flip to pass) | `kilim_dark`, `kilim_light_neo` | 4a, and each family's glyphs |
| **Fall-through:** `QDial`, `QCalendarWidget`, `QMdiArea` render under LaceStyle with no warnings | `kilim_dark` | 4a |
| **Scrollbar modes:** extent per mode; `fusion` mode matches stock Fusion pixel for pixel | `kilim_dark` | 4a |
| **Ownership:** the bridge keeps the style alive; deleting the bridge leaves no dangling style | — | 4a |

**Visual review per sub-phase** (small, by design): the gallery for that family only, under
`kilim_dark` and `kilim_light_neo`, side by side with stock Fusion — one image per theme. The full
gallery × `FULL` set is reviewed only at milestone M2.

**Smoke:** `smoke_lace_style.py` (new) builds the demo, applies every theme of the selected stage (`--themes auto`) under
LaceStyle, grabs one frame each, and fails on any Qt warning.

**Interactive:** `S5_style_checklist.md` — hover, press, focus and keyboard navigation for each
family in the demo; Weave canvas at 100 %, 200 % and 400 % zoom with every family on a node.

## 4a status

Landed: `LaceStyle` (`lace/lace_style.py`), `lace/style/_paint.py`, `lace/style/_primitives.py`,
the gallery, `tests/test_lace_style.py`. `DockThemeBridge(style_name=None)` installs it, parented
to the target; the demos call `app.setStyle(LaceStyle())`. The knobs `scrollbar`, `control_radius`
and `contrast` live on `ThemeSpec` / `ThemeJson` and in the CORE tokens. Non-text UI (indicator
outlines, focus ring, scrollbar handle) is held to the theme's `ui` target against the window,
frames to `border`. The focus ring shows on keyboard focus only, as in Fusion.

**Zoom harness corrected.** It stretched the render into an image 1 px larger than `src * zoom`,
putting every edge on a fractional pixel, and it counted ramp width along rows and columns only, so
a perfectly sharp diagonal read 3 px. Edges are now measured as the 10–90 % rise across each edge
(the shorter of the row and column ramp). Stretched pixmaps still read 3.5–6 px, vectors ≤ 2:

| Glyph (4x, kilim_dark / kilim_light_neo) | Fusion | LaceStyle |
|---|---|---|
| check indicator | 1.83 / 1.78 | 1.98 / 1.94 |
| radio indicator | 3.15 / 2.16 | 1.81 / 1.80 |
| scrollbar h / v | 3.68 / 2.46 | 1.27 / 1.27 |
| tree branch | 5.95 / 5.82 | 1.91 / 1.88 |
| menu submenu arrow | 5.56 / 3.54 | 1.92 / 1.50 |
| slider handle (Fusion vector, already sharp) | 1.57 / 1.28 | unchanged |
| combo / spin arrows (4b-2) | 4.6–5.3 | unchanged, still xfail |

Still to do for 4a exit: the Weave zoom check by hand (S5 section 8). `smoke_lace_style.py`
landed with 4b.

**Limit raised to 2.5 (4b-2).** Under the 10–90 % measure a perfectly sharp edge reads 1 on the
pixel grid and 2 off it, so vector glyphs with diagonals average 1.8–2.2 and sat right on the old
2.0 limit (the spin chevrons read 2.21). A stretched 1x pixmap reads 3.5 and up; 2.5 splits the
two. With 4b-2 the combo and spin arrows read 1.8–2.2 (Fusion: 4.6–5.8) and no glyph is xfail.

## 4b status

- **4b-1 Buttons** — done. `PE_PanelButtonCommand` carries every Fusion button face (push, tool,
  non-editable combo), so one override covers them; keyboard focus rings the face.
- **4b-2 Inputs** — done. Line edits, combo and spin boxes as one rounded field with vector
  chevrons inside; Fusion's spin/combo sub-control rects are kept.
- **4b-3 Range** — done (`lace/style/_range.py`). Slider groove, accent fill
  and round handle; tick marks drawn flat. Progress track and fill rounded;
  the busy segment animates only on a visible widget and rests mid-track
  otherwise, so renders are deterministic. `CE_ProgressBarLabel` stays Fusion's.
- **4b-4 Containers** — done (`lace/style/_containers.py`). Tabs: bare at
  rest, a hover wash, the selected tab filled with an accent underline on the
  pane edge (all four shapes). Tab-widget and group-box frames reuse the
  rounded `frame`; the tab-bar base is a 1 px line. Header sections are flat
  Button fills with a separator and a vector sort chevron. Menus: a square
  popup with a 1 px line, rounded Highlight on the selected item (Fusion's own
  fill is suppressed by a transparent Highlight), flat separators; checks in
  menus are bare ticks / dots, detected by the `QMenu` widget because Fusion
  routes them through `PE_IndicatorCheckBox` / `PE_IndicatorRadioButton`.
  Menu bar items draw their own label, since Fusion's fill would cover the
  selection. Item views: flat Highlight, faint hover wash, square rows so
  columns join. Tooltips: flat ToolTipBase with a line, rounded by
  `scaled_radius` (shared with check boxes) on one line's height; the tip
  window is masked to the shape from the paint call, because PySide can't
  fill `SH_ToolTip_Mask`'s return data. Tool box tabs: rounded Button faces.
- **Smoke and S5** — `dev_smoke/smoke_lace_style.py` (in `run_all.py`) builds
  the demo and `dev_smoke/interactive/style_showcase.py` (every family on live
  widgets, plus a `--zoom` QGraphicsView), grabs a frame per theme of the
  stage, switches the tokens live, opens a menu, a tooltip (checks its mask),
  the busy progress and keyboard focus, and fails on any Qt warning. Offscreen
  platform messages are listed with their reasons; native runs are clean.
  `S5_style_checklist.md` covers the rest by hand — to be signed off, along
  with the Weave zoom check.

## Exit criteria
- 4a: zoom metrics pass, no reflow, scrollbar modes verified, Weave zoom checked by hand
- each 4b family: flat and contrast checks green over `QUICK`, no reflow, its gallery images
  reviewed, its part of S5 signed off
- end of Phase 4: flat and contrast checks green over `REGULAR` for all families together —
  **done**: `tests/test_lace_style_sweep.py` (every family's surface flat in normal / hover /
  pressed; outlines, focus outline, selected-tab underline, check mark and disabled text against
  their targets at all three contrast levels) passes over `REGULAR`, 803 style tests in all.
  Disabled outlines keep `min(own target, 1.5)`, so a disabled field stays at the border target
  rather than outdoing an enabled one.

---

# Phase 5 — Rounded content (Track C)

**Files:** `lace/dock_chrome.py`, `lace/dock_widget.py`, `lace/dock_area_widget.py`,
`lace/floating_behaviour.py`, `lace/dock_paint.py`, `tests/visual/test_corner_clip.py`,
`tests/test_corner_modes.py` (new)
**Risk:** Medium — changes the widget stacking order inside every dock area

## Changes
1. **Corner cap.** `_ChromeBorderOverlay` (already above the content) first fills the region
   *between the widget rect and the rounded outline* with the backdrop colour, antialiased, then
   strokes the border as it does today. Computed as `QPainterPath(rect) - rounded_path`, cached per
   size and radius.
2. **Backdrop colour.** Whatever sits behind the card: `CORE.canvas_bg` for docked areas, the
   sidebar panel for sidebar content. Resolved by a new `ChromeFrame.chrome_backdrop()`, so nested
   cases resolve to their real parent colour.
3. **Masks removed** from docked content (`DockWidget._apply_bottom_mask` and the `_mask_*`
   caches). Floating windows keep a mask only when they are *not* translucent; translucent
   frameless floats already get true per-pixel alpha from the window, so they need neither.
4. **`corner_clip` keyword.**
   - `cap` (default): as above; content fills to the edge
   - `inset`: layout margins grow to `chrome_content_margin()` so square content never reaches the
     arc; no cap needed
   - `none`: no cap and no inset, for apps that round their own content
5. **Overlay stacking.** The overlay is re-raised after every content change (`set_widget`,
   tab switch, restore from layout), and on `ChildAdded` events, so user widgets inserted later
   can't end up above it.
6. **Title bar top corners** get the same treatment when `title_margin = 0`, so a flush title bar
   with a custom background can't square off the card's top corners.

## Tests
- **Visual, parallel:** corner harness across `corner_radius ∈ {0, 4, 10, 16}` ×
  `border_width ∈ {0, 1, 1.5, 2}` × `corner_clip ∈ {cap, inset}`: no leak, anti-aliased arc
  (Phase 0 xfails flip to pass)
- **Visual:** child with its own 1 px frame (`QTextEdit`), a scroll area with both scrollbars
  showing, and a `QTableView` with gridlines — nothing extends past the outline at any corner
- **Unit:** the overlay is the top child after `set_widget`, tab switch, layout restore and a
  late `addWidget` into user content; `corner_clip="none"` creates no cap path
- **Unit:** no `setMask` on docked content (patch `QWidget.setMask` and assert it isn't called)
- **Smoke:** `smoke_corner_clip.py` (new) toggles the three modes on a populated window and checks
  layout margins
- **Interactive:** resize a rounded area while a `QOpenGLWidget` / `QWebEngineView` is inside
  (overlays above native child windows are the known risk — see
  `docs/frameless-webengine-findings.md`). If a native child can't be covered, that dock area falls
  back to `inset` automatically and logs it once.

## Status

Done, except the native-child check by hand.

- **Two caps, both painted with Source composition** (`dock_paint.paint_corner_cap`), so a
  transparent backdrop clears rather than leaves the corner:
  - The dock area's `_ChromeBorderOverlay` caps everything outside the card's outer edge, then
    strokes the outline. It sits above the title bar, which covers item 6 without extra code.
  - Each `DockWidget` owns a `CornerCap` overlay in place of its old `QRegion` mask. It has the
    same shape (the content's bottom arc: card radius less the border and the bottom margin) but
    is antialiased. This also covers sidebar content, whose backdrop is the sidebar panel.
- **Backdrop** comes from `backdrop_color(widget)`: the nearest ancestor's `chrome_fill()`, else
  the nearest auto-filling ancestor or window, else transparent for a translucent window.
  `ChromeFrame.chrome_backdrop()` wraps it.
- **Modes:** `corner_clip` is on `ThemeSpec`, `ThemeJson` (`Literal`) and CORE.
  - `inset` grows the DockWidget's left, right and bottom margins to
    `chrome_content_margin - border`.
  - `none` paints no cap.
  - Content holding a native child window falls back to `inset`, logged once per widget.
- **Floating windows are unchanged.** A chromeless float keeps its mask: in a translucent window
  the float's own dock container paints the canvas into the corners, so dropping the mask would
  square them off.
- **Tests:**
  - `tests/visual/test_corner_clip.py`: 6 themes plus `flush_r10`, × 4 content kinds (frame,
    `QTextEdit`, a scroll area with both bars, a gridded `QTableView`), and the 32-case grid
    (radius × border × cap/inset). The harness also counts any non-backdrop pixel outside the
    outline, which catches child frame lines that magenta alone misses. The Phase 0 xfails are
    gone.
  - `tests/test_corner_modes.py`: overlays on top after `set_widget`, tab switch, restore and a
    late child; no `setMask`; `cap` / `inset` / `none`; the native fallback.
  - `dev_smoke/smoke_corner_clip.py` runs the three modes on the demo.

## Exit criteria
Corner metrics pass; no masks on docked content; native-child fallback verified by hand.

---

# Phase K1 — Theme kit: library & CLI (Track D)

**Precondition:** Phase 2 merged (colour engine + keyword derivation)
**Runs in parallel with:** Phase 3, Phase 4, Phase 5
**Files:** `lace/theme_kit/` (new package: `__init__.py`, `derive.py`, `audit.py`, `family.py`,
`chassis.py`, `export.py`, `__main__.py`), `tests/test_theme_kit.py`
**Risk:** Low — new code that only reads the engine; no existing theme changes

## Goal
Make a new theme a matter of choosing a few seed colours and a look, then checking the result,
instead of hand-tuning 40 tokens. The same tools also check and extend the existing presets
(Phase 6 uses them for the retune).

## A theme = palette + chassis

Today every preset repeats its geometry, and Kilim already factors it out by hand
(`KILIM_GEOMETRY`, `KILIM_NEO_GEOMETRY`). The kit makes that split official:

- **Palette:** the seed colours plus the colour keywords (`contrast`, `depth`, `selection`,
  `title_mode`, `hover_mode`).
- **Chassis:** a named bundle of geometry and styling tokens: radii, border widths, title bar
  layout, tab and sidebar-tab treatment, indicators, `control_radius`, `scrollbar`,
  `corner_clip`.

Chassis extracted from the current presets:

| Chassis | Taken from | Look |
|---|---|---|
| `classic` | `dark`, Kilim classic | 4 px, 1.5 px border, inset title bar |
| `flat` | `nordic`, `solarized_*` | 4 px, no border |
| `square` | `midnight` | 0 px, 0.5 px hairline |
| `edge` | `cyberpunk_edge*`, Kilim neo | 10 px, flush title bar, 1.5 px rule, ringed sidebar tabs |
| `haze` | `violet_haze*`, `midnight_haze*` | 10 px, 2 px frame starting below the title bar, tab outlines |
| `neon` | `cyberpunk_neon` | 10 px, glowing border, pill sidebar tabs |

`compose(palette, chassis="classic", **overrides) -> ThemeSpec`. Overrides win, so any
single token can still be set by hand.

## API

```python
from lace.theme_kit import derive, audit, family, status_colors, compose, export

# 1. Derive: two seeds are enough; text comes from on_color(base) if omitted
pal = derive(base="#1b1d23", accent="#4f8cff", contrast="normal", depth="subtle")

# 2. Compose with a chassis
spec = compose(pal, chassis="edge", title_mode="darker")

# 3. Audit: every token pair that is drawn on top of another, checked against the targets
report = audit(spec)            # -> AuditReport
report.failures                 # [(token, surface, ratio, target), ...]
report.suggest()                # smallest change that fixes each failure (OKLCH lightness only)

# 4. Family: light / neutral / dark counterparts with the same hue and chassis
fam = family(spec)              # {"dark": ..., "neutral": ..., "light": ...}

# 5. Status colours harmonised to the palette
status_colors(pal)              # success / warning / error / info at matching lightness and contrast

# 6. Export
export.to_json(spec, "my_theme.json")     # loads with load_theme_json()
export.to_python(spec, name="my_theme")   # a ThemeSpec(...) literal for dock_custom_theme.py
export.diff(spec_a, spec_b)               # per-token ΔE, for reviews
```

What each part does:
- **`derive`:** fills in text from the base if missing, picks light/dark automatically, and runs
  the Phase 2 derivation. Can tint the neutrals slightly toward the accent hue
  (`neutral_tint=0..1`), the way `slate_amber` and `midnight_haze` were tuned by hand.
- **`audit`:** covers every text-on-surface and UI-on-surface pair Lace actually draws (tab text on
  tab, title text on title bar, check mark on accent, focus ring on panel, disabled text on
  disabled fill, …). It also flags surfaces too close to tell apart (ΔL below the `depth` step),
  an accent too close to the base, and colours that had to be clipped to fit sRGB.
- **`family`:** maps lightness while keeping hue and chroma, so dark ↔ neutral ↔ light variants
  come out consistent. This formalises how the `*_neutral` and `*_light` presets were made by hand.
- **`status_colors`:** keeps the conventional hues (green, amber, red, blue) and adjusts only
  lightness and chroma, so status colours read equally strong on the theme.

## CLI

```bash
python -m lace.theme_kit derive --base "#1b1d23" --accent "#4f8cff" --chassis edge --out my_theme.json
python -m lace.theme_kit audit my_theme.json
python -m lace.theme_kit family my_theme.json --out-dir themes/
python -m lace.theme_kit audit --preset slate_amber
```

`audit` exits non-zero when a target fails, so it can gate CI for a project's own theme files
(Kilim's, for example).

## Tests (QUICK stage; pure functions, parallel)
- **Properties (hypothesis):** for random base/accent seeds, `derive` + `compose` passes `audit`
  at the requested `contrast`, or `audit` reports exactly which target couldn't be reached
- **Family check against the hand-made presets:** `family(cyberpunk_edge)` reproduces
  `cyberpunk_edge_neutral` and `cyberpunk_edge_light` within a stated ΔE budget; the same for
  `violet_haze`, `midnight_haze` and `slate_amber`. This measures how close the kit gets to
  hand tuning. Presets it misses by a wide margin are listed, not forced to pass
- **Chassis round-trip:** `chassis_of(preset)` returns the closest chassis plus the overrides
  that preset needs (`neon_dusk`, for one, fits none exactly), and
  `compose(palette_of(preset), *chassis_of(preset))` rebuilds every preset's tokens exactly
- **Export round-trip:** `to_json` → `load_theme_json` → identical tokens; `to_python` output
  runs and builds the same theme
- **Audit agrees with Phase 2:** a preset that passes Phase 2's contrast table passes `audit`,
  and the reverse
- **CLI smoke:** each subcommand runs on a Kilim fixture and on `--preset slate_amber`; `audit`
  returns non-zero on a deliberately failing theme

## Status

Done. The API and CLI are documented in `docs/THEME_KIT.md`; the tests are in
`tests/test_theme_kit.py` (177 cases).

- **Chassis.** A seventh chassis, `stock` (nothing set), covers presets like `warm` and
  `dracula`. Chassis colour tokens are roles (`"focus"`, `"border"`, `"clear"`,
  `(role, alpha)`), so a chassis fits any palette.
  - `chassis_of` finds each chassis's source preset.
  - `neon_dusk` fits `haze` with 9 overrides.
  - `compose(palette_of(p), *chassis_of(p))` rebuilds all 36 themes token for token.
- **Audit.** `audit` uses the `lace.theme_contrast` rules. Its `failures` equal Phase 2's hard
  misses on all 36 themes. Two more lists sit beside them:
  - `capped`: the spec's own colours
  - `unreachable`
  
  Warnings cover a faint accent, a faint focus ring and colours clipped to fit sRGB.
  `suggest()` gives a fix that changes OKLCH lightness only.
- **Family.** Calibrated on the hand-made families. The mean ΔE per member against the hand
  presets:

  | Family | neutral | light |
  |---|---|---|
  | `cyberpunk_edge` | 0.052 | 0.057 |
  | `violet_haze` | 0.047 | 0.040 |
  | `midnight_haze` | 0.041 | 0.030 |
  | `slate_amber_dark` | 0.104 (listed miss) | 0.029 |

  The budget is 0.06. `slate_amber` is listed as a strict xfail: the kit's neutral sits at
  L 0.72, and `slate_amber` sits at 0.815.
- **Status colours.** One lightness and chroma for all four hues, at the "muted" floor.
- **Export.** `to_json` and `to_python` round-trip all 36 themes exactly. `diff` gives ΔE per
  token.
- **CLI.** Subcommands `derive`, `audit` (exits 1 on a miss, `--allow-capped`), `family` and
  `chassis`.

## Exit criteria
The API and CLI are documented; the family check reports on every hand-made family; the property
tests are green.

---

# Phase K2 — Theme Studio (Track D)

**Precondition:** K1, Phase 4a (control gallery), Phase 5 (corner cap)
**Runs in parallel with:** the Phase 4b control families
**Files:** `lace/theme_kit/studio.py` (new), `tests/test_theme_studio.py`
**Risk:** Low — a separate window built from existing parts

## What it is
A small window, launched with `python -m lace.theme_kit studio`, for building a theme by eye:

| Area | Contents |
|---|---|
| Inputs | Colour pickers for base, accent, text (optional), surface and border (optional); keyword drop-downs (`contrast`, `depth`, `selection`, `title_mode`, `hover_mode`); chassis picker; neutral-tint slider; "open preset / JSON" to start from an existing theme |
| Live preview | A small dock layout (two areas, tabs, a sidebar, a floating window) with the Phase 4 control gallery inside, all themed live. A zoom slider (100–400 %) previews the look inside a scaled canvas, as in Weave |
| Audit panel | The `audit` table with pass/fail per pair; clicking a failure applies its suggested fix |
| Family strip | The dark / neutral / light counterparts side by side, each openable for editing |
| Export | Save as JSON, copy as a `ThemeSpec(...)` literal, show a diff against the theme it started from |

The Studio installs its own `DockThemeBridge` on the preview only, so it doesn't restyle the host
app when launched from inside one.

## Tests (QUICK stage)
- **Smoke, offscreen:** open the Studio, set seeds, switch each keyword and chassis, apply a
  suggested fix, export JSON; the exported file loads and passes `audit`
- **Unit:** the preview's theme never leaks to the host application palette
- **Interactive:** `S7_studio_checklist.md` — build a theme from two seeds to a passing audit,
  generate its family, export, load it in the demo

## Exit criteria
The checklist is signed off; a theme made in the Studio loads unchanged in the demo and through
`load_theme_json()` in another app.

## Status

Done, except the S7 checklist by hand.

- **Isolation.** Lace's `DockStyleManager` is process-wide, and `DockManager` installs an
  app-wide bridge, so no in-process preview can leave a host's Lace widgets alone. From a host
  app, `studio.launch()` opens the Studio in a process of its own. Inside the Studio, its own
  panels carry a pinned copy of the app palette (every role set, so the resolve mask holds) and
  only the preview follows the theme.
- **Model.** `StudioModel` holds seeds, keywords, chassis and overrides, neutral tint, the
  palette extras a loaded theme set, and the applied fixes. Loading a preset and changing
  nothing gives the preset back token for token.
- **Click to fix.** `theme_kit.apply_fix(spec, suggestion)` finds the spec colour a suggestion
  came from by colour (ΔE ≤ 0.08, nearest first). It keeps the first one whose change clears the
  miss without adding one. A derived failure has no such colour, and the Studio says so.
- **Gallery.** It moved to `lace/style/gallery.py`, so the packaged Studio can show it;
  `tests/visual/gallery.py` keeps the command line. `render(..., scale=)` zooms through the
  painter transform, as a `QGraphicsView` does.
- **CLI.** `python -m lace.theme_kit studio [file | --preset NAME] [--screenshot PNG --tab N
  --zoom Z]`.
- **Tests.** `tests/test_theme_studio.py`:
  - model round trip on five presets
  - fix and seed behaviour
  - an offscreen run through every keyword and chassis, fixed to a strict pass, then exported
    and reloaded
  - the Studio's panels keep their palette
  - `launch()` leaves the host's palette, tooltip palette and manager generation unchanged
  - the CLI screenshot run

---

# Phase 6 — Integration & preset retune

**Precondition:** Tracks A, B, C, D merged into `dev_v08`
**Files:** `lace/dock_custom_theme.py`, `lace/dock_theme.py` (defaults only), tests, screenshots
**Risk:** Medium — the visible outcome of the release

## Work
1. **Full gate on the combined tree:** unit (`-n auto`), smoke (`--jobs auto`), visual, on all
   three OS in CI
2. **Cross-feature checks:**
   - LaceStyle scrollbars inside a `cap` corner: the handle stays inside the arc at the maximum
     radius shipped by any preset
   - `selection="tint"` with LaceStyle check marks and item views
   - `contrast="high"` with every `REGULAR` theme under LaceStyle
3. **Preset review (M2).** Walk the 20 `FULL` themes in the demo at `depth="subtle"`; set per-preset
   `depth`/`contrast`/`selection` only where the review calls for it. Use the theme kit for it:
   `audit` over `ALL` lists what fails; `family` regenerates the `*_neutral` / `*_light`
   counterparts where it beats the hand-tuned ones. Default theme becomes the
   "sleek" reference: `depth="subtle"`, `scrollbar="thin"`, `corner_clip="cap"`.
4. **Performance check.** Theme switch time and a paint benchmark (resize a 12-area layout 100×)
   within +10 % of the Phase 0 baseline. OKLCH derivation happens once per theme apply, not per
   paint.
5. **Deferred 0.7 items** (icon geometry: `pin`/`unpin` size, `close` stroke, SVG metadata) land
   here if time allows, since the icon plumbing is ready and LaceStyle sets the stroke weight
   the icons should match (1.5 px).

## Tests
- Visual (M2): `FULL` screenshot set; side-by-side 0.7.6 vs 0.8 grid
  (`screenshots/compare_grid.png`)
- Interactive: S1–S4 existing checklists re-run (no behavioural regressions from the overlay
  and style changes) plus S5 (style) and a new S6 (corners)

## Status
Done on the engineering side; the visual review (M2) and S1–S7 are for the user.
- **Gate:** 1582 unit tests pass (2 skipped, 1 xfail), with a `--themes all` sweep of 1896,
  visual tests (82), smoke and lint all green. CI on macOS had failed on a combo size hint: LaceStyle's
  scroll extent reached `QComboBox`. It is now limited to scroll bars and scroll areas.
- **Cross-feature** (`tests/test_cross_features.py`). The checks found three real bugs:
  - The item-view check on a `tint` selection used the Window colour as its surface (dracula 2.77:1).
    Primitives now judge legibility on Highlight when the item is selected.
  - The engine had no text-on-`button_bg` / `input_bg` pairs, so high contrast left
    button and field text short. Both pairs are now in `CONTRAST_PAIRS`.
  - `audit.suggest()` fixed one surface per token. It now groups misses by token.
  Explicit preset colours that cannot move far enough are reported as *capped*, never silently.
- **Default theme** is the sleek reference: subtle depth, thin scrollbars and `cap` corners,
  pinned by a test.
- **Audit over ALL:** no hard failures. The capped and warning items are all the presets' own
  colours: focus rings under 3:1 on dark, midnight, warm, monokai, nordic, catppuccin
  and solarized, accents under 3:1 on the `*_neutral` members and slate_amber, and dracula's
  tooltip at 6.48:1 at high contrast. Retuning these is a review decision.
- **Performance** (`dev_smoke/perf_bench.py`, best of 5, vs the 0.7.6 worktree):
  - Theme switch: 25.0 → 27.0 ms per theme (+8 %). Before the palette cache it was +47 %.
    `build_dock_palette` is now built once per colour snapshot.
  - Resize: 13.7 → 13.8 ms per frame (+1 %).
  - LaceStyle's colour derivations are memoised, so OKLCH runs once per colour, not per paint.
- **Screenshots:** `screenshots/m2_0.8/` (FULL set) and `screenshots/compare_grid.png` /
  `compare_grid_float.png` (`dev_smoke/compare_grid.py`).
- **Deferred icon items:** not done. They carry over to 0.8.x.

---

# Phase 7 — Docs, screenshots, release 0.8.0

- `docs/theming_and_geometry.md`: keyword reference, contrast table, corner modes, LaceStyle
  section with the Weave / `QGraphicsView` use case
- `docs/ARCHITECTURE.md`: `color_science`, `lace_style` and `theme_kit` in the module map
- `docs/theme_kit.md` (new): making a theme from two seeds with the API, the CLI and the Studio;
  the chassis list; how to audit a project's own theme files in CI
- README feature list and screenshots regenerated
- `CHANGELOG.md`: added / changed / removed, with the drift report summary
- Version bump to `0.8.0` in `pyproject.toml`, `lace/__init__.py`, README
  (`test_version_is_consistent` guards it)
- Tag `v0.8.0` → the existing workflow builds and publishes

---

## Risk register

| Risk | Where | Mitigation |
|---|---|---|
| Preset colours shift visibly | Phase 2 | Token snapshot + ΔE drift budget; explicit colours move ≤ ΔE 0.04 and only to improve readability |
| Host layouts reflow under LaceStyle | Phase 4 | Metrics stay Fusion's; `sizeHint` equality test over the whole control gallery |
| Restyle drifts into a native-style copy, or controls look inconsistent with each other | Phase 4b | One helper module (`style/_paint.py`) owns fills, strokes, focus and radius; families may not pick colours or radii of their own |
| Rounded menu popups need translucent windows, which not every platform supports | Phase 4b-4 | Round the item highlights everywhere; round the outer popup only where translucency works, square otherwise |
| Review load of a full restyle | Phase 4b | Per-family gallery under 2 themes only; full gallery × `FULL` only at M2 |
| Overlay can't cover native child windows (GL / WebEngine) | Phase 5 | Automatic `inset` fallback for areas holding a native child; manual check |
| Visual goldens flaky across OS / fonts | Phase 0 | Goldens on Windows only; numeric metrics (sharpness, corner leak) everywhere else |
| xdist exposes hidden test coupling | Phase 0 | Fixed in Phase 0 before any feature work, so later failures are real |
| Scope creep in the preset retune | Phase 6 | Keyword-level tweaks only; per-token overrides need a stated reason in the PR |

## Out of scope for 0.8
- Changing control sizes (a denser or roomier layout than Fusion's): it would reflow host apps
- Native OS styles (`windows11`, `macos`) as the base, or copying their look: they ignore parts
  of `QPalette`, which is the reason Lace uses Fusion. The target is a cleaner Fusion
- Restyling `QDial`, `QCalendarWidget` and MDI windows: they fall through to Fusion and still
  follow the palette
- Animated theme transitions
