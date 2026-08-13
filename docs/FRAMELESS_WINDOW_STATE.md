# Frameless floating windows — window-state defects on Windows 11

Scope: `TitleBarMode.custom`, i.e. `FramelessFloatingDockContainer`
(`lace/floating_dock_container_frameless.py`) on top of
`FramelessLaceWindow` → `qframelesswindow.WindowsFramelessWindow` (0.8.1),
PySide6 6.11.1, Windows 11 26200.

Everything below was measured on this machine with the real `windows` QPA
plugin; the probe transcripts are reproduced inline. The native-frame
container (`FloatingDockContainer`) is used as the control.

---

## 0. Reported symptoms

All four are fixed as of 0.5.54; this document is kept as the record of
what was wrong and why, because the mechanisms are not obvious and the
Win32 behaviour will outlive the code.

1. A minimized float does not appear in the taskbar. *(fixed 0.5.51)*
2. A float maximized by double-clicking the title bar cannot be "ripped"
   out of maximize by dragging. *(fixed 0.5.53)*
3. A float maximized with the title bar's **maximize button** cannot be
   restored by double-clicking the title bar. *(fixed 0.5.52)*
4. After a maximize/restore cycle the float often can no longer be moved.
   *(fixed 0.5.52)*

Symptom 1 stands alone. Symptoms 3 and 4 are two faces of a single defect,
and symptom 2 is a missing gesture that the same defect made unfixable.

---

## 1. The cast

| Piece | File | Role |
| --- | --- | --- |
| `FramelessFloatingDockContainer` | `lace/floating_dock_container_frameless.py` | the float; owns the drag state machine |
| `FloatingContainerBehaviour` | `lace/floating_behaviour.py` | chrome-independent half, shared with the native float |
| `FramelessLaceWindow` | `lace/frameless_window.py` | thin subclass of `qframelesswindow.FramelessWindow` |
| `LaceStandardTitleBar` | `lace/frameless_window.py` | subclass of `qframelesswindow.StandardTitleBar`; overrides `mouseDoubleClickEvent` |
| `TitleBarBase` | `qframelesswindow/titlebar/__init__.py` | owns `minBtn` / `maxBtn` / `closeBtn` and their wiring |
| `WindowsMoveResize` | `qframelesswindow/utils/win32_utils.py` | `startSystemMove`, `toggleMaxState` |

---

## 2. Root cause: two maximize mechanisms on one window

There are **four** ways a float gets maximized, and they do not use the same
mechanism.

| # | Entry point | Implementation | Mechanism |
| --- | --- | --- | --- |
| 1 | Double-click the title bar | `LaceStandardTitleBar.mouseDoubleClickEvent` → `showMaximized()` / `showNormal()` | **Qt** |
| 2 | Dock-area ⛶ button on a solo-area float | `DockContainerWidget.toggle_maximize_dock_area` ([dock_container_widget.py:842](../lace/dock_container_widget.py#L842)) | **Qt** |
| 3 | Layout restore | `LayoutSerializer` → `fw.showMaximized()` ([layout_serializer.py:302](../lace/layout_serializer.py#L302)) | **Qt** |
| 4 | **Title-bar maximize button** | `TitleBarBase.maxBtn.clicked` → `qframelesswindow.utils.toggleMaxState` | **Win32** |

Fixed in 0.5.52: `LaceStandardTitleBar.__init__` disconnects the base wiring
and reconnects `maxBtn` to `toggle_max_state()`, the same call the
double-click makes. Entry points 2 and 3 route through the same helper, so
all four are one mechanism. The rest of this section is the diagnosis that
led there, kept because the OS can still maximize a window behind Lace's
back and the recovery path below is what handles that.

`toggleMaxState` on Qt ≥ 6.8 (we are on 6.11.1) does:

```python
win32gui.PostMessage(int(window.winId()), win32con.WM_SYSCOMMAND,
                     win32con.SC_MAXIMIZE, 0)   # or SC_RESTORE
releaseMouseLeftButton(window.winId())
```

Lace already knew this path was trouble — `LaceStandardTitleBar` exists
specifically to replace the async `SC_MAXIMIZE` with a synchronous
`showMaximized()`. But it only replaced the **double-click**. The maximize
*button* was left on the Win32 path, so one window now has two disagreeing
notions of "maximized".

### 2.1 Why the two do not round-trip

For a **frameless** window, Qt's `showMaximized()` is a pure geometry
change: it resizes the widget to the available screen rect and records
`Qt::WindowMaximized` internally. It never calls `ShowWindow(SW_MAXIMIZE)`,
so Win32's window placement stays `SW_NORMAL`. The Win32 path does the
opposite: it sets `SW_MAXIMIZED` and Qt merely observes the result.

Measured (probe 7 — a fresh float at `(x, 150, 500, 400)` each time):

```
A) native SC_MAXIMIZE -> native SC_RESTORE
    start                      QtMax=False win32=NORMAL geom=(100, 150, 500, 400)
    after SC_MAXIMIZE          QtMax=True  win32=MAX    geom=(0, 0, 3072, 1232)
    after SC_RESTORE           QtMax=False win32=NORMAL geom=(100, 150, 500, 400)   OK

B) Qt showMaximized -> native SC_RESTORE
    start                      QtMax=False win32=NORMAL geom=(700, 150, 500, 400)
    after showMaximized        QtMax=True  win32=NORMAL geom=(0, 0, 3072, 1232)
    after SC_RESTORE           QtMax=True  win32=NORMAL geom=(0, 0, 3072, 1232)     STUCK

C) native SC_MAXIMIZE -> Qt showNormal        <-- the reported case
    start                      QtMax=False win32=NORMAL geom=(1300, 150, 500, 400)
    after SC_MAXIMIZE          QtMax=True  win32=MAX    geom=(0, 0, 3072, 1232)
    after showNormal           QtMax=True  win32=MAX    geom=(0, 0, 3072, 1232)     no-op
    after showNormal #2        QtMax=False win32=MAX    geom=(0, 0, 3072, 1232)     DESYNCED

D) Qt showMaximized -> Qt showNormal
    ... round-trips cleanly, twice.                                                 OK
```

Case **C** is the one users hit, and it is worse than a no-op. The first
`showNormal()` does nothing at all. The second one flips *Qt's flag* to
`False` while the window stays maximized. From then on `isMaximized()`
lies, so the next double-click takes the `else` branch and calls
`showMaximized()` — the float can never be restored again by any Qt-side
caller. Entry points 2 and 3 read the same lying flag
(`is_area_maximized()` at [dock_container_widget.py:759](../lace/dock_container_widget.py#L759)),
so the dock-area ⛶ icon goes wrong too.

Cases A and D are each individually correct. **Only the mixture is broken.**

---

## 3. Symptom by symptom

### 3.1 Minimized floats do not reach the taskbar — FIXED in 0.5.51

Two independent facts combine.

**The window is owned.** The float is constructed as
`super().__init__(dock_manager.root_container())`
([floating_dock_container_frameless.py:69](../lace/floating_dock_container_frameless.py#L69))
and then promoted with `Qt.Window`. Qt gives a parented top-level window
the parent's `HWND` as its *owner*. Win32 gives an owned window a taskbar
button only when `WS_EX_APPWINDOW` is set. Measured:

```
=== frameless float ===
  style  : WS_CAPTION WS_THICKFRAME WS_MINIMIZEBOX WS_MAXIMIZEBOX WS_SYSMENU WS_POPUP
  exstyle: -
  owner  : 2035266     (the main window)
  -> taskbar button expected: False

=== NATIVE float (control) ===
  style  : WS_CAPTION WS_THICKFRAME WS_MAXIMIZEBOX WS_SYSMENU WS_POPUP
  missing: WS_MINIMIZEBOX
  owner  : 2035266
  -> taskbar button expected: False
```

**Only the frameless float can actually be minimized.** Both floats are
owned, but the native one has no `WS_MINIMIZEBOX` and no minimize
affordance, so nobody ever notices. The frameless one gets
`WS_MINIMIZEBOX` from `WindowsWindowEffect.addWindowAnimation()` (which
`updateFrameless()` calls) *and* shows a `minBtn` wired to
`window().showMinimized()`. So it minimizes to nowhere:

```
[after minimize] isMin=True IsIconic=True showCmd=SW_MINIMIZED
                 owner=1312016 APPWINDOW=False TOOL=False
```

There is a third inconsistency in the same area: the float's Qt window
flags are

```python
Qt.Window | Qt.FramelessWindowHint | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint
```

— **no `Qt.WindowMinimizeButtonHint`**, while the title bar shows a
minimize button that works. The declared capabilities and the offered
buttons disagree. The same literal is repeated in
`update_window_flags_from_config()`, so any fix has to land in both places
(lines 112 and 255).

**The fix (0.5.51).** A new opt-in flag, `DockFlags.floating_taskbar_button`:

* set — the float's window flags gain `Qt.WindowMinimizeButtonHint`,
  `FloatingContainerBehaviour._apply_taskbar_presence()` ORs
  `WS_EX_APPWINDOW` onto the handle, and the title bar's `minBtn` is shown;
* cleared (the default) — the ex-style is removed and `minBtn` is hidden, so
  nothing can throw a float away. Hiding it also widens the draggable
  region, since qframelesswindow's `_isDragRegion()` measures only visible
  buttons.

The ex-style is re-applied after every `setWindowFlags()` — the recreated
handle does not inherit it — and it is set while the window is hidden so
the following `show()` is what the shell reads. The flag works on both
float implementations: the helper and the `_wants_taskbar_button()` predicate
live in the shared mixin, and each container has its own `_window_flags()`,
which also collapses the flag literal that used to be spelled twice per
class (fix 4 below).

Verified against the real shell: with the flag set the taskbar shows the
Win11 "stacked card" indicator for a second window of the same app, and it
survives the minimize, so the float is clickable again. Toggling the flag on
a live float adds and removes the button through
`update_window_flags_from_config()`.

### 3.2 A maximized float cannot be dragged out of maximize — FIXED in 0.5.53

Nothing in the chain restores the window before moving it.

`FramelessFloatingDockContainer.eventFilter` routes every title-bar mouse
event into `_handle_titlebar_drag`, which **consumes** `MouseMove`
unconditionally (`return True` on both the drag-start and the sub-threshold
branch, lines 672/675/682). `TitleBarBase.mouseMoveEvent` therefore never
runs — by design, Lace drives the move itself. On the threshold crossing it
calls `startSystemMove(self, globalPos)`, which is

```python
win32gui.ReleaseCapture()
win32api.SendMessage(hwnd, WM_SYSCOMMAND, SC_MOVE | HTCAPTION, 0)
```

Two problems:

* Neither Lace nor qframelesswindow ever calls `showNormal()` on
  drag-start. Un-maximize-on-drag is simply not implemented anywhere in
  the stack — upstream qframelesswindow has the same gap.
* `SC_MOVE` is the *system-menu* move command, not the caption drag. The
  rip-out gesture Windows implements natively lives in
  `WM_NCLBUTTONDOWN`/`HTCAPTION`, which a frameless window never receives
  for its client-area title bar.

Measured offscreen with `startSystemMove` stubbed: press + move past the
threshold on a maximized float leaves `isMaximized() == True` and calls
`startSystemMove` once — the window stays maximized and the OS is asked to
move a maximized window.

**The fix (0.5.53).** `_restore_under_cursor()` runs at the drag threshold
(and, on platforms where the press starts the move, at the press). It
restores the window and places it so the pointer keeps the same fraction
across the title bar — grab a maximized float near its right edge and it
comes loose near its right edge, instead of jumping so a corner lands under
the pointer.

One ordering trap, measured on both platforms: `showNormal()` does **not**
apply the geometry before it returns, so reading `size()` afterwards still
measures the maximized window, and a plain `move()` then loses to Qt's own
deferred restore. The restored size is therefore taken from
`normalGeometry()` *before* restoring, and the whole rect is applied with
one `setGeometry()` afterwards.

### 3.3 Double-click does not restore after the maximize button — FIXED in 0.5.52

This is case **C** of §2.1 verbatim. Instrumented run:

```
== maximize via maxBtn (real click) ==
  isMaximized: True   geom: (0, 0, 3072, 1232)

== dblclick #1 (expect restore) ==
    >> mouseDoubleClickEvent  isMax=True
    << after handler          isMax=False   geom=(0, 0, 3072, 1232)
  isMaximized: True   geom: (0, 0, 3072, 1232)      <-- reverted

== dblclick #2 ==
    >> mouseDoubleClickEvent  isMax=True
    << after handler          isMax=False   geom=(0, 0, 3072, 1232)
  isMaximized: False  geom: (0, 0, 3072, 1232)      <-- flag flipped, window did not
```

The handler itself is correct and does run. `showNormal()` is the wrong
undo for a `SC_MAXIMIZE` maximize.

For contrast, maximizing *and* restoring by double-click both work (§2.1
case D) — which is why this only reproduces when the maximize button was
used first.

### 3.4 The float loses the ability to be moved — FIXED in 0.5.52

Direct consequence of being left at `showCmd == SW_MAXIMIZED`: Windows
refuses `SC_MOVE` for a zoomed window. Measured (probe 8) — on a natively
maximized float, `SendMessage(WM_SYSCOMMAND, SC_MOVE | HTCAPTION)` returns
without entering the modal move loop:

```
showCmd: 3 (3 == SW_MAXIMIZED)
geometry before: (0, 0, 3072, 1232)
sending WM_SYSCOMMAND SC_MOVE|HTCAPTION ...
SendMessage returned after 0.1 ms
geometry after : (0, 0, 3072, 1232)
VERDICT: REFUSED (no modal loop)
```

(The same rule is why the system menu greys out *Move* while maximized —
Lace's own Qt fallback menu encodes it at
[frameless_window.py:211](../lace/frameless_window.py#L211).)

So after the §3.3 sequence the float is in the terminal state: Win32 says
maximized (no moving), Qt says normal (no restoring). The title bar is
still `canDrag()`-able and `_handle_titlebar_drag` still runs the whole
state machine cleanly — it just asks the OS to do something the OS will
not do. Verified that the drag state machine itself is *not* the culprit:
after a maximize/restore cycle `_dragging_state` is `inactive`,
`_os_move_active` is `False`, `_frameless_drag_filter` is `False`,
`_titlebar_drag_start` is cleared and no title-bar button is stuck
`PRESSED`.

The word "often" in the report is explained by which entry point was used:
double-click-only sessions never desync, so the window keeps moving. The
full entry-point matrix from the smoke check makes the boundary exact —
every same-mechanism pair round-trips, every mixed pair breaks:

| maximized by ↓ / restored by → | maximize button | double click | dock-area ⛶ |
| --- | --- | --- | --- |
| **maximize button** (was Win32) | OK | **broken** | **broken** |
| **double click** (Qt) | **broken** | OK | OK |
| **dock-area ⛶** (Qt) | **broken** | OK | OK |

All nine round-trip since 0.5.52, and every cell now ends at `SW_NORMAL`.

**The fix (0.5.52).** `lace.util` grew three helpers that all four entry
points share:

* `is_window_maximized()` — asks the OS first. Its answer is the one that
  decides whether the window can still be moved, and it stays right when
  Qt's has gone stale.
* `restore_window()` — un-maximizes through whichever mechanism maximized
  it: `ShowWindow(SW_RESTORE)` for a native maximize, `showNormal()`
  otherwise. `ShowWindow` rather than a posted `SC_RESTORE` because it is
  synchronous and Windows ignores `SC_*` while a mouse button is held —
  the exact state a double-click is in.
* `toggle_window_maximized()` — the two together.

This matters beyond the button, because the OS can maximize a float behind
Lace's back: Aero Snap against the top edge (reachable from our own drag,
which runs the OS move loop) and Win+Up both produce a real
`SW_MAXIMIZED`. Before, that state was terminal. The smoke check exercises
it directly — a posted `SC_MAXIMIZE`, then restore through each of the
three entry points.

### 3.5 A second, independent contributor: the stranded button state — FIXED in 0.5.54

`qframelesswindow.TitleBarButton` sets `PRESSED` in `mousePressEvent` and
**never clears it in `mouseReleaseEvent`** — the only paths back are
`enterEvent` and `leaveEvent`. Since

```python
canDrag(pos) = _isDragRegion(pos) and not _hasButtonPressed()
```

a button left in `PRESSED` makes the *whole title bar* undraggable, and
`_handle_titlebar_drag` then declines every press
([floating_dock_container_frameless.py:600](../lace/floating_dock_container_frameless.py#L600)).
Measured offscreen: after a complete press+release on `maxBtn` the state is
still `PRESSED` and `canDrag()` is still `False`.

On a real display this usually self-heals — maximizing resizes the window
and moves the right-aligned button out from under the cursor, which
delivers the `leaveEvent` — which is why the symptom is intermittent rather
than permanent. It is an upstream defect, but Lace is the one that depends
on `canDrag()` for its drag routing.

Note `_hasButtonPressed()` iterates every `TitleBarButton` child with no
visibility check, so the minimize button blocks the bar even in the default
configuration where §3.1 hides it.

**The fix (0.5.54).** `LaceStandardTitleBar` installs itself as an event
filter on its buttons and clears the state on `MouseButtonRelease` —
`HOVER` if the pointer is still over the button, `NORMAL` otherwise. The
button's own action is unaffected: the filter runs before delivery, and
`QAbstractButton` emits `clicked()` from `isDown()`, not from this state.

---

## 4. Where a fix goes

All five landed: items 3 and 4 in 0.5.51 (§3.1), item 1 in 0.5.52
(§3.3/§3.4), item 2 in 0.5.53 (§3.2), item 5 in 0.5.54 (§3.5).

1. ~~**Pick one mechanism and route every entry point through it.**~~ Done
   in `LaceStandardTitleBar.__init__` — `TitleBarBase.__toggleMaxState` is
   name-mangled and cannot be overridden, so `maxBtn.clicked` is
   disconnected and reconnected. It covers the main window and every float
   at once, since both use that class.
2. ~~**Restore before dragging.**~~ Done — `_restore_under_cursor()`, §3.2.
3. ~~**Make declared and offered window buttons agree**, and decide the
   taskbar question.~~ Done — `DockFlags.floating_taskbar_button`, §3.1.
4. ~~**Deduplicate the window-flag literal** repeated at `__init__` and
   `update_window_flags_from_config`.~~ Done — `_window_flags()`.
5. ~~**Clear the button state on release.**~~ Done — an event filter on the
   buttons in `LaceStandardTitleBar`, §3.5.

## 5. What the new tests pin

`tests/test_frameless_window_state.py` — 29 tests, offscreen, runs in CI,
**all passing**. They cover the full 3×3 maximize/restore matrix, the
taskbar flag in both states, the rip-out keeping the grab in place, and
every title-bar button clearing its own pressed state. Each started as an
`xfail(strict=True)` reproduction and lost the marker when its fix landed;
strict is what forced that, since a fixed defect XPASSes and fails the
suite. Neither native entry point is allowed to reach a real HWND —
`toggleMaxState` and `startSystemMove` are trapped by fixtures, which is
also what makes the mechanism visible from a headless test.

`dev_smoke/smoke_frameless_winstate.py` — needs a real display and Win32;
listed in `run_all.py`'s `NEEDS_DISPLAY`, so it does not run in the normal
smoke pass. It reads `GetWindowPlacement` and the Win32 ex-styles
alongside Qt's view, exercises both states of the taskbar flag, walks the
full 3×3 maximize matrix, recovers from an OS-side `SC_MAXIMIZE` through
each entry point, and checks the geometry round-trip, the still-movable
invariant and the rip-out gesture, including that the grab keeps its place
across the restored title bar. **All 49 checks pass as of 0.5.53.**
