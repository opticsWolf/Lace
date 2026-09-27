# -*- coding: utf-8 -*-
"""Pick the theme stage (quick / regular / full) from what the branch changed.

    <python> tests/select_theme_set.py [base-ref]   # prints the stage

Rules, from the plan's stage table:
- full:    the style, palette derivation or chrome painting changed.
- regular: any other theme or paint code changed.
- quick:   everything else (docs, tests, layout logic).
"""

import subprocess
import sys
from typing import List

FULL_TRIGGERS = (
    "lace/dock_theme.py",
    "lace/dock_theme_bridge.py",
    "lace/dock_custom_theme.py",
    "lace/dock_paint.py",
    "lace/dock_chrome.py",
    "lace/lace_style",
    "lace/color",
)
REGULAR_TRIGGERS = (
    "lace/theme_",
    "lace/dock_style",
    "lace/dock_widget_tab.py",
    "lace/dock_area_title_bar.py",
    "lace/sidebar",
    "tests/fixtures/themes/",
)


def changed_files(base: str = "main") -> List[str]:
    try:
        out = subprocess.run(["git", "diff", "--name-only", f"{base}...HEAD"],
                             capture_output=True, text=True, check=True).stdout
        out += subprocess.run(["git", "diff", "--name-only", "HEAD"],
                              capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]


def select_stage(base: str = "main") -> str:
    files = changed_files(base)
    if not files:
        return "quick"
    if any(f.startswith(FULL_TRIGGERS) for f in files):
        return "full"
    if any(f.startswith(REGULAR_TRIGGERS) for f in files):
        return "regular"
    return "quick"


if __name__ == "__main__":
    print(select_stage(sys.argv[1] if len(sys.argv) > 1 else "main"))
