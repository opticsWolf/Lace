import sys
import os
import logging
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

logging.disable(logging.CRITICAL)
from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtGui import QAction

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from demo_app import DemoMainWindow
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea, InsertionOrder


def run_smoke_test():
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    win = DemoMainWindow()
    win.show()
    app.processEvents()

    mgr = win.dock_manager

    # Clear any existing actions from view_menu for our test assertions
    mgr.view_menu.clear()

    # 1. Default should be InsertionOrder.by_spelling
    assert mgr.menu_insertion_order == InsertionOrder.by_spelling, f"Expected by_spelling, got {mgr.menu_insertion_order}"

    # Create dock widgets with titles out of alphabetical order
    w_zebra = DockWidget("Zebra Widget", win)
    w_zebra.set_widget(QLabel("Zebra"))
    
    w_apple = DockWidget("Apple Widget", win)
    w_apple.set_widget(QLabel("Apple"))
    
    w_monkey = DockWidget("Monkey Widget", win)
    w_monkey.set_widget(QLabel("Monkey"))

    # Add them: Zebra first, then Apple, then Monkey
    mgr.add_dock_widget(DockWidgetArea.left, w_zebra)
    mgr.add_dock_widget(DockWidgetArea.left, w_apple)
    mgr.add_dock_widget(DockWidgetArea.left, w_monkey)

    # Since by_spelling is active, view_menu actions should be sorted alphabetically:
    # Apple Widget, Monkey Widget, Zebra Widget
    actions = [a.text() for a in mgr.view_menu.actions() if not a.isSeparator() and not a.menu()]
    assert actions == ["Apple Widget", "Monkey Widget", "Zebra Widget"], f"Expected sorted actions, got {actions}"

    # 2. Now switch dynamically to InsertionOrder.by_insertion
    mgr.menu_insertion_order = InsertionOrder.by_insertion
    assert mgr.menu_insertion_order == InsertionOrder.by_insertion

    # Re-check actions: they should now be in exact registration order (including any from DemoMainWindow if in map, plus Zebra, Apple, Monkey)
    # Let's verify that Zebra comes before Apple, and Apple comes before Monkey
    actions_chronological = [a.text() for a in mgr.view_menu.actions() if not a.isSeparator() and not a.menu()]
    idx_zebra = actions_chronological.index("Zebra Widget")
    idx_apple = actions_chronological.index("Apple Widget")
    idx_monkey = actions_chronological.index("Monkey Widget")
    assert idx_zebra < idx_apple < idx_monkey, f"Expected chronological ordering, got {actions_chronological}"

    # 3. Add a sidebar widget ("Banana Widget") while by_insertion is active
    w_banana = DockWidget("Banana Widget", win)
    w_banana.set_widget(QLabel("Banana"))
    mgr.add_sidebar_widget(DockWidgetArea.right, w_banana)

    actions_with_banana = [a.text() for a in mgr.view_menu.actions() if not a.isSeparator() and not a.menu()]
    assert actions_with_banana[-1] == "Banana Widget", f"Got {actions_with_banana}"

    # 4. Switch back to InsertionOrder.by_spelling
    mgr.menu_insertion_order = InsertionOrder.by_spelling
    actions_spelling_all = [a.text() for a in mgr.view_menu.actions() if not a.isSeparator() and not a.menu()]
    assert actions_spelling_all == sorted(actions_spelling_all, key=lambda s: s.lower()), f"Got {actions_spelling_all}"

    # 5. Remove a widget and check menu update
    mgr.remove_dock_widget(w_apple)
    actions_after_remove = [a.text() for a in mgr.view_menu.actions() if not a.isSeparator() and not a.menu()]
    assert "Apple Widget" not in actions_after_remove, f"Got {actions_after_remove}"

    print("SMOKE INSERTION ORDER OK")


if __name__ == "__main__":
    run_smoke_test()
