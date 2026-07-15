import sys
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import QCoreApplication
app = QApplication(sys.argv)

from lace.dock_styled import DockStyled
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import DockStyleCategory

sm = get_dock_style_manager()

class Probe(QWidget, DockStyled):
    STYLE_CATEGORIES = (DockStyleCategory.CORE, DockStyleCategory.PANEL)
    def __init__(self):
        super().__init__()
        self.count = 0
        self._init_dock_style()
    def refresh_style(self):
        self.count += 1

p = Probe()
assert p.count == 1, "initial refresh should run once"

# Two category changes in one frame -> debounced to a single refresh
sm.update(DockStyleCategory.CORE, accent_color="#123456")
sm.update(DockStyleCategory.PANEL, bg_normal="#654321")
assert p.count == 1, "refresh must be deferred, not synchronous"
app.processEvents()
assert p.count == 2, f"expected one coalesced refresh, got {p.count-1}"

# Registration-bug fix: PANEL-only change now triggers a refresh
sm.update(DockStyleCategory.PANEL, bg_normal="#111111")
app.processEvents()
assert p.count == 3, f"PANEL change should refresh, count={p.count}"

# A category we did NOT register for must NOT refresh us
sm.update(DockStyleCategory.SPLITTER, handle_width=9)
app.processEvents()
assert p.count == 3, f"unrelated category must not refresh, count={p.count}"

print("M2 SMOKE OK: debounce coalesces, multi-category registration works")
