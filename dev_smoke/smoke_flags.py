"""Smoke test for DockFlags configuration behavior.

Verifies:
1. always_show_tabs
2. show_tab_close_button
3. active_tab_has_close_button
4. middle_mouse_button_closes_tab
5. floatable_tabs
6. pinnable_tabs
"""
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt, QPoint, QEvent
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget

from lace.dock_manager import DockManager
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea, DockFlags, DockWidgetFeature
from lace.dock_menu import menu_default_pin
from lace.dock_icon_provider import get_icon_provider


def run_test():
    app = QApplication.instance() or QApplication(sys.argv)
    icons_dir = os.path.join(ROOT, "lace", "resources", "lace_icons")
    try:
        get_icon_provider(icons_dir)
    except Exception:
        pass
    window = QMainWindow()
    mgr = DockManager(window)

    # 1. Test always_show_tabs
    dw1 = DockWidget("Tab 1")
    dw1.set_features(DockWidgetFeature.closable | DockWidgetFeature.floatable | DockWidgetFeature.pinnable)
    area = mgr.add_dock_widget(DockWidgetArea.left, dw1)
    tab_bar = area._tab_bar()

    # By default, always_show_tabs is in default_config
    assert DockFlags.always_show_tabs in mgr.config_flags
    assert tab_bar.isVisibleTo(area) or not tab_bar.isHidden(), "Tab bar should be visible with always_show_tabs even with 1 tab"

    # Turn off always_show_tabs
    mgr.set_config_flags(mgr.config_flags & ~DockFlags.always_show_tabs)
    assert not tab_bar.isVisibleTo(area) or tab_bar.isHidden(), "Tab bar should be hidden with 1 tab when always_show_tabs is disabled"

    # Turn it back on
    mgr.set_config_flags(mgr.config_flags | DockFlags.always_show_tabs)
    assert tab_bar.isVisibleTo(area) or not tab_bar.isHidden(), "Tab bar should show when always_show_tabs is re-enabled"

    # 2. Test show_tab_close_button and active_tab_has_close_button
    dw2 = DockWidget("Tab 2")
    dw2.set_features(DockWidgetFeature.closable | DockWidgetFeature.floatable | DockWidgetFeature.pinnable)
    mgr.add_dock_widget(DockWidgetArea.center, dw2, area)

    window.show()
    app.processEvents()

    tab1 = dw1.tab_widget()
    tab2 = dw2.tab_widget()

    tab_bar.set_current_index(1)  # Tab 2 active
    app.processEvents()
    assert not tab1.is_active_tab()
    assert tab2.is_active_tab()

    # With active_tab_has_close_button active (and show_tab_close_button active)
    assert DockFlags.show_tab_close_button in mgr.config_flags
    assert DockFlags.active_tab_has_close_button in mgr.config_flags
    assert not tab1._close_button.isVisible(), "Inactive tab should hide close button when active_tab_has_close_button is enabled"
    assert tab2._close_button.isVisible(), "Active tab should show close button"

    # Turn off active_tab_has_close_button -> both tabs should show close buttons
    mgr.set_config_flags(mgr.config_flags & ~DockFlags.active_tab_has_close_button)
    assert tab1._close_button.isVisible(), "All closable tabs should show close buttons when active_tab_has_close_button is false"
    assert tab2._close_button.isVisible()

    # Turn off show_tab_close_button entirely -> no tab should show close button
    mgr.set_config_flags(mgr.config_flags & ~DockFlags.show_tab_close_button)
    assert not tab1._close_button.isVisible()
    assert not tab2._close_button.isVisible()

    # Restore default close button flags
    mgr.set_config_flags(mgr.config_flags | DockFlags.show_tab_close_button | DockFlags.active_tab_has_close_button)

    # 3. Test middle_mouse_button_closes_tab
    close_emitted = []
    tab2.close_requested.connect(lambda: close_emitted.append(True))

    ev_middle = QMouseEvent(QEvent.Type.MouseButtonPress, QPoint(5, 5), QPoint(5, 5), Qt.MiddleButton, Qt.MiddleButton, Qt.NoModifier)
    tab2.mousePressEvent(ev_middle)
    assert len(close_emitted) == 1, "Middle click should emit close_requested when middle_mouse_button_closes_tab is enabled"

    # Turn off middle_mouse_button_closes_tab
    mgr.set_config_flags(mgr.config_flags & ~DockFlags.middle_mouse_button_closes_tab)
    tab2.mousePressEvent(ev_middle)
    assert len(close_emitted) == 1, "Middle click should NOT emit close_requested when middle_mouse_button_closes_tab is disabled"

    # 4. Test floatable_tabs
    assert DockFlags.floatable_tabs in mgr.config_flags
    assert tab1._floatable
    assert area._title_bar._undock_button.isEnabled()

    mgr.set_config_flags(mgr.config_flags & ~DockFlags.floatable_tabs)
    assert not tab1._floatable, "Tab _floatable property should be false when floatable_tabs config flag is disabled"
    assert not area._title_bar._undock_button.isEnabled(), "Titlebar float/undock button should be disabled when floatable_tabs is disabled"
    assert not tab1._start_floating(), "_start_floating on tab should return False when floatable_tabs is disabled"

    # 5. Test pinnable_tabs
    mgr.set_config_flags(mgr.config_flags | DockFlags.pinnable_tabs)
    assert tab1._pinnable
    mgr.set_config_flags(mgr.config_flags & ~DockFlags.pinnable_tabs)
    assert not tab1._pinnable, "Tab _pinnable property should be false when pinnable_tabs config flag is disabled"
    assert not area._title_bar._pin_button.isEnabled()

    # Test menu_default_pin early return when pinnable_tabs is false
    pinned_count_before = len(mgr.sidebar_manager._sidebars) if hasattr(mgr, 'sidebar_manager') else 0
    menu_default_pin(dw1, area)
    pinned_count_after = len(mgr.sidebar_manager._sidebars) if hasattr(mgr, 'sidebar_manager') else 0
    # 6. Test opaque_undocking
    from lace.floating_dock_container import FloatingDockContainer
    from lace.enums import DragState
    fw = FloatingDockContainer(dock_widget=dw1)
    mgr.set_config_flags(mgr.config_flags | DockFlags.opaque_undocking)
    fw._set_state(DragState.floating_widget)
    assert fw.windowOpacity() == 1.0, f"Expected opacity 1.0 with opaque_undocking enabled, got {fw.windowOpacity()}"

    mgr.set_config_flags(mgr.config_flags & ~DockFlags.opaque_undocking)
    fw._set_state(DragState.floating_widget)
    assert abs(fw.windowOpacity() - 0.6) < 0.01, f"Expected opacity 0.6 with opaque_undocking disabled, got {fw.windowOpacity()}"
    fw._set_state(DragState.inactive)
    assert fw.windowOpacity() == 1.0, f"Expected opacity 1.0 after inactive state, got {fw.windowOpacity()}"

    # 7. Test chromeless_float
    mgr.set_config_flags(mgr.config_flags | DockFlags.chromeless_float)
    assert bool(fw.windowFlags() & Qt.FramelessWindowHint), "Expected Qt.FramelessWindowHint when chromeless_float is enabled"

    mgr.set_config_flags(mgr.config_flags & ~DockFlags.chromeless_float)
    assert not bool(fw.windowFlags() & Qt.FramelessWindowHint), "Expected no Qt.FramelessWindowHint when chromeless_float is disabled"

    fw.deleteLater()

    # 8. Test sidebar_area_has_maximize_button
    assert DockFlags.sidebar_area_has_maximize_button in mgr.config_flags
    sm = mgr.sidebar_manager
    sm.pin_widget(dw2, area=DockWidgetArea.right)
    app.processEvents()
    sm.show_widget(dw2)
    app.processEvents()
    
    sidebar_title_bar = sm._overlay._title_bar
    max_btn = sidebar_title_bar._maximize_btn
    assert max_btn.isVisible(), "Sidebar maximize button should be visible with flag enabled"
    
    # Disable flag
    mgr.set_config_flags(mgr.config_flags & ~DockFlags.sidebar_area_has_maximize_button)
    app.processEvents()
    assert not max_btn.isVisible(), "Sidebar maximize button should be hidden when flag is disabled"
    
    # Re-enable flag
    mgr.set_config_flags(mgr.config_flags | DockFlags.sidebar_area_has_maximize_button)
    app.processEvents()
    assert max_btn.isVisible(), "Sidebar maximize button should be visible when flag is re-enabled"
    
    # Clean up
    sm.unpin_widget(dw2)

    print("SMOKE FLAGS OK")


if __name__ == "__main__":
    run_test()
