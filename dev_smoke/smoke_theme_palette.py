# -*- coding: utf-8 -*-
"""Smoke test for Lace 5-color ThemeSpec, WCAG contrast, and bridge updates."""
import os
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QColor, QPalette

app = QApplication(sys.argv)

from lace.dock_theme import (
    ThemeSpec, build_theme, _get_contrasting_text_color,
    DockStyleCategory, resolve_dock_colors
)
from lace.dock_style_manager import get_dock_style_manager, apply_dock_theme
from lace.dock_theme_bridge import DockThemeBridge
from lace.dock_widget import DockWidget
from lace.dock_icon_provider import get_icon_provider
from lace.dock_custom_theme import DOCK_THEMES, THEME_SPECS

# Initialize icon provider so DockWidget tabs can create buttons
icons_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lace", "resources", "lace_icons")
try:
    get_icon_provider(icons_dir)
except Exception:
    pass

# 1. Verify 5-Color ThemeSpec & Status Colors
spec = ThemeSpec(
    base=[10, 10, 10, 255],
    accent=[0, 100, 200, 255],
    text=[240, 240, 240, 255],
    surface=[30, 30, 40, 255],
    border=[50, 10, 10, 255],
    success_color=[100, 250, 100, 255],
    warning_color=[250, 200, 50, 255],
    error_color=[250, 50, 50, 255],
    info_color=[50, 150, 250, 255],
)
theme_dict = build_theme(spec)
assert theme_dict[DockStyleCategory.CORE]["canvas_bg"] == [10, 10, 10, 255]
assert theme_dict[DockStyleCategory.CORE]["focus_border_color"] == [50, 10, 10, 255]
assert theme_dict[DockStyleCategory.CORE]["border_color"] == [50, 10, 10, 255]
assert theme_dict[DockStyleCategory.PANEL]["bg_normal"] == [30, 30, 40, 255]
assert theme_dict[DockStyleCategory.CORE]["success_color"] == [100, 250, 100, 255]
assert theme_dict[DockStyleCategory.CORE]["error_color"] == [250, 50, 50, 255]
print("5-Color ThemeSpec and status overrides OK")

# 2. Verify _get_contrasting_text_color
dark_accent = [10, 10, 30, 255]      # low luminance -> white text
light_accent = [250, 250, 240, 255]  # high luminance -> dark text
assert _get_contrasting_text_color(dark_accent) == QColor(255, 255, 255)
assert _get_contrasting_text_color(light_accent) == QColor(20, 20, 20)
print("_get_contrasting_text_color dynamic contrast OK")

# 3. Verify DockThemeBridge and DockWidget subscriptions for CORE and PANEL
sm = get_dock_style_manager()
bridge_app = DockThemeBridge(target=app)
dw = DockWidget("Test Panel")

# Apply a base theme first
apply_dock_theme("dark")
app.processEvents()

# Updating CORE canvas_bg should update app's Window role via DockThemeBridge
sm.update(DockStyleCategory.CORE, canvas_bg=[99, 88, 77, 255])
app.processEvents()
assert app.palette().color(QPalette.ColorRole.Window) == QColor(99, 88, 77, 255), (
    f"Expected app Window color rgb(99, 88, 77), got {app.palette().color(QPalette.ColorRole.Window).name()}"
)

# Updating PANEL bg_normal should update DockWidget's localized panel palette upon visible/refresh
sm.update(DockStyleCategory.PANEL, bg_normal=[123, 45, 67, 255])
app.processEvents()
dw.refresh_style()
assert dw.palette().color(QPalette.ColorRole.Window) == QColor(123, 45, 67, 255), (
    f"Expected DockWidget Window color rgb(123, 45, 67), got {dw.palette().color(QPalette.ColorRole.Window).name()}"
)
assert resolve_dock_colors().panel_bg == QColor(123, 45, 67, 255)
print("DockThemeBridge & DockWidget subscription updates OK")

# 4. Verify all presets in THEME_SPECS and DOCK_THEMES
for name, preset_spec in THEME_SPECS.items():
    assert name in DOCK_THEMES, f"Preset {name} missing from DOCK_THEMES"
    assert apply_dock_theme(name), f"Failed to apply preset {name}"
    colors = resolve_dock_colors()
    assert isinstance(colors.highlighted_text, QColor)
    assert isinstance(colors.success_color, QColor)
    assert isinstance(colors.warning_color, QColor)
    assert isinstance(colors.error_color, QColor)
    assert isinstance(colors.info_color, QColor)

print(f"Verified all {len(THEME_SPECS)} presets in THEME_SPECS and DOCK_THEMES OK")
print("SMOKE THEME PALETTE OK")
