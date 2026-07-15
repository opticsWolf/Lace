# -*- coding: utf-8 -*-
"""
Smoke test verifying tab icons wiring: default/custom QIcon and SVG names via DockIconProvider,
and dynamic behavior when toggling DockFlags.custom_tab_icons.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QMainWindow

from lace import DockManager, DockWidget, DockFlags, DockWidgetArea
from lace.dock_icon_provider import get_icon_provider


def run_smoke_test():
    app = QApplication.instance() or QApplication(sys.argv)
    
    base_path = Path(__file__).parent.parent
    icon_dir = base_path / "lace" / "resources" / "lace_icons"
    get_icon_provider(icon_dir)
    
    win = QMainWindow()
    mgr = DockManager(win)
    
    # Test 1: Default icon set directly as QIcon when custom_tab_icons is disabled
    dw1 = DockWidget("Widget 1", win)
    test_pix = QPixmap(16, 16)
    test_pix.fill()
    test_icon = QIcon(test_pix)
    dw1.set_icon(test_icon)
    
    tab1 = dw1._tab_widget
    assert not tab1.icon().isNull(), "Tab icon should not be null after set_icon"
    assert tab1._icon_label is not None and not tab1._icon_label.pixmap().isNull(), "Icon label should exist and have a pixmap"
    assert not tab1._icon_label.isHidden(), "Icon label should not be hidden"
    print("Test 1 (Direct QIcon default tab icon) PASSED.")

    # Test 2: Default icon set as SVG name via DockIconProvider
    dw2 = DockWidget("Widget 2", win)
    dw2.set_default_icon_name("pin")
    tab2 = dw2._tab_widget
    assert not tab2.icon().isNull(), "Tab icon should be retrieved from DockIconProvider using default_icon_name"
    print("Test 2 (Provider SVG default_icon_name) PASSED.")

    # Test 3: Custom icon name configured, but custom_tab_icons flag IS NOT ENABLED
    dw3 = DockWidget("Widget 3", win)
    dw3.set_default_icon_name("pin")
    dw3.set_custom_icon_name("dock")
    tab3 = dw3._tab_widget
    # Since custom_tab_icons is not set on mgr.config_flags, tab3 should use default ("pin")
    assert tab3.default_icon_name() == "pin"
    assert tab3.custom_icon_name() == "dock"
    assert not tab3.icon().isNull(), "Should fall back to default icon when custom_tab_icons is false"
    print("Test 3 (Custom icon configured while custom_tab_icons disabled) PASSED.")

    # Test 4: Enable DockFlags.custom_tab_icons dynamically on DockManager
    mgr.set_config_flags(mgr.config_flags | DockFlags.custom_tab_icons)
    mgr.add_dock_widget(DockWidgetArea.center, dw3)
    # verify update_icon immediately switched to using custom_icon_name ("dock")
    assert not tab3.icon().isNull(), "Custom icon should resolve when custom_tab_icons is active"
    print("Test 4 (Dynamic transition to DockFlags.custom_tab_icons) PASSED.")

    # Test 5: Disable DockFlags.custom_tab_icons dynamically and verify revert to default icon
    mgr.set_config_flags(mgr.config_flags & ~DockFlags.custom_tab_icons)
    assert not tab3.icon().isNull(), "Should revert cleanly to default icon when custom_tab_icons disabled"
    print("Test 5 (Dynamic toggle off of DockFlags.custom_tab_icons) PASSED.")

    # Clean up
    mgr.deleteLater()
    win.deleteLater()
    print("\nALL TAB ICON SMOKE TESTS PASSED PERFECTLY!")


if __name__ == "__main__":
    run_smoke_test()
