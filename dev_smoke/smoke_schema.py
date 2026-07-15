import sys
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)
from lace.dock_style_manager import get_dock_style_manager, apply_dock_theme
from lace.dock_theme import (DockStyleCategory, DockTitleBarStyleSchema,
    DockSidePanelStyleSchema, DockCoreStyleSchema, DockTabStyleSchema)
from dataclasses import fields

sm = get_dock_style_manager()
BTN = ("button_color", "button_disable_clr", "button_hover_bg", "button_corner_radius",
       "button_padding", "button_expand_vertical", "button_size", "button_icon_size", "button_spacing")
FONT = ("font_family", "font_size", "font_weight", "font_italic", "font_underline")

tb = sm.get_all(DockStyleCategory.TITLE_BAR)
sp = sm.get_all(DockStyleCategory.SIDEPANEL)
for key in BTN:
    assert key in tb, f"TITLE_BAR missing {key}"
    assert key in sp, f"SIDEPANEL missing {key}"

# shared defaults identical, per-host spacing preserved
assert tb["button_size"] == 18 == sp["button_size"]
assert tb["button_corner_radius"] == 3 == sp["button_corner_radius"]
assert tb["button_spacing"] == 4, tb["button_spacing"]
assert sp["button_spacing"] == 2, sp["button_spacing"]

# field names remain flat on the composed dataclasses
tb_fields = {f.name for f in fields(DockTitleBarStyleSchema)}
assert {"button_color", "button_spacing", "bg_normal"} <= tb_fields

# --- shared _FontFields block (CORE / TAB / TITLE_BAR) ---
for cat in (DockStyleCategory.CORE, DockStyleCategory.TAB, DockStyleCategory.TITLE_BAR):
    got = sm.get_all(cat)
    for key in FONT:
        assert key in got, f"{cat.name} missing {key}"

# shared defaults identical, per-host weight preserved
core = DockCoreStyleSchema()
tab = DockTabStyleSchema()
tbar = DockTitleBarStyleSchema()
assert core.font_family == tab.font_family == tbar.font_family == "Segoe UI"
assert core.font_size == tab.font_size == tbar.font_size == 10
assert core.font_weight == "normal" and tab.font_weight == "normal"
assert tbar.font_weight == "bold", tbar.font_weight          # title bars stay bold
assert tab.active_font_weight == "normal", tab.active_font_weight  # tab-only extra field

# flat names on the composed dataclasses
assert {"font_family", "font_weight"} <= {f.name for f in fields(DockTitleBarStyleSchema)}
assert "active_font_weight" in {f.name for f in fields(DockTabStyleSchema)}

# themes still apply and button tokens resolve
for name in ("default", "light", "monokai"):
    assert apply_dock_theme(name), name
    assert isinstance(sm.get(DockStyleCategory.TITLE_BAR, "button_size"), int)
    assert sm.get(DockStyleCategory.TITLE_BAR, "button_hover_bg") is not None

# --- M6.2 grouped update() sugar: dict expands to flat tokens ---
changed = sm.update(DockStyleCategory.TITLE_BAR,
                    button={"size": 22, "hover_bg": [70, 70, 74]},
                    font={"weight": "normal"})
assert "button_size" in changed and "button_hover_bg" in changed, changed
assert "font_weight" in changed, changed
assert sm.get(DockStyleCategory.TITLE_BAR, "button_size") == 22
assert sm.get(DockStyleCategory.TITLE_BAR, "font_weight") == "normal"
# colour sub-value coerced to QColor like a flat write
assert sm.get(DockStyleCategory.TITLE_BAR, "button_hover_bg").getRgb()[:3] == (70, 70, 74)
# unknown sub-keys are skipped silently, flat writes still work alongside groups
changed = sm.update(DockStyleCategory.TITLE_BAR, button={"nope": 1}, height=33)
assert changed == {"height"}, changed

# --- M6.3 ThemeSpec wrapper is byte-identical to positional _build_theme ---
from lace.dock_theme import ThemeSpec, build_theme, _build_theme
from PySide6.QtGui import QColor
args = ([20, 23, 30, 255], [45, 85, 170, 255], [200, 205, 215, 255])
spec = ThemeSpec(*args, title_mode="darker", hover_mode="lighter")
assert build_theme(spec) == _build_theme(*args, title_mode="darker", hover_mode="lighter")
# QColor inputs normalise to the identical result as list inputs
qspec = ThemeSpec(QColor(20, 23, 30), QColor(45, 85, 170), QColor(200, 205, 215),
                  title_mode="darker", hover_mode="lighter")
assert build_theme(qspec) == build_theme(spec)

print("SCHEMA SMOKE OK")
