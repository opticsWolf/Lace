# Session S1 Checklist — Manager & Composition

**Goal:** Verify `DockManager` and container composition behavior (`manager.*` trace points).

## Instructions
1. Launch app with `capture.py S1 baseline_S1.trace`.
2. In the running demo app, perform the following actions in exact order:
   - [ ] **Action 1:** Notice the initial docked layout (Standard Editor, Unclosable Logger, etc.).
   - [ ] **Action 2:** Click/drag "Unfloatable Tool" tab (or another floatable tab like "Standard Editor") out to float as an independent window.
   - [ ] **Action 3:** Dock the floating window back into the main dock container.
   - [ ] **Action 4:** In the demo app menu/toolbar, click **Save State** (or trigger layout save).
   - [ ] **Action 5:** In the demo app menu/toolbar, click **Restore State** (or trigger layout restore).
   - [ ] **Action 6:** Switch theme using the theme selector (e.g., switch to 'light' or 'monokai').
3. Close the application cleanly.
4. Verify `baseline_S1.trace` was generated and contains `manager.*` trace events.
