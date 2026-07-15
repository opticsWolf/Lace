# Session S3 Checklist — Menu Decoupling & Actions

**Goal:** Verify context menu construction and action dispatch (`menu.build` and `menu.action` trace points).

## Instructions
1. Launch app with `capture.py S3 baseline_S3.trace`.
2. For each of the 4 widget types (Dock-area title bar, Dock tab, Sidebar overlay title bar, Sidebar tab) across 3 states (Docked, Floating, Pinned):
   - [ ] **Docked Area Title Bar:** Right-click title bar of a docked widget -> trigger an available action (e.g., Float or Close).
   - [ ] **Docked Tab:** Right-click tab of a docked widget -> trigger an available action.
   - [ ] **Floating Widget:** Right-click title bar and tab of a floating widget -> trigger Dock or Close.
   - [ ] **Pinned Sidebar Tab:** Right-click a pinned sidebar tab -> trigger Unpin or Float.
   - [ ] **Sidebar Overlay Title Bar:** Hover to open overlay, right-click overlay title bar -> trigger Unpin or Close.
3. Switch theme and verify menu content remains identical.
4. Close the application cleanly.
5. Verify `baseline_S3.trace` contains stable `menu.build` section-lists and `menu.action` dispatches.
