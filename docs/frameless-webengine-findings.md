# Frameless windows, custom title bars, and QWebEngineView

Findings from the Kilim Qt surface (v0.1.65–0.1.68). Versions matter:
**PySide6 6.11.2**, **PySideSix-Frameless-Window (qframelesswindow) 0.8.2**,
**Lace 0.7.0**, Windows 11.

---

## 1. qframelesswindow: where the embedded widgets go

`StandardTitleBar` (qframelesswindow 0.8.2) builds its `hBoxLayout` in three
steps:

```
TitleBarBase.__init__   resize(200, 32); setFixedHeight(32)
TitleBar.__init__       [stretch, minBtn, maxBtn, closeBtn]
StandardTitleBar        insertSpacing(0, 10)
                        insertWidget(1, iconLabel)
                        insertWidget(2, titleLabel)
```

Final order and layout indices:

| index | item |
|---|---|
| 0 | spacing (10px) |
| 1 | `iconLabel` |
| 2 | `titleLabel` |
| 3 | stretch |
| 4–6 | min / max / close buttons |

Consequences for custom bars:

- `insertWidget(2, w)` puts `w` **between icon and title** (the Lace
  `demo_app_custom_titlebar_menus.MenuEmbeddedTitleBar` does this and hides
  `titleLabel`, so menus sit right after the icon).
- `insertWidget(3, w)` puts `w` **after the title, before the stretch**.
- Don't trust a remembered index: `LaceStandardTitleBar` grew the leading
  spacing once already. Anchor with `hBoxLayout.indexOf(self.titleLabel)`
  when the position is "after the title".
- `setFixedHeight(self.height())` on an embedded menu bar works because the
  base sets a fixed 32px height in `TitleBarBase.__init__` — `height()` is
  valid during `__init__`.

### Dragging

`TitleBarBase.canDrag(pos)` is only `_isDragRegion(pos) and not
_hasButtonPressed()`. `_isDragRegion` subtracts the buttons' width on the
right; it knows nothing about embedded children. Every custom bar must
override `canDrag()` and walk `childAt(pos)` up the parents, returning
`False` for `QMenuBar`, `QMenu`, `QAbstractButton`, `QLineEdit` (and any
other interactive child). Otherwise a press on a menu item can start the
OS move loop.

---

## 2. Lace integration points

- `FramelessLaceMainWindow.__init__(title_bar=...)` resolves the descriptor
  (`None` → `LaceStandardTitleBar`; class/instance/callable otherwise),
  replaces the base title bar, then calls `setMenuWidget(self.titleBar)`.
  `setCentralWidget` is overridden to `titleBar.raise_()` afterwards
  ("keeps the title bar on top") — so the central widget must be set
  **after** the dock manager exists.
- `DockManager(parent)` calls `parent._register_titlebar_theme()`, creating
  a `FramelessTitleBarStyler` that restyles the title bar (and an optional
  QMainWindow menu bar) from dock-theme tokens. That styler sets
  `WA_StyledBackground` and paints min/max/close colors via the buttons'
  private `_normalColor` / `_hoverBgColor` attributes.
- The dock-theme background does **not** always reach a QSS-styled title
  bar: the Lace demo's custom bar fills the rect explicitly in
  `paintEvent` before `super().paintEvent(event)` so the bar and the
  embedded menu bar share one exact color.
- `DockManager.title_bar_mode` only chooses the **floating container**
  class (`custom` → `FramelessFloatingDockContainer`; anything else →
  native `FloatingDockContainer`). The main window's chrome comes from the
  `FramelessLaceMainWindow` subclass. `floating_title_bar` is resolved by
  `FramelessFloatingDockContainer._create_title_bar()` from the owning
  manager.
- QMenus are top-level windows: they read the *application* palette, not
  the dock root's. `DockThemeBridge()` is required or tab/context menus
  keep the system palette while the bar is themed.

---

## 3. The WebEngine finding: a QWebEngineView rebuilds the top-level window

### Symptom

Kilim's main window lost Windows 11 rounded corners and Aero Snap as soon
as a markdown pane existed. The Lace demo — same `FramelessLaceMainWindow`,
no WebEngine — was unaffected.

### Evidence

Native styles read with `GetWindowLongW(hwnd, GWL_STYLE / GWL_EXSTYLE)`:

| window | style | ex-style |
|---|---|---|
| frameless main window (term/file panes) | `0x86cf0008` (CAPTION, THICKFRAME, SYSMENU, MIN, MAX, POPUP, DLGFRAME, BORDER) | `0x00000100` (WINDOWEDGE) |
| same window after markdown `setHtml()` | `0x860b0000` (SYSMENU, MIN, MAX, POPUP) | `0x0` |
| demo window (no WebEngine) | `0x86cf0008` | `0x100` |

The `winId()` value changes across `setHtml()` — Qt **destroys and
recreates the top-level native handle**. On recreation the frameless
window no longer gets the CAPTION/THICKFRAME bits, and those bits are what
DWM rounding and Snap depend on (QSS cannot bring either back).

Trigger scope (measured):

- `QWebEngineView(parent)` alone: harmless.
- `setHtml()` (first load / Chromium init): recreates the window.
- `QOpenGLWidget` also recreates it; a plain native `QWidget` child does
  not. So this is GL/Chromium-related, not WebEngine-specific.
- Pre-creating any native child happened to prevent the recreation in one
  probe; that is incidental and not a supported fix.

What did **not** help:

- `QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)` before the app.
- Initialising Chromium in a throwaway view before the main window.
- Showing the window first.
- `window.setWindowFlags(window.windowFlags())` after the fact — for an
  existing window Qt recomputes the stripped style.

### Supported fix

Call `window().updateFrameless()` **after** the WebEngine view has loaded.
This is exactly what qframelesswindow's own
`qframelesswindow.webengine.FramelessWebEngineView` does:

```python
super().__init__(parent=parent)
if sys.platform in ("win32", "darwin"):
    self.setHtml("")                      # force Chromium init now
if isinstance(self.window(), (FramelessWindow, FramelessMainWindow, FramelessDialog)):
    self.window().updateFrameless()       # restore the native chrome
```

- It restores the framed style (`0x86cf0008`, `0x96cf0008` once visible).
- It **sticks**: later `setHtml` calls and later views do not recreate the
  handle again.
- In Kilim the markdown pane is built before it is inserted into the
  window, so `FramelessWebEngineView`'s own `isinstance(window(), ...)`
  check cannot see the Lace window yet. Kilim therefore calls
  `self.updateFrameless()` once at the end of `KilimWindow._init_inner`,
  after all panes exist — one window-level call covers every view.
- A raw ctypes `SetWindowLongW` + `SetWindowPos(SWP_FRAMECHANGED)` also
  re-adds the bits (and `DwmSetWindowAttribute(hwnd, 33, DWMWCP_ROUND)`
  sets rounding), and both persist — but the `updateFrameless()` route is
  the library's own, needs no ctypes, and is the one to prefer.

### General rule

On Windows, a frameless top-level that hosts a GL child (WebEngine,
`QOpenGLWidget`, …) must re-apply its frameless chrome **after** that
child's first initialization. Anything that DWM-tunes the window at
startup must run after that point too, or it tunes a handle that is about
to disappear.

---

## 4. Checklist for a custom Lace title bar

1. `super().__init__(parent)`, hide/adjust `titleLabel` as desired.
2. Embed widgets at a computed index (see §1), same height as the bar.
3. Transparent QSS on the embedded menu bar; popups styled from the same
   dock-theme tokens.
4. `paintEvent` fills the rect with the theme background before `super()`.
5. `canDrag()` returns `False` over every interactive child.
6. `DockStyled` with `STYLE_CATEGORIES = (TITLE_BAR, SIDEBAR, CORE)` so
   theme switches restyle the bar.
7. If a `QWebEngineView` (or `QOpenGLWidget`) lives inside the window,
   call `window().updateFrameless()` after it initializes (§3).
8. Floats get a custom bar via `title_bar_mode = TitleBarMode.custom` plus
   `floating_title_bar = <descriptor>` — the main window's bar is the
   `title_bar=` argument to `FramelessLaceMainWindow`, not
   `title_bar_mode`.
