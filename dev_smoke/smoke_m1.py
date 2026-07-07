import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor

app = QApplication(sys.argv)

from lace.dock_style_manager import get_dock_style_manager, apply_dock_theme
from lace.dock_theme import DockStyleCategory
from lace.dock_palette_bridge import resolve_dock_colors
from lace.dock_custome_theme import DOCK_THEMES

sm = get_dock_style_manager()

# 1. Colours are stored natively as QColor now
bg = sm.get(DockStyleCategory.CORE, "canvas_bg")
assert isinstance(bg, QColor), f"expected QColor, got {type(bg)}"
print("canvas_bg is QColor:", bg.name())

allc = sm.get_all(DockStyleCategory.PANEL)
assert isinstance(allc["bg_normal"], QColor)
print("panel bg_normal:", allc["bg_normal"].name())

# 2. generation counter advances on update
g0 = sm.generation
sm.update(DockStyleCategory.CORE, accent_color="#ff8800")
assert sm.generation > g0, "generation did not advance"
acc = sm.get(DockStyleCategory.CORE, "accent_color")
assert isinstance(acc, QColor) and acc.name() == "#ff8800", acc.name()
print("hex string stored as QColor:", acc.name(), "gen", g0, "->", sm.generation)

# 3. resolve cache: same generation -> identical object; new gen -> fresh
c1 = resolve_dock_colors()
c2 = resolve_dock_colors()
assert c1 is c2, "cache should return the same snapshot at same generation"
sm.update(DockStyleCategory.CORE, text_color=[10, 20, 30])
c3 = resolve_dock_colors()
assert c3 is not c1, "cache should refresh after a mutation"
assert c3.text_color.red() == 10
print("resolve cache hit-then-refresh OK")

# 4. list token still accepted
sm.update(DockStyleCategory.CORE, accent_color=[0, 120, 212, 255])
assert sm.get(DockStyleCategory.CORE, "accent_color").blue() == 212

# 5. every theme applies and re-resolves cleanly
for name in DOCK_THEMES:
    assert apply_dock_theme(name), f"theme {name} failed"
    col = resolve_dock_colors()
    assert isinstance(col.canvas_bg, QColor)
print("themes applied:", list(DOCK_THEMES.keys()))

print("M1 SMOKE OK")
