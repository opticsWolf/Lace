# Theme kit

`lace.theme_kit` builds a Lace theme from a few seed colours and a look. It then checks the
result and derives the theme's dark, neutral and light counterparts. It only reads the theme
engine, so a theme made here is an ordinary `ThemeSpec` or JSON theme file.

## A theme = palette + chassis

- **Palette:** the seed colours (`base`, `accent`, `text`, and optionally `surface`, `border`,
  `title_bg`, `focus_border_color`, status and tooltip colours) and the colour keywords
  (`contrast`, `depth`, `selection`, `title_mode`, `hover_mode`).
- **Chassis:** everything else, which means geometry and styling: radii, border widths, title
  bar layout, tab and sidebar-tab treatment, indicators, `control_radius`, `scrollbar` and
  `corner_clip`.

| Chassis | Taken from | Look |
|---|---|---|
| `stock` | `warm`, `dracula`, … | Lace's default geometry, nothing set |
| `classic` | `dark`, `light`, `neutral`, Kilim classic | 4 px, 1.5 px border, inset title bar |
| `flat` | `nordic`, `solarized_*` | no border |
| `square` | `midnight` | square card, 0.5 px hairline |
| `edge` | `cyberpunk_edge*`, Kilim neo | 10 px, flush title bar with a 1.5 px rule, ringed sidebar tabs |
| `haze` | `violet_haze*`, `midnight_haze*` | 10 px, 2 px frame starting below the title bar, outlined tabs |
| `neon` | `cyberpunk_neon` | 10 px, glowing border, pill sidebar tabs |

A chassis writes its colour tokens as roles, so it fits any palette:
- `"focus"`: the palette's focus colour, or its accent when it has none
- `"accent"` and `"border"`: those palette colours
- `"clear"`: fully transparent
- `(role, alpha)`: a role at that alpha

## API

```python
from lace.theme_kit import derive, compose, audit, family, status_colors, export

pal = derive(base="#1b1d23", accent="#4f8cff")        # text picked for the base
pal = derive("#1b1d23", "#4f8cff", neutral_tint=0.4,  # neutrals leaned toward the accent hue
             contrast="high", status=True)            # + status colours

spec = compose(pal, chassis="edge", title_mode="darker")   # overrides win

report = audit(spec)             # at the spec's own contrast / depth, or pass them
report.passed                    # no derived colour misses a floor (= Phase 2's table)
report.strict_passed             # ... and neither do the spec's own colours
report.failures, report.capped, report.unreachable, report.warnings
report.suggest()                 # smallest OKLCH-lightness fix per miss
print("\n".join(report.lines()))

fam = family(spec)               # {"dark": ..., "neutral": ..., "light": ...}
status_colors(pal)               # {"success_color": ..., "warning_color": ..., ...}

export.to_json(spec, "my_theme.json", name="my_theme")   # loads with load_theme_json()
export.to_python(spec, name="my_theme")                  # a THEME_SPECS entry
export.diff(spec_a, spec_b)                              # "CATEGORY.key" -> ΔE

from lace.theme_kit import chassis_of, palette_of, restyle
chassis_of(spec)                 # ("edge", {overrides}); compose(palette_of(s), *...) == s
restyle(spec, "haze")            # the same palette on another chassis
```

**What `audit` checks.** It uses the engine's own rules (`lace.theme_contrast`): every
text-on-surface and UI-on-surface pair Lace draws, and the lightness separation between each
surface and its parent. It sorts each miss as one of:
- **failure:** a derived colour; the engine should have fixed it
- **capped:** a colour the spec set itself; the engine only nudges these
- **unreachable:** nothing meets the floor on that surface, so the surface itself must move

It also warns when:
- the accent is too close to the base to read as a state colour
- the focus ring is faint on the panel
- colours lost chroma to fit sRGB while being derived

**How `family` maps colours.** Each colour moves to the new member's lightness and keeps its hue:
- The base moves to a set lightness: 0.22 for dark (a dark source keeps its own), 0.72 for
  neutral, 0.92 for light.
- Surfaces keep their signed step off the base.
- Lines keep pointing toward the text.
- Text goes to near-white or near-black.
- Chromatic colours keep their contrast with the base, capped at what that base allows.
- Status colours are derived again for the new member.

Against the hand-made families, the mean ΔE is 0.03–0.06 (`tests/test_theme_kit.py`), with one
exception. `slate_amber` is the neutral of `slate_amber_dark`, but it sits at L 0.815, which is
a light theme rather than a mid-tone.

**How `status_colors` works.** Green, amber, red and blue share one lightness and chroma. The
lightness is the first one, moving away from the base, at which all four meet the theme's
"muted" floor.

## CLI

```bash
python -m lace.theme_kit derive --base "#1b1d23" --accent "#4f8cff" --chassis edge --out my_theme.json
python -m lace.theme_kit audit my_theme.json
python -m lace.theme_kit audit --preset slate_amber --allow-capped
python -m lace.theme_kit family my_theme.json --out-dir themes/
python -m lace.theme_kit chassis                     # list them
python -m lace.theme_kit chassis --preset neon_dusk  # closest chassis + overrides
```

`audit` exits 1 when any floor is missed, including by the theme's own colours. Pass
`--allow-capped` to forgive those. The exit code lets the command gate CI for a project's
theme files.

### Auditing your themes in CI

`audit` takes one theme per call. Loop over the theme folder and fail the job on the first miss:

```yaml
# .github/workflows/themes.yml (a step)
- name: Audit themes
  env:
    QT_QPA_PLATFORM: offscreen
  run: |
    for f in themes/*.json; do
      python -m lace.theme_kit audit "$f" --allow-capped || exit 1
    done
```

Leave out `--allow-capped` to also fail when your own explicit colours miss a floor. Add
`--contrast high` to check the high-contrast build too.

## Theme Studio

```bash
python -m lace.theme_kit studio                       # start from two seeds
python -m lace.theme_kit studio --preset slate_amber  # or from a preset / JSON file
```

The Studio has:
- seed colour pickers, the keyword drop-downs, a chassis picker and a neutral-tint slider
- a live dock layout (two areas, tabs, a sidebar, a floating window) and the control gallery
  with a 100–400 % zoom
- the audit, where *Fix* applies a suggestion to the colour it came from
- the family strip, where clicking a member opens it
- JSON export, a `ThemeSpec` literal on the clipboard, and a diff against the starting theme

Lace's style manager is process-wide. From inside a Lace app, open the Studio with
`lace.theme_kit.studio.launch()`: it runs in its own process, so the app's theme is untouched.
