"""Dev smoke check for JSON theme loading and application.

Covers:
  1. Pydantic theme loading: ThemeJson.load() from a JSON file
  2. JSON theme loading: load_theme_json() one-shot helper + hex color conversion
  3. Applying a theme from JSON: DockStyleManager.apply_theme_dict(),
     ThemeManager.sync_theme(path=...), and default_theme_path resolution
     (single file + directory of "<name>.json" files)
  4. Validation failures: out-of-range channels, missing required fields,
     malformed JSON
"""
import json
import logging
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

logging.disable(logging.CRITICAL)

from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

from lace import ThemeJson, load_theme_json
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import DockStyleCategory, deep_to_serializable
from lace.theme_manager import ThemeManager

SMOKE_THEME = {
    "name": "SmokeTheme",
    "base": [14, 11, 28, 255],
    "accent": "#ff007f",                      # hex string -> [255, 0, 127, 255]
    "text": [245, 245, 255, 255],
    "surface": [24, 19, 44, 255],
    "border": [0, 180, 205, 205],
    "focus_border_color": "#00f0ff",          # hex string with alpha
    "title_mode": "darker",
    "hover_mode": "lighter",
    "corner_radius": 10,
    "border_width": 1.5,
    "title_height": 32,
    "tab_radius": 8,
    "content_margin": [8, 2],
    "indicator_width": 2.0,
    "indicator_position": "bottom",
    "tab_dimming": True,
    "unknown_future_key": "ignored",          # extra keys must be ignored
}

sm = get_dock_style_manager()


def write_json(dirpath, filename, payload):
    path = os.path.join(dirpath, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f)
    return path


with tempfile.TemporaryDirectory() as tmpdir:
    theme_path = write_json(tmpdir, "smoke.json", SMOKE_THEME)

    # 1. Pydantic theme loading from a JSON file ------------------------------
    theme = ThemeJson.load(theme_path)
    assert theme.name == "SmokeTheme"
    assert theme.accent == "#ff007f"          # hex kept as-is in the model
    assert theme.content_margin == [8, 2]
    theme_dict = theme.build_theme_dict()
    assert DockStyleCategory.CORE in theme_dict
    assert len(theme_dict) == len(list(DockStyleCategory))

    # 2. JSON theme loading (one-shot helper) ---------------------------------
    loaded = load_theme_json(theme_path)
    assert loaded == theme_dict
    assert deep_to_serializable(loaded[DockStyleCategory.CORE]["accent_color"]) == [255, 0, 127, 255]
    assert deep_to_serializable(loaded[DockStyleCategory.CORE]["focus_border_color"]) == [0, 240, 255, 255]

    # 3a. Apply a theme from JSON via DockStyleManager -------------------------
    sm.apply_theme_dict(theme_dict)
    assert deep_to_serializable(sm.get(DockStyleCategory.CORE, "canvas_bg")) == [14, 11, 28, 255]
    assert deep_to_serializable(sm.get(DockStyleCategory.CORE, "accent_color")) == [255, 0, 127, 255]
    assert sm.get(DockStyleCategory.TAB, "corner_radius") == 8
    assert sm.get(DockStyleCategory.PANEL, "content_margin") == [8.0, 2.0]

    # 3b. Apply from JSON via ThemeManager.sync_theme(path=...) ----------------
    tm = ThemeManager(app)
    tm.is_windows_dark_mode = lambda: False
    tm.user_light_theme = "light"
    assert tm.sync_theme(force=True, path=theme_path) is True
    assert tm._last_applied_theme == theme_path
    assert deep_to_serializable(sm.get(DockStyleCategory.CORE, "accent_color")) == [255, 0, 127, 255]

    # 3c. Apply from JSON via default_theme_path (single file) -----------------
    tm.default_theme_path = theme_path
    assert tm.sync_theme(force=True) is True
    assert deep_to_serializable(sm.get(DockStyleCategory.CORE, "canvas_bg")) == [14, 11, 28, 255]

    # 3d. Apply from JSON via default_theme_path (directory of <name>.json) ----
    write_json(tmpdir, "dark.json", SMOKE_THEME)
    tm.default_theme_path = tmpdir            # str assignment must normalize
    tm.user_dark_theme = "dark"
    tm.user_light_theme = "dark"
    tm.is_windows_dark_mode = lambda: True
    assert tm.sync_theme(force=True) is True
    assert deep_to_serializable(sm.get(DockStyleCategory.CORE, "canvas_bg")) == [14, 11, 28, 255]

    # 4a. Validation: colour channel out of range ------------------------------
    bad = dict(SMOKE_THEME)
    bad["base"] = [300, 0, 0]
    try:
        ThemeJson.load(write_json(tmpdir, "bad_channel.json", bad))
        raise AssertionError("expected ValidationError for channel 300")
    except Exception as e:
        assert type(e).__name__ == "ValidationError"

    # 4b. Validation: missing required field -----------------------------------
    missing = {k: v for k, v in SMOKE_THEME.items() if k != "text"}
    try:
        ThemeJson.load(write_json(tmpdir, "missing.json", missing))
        raise AssertionError("expected ValidationError for missing 'text'")
    except Exception as e:
        assert type(e).__name__ == "ValidationError"

    # 4c. Validation: malformed JSON -------------------------------------------
    bad_json_path = os.path.join(tmpdir, "bad_syntax.json")
    with open(bad_json_path, "w", encoding="utf-8") as f:
        f.write('{ "base": [1, 2, 3] ')
    try:
        ThemeJson.load(bad_json_path)
        raise AssertionError("expected JSONDecodeError for malformed JSON")
    except Exception as e:
        assert type(e).__name__ == "JSONDecodeError"

    # 4d. Bad JSON theme falls back to registered names, not False-application -
    tm.default_theme_path = bad_json_path
    tm.user_dark_theme = "nordic"             # registered preset -> fallback works
    assert tm.sync_theme(force=True) is True
    assert deep_to_serializable(sm.get(DockStyleCategory.CORE, "canvas_bg")) == [40, 46, 58, 255]

    # 4e. Nonexistent explicit path -> False (no fallback with path=) ----------
    tm.default_theme_path = None
    assert tm.sync_theme(force=True, path=os.path.join(tmpdir, "nope.json")) is False

print("SMOKE THEME JSON OK")
