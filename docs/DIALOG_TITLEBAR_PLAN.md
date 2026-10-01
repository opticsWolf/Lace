# Dialog title bars: plan

**Status:** done. D1 released in 0.8.5 (`lace/title_bar_colors.py`, `lace/native_frame.py`);
D2–D4 in 0.9.0 (`lace/frameless_dialog.py`, `lace/dialogs.py`, `dev_smoke/smoke_dialogs.py`,
`docs/theming_and_geometry.md` §14). Not checked: Windows 10, and the colour dialog's
"Pick Screen Color" while embedded
**Target:** 0.8.x / 0.9
**Scope:** make every window an app shows (dialogs, message boxes, tool windows, Theme Studio)
match the themed custom title bar of `FramelessLaceMainWindow`.

---

## 1. Problem

A Lace app's own windows have a themed title bar, but any dialog it opens has the system frame:

| Window | Title bar today | Themed? |
|---|---|---|
| `FramelessLaceMainWindow` | `LaceStandardTitleBar` + `FramelessTitleBarStyler` | yes: bg, text, buttons, font |
| `FramelessFloatingDockContainer` | same bar + styler (`floating_dock_container_frameless.py:202`) | yes |
| `FloatingDockContainer` (native) | OS frame, `_apply_dwm_dark_frame` (`floating_dock_container.py:283`) | light/dark only |
| `QMessageBox`, `QInputDialog`, `QColorDialog`, app `QDialog`s | OS frame | **no**; follows the Windows light/dark setting, not the theme |
| `QFileDialog` (native mode, the default on Windows/macOS) | an OS dialog, not a `QWidget` | **no**, and Qt can't reach it |
| Theme Studio (`StudioWindow(QMainWindow)`) | OS frame | **no** |

The worst case is a light theme on a dark Windows setup, or the reverse: the dialog frame is the
opposite brightness to the app.

## 2. What exists

- **`FramelessTitleBarStyler`** (`lace/frameless_titlebar.py`). It styles *any* title bar widget
  from the tokens and registers with `DockStyleManager` (TITLE_BAR, CORE, PANEL), debouncing
  refreshes. It doesn't depend on a main window, so a dialog can reuse it unchanged.
- **Token contract used by the custom bar.**
  - Background: `SIDEBAR.bg_color`, falling back to `TITLE_BAR.bg_normal`.
  - Text: `TITLE_BAR.text_normal`.
  - Buttons: `TITLE_BAR.button_color`, `button_hover_bg`, `button_disable_clr`, `button_size`,
    `button_icon_size`, `button_corner_radius`.
  - Font: `TITLE_BAR.font_family`, `font_size`, `font_weight`.
- **`LaceStandardTitleBar`** (`lace/frameless_window.py:248`). It has one synchronous maximize
  path, the system menu on the icon, a `canDrag` veto for interactive children, and a theme paint.
- **`_FramelessChromeHealMixin` / `ensure_frameless_chrome`.** They restore the DWM bits after a
  `WinIdChange`.
- **`_enable_system_dark_mode_menus()`.** It makes the process accept dark mode, so native popup
  menus, and native common dialogs, follow the *system* light/dark mode.
- **`_apply_dwm_dark_frame(is_dark)`.** It sets `DWMWA_USE_IMMERSIVE_DARK_MODE` (20, then 19),
  but only on the native floating container, as a private method.
- **`qframelesswindow.FramelessDialog`.** Present in the installed package; nothing in Lace wraps
  it yet.
- **Registration path.** `DockManager.__init__` calls `parent._register_titlebar_theme()` when the
  parent is a frameless main window (`dock_manager.py:114`). Nothing tracks any other window.

## 3. Goals and non-goals

**Goals**
1. **G1.** Every native-framed top-level window gets the theme's title-bar colours where the OS
   allows it (Windows 11), and at least the right brightness (Windows 10), with nothing for the
   app to do.
2. **G2.** A frameless, fully themed dialog class that looks and behaves like the main window's
   title bar.
3. **G3.** Drop-in helpers for the common modal dialogs (message, question, text/item/int input,
   colour, file), built on G2.
4. **G4.** One written contract: which tokens drive a title bar, native or custom, on each
   platform.
5. **G5.** Retheme live: open dialogs follow a theme switch.

**Non-goals**
- Recolouring OS-owned dialogs beyond the light/dark mode the OS already gives them (see §5.4).
- macOS and Linux native frame colouring. The window manager owns the frame there. A macOS
  `NSAppearance` hook may come later (§10).
- Replacing `QMessageBox`'s full API (detailed text, escape button semantics, …). The helpers
  cover the common subset; the rest stay native-framed under G1.

---

## 4. Design overview

Two layers that complement each other:

```
            ┌────────────────────────── any top-level QWidget ─────────────────────────┐
            │                                                                          │
   frameless (FramelessWindowHint)                              native frame
            │                                                                          │
  FramelessLaceMainWindow / FramelessLaceWindow /                    Layer A: NativeFrameTheme
  FramelessLaceDialog (new)                                          (app-wide event filter)
            │                                                                          │
  FramelessTitleBarStyler (existing)                                 apply_native_frame(w)
            │                                                          DWM: dark mode (Win10+)
  full theme: bg, text, buttons, font                                       caption/text/border
                                                                            colour (Win11)
```

- **Layer A: native frame theming** (Phase D1). Automatic, broad and shallow: every native frame
  gets the right colours.
- **Layer B: frameless dialogs** (Phases D2 and D3). Opt-in, narrow and deep: pixel-identical to
  the main window's bar.

Both read the same tokens through one function (`title_bar_colors()`, §5.1), so they can't drift.

---

## 5. Phase D1: native frame theming (Layer A)

### 5.1 One source for title-bar colours

A new `lace/title_bar_colors.py`:

```python
@dataclass(frozen=True)
class TitleBarColors:
    background: QColor      # SIDEBAR.bg_color → TITLE_BAR.bg_normal
    text: QColor            # TITLE_BAR.text_normal
    text_inactive: QColor   # TITLE_BAR.text_normal at reduced alpha (or a token, see §9)
    border: QColor          # CORE outline token used by the card, or background
    is_dark: bool           # background.lightnessF() < 0.5

def title_bar_colors(sm=None) -> TitleBarColors: ...
```

`FramelessTitleBarStyler.refresh_style()` switches to it for its bg and text, so this is a pure
refactor for the existing bar. A unit test asserts the styler's QSS colours equal
`title_bar_colors()`.

### 5.2 `apply_native_frame(window)`

A new `lace/native_frame.py`, replacing the private `_apply_dwm_dark_frame`:

| DWM attribute | Id | OS | Value |
|---|---|---|---|
| `DWMWA_USE_IMMERSIVE_DARK_MODE` | 20 (19 before build 19041) | Win10 1809+ | `is_dark` |
| `DWMWA_BORDER_COLOR` | 34 | Win11 22000+ | `border` as COLORREF (`0x00BBGGRR`) |
| `DWMWA_CAPTION_COLOR` | 35 | Win11 22000+ | `background` |
| `DWMWA_TEXT_COLOR` | 36 | Win11 22000+ | `text` |

Rules:
- It's a no-op off Windows, and a no-op for windows with `FramelessWindowHint` (they have no
  caption).
- Each attribute is best-effort: a non-zero HRESULT is logged at debug level and skipped, so
  Win10 gets dark mode only.
- `DWMWA_CAPTION_COLOR` ignores alpha, so the colour is composited over the window background
  first.
- It's idempotent. Cache the last applied tuple per HWND (`window.property("_lace_frame_key")`)
  so repeat calls don't touch DWM.
- It forces a non-client repaint only when the value changed. DWM repaints the caption itself for
  34–36; after a dark-mode flip, `SetWindowPos(... SWP_FRAMECHANGED)` is needed on Win10.
- `FloatingDockContainer._apply_dwm_dark_frame` becomes a one-line call to it, and its tests move
  over.

### 5.3 `NativeFrameTheme`: the app-wide hook

It's an event filter on `QApplication` plus a style subscriber:

```python
class NativeFrameTheme(QObject):
    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Type.Show and obj.isWidgetType() and obj.isWindow():
            if _wants_native_frame(obj):
                apply_native_frame(obj)
        elif ev.type() == QEvent.Type.WinIdChange and ...:
            apply_native_frame(obj)          # new HWND, attributes lost
        return False

    def on_style_changed(self, category, changes):   # debounced like the styler
        for w in QApplication.topLevelWidgets():
            if w.isVisible() and _wants_native_frame(w):
                apply_native_frame(w)
```

`_wants_native_frame(w)` is true for a window type of `Window`, `Dialog` or `Tool`, with no
`FramelessWindowHint`, not a `Popup`/`ToolTip`/`SplashScreen`/`Drawer`, and not opted out through
`w.property("laceNativeFrame") is False`.

**Install.** `DockManager` installs one instance per `QApplication`, idempotently (a module
global, like `_DARK_MODE_OPTED_IN`), unless `DockManager(native_frames=False)` is given. It's also
public: `lace.install_native_frame_theme(app)` for apps that theme without a `DockManager`. The
Theme Studio installs it itself.

**Cost.** The filter sees every event, so it tests the type first (two int compares). `Show` on
top-level windows is rare. This matches how the FrameCap filters were measured in Phase 7.

### 5.4 What Layer A can't reach

- **Native `QFileDialog` (IFileDialog) and the native print/page setup dialogs.** They're OS
  windows with no Qt widget, so the filter never sees them. They follow the *system* light/dark
  mode through `SetPreferredAppMode(AllowDark)`, which is already on. Full theming needs the
  Qt-drawn file dialog: `lace.dialogs.get_open_file_name(..., native=False)`, from Phase D3.
- **Win10.** Dark mode only; no caption colour. The frame is black or white, not the theme
  colour.
- **Windows the app styled deliberately.** They can opt out with the `laceNativeFrame` property.

### 5.5 D1 tests

- `apply_native_frame` on an offscreen or mocked `dwmapi`: the right attribute ids, COLORREF
  packing (`QColor(0x12,0x34,0x56)` → `0x563412`), and a no-op for frameless windows and off
  Windows.
- Caching: a second call with the same theme doesn't call DWM (mock the call count).
- `NativeFrameTheme`:
  - a `QDialog` shown after install gets exactly one call;
  - a theme switch reapplies to visible native windows only;
  - popups and tooltips are ignored;
  - the opt-out property is respected.
- The refactor: styler colours equal `title_bar_colors()` for every preset in
  `tests/theme_sets.QUICK`.
- A Windows-only manual check (S-list): `QMessageBox` over the demo on Win11 in `cyberpunk_neon`
  and `light`; its caption matches the custom bar.

---

## 6. Phase D2: `FramelessLaceDialog` (Layer B)

### 6.1 Class

`lace/frameless_dialog.py`:

```python
class FramelessLaceDialog(_FramelessChromeHealMixin, FramelessDialog):
    def __init__(self, parent=None, title_bar: TitleBarDescriptor = None,
                 resizable: bool = True, buttons: str = "close"):  # "close" | "min_close" | "all"
```

- **Title bar.** `LaceStandardTitleBar`, or the descriptor through `_resolve_title_bar`. Min and
  max are hidden per `buttons`, and double-click-to-maximize is disabled unless `buttons == "all"`.
- **Styling.** Its own `FramelessTitleBarStyler(title_bar=self.titleBar, parent=self)`, so
  dialogs retheme live (G5). Dispose of it on `destroyed` and unregister from `DockStyleManager`.
  Check whether the styler already unregisters; if not, add `dispose()`. That's a leak fix the
  main window needs as well.
- **Layout.** A `QVBoxLayout`: title bar, then a content widget. `setContentWidget(w)` or
  `contentLayout()`; `layout()` must not be replaced by callers, which the docstring explains.
- **Heal.** `event()` handles `WinIdChange`, like `FramelessLaceWindow`.
- **Window icon and title.** Kept in sync: `windowTitleChanged` → `titleLabel`, and the icon as in
  the floating container (`floating_dock_container_frameless.py:155`).
- **Modality.** `exec()` and `open()` both work. `FramelessDialog` is a `QDialog`, so `accept()`,
  `reject()` and `done()` behave as usual.
- **Keyboard.** Escape → `reject()` (default `QDialog` behaviour; check the frameless base doesn't
  swallow it). Default and auto-default buttons work.
- **Placement.** Centred on `parentWidget().window()` at first show. On multi-screen setups it's
  clamped to that screen's `availableGeometry`, since frameless windows don't get the OS's
  placement.
- **Resize.** When `resizable=False`, fix the size and turn off the resize border
  (`setResizeEnabled(False)` in qframelesswindow).
- **Snap.** On Windows, remove `WS_MAXIMIZEBOX` when max is hidden, so Aero Snap and Win+Up don't
  maximize a dialog.
- **Shadow and corners.** Keep the qframelesswindow DWM shadow; Win11 rounds the corners through
  DWM like the main window.
- **Accessibility.** The title label is the accessible name, and the buttons keep their tooltips
  and accessible names from the base.

### 6.2 Shared code with the main window and floating window

Today `FramelessLaceMainWindow.__init__` and `FramelessLaceWindow.__init__` repeat
"resolve descriptor or upgrade to `LaceStandardTitleBar`, opt into dark menus, init heal state".
Pull that into `_init_lace_chrome(self, title_bar)` in `frameless_window.py`, then use it in all
three classes. It's a small refactor that keeps the three consistent from then on.

### 6.3 D2 tests

- It constructs offscreen: the title bar is a `LaceStandardTitleBar`, min and max are hidden for
  `buttons="close"`, and `titleLabel` follows `setWindowTitle`.
- Theme switch: title bar QSS and button colours change, the same as the main window's styler on
  the same theme.
- `exec()` returns on `accept()`/`reject()` driven by a `QTimer`. Escape rejects.
- Disposal: after `deleteLater` plus `sendPostedEvents(None, 52)`, the styler is unregistered and
  the style manager holds no reference to it (the same pattern as the FrameCap registry test).
- Heal: a simulated `WinIdChange` calls `ensure_frameless_chrome` once, coalesced.
- Placement: centred on the parent and clamped to the screen.

---

## 7. Phase D3: `lace.dialogs` helpers

A module mirroring the static Qt helpers. Each builds a `FramelessLaceDialog`, embeds the
matching Qt widget, and returns the same result type as Qt.

| Helper | Embeds | Returns |
|---|---|---|
| `message(parent, title, text, icon="info", buttons=Ok)` | custom body: icon label + text + `QDialogButtonBox` | `QDialogButtonBox.StandardButton` |
| `question(parent, title, text, buttons=Yes\|No, default=...)` | same | `StandardButton` |
| `warning(...)`, `critical(...)`, `information(...)`, `about(...)` | same | `StandardButton` / None |
| `get_text`, `get_item`, `get_int`, `get_double` | `QInputDialog` with `Qt.Widget` flags | `(value, ok)` like Qt |
| `get_color(initial, parent, title, options)` | `QColorDialog` with `Qt.Widget` flags, `NoButtons` off | `QColor` (invalid on cancel) |
| `get_open_file_name`, `get_open_file_names`, `get_save_file_name`, `get_existing_directory` | `native=True` → Qt static (OS dialog, §5.4); `native=False` → `QFileDialog` with `DontUseNativeDialog`, `Qt.Widget` flags | `(path, filter)` like Qt |

Implementation notes:
- **Embedding.** Qt's dialogs are `QDialog`s. Embed each by clearing the window flags
  (`setWindowFlags(Qt.WindowType.Widget)`) and forwarding its `accepted`/`rejected` to the
  host's `accept()`/`reject()`. Check this for `QColorDialog`'s screen colour picker (it grabs the
  mouse on a top-level window) and for `QFileDialog`'s sidebar.
- **Message body.** It's built, not embedded: `QMessageBox` lays itself out on `showEvent` and
  resizes its own window, so embedding it is fragile. The icon comes from
  `style().standardIcon(SP_MessageBox*)`, which LaceStyle already themes. Text is selectable
  (`TextSelectableByMouse`) and rich text is auto-detected, as in `QMessageBox`.
- **Button order.** `QDialogButtonBox` gives each platform its native order.
- **Signature.** `parent` comes first, to match Qt's static helpers, so migrating is a rename.
- **No `DockManager`?** The helpers still work; the styler falls back to the default theme.
- **Opt-out.** `lace.dialogs.set_default_frameless(False)` makes every helper call the plain Qt
  static function, which Layer A still themes.

Demos and Theme Studio:
- `demo_app_custom_titlebar_menus.py`: `QMessageBox.information`/`about` → `lace.dialogs`.
- The demos' "load theme" `QFileDialog.getOpenFileName` → `lace.dialogs.get_open_file_name`
  (native, so it's unchanged by default).
- `theme_kit/studio.py`: `QColorDialog.getColor` → `lace.dialogs.get_color`. The file dialogs stay
  native. The Studio window itself uses Layer A; a frameless Studio is a separate, optional item.

### 7.1 D3 tests

- For each helper: the host is a `FramelessLaceDialog`, the Qt widget is embedded (not a window),
  and the return value matches Qt's for accept and cancel, driven by `QTimer` + `QTest` keys.
- `message(..., buttons=Yes|No)` returns the clicked button; Escape returns the escape button,
  using Qt's rules (`NoButton` if none).
- `get_file(native=False)` embeds the Qt file dialog; `native=True` calls the Qt static function
  (mocked).
- Smoke: `dev_smoke/smoke_dialogs.py` opens each helper under `--themes auto` offscreen, grabs it
  and checks the title-bar pixels equal `title_bar_colors().background`. Added to `run_all.py`.

---

## 8. Phase D4: docs, screenshots, release

- `docs/theming_and_geometry.md` gets a new section, "Title bars":
  - the token contract (§2);
  - Layers A and B;
  - a platform table (Win11 full caption colour, Win10 dark mode only, macOS/Linux WM frame);
  - the file-dialog limitation and the opt-outs.
- `docs/ARCHITECTURE.md`: a section on `native_frame`, `NativeFrameTheme`, `FramelessLaceDialog`
  and `lace.dialogs`.
- `docs/QUICK_REFERENCE.md`: the helper table.
- `screenshot_themes.py`: a new special state `dialog_<theme>.png`, a message box over the main
  window. It's a screen grab, so it goes with the special states, not the standard set.
- README: one line in the features list. CHANGELOG entry.

---

## 9. Decisions (defaults proposed)

| # | Question | Proposal |
|---|---|---|
| Q1 | Is Layer A on by default through `DockManager`? | **Yes**, with `native_frames=False` to opt out. Its only effect is colouring frames the app didn't style. |
| Q2 | Do the file-dialog helpers default to native or Qt-drawn? | **Native.** It keeps OS features (recent places, cloud providers); the Qt-drawn one is opt-in. |
| Q3 | Inactive caption: dim the text or keep it? | Win11 DWM has no inactive text attribute, so set 36 on `WindowActivate`/`WindowDeactivate` from the filter, using `text_inactive` = text at 60 % alpha over the bg. This needs no new token; add `TITLE_BAR.text_inactive` only if a theme asks for it. |
| Q4 | Border colour source? | The card outline token when the theme has one (visible frames themes); otherwise `DWMWA_COLOR_DEFAULT` (`0xFFFFFFFF`) so Windows keeps its accent border rule. |
| Q5 | Frameless Theme Studio? | Not in this plan; Layer A covers it. Revisit after D2. |
| Q6 | Should the helpers live in `lace.dialogs` or on `FramelessLaceDialog` as static methods? | `lace.dialogs` (a module with functions, like `QMessageBox`'s statics but importable one by one). |

## 10. Risks

- **DWM attribute support varies by build.** Mitigation: per-attribute best effort, and a debug
  log. The unit tests mock `dwmapi`; the real behaviour is on the manual S-list.
- **App-wide filter conflicts with an app that sets DWM colours itself.** Mitigation: the
  `laceNativeFrame` property plus the global opt-out; the cache makes Lace write only on a theme
  change or a new HWND.
- **Embedding `QColorDialog`/`QFileDialog` as a widget.** Some Qt versions assume the dialog is a
  window (the screen colour picker, size grip). Mitigation: a smoke test per helper; fall back to
  the plain static function under Layer A if the embedded one misbehaves on a Qt version (a
  version check in `lace.dialogs`).
- **Frameless modal dialogs and focus.** A frameless window can lose the OS "flash owner when you
  click the disabled parent" behaviour. Mitigation: check it on Win11; qframelesswindow keeps
  `WS_CAPTION` for DWM, which normally keeps it.
- **macOS.** `FramelessDialog` there uses the transparent title bar path; check the traffic-light
  buttons are hidden or placed correctly, or fall back to Layer A (native) on macOS for D2.
  Decide after a test run.
- **Styler leak.** Each dialog registers a styler; if unregistering is missing, the style manager
  grows with every dialog opened. The D2 disposal test guards this.

## 11. Order and size

| Phase | Content | Size | Depends on |
|---|---|---|---|
| D1 | `title_bar_colors`, `apply_native_frame`, `NativeFrameTheme`, native floating-container switch | S–M | none |
| D2 | `FramelessLaceDialog`, `_init_lace_chrome` refactor, styler `dispose()` | M | D1 (colours) |
| D3 | `lace.dialogs`, demo and Studio migration, `smoke_dialogs.py` | M | D2 |
| D4 | docs, `dialog_<theme>` screenshots, CHANGELOG | S | D1–D3 |

Commit per phase. D1 alone fixes the most visible problem (the dark/light mismatch and caption
colour on Win11) and can ship on its own as 0.8.1.

## 12. Acceptance

- On Win11, every Qt-created window (message box, input, colour, app dialogs, Studio, native
  floating container) shows the theme's title-bar background and text. It follows a theme switch
  within one event pass.
- On Win10, those windows match the theme's brightness.
- `lace.dialogs` helpers look identical to the main window's title bar in every `QUICK` theme (the
  smoke pixel check) and return the same values as their Qt counterparts.
- No styler or filter leaks: the style manager's subscriber count is back at its baseline after
  opening and closing 20 dialogs.
- Unit, visual and smoke tests green on the CI matrix. The manual S-list is checked on Win11 and
  Win10.
