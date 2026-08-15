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
checked wins over hovered, the same precedence the fill uses.

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
