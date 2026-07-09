"""Run every dev smoke check, each in its own process. Exit non-zero on any failure.

Usage (from the repo root):
    <python> dev_smoke/run_all.py

Each check is a standalone script that builds its own QApplication, so they must
run in separate processes (QApplication is a singleton). This runner sets
QT_QPA_PLATFORM=offscreen and PYTHONPATH for each child.

These are lightweight, no-display regression checks — NOT a real test suite.
They exercise the paths that offscreen Qt can drive: color core, the
DockStyled debounce/registration, save/restore round-trips (docked + floating),
sidebar pin/unpin, the schema button block, DragDetector, and an 8-theme switch.
Drag-DROP and tear-off are NOT covered (need a real cursor); verify those by
running the app.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

env = os.environ.copy()
env["QT_QPA_PLATFORM"] = "offscreen"
env["PYTHONPATH"] = ROOT

CHECKS = [
    "smoke_m1.py",          # color core: QColor-native storage, generation cache
    "smoke_m2.py",          # DockStyled mixin: debounce + multi-category registration
    "smoke_schema.py",      # _ActionButtonFields dedup keeps flat fields/defaults
    "smoke_m4.py",          # DragDetector threshold behavior
    "smoke_sidebar.py",     # pin / unpin-to-dock / unpin-to-float
    "smoke_sidebar_paint.py", # sidebar chrome painted (overlay + title + strip) vs tokens
    "smoke_tab_paint.py",   # dock tab label palette + ChromeToolButton painted hover
    "smoke_nudge.py",       # theme recolour works without the stylesheet nudge
    "smoke_roundtrip.py",   # main container save/restore + corrupt payload
    "smoke_float.py",       # floating container save/restore branch
    "smoke_themeswitch.py", # apply all 8 themes on a populated window
    "smoke_autotheme.py",   # OS-Aware Auto Theme Switcher (registry, QEvent.PaletteChange, QSS/dock overrides)
    "smoke_flags.py",       # global DockFlags configuration checks
]

failed = []
for name in CHECKS:
    print(f"\n=== {name} ===", flush=True)
    result = subprocess.run([sys.executable, os.path.join(HERE, name)],
                            env=env, cwd=ROOT)
    if result.returncode != 0:
        failed.append(name)

if failed:
    print(f"\nFAILED: {', '.join(failed)}")
    sys.exit(1)
print("\nALL DEV SMOKE CHECKS PASSED")
