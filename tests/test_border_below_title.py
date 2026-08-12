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
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import QLabel, QMainWindow

from lace.dock_custom_theme import THEME_SPECS
from lace.dock_manager import DockManager
from lace.dock_paint import (ChromeTokens, bottom_open_path,
                             paint_panel_border, top_rounded_path)
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
    # Twice: the first pass runs the DockStyled debounce, the second lets the
    # layout it invalidated settle. Rendering in between catches the area a
    # couple of pixels short of its final size.
    qapp.processEvents()
    qapp.processEvents()
    image = QImage(dock_area.size(), QImage.Format_ARGB32)
    image.fill(0)
    dock_area.render(image)
    return image


def _bg(image, dock_area):
    return image.pixelColor(dock_area.width() // 2, dock_area.height() // 2)


def _differential(dock_area, qapp, **overrides):
    """Render the area with and without the outline, so the two can be diffed.

    Above the join the outline runs through the title bar and the tabs, which
    paint their own background and their own outline in the same pixels. A test
    that compared those pixels against the *content* background would call the
    tab strip an outline. Diffing two renders that differ only in border_width
    isolates what the outline itself puts on screen.
    """
    manager = get_dock_style_manager()
    manager.apply_theme_dict(build_theme(_spec(**overrides)))
    inked = _render(dock_area, qapp)
    # A transparent outline rather than a zero-width one: border_width feeds the
    # content margins, so dropping it would resize the area and leave the two
    # renders misaligned by a couple of pixels — a diff of everything.
    manager.apply_theme_dict(build_theme(
        _spec(**{**overrides, "border": [0, 0, 0, 0],
                 "focus_border_color": [0, 0, 0, 0]})))
    bare = _render(dock_area, qapp)
    assert inked.size() == bare.size(), "the two renders must line up"
    return inked, bare


def _edge_is_inked(inked, bare, dock_area, edge, inset=0):
    """Whether the outline puts anything on the row/column *inset* in from
    *edge*."""
    w, h = dock_area.width(), dock_area.height()
    i = int(inset)
    xs = range(w // 3, w - w // 3)
    ys = range(h // 3, h - h // 3)
    points = {
        "top": [(x, i) for x in xs],
        "bottom": [(x, h - 1 - i) for x in xs],
        "left": [(i, y) for y in ys],
        "right": [(w - 1 - i, y) for y in ys],
    }[edge]
    return any(inked.pixelColor(x, y) != bare.pixelColor(x, y) for x, y in points)


# ── Geometry ──────────────────────────────────────────────────────────────
def test_full_outline_covers_all_four_edges(area, qapp):
    """The default — the token off — is unchanged."""
    dock_manager, dock_area = area
    inked, bare = _differential(dock_area, qapp)

    for edge in ("top", "bottom", "left", "right"):
        assert _edge_is_inked(inked, bare, dock_area, edge), f"no outline on the {edge}"


def test_below_title_drops_only_the_top_edge(area, qapp):
    dock_manager, dock_area = area
    inked, bare = _differential(dock_area, qapp, border_below_title=True)
    inset = dock_area.chrome_border_inset()

    assert not _edge_is_inked(inked, bare, dock_area, "top", inset), \
        "the top edge is still drawn"
    for edge in ("bottom", "left", "right"):
        assert _edge_is_inked(inked, bare, dock_area, edge, inset), \
            f"lost the {edge} edge"


def test_sides_start_at_the_title_bar_underside(area, qapp):
    """Above that line the sides must be bare; below it they must be drawn."""
    dock_manager, dock_area = area
    inked, bare = _differential(dock_area, qapp, border_below_title=True)
    top = int(dock_area.chrome_border_top())
    x = int(dock_area.chrome_border_inset())

    # A few rows above the join, clear of the rounded top corner.
    for y in range(top - 12, top - 6):
        assert inked.pixelColor(x, y) == bare.pixelColor(x, y), \
            f"left side drawn at y={y}, above the title bar"
    # ...and below it.
    for y in range(top + 2, top + 8):
        assert inked.pixelColor(x, y) != bare.pixelColor(x, y), \
            f"left side missing at y={y}"


# ── The side inset ────────────────────────────────────────────────────────
def test_sides_sit_at_the_title_bar_edges_not_the_widget_edges(area, qapp):
    """The three sides move in to the tab column, so they are not at x=0."""
    dock_manager, dock_area = area
    get_dock_style_manager().apply_theme_dict(
        build_theme(_spec(border_below_title=True)))
    inked, bare = _differential(dock_area, qapp, border_below_title=True)
    inset = dock_area.chrome_border_inset()

    assert inset and inset > 0, "no inset to test — the title bar is flush"
    for edge in ("left", "right", "bottom"):
        assert not _edge_is_inked(inked, bare, dock_area, edge, 0), \
            f"the {edge} edge still hugs the widget edge"
        assert _edge_is_inked(inked, bare, dock_area, edge, inset), \
            f"the {edge} edge is not at the title bar's edge"


def test_side_meets_the_leftmost_tabs_outline(area, qapp):
    """One continuous line from the tab down the panel, with no step.

    The panel's left stroke and the tab's are both centred half a pen width in
    from the same edge; if either used a different inset the column would break
    at the join, which is exactly what this asserts cannot happen.
    """
    dock_manager, dock_area = area
    get_dock_style_manager().apply_theme_dict(
        build_theme(_spec(border_below_title=True,
                          tab_border_width=2.0,
                          tab_border_color=[189, 147, 249, 255],
                          tab_border_active_color=[189, 147, 249, 255],
                          indicator_position="none")))
    image = _render(dock_area, qapp)
    bg = _bg(image, dock_area)
    x = int(dock_area.chrome_border_inset())
    top = int(dock_area.chrome_border_top())

    # Unbroken from inside the tab strip, across the join, into the panel.
    for y in range(8, top + 8):
        assert image.pixelColor(x, y) != bg, \
            f"gap at y={y} — the tab outline and the panel edge are not aligned"


def test_no_inset_keeps_the_outline_at_the_widget_edge(area, qapp):
    """A frame that does not override the hook is unmoved."""
    dock_manager, dock_area = area
    get_dock_style_manager().apply_theme_dict(
        build_theme(_spec(border_below_title=True)))
    qapp.processEvents()
    dock_area.chrome_border_inset = lambda: None
    try:
        inked, bare = _differential(dock_area, qapp, border_below_title=True)
    finally:
        del dock_area.chrome_border_inset

    for edge in ("left", "right", "bottom"):
        assert _edge_is_inked(inked, bare, dock_area, edge, 0), \
            f"the {edge} edge moved without an inset to move it"


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
    inked, bare = _differential(dock_area, qapp, border_below_title=True)
    assert dock_area.chrome_border_top() is None
    assert dock_area.chrome_border_inset() is None

    assert _edge_is_inked(inked, bare, dock_area, "top"), \
        "the top edge should come back when there is no title bar to close it"


def test_zero_border_width_draws_nothing(qapp):
    """Straight at the primitive — a rendered area's edges would have to be
    told apart from the title bar's own strip, which is a different claim."""
    image = QImage(60, 40, QImage.Format_ARGB32)
    image.fill(0)
    p = QPainter(image)
    paint_panel_border(
        p, QRectF(0, 0, 60, 40),
        ChromeTokens(bg=QColor(0, 0, 0, 0), border=QColor(255, 0, 0),
                     border_width=0.0, radius=8.0, border_below_title=True),
        top=10.0, side_inset=2.0)
    p.end()
    assert all(image.pixelColor(x, y).alpha() == 0
               for x in range(60) for y in range(40)), \
        "border_width=0 still put ink on the canvas"


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
    inset = int(dock_area.chrome_border_inset())
    w = dock_area.width()
    # The rule sits on the title bar's last row and spans it end to end; the
    # verticals now run up the title bar's own edges, so they meet it there.
    rule_row = top - 1
    assert image.pixelColor(inset, rule_row) != bg, "nothing at the left corner"
    assert image.pixelColor(w - 1 - inset, rule_row) != bg, "nothing at the right corner"
