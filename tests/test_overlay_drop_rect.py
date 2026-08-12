# -*- coding: utf-8 -*-
"""The drop preview rect — docs/CODE_REVIEW.md §4.4.

Where a dragged window lands is read from DockOverlay.drop_overlay_rect() by
_finalize_drag(). That rect used to be assigned inside paintEvent(), so the
landing geometry was a function of whether a repaint happened to run: an
obscured overlay, or a compositor coalescing paints, handed back a stale or
empty rect. These tests pin that the geometry is computed on demand and does
not depend on painting at all.
"""

import pytest
from PySide6.QtCore import QRect
from PySide6.QtWidgets import QMainWindow, QWidget

from lace.dock_overlay import DockOverlay, OverlayMode
from lace.enums import DockWidgetArea


@pytest.fixture
def overlay(qapp):
    host = QMainWindow()
    host.resize(600, 400)
    target = QWidget(host)
    target.resize(400, 300)
    host.setCentralWidget(target)
    host.show()
    qapp.processEvents()

    ov = DockOverlay(host, OverlayMode.dock_area)
    ov.resize(400, 300)
    yield ov, target

    ov.hide_overlay()
    host.close()


def _at(overlay, area, monkeypatch):
    monkeypatch.setattr(overlay, "drop_area_under_cursor", lambda: area)


@pytest.mark.parametrize("area,expected", [
    (DockWidgetArea.top, QRect(0, 0, 400, 150)),
    (DockWidgetArea.bottom, QRect(0, 150, 400, 150)),
    (DockWidgetArea.left, QRect(0, 0, 200, 300)),
    (DockWidgetArea.right, QRect(200, 0, 200, 300)),
    (DockWidgetArea.center, QRect(0, 0, 400, 300)),
])
def test_rect_is_available_without_ever_painting(overlay, area, expected, monkeypatch):
    ov, _ = overlay
    _at(ov, area, monkeypatch)
    assert ov.drop_overlay_rect() == expected


def test_no_drop_area_means_no_rect(overlay, monkeypatch):
    ov, _ = overlay
    _at(ov, DockWidgetArea.invalid, monkeypatch)
    assert not ov.drop_overlay_rect().isValid()


def test_disabled_preview_means_no_rect(overlay, monkeypatch):
    ov, _ = overlay
    _at(ov, DockWidgetArea.left, monkeypatch)
    ov.enable_drop_preview(False)
    assert not ov.drop_overlay_rect().isValid()


def test_rect_follows_the_cursor_without_a_repaint(overlay, qapp, monkeypatch):
    """The failure mode: the rect lagging one drop area behind the cursor."""
    ov, _ = overlay
    painted = []
    monkeypatch.setattr(type(ov), "repaint",
                        lambda self, *a, **k: painted.append(True))

    _at(ov, DockWidgetArea.left, monkeypatch)
    first = ov.drop_overlay_rect()
    _at(ov, DockWidgetArea.right, monkeypatch)
    second = ov.drop_overlay_rect()

    assert first != second, "the rect did not follow the drop area"
    assert not painted, "the drop rect still depends on a synchronous repaint"


def test_container_mode_uses_thirds(qapp, monkeypatch):
    """The split factor differs by overlay mode; both paths are pure geometry."""
    host = QMainWindow()
    host.resize(600, 400)
    host.show()
    ov = DockOverlay(host, OverlayMode.container)
    ov.resize(300, 300)
    try:
        monkeypatch.setattr(ov, "drop_area_under_cursor",
                            lambda: DockWidgetArea.top)
        assert ov.drop_overlay_rect() == QRect(0, 0, 300, 100)
    finally:
        ov.hide_overlay()
        host.close()
