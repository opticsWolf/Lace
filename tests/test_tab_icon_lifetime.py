# -*- coding: utf-8 -*-
"""A tab icon on a dock that never reached a manager, then the dock deleted
from C++ and collected, must not corrupt the heap.

The tab's icon gap used to be a QSpacerItem made by insertSpacing() with a
Python wrapper held on it; C++ freed the item with the parentless tab and the
collector then touched the stale wrapper (Windows 0xc0000374). The loop runs
in a subprocess so a crash fails this test instead of the whole run.
"""

import os
import subprocess
import sys

SCRIPT = """
import gc, os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import shiboken6
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QLabel
app = QApplication([])
from lace import DockWidget
pixmap = QPixmap(16, 16)
pixmap.fill(Qt.GlobalColor.red)
for i in range(30):
    dock = DockWidget(f"D{i}")           # never added to a DockManager
    dock.set_widget(QLabel("x"))
    dock.set_icon(QIcon(pixmap))
    shiboken6.delete(dock)
    del dock
    gc.collect()
    app.processEvents()
print("survived")
"""


def test_an_unplaced_dock_with_an_icon_is_collected_safely():
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    result = subprocess.run([sys.executable, "-c", SCRIPT], capture_output=True, text=True,
                            env=env, timeout=120)
    assert result.returncode == 0, result.stderr[-2000:]
    assert "survived" in result.stdout
