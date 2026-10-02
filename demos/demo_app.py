# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.

"""Dock feature & flags testbed in a plain QMainWindow.

The testbed itself lives in demo_common; demo_app_custom_titlebar runs the
same one in a frameless window.
"""

import sys
import logging
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMainWindow

# demo_common sits next to this file; importable whether the demo runs as
# a script (demos/ on sys.path) or as the demos.<name> module.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from demo_common import DemoWindowMixin  # noqa: E402

from lace import LaceStyle, DockMenuBarStyler

logging.basicConfig(level=logging.DEBUG)


class DemoMainWindow(DemoWindowMixin, QMainWindow):
    def __init__(self):
        super().__init__()
        self._build_demo("Dock Feature & Flags Testbed")

    def _style_menu_bar(self):
        # Remove Fusion's 1px bottom border from the menu bar and pin its
        # background to the sidebar colour; re-applied on every theme
        # switch by DockMenuBarStyler.
        self._menu_bar_styler = DockMenuBarStyler(self.menuBar(), parent=self)


if __name__ == '__main__':
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle(LaceStyle())
    window = DemoMainWindow()
    window.show()
    sys.exit(app.exec())
