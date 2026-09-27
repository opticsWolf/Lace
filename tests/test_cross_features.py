# -*- coding: utf-8 -*-
"""Phase 6 cross-feature checks: features that were each tested alone, together.

- LaceStyle scrollbars inside a ``cap`` corner at the largest radius any
  preset ships: the handle stays inside the arc.
- ``selection="tint"`` themes under LaceStyle: check marks and selected
  item-view text still read on the tinted selection.
- Every REGULAR theme *built* at ``contrast="high"`` under LaceStyle at
  ``contrast="high"``: outlines, the selected-tab underline and disabled text
  meet the high targets.
"""

from dataclasses import replace

import pytest
from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QPainterPath, QPalette
from PySide6.QtWidgets import (QApplication, QMainWindow, QStyle, QStyleOptionButton,
                               QStyleOptionSlider, QStyleOptionTab, QStyleOptionViewItem,
                               QTabBar, QTextEdit)

from lace.dock_custom_theme import THEME_SPECS
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import build_dock_palette, build_theme, resolve_dock_colors
from lace.lace_style import LaceStyle
from lace.theme_contrast import CONTRAST_TARGETS
from lace.theme_models import ThemeJson
from tests.test_lace_style_sweep import (_meets, _outline_cases, _paint_into, _ratio, _state,
                                         W, H)
from tests.theme_sets import FIXTURES, REGULAR, kilim_keys

S = QStyle.StateFlag
PE = QStyle.PrimitiveElement
CE = QStyle.ControlElement
Role = QPalette.ColorRole
G = QPalette.ColorGroup


def spec_for(key):
    if key.startswith("kilim_"):
        return ThemeJson.load(FIXTURES / f"{key}.json").to_theme_spec()
    return THEME_SPECS[key]


def palette_for(spec):
    get_dock_style_manager().apply_theme_dict(build_theme(spec))
    return build_dock_palette(is_panel=False, colors=resolve_dock_colors())


# ---------------------------------------------------------------------------
# Scrollbars inside a cap corner
# ---------------------------------------------------------------------------
def _largest_radius_spec():
    specs = [spec_for(k) for k in list(THEME_SPECS) + kilim_keys()]
    return max(specs, key=lambda s: s.corner_radius or 0)


def _area(path: QPainterPath) -> float:
    total = 0.0
    for poly in path.toFillPolygons():
        pts = [poly.at(i) for i in range(poly.size())]
        total += abs(sum(a.x() * b.y() - b.x() * a.y()
                         for a, b in zip(pts, pts[1:] + pts[:1]))) / 2
    return total


def _handle_path(sb, into) -> QPainterPath:
    """The handle LaceStyle paints (``_primitives.scrollbar``), in ``into``'s
    coordinates."""
    style = sb.style()
    assert isinstance(style, LaceStyle), type(style)
    opt = QStyleOptionSlider()
    sb.initStyleOption(opt)
    h = QRectF(style.subControlRect(QStyle.ComplexControl.CC_ScrollBar, opt,
                                    QStyle.SubControl.SC_ScrollBarSlider, sb))
    thick = sb.height() if sb.orientation() == Qt.Orientation.Horizontal else sb.width()
    pad = 2.0 if thick >= 7 else 1.0
    h = h.adjusted(pad, pad, -pad, -pad)
    r = min(h.width(), h.height()) / 2
    path = QPainterPath()
    path.addRoundedRect(h, r, r)
    return path.translated(QPointF(sb.mapTo(into, sb.rect().topLeft())))


@pytest.fixture
def lace_app(qapp):
    """LaceStyle on the application, restored afterwards."""
    previous, palette = qapp.style().name(), QPalette(qapp.palette())
    style = LaceStyle()
    qapp.setStyle(style)
    yield style
    # setStyle() also resets the app palette; later tests compare against it.
    qapp.setStyle(previous)
    qapp.setPalette(palette)
    QApplication.processEvents()


@pytest.mark.parametrize("bar", ["vertical", "horizontal"])
@pytest.mark.parametrize("mode", ["thin", "expanding"])
def test_scrollbar_handle_stays_inside_the_cap(lace_app, bar, mode):
    """Flush content (margin 0) at the largest shipped radius, scrolled to
    the end so the handle sits against the rounded corner."""
    from lace import DockManager, DockWidget
    from lace.enums import DockWidgetArea, InsertMode

    spec = replace(_largest_radius_spec(), content_margin=0, corner_clip="cap", scrollbar=mode)
    get_dock_style_manager().apply_theme_dict(build_theme(spec))
    lace_app.set_tokens(scrollbar=mode)
    win = QMainWindow()
    win.resize(640, 420)
    dm = DockManager(win)
    text = QTextEdit()
    if bar == "vertical":
        text.setPlainText("word " * 20000)
    else:
        text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        text.setPlainText("x" * 2000)
    dw = DockWidget("Probe", win)
    dw.set_widget(text, InsertMode.force_no_scroll_area)
    dm.add_dock_widget(DockWidgetArea.center, dw)
    win.show()
    for _ in range(6):
        QApplication.processEvents()
    sb = text.verticalScrollBar() if bar == "vertical" else text.horizontalScrollBar()
    sb.setValue(sb.maximum())
    QApplication.processEvents()
    try:
        cap = dw._cap_shape()
        assert cap is not None, "flush content at a non-zero radius must be capped"
        path = cap[0]
        # The measure itself: the content's own bottom-right pixel is capped.
        corner = QPainterPath()
        corner.addRect(path.boundingRect().right() - 1, path.boundingRect().bottom() - 1, 1, 1)
        assert _area(path.intersected(corner)) > 0.2
        handle = _handle_path(sb, dw)
        assert _area(path.intersected(handle)) < 0.05, spec.corner_radius
    finally:
        win.close()
        win.deleteLater()
        QApplication.processEvents()


# ---------------------------------------------------------------------------
# selection="tint"
# ---------------------------------------------------------------------------
def _selected_fill(style, pal):
    opt = QStyleOptionViewItem()
    opt.rect, opt.palette, opt.state = QRect(0, 0, W, H), pal, _state(S.State_Selected)
    img = _paint_into(lambda p: style.drawPrimitive(PE.PE_PanelItemViewItem, opt, p, None))
    return img, img.pixelColor(W // 2, H // 2)


@pytest.mark.parametrize("key", REGULAR)
def test_tint_selection_keeps_marks_and_text_legible(qapp, key):
    spec = replace(spec_for(key), selection="tint")
    pal = palette_for(spec)
    style = LaceStyle(contrast=spec.contrast)
    ui = CONTRAST_TARGETS["ui"][spec.contrast]
    on_accent = CONTRAST_TARGETS["on_accent"][spec.contrast]

    img, fill = _selected_fill(style, pal)
    assert _meets(pal.color(G.Active, Role.HighlightedText), fill, on_accent), \
        round(_ratio(pal.color(G.Active, Role.HighlightedText), fill), 2)

    # An item-view check mark drawn on the selected row.
    check = QStyleOptionViewItem()
    check.rect, check.palette = QRect((W - 16) // 2, (H - 16) // 2, 16, 16), pal
    check.state = _state(S.State_On | S.State_Selected)
    painter_img = img.copy()
    from PySide6.QtGui import QPainter
    p = QPainter(painter_img)
    style.drawPrimitive(PE.PE_IndicatorItemViewItemCheck, check, p, None)
    p.end()
    r = check.rect
    best = max(_ratio(painter_img.pixelColor(x, y), fill)
               for x in range(r.left(), r.right() + 1) for y in range(r.top(), r.bottom() + 1))
    assert best >= min(ui, _best_possible(fill)) - 0.05, round(best, 2)

    # A plain check box under the tint theme.
    box = QStyleOptionButton()
    box.rect, box.palette, box.state = QRect(0, 0, 16, 16), pal, _state(S.State_On)
    bimg = _paint_into(lambda p: style.drawPrimitive(PE.PE_IndicatorCheckBox, box, p, None), 16, 16)
    face = bimg.pixelColor(3, 3)
    best = max(_ratio(bimg.pixelColor(x, y), face) for x in range(3, 13) for y in range(3, 13))
    assert best >= min(ui, _best_possible(face)) - 0.05, round(best, 2)


def _best_possible(bg):
    from PySide6.QtGui import QColor
    return max(_ratio(QColor("white"), bg), _ratio(QColor("black"), bg))


# ---------------------------------------------------------------------------
# contrast="high"
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("key", REGULAR)
def test_high_contrast_themes_under_lace_style(qapp, key):
    spec = replace(spec_for(key), contrast="high")
    pal = palette_for(spec)
    style = LaceStyle(contrast="high")
    window = pal.color(G.Active, Role.Window)
    failures = {name: round(_ratio(line, window), 2)
                for name, (line, target) in _outline_cases(style, pal).items()
                if not _meets(line, window, target)}
    assert not failures, failures

    tab = QStyleOptionTab()
    tab.rect, tab.palette = QRect(0, 0, W, H), pal
    tab.state, tab.shape = _state(S.State_Selected), QTabBar.Shape.RoundedNorth
    img = _paint_into(lambda p: style.drawControl(CE.CE_TabBarTabShape, tab, p, None))
    assert _meets(img.pixelColor(W // 2, H - 1), window, style.ui_ratio)

    # Text on the panel, a button and a field: at the high floor, or a miss
    # the audit reports as the theme's own colour (the engine only nudges those).
    from lace.theme_kit import audit
    report = audit(spec)
    capped = {(m.token, m.surface) for m in report.capped}
    assert not report.failures, report.lines()
    for text, surface, pair in (
            (Role.ButtonText, Role.Button, ("PANEL.text_color", "PANEL.button_bg")),
            (Role.Text, Role.Base, ("PANEL.text_color", "PANEL.input_bg")),
            (Role.WindowText, Role.Window, ("CORE.text_color", "CORE.canvas_bg"))):
        ratio = _ratio(pal.color(G.Active, text), pal.color(G.Active, surface))
        assert pair in capped or _meets(pal.color(G.Active, text), pal.color(G.Active, surface),
                                        CONTRAST_TARGETS["text"]["high"]), (text, round(ratio, 2))


def test_default_theme_is_the_sleek_reference():
    """The default theme is the M2 reference: subtle depth, expanding scrollbars,
    capped corners -- explicitly, not by accident of whichever defaults."""
    from lace.dock_theme import BASE_DOCK_DEFAULTS, ThemeSpec
    spec = ThemeSpec(base=[0, 0, 0], accent=[0, 0, 255], text=[255, 255, 255])
    assert (spec.depth, spec.scrollbar, spec.corner_clip) == ("subtle", "expanding", "cap")
    core = BASE_DOCK_DEFAULTS[next(c for c in BASE_DOCK_DEFAULTS if c.name == "CORE")]
    assert (core["scrollbar"], core["corner_clip"]) == ("expanding", "cap")


def test_dock_content_frame_draws_no_inner_ring(lace_app):
    """A text edit as a dock widget's content has no outline of its own: the
    card is its frame. The same frame outside a dock widget keeps its outline."""
    from PySide6.QtGui import QColor, QImage
    from PySide6.QtWidgets import QStyleOptionFrame

    def edge(widget):
        opt = QStyleOptionFrame()
        opt.initFrom(widget)
        opt.rect = QRect(0, 0, 40, 30)
        img = QImage(40, 30, QImage.Format.Format_ARGB32)
        img.fill(QColor(0, 0, 0, 0))
        from PySide6.QtGui import QPainter
        p = QPainter(img)
        lace_app.drawPrimitive(QStyle.PrimitiveElement.PE_Frame, opt, p, widget)
        p.end()
        return img.pixelColor(0, 15).alpha()

    plain, content = QTextEdit(), QTextEdit()
    content.setProperty("dockWidgetContent", True)
    assert edge(plain) > 0
    assert edge(content) == 0


def test_nested_scroll_area_gets_rounded_corners(lace_app):
    """A text edit inside a form is capped to the control radius: the corner
    pixel shows the backdrop, the edge midpoint the outline. A combo box's
    popup list gets no cap, and switching style away removes it."""
    from PySide6.QtWidgets import QComboBox, QStyleFactory, QVBoxLayout, QWidget
    from lace.style import _frame_cap

    lace_app.set_tokens(control_radius=8)
    host = QWidget()
    host.setAutoFillBackground(True)
    lay = QVBoxLayout(host)
    edit = QTextEdit("x")
    combo = QComboBox()
    combo.addItems(["a", "b"])
    lay.addWidget(edit)
    lay.addWidget(combo)
    host.resize(200, 160)
    host.show()
    QApplication.processEvents()

    cap = _frame_cap.cap_of(edit)
    assert cap is not None and cap.geometry() == edit.rect()
    assert _frame_cap.cap_of(combo.view()) is None

    img = host.grab().toImage()
    o = edit.geometry().topLeft()
    backdrop = host.palette().color(host.backgroundRole())
    assert img.pixelColor(o) == backdrop                                  # corner capped
    assert img.pixelColor(o.x(), o.y() + edit.height() // 2) != backdrop  # outline drawn

    fusion = QStyleFactory.create("Fusion")
    edit.setStyle(fusion)
    assert _frame_cap.cap_of(edit) is None
    host.close()


@pytest.mark.parametrize("order", ["style_first", "manager_first"])
def test_theme_tokens_reach_an_app_set_lace_style(qapp, order):
    """The demo setup: the app sets LaceStyle itself and a DockManager's
    bridges install none. The theme's knobs still reach the style, whether it
    is set before or after the manager is made."""
    from lace import DockManager

    previous, palette = qapp.style().name(), QPalette(qapp.palette())
    spec = replace(spec_for("violet_haze"), control_radius=9, scrollbar="expanding",
                   focus_width=1.0)
    win = QMainWindow()
    style = LaceStyle()
    if order == "style_first":
        qapp.setStyle(style)
    DockManager(win)
    get_dock_style_manager().apply_theme_dict(build_theme(spec))
    QApplication.processEvents()
    if order == "manager_first":
        qapp.setStyle(style)
        QApplication.processEvents()
    try:
        assert (style.control_radius, style.scrollbar, style.focus_width) == (9, "expanding", 1.0)
    finally:
        win.close()
        get_dock_style_manager().apply_theme_dict(build_theme(spec_for("dark")))
        qapp.setStyle(previous)
        qapp.setPalette(palette)
        QApplication.processEvents()


@pytest.mark.parametrize("theme, rounded", [("cyberpunk_neon", True), ("dark", False)])
def test_dock_content_is_rounded_only_when_inset(lace_app, theme, rounded):
    """A text edit set as a dock's content: inset by the content margin it is
    a box of its own and its viewport corner shows the backdrop; flush with
    the card (margin 0) it is left to the card."""
    from lace import DockManager, DockWidget
    from lace.dock_chrome import backdrop_color
    from lace.enums import DockWidgetArea
    from lace.style import _frame_cap

    win = QMainWindow()
    win.resize(320, 240)
    dm = DockManager(win)
    edit = QTextEdit()
    dw = DockWidget("Edit", win)
    dw.set_widget(edit)
    dm.add_dock_widget(DockWidgetArea.center, dw)
    get_dock_style_manager().apply_theme_dict(build_theme(spec_for(theme)))
    win.show()
    for _ in range(5):
        QApplication.processEvents()
    try:
        assert lace_app.control_radius > 0
        assert _frame_cap.cap_of(edit)._mode() == ("cap" if rounded else None)
        img = win.grab().toImage()
        corner = edit.mapTo(win, edit.contentsRect().topLeft())
        fill = img.pixelColor(corner.x() + 10, corner.y() + 10)
        got = img.pixelColor(corner)
        if rounded:
            assert got == backdrop_color(edit), (got.name(), fill.name())
        else:
            assert got == fill, (got.name(), fill.name())
    finally:
        win.close()
        get_dock_style_manager().apply_theme_dict(build_theme(spec_for("dark")))


def test_frame_cap_is_hidden_when_idle_and_masked_when_shown(lace_app):
    """A cap only exists on screen where it paints: hidden on an unframed
    scroll area, masked to corners and edges on a framed one, so updates in
    the middle of the viewport never repaint it. Framing the area later
    brings the cap up."""
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QFrame, QVBoxLayout, QWidget
    from lace.style import _frame_cap

    host = QWidget()
    lay = QVBoxLayout(host)
    framed, bare = QTextEdit(), QTextEdit()
    bare.setFrameShape(QFrame.Shape.NoFrame)
    lay.addWidget(framed)
    lay.addWidget(bare)
    host.resize(240, 300)
    host.show()
    QApplication.processEvents()
    try:
        cap, idle = _frame_cap.cap_of(framed), _frame_cap.cap_of(bare)
        assert cap.isVisible() and not idle.isVisible()
        mask = cap.mask()
        centre = framed.rect().center()
        assert not mask.contains(centre)
        assert mask.contains(QPoint(0, 0)) and mask.contains(QPoint(0, centre.y()))

        bare.setFrameShape(QFrame.Shape.StyledPanel)
        bare.update()
        for _ in range(3):
            QApplication.processEvents()
        assert idle.isVisible()
    finally:
        host.close()
