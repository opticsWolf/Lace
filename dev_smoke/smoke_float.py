import sys, logging
import os
# Run directly (python dev_smoke/<name>.py) and sys.path[0] is dev_smoke/,
# so the demos package below would not resolve. run_all.py sets PYTHONPATH
# instead, which is why this only ever broke on direct invocation.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.disable(logging.CRITICAL)
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
from demos.demo_app import DemoMainWindow
from lace.floating_dock_container import FloatingDockContainer

win = DemoMainWindow()
win.show()
app.processEvents()

dm = win.dock_manager
dw = list(dm.dock_widgets_map().values())[0]

# Float a dock widget, then save/restore -- exercises the is_floating branch
# of the moved save_container_state / restore_container_state.
fw = FloatingDockContainer(dock_widget=dw)
fw.show()
app.processEvents()

n_float = len(dm.floating_widgets())
assert n_float >= 1, f"expected a floating widget, got {n_float}"

state = dm.save_state()
assert '"floating": true' in state, "saved state should contain a floating container"
ok = dm.restore_state(state)
assert ok, "restore of a layout with a float failed"
print("FLOAT ROUNDTRIP OK")
