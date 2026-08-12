# -*- coding: utf-8 -*-
"""Which restyle path runs when — docs/CODE_REVIEW.md §4.1, §4.2.

Focus changes fire on every click, and a single click restyles both the losing
and the gaining dock area. The full refresh_style() rebuilds stylesheets,
re-renders icons and rebuilds fonts, none of which depends on focus, so the
focus path must not reach it. These tests pin the split: the cheap path runs,
the expensive one does not, and the visible result is the same either way.
"""

import pytest
from PySide6.QtWidgets import QLabel, QMainWindow

from lace.dock_area_title_bar import DockAreaTitleBar
from lace.dock_manager import DockManager
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import DockStyleCategory, ThemeSpec, build_theme
from lace.dock_widget import DockWidget
from lace.dock_widget_tab import DockWidgetTab
from lace.enums import DockWidgetArea


@pytest.fixture
def desk(qapp):
    win = QMainWindow()
    win.resize(900, 600)
    dock_manager = DockManager(win)

    def mk(name):
        dock_widget = DockWidget(name)
        dock_widget.set_widget(QLabel(name))
        return dock_widget

    area = dock_manager.add_dock_widget(DockWidgetArea.left, mk("Alpha"))
    dock_manager.add_dock_widget(DockWidgetArea.center, mk("Beta"), area)
    other = dock_manager.add_dock_widget(DockWidgetArea.bottom, mk("Gamma"))
    win.show()
    qapp.processEvents()

    yield dock_manager, area, other

    win.close()
    get_dock_style_manager().apply_theme("default")


@pytest.fixture
def spy(monkeypatch):
    """Count calls to the refresh methods on both chrome classes."""
    calls = {}

    def watch(cls, name):
        original = getattr(cls, name)
        key = f"{cls.__name__}.{name}"
        calls[key] = 0

        def counted(self, *args, **kwargs):
            calls[key] += 1
            return original(self, *args, **kwargs)

        monkeypatch.setattr(cls, name, counted)

    for cls in (DockWidgetTab, DockAreaTitleBar):
        watch(cls, "refresh_style")
        watch(cls, "refresh_focus_tint")
    return calls


def _dimming_theme():
    return build_theme(ThemeSpec(
        base=[14, 11, 28, 255],
        accent=[255, 0, 127, 255],
        text=[245, 245, 255, 255],
        border=[0, 180, 205, 255],
        focus_border_color=[0, 240, 255, 255],
        title_border_bottom=1.5,
        tab_dimming=True,
    ))


def test_focus_change_takes_the_cheap_path(desk, spy, qapp):
    dock_manager, area, other = desk
    dock_manager.set_active_dock_area(other)
    qapp.processEvents()
    spy.update({k: 0 for k in spy})

    dock_manager.set_active_dock_area(area)
    qapp.processEvents()

    assert spy["DockWidgetTab.refresh_focus_tint"] > 0, "no tab restyled at all"
    assert spy["DockWidgetTab.refresh_style"] == 0, \
        "a focus change ran the full tab restyle"
    assert spy["DockAreaTitleBar.refresh_style"] == 0, \
        "a focus change ran the full title-bar restyle"


def test_tab_switch_takes_the_cheap_path(desk, spy, qapp):
    dock_manager, area, _ = desk
    spy.update({k: 0 for k in spy})

    area.set_current_index(1 if area.current_index() == 0 else 0)
    qapp.processEvents()

    assert spy["DockWidgetTab.refresh_focus_tint"] >= 2, \
        "both the leaving and the arriving tab should retint"
    assert spy["DockWidgetTab.refresh_style"] == 0, \
        "a tab switch ran the full tab restyle"


def test_cheap_path_still_produces_the_dimmed_colours(desk, qapp):
    """The split must not change what the user sees."""
    dock_manager, area, other = desk
    get_dock_style_manager().apply_theme_dict(_dimming_theme())

    dock_manager.set_active_dock_area(area)
    qapp.processEvents()
    active_tab = area.dock_widget(area.current_index()).tab_widget()
    focused_indicator = active_tab._indicator
    focused_text = active_tab._applied_text_color
    focused_rule = active_tab._bottom_rule_color

    dock_manager.set_active_dock_area(other)
    qapp.processEvents()
    assert active_tab._indicator != focused_indicator, "indicator did not dim"
    assert active_tab._applied_text_color != focused_text, "label did not dim"
    assert active_tab._bottom_rule_color != focused_rule, "rule kept the focus colour"

    # ...and a full restyle from the same state must agree with the cheap one.
    dimmed = (active_tab._indicator, active_tab._applied_text_color,
              active_tab._bottom_rule_color)
    active_tab.refresh_style()
    assert (active_tab._indicator, active_tab._applied_text_color,
            active_tab._bottom_rule_color) == dimmed


def test_repeated_restyle_reapplies_nothing(desk, qapp):
    """The guards make an unchanged theme a no-op, not a stylesheet rebuild."""
    dock_manager, area, _ = desk
    get_dock_style_manager().apply_theme_dict(_dimming_theme())
    qapp.processEvents()

    tab = area.dock_widget(0).tab_widget()
    applied = []
    original = tab._title_label.setStyleSheet
    tab._title_label.setStyleSheet = lambda qss: (applied.append(qss), original(qss))[1]
    close_applied = []
    close_original = tab._close_button.setStyleSheet
    tab._close_button.setStyleSheet = \
        lambda qss: (close_applied.append(qss), close_original(qss))[1]

    for _ in range(3):
        tab.refresh_style()

    assert not applied, "the label stylesheet was rebuilt for an unchanged colour"
    assert not close_applied, "the close-button stylesheet was rebuilt unchanged"


def test_theme_apply_refreshes_each_dock_widget_once(desk, qapp, monkeypatch):
    """DockWidget subscribes to PANEL *and* CORE, and the bridge used to sweep.

    Three restyles per theme apply for every visible widget: one per subscribed
    category, plus one from DockThemeBridge.refresh_dock_palette() walking
    findChildren(DockWidget). The DockStyled debounce collapses the first two;
    the sweep is gone because the subscription already covers it.
    """
    dock_manager, area, _ = desk
    calls = []
    original = DockWidget.refresh_style
    monkeypatch.setattr(
        DockWidget, "refresh_style",
        lambda self, *a, **k: (calls.append(self), original(self, *a, **k))[1])

    get_dock_style_manager().apply_theme_dict(_dimming_theme())
    qapp.processEvents()

    visible = [dw for dw in calls if dw.isVisible()]
    assert visible, "no visible dock widget restyled on a theme change"
    for dock_widget in set(visible):
        assert visible.count(dock_widget) == 1, \
            f"{dock_widget.objectName()} restyled {visible.count(dock_widget)}x"


def test_theme_change_still_reaches_the_guarded_setters(desk, qapp):
    """A guard that never lets go would be worse than no guard."""
    dock_manager, area, _ = desk
    manager = get_dock_style_manager()
    manager.apply_theme_dict(_dimming_theme())
    qapp.processEvents()

    tab = area.dock_widget(0).tab_widget()
    before = tab._applied_text_color

    manager.apply_theme_dict(build_theme(ThemeSpec(
        base=[250, 250, 250, 255],
        accent=[0, 90, 180, 255],
        text=[20, 20, 20, 255],
        is_light=True,
    )))
    qapp.processEvents()
    assert tab._applied_text_color != before, "the label colour never followed the theme"
    assert manager.get_all(DockStyleCategory.TAB)["text_normal"] is not None
