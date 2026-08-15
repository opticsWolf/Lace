# -*- coding: utf-8 -*-
"""Painting primitive tests — ARCHITECTURE.md §2.10 (dock_paint.py).

Covers the chrome content-margin derivation, the rounded-corner path helpers,
the ChromeTokens token bundle, and a smoke paint of the panel/tab painters
onto an offscreen QImage (no real display required).
"""

from math import ceil

import pytest
from PySide6.QtCore import QRectF, QPointF, QSizeF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QBrush

from lace.dock_paint import (
    chrome_content_margin,
    tab_path,
    top_rounded_path,
    bottom_rounded_path,
    ChromeTokens,
    paint_panel,
    paint_tab,
)

EDGE_NAMES = {Qt.Edge.TopEdge: "top", Qt.Edge.BottomEdge: "bottom",
              Qt.Edge.LeftEdge: "left", Qt.Edge.RightEdge: "right"}


def test_chrome_content_margin_zero_when_plain():
    assert chrome_content_margin(0.0, 0.0) == 0


def test_chrome_content_margin_respects_border():
    assert chrome_content_margin(3.0, 0.0) == 3
    assert chrome_content_margin(0.5, 0.0) == 1  # ceil(0.5)


def test_chrome_content_margin_grows_with_radius():
    assert chrome_content_margin(0.0, 8.0) >= 2
    assert chrome_content_margin(1.0, 12.0) >= chrome_content_margin(1.0, 4.0)


def test_flat_paths_are_plain_rects():
    rect = QRectF(0, 0, 100, 40)
    for path in (top_rounded_path(rect, 0.0), bottom_rounded_path(rect, 0.0)):
        assert path.contains(QPointF(50, 20))
        assert path.boundingRect() == rect


def test_rounded_paths_keep_full_bounds():
    rect = QRectF(10, 10, 120, 50)
    top = top_rounded_path(rect, 8.0)
    bottom = bottom_rounded_path(rect, 8.0)
    assert top.boundingRect() == rect
    assert bottom.boundingRect() == rect
    # Negative radius is clamped to a plain rect, never crashes.
    assert top_rounded_path(rect, -5.0).boundingRect() == rect


# ── tab_path: the general form behind every tab outline ───────────────────
def _corner_points(rect):
    return {
        "top_left": QPointF(rect.left(), rect.top()),
        "top_right": QPointF(rect.right(), rect.top()),
        "bottom_right": QPointF(rect.right(), rect.bottom()),
        "bottom_left": QPointF(rect.left(), rect.bottom()),
    }


@pytest.mark.parametrize("flat_edge, square", [
    (Qt.Edge.BottomEdge, {"bottom_left", "bottom_right"}),
    (Qt.Edge.TopEdge, {"top_left", "top_right"}),
    (Qt.Edge.LeftEdge, {"top_left", "bottom_left"}),
    (Qt.Edge.RightEdge, {"top_right", "bottom_right"}),
    (None, set()),
])
def test_only_the_flat_edges_corners_stay_square(flat_edge, square):
    """Every edge can be the flat one, and it owns exactly its own two corners."""
    rect = QRectF(0, 0, 100, 60)
    path = tab_path(rect, 10.0, flat_edge)
    # A point 1px diagonally inside each corner is covered iff that corner is
    # square: at radius 10 the arc is nowhere near it.
    inward = {"top_left": (1, 1), "top_right": (-1, 1),
              "bottom_right": (-1, -1), "bottom_left": (1, -1)}
    covered = set()
    for name, point in _corner_points(rect).items():
        dx, dy = inward[name]
        if path.contains(QPointF(point.x() + dx, point.y() + dy)):
            covered.add(name)
    assert covered == square
    assert path.boundingRect() == rect, "the path no longer fills its rect"


@pytest.mark.parametrize("flat_edge", list(EDGE_NAMES))
def test_an_open_path_starts_and_ends_on_the_flat_edge(flat_edge):
    """The skipped segment is the flat edge, so both ends sit on it."""
    rect = QRectF(0, 0, 100, 60)
    for radius in (0.0, 8.0):
        path = tab_path(rect, radius, flat_edge, closed=False)
        ends = [path.elementAt(0),
                path.elementAt(path.elementCount() - 1)]
        for end in ends:
            if flat_edge == Qt.Edge.TopEdge:
                assert end.y == pytest.approx(rect.top())
            elif flat_edge == Qt.Edge.BottomEdge:
                assert end.y == pytest.approx(rect.bottom())
            elif flat_edge == Qt.Edge.LeftEdge:
                assert end.x == pytest.approx(rect.left())
            else:
                assert end.x == pytest.approx(rect.right())
        assert {(round(e.x), round(e.y)) for e in ends} == {
            (round(p.x()), round(p.y()))
            for name, p in _corner_points(rect).items()
            if name in _flat_corner_names(flat_edge)
        }, f"radius={radius}: the open path does not span the flat edge"


def _flat_corner_names(flat_edge):
    from lace.dock_paint import _EDGE_CORNERS
    return set(_EDGE_CORNERS[flat_edge])


def test_all_corners_rounded_cannot_be_left_open():
    """With no flat edge there is no segment to skip, so closed is forced."""
    rect = QRectF(0, 0, 100, 60)
    assert tab_path(rect, 8.0, None, closed=False).elementCount() == \
        tab_path(rect, 8.0, None, closed=True).elementCount()
    assert tab_path(rect, 8.0, None, closed=False).contains(rect.center())


def test_the_named_helpers_are_tab_path_special_cases():
    """One implementation behind all three, so they cannot drift apart."""
    rect = QRectF(5, 5, 90, 40)
    for radius in (0.0, 7.0):
        assert top_rounded_path(rect, radius) == \
            tab_path(rect, radius, Qt.Edge.BottomEdge, closed=True)
        assert bottom_rounded_path(rect, radius) == \
            tab_path(rect, radius, Qt.Edge.TopEdge, closed=True)


def test_chrome_tokens_content_margin_matches_free_function():
    tokens = ChromeTokens(bg=QColor(20, 20, 20), border=QColor(255, 255, 255),
                          border_width=2.0, radius=8.0, focus_border=QColor(0, 255, 0))
    assert tokens.content_margin() == chrome_content_margin(2.0, 8.0)
    assert tokens.content_margin() == ceil(max(2.0, 8.0 * (1 - 1 / 2 ** 0.5) + 2.0 / 2 ** 0.5))


def test_paint_panel_and_tab_smoke(qapp):
    """Painting onto a QImage must not crash and must touch pixels."""
    image = QImage(120, 60, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    try:
        rect = QRectF(2, 2, 116, 56)
        tokens = ChromeTokens(bg=QColor(30, 30, 30, 255),
                              border=QColor(200, 200, 200, 255),
                              border_width=2.0, radius=8.0,
                              focus_border=QColor(0, 120, 212, 255))
        paint_panel(painter, rect, tokens, focused=True)
        paint_tab(painter, rect, bg=QColor(40, 40, 40, 255), radius=6.0,
                  indicator=QColor(0, 120, 212, 255), indicator_width=3,
                  indicator_edge=Qt.Edge.BottomEdge)
    finally:
        painter.end()
    # Center pixel should no longer be fully transparent (panel fill applied).
    center = image.pixelColor(60, 30)
    assert center.alpha() > 0


def test_paint_tab_top_indicator_accepted(qapp):
    image = QImage(80, 40, QImage.Format.Format_ARGB32)
    image.fill(QColor(0, 0, 0, 0))
    painter = QPainter(image)
    try:
        paint_tab(painter, QRectF(0, 0, 80, 40), bg=QColor(40, 40, 40, 255),
                  radius=6.0, indicator=QColor(0, 120, 212, 255),
                  indicator_width=3, indicator_edge=Qt.Edge.TopEdge)
    finally:
        painter.end()
    assert image.pixelColor(40, 20).alpha() > 0


def test_high_dpi_drop_indicator_pixmap(qapp):
    from lace.dock_paint import create_high_dpi_drop_indicator_pixmap
    from lace.enums import DockWidgetArea, OverlayMode

    pixmap = create_high_dpi_drop_indicator_pixmap(
        QSizeF(48, 48), DockWidgetArea.left, OverlayMode.container,
        (QColor(255, 255, 255, 255), QColor(0, 0, 0, 0),
         QColor(0, 0, 0, 64), QColor(0, 120, 212, 90), QColor(255, 255, 255, 255)),
        device_pixel_ratio=1.0)
    assert not pixmap.isNull()
    assert pixmap.width() == 48
