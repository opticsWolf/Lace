# Lace Theming & Geometrical Architecture Documentation

Lace features a declarative, high-performance 5-color theming architecture (`ThemeSpec`) with localized category styling (`DockStyleCategory`) and responsive geometrical adjustment tokens.

---

## 1. Declarative `ThemeSpec` Interface (`dock_theme.py`)

Themes in `dock_custom_theme.py` are defined using `ThemeSpec`, a dataclass that accepts color palettes (list or `QColor`) alongside optional geometrical and status tokens:

```python
@dataclass(frozen=True)
class ThemeSpec:
    base: Union[QColor, List[int]]
    accent: Union[QColor, List[int]]
    text: Union[QColor, List[int]]
    surface: Optional[Union[QColor, List[int]]] = None
    border: Optional[Union[QColor, List[int]]] = None
    is_light: bool = False
    title_mode: str = "darker"   # "darker" | "lighter" relative to panel
    hover_mode: str = "lighter"  # "darker" | "lighter" relative to panel
    
    # Status Tokens
    success_color: Optional[Union[QColor, List[int]]] = None
    warning_color: Optional[Union[QColor, List[int]]] = None
    error_color: Optional[Union[QColor, List[int]]] = None
    info_color: Optional[Union[QColor, List[int]]] = None
    
    # Tooltip Tokens (default: derived from panel/text; drive QToolTip palette)
    tooltip_bg: Optional[Union[QColor, List[int]]] = None
    tooltip_text: Optional[Union[QColor, List[int]]] = None
    
    # Geometrical Tokens
    corner_radius: Optional[int] = None
    border_width: Optional[float] = None
    title_height: Optional[int] = None
    title_padding_left: Optional[int] = None
    title_padding_right: Optional[int] = None
    title_button_spacing: Optional[int] = None
    title_margin: Optional[int] = None           # 0 for flush against outer card edges, 2-3 for inset ring
    title_border_width: Optional[float] = None # Stroke outline around title bar
    title_border_bottom: Optional[float] = None # Divider stroke underneath title bar
    title_border_color: Optional[Union[QColor, List[int]]] = None
    title_border_focus_color: Optional[Union[QColor, List[int]]] = None  # title_border_color while the area has focus
    tab_radius: Optional[int] = None
    tab_margin: Optional[int] = None
    content_margin: Optional[Union[int, float, List[int], Tuple[int, ...]]] = None
    tab_dimming: bool = False
    indicator_width: Optional[int] = None
    indicator_position: Optional[Union[str, List[str], Tuple[str, ...]]] = None

    # Sidebar Tab Tokens — shape and outline of the vertical auto-hide tabs.
    # "all" (the default flat edge) keeps them the plain rectangles they have
    # always been; "outward" / "inward" / "none" pick which side stays flat,
    # and the radius follows tab_radius unless pinned here.
    sidebar_tab_flat_edge: Optional[str] = None
    sidebar_tab_radius: Optional[int] = None
    sidebar_tab_bg_normal: Optional[Union[QColor, List[int]]] = None       # inactive fill
    sidebar_tab_bg_hover_start: Optional[Union[QColor, List[int]]] = None  # hover gradient
    sidebar_tab_bg_hover_end: Optional[Union[QColor, List[int]]] = None
    sidebar_tab_bg_active: Optional[Union[QColor, List[int]]] = None       # selected fill
    sidebar_tab_border_width: Optional[float] = None
    sidebar_tab_border_color: Optional[Union[QColor, List[int]]] = None
    sidebar_tab_border_active_color: Optional[Union[QColor, List[int]]] = None
    sidebar_tab_border_hover_color: Optional[Union[QColor, List[int]]] = None
    sidebar_tab_border_closed: Optional[bool] = None
    sidebar_indicator_width: Optional[float] = None
    sidebar_indicator_position: Optional[str] = None
```

### Sidebar tab shape

A sidebar tab is a vertical strip in a bar that runs along one window edge, so the side it is
*joined along* is not the bottom the way a dock widget tab's is — it is the window-facing
(`"outward"`) or content-facing (`"inward"`) side, and which one that is mirrors with the bar.

```python
ThemeSpec(
    ...,
    tab_radius = 6,                      # sidebar tabs inherit this roundness
    sidebar_tab_flat_edge = "outward",   # flat against the window edge
    sidebar_tab_border_width = 1.0,      # outlined, open along that flat edge
    sidebar_tab_border_closed = True,    # ...or closed all the way round
)
```

With `sidebar_tab_flat_edge = "none"` all four corners are rounded, the tab reads as a
detached pill, and the outline is always closed — there is no flat edge left to open. That is
what `cyberpunk_neon` and `cyberpunk_edge` ship; the only difference between them is that
neon leaves the inactive tabs bare (`sidebar_tab_border_color = [0, 0, 0, 0]`) while edge
rings them in its muted violet:

```python
ThemeSpec(
    ...,
    sidebar_tab_flat_edge = "none",                          # a closed ring
    sidebar_tab_border_width = 1.5,
    sidebar_tab_border_color = [0, 0, 0, 0],                 # inactive: no ring
    sidebar_tab_border_active_color = [255, 154, 0, 255],
    sidebar_indicator_width = 1.5,                           # == the ring's width
)
```

Keep the stripe's width equal to the ring's. The stripe sits on the ring's content-facing
edge and is painted *under* it, so at equal widths the ring covers it and the tab is one
clean line all the way round; a wider stripe (the default is 3) shows the difference as a
band of the accent inside the ring.

The outline has a third colour, `sidebar_tab_border_hover_color`, and it is the one that is
*not* seeded: left unset, hover is not a state of its own and a hovered tab keeps the
inactive outline — the behaviour of every theme written before the token existed. Set it with
the inactive colour transparent and the ring becomes the hover cue, which is what
`violet_haze` ships:

```python
ThemeSpec(
    ...,
    sidebar_tab_flat_edge = "none",
    sidebar_tab_border_width = 2.0,
    sidebar_tab_border_color = [0, 0, 0, 0],             # idle: bare
    sidebar_tab_border_hover_color = [189, 147, 249, 130],   # the active ring, previewed
    sidebar_indicator_width = 2.0,
)
```

The active colour is left out there on purpose: it is seeded with the accent for every theme,
so the width alone is what switches it on. A checked tab keeps that ring under the cursor —
checked wins over hovered, the same precedence the fill uses. `slate_amber` ships the same
three steps in its own amber, at the 1.5px it rules everything else with.

An outline on a tab that keeps a flat edge is a U rather than a ring, and `neon_dusk` is the
only preset whose sidebar tabs do that:

```python
ThemeSpec(
    ...,
    sidebar_tab_flat_edge = "outward",      # rounded on the content-facing side only
    sidebar_tab_border_width = 2.0,         # ...open along the window-facing one
    sidebar_tab_border_color = [0, 0, 0, 0],                # idle: bare
    sidebar_tab_border_hover_color = [98, 114, 164, 160],   # hover: the U alone...
    sidebar_tab_bg_hover_start = [0, 0, 0, 0],              # ...and nothing behind it
    sidebar_tab_bg_hover_end = [0, 0, 0, 0],
    sidebar_indicator_width = 2.0,          # the strip stays on the content-facing
)                                           # edge, where the U already runs
```

The transparent hover fill is not decoration. The derived one is a lifted slab over the whole
tab *shape* — flat edge included — and its straight window-facing side is a harder line than
the U in front of it, so the tab reads as a rectangle with three sides drawn. An open outline
only reads as open if nothing fills the shape it belongs to — and nothing may be put on the
open edge either: leaving `sidebar_indicator_position` at its content-facing default is what
keeps the U open, since a strip there would close it.

### Inactive sidebar tabs with a background

A sidebar tab has the same three-state fill a dock widget tab does — normal, hover, active —
but the normal one is transparent in every shipped theme, so an idle tab shows only its
label. `sidebar_tab_bg_normal` fills it:

```python
ThemeSpec(
    ...,
    sidebar_tab_bg_normal = [125, 124, 252, 40],   # the accent, as a tint
)
```

Pass the accent at full alpha and every inactive tab becomes a slab of the highlight colour;
at a low alpha it reads as a tint, and the active tab still stands out through its own
`tab_bg_active` and indicator. Hover keeps priority over both.

Hover is what caps the alpha, and lower than you would guess. Left derived it comes off the
base and carries no accent, so it sits at a fixed luminance however deep the tint goes — push
the tint past it and an *idle* tab out-glows a hovered one, which reads as a glitch.
`midnight_haze` ships the only tinted sidebar in the presets and uses alpha 30 against a
crossover just past 40.

That limit is the derived hover's, not the tint's. The fill is a three-state set and all of
it is themeable, so give hover the accent as well and the ceiling rises with it:

```python
ThemeSpec(
    ...,
    sidebar_tab_bg_normal      = [125, 124, 252, 90],    # a much deeper tint
    sidebar_tab_bg_hover_start = [125, 124, 252, 160],   # ...that hover still beats
    sidebar_tab_bg_hover_end   = [125, 124, 252, 130],
    sidebar_tab_bg_active      = [58, 60, 96, 255],      # optional; panel colour when unset
)
```

The hover pair is a horizontal gradient (start on the left edge, end on the right); pass the
same colour twice for a flat fill.

---

## 2. Titlebar Flushness & Borders (`title_margin` & `title_border_bottom`)

When a dock card (`DockAreaWidget`) has rounded corners (`corner_radius`) and an outer `border_width`, the outer card layout applies an inset (`chrome_content_margin`) to its children by default (`4 px` in Cyberpunk Neon, `1 px` in standard themes) so that square inner children stay inside the curve. This produces a `1-4 px` ring of the panel background (`surface`) surrounding the title bar (`DockAreaTitleBar`).

To take full control of this ring and title bar boundaries, `ThemeSpec` provides:
- **`title_margin`**: Sets the inset around the top, left, and right sides of `DockAreaTitleBar`.
  - Set `title_margin = 0` to make the title bar **100% flush** against the outer card edges! When `0`, `DockAreaTitleBar` automatically takes the outer `corner_radius` for its top corners, perfectly following the outer card contour without double-padding.
  - Set `title_margin = 2` (or `3`) to explicitly create a `2-3 px` concentric border around the title bar.
- **`title_border_bottom`**: Draws a crisp divider line (`QPen`) across the bottom edge of `DockAreaTitleBar` to cleanly separate the header from the content panel below (`title_border_color` controls its color).
- **`title_border_width`**: Draws a full outline stroke around `DockAreaTitleBar`.

---

## 3. Titlebar Spacing (`pad_left = 0`)

By default, `DockTitleBarStyleSchema.padding_left` is set to `0` (with fallback to `0` in `DockAreaTitleBar.refresh_style()`). This ensures that the leftmost tab (`DockWidgetTab`) aligns flush against the inner card border of `DockAreaTitleBar`.

Because `DockAreaTitleBar` is nested inside `DockAreaWidget` with a `chrome_content_margin` inset (`2px`), `pad_left = 0` eliminates double-padding and produces a clean, professional visual hierarchy.

---

## 3. Dynamic `content_margin` in `DockWidget`

`DockWidget` supports dynamic `content_margin` styling via `DockStyleCategory.PANEL`. Instead of hardcoded margins around child widgets (`QTextEdit`, `QScrollArea`, etc.), `DockWidget.refresh_style()` parses `content_margin` using two modes:

1. **Single Value** (e.g. `content_margin = 6`):
   Applies equally to all four sides (`left=6, top=6, right=6, bottom=6`).
2. **Two Values** (e.g. `content_margin = (8, 2)`):
   The first value (`8`) applies to `left`, `right`, and `bottom`. The second value (`2`) specifically controls the `top` margin immediately beneath the titlebar, enabling tight integration without visual gaps or double borders.

---

## 4. Customizable Tab Highlight Stripe & Tab Dimming

Lace supports advanced active tab indicator customization and dynamic theme dimming behavior:

- **`tab_dimming`** (boolean, defaults to `False`):
  - When set to `True`, the active/focused tab inside **unfocused (non-active)** dock areas gets visually dimmed to help the user identify which container currently has key focus.
  - The tab's text color is blended halfway (`factor = 0.5`) between `text_active` and `text_normal`.
  - The tab's selection highlight indicator stripe is blended halfway with `bg_active` (the tab's background color).
  - This updates reactively when the active/focused dock area changes or when window focus transitions.
- **`indicator_width`** (integer, thickness):
  - Directly sets the thickness (in pixels) of the active tab's selection highlight indicator stripe.
- **`indicator_position`** (string or list/tuple of strings):
  - Sets which edge(s) of the active tab display the highlight selection stripe.
  - Accepts `"none"`, `"left"`, `"right"`, `"top"`, `"bottom"`, or combinations thereof (such as comma/space-separated strings `"top, bottom"`, `"left, right"`, or a list `["left", "right"]`).

---

## 5. Example Theme: `Cyberpunk Neon`

The `Cyberpunk Neon` (`"cyberpunk_neon"`) preset demonstrates the full range of both color and geometrical tokens:

```python
"cyberpunk_neon": ThemeSpec(
    base       = [14, 11, 28, 255],     # Deep cyber indigo
    accent     = [255, 0, 127, 255],    # Electric neon pink
    text       = [245, 245, 255, 255],  # Crisp white text
    surface    = [24, 19, 44, 255],     # Rich violet inner panel
    border     = [0, 240, 255, 255],    # Glowing cyan structural border
    title_mode = "darker",              # Recessed dark indigo header
    hover_mode = "lighter",             # Tabs highlight brightly on hover
    success_color = [57, 255, 20, 255], # Neon green
    warning_color = [255, 215, 0, 255], # Cyber gold
    error_color   = [255, 42, 109, 255],# Neon red
    info_color    = [5, 217, 232, 255], # Cyan
    
    # Geometrical Adjustments
    corner_radius = 10,                 # Distinct rounded card corners
    border_width = 1.5,                 # Visible glowing 1.5px cyan outline
    title_height = 32,                  # Roomy 32px title bar height
    title_padding_left = 0,             # Leftmost tabs sit flush against left edge
    title_padding_right = 8,            # 8px padding on right side
    title_button_spacing = 6,           # 6px spacing between action buttons
    tab_radius = 8,                     # 8px rounded top corners on tabs
    tab_margin = 3,                     # 3px gap separating adjacent tabs
    content_margin = (8, 2),            # 8px left/right/bottom, tight 2px top gap under title bar
)
```

---

## 6. Reactive Border Colors (`_focus_border` vs `_neutral_border`)

In Lace's docking architecture, card borders (`border_width`) on `DockAreaWidget` panels (`ChromeFrame`) are **reactive to focus**:

1. **Focused (`_chrome_focused = True`)**:
   Only the active dock area (`DockAreaWidget`) displaying the currently focused/selected tab receives the vibrant `focus_border_color` (`_focus_border`). If `ThemeSpec.border` is explicitly defined (such as `[0, 240, 255, 255]` in `cyberpunk_neon`), it is used as the high-visibility active outline (`c.focus_border`). If `border` is not provided, `_accent_bright` is used automatically.

2. **Unfocused (`_chrome_focused = False`)**:
   All inactive dock areas display a calm, neutral border (`border_color` -> `_neutral_border`) derived automatically from the inner card surface (`_panel`) or base canvas (`base`):
   - **Dark Themes (`is_light = False`)**: Derived by stepping slightly lighter (`+0.08`) than the dark panel surface, creating a subtle, elegant structural edge against dark backgrounds.
   - **Light Themes (`is_light = True`)**: Derived by stepping slightly darker (`-0.12`) than the light panel surface, ensuring clear, clean separation on bright backgrounds.

3. **Focus Coordination (`DockManager` & `QApplication`)**:
   `DockManager.set_active_dock_area(area)` acts as the global coordinator across all open docking containers. It updates `set_chrome_focused(True)` on the active area and `set_chrome_focused(False)` on the previously active area whenever any child widget gains keyboard focus (`qapp.focusChanged`), when a tab is selected (`set_current_index`), or upon mouse interaction (`mousePressEvent`).

---

## 7. Architectural Flow

```
[ThemeSpec in dock_custom_theme.py]
              │
              ▼
   [build_theme() / _build_theme()]
   ├── _neutral_border (unfocused, derived by light/dark contrast)
   └── _focus_border   (focused, explicit spec.border or accent)
              │
              ▼
  [Dict of DockStyleCategory schemas]
   ├── CORE      ──> [ChromeTokens(border=_neutral_border, focus_border=_focus_border)]
   │                   │
   │                   ▼
   │              [DockManager.set_active_dock_area(area)]
   │              swaps outline dynamically on focus / tab selection
   │
   ├── TITLE_BAR ──> [DockAreaTitleBar (height, pad_left=0, button_spacing)]
   ├── TAB       ──> [DockWidgetTab (corner_radius, margin)]
   └── PANEL     ──> [DockWidget (content_margin -> setContentsMargins)]
```

---

## 8. JSON Theme Files (`theme_models.py`)

Declarative themes can also be shipped as **JSON files**, validated by Pydantic
before they touch the engine. The JSON schema mirrors `ThemeSpec` (see §1): the
same 3–5 seed colors plus every geometry/status token, so a JSON theme derives
its complete token set through the same `build_theme()` pipeline as the
built-in presets.

### Format

- **Colors** may be `[r, g, b(, a)]` lists **or** `"#rrggbb"` / SVG-name strings.
  Channel lists are validated (ints in `0..255`, 3 or 4 channels); strings are
  resolved through Qt's canonical `QColor` conversion.
- **Unknown keys are ignored**, so future metadata can be embedded safely.
- **Schema violations raise `pydantic.ValidationError`** (e.g. out-of-range
  channel, missing required `base`/`accent`/`text`), and malformed JSON raises
  `JSONDecodeError`.

```json
{
    "name": "MyTheme",
    "base": [14, 11, 28, 255],
    "accent": "#ff007f",
    "text": [245, 245, 255, 255],
    "surface": [24, 19, 44, 255],
    "border": [0, 180, 205, 205],
    "is_light": false,
    "corner_radius": 10,
    "border_width": 1.5,
    "title_height": 32,
    "tab_radius": 8,
    "sidebar_tab_flat_edge": "outward",
    "sidebar_tab_border_width": 1.0,
    "content_margin": [8, 2],
    "tab_dimming": true
}
```

### Loading & Applying

```python
from lace import load_theme_json, get_dock_style_manager

# Validate + build the full theme dict
theme = load_theme_json("my_theme.json")      # -> {DockStyleCategory: {token: value}}

# Apply through the same path as named themes (resets to defaults first)
get_dock_style_manager().apply_theme_dict(theme)

# Or route it through the OS-aware switcher:
from lace import ThemeManager

tm = ThemeManager(QApplication.instance(), default_theme_path="themes/")
tm.sync_theme()                                # loads themes/dark.json or themes/light.json

tm.sync_theme(path="my/custom/theme.json")    # explicit override
```

`ThemeManager.default_theme_path` may point at a single theme file (`.json` /
`.qss` / `.css`) or a directory containing `<theme_name>.json|.qss|.css`, used
when `sync_theme()` is called without an explicit `path`.

---

## 9. Theme Keywords (0.8)

Since 0.8, `build_theme()` derives every surface in **OKLCH** (`lace/color_science.py`), not HLS.
Equal steps now look equal on any base colour. A few keywords on `ThemeSpec` (and in JSON
themes) steer the derivation. Every keyword has a default, so 0.7 themes load unchanged.

| Keyword | Values (default **bold**) | Effect |
|---|---|---|
| `contrast` | `low`, **`normal`**, `high` | WCAG floor for text and UI tokens, see §10 |
| `depth` | `flat`, **`subtle`**, `raised` | how far derived surfaces (panel, title, hover, input, button, …) step off each other |
| `selection` | **`solid`**, `tint` | selected items: an accent fill, or an accent wash that keeps the normal text colour |
| `scrollbar` | `thin`, **`expanding`**, `fusion` | LaceStyle scroll bars: a slim overlay handle, one that widens on hover, or Fusion's |
| `corner_clip` | **`cap`**, `inset`, `none` | how dock content meets the card's rounded corners, see §11 |
| `control_radius` | **4** | corner radius of every LaceStyle control; 0 is square |
| `focus_width` | **2.0** | pen width of LaceStyle's keyboard focus ring; 0 hides it |
| `outline_strength` | **0.22** | how much text colour is mixed over a control's fill for its 1 px outline |
| `field_outline` | **True** | outline input fields and framed views while unfocused; False leaves only the fill and a focused field's accent ring. Containers (group boxes, tab-widget panes) keep their frame either way |
| `outline_contrast` | **"auto"** | contrast level (`"low"` / `"normal"` / `"high"`) the unfocused outlines of fields, views, buttons and containers are held to; `"auto"` follows `contrast`. Focus rings and indicators always follow `contrast`. The classic basics use `"low"` to keep their outlines faint |
| `keep_tint` | **False** | derived colours keep the theme's hue: the active text (tabs, title bars, sidebar) stops short of pure white or black, and zebra rows striped off a white input take the panel's tint; selected text on a solid accent still uses the full-strength step |
| `splitter_length` | **50** | length in px of the grip on a LaceStyle splitter handle (clipped to the handle) |
| `is_light` | **None** | None decides from the base (OKLCH lightness below 0.6 is dark) |

`subtle` is calibrated to the median step 0.7.6 produced over every preset, so the default look
is kept. The default theme is the "sleek" reference: `subtle`, `expanding` and `cap`.

Derivation happens once per theme apply. `build_dock_palette()` is built once per colour snapshot,
and LaceStyle memoises its colour mixes, so painting does no colour science.

---

## 10. Contrast Floors (`theme_contrast.py`)

After derivation, `enforce` moves **foregrounds only** until each pair in `CONTRAST_PAIRS`
meets its floor. Surfaces are never moved. Colours that already pass stay as they are.

| Role | low | normal | high |
|---|---|---|---|
| text | 4.5 | 7.0 | 10.0 |
| muted | 3.0 | 4.5 | 7.0 |
| disabled | 1.8 | 2.3 | 3.0 |
| ui (outlines, focus, indicators) | 1.5 | 3.0 | 4.5 |
| border | 1.15 | 1.3 | 1.6 |
| on_accent (text on a selection) | 3.0 | 4.5 | 7.0 |

- A colour the preset sets **explicitly** moves only up to ΔE 0.04 (`EXPLICIT_MAX_DE`), so the
  author's colour survives. A floor it still misses is reported as *capped*.
- A floor that no colour can reach on its surface is reported as *unreachable*.

Neither of these is an error. `python -m lace.theme_kit audit` and `dev_smoke/theme_drift.py`
list both.

The completed `QPalette` sets every role in every colour group (Active, Inactive, Disabled).
Disabled text keeps the disabled floor on its disabled fill, and an inactive selection is quieter
but still legible.

---

## 11. Corner Modes (`corner_clip`)

A dock widget's content (a text edit, a view) is square, but the card around it can be rounded.
`corner_clip` decides what happens at the corners:

- **`cap`** (default): after the content paints, an antialiased cap in the backdrop colour
  is drawn over each corner. The content keeps its full size, and the arc stays clean at any radius
  and scale. LaceStyle scroll-bar handles stay inside the arc. Content that holds a native child
  window (`QWebEngineView`, `QOpenGLWidget`) can't be painted over, so it falls back to `inset`
  and logs this once.
- **`inset`**: the content is inset far enough that it never reaches the arc.
- **`none`**: the content is left as it is. This matches 0.7 behaviour.

---

## 12. LaceStyle (`lace_style.py`, `lace/style/`)

`LaceStyle` is a modern, flat Fusion: a `QProxyStyle` over Fusion.
- Fusion keeps the layout, identical on every OS, and paints what LaceStyle doesn't override.
- LaceStyle replaces the gradients, bevels and pixmap glyphs with flat fills, one 1.5 px stroke
  and vector paths.
- Sizes stay Fusion's. The only exceptions are the scroll-bar extent in the `thin` / `expanding`
  modes, a wider split-button arrow and an 11 px splitter handle.

It draws buttons, check and radio boxes, line edits, combo and spin boxes, sliders, dials, progress
bars, tabs, headers, menus, item views, tooltips, the tool box and scroll bars. The rest of the
chrome (`lace/style/_chrome.py`) is flat too:
- **Splitter handles** show a faint round-ended grip, 3 px thick (a pixel under the resting
  `expanding` scroll bar) and `splitter_length` long, padded 3 px on each side. On hover or drag it turns accent and
  grows by 2 px. `DockSplitter` keeps its own handle width; handles narrower than the grip keep
  Fusion's look.
- **Tab close buttons** are a vector cross with a rounded wash on hover and press.
- **`QFrame` lines** (`HLine`, `VLine`) are one line in the border colour, and boxes and panels a
  flat rounded outline, whatever their shadow.
- **Toolbar handles and separators and size grips** are flat lines in the muted text colour.
- **Menus and combo box popups** get rounded corners (`control_radius` + 2) and a few pixels of
  top and bottom padding, over a soft painted shadow (`lace/style/_popup.py`). `polish()` makes
  each popup window translucent and frameless before it is created, and swaps the native square
  drop shadow for a painted one: the window grows by 5 px on every side for the shadow, and on
  show it moves back by as much, so the panel sits exactly where Qt placed it (at the cursor, under
  its menu-bar item, beside its parent menu, or at its combo's width). With `control_radius=0`, a
  popup the app already made translucent, or one whose window existed before LaceStyle arrived,
  the popup stays square with no shadow.
- **`QCalendarWidget`** weekends use the accent (held to the text floor) instead of Qt's red,
  re-tinted on each theme switch.

**Framed scroll areas** (text edits and list, tree and table views) get rounded corners at
`control_radius`. Their viewport is a square child that would paint over the arc. So LaceStyle's
`polish()` adds a transparent overlay (`lace/style/_frame_cap.py`) that caps the corners with the
backdrop and then draws the outline, the same way the dock card uses `cap`.
- A dock widget's own content gets no outline, because the card already frames it. When the
  theme's `content_margin` insets it on every side, it is a box of its own and gets rounded
  corners. When it sits flush, the card's corners round it.
- `DockThemeBridge` forwards the theme's keywords to whatever LaceStyle paints its target,
  including one the app set with `app.setStyle(LaceStyle())`, before or after the `DockManager`.
- Combo box popup lists and areas holding a native child window are left square.

```python
from lace import DockThemeBridge, LaceStyle

DockThemeBridge()                 # installs LaceStyle on the app; tokens follow the theme
DockThemeBridge(style_name="Fusion")   # or keep a named Qt style instead
DockThemeBridge(install_style=False)  # colours only; the target keeps its style
DockManager(window, app_style="lace")  # the same choice, made by the DockManager

app.setStyle(LaceStyle(control_radius=6, scrollbar="expanding"))  # standalone, no Lace theme
```

`LaceStyle.set_tokens(control_radius=, scrollbar=, contrast=, focus_width=, outline_strength=,
splitter_length=, field_outline=)`
updates the knobs live. The bridge calls it on every theme switch.

**Use case: widgets in a `QGraphicsView`.** A node editor such as Weave embeds ordinary widgets in
a scene through `QGraphicsProxyWidget`. Native styles draw those poorly: they are scaled as bitmaps,
and the platform look clashes with the scene. LaceStyle paints only vector paths from the palette,
so proxied widgets stay sharp at any zoom and take the theme's colours. Set it on the view (or the
app) with a `DockThemeBridge(target=view)`, and every embedded control follows theme switches.

`lace.style.gallery.render(scale=)` draws every control LaceStyle styles in every state. The Theme
Studio's gallery tab uses it (see `docs/THEME_KIT.md`).

---

## 13. Style Token Reference (`DockStyleManager`)

A theme ends up as style tokens: flat fields on one schema per `DockStyleCategory`, held by the
`DockStyleManager` singleton. Widgets read them on every theme change. `build_theme()` turns a
`ThemeSpec` into these tokens, and a token can also be set directly.

### Setting tokens

```python
from lace import DockStyleCategory, build_theme, get_dock_style_manager

sm = get_dock_style_manager()

# Live, one category at a time. Only the changed tokens are sent to the widgets.
sm.update(DockStyleCategory.TAB, close_btn_size=20, indicator_width=3)
sm.update(DockStyleCategory.TITLE_BAR, button={"size": 20, "hover_bg": "#3a3f4b"})  # = button_size, button_hover_bg

# Kept across theme switches: add the tokens to the theme dict before applying it.
theme = build_theme(spec)
theme[DockStyleCategory.SIDEBAR]["badge_radius"] = 4
sm.apply_theme_dict(theme)

sm.get(DockStyleCategory.TAB, "close_btn_size")   # read one token
sm.get_all(DockStyleCategory.SIDEBAR)             # a dict of every token in a category
```

- **`update(category, **tokens)`** returns the names that changed. A dict value is shorthand for
  a group of prefixed tokens, as `button=` above.
- **Theme switches reset everything.** `apply_theme()` and `apply_theme_dict()` put every token
  back to the defaults below before applying the theme, so a live `update()` lasts only until
  the next switch.
- **Colours** may be `[r, g, b(, a)]` lists, `"#rrggbb"` strings or `QColor`s. They are stored as `QColor`s, and the
  ones `get()` returns are the live theme objects, so copy one (`QColor(c)`) before changing it.
- **Unknown names** log a warning and are ignored. That includes the unused tokens removed after
  0.8.1 (listed in the CHANGELOG), so a theme dict written for 0.7 or 0.8 still applies.

### Reading the tables

- **Default** is the value before any theme is applied. *derived* means `build_theme()` always
  computes it from the seed colours and keywords, so every theme overwrites it.
- **`ThemeSpec`** names the `ThemeSpec` field that sets the token, when one does. Tokens with no
  `ThemeSpec` field keep their default unless you set them yourself.
- Font weights take `"normal"`, `"bold"`, an int (100–900) or a `QFont.Weight`.

### `CORE`: the app and dock areas

| Token | Default | `ThemeSpec` | What it does |
|---|---|---|---|
| `canvas_bg` | *derived* | `base` | window background behind the dock areas |
| `border_color` | *derived* | `border` | dock area outline |
| `focus_border_color` | *derived* | `focus_border_color`, `accent` | dock area outline while the area has focus |
| `accent_color` | *derived* | `accent` | the accent; also the palette's link colour |
| `text_color` | *derived* | `text` | main text colour |
| `disabled_text_color` | *derived* | — | disabled menu items and icons |
| `success_color`, `warning_color`, `error_color`, `info_color` | *derived* | same names | status colours |
| `tooltip_bg`, `tooltip_text` | *derived* | same names | `QToolTip` palette |
| `border_width` | 1.5 | `border_width` | dock area outline width; 0 draws none |
| `border_below_title` | False | `border_below_title` | draw the area outline only below the title bar, whose bottom rule closes it |
| `corner_radius` | 4 | `corner_radius` | dock area corner radius |
| `margin`, `padding` | 0 | — | contents margins of the dock container's layout |
| `control_radius` | 4 | `control_radius` | LaceStyle control radius (see §9) |
| `scrollbar` | `"expanding"` | `scrollbar` | LaceStyle scroll bars (see §9) |
| `corner_clip` | `"cap"` | `corner_clip` | how content meets the card's corners (see §11) |
| `focus_width` | 2.0 | `focus_width` | LaceStyle focus ring width |
| `outline_strength` | 0.22 | `outline_strength` | LaceStyle outline strength |
| `field_outline` | True | `field_outline` | outline unfocused input fields and framed views (not group boxes or tab panes, which always keep theirs) |
| `outline_contrast` | `"auto"` | `outline_contrast` | contrast floor for unfocused outlines only (`"auto"` = `contrast`) |
| `splitter_length` | 50 | `splitter_length` | LaceStyle splitter grip length |
| `contrast` | `"normal"` | `contrast` | contrast floor for LaceStyle's non-text UI |

### `PANEL`: dock widget content

These colours build the `QPalette` of every dock widget (see §7). The dock area's outline and
corner radius are `CORE`'s.

| Token | Default | `ThemeSpec` | What it does |
|---|---|---|---|
| `bg_normal` | *derived* | `surface` | panel background (`Window` role) |
| `text_color` | *derived* | `text` | panel text (`WindowText`, `Text`) |
| `input_bg` | *derived* | — | inputs and item views (`Base`) |
| `alternate_base` | *derived* | — | striped rows (`AlternateBase`) |
| `button_bg` | *derived* | — | button faces (`Button`) |
| `color_light`, `color_mid`, `color_dark`, `color_shadow` | *derived* | — | `Light`, `Mid`, `Dark` and `Shadow` roles |
| `highlight`, `highlighted_text` | *derived* | `selection` | selection fill and its text |
| `content_margin` | 0 | `content_margin` | inset of a dock widget's content: a number, `(horizontal, top)`, `(left, top, right)` or `(left, top, right, bottom)` |

### `TAB`: dock area tabs

| Token | Default | `ThemeSpec` | What it does |
|---|---|---|---|
| `bg_normal`, `bg_hover`, `bg_active` | *derived* | `title_bg`, `title_mode`, `hover_mode` | tab fill at rest, on hover, and when selected |
| `text_normal`, `text_active` | *derived* | `text` | label colour, unselected and selected |
| `font_family`, `font_size`, `font_weight`, `font_italic`, `font_underline` | `"Segoe UI"`, 10, `"normal"`, False, False | — | label font |
| `active_font_weight` | `"normal"` | — | label weight on the selected tab |
| `border_normal_color`, `border_active_color` | *derived* | `tab_border_color`, `tab_border_active_color` | outline on the left, top and right; a transparent colour skips that state |
| `border_unfocused_color` | None | `tab_border_unfocused_color` | selected tab's outline while its area is unfocused; unset dims `border_active_color` (with `tab_dimming`) |
| `border_width` | 0.0 | `tab_border_width` | outline width; 0 draws none |
| `corner_radius` | 4 | `tab_radius` | tab corner radius |
| `margin` | 0 | `tab_margin` | gap between tabs |
| `indicator_color` | *derived* | `accent` | selected tab's stripe |
| `indicator_width` | 2.0 | `indicator_width` | stripe thickness |
| `indicator_position` | `"bottom"` | `indicator_position` | `"top"` or `"bottom"` |
| `tab_dimming` | False | `tab_dimming` | dim the selected tab of an unfocused area |
| `tab_icon_size` | 16 | — | size of the widget's icon left of the label |
| `close_btn_color`, `close_btn_bg_hover`, `close_btn_bg_disable` | *derived* | — | close button icon, hover fill and disabled icon |
| `close_btn_size` | 17 | — | close button minimum size; the box is `size + 2 × padding + 3` |
| `close_btn_icon_size` | 14 | — | close icon size |
| `close_btn_corner_radius` | 3 | — | close button hover fill radius |
| `close_btn_padding` | 2 | — | close button padding |
| `close_btn_expand_vertical` | False | — | stretch the close button to the tab's height |

### `TITLE_BAR`: dock area title bars and the frameless window title

| Token | Default | `ThemeSpec` | What it does |
|---|---|---|---|
| `bg_normal` | *derived* | `title_bg`, `title_mode` | title bar background |
| `text_normal` | *derived* | `text` | frameless window title text |
| `text_active` | *derived* | — | tint of active icons drawn in this category |
| `font_family`, `font_size`, `font_weight`, `font_italic`, `font_underline` | `"Segoe UI"`, 13, `"normal"`, False, False | — | frameless window title font |
| `border_color` | *derived* | `title_border_color` | title bar outline and bottom rule |
| `focus_border_color` | *derived* | `title_border_focus_color` | `border_color` while the area has focus; unset falls back to `CORE`'s pair |
| `border_width` | 0.0 | `title_border_width` | outline around the title bar |
| `border_bottom` | 0.0 | `title_border_bottom` | rule under the title bar; 0 uses `border_width` |
| `height` | 30 | `title_height` | title bar height |
| `padding_left`, `padding_right`, `padding_top` | 0, 6, 0 | `title_padding_left`, `title_padding_right` | title bar contents margins |
| `margin` | 0 | `title_margin` | inset from the card edge: 0 is flush, 2–3 an inset ring |
| `active_edge_color` | *derived* | `accent` | strip along the top of the focused area's title bar, drawn over its tabs |
| `active_edge_width` | 0.0 | — | strip thickness; 0 draws none |
| `button_color`, `button_disable_clr`, `button_hover_bg` | *derived* | — | button icon, disabled icon and hover fill |
| `button_size` | 17 | — | button minimum size; the box is `size + 2 × padding + 3` |
| `button_icon_size` | 16 | — | button icon size |
| `button_corner_radius` | 3 | — | hover fill radius |
| `button_padding` | 2 | — | button padding |
| `button_expand_vertical` | False | — | stretch buttons to the bar's height |
| `button_spacing` | 4 | `title_button_spacing` | gap between buttons |

### `SIDEBAR`: auto-hide sidebar strips and their tabs

| Token | Default | `ThemeSpec` | What it does |
|---|---|---|---|
| `width` | 30 | — | strip width |
| `bg_color` | *derived* | — | strip background |
| `border_color` | None | — | strip outline; unset draws none |
| `border_width` | 1.0 | — | strip outline width |
| `padding` | 0 | — | strip contents margins |
| `tab_margin` | 2 | — | gap between tabs |
| `tab_bg_normal`, `tab_bg_active` | *derived* | `sidebar_tab_bg_normal`, `sidebar_tab_bg_active` | tab fill at rest and when open |
| `tab_bg_hover_start`, `tab_bg_hover_end` | *derived* | `sidebar_tab_bg_hover_start`, `sidebar_tab_bg_hover_end` | hover gradient |
| `tab_corner_radius` | None | `sidebar_tab_radius` | tab radius; unset follows `TAB.corner_radius` |
| `tab_flat_edge` | `"all"` | `sidebar_tab_flat_edge` | edge left square: `"outward"`, `"inward"`, `"none"`, or `"all"` for a plain rectangle (see §1) |
| `tab_border_normal_color`, `tab_border_active_color` | *derived* | `sidebar_tab_border_color`, `sidebar_tab_border_active_color` | tab outline; a transparent colour skips that state |
| `tab_border_hover_color` | None | `sidebar_tab_border_hover_color` | outline of a hovered inactive tab; unset keeps the normal one |
| `tab_border_width` | 0.0 | `sidebar_tab_border_width` | outline width; 0 draws none |
| `tab_border_closed` | False | `sidebar_tab_border_closed` | close the outline across the flat edge |
| `tab_icon_size`, `tab_icon_gap` | 16, 8 | — | tab icon size and its gap to the label |
| `tab_text_normal`, `tab_text_active`, `tab_text_disabled` | *derived* | — | label colours |
| `tab_font_family`, `tab_font_size`, `tab_font_weight`, `tab_font_italic`, `tab_font_underline` | `"Segoe UI"`, 10, `"normal"`, False, False | — | label font |
| `tab_active_font_weight` | None | — | label weight on the open tab; unset keeps `tab_font_weight` |
| `indicator_color` | *derived* | — | open tab's stripe |
| `indicator_width` | 3.0 | `sidebar_indicator_width` | stripe thickness |
| `indicator_position` | `"right"` | `sidebar_indicator_position` | `"left"` or `"right"` |
| `badge_bg`, `badge_text` | *derived* | — | badge fill and text |
| `badge_font_family`, `badge_font_size`, `badge_font_weight` | `"Segoe UI"`, 8, `"bold"` | — | badge font |
| `badge_radius` | 6 | — | badge radius |
| `badge_position` | `"top_right"` | — | `"top_left"`, `"top_right"`, `"bottom_left"` or `"bottom_right"` (or a `TabBadgePosition`) |

### `SIDEPANEL`: the panel an open sidebar tab slides out

| Token | Default | `ThemeSpec` | What it does |
|---|---|---|---|
| `bg_normal` | *derived* | `base` | panel background |
| `height` | 30 | — | title strip height |
| `padding_left`, `padding_right`, `padding_top` | 10, 6, 0 | — | title strip contents margins |
| `title_text_color` | *derived* | — | title colour |
| `title_font_family`, `title_font_size`, `title_font_weight` | `"Segoe UI"`, 10, `"bold"` | — | title font |
| `button_*` | as `TITLE_BAR` | — | the same button tokens as the title bar |
| `button_spacing` | 2 | — | gap between buttons |
| `corner_radius` | 4 | `corner_radius` | panel radius |
| `border_width` | 1.5 | `border_width` | panel outline width |
| `border_color`, `focus_border_color` | *derived* | `border`, `focus_border_color` | panel outline, unfocused and focused |
| `shadow_color` | *derived* | — | drop shadow colour |
| `shadow_blur_radius` | 20 | — | drop shadow blur |

### `SPLITTER`: `DockSplitter` handles between dock areas

| Token | Default | `ThemeSpec` | What it does |
|---|---|---|---|
| `handle_color`, `handle_hover_color` | *derived* | `base`, `accent` | handle line at rest and on hover or drag |
| `handle_width` | 3 | — | thickness of the drawn line |
| `total_width` | 7 | — | width of the grab area |
| `handle_margin` | 0 | — | gap between the line's ends and the handle's ends |

### `OVERLAY`: drag-and-drop indicators

| Token | Default | `ThemeSpec` | What it does |
|---|---|---|---|
| `frame_color`, `overlay_color` | *derived* | — | drop-area preview outline and fill |
| `background_color`, `arrow_color`, `shadow_color` | *derived* | — | drop-target cross buttons, their arrows and shadow |


---

## 14. Title Bars

Every window an app shows can carry the theme's title bar. There are two
kinds of title bar, and both read their colours from one function,
`lace.title_bar_colors()`, so they cannot drift apart.

### The tokens

| Part | Token | Used by |
|---|---|---|
| Background | `SIDEBAR.bg_color`, else `TITLE_BAR.bg_normal` | both |
| Title text | `TITLE_BAR.text_normal` | both |
| Inactive title text | the title text at 60 % over the background (`INACTIVE_TEXT_ALPHA`) | native frame |
| Outline | `CORE.border_color` when `CORE.border_width` > 0 and it isn't transparent; otherwise the system's own | native frame |
| Buttons | `TITLE_BAR.button_color`, `button_hover_bg`, `button_disable_clr`, `button_size`, `button_icon_size`, `button_corner_radius` | custom bar |
| Font | `TITLE_BAR.font_family`, `font_size`, `font_weight`, `font_italic`, `font_underline` | custom bar |

The custom bar's close button keeps the system red on hover.

### Custom title bars (frameless windows)

`FramelessLaceMainWindow`, the frameless floating containers and
`FramelessLaceDialog` draw their own bar (`LaceStandardTitleBar`), styled by a
`FramelessTitleBarStyler` that follows theme switches live.

For dialogs, use `FramelessLaceDialog` directly or the `lace.dialogs` helpers,
which mirror Qt's static dialog functions:

```python
from lace import dialogs
from lace.frameless_dialog import FramelessLaceDialog

if dialogs.question(self, "Close", "Discard changes?") == dialogs.StandardButton.Yes:
    ...
name, ok = dialogs.get_text(self, "Rename", "Name:", text="Layer 3")

dlg = FramelessLaceDialog(self, buttons="close", resizable=False)
dlg.setWindowTitle("New layer")
dlg.contentLayout().addWidget(my_form)   # don't call dlg.setLayout()
dlg.exec()
```

### System title bars (native frames)

Windows that keep the OS frame (`QMessageBox`, `QInputDialog`, your own
`QDialog`s, tool windows, the native floating container) get the theme's
colours through the window manager. `DockManager` turns this on for the whole
application (`install_native_frame_theme()` does it without one). It reapplies
on every theme switch, and dims the title text of inactive windows.

| Platform | System title bar |
|---|---|
| Windows 11 | caption colour, title text (dimmed while inactive) and outline from the theme |
| Windows 10 | the theme's light or dark mode only; the caption stays black or white |
| macOS, Linux | the window manager's frame, unchanged |

### What stays out of reach

The OS file and print dialogs (`QFileDialog` in native mode, the default on
Windows and macOS) are OS windows with no Qt widget behind them. They follow
the system's light/dark setting, not the theme. To theme a file dialog, use Qt's
own: `dialogs.get_open_file_name(..., native=False)`.

### Opting out

| To | Use |
|---|---|
| leave every system frame alone | `DockManager(window, native_frames=False)` |
| leave one window's system frame alone | `window.setProperty("laceNativeFrame", False)` |
| make the `lace.dialogs` helpers open plain Qt dialogs | `dialogs.set_default_frameless(False)` |
