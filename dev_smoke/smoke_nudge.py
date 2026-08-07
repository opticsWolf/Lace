"""Verifies dock chrome + panels recolour on theme switch WITHOUT relying on the
DockThemeBridge stylesheet "nudge".

After the M5 hex-QSS removal, every coloured surface is painted or palette-driven,
so a theme switch must recolour purely via palettes + refresh_style — no
stylesheet re-evaluation thrash.  This samples a visible DockWidget panel and a
dock-area title bar across themes.
"""
import sys, logging
logging.disable(logging.CRITICAL)
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)

from PySide6.QtGui import QPalette
from demos.demo_app import DemoMainWindow
from lace.dock_widget import DockWidget
from lace.dock_area_title_bar import DockAreaTitleBar
from lace.dock_theme import DockStyleCategory
from lace.dock_style_manager import get_dock_style_manager, apply_dock_theme

win = DemoMainWindow(); win.resize(1000, 700); win.show(); app.processEvents()
sm = get_dock_style_manager()


def check(theme: str):
    apply_dock_theme(theme)
    app.processEvents()   # flush the debounced refresh_style singleShots

    dw = next((d for d in win.findChildren(DockWidget) if d.isVisible()), None)
    assert dw is not None, "no visible dock widget"
    panel_win = dw.palette().color(QPalette.Window).getRgb()[:3]
    panel_tok = sm.get(DockStyleCategory.PANEL, "bg_normal").getRgb()[:3]

    tbar = next((t for t in win.findChildren(DockAreaTitleBar) if t.isVisible()), None)
    tb_bg = getattr(tbar, "_bg_color", None)
    tb_px = tb_bg.getRgb()[:3] if tb_bg else None
    tb_tok = sm.get(DockStyleCategory.TITLE_BAR, "bg_normal").getRgb()[:3]

    return {"panel": panel_win, "panel_tok": panel_tok, "tbar": tb_px, "tbar_tok": tb_tok}


for theme in ("default", "light", "monokai", "nordic"):
    r = check(theme)
    print(f"[{theme}] panel={r['panel']}/{r['panel_tok']} titlebar={r['tbar']}/{r['tbar_tok']}")
    for got, want in zip(r["panel"], r["panel_tok"]):
        assert abs(got - want) <= 2, f"{theme}: panel {r['panel']} != {r['panel_tok']}"
    if r["tbar"] is not None:
        for got, want in zip(r["tbar"], r["tbar_tok"]):
            assert abs(got - want) <= 2, f"{theme}: titlebar {r['tbar']} != {r['tbar_tok']}"

print("NUDGE-FREE RECOLOR OK")
