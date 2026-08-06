# -*- coding: utf-8 -*-
"""DockStyleManager tests — ARCHITECTURE.md §3.10 (dock_style_manager.py).

Covers the singleton, token update/coercion (QColor storage), the generation
counter, grouped ``update()`` sugar, subscriber registration/notification,
named-theme application (with reset-to-defaults semantics), and
``apply_theme_dict()`` used by JSON theme loading.
"""

import pytest
from PySide6.QtCore import QObject
from PySide6.QtGui import QColor

from lace.dock_style_manager import (
    DockStyleManager,
    get_dock_style_manager,
    apply_dock_theme,
)
from lace.dock_theme import DockStyleCategory


def test_singleton_instance():
    assert DockStyleManager.instance() is DockStyleManager.instance()
    assert get_dock_style_manager() is DockStyleManager.instance()


def test_colors_stored_natively_as_qcolor(qapp):
    sm = get_dock_style_manager()
    sm.update(DockStyleCategory.CORE, accent_color="#ff8800")
    value = sm.get(DockStyleCategory.CORE, "accent_color")
    assert isinstance(value, QColor)
    assert value.name() == "#ff8800"
    # list token is coerced too
    sm.update(DockStyleCategory.CORE, accent_color=[0, 120, 212, 255])
    assert sm.get(DockStyleCategory.CORE, "accent_color").blue() == 212


def test_update_returns_changed_keys_only():
    sm = get_dock_style_manager()
    changed = sm.update(DockStyleCategory.TAB, corner_radius=6, indicator_width=4)
    assert changed == {"corner_radius", "indicator_width"}
    assert sm.update(DockStyleCategory.TAB, corner_radius=6) == set()  # no-op


def test_generation_advances_on_mutation_only():
    sm = get_dock_style_manager()
    g0 = sm.generation
    sm.update(DockStyleCategory.CORE, text_color=[10, 20, 30])
    assert sm.generation == g0 + 1
    sm.update(DockStyleCategory.CORE, text_color=[10, 20, 30])  # same value
    assert sm.generation == g0 + 1


def test_unknown_keys_are_skipped_silently():
    sm = get_dock_style_manager()
    assert sm.update(DockStyleCategory.CORE, not_a_real_token=1) == set()
    assert sm.get(DockStyleCategory.CORE, "not_a_real_token", "fallback") == "fallback"


def test_get_all_returns_flat_schema_dict():
    sm = get_dock_style_manager()
    tokens = sm.get_all(DockStyleCategory.TITLE_BAR)
    assert {"bg_normal", "height", "button_spacing", "font_family"} <= set(tokens)
    assert isinstance(tokens["button_size"], int)


def test_grouped_update_sugar_expands_to_flat_tokens():
    sm = get_dock_style_manager()
    changed = sm.update(
        DockStyleCategory.TITLE_BAR,
        button={"size": 22, "hover_bg": [70, 70, 74]},
        font={"weight": "bold"},
    )
    assert {"button_size", "button_hover_bg", "font_weight"} <= changed
    assert sm.get(DockStyleCategory.TITLE_BAR, "button_size") == 22
    assert sm.get(DockStyleCategory.TITLE_BAR, "font_weight") == "bold"
    assert sm.get(DockStyleCategory.TITLE_BAR, "button_hover_bg").getRgb()[:3] == (70, 70, 74)
    # unknown sub-keys inside a group are skipped, flat writes still work
    changed = sm.update(DockStyleCategory.TITLE_BAR, button={"nope": 1}, height=33)
    assert changed == {"height"}


def test_apply_theme_applies_and_resets_missing_keys(qapp):
    sm = get_dock_style_manager()
    assert apply_dock_theme("monokai")
    assert sm.get(DockStyleCategory.CORE, "canvas_bg").name() == "#1c1a1d"
    # custom token set while monokai is active...
    sm.update(DockStyleCategory.CORE, canvas_bg=[1, 2, 3, 255])
    # ...reverts when switching to a theme that does not define it
    assert apply_dock_theme("light")
    assert sm.get(DockStyleCategory.CORE, "canvas_bg").name() == "#dadde1"
    # "default" resets to the hardcoded BASE_DOCK_DEFAULTS
    assert apply_dock_theme("default")
    assert sm.get(DockStyleCategory.CORE, "canvas_bg").name() == "#181818"


def test_apply_theme_unknown_name_returns_false():
    assert apply_dock_theme("does_not_exist") is False


def test_apply_theme_dict_applies_raw_theme_data(qapp):
    from lace.dock_theme import build_theme, ThemeSpec

    sm = get_dock_style_manager()
    theme = build_theme(ThemeSpec(base=[1, 2, 3, 255], accent=[4, 5, 6, 255],
                                  text=[200, 200, 200, 255]))
    assert sm.apply_theme_dict(theme) is True
    assert sm.get(DockStyleCategory.CORE, "canvas_bg").getRgb()[:3] == (1, 2, 3)


# ---------------------------------------------------------------------------
# Subscribers / notifications
# ---------------------------------------------------------------------------
class _Subscriber(QObject):
    def __init__(self):
        super().__init__()
        self.calls = []

    def on_style_changed(self, category, changes):
        self.calls.append((category, dict(changes)))


def test_subscriber_notified_on_update_and_unregistered_after():
    sm = get_dock_style_manager()
    sub = _Subscriber()
    sm.register(sub, DockStyleCategory.CORE)
    try:
        sm.update(DockStyleCategory.CORE, accent_color=[1, 2, 3, 255])
        assert len(sub.calls) == 1
        category, changes = sub.calls[0]
        assert category is DockStyleCategory.CORE
        assert changes["accent_color"].getRgb()[:3] == (1, 2, 3)
        # unrelated category does not notify this subscriber
        sm.update(DockStyleCategory.TAB, corner_radius=5)
        assert len(sub.calls) == 1
    finally:
        sm.unregister(sub, DockStyleCategory.CORE)

    sm.update(DockStyleCategory.CORE, accent_color=[9, 9, 9, 255])
    assert len(sub.calls) == 1  # no further notifications


def test_style_changed_signal_emitted_with_changes():
    sm = get_dock_style_manager()
    received = []
    sm.style_changed.connect(lambda category, changes: received.append((category, changes)))
    try:
        sm.update(DockStyleCategory.PANEL, bg_normal=[11, 12, 13, 255])
        assert len(received) == 1
        assert received[0][0] is DockStyleCategory.PANEL
    finally:
        try:
            sm.style_changed.disconnect()
        except TypeError:
            pass


def test_broadcast_on_apply_theme_notifies_all_categories():
    sm = get_dock_style_manager()
    categories = set()
    sm.style_changed.connect(lambda category, changes: categories.add(category))
    try:
        apply_dock_theme("dracula")
        assert categories == set(DockStyleCategory)
    finally:
        try:
            sm.style_changed.disconnect()
        except TypeError:
            pass
