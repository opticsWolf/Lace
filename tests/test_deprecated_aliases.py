"""Duplicate entry points warn and point at the name that stays.

Each deprecated alias must raise a DeprecationWarning naming its replacement
and still return what the replacement returns; the replacement itself must
stay silent.
"""
import warnings

import pytest

from lace.enums import DockWidgetArea


@pytest.fixture
def pinned(make_desk):
    desk = make_desk(800, 600)
    desk.add(DockWidgetArea.center, desk.widget("Center"))
    dock = desk.widget("Pinned")
    desk.manager.add_sidebar_widget(DockWidgetArea.left, dock)
    sm = desk.manager.sidebar_manager
    sm.set_animations_enabled(False)
    desk.show()
    return dock, sm, sm._sidebars[DockWidgetArea.left]


def _silent(call):
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        return call()


def test_is_pinned_warns_and_matches_is_in_sidebar(pinned):
    dock, _, _ = pinned
    with pytest.warns(DeprecationWarning, match=r"is_in_sidebar\(\)"):
        assert dock.is_pinned() is _silent(dock.is_in_sidebar) is True


def test_tab_count_warns_and_matches_count(pinned):
    _, _, bar = pinned
    with pytest.warns(DeprecationWarning, match=r"count\(\)"):
        assert bar.tab_count() == _silent(bar.count) == 1


def test_focus_sidebar_warns_and_toggles(pinned, monkeypatch):
    _, sm, _ = pinned
    seen = []
    monkeypatch.setattr(sm, "toggle_sidebar", seen.append)
    with pytest.warns(DeprecationWarning, match=r"toggle_sidebar\(\)"):
        sm.focus_sidebar(DockWidgetArea.left)
    assert seen == [DockWidgetArea.left]


def test_update_resize_margins_warns(pinned):
    _, sm, _ = pinned
    container = sm._overlay
    with pytest.warns(DeprecationWarning, match=r"_update_layout_margins\(\)"):
        container._update_resize_margins()
    _silent(container._update_layout_margins)


def test_internal_paths_use_the_remaining_names(pinned):
    """Showing and counting a sidebar must not hit a deprecated alias."""
    _, sm, bar = pinned
    _silent(lambda: sm.toggle_sidebar(DockWidgetArea.left))
    _silent(bar._update_scroll_visibility)
    _silent(lambda: sm._keyboard.focus_sidebar.emit(DockWidgetArea.left))
