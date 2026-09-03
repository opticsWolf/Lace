# -*- coding: utf-8 -*-
"""Tab icon colour, size and fallback — docs/IMPROVEMENT_PLAN_v0.7.md §6.

Three separate bugs live in here, and each has its own test below:

* the icon was tinted by ``DockIconProvider``, which knows ``active`` and
  nothing about *focus*, so on every theme with ``tab_dimming`` the label
  dimmed on focus loss and the icon beside it stayed bright;
* the fallback chain was a run of ``elif``s, so a *named* icon that failed to
  resolve (a typo, a missing SVG) suppressed every later fallback and the tab
  ended up with no icon at all rather than the one it should have dropped to;
* the memo guard required an icon *name*, so a tab whose icon comes from
  ``windowIcon()`` re-ran the whole of ``_set_icon_internal`` — pixmap render
  and ``setPixmap`` included — on every single tab switch.
"""

import pytest
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import QLabel, QMainWindow

from lace.dock_icon_provider import get_icon_provider
from lace.dock_manager import DockManager
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import DockStyleCategory
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea
from lace.sidebar_tab import VerticalTabButton


def _solid_icon(color: str) -> QIcon:
    pm = QPixmap(16, 16)
    pm.fill(QColor(color))
    return QIcon(pm)


def _dominant(icon: QIcon, size: int = 16) -> str:
    """The most common non-transparent colour in *icon*'s pixmap."""
    img = icon.pixmap(size, size).toImage()
    counts = {}
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y)
            if c.alpha() > 200:
                counts[c.name()] = counts.get(c.name(), 0) + 1
    assert counts, "icon rendered fully transparent"
    return max(counts, key=counts.get)


@pytest.fixture
def tabbed(qapp):
    """Two dock widgets tabbed into one area, so a tab switch is possible."""
    win = QMainWindow()
    win.resize(800, 600)
    manager = DockManager(win)

    def mk(name):
        dock_widget = DockWidget(name)
        dock_widget.set_widget(QLabel(name))
        return dock_widget

    first = mk("Alpha")
    area = manager.add_dock_widget(DockWidgetArea.left, first)
    second = mk("Beta")
    manager.add_dock_widget(DockWidgetArea.center, second, area)
    win.show()
    qapp.processEvents()

    yield manager, win, first, second

    win.close()


# --- The provider's explicit-colour override ------------------------------

def test_provider_honours_an_explicit_tint(qapp):
    """``color=`` overrides the category's own active/normal resolution.

    Without it a caller whose colour depends on something the provider cannot
    see — the tab's focus state — has no way to ask for it.
    """
    provider = get_icon_provider()
    red = provider.get("close_tab", DockStyleCategory.TAB, color="#ff0000")
    blue = provider.get("close_tab", DockStyleCategory.TAB, color=QColor("#0000ff"))

    assert _dominant(red) == "#ff0000"
    assert _dominant(blue) == "#0000ff"


def test_disabled_still_wins_over_an_explicit_tint(qapp):
    """A disabled icon is disabled-coloured whatever the caller asked for."""
    provider = get_icon_provider()
    forced = provider.get("close_tab", DockStyleCategory.TAB,
                          color="#ff0000", disabled=True)
    assert _dominant(forced) != "#ff0000"


# --- The tab's own icon ----------------------------------------------------

def test_the_tab_icon_follows_the_focus_tint(tabbed):
    """The icon dims with its label, not with ``active`` alone.

    The tint is part of ``update_icon``'s memo key; without that the memo
    short-circuits the very refresh ``refresh_focus_tint()`` asked for.
    """
    _, _, first, _ = tabbed
    tab = first.tab_widget()
    tab.set_default_icon_name("dock")

    tab._focus_icon_color = QColor("#ff0000")
    tab.update_icon()
    bright = _dominant(tab._icon)

    tab._focus_icon_color = QColor("#404040")
    tab.update_icon()
    dimmed = _dominant(tab._icon)

    assert bright == "#ff0000"
    assert dimmed == "#404040"


def test_a_missing_named_icon_falls_back_instead_of_blanking(tabbed):
    """An unresolvable name must not suppress the fallbacks below it.

    With the old ``elif`` chain the name won the branch, resolved to a null
    QIcon, and the tab painted nothing at all.
    """
    _, _, first, _ = tabbed
    tab = first.tab_widget()
    tab.set_default_icon_name("no_such_icon_anywhere")
    first.setWindowIcon(_solid_icon("#00ff00"))
    tab._applied_icon_key = None
    tab.update_icon()

    assert not tab._icon.isNull()
    assert _dominant(tab._icon) == "#00ff00"


def test_an_unnamed_icon_is_memoised_across_tab_switches(tabbed):
    """The memo has no "has a name" guard on it any more.

    A tab whose icon comes from ``windowIcon()`` used to re-render on every
    switch, which is the one path a user hits constantly.
    """
    _, _, first, _ = tabbed
    tab = first.tab_widget()
    first.setWindowIcon(_solid_icon("#00ff00"))
    tab._applied_icon_key = None
    tab.update_icon()

    calls = []
    original = type(tab)._set_icon_internal
    type(tab)._set_icon_internal = lambda self, *a, **k: (
        calls.append(a), original(self, *a, **k))[1]
    try:
        for _ in range(5):
            tab.update_icon()
    finally:
        type(tab)._set_icon_internal = original

    assert calls == []


def test_the_tab_icon_size_comes_from_the_theme(tabbed):
    """``TAB.tab_icon_size``, not a literal 16 buried in update_icon()."""
    _, _, first, _ = tabbed
    tab = first.tab_widget()
    tab.set_default_icon_name("dock")
    tab.update_icon()

    get_dock_style_manager().update(DockStyleCategory.TAB, tab_icon_size=32)
    tab.update_icon()

    assert tab._icon.availableSizes()
    assert max(s.width() for s in tab._icon.availableSizes()) >= 32


# --- The sidebar's tabs ----------------------------------------------------

def test_a_sidebar_tab_tints_its_named_icon(qapp):
    """A named sidebar icon is drawn in the tab's own text colour.

    Sidebar tabs painted whatever QIcon they were handed, so a dark icon
    stayed dark on a dark theme while the text beside it turned light.
    """
    sm = get_dock_style_manager()
    sm.update(DockStyleCategory.SIDEBAR,
              tab_text_normal=QColor("#112233"),
              tab_text_active=QColor("#ffaa00"))

    button = VerticalTabButton("Alpha")
    button.refresh_style()
    button.set_icon_name("dock")

    assert _dominant(button._resolved_icon()) == "#112233"

    button.setChecked(True)
    assert _dominant(button._resolved_icon()) == "#ffaa00"

    button.deleteLater()


def test_sidebar_icon_geometry_is_themed(qapp):
    """``tab_icon_size`` / ``tab_icon_gap``, not the literals 16 and 8."""
    sm = get_dock_style_manager()
    button = VerticalTabButton("Alpha")
    button.refresh_style()
    assert (button._icon_size, button._icon_gap) == (16, 8)

    sm.update(DockStyleCategory.SIDEBAR, tab_icon_size=24, tab_icon_gap=3)
    button.refresh_style()
    assert (button._icon_size, button._icon_gap) == (24, 3)

    button.deleteLater()
