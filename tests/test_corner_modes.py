# -*- coding: utf-8 -*-
"""Phase 5 corner handling: the cap overlays stay on top, docked content is
never masked, and ``corner_clip`` picks cap / inset / none."""

import json
import logging

import pytest
from PySide6.QtWidgets import QLabel, QMainWindow, QVBoxLayout, QWidget

from lace.dock_manager import DockManager
from lace.dock_paint import chrome_content_margin
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea
from lace.theme_models import ThemeJson
from tests.theme_sets import FIXTURES


def _apply(qapp, **overrides):
    raw = json.loads((FIXTURES / "kilim_midnight_neo.json").read_text(encoding="utf-8"))
    raw.update(overrides)
    get_dock_style_manager().apply_theme_dict(ThemeJson.model_validate(raw).build_theme_dict())
    for _ in range(3):
        qapp.processEvents()


@pytest.fixture
def manager(qapp):
    _apply(qapp)
    win = QMainWindow()
    dm = DockManager(win)
    win.resize(800, 600)
    win.show()
    qapp.processEvents()
    yield dm
    win.close()


def _mk(name, widget=None):
    dw = DockWidget(name)
    dw.set_widget(widget or QLabel(name))
    return dw


def _top_child(w):
    return [c for c in w.children() if isinstance(c, QWidget)][-1]


def _assert_on_top(dw):
    area = dw.dock_area_widget()
    assert _top_child(area) is area._border_overlay
    assert _top_child(dw) is dw._corner_cap


def test_overlays_on_top_after_set_widget(manager, qapp):
    dw = _mk("A")
    manager.add_dock_widget(DockWidgetArea.center, dw)
    qapp.processEvents()
    dw.set_widget(QLabel("replaced"))
    qapp.processEvents()
    _assert_on_top(dw)


def test_overlays_on_top_after_tab_switch(manager, qapp):
    a, b = _mk("A"), _mk("B")
    area = manager.add_dock_widget(DockWidgetArea.center, a)
    manager.add_dock_widget(DockWidgetArea.center, b, area)
    qapp.processEvents()
    area.set_current_dock_widget(a)
    qapp.processEvents()
    _assert_on_top(a)
    area.set_current_dock_widget(b)
    qapp.processEvents()
    _assert_on_top(b)


def test_overlays_on_top_after_restore(manager, qapp):
    a, b = _mk("A"), _mk("B")
    manager.add_dock_widget(DockWidgetArea.left, a)
    manager.add_dock_widget(DockWidgetArea.right, b)
    qapp.processEvents()
    assert manager.restore_state(manager.save_state())
    qapp.processEvents()
    _assert_on_top(a)
    _assert_on_top(b)


def test_late_child_in_user_content_stays_below(manager, qapp):
    content = QWidget()
    QVBoxLayout(content)
    dw = _mk("A", content)
    manager.add_dock_widget(DockWidgetArea.center, dw)
    qapp.processEvents()
    content.layout().addWidget(QLabel("late"))
    qapp.processEvents()
    _assert_on_top(dw)


def test_no_mask_on_docked_content(manager, qapp, monkeypatch):
    calls = []
    monkeypatch.setattr(QWidget, "setMask", lambda self, *a: calls.append(self))
    dw = _mk("A")
    manager.add_dock_widget(DockWidgetArea.center, dw)
    for _ in range(3):
        qapp.processEvents()
    dw.resize(dw.width() - 40, dw.height() - 30)
    _apply(qapp, corner_radius=16)
    assert calls == []


def test_cap_mode_caps_flush_content(manager, qapp):
    _apply(qapp, content_margin=0, corner_clip="cap")
    dw = _mk("A")
    manager.add_dock_widget(DockWidgetArea.center, dw)
    qapp.processEvents()
    shape = dw._cap_shape()
    assert shape is not None and not shape[0].isEmpty()


def test_none_mode_creates_no_cap(manager, qapp):
    _apply(qapp, content_margin=0, corner_clip="none")
    dw = _mk("A")
    area = manager.add_dock_widget(DockWidgetArea.center, dw)
    qapp.processEvents()
    area.grab()
    assert dw._cap_shape() is None
    assert dw._cap_key is None
    assert area._border_overlay._cap_key is None


def test_inset_mode_grows_margins(manager, qapp):
    _apply(qapp, content_margin=0, corner_clip="inset", corner_radius=16, border_width=1)
    dw = _mk("A")
    manager.add_dock_widget(DockWidgetArea.center, dw)
    qapp.processEvents()
    m = dw._layout.contentsMargins()
    need = chrome_content_margin(1, 16) - 1
    assert (m.left(), m.right(), m.bottom()) == (need, need, need)
    assert dw._cap_shape() is None


def test_native_child_falls_back_to_inset(manager, qapp, caplog):
    content = QWidget()
    native = QWidget(content)
    native.winId()   # forces a native window
    with caplog.at_level(logging.INFO, logger="lace.dock_widget"):
        dw = _mk("A", content)
        manager.add_dock_widget(DockWidgetArea.center, dw)
        _apply(qapp, content_margin=0, corner_clip="cap", corner_radius=10)
        _apply(qapp, content_margin=0, corner_clip="cap", corner_radius=12)
    assert dw._corner_clip == "inset"
    assert sum("native child" in r.message for r in caplog.records) == 1


def test_invalid_corner_clip_rejected():
    raw = json.loads((FIXTURES / "kilim_midnight_neo.json").read_text(encoding="utf-8"))
    raw["corner_clip"] = "round"
    with pytest.raises(Exception):
        ThemeJson.model_validate(raw)
