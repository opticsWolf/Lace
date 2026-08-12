# -*- coding: utf-8 -*-
"""CORE.border_below_title — the area outline as three sides, not four.

With the token set, the dock area's outline runs down the left, across the
bottom and back up the right, stopping at the underside of the title bar. The
rule the title bar already draws there (title_border_bottom) becomes the fourth
side, so the frame closes without a second horizontal line above the header.

Pixels rather than tokens throughout: the claim is about geometry, and a token
that reaches paint_panel_border but strokes the wrong path would satisfy any
token-level check.
"""

import pytest
from PySide6.QtCore import QRectF
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QLabel, QMainWindow

from lace.dock_custom_theme import THEME_SPECS
from lace.dock_manager import DockManager
from lace.dock_paint import bottom_open_path, top_rounded_path
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import DockStyleCategory, ThemeSpec, build_theme
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea


@pytest.fixture
def area(qapp):
    win = QMainWindow()
    win.resize(800, 600)
    dock_manager = DockManager(win)
    first = DockWidget("Alpha")
    first.set_widget(QLabel("x"))
    dock_area = dock_manager.add_dock_widget(DockWidgetArea.center, first)
    win.show()
    qapp.processEvents()
    dock_manager.set_active_dock_area(dock_area)
    qapp.processEvents()

    yield dock_manager, dock_area

    win.close()
    get_dock_style_manager().apply_theme("default")


def _spec(**overrides):
    base = dict(
        base=[40, 42, 54, 255],
        accent=[189, 147, 249, 255],
        text=[248, 248, 242, 255],
        border=[189, 147, 249, 255],
        focus_border_color=[189, 147, 249, 255],
        border_width=2.0,
        corner_radius=10,
    )
    base.update(overrides)
    return ThemeSpec(**base)


def _render(dock_area, qapp):
    qapp.processEvents()
    image = QImage(dock_area.size(), QImage.Format_ARGB32)
    image.fill(0)
    dock_area.render(image)
    return image


def _edge_has_ink(image, dock_area, edge, bg):
    """Whether the outermost row/column of *edge* carries anything but bg."""
    w, h = dock_area.width(), dock_area.height()
    # Middle third only — the rounded corners fall outside the straight edges.
    xs = range(w // 3, w - w // 3)
    ys = range(h // 3, h - h // 3)
    points = {
        "top": [(x, 0) for x in xs],
        "bottom": [(x, h - 1) for x in xs],
        "left": [(0, y) for y in ys],
        "right": [(w - 1, y) for y in ys],
    }[edge]
    return any(image.pixelColor(x, y) != bg for x, y in points)


def _bg(image, dock_area):
    return image.pixelColor(dock_area.width() // 2, dock_area.height() // 2)


# ── Geometry ──────────────────────────────────────────────────────────────
def test_full_outline_covers_all_four_edges(area, qapp):
    """The default — the token off — is unchanged."""
    dock_manager, dock_area = area
    get_dock_style_manager().apply_theme_dict(build_theme(_spec()))
    image = _render(dock_area, qapp)
    bg = _bg(image, dock_area)

    for edge in ("top", "bottom", "left", "right"):
        assert _edge_has_ink(image, dock_area, edge, bg), f"no outline on the {edge}"


def test_below_title_drops_only_the_top_edge(area, qapp):
    dock_manager, dock_area = area
    get_dock_style_manager().apply_theme_dict(
        build_theme(_spec(border_below_title=True)))
    image = _render(dock_area, qapp)
    bg = _bg(image, dock_area)

    assert not _edge_has_ink(image, dock_area, "top", bg), \
        "the top edge is still drawn"
    for edge in ("bottom", "left", "right"):
        assert _edge_has_ink(image, dock_area, edge, bg), f"lost the {edge} edge"


def test_sides_start_at_the_title_bar_underside(area, qapp):
    """Above that line the sides must be bare; below it they must be drawn."""
    dock_manager, dock_area = area
    get_dock_style_manager().apply_theme_dict(
        build_theme(_spec(border_below_title=True)))
    image = _render(dock_area, qapp)
    bg = _bg(image, dock_area)
    top = int(dock_area.chrome_border_top())

    # A few rows above the join, clear of the rounded top corner.
    for y in range(top - 12, top - 6):
        assert image.pixelColor(0, y) == bg, f"left side drawn at y={y}, above the title bar"
    # ...and below it.
    for y in range(top + 2, top + 8):
        assert image.pixelColor(0, y) != bg, f"left side missing at y={y}"


def test_border_top_follows_the_title_bar(area, qapp):
    """Resolved per repaint, so a taller title bar moves the join with it."""
    dock_manager, dock_area = area
    manager = get_dock_style_manager()

    manager.apply_theme_dict(build_theme(_spec(border_below_title=True,
                                               title_height=24)))
    qapp.processEvents()
    short = dock_area.chrome_border_top()

    manager.apply_theme_dict(build_theme(_spec(border_below_title=True,
                                               title_height=48)))
    qapp.processEvents()
    tall = dock_area.chrome_border_top()

    assert tall > short, "the join did not move with the title bar's height"
    assert tall - short == pytest.approx(24, abs=2)


def test_no_title_bar_leaves_the_outline_closed(area, qapp):
    """Three sides around nothing would just look like a broken frame."""
    dock_manager, dock_area = area
    get_dock_style_manager().apply_theme_dict(
        build_theme(_spec(border_below_title=True)))
    qapp.processEvents()

    dock_area._title_bar.setVisible(False)
    qapp.processEvents()
    assert dock_area.chrome_border_top() is None

    image = _render(dock_area, qapp)
    bg = _bg(image, dock_area)
    assert _edge_has_ink(image, dock_area, "top", bg), \
        "the top edge should come back when there is no title bar to close it"


def test_zero_border_width_draws_nothing(area, qapp):
    dock_manager, dock_area = area
    get_dock_style_manager().apply_theme_dict(
        build_theme(_spec(border_width=0.0, border_below_title=True)))
    image = _render(dock_area, qapp)
    bg = _bg(image, dock_area)
    for edge in ("top", "bottom", "left", "right"):
        assert not _edge_has_ink(image, dock_area, edge, bg), \
            f"border_width=0 still drew the {edge} edge"


# ── The path helper ───────────────────────────────────────────────────────
def test_bottom_open_path_omits_the_top_segment():
    rect = QRectF(0, 0, 80, 40)
    for radius in (0.0, 8.0):
        path = bottom_open_path(rect, radius)
        assert path.elementAt(0).y == pytest.approx(rect.top())
        last = path.elementAt(path.elementCount() - 1)
        assert last.y == pytest.approx(rect.top())
        # Starts and ends on opposite sides, so the top is genuinely open.
        assert path.elementAt(0).x == pytest.approx(rect.left())
        assert last.x == pytest.approx(rect.right())
        assert path.elementCount() < top_rounded_path(rect, radius).elementCount() + 2


# ── The preset ────────────────────────────────────────────────────────────
def test_violet_haze_uses_it():
    spec = THEME_SPECS["violet_haze"]
    assert spec.border_below_title is True
    assert spec.border_width, "the outline has to exist for the token to show"
    assert spec.title_border_bottom, "nothing would close the top of the frame"


def test_violet_haze_frame_meets_the_title_rule(area, qapp):
    """The rule spans the full width, so the three sides join it at the corners.

    A gap here would read as a broken frame — the same defect the sidebar
    header had against its card outline.
    """
    dock_manager, dock_area = area
    get_dock_style_manager().apply_theme("violet_haze")
    qapp.processEvents()
    dock_manager.set_active_dock_area(dock_area)
    image = _render(dock_area, qapp)
    bg = _bg(image, dock_area)

    top = int(dock_area.chrome_border_top())
    w = dock_area.width()
    # The rule sits on the title bar's last row; both far ends must carry ink
    # so the verticals have something to meet.
    rule_row = top - 1
    assert image.pixelColor(0, rule_row) != bg, "nothing at the left corner"
    assert image.pixelColor(w - 1, rule_row) != bg, "nothing at the right corner"
