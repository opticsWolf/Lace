# -*- coding: utf-8 -*-
"""Dock context-menu icons: each tab entry carries its own panel icon.

Regression for the title-bar / tabs menu showing ``tab_list`` for every dock.
"""

from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import QMenu

from lace.dock_menu import (dock_icon, MenuContext, MenuSection,
                            build_dock_context_menu)
from lace.dock_theme import DockStyleCategory
from lace.enums import DockWidgetArea


def _icon(color):
    pixmap = QPixmap(16, 16)
    pixmap.fill(QColor(color))
    return QIcon(pixmap)


def _add_tab(desk, title, icon=None, target=None):
    dock = desk.widget(title)
    if icon is not None:
        dock.set_icon(icon)
    return desk.add(DockWidgetArea.center, dock, target)


def _switch_actions(menu):
    """``{tab index: action}`` for the checkable tab entries."""
    found = {}
    for action in menu.actions():
        data = action.data()
        if isinstance(data, (tuple, list)) and data and data[0] == "switch_tab":
            found[data[1]] = action
    return found


def test_tab_menu_uses_each_tabs_own_icon(qapp, make_desk):
    desk = make_desk()
    area = _add_tab(desk, "Red", _icon("#ff0000"))
    _add_tab(desk, "Green", _icon("#00ff00"), area)
    desk.show(area)
    qapp.processEvents()

    menu = QMenu()
    area._title_bar.build_dock_menu(menu, area._title_bar.tab_bar())
    actions = _switch_actions(menu)

    assert set(actions) == {0, 1}
    assert actions[0].text() == "Red"
    assert actions[1].text() == "Green"
    assert actions[0].icon().cacheKey() == area._title_bar.tab_bar().tab(0).icon().cacheKey()
    assert actions[1].icon().cacheKey() == area._title_bar.tab_bar().tab(1).icon().cacheKey()
    assert actions[0].icon().cacheKey() != actions[1].icon().cacheKey()


def test_a_tab_without_an_icon_falls_back_to_the_generic_tab_icon(qapp, make_desk):
    desk = make_desk()
    area = _add_tab(desk, "No icon")
    _add_tab(desk, "Other", target=area)
    desk.show(area)
    qapp.processEvents()

    assert area._title_bar.tab_bar().tab(0).icon().isNull()

    menu = QMenu()
    area._title_bar.build_dock_menu(menu, area._title_bar.tab_bar())
    actions = _switch_actions(menu)

    assert not actions[0].icon().isNull()
    assert (actions[0].icon().cacheKey()
            == dock_icon("tab_list", DockStyleCategory.TITLE_BAR).cacheKey())


def test_the_title_bar_context_menu_uses_the_same_tab_icons(qapp, make_desk):
    desk = make_desk()
    area = _add_tab(desk, "Blue", _icon("#0000ff"))
    _add_tab(desk, "Magenta", _icon("#ff00ff"), area)
    desk.show(area)
    qapp.processEvents()

    # The title-bar context menu and its tabs menu share this builder.
    title_bar = area._title_bar
    title_bar.mark_tabs_menu_outdated()
    title_bar.on_tabs_menu_about_to_show()
    actions = _switch_actions(title_bar._tabs_menu)

    assert actions[0].icon().cacheKey() == title_bar.tab_bar().tab(0).icon().cacheKey()
    assert actions[1].icon().cacheKey() == title_bar.tab_bar().tab(1).icon().cacheKey()


def test_the_application_icon_is_the_final_fallback(qapp, make_desk):
    desk = make_desk()
    area = _add_tab(desk, "No icon")
    _add_tab(desk, "Other", target=area)
    desk.show(area)
    qapp.processEvents()

    app_icon = _icon("#123456")
    previous = qapp.windowIcon()
    qapp.setWindowIcon(app_icon)
    try:
        menu = QMenu()
        context = MenuContext(
            widget_type="DockAreaTitleBar",
            sections=MenuSection.TITLE_BAR,
            area=area,
            tab_bar=area._title_bar.tab_bar(),
            count=2,
            icon_overrides={"tab_list": QIcon()},  # force the generic glyph out
        )
        build_dock_context_menu(context, menu)
        actions = _switch_actions(menu)
        assert actions[0].icon().cacheKey() == app_icon.cacheKey()
    finally:
        qapp.setWindowIcon(previous)
