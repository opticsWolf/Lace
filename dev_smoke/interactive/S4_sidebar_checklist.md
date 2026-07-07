# Session S4 Checklist — Sidebar Controllers & Transitions

**Goal:** Verify sidebar transitions, hover timers, and overlay behavior (`sidebar.*` trace points).

## Instructions
1. Launch app with `capture.py S4 baseline_S4.trace`.
2. Perform the following sidebar interactions:
   - [ ] **Action 1 (Pin):** Pin a docked widget to a sidebar (e.g., Left or Right sidebar).
   - [ ] **Action 2 (Hover Open):** Hover over the sidebar tab button until the overlay widget opens.
   - [ ] **Action 3 (Hide Timeout):** Move cursor away from the sidebar overlay and let the auto-hide timer expire so overlay closes.
   - [ ] **Action 4 (Switch Buttons):** Pin a second widget to the same sidebar. Hover over the first tab button to open its overlay, then move cursor directly to the second tab button (exercises `_process_pending_switch`).
   - [ ] **Action 5 (Resize Overlay):** Click and drag the resize border of an open sidebar overlay to resize it.
   - [ ] **Action 6 (Drag to Float):** Click and drag a sidebar tab off the sidebar bar into the main workspace to float it.
   - [ ] **Action 7 (Unpin):** Re-pin a widget, then unpin it back to standard docked state.
3. Close the application cleanly.
4. Verify `baseline_S4.trace` contains stable `sidebar.transition`, `sidebar.hover`, `sidebar.timer`, and `sidebar.overlay` lines.
