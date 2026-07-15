import sys
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)
from demo_app import DemoMainWindow

win = DemoMainWindow()
state = win.dock_manager.save_state()
print("saved bytes:", len(state))

ok = win.dock_manager.restore_state(state)
print("restore_state ->", ok)

# corrupt payload should fail gracefully (return False), not raise
bad = win.dock_manager.restore_state("{not valid json")
print("restore bad ->", bad)

import json
state_dict = json.loads(state)
assert "sidebars" in state_dict, "sidebars key missing from serialized layout state"

state_after = win.dock_manager.save_state()
state_dict_after = json.loads(state_after)
assert state_dict["sidebars"] == state_dict_after["sidebars"], "sidebar state did not round-trip cleanly!"

assert ok is True, "round-trip restore failed"
assert bad is False, "corrupt payload should return False"
print("ROUNDTRIP OK (including sidebar state)")
