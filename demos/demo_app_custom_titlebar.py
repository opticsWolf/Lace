# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.

"""Dock feature & flags testbed in a frameless window with a custom title bar.

The testbed itself lives in demo_common; demo_app runs the same one in a
plain QMainWindow.
"""

import sys
import logging
from pathlib import Path

from PySide6.QtWidgets import QApplication

# demo_common sits next to this file; importable whether the demo runs as
# a script (demos/ on sys.path) or as the demos.<name> module.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from demo_common import DEMOS_DIR, DemoWindowMixin, load_icon  # noqa: E402

from lace import LaceStyle, TitleBarMode
from lace.frameless_window import FramelessLaceMainWindow, LaceStandardTitleBar

logging.basicConfig(level=logging.DEBUG)


class DemoMainWindow(DemoWindowMixin, FramelessLaceMainWindow):
    """Demo main window using a custom title bar from PySideSix-Frameless-Window."""

    # "Unpinnable Data" sits directly to the right of the locked DesignArea,
    # so it is a splitter neighbour of Design Item A/B.
    UNPINNABLE_BESIDE_DESIGN = True

    def __init__(self):
        super().__init__()

        # Use StandardTitleBar which shows window icon + title label;
        # LaceStandardTitleBar toggles maximize synchronously so the
        # double-click works even while the mouse button is still held.
        self.setTitleBar(LaceStandardTitleBar(self))

        self._build_demo("Dock Feature & Flags Testbed (Custom TitleBar)")

    def _configure_dock_manager(self):
        self.dock_manager.title_bar_mode = TitleBarMode.custom

        # Dedicated icon for the frameless floating dock windows.
        floating_icon = load_icon(DEMOS_DIR / "icon2.ico")
        if floating_icon is not None:
            self.dock_manager.set_floating_window_icon(floating_icon)


if __name__ == '__main__':
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle(LaceStyle())
    window = DemoMainWindow()
    window.show()
    sys.exit(app.exec())
