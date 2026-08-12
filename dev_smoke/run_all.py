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
    "smoke_themeswitch.py", # apply all 13 themes on a populated window
    "smoke_theme_palette.py", # verify 5-color ThemeSpec, status tokens, WCAG contrast, and bridge refresh
    "smoke_autotheme.py",   # OS-Aware Auto Theme Switcher (registry, QEvent.PaletteChange, QSS/dock overrides)
    "smoke_theme_json.py", # pydantic JSON theme loading + applying themes from JSON
    "smoke_flags.py",       # global DockFlags configuration checks
    "smoke_movable.py",     # DockWidgetFeature.movable property and drag blocking checks
    "smoke_pin_button.py",  # TitleBarButton.pin visibility, enablement, and pin/unpin toggling checks
    "smoke_lock.py",        # locked_to_area / locked_name strip pinnable + floatable
    "smoke_maximize.py",    # maximize/restore: siblings, splitter sizes, floating delegation
    "smoke_tab_icons.py",   # DockFlags.custom_tab_icons resolution through the provider
    "smoke_insertion_order.py",  # InsertionOrder placement of newly added widgets
]

# Checks that cannot run headless, with the reason. Everything else in this
# directory must appear in CHECKS above — see the guard below.
NEEDS_DISPLAY = {
    # Drives real WM_LBUTTONDOWN messages through PostMessage, which needs a
    # genuine window handle; offscreen Qt has none.
    "smoke_dblclick.py": "posts native window messages",
}


def _unlisted():
    """Smoke scripts present on disk but in neither list.

    smoke_lock.py and smoke_maximize.py sat unlisted long enough to rot against
    renamed APIs (setWidget, DockManager()) and to accumulate assertions that
    contradicted the behaviour asserted elsewhere in the same file. A check the
    runner does not run is a check that is not maintained.
    """
    on_disk = {f for f in os.listdir(HERE)
               if f.startswith("smoke_") and f.endswith(".py")}
    return sorted(on_disk - set(CHECKS) - set(NEEDS_DISPLAY))

unlisted = _unlisted()
if unlisted:
    print("ERROR: smoke checks exist but are not listed in run_all.py:")
    for name in unlisted:
        print(f"  {name}")
    print("Add them to CHECKS, or to NEEDS_DISPLAY with a reason.")
    sys.exit(1)

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
