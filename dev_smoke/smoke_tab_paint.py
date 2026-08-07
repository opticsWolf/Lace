"""Verifies the DockWidgetTab chrome after the M5 hex-QSS removal:
  * tab label colour now comes from the palette (was hex QSS),
  * the close button is a ChromeToolButton whose hover fill is painted.

Grab -> QImage -> pixel/palette checks; hover is driven by the settable flag so
no cursor is needed.
"""
import sys, logging
logging.disable(logging.CRITICAL)
from PySide6.QtWidgets import QApplication
app = QApplication(sys.argv)

from PySide6.QtGui import QPalette
from PySide6.QtCore import QSize
from demos.demo_app import DemoMainWindow
from lace.dock_widget_tab import DockWidgetTab
from lace.dock_theme import DockStyleCategory
from lace.dock_style_manager import get_dock_style_manager, apply_dock_theme

win = DemoMainWindow(); win.resize(1000, 700); win.show(); app.processEvents()
sm = get_dock_style_manager()


def check(theme: str):
    apply_dock_theme(theme)
    app.processEvents()
    tab = next((t for t in win.findChildren(DockWidgetTab) if t.isVisible()), None)
    assert tab is not None, "no visible tab"
    tab.refresh_style()   # reflect the tab's current active state (as on theme change)
    app.processEvents()

    # 1. Label colour via palette (was hex QSS 'color:')
    is_active = tab._is_active_tab
    key = "text_active" if is_active else "text_normal"
    tok = sm.get(DockStyleCategory.TAB, key)
    exp_text = tok.getRgb()[:3] if tok else None
    lbl_pal = tab._title_label.palette().color(QPalette.WindowText).getRgb()[:3]

    # 2. Close-button painted hover (was ':hover' QSS)
    cb = tab._close_button
    cb.setVisible(True)
    cb.setFixedSize(QSize(20, 20))
    app.processEvents()
    hb = sm.get(DockStyleCategory.TAB, "close_btn_bg_hover")
    exp_hb = hb.getRgb()[:3] if hb else None
    cb.set_hovered(True)
    app.processEvents()
    himg = cb.grab().toImage()
    hpx = himg.pixelColor(2, 2)
    cb.set_hovered(False)

    return {"is_active": is_active, "lbl_pal": lbl_pal, "exp_text": exp_text,
            "cls": type(cb).__name__, "hover": (hpx.red(), hpx.green(), hpx.blue()),
            "exp_hb": exp_hb}


for theme in ("default", "light", "monokai"):
    r = check(theme)
    print(f"[{theme}] active={r['is_active']} lbl_pal={r['lbl_pal']}/{r['exp_text']} "
          f"close={r['cls']} hover={r['hover']}/{r['exp_hb']}")
    assert r["cls"] == "ChromeToolButton", f"{theme}: close button not ChromeToolButton"
    for got, want in zip(r["lbl_pal"], r["exp_text"]):
        assert abs(got - want) <= 2, f"{theme}: label palette {r['lbl_pal']} != {r['exp_text']}"
    for got, want in zip(r["hover"], r["exp_hb"]):
        assert abs(got - want) <= 2, f"{theme}: close hover {r['hover']} != {r['exp_hb']}"

print("TAB PAINT OK")
