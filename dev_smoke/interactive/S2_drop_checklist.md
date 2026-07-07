# Session S2 Checklist — Drag & Drop Resolution

**Goal:** Verify drop resolution and splitter insertion behavior (`drop.resolve` and `drop.insert` trace points).

## Instructions
1. Launch app with `capture.py S2 baseline_S2.trace`.
2. Tear a tab out to a floating window (e.g., "Standard Editor").
3. Perform the following 10 drop operations by dragging the floating window over target areas/containers:
   - [ ] **Drop 1 (Center):** Drop onto the center overlay of an existing dock area.
   - [ ] **Drop 2 (Area Top):** Drop onto the top edge overlay of an existing dock area.
   - [ ] **Drop 3 (Area Bottom):** Drop onto the bottom edge overlay of an existing dock area.
   - [ ] **Drop 4 (Area Left):** Drop onto the left edge overlay of an existing dock area.
   - [ ] **Drop 5 (Area Right):** Drop onto the right edge overlay of an existing dock area.
   - [ ] **Drop 6 (Container Top):** Drop onto the outer top edge of the main dock container.
   - [ ] **Drop 7 (Container Bottom):** Drop onto the outer bottom edge of the main dock container.
   - [ ] **Drop 8 (Container Left):** Drop onto the outer left edge of the main dock container.
   - [ ] **Drop 9 (Container Right):** Drop onto the outer right edge of the main dock container.
   - [ ] **Drop 10 (Tab Merge):** Drop directly onto the tab bar of an existing area to merge as a tab.
4. Close the application cleanly.
5. Verify `baseline_S2.trace` contains identical `drop.*` lines across runs.
