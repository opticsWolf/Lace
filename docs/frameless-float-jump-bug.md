# Frameless Floating Dock Container Jump / Vanish Bug

## Summary

Frameless floating dock containers (FDCs) would sporadically **jump to a wrong
position** (often off-screen) or **appear to vanish** when multiple floating
windows were open. The bug was most noticeable when at least one of the floats
contained a "special" dock widget such as a non-closable dock widget, but it
could affect any frameless float.

The root cause was a combination of two problems:

1. **A stale drag state** that survived after the OS move loop consumed the
   mouse release.
2. **A wrong coordinate mapping** when a dock area title bar (inner tab bar)
   was used to drag an already-floating container.

Both problems caused `move_floating()` to receive a drag-offset that was really
a global screen position. `move_floating()` then moved the window to
`cursor - global_position`, which threw it far off-screen.

## Reproduction

With three frameless floats open (e.g. two standard editors + one
non-closable logger):

1. Drag one float by its inner dock-area title bar (the tab/title strip above
   the dock widget content).
2. Release the mouse.
3. Start another drag on the same or a different float.

The second drag could start with a `drag_start` value such as
`(1303, 599)` instead of a small local offset such as `(66, 16)`. The window
would then jump to e.g. `(-421, 123)` and could leave the visible screen area.

Debug output before the fix looked like this:

```text
[FDC.move_floating] border=0.0 drag_start=QPoint(1303, 599) cursor=QPoint(882, 722)
                    move_to=QPoint(-421, 123) current=QPoint(651, 671)
```

## Root cause analysis

### 1. Stale drag state after the OS move loop

The frameless variant routes title-bar drags through
`_handle_titlebar_drag()`, which calls the OS move loop
(`startSystemMove()` / `WM_SYSCOMMAND SC_MOVE`). That loop is **modal**: it
blocks Qt's event loop while the window follows the cursor. When the user
releases the mouse button, the OS loop consumes the release and returns.

In some cases the Qt `MouseButtonRelease` event never reached the dock-drag
state machine, so the float stayed in `DragState.floating_widget` with its
application-level event filter still installed. The next unrelated mouse press
or release elsewhere (for example clicking a dock widget in another floating
window) was then interpreted as the end of the stale drag:

```text
[FDC._end_programmatic_drag] -> [_finalize_drag] -> [drop into other window]
```

Because the cursor happened to be over another dock container, the float
silently docked into it and was deleted, making it "vanish".

### 2. Wrong coordinate mapping for dock-area title bar drags

When a dock area is already the only area in a floating container, dragging its
inner title bar re-uses the existing float instead of creating a new one. The
code in `dock_area_title_bar.py` (and similarly in `dock_widget_tab.py`) tried
to compute the drag offset like this:

```python
mapped_start_pos = self.mapTo(floating_window, self._drag_start_mouse_position)
floating_window.start_dragging(mapped_start_pos, floating_window.size(), self)
```

`mapTo()` maps a point from the source widget's coordinate system into the
target widget's coordinate system. When the dock area title bar and the float
are in the same window, this works and produces a small local offset.

However, during the interaction the dock area can be reparented (for example
after a focus change, activation, or a previous partial drop). When the title
bar and the float are no longer in the same top-level window, `mapTo()` walks
through the desktop and produces a value that is effectively a **global screen
position**. `move_floating()` then does:

```python
move_to_pos = QCursor.pos() - self._drag_start_mouse_position
```

Subtracting a global screen position from the current cursor position moves the
window to the screen edge or off-screen.

The same pattern existed in `dock_widget_tab.py`.

### 3. Extra movement after the OS move loop

The title-bar mouse-move handler called `move_floating()` whenever the state
was `floating_widget`. If the OS move loop had already moved the window, a
subsequent queued `MouseMove` event would call `move_floating()` again with a
stale local offset, producing an additional jump.

## Fixes applied

### A. Cancel stale drag state aggressively

A new helper `_cancel_stale_drag()` resets:

- drag state to `DragState.inactive`
- any grabbed mouse handler
- the transient app-level event filter
- the drop container and overlays

It is called in three places:

1. **On any new `MouseButtonPress`** seen by the FDC's event filter while a
   drag is still armed. This prevents a click in another floating window from
   being treated as the end of the stale drag.
2. **At the start of a new title-bar press** in `_handle_titlebar_drag()`, so
   an old drag cannot leak into a new one.
3. **On `NonClientAreaMouseButtonPress`** in `event()`, so a resize-border
   click does not start or perpetuate a stale drag.

### B. Safety nets for consumed releases

- `moveEvent()` now checks `QApplication.mouseButtons()`. If no button is held
  while the FDC thinks it is dragging, the drag is stale and is cancelled.
- `changeEvent()` does the same check on `ActivationChange`. A focus change
  with no button held means the user is done interacting, so any stale drag is
  cleaned up before it can jump on the next move.

### C. Do not manually move the window after the OS move loop

In `_handle_titlebar_drag()` mouse-move, `move_floating()` is now only called
when `_os_move_active` is `False` (the manual fallback). If the OS loop was
used, the OS has already positioned the window correctly and our stale local
offset must not be applied again.

### D. Fix coordinate mapping via the global screen

In both `lace/dock_area_title_bar.py` and `lace/dock_widget_tab.py`, the
mapping was changed from a direct `mapTo()` to a global-roundtrip:

```python
mapped_start_pos = floating_window.mapFromGlobal(
    self.mapToGlobal(self._drag_start_mouse_position)
)
floating_window.start_dragging(mapped_start_pos, floating_window.size(), self)
```

This always produces the cursor position **relative to the floating window's
client top-left**, regardless of whether the dock area/title bar/tab has been
reparented to a different window.

### E. Clean up the transient event filter on title-bar release

`_handle_titlebar_drag()` now removes the transient app-level event filter in
both the "click without drag" and "real drag" release branches, preventing the
filter from outliving the interaction.

### F. Do not start a dock drag from OS resize borders

`event()` no longer transitions from `inactive` to `mouse_pressed` on
`NonClientAreaMouseButtonPress`. Those events come from the OS resize borders
(HTTOP, HTLEFT, etc.), not from a native title bar. Treating them as the start
of a dock drag armed the state machine for a resize-border click and left it
stuck.

## Verification

After the fixes:

- `move_floating()` logs only small local offsets (e.g. `drag_start=(66, 16)`
  or `(81, 19)`) and the window follows the cursor smoothly.
- No more `drag_start` values in the thousands that produce negative
  `move_to` coordinates.
- Clicking a dock widget in another floating window can no longer trigger a
  phantom drop.
- The smoke suite still passes (only pre-existing baseline failures remain).

## Code changes

### `lace/floating_dock_container_frameless.py`

#### New `_cancel_stale_drag()` helper

```python
    def _cancel_stale_drag(self):
        """End a drag whose release was consumed (e.g. by the OS move loop)
        without dropping into a container.

        Called when a new mouse press starts while a drag is still armed, so
        the new interaction's release can never be mistaken for the drag's
        release and trigger a phantom drop.
        """
        self._set_state(DragState.inactive)
        if self._mouse_event_handler is not None:
            try:
                self._mouse_event_handler.releaseMouse()
            except RuntimeError:
                pass
            self._mouse_event_handler = None
        self._titlebar_drag_start = None
        self._os_move_active = False
        self._remove_frameless_drag_filter()
        if self._drop_container is not None:
            self._drop_container = None
            if self._dock_manager:
                self._dock_manager.container_overlay().hide_overlay()
                self._dock_manager.dock_area_overlay().hide_overlay()
```

#### Stale-drag cancellation on any new press

```python
        # A new press starting elsewhere while a drag is still armed means the
        # previous drag's release was consumed (e.g. by the OS move loop) and
        # never reached the state machine.  Without this, the new interaction's
        # release would be mistaken for the drag's release and finalize the
        # drag into whatever container the cursor happens to be over — e.g.
        # clicking a dock widget in another floating window would drop this float
        # into it and delete it ("vanishing").  End the stale drag at the press
        # instead, and let the press reach its real target.
        if (event.type() == QEvent.MouseButtonPress
                and self._dragging_state != DragState.inactive):
            self._cancel_stale_drag()
            return False
```

#### Cancel stale drag at the start of a new title-bar press

```python
        if etype == QEvent.MouseButtonPress:
            if event.button() != Qt.LeftButton:
                return False
            if not getattr(self.titleBar, "canDrag", lambda p: True)(
                    event.position().toPoint()):
                return False  # press on a min/max/close button
            # A previous drag may still be armed (its release was consumed by
            # the OS move loop) — end it cleanly before starting a new drag so
            # stale drop-overlay state cannot linger.
            if self._dragging_state != DragState.inactive:
                self._cancel_stale_drag()
            self._titlebar_drag_start = event.position().toPoint()
            self._drag_start_mouse_position = event.position().toPoint()
```

#### Remove the transient filter on every title-bar release

```python
        if etype == QEvent.MouseButtonRelease:
            if state in (DragState.mouse_pressed, DragState.floating_widget):
                was_dragging = state == DragState.floating_widget
                self._set_state(DragState.inactive)
                if self._mouse_event_handler is not None:
                    try:
                        self._mouse_event_handler.releaseMouse()
                    except RuntimeError:
                        pass
                    self._mouse_event_handler = None
                # Always remove the transient app filter here — the drag is
                # over.  If it was a real drag we still finalize below, but the
                # filter must not outlive this interaction.
                self._remove_frameless_drag_filter()
                if was_dragging:
                    QTimer.singleShot(0, self._finalize_drag)
                self._titlebar_drag_start = None
                self._os_move_active = False
                return True
            return False
```

#### Do not manually re-move after the OS move loop

```python
            if state == DragState.floating_widget:
                # If the OS move loop was used, the OS already moved the window.
                # Manually re-positioning here with stale local coordinates would
                # make the float jump to the wrong place.
                if not self._os_move_active:
                    self.move_floating()
                return True
            return False
```

#### Safety nets in `moveEvent()` and `changeEvent()`

```python
    def moveEvent(self, event: QMoveEvent):
        super().moveEvent(event)
        state = getattr(self, '_dragging_state', DragState.inactive)
        # Ultimate stuck-state safety net: a drag with no button held is stale
        # (e.g. the OS move loop swallowed the release).  Cancel it before any
        # further moves cause a phantom jump or drop.
        if state != DragState.inactive and QApplication.mouseButtons() == Qt.NoButton:
            logger.debug('[FDC] moveEvent with no button held — canceling stale drag')
            self._cancel_stale_drag()
            return
        if state == DragState.mouse_pressed:
            self._set_state(DragState.floating_widget)
            self._update_drop_overlays(QCursor.pos())
        elif state == DragState.floating_widget:
            self._update_drop_overlays(QCursor.pos())
```

```python
    def changeEvent(self, event: QEvent):
        super().changeEvent(event)
        if (event.type() == QEvent.ActivationChange) and self.isActiveWindow():
            ...
            # If the OS move loop consumed the release, the float can be left
            # stuck in a drag state.  A focus/activation change with no button
            # held means the user has finished interacting elsewhere; end any
            # stale drag before it can jump on the next move.
            if (self._dragging_state != DragState.inactive
                    and QApplication.mouseButtons() == Qt.NoButton):
                logger.debug('[FDC] ActivationChange with no button held — canceling stale drag')
                self._cancel_stale_drag()
```

#### `event()` no longer starts a drag from resize borders

```python
    def event(self, e: QEvent) -> bool:
        ...
        if etype == QEvent.NonClientAreaMouseButtonPress:
            # Never start a dock drag from a resize border.  If a stale drag is
            # still armed (e.g. the OS move loop consumed its release), cancel
            # it now rather than letting it persist.
            if state != DragState.inactive:
                logger.debug('[FDC] NonClientAreaMouseButtonPress with stale drag state %s — canceling', state)
                self._cancel_stale_drag()
        elif state == DragState.mouse_pressed:
            ...
        elif state == DragState.floating_widget:
            ...
        return super().event(e)
```

### `lace/dock_area_title_bar.py`

```python
                if is_floating_dock_container(floating_window):
                    self._drag_state = DragState.floating_widget
                    self._floating_widget = floating_window

                    # Convert the local press position to the floating window's
                    # coordinate system via the global screen, so dragging a dock
                    # area title bar that has been reparented to another window
                    # still uses the correct cursor offset.
                    mapped_start_pos = floating_window.mapFromGlobal(
                        self.mapToGlobal(self._drag_start_mouse_position))
                    floating_window.start_dragging(mapped_start_pos, floating_window.size(), self)
```

### `lace/dock_widget_tab.py`

```python
                if is_floating_dock_container(floating_window):
                    self._drag_state = DragState.floating_widget
                    self._floating_widget = floating_window

                    # Use global coordinates so the mapped start position is
                    # correct even if this tab widget has been reparented away
                    # from the floating window it belongs to.
                    mapped_start_pos = floating_window.mapFromGlobal(
                        self.mapToGlobal(self._drag_start_mouse_position))
                    floating_window.start_dragging(mapped_start_pos, floating_window.size(), self)
                return
```

## Files changed

- `lace/floating_dock_container_frameless.py`
- `lace/dock_area_title_bar.py`
- `lace/dock_widget_tab.py`
