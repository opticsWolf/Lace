# -*- coding: utf-8 -*-
"""set_allowed_areas() and what the user actually sees — §5.3.

DockOverlayCross.reset() was a `pass` with a comment saying so, which made
set_allowed_areas() visually inert: only cursor_location() consulted the
allowed set, so a disallowed drop indicator stayed on screen at full size and
merely did nothing when the drag reached it. These tests read the indicator
widgets' visibility, not the refusal — the refusal never regressed.
"""

import pytest
from PySide6.QtWidgets import QMainWindow, QWidget

from lace.dock_overlay import DockOverlay, DockOverlayCross, OverlayMode
from lace.enums import DockWidgetArea


ALL = (DockWidgetArea.left, DockWidgetArea.right, DockWidgetArea.top,
       DockWidgetArea.bottom, DockWidgetArea.center)


@pytest.fixture
def overlay(qapp):
    host = QMainWindow()
    host.resize(600, 400)
    host.setCentralWidget(QWidget(host))
    host.show()
    qapp.processEvents()

    ov = DockOverlay(host, OverlayMode.dock_area)
    ov.resize(400, 300)
    ov._cross.setup_overlay_cross(OverlayMode.dock_area)
    qapp.processEvents()

    yield ov

    ov.hide_overlay()
    host.close()


def _shown(overlay):
    return {area for area, widget in overlay._cross._drop_indicator_widgets.items()
            if not widget.isHidden()}


def test_only_the_allowed_indicators_are_shown(overlay, qapp):
    overlay.set_allowed_areas(DockWidgetArea.left | DockWidgetArea.right)
    qapp.processEvents()

    assert _shown(overlay) == {DockWidgetArea.left, DockWidgetArea.right}


def test_widening_the_set_brings_indicators_back(overlay, qapp):
    """Hiding is not one-way — a later drag with more room must show them."""
    overlay.set_allowed_areas(DockWidgetArea.center)
    qapp.processEvents()
    assert _shown(overlay) == {DockWidgetArea.center}

    overlay.set_allowed_areas(DockWidgetArea.all_dock_areas)
    qapp.processEvents()
    assert _shown(overlay) == set(ALL)


def test_no_allowed_areas_hides_every_indicator(overlay, qapp):
    overlay.set_allowed_areas(DockWidgetArea.no_area)
    qapp.processEvents()

    assert _shown(overlay) == set()


def test_a_hidden_indicator_is_still_refused(overlay, qapp, monkeypatch):
    """The two mechanisms must agree: invisible *and* not droppable."""
    overlay.set_allowed_areas(DockWidgetArea.left)
    qapp.processEvents()

    cross = overlay._cross
    right = cross._drop_indicator_widgets[DockWidgetArea.right]
    monkeypatch.setattr(cross, "mapFromGlobal",
                        lambda _p: right.geometry().center())
    assert cross.cursor_location() != DockWidgetArea.right


def test_rebuilding_the_widgets_reapplies_the_set(overlay, qapp):
    """setup_overlay_cross() makes fresh labels; they must not arrive visible."""
    overlay.set_allowed_areas(DockWidgetArea.top)
    overlay._cross.setup_overlay_cross(OverlayMode.container)
    qapp.processEvents()

    assert _shown(overlay) == {DockWidgetArea.top}


# ── The dead fallback in drop_area_under_cursor() ─────────────────────────
def test_drop_area_is_whatever_the_cross_says(overlay, monkeypatch):
    monkeypatch.setattr(overlay._cross, "cursor_location",
                        lambda: DockWidgetArea.bottom)
    assert overlay.drop_area_under_cursor() == DockWidgetArea.bottom

    monkeypatch.setattr(overlay._cross, "cursor_location",
                        lambda: DockWidgetArea.invalid)
    assert overlay.drop_area_under_cursor() == DockWidgetArea.invalid


def test_no_cross_means_no_drop_area(qapp):
    host = QMainWindow()
    host.show()
    ov = DockOverlay(host, OverlayMode.dock_area)
    try:
        ov._cross = None
        assert ov.drop_area_under_cursor() == DockWidgetArea.invalid
    finally:
        ov.hide_overlay()
        host.close()
