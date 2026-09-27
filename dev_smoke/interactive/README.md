# Lace Interactive Trace & Verification

This directory contains scripts and checklists for Tier 2 verification of interactive code paths (menus, drag-drop, hover, composition) that cannot be exercised by offscreen automated smoke tests.

## Overview

The golden-master (characterization) approach works by recording deterministic trace logs of decision points during a scripted manual session. By comparing trace logs before and after a refactor phase, we verify that interactive behaviors remain identical.

## Usage

### 1. Recording a Trace
Run the capture script or execute manually with `LACE_TRACE=1`:
```powershell
# Using powershell
$env:LACE_TRACE=1
python -m demos.demo_app > baseline_S1.trace 2>&1
```
or using python:
```powershell
python dev_smoke/interactive/capture.py S1 baseline_S1.trace
```

### 2. Follow the Checklist
Follow the steps outlined in the corresponding checklist:
- `S1_manager_checklist.md` — Phase B (DockManager composition)
- `S2_drop_checklist.md` — Phase C (DropController extraction)
- `S3_menus_checklist.md` — Phase D (Menu decoupling)
- `S4_sidebar_checklist.md` — Phase E (SidebarManager controllers)
- `S5_style_checklist.md` — 0.8 Phase 4 (LaceStyle); no trace log, run
  against `style_showcase.py` and signed off in the checklist itself

### 3. Verify Diff
After applying the refactor phase, re-run the exact same sequence to produce `after_S1.trace`:
```powershell
diff baseline_S1.trace after_S1.trace
```
An empty diff confirms zero behavioral regression!
