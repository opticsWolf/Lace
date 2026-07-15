# -*- coding: utf-8 -*-
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from lace.dock_manager import DockManager
from lace.dock_widget import DockWidget
from lace.dock_area_widget import DockAreaWidget
from lace.enums import DockWidgetFeature, DragState

def run_test():
    app = QApplication.instance() or QApplication(sys.argv)
    
    mgr = DockManager()
    
    # Create locked widgets
    dw = DockWidget("Design Item A")
    mgr.add_dock_widget(0, dw)  # Add to central area
    
    area = dw.dock_area_widget()
    assert area is not None, "DockAreaWidget should be initialized"
    
    # 1. Assert normal default features
    assert DockWidgetFeature.pinnable in dw.features(), "Should initially be pinnable"
    assert DockWidgetFeature.floatable in dw.features(), "Should initially be floatable"
    
    # 2. Apply locks
    area.locked_name = "DesignArea"
    dw.locked_to_area = "DesignArea"
    
    # 3. Assert stripped features in features()
    features_after = dw.features()
    assert DockWidgetFeature.pinnable not in features_after, "Pinnable feature should be stripped when locked"
    assert DockWidgetFeature.floatable not in features_after, "Floatable feature should be stripped when locked"
    
    # 4. Assert tab properties
    tab = dw.tab_widget()
    assert tab is not None, "TabWidget should exist"
    
    # Gather menu context and assert floatable/pinnable are False
    menu_context = tab._gather_menu_context()
    assert not menu_context.is_floatable, "tab floatable context should be False when locked"
    assert not menu_context.is_pinnable, "tab pinnable context should be False when locked"
    assert DockWidgetFeature.floatable in area.features(), "DockAreaWidget itself should remain floatable when locked"
    assert DockWidgetFeature.pinnable not in area.features(), "DockAreaWidget itself should not be pinnable when locked"
    
    # 5. Verify float prevention
    assert not tab._start_floating(), "_start_floating should return False for a locked widget"
    
    # 6. Verify lock release behaves normally
    dw.locked_to_area = None
    features_unlocked = dw.features()
    assert DockWidgetFeature.pinnable in features_unlocked, "Pinnable feature should restore when unlocked"
    assert DockWidgetFeature.floatable in features_unlocked, "Floatable feature should restore when unlocked"
    
    print("ALL LOCK SMOKE TESTS PASSED!")

if __name__ == "__main__":
    run_test()
