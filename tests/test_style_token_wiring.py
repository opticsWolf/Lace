# -*- coding: utf-8 -*-
"""Style tokens that were declared on the schemas but read by no widget.

Those with a clear purpose are wired up: each test sets one through the style
manager and checks the widget that should follow it, so a token cannot go
back to being silently inert. The rest were removed, and a theme dict written
for 0.7/0.8 that still sets them must load with a warning, not fail.
"""

import logging
import os
import sys
from dataclasses import fields

import pytest
from PySide6.QtGui import QColor, QImage

from lace.dock_manager import DockManager
from lace.dock_style_manager import _SCHEMA_MAP, default_theme_tokens, get_dock_style_manager
from lace.enums import DockWidgetArea
from lace.dock_theme import DockStyleCategory, ThemeSpec, build_theme
from lace.sidebar_tab import VerticalTabButton

#: Declared up to 0.8.1, read by nothing, and removed.
REMOVED = {
    DockStyleCategory.CORE: ("font_family", "font_size", "font_weight",
                             "font_italic", "font_underline"),
    DockStyleCategory.PANEL: ("border_width", "corner_radius", "padding", "margin"),
    DockStyleCategory.TAB: ("padding",),
    DockStyleCategory.TITLE_BAR: ("bg_active", "corner_radius", "padding"),
    DockStyleCategory.SIDEBAR: ("corner_radius", "margin", "tab_padding"),
}


def test_removed_tokens_are_gone_from_schema_defaults_and_builder():
    theme = build_theme(ThemeSpec(base=[20, 20, 20, 255], accent=[0, 120, 212, 255],
                                  text=[220, 220, 220, 255], corner_radius=6,
                                  border_width=1.0))
    for category, names in REMOVED.items():
        declared = {f.name for f in fields(_SCHEMA_MAP[category])}
        for name in names:
            assert name not in declared, f"{category.name}.{name} is still declared"
            assert name not in default_theme_tokens()[category], f"default sets {category.name}.{name}"
            assert name not in theme[category], f"build_theme sets {category.name}.{name}"


def test_old_theme_dict_with_removed_tokens_still_applies(qapp, caplog):
    theme = build_theme(ThemeSpec(base=[20, 20, 20, 255], accent=[0, 120, 212, 255],
                                  text=[220, 220, 220, 255]))
    for category, names in REMOVED.items():
        for name in names:
            theme[category][name] = 1
    theme[DockStyleCategory.TAB]["close_btn_size"] = 21   # a live token alongside

    sm = get_dock_style_manager()
    with caplog.at_level(logging.WARNING):
        sm.apply_theme_dict(theme)

    assert sm.get(DockStyleCategory.TAB, "close_btn_size") == 21
    warned = " ".join(r.getMessage() for r in caplog.records)
    for names in REMOVED.values():
        for name in names:
            assert f"unknown token {name} " in warned


@pytest.fixture
def desk(make_desk):
    desk = make_desk()
    area = desk.add(DockWidgetArea.left, "Alpha")
    desk.add(DockWidgetArea.center, "Beta", area)
    desk.show()
    return desk.manager, area


def _tabs(area):
    return [area.dock_widget(i).tab_widget() for i in range(area.dock_widgets_count())]


@pytest.mark.parametrize("token, getter", [
    ("font_italic", "italic"),
    ("font_underline", "underline"),
])
def test_tab_label_font_follows_italic_and_underline(qapp, desk, token, getter):
    _, area = desk
    tabs = _tabs(area)
    assert not any(getattr(t._title_label.font(), getter)() for t in tabs)

    get_dock_style_manager().update(DockStyleCategory.TAB, **{token: True})
    qapp.processEvents()

    # Both states: the active tab's font is rebuilt on its own path.
    assert all(getattr(t._title_label.font(), getter)() for t in tabs)


@pytest.fixture
def two_areas(make_desk):
    desk = make_desk()
    area = desk.add(DockWidgetArea.left, "Alpha")
    other = desk.add(DockWidgetArea.right, "Beta")
    desk.show(active=area)
    return desk.manager, area, other


def _top_pixel_over_first_tab(title_bar, qapp):
    qapp.processEvents()
    img = QImage(title_bar.size(), QImage.Format_ARGB32)
    img.fill(0)
    title_bar.render(img)
    tab = title_bar.tab_bar().tab(0)
    x = tab.mapTo(title_bar, tab.rect().center()).x()
    return QColor(img.pixel(x, 0))


def test_active_edge_is_off_by_default(qapp, two_areas):
    _, area, other = two_areas
    assert not area._title_bar._active_edge.isVisible()
    assert not other._title_bar._active_edge.isVisible()


def test_active_edge_strip_marks_the_focused_area_over_its_tabs(qapp, two_areas):
    dock_manager, area, other = two_areas
    sm = get_dock_style_manager()
    sm.update(DockStyleCategory.TITLE_BAR, active_edge_color=[255, 0, 0, 255],
              active_edge_width=3)
    qapp.processEvents()

    bar, other_bar = area._title_bar, other._title_bar
    assert bar._active_edge.isVisible()
    assert not other_bar._active_edge.isVisible()
    # Drawn above the tab, which fills its own background over the bar's.
    assert _top_pixel_over_first_tab(bar, qapp).getRgb()[:3] == (255, 0, 0)
    assert _top_pixel_over_first_tab(other_bar, qapp).getRgb()[:3] != (255, 0, 0)

    # Follows focus on the cheap path.
    dock_manager.set_active_dock_area(other)
    qapp.processEvents()
    assert other_bar._active_edge.isVisible()
    assert not bar._active_edge.isVisible()

    # Width 0 turns it off again.
    sm.update(DockStyleCategory.TITLE_BAR, active_edge_width=0)
    qapp.processEvents()
    assert not other_bar._active_edge.isVisible()


def test_open_sidebar_tab_takes_the_active_font_weight(qapp):
    # Fonts rather than pixels: the offscreen platform has no font database,
    # so bold and regular text render alike there.
    button = VerticalTabButton("Panel")
    sm = get_dock_style_manager()
    try:
        assert not button._label_font(True).bold()

        sm.update(DockStyleCategory.SIDEBAR, tab_active_font_weight="bold")
        qapp.processEvents()

        assert button._label_font(True).bold(), "the open tab's label is not bold"
        assert not button._label_font(False).bold(), "the closed tab's label changed too"
        # Sized for the wider weight in either state, so opening never moves a tab.
        button.setChecked(True)
        open_length = button.sizeHint().height()
        button.setChecked(False)
        assert button.sizeHint().height() == open_length

        # Unset, the open tab keeps the closed tabs' weight: a theme that made
        # every sidebar label bold before this token was read stays bold.
        sm.update(DockStyleCategory.SIDEBAR, tab_font_weight="bold",
                  tab_active_font_weight=None)
        qapp.processEvents()
        assert button._label_font(False).bold()
        assert button._label_font(True).bold()

        sm.update(DockStyleCategory.SIDEBAR, tab_active_font_weight="normal")
        qapp.processEvents()
        assert button._label_font(False).bold()
        assert not button._label_font(True).bold()
    finally:
        button.deleteLater()


@pytest.mark.skipif(sys.platform == "darwin" and os.environ.get("QT_QPA_PLATFORM") == "offscreen",
                    reason="frameless windows segfault on macOS under offscreen")
def test_frameless_title_follows_italic_and_underline(qapp):
    from lace.frameless_window import FramelessLaceMainWindow

    win = FramelessLaceMainWindow()
    win.setWindowTitle("Title")
    DockManager(win)
    win.show()
    qapp.processEvents()
    try:
        label = win.titleBar.titleLabel
        assert not label.font().italic() and not label.font().underline()

        get_dock_style_manager().update(DockStyleCategory.TITLE_BAR,
                                        font_italic=True, font_underline=True)
        qapp.processEvents()   # the styler refreshes on a zero timer
        qapp.processEvents()
        label.ensurePolished()

        assert label.font().italic()
        assert label.font().underline()
    finally:
        win.close()
