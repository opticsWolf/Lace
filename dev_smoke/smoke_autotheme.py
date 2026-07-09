"""Dev smoke check for OS-Aware Auto Theme Switcher (ThemeManager).
Tests registry check fallback, theme syncing between light/dark defaults,
user-defined stylesheet and theme name overrides, and PaletteChange event handling.
"""
import os
import sys
import tempfile
import logging

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

logging.disable(logging.CRITICAL)

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QApplication, QMainWindow
app = QApplication(sys.argv)

from lace import ThemeManager
from lace.dock_style_manager import apply_dock_theme, get_dock_style_manager

# 1. Initialize ThemeManager
tm = ThemeManager(app)
assert tm.auto_mode_enabled is True
assert tm.user_light_theme == "light"
assert tm.user_dark_theme == "dark"

# 2. Check is_windows_dark_mode returns bool
is_dark = tm.is_windows_dark_mode()
assert isinstance(is_dark, bool)

# 3. Test sync_theme with default dock themes ("light"/"dark")
# Mock dark mode = True
tm.is_windows_dark_mode = lambda: True
assert tm.sync_theme(force=True) is True
assert tm._last_applied_theme == "dark"

# Mock dark mode = False
tm.is_windows_dark_mode = lambda: False
assert tm.sync_theme(force=True) is True
assert tm._last_applied_theme == "light"

# 4. Test auto_mode_enabled = False
tm.auto_mode_enabled = False
tm.is_windows_dark_mode = lambda: True
assert tm.sync_theme(force=True) is False
assert tm._last_applied_theme == "light"  # Unchanged

# 5. Test user-defined overrides (Lace dock theme names e.g. nordic/monokai)
tm.auto_mode_enabled = True
tm.user_dark_theme = "monokai"
tm.user_light_theme = "nordic"

tm.is_windows_dark_mode = lambda: True
assert tm.sync_theme(force=True) is True
assert tm._last_applied_theme == "monokai"

tm.is_windows_dark_mode = lambda: False
assert tm.sync_theme(force=True) is True
assert tm._last_applied_theme == "nordic"

# 6. Test user-defined overrides (Paths to custom .qss files)
with tempfile.TemporaryDirectory() as tmpdir:
    dark_qss_path = os.path.join(tmpdir, "custom_dark.qss")
    light_qss_path = os.path.join(tmpdir, "custom_light.qss")
    
    with open(dark_qss_path, "w", encoding="utf-8") as f:
        f.write("QMainWindow { background-color: #111111; }")
    with open(light_qss_path, "w", encoding="utf-8") as f:
        f.write("QMainWindow { background-color: #eeeeee; }")

    tm.user_dark_theme = dark_qss_path
    tm.user_light_theme = light_qss_path

    tm.is_windows_dark_mode = lambda: True
    assert tm.sync_theme(force=True) is True
    assert tm._last_applied_theme == dark_qss_path
    assert "background-color: #111111;" in app.styleSheet()

    tm.is_windows_dark_mode = lambda: False
    assert tm.sync_theme(force=True) is True
    assert tm._last_applied_theme == light_qss_path
    assert "background-color: #eeeeee;" in app.styleSheet()

# 7. Test PaletteChange event filtering
win = QMainWindow()
tm.install_listener(win)
sync_count = [0]
orig_sync = tm.sync_theme
def count_sync(*args, **kwargs):
    sync_count[0] += 1
    return orig_sync(*args, **kwargs)
tm.sync_theme = count_sync

event = QEvent(QEvent.Type.PaletteChange)
QApplication.sendEvent(win, event)
assert sync_count[0] == 1, f"Expected 1 sync_theme call on PaletteChange, got {sync_count[0]}"

tm.remove_listener(win)
print("SMOKE AUTO THEME SWITCHER OK")
