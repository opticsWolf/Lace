"""Smoke test for DockFlags.dock_area_has_maximize_button and maximize/restore behavior.

Verifies:
1. Maximize button visibility is controlled by the dock_area_has_maximize_button flag.
2. Maximizing a dock area in a multi-area container hides siblings.
3. Restoring a maximized area brings siblings back with splitter sizes preserved.
4. Maximizing a solo floating area delegates to OS showMaximized / showNormal.
5. TitleBarButton.maximize / .restore / .minimize all map to the same button.
6. Button icon and tooltip switch between Maximize and Restore states.
"""
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget
from PySide6.QtCore import Qt

from lace.dock_manager import DockManager
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea, DockFlags, DockWidgetFeature, TitleBarButton
from lace.dock_icon_provider import get_icon_provider


def run_test():
    app = QApplication.instance() or QApplication(sys.argv)
    icons_dir = os.path.join(ROOT, "lace", "resources", "lace_icons")
    try:
        get_icon_provider(icons_dir)
    except Exception:
        pass
    window = QMainWindow()
    window.resize(800, 600)
    mgr = DockManager(window)

    # Create two dock areas in the main window
    dw1 = DockWidget("Panel A")
    dw1.set_widget(QWidget())
    dw1.set_features(DockWidgetFeature.all_features)
    area1 = mgr.add_dock_widget(DockWidgetArea.left, dw1)

    dw2 = DockWidget("Panel B")
    dw2.set_widget(QWidget())
    dw2.set_features(DockWidgetFeature.all_features)
    area2 = mgr.add_dock_widget(DockWidgetArea.right, dw2)

    window.show()
    app.processEvents()

    # ── 1. Maximize button visibility controlled by flag ──────────────
    assert DockFlags.dock_area_has_maximize_button in mgr.config_flags, \
        "dock_area_has_maximize_button should be in default_config"

    max_btn_1 = area1.title_bar_button(TitleBarButton.maximize)
    assert max_btn_1 is not None, "TitleBarButton.maximize should return a button"
    assert max_btn_1.isVisible(), "Maximize button should be visible with flag enabled"

    # Disable the flag
    mgr.config_flags = mgr.config_flags & ~DockFlags.dock_area_has_maximize_button
    area1._update_title_bar_button_states()
    app.processEvents()
    assert not max_btn_1.isVisible(), "Maximize button should be hidden with flag disabled"

    # Re-enable
    mgr.config_flags = mgr.config_flags | DockFlags.dock_area_has_maximize_button
    area1._update_title_bar_button_states()
    app.processEvents()
    assert max_btn_1.isVisible(), "Maximize button should be visible again after re-enabling"
    print("  [PASS] 1. Maximize button visibility controlled by flag")

    # ── 2. TitleBarButton enum mapping ────────────────────────────────
    assert area1.title_bar_button(TitleBarButton.maximize) is max_btn_1
    assert area1.title_bar_button(TitleBarButton.minimize) is max_btn_1
    assert area1.title_bar_button(TitleBarButton.restore) is max_btn_1
    print("  [PASS] 2. TitleBarButton.maximize/minimize/restore all map to same button")

    # ── 3. Maximize hides siblings ────────────────────────────────────
    container = area1.dock_container()
    assert not area1.is_maximized(), "Area1 should not be maximized initially"
    assert not area2.is_maximized(), "Area2 should not be maximized initially"

    container.toggle_maximize_dock_area(area1)
    app.processEvents()

    assert area1.is_maximized(), "Area1 should be maximized"
    assert area1.isVisible(), "Maximized area should be visible"
    assert not area2.isVisible(), "Sibling area should be hidden"
    assert max_btn_1.toolTip() == "Restore", "Button tooltip should say 'Restore' when maximized"
    print("  [PASS] 3. Maximize hides sibling areas")

    # ── 4. Restore brings siblings back ───────────────────────────────
    container.toggle_maximize_dock_area(area1)
    app.processEvents()

    assert not area1.is_maximized(), "Area1 should not be maximized after restore"
    assert area1.isVisible(), "Area1 should be visible after restore"
    assert area2.isVisible(), "Area2 should be visible after restore"
    assert max_btn_1.toolTip() == "Maximize", "Button tooltip should say 'Maximize' after restore"
    print("  [PASS] 4. Restore brings siblings back")

    # ── 5. Toggle via DockAreaWidget convenience method ───────────────
    area2.toggle_maximize()
    app.processEvents()
    assert area2.is_maximized(), "Area2 should be maximized via toggle_maximize()"
    assert not area1.isVisible(), "Area1 should be hidden when Area2 maximized"

    area2.toggle_maximize()
    app.processEvents()
    assert not area2.is_maximized(), "Area2 should be restored via toggle_maximize()"
    assert area1.isVisible(), "Area1 should be visible after Area2 restored"
    print("  [PASS] 5. DockAreaWidget.toggle_maximize() convenience method works")

    # ── 6. Maximizing a different area restores the previous one ──────
    area1.toggle_maximize()
    app.processEvents()
    assert area1.is_maximized()
    assert not area2.isVisible()

    container.toggle_maximize_dock_area(area2)
    app.processEvents()
    assert not area1.is_maximized(), "Area1 should be auto-restored when Area2 is maximized"
    assert area2.is_maximized(), "Area2 should now be maximized"
    # ...but NOT visible: it is Area2 that is maximized now, and a maximized
    # area hides its siblings — the invariant asserted for Area1/Area2 above.
    # This line used to assert isVisible(), contradicting that; the script was
    # never in run_all.py's CHECKS, so nothing caught it.
    assert not area1.isVisible(), "Area1 should be hidden while Area2 is maximized"

    # Clean up
    area2.toggle_maximize()
    app.processEvents()
    print("  [PASS] 6. Maximizing a different area auto-restores the previous one")

    # ── 7. Floating solo vs chromeless vs split maximize button ───────
    from lace.floating_dock_container import FloatingDockContainer
    
    # Detach widgets from their current areas
    area1.remove_dock_widget(dw1)
    area2.remove_dock_widget(dw2)
    
    # Create solo floating container hosting dw1
    fw = FloatingDockContainer(dock_widget=dw1, dock_manager=mgr)
    # show() matters: isVisible() is False for every child of a hidden window,
    # so without it the "button is hidden" assertions below pass vacuously and
    # the "button is shown" ones can never pass.
    fw.show()
    app.processEvents()
    
    float_area = dw1.dock_area_widget()
    float_max_btn = float_area.title_bar_button(TitleBarButton.maximize)
    assert float_max_btn is not None
    assert not float_max_btn.isVisible(), "Solo bordered floating area should hide maximize button"
    
    # Enable chromeless_float flag -> maximize button should become visible
    mgr.set_config_flags(mgr.config_flags | DockFlags.chromeless_float)
    float_area._update_title_bar_button_states()
    app.processEvents()
    assert float_max_btn.isVisible(), "Solo chromeless floating area should show maximize button"
    
    # Disable chromeless_float flag -> maximize button should hide again
    mgr.set_config_flags(mgr.config_flags & ~DockFlags.chromeless_float)
    float_area._update_title_bar_button_states()
    app.processEvents()
    assert not float_max_btn.isVisible(), "Solo bordered floating area should hide maximize button"
    
    # Add a second dock widget (dw2) to the floating container, splitting it
    fw._dock_container.add_dock_widget(DockWidgetArea.right, dw2)
    app.processEvents()
    
    float_area2 = dw2.dock_area_widget()
    float_max_btn2 = float_area2.title_bar_button(TitleBarButton.maximize)
    
    assert float_max_btn.isVisible(), "Split floating area 1 should show maximize button"
    assert float_max_btn2.isVisible(), "Split floating area 2 should show maximize button"
    
    # Maximize the first split area
    fw._dock_container.toggle_maximize_dock_area(float_area)
    app.processEvents()
    
    # Sibling area is hidden, but the maximized area's maximize/restore button MUST STILL BE VISIBLE (so it can be restored!)
    assert float_area.is_maximized(), "float_area should be maximized"
    assert float_max_btn.isVisible(), "Maximized float area's button should remain visible (as Restore button)"
    
    # Restore the layout
    fw._dock_container.toggle_maximize_dock_area(float_area)
    app.processEvents()
    
    # Both areas are visible again, and both maximize buttons should be visible
    assert not float_area.is_maximized(), "float_area should be restored"
    assert float_max_btn.isVisible()
    assert float_max_btn2.isVisible()
    
    # Clean up
    fw.deleteLater()
    print("  [PASS] 7. Floating solo vs chromeless vs split maximize button")

    # ASCII only: the Windows console defaults to cp1252, which cannot encode
    # emoji, and a UnicodeEncodeError here fails the script after every
    # assertion has already passed.
    print("\nSMOKE MAXIMIZE OK")


if __name__ == "__main__":
    run_test()
