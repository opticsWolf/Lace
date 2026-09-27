# -*- coding: utf-8 -*-
"""LaceStyle (Phase 4a): sizes stay Fusion's, fall-through, scrollbar modes,
contrast of the non-text UI, and the bridge's ownership of the style."""

import gc

import pytest
from PySide6.QtCore import QRect, Qt, qInstallMessageHandler
from PySide6.QtGui import QImage, QPainter, QPalette
from PySide6.QtWidgets import (
    QAbstractScrollArea, QCalendarWidget, QCheckBox, QComboBox, QDial, QDoubleSpinBox, QGroupBox, QLabel,
    QLineEdit, QListWidget, QMdiArea, QProgressBar, QPushButton, QRadioButton,
    QScrollBar, QSlider, QSpinBox, QStyle, QStyleFactory, QStyleOptionButton,
    QStyleOptionSlider, QTabWidget, QTextEdit, QToolButton, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)

from lace import color_science as cs
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import build_dock_palette, resolve_dock_colors
from lace.lace_style import LaceStyle
from tests.theme_sets import load

S = QStyle.StateFlag

GALLERY = (QPushButton, QToolButton, QCheckBox, QRadioButton, QLineEdit, QComboBox,
           QSpinBox, QDoubleSpinBox, QSlider, QProgressBar, QTabWidget, QGroupBox,
           QTextEdit, QListWidget, QTreeWidget, QLabel, QDial, QCalendarWidget, QMdiArea)
#: Hints that legitimately follow PM_ScrollBarExtent: scroll areas count their
#: scrollbars, the combo box its popup's.
EXTENT_DEPENDENT = (QScrollBar, QComboBox, QAbstractScrollArea)


def _styled(cls, style):
    w = cls()
    if cls in (QCheckBox, QRadioButton, QPushButton, QToolButton):
        w.setText("Label")
    if cls is QComboBox:
        w.addItems(["Alpha", "Beta"])
    w.setStyle(style)
    for child in w.findChildren(QWidget):
        child.setStyle(style)
    return w


@pytest.fixture
def themed(qapp):
    get_dock_style_manager().apply_theme_dict(load("kilim_dark"))
    return build_dock_palette(is_panel=False, colors=resolve_dock_colors())


@pytest.fixture
def warnings():
    msgs = []
    prev = qInstallMessageHandler(lambda _t, _c, m: msgs.append(m))
    yield msgs
    qInstallMessageHandler(prev)


# ---------------------------------------------------------------------------
# No reflow
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("mode", ["thin", "expanding", "fusion"])
@pytest.mark.parametrize("cls", GALLERY, ids=lambda c: c.__name__)
def test_size_hints_match_fusion(qapp, cls, mode):
    lace, fusion = LaceStyle(scrollbar=mode), QStyleFactory.create("Fusion")
    a, b = _styled(cls, lace), _styled(cls, fusion)
    if mode != "fusion" and issubclass(cls, EXTENT_DEPENDENT):
        # Preferred size: off only by the extent change. Minimum: never larger
        # (a thin bar has no step buttons, so a scroll area's minimum shrinks).
        pm = QStyle.PixelMetric.PM_ScrollBarExtent
        slack = fusion.pixelMetric(pm) - lace.pixelMetric(pm)
        got, want = a.sizeHint(), b.sizeHint()
        assert 0 <= want.width() - got.width() <= slack
        assert 0 <= want.height() - got.height() <= slack
        got, want = a.minimumSizeHint(), b.minimumSizeHint()
        assert got.width() <= want.width() and got.height() <= want.height()
    else:
        assert a.sizeHint() == b.sizeHint()
        assert a.minimumSizeHint() == b.minimumSizeHint()


# ---------------------------------------------------------------------------
# Fall-through
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("cls", [QDial, QCalendarWidget, QMdiArea], ids=lambda c: c.__name__)
def test_unstyled_controls_fall_through_cleanly(qapp, themed, warnings, cls):
    w = _styled(cls, LaceStyle())
    w.setPalette(themed)
    w.resize(w.sizeHint().expandedTo(w.minimumSizeHint()))
    img = w.grab().toImage()
    assert not img.isNull()
    assert [m for m in warnings if "QFontDatabase" not in m] == []


# ---------------------------------------------------------------------------
# Scrollbar modes
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("mode, extent", [("thin", 8), ("expanding", 10)])
def test_scrollbar_extent_per_mode(qapp, mode, extent):
    assert LaceStyle(scrollbar=mode).pixelMetric(QStyle.PixelMetric.PM_ScrollBarExtent) == extent


def test_fusion_scrollbar_mode_passes_extent_through(qapp):
    fusion = QStyleFactory.create("Fusion")
    pm = QStyle.PixelMetric.PM_ScrollBarExtent
    assert LaceStyle(scrollbar="fusion").pixelMetric(pm) == fusion.pixelMetric(pm)


def _scrollbar_image(style, palette, orientation):
    bar = QScrollBar(orientation)
    bar.setRange(0, 100)
    bar.setValue(30)
    bar.setStyle(style)
    bar.setPalette(palette)
    bar.resize(160, 160)
    if orientation == Qt.Orientation.Horizontal:
        bar.setFixedHeight(bar.sizeHint().height())
    else:
        bar.setFixedWidth(bar.sizeHint().width())
    return bar.grab().toImage()


@pytest.mark.parametrize("orientation", [Qt.Orientation.Horizontal, Qt.Orientation.Vertical],
                         ids=["h", "v"])
def test_fusion_scrollbar_mode_is_pixel_identical(qapp, themed, orientation):
    lace = _scrollbar_image(LaceStyle(scrollbar="fusion"), themed, orientation)
    fusion = _scrollbar_image(QStyleFactory.create("Fusion"), themed, orientation)
    assert lace == fusion


def test_thin_scrollbar_has_no_step_buttons(qapp):
    style = LaceStyle()
    opt = QStyleOptionSlider()
    opt.rect = QRect(0, 0, 8, 200)
    opt.orientation = Qt.Orientation.Vertical
    opt.minimum, opt.maximum, opt.pageStep, opt.sliderPosition = 0, 100, 20, 50
    cc, sc = QStyle.ComplexControl.CC_ScrollBar, QStyle.SubControl
    assert style.subControlRect(cc, opt, sc.SC_ScrollBarAddLine).isEmpty()
    assert style.subControlRect(cc, opt, sc.SC_ScrollBarSubLine).isEmpty()
    handle = style.subControlRect(cc, opt, sc.SC_ScrollBarSlider)
    before = style.subControlRect(cc, opt, sc.SC_ScrollBarSubPage)
    after = style.subControlRect(cc, opt, sc.SC_ScrollBarAddPage)
    assert opt.rect.contains(handle) and handle.height() >= 20
    assert before.bottom() + 1 == handle.top() and handle.bottom() + 1 == after.top()
    assert after.bottom() == opt.rect.bottom()


def test_expanding_scrollbar_has_square_step_buttons(qapp):
    style = LaceStyle(scrollbar="expanding")
    opt = QStyleOptionSlider()
    opt.rect = QRect(0, 0, 10, 200)
    opt.orientation = Qt.Orientation.Vertical
    opt.minimum, opt.maximum, opt.pageStep, opt.sliderPosition = 0, 100, 20, 100
    cc, sc = QStyle.ComplexControl.CC_ScrollBar, QStyle.SubControl
    sub = style.subControlRect(cc, opt, sc.SC_ScrollBarSubLine)
    add = style.subControlRect(cc, opt, sc.SC_ScrollBarAddLine)
    groove = style.subControlRect(cc, opt, sc.SC_ScrollBarGroove)
    handle = style.subControlRect(cc, opt, sc.SC_ScrollBarSlider)
    assert sub == QRect(0, 0, 10, 10) and add == QRect(0, 190, 10, 10)
    assert groove == QRect(0, 10, 10, 180)
    assert groove.contains(handle) and handle.bottom() == groove.bottom()


@pytest.mark.parametrize("mode", ["thin", "expanding"])
def test_scrollbar_steps_work(qapp, mode):
    """Clicking the bottom end steps (expanding) or pages (thin); never stuck."""
    from PySide6.QtCore import QPoint
    from PySide6.QtTest import QTest
    bar = QScrollBar(Qt.Orientation.Vertical)
    bar.setStyle(LaceStyle(scrollbar=mode))
    bar.setRange(0, 100)
    bar.setPageStep(20)
    bar.resize(bar.sizeHint().width(), 200)
    QTest.mouseClick(bar, Qt.MouseButton.LeftButton, pos=QPoint(bar.width() // 2, 197))
    assert bar.value() == (1 if mode == "expanding" else 20)


def test_focus_width_token(qapp, themed):
    from PySide6.QtWidgets import QStyleOptionFocusRect

    def ring_rows(width):
        img = QImage(60, 30, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        opt = QStyleOptionFocusRect()
        opt.rect = QRect(8, 8, 44, 14)
        opt.palette = themed
        opt.state = S.State_Enabled | S.State_Active | S.State_KeyboardFocusChange
        p = QPainter(img)
        LaceStyle(focus_width=width).drawPrimitive(
            QStyle.PrimitiveElement.PE_FrameFocusRect, opt, p, None)
        p.end()
        return sum(1 for y in range(15) if img.pixelColor(30, y).alpha() > 128)

    assert ring_rows(0) == 0
    assert ring_rows(1) < ring_rows(2) < ring_rows(4)


def test_outline_strength_token(qapp, themed):
    from lace.style import _paint
    opt = _option(themed, S.State_Off)
    base = _paint.color(opt, QPalette.ColorRole.Base)
    text = _paint.color(opt, QPalette.ColorRole.Text)
    weak = LaceStyle(outline_strength=0.1, contrast="low")
    strong = LaceStyle(outline_strength=0.6, contrast="low")
    from lace.style import _primitives
    assert _ratio(_primitives._outline(strong, opt, base), base) > \
        _ratio(_primitives._outline(weak, opt, base), base)
    assert LaceStyle(outline_strength=5).outline_strength == 1.0
    assert _ratio(text, base) > 1   # sanity: the palette is themed


def test_partial_check_sits_between_off_and_on(qapp, themed):
    """B look: the partial fill is an accent wash, not the solid accent."""
    def centre_fill(state):
        img = QImage(20, 20, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        opt = _option(themed, state)
        opt.rect = QRect(2, 2, 16, 16)
        p = QPainter(img)
        LaceStyle().drawPrimitive(QStyle.PrimitiveElement.PE_IndicatorCheckBox, opt, p, None)
        p.end()
        return img.pixelColor(6, 6)   # inside the box, off the glyph

    off, part, on = (centre_fill(s) for s in (S.State_Off, S.State_NoChange, S.State_On))
    assert part != on and part != off
    assert _ratio(part, off) < _ratio(on, off)


def test_tokens_validate(qapp):
    style = LaceStyle()
    with pytest.raises(ValueError):
        style.set_tokens(scrollbar="wide")
    with pytest.raises(ValueError):
        style.set_tokens(contrast="max")
    style.set_tokens(control_radius=-3)
    assert style.control_radius == 0


# ---------------------------------------------------------------------------
# Contrast of the non-text UI
# ---------------------------------------------------------------------------
def _ratio(fg, bg) -> float:
    return cs.contrast_ratio([fg.red(), fg.green(), fg.blue(), fg.alpha()],
                             [bg.red(), bg.green(), bg.blue()])


def _option(palette, state):
    opt = QStyleOptionButton()
    opt.rect = QRect(0, 0, 16, 16)
    opt.palette = palette
    opt.state = S.State_Enabled | S.State_Active | state
    return opt


@pytest.mark.parametrize("contrast", ["low", "normal", "high"])
@pytest.mark.parametrize("hover", [False, True], ids=["rest", "hover"])
def test_indicator_outline_meets_ui_target(qapp, theme_key, contrast, hover):
    """Check box and radio share the outline rule: ``ui`` target vs the window."""
    from lace.style import _paint, _primitives
    get_dock_style_manager().apply_theme_dict(load(theme_key))
    palette = build_dock_palette(is_panel=False, colors=resolve_dock_colors())
    style = LaceStyle(contrast=contrast)
    opt = _option(palette, S.State_Off | (S.State_MouseOver if hover else S.State_None))
    base = _paint.state_fill(opt, _paint.color(opt, QPalette.ColorRole.Base))
    line = _primitives._outline(style, opt, base)
    window = _paint.color(opt, QPalette.ColorRole.Window)
    # ensure_contrast returns the best reachable colour when the ratio is out of reach.
    best = max(_ratio(c, window) for c in (line, _paint.QColor("white"), _paint.QColor("black")))
    assert _ratio(line, window) >= min(style.ui_ratio, best) - 0.01


def test_disabled_indicator_outline_stays_visible(qapp, theme_key):
    """Disabled indicators drop to the muted floor, not below it."""
    from lace.style import _paint, _primitives
    get_dock_style_manager().apply_theme_dict(load(theme_key))
    palette = build_dock_palette(is_panel=False, colors=resolve_dock_colors())
    opt = _option(palette, S.State_Off)
    opt.state &= ~S.State_Enabled
    base = _paint.color(opt, QPalette.ColorRole.Base)
    line = _primitives._outline(LaceStyle(), opt, base)
    assert _ratio(line, _paint.color(opt, QPalette.ColorRole.Window)) >= _paint.DISABLED_RATIO - 0.01


@pytest.mark.parametrize("radius", [0, 4, 20])
def test_check_box_corners_follow_control_radius_capped(qapp, themed, radius):
    """0 is square, small radii pass through, large ones stop at the cap."""
    from lace.style import _paint
    palette = themed
    img = QImage(16, 16, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    p = QPainter(img)
    LaceStyle(control_radius=radius).drawPrimitive(
        QStyle.PrimitiveElement.PE_IndicatorCheckBox, _option(palette, S.State_Off), p, None)
    p.end()
    corner = img.pixelColor(0, 0).alpha()
    if radius == 0:
        assert corner > 0
    else:
        assert corner < img.pixelColor(8, 0).alpha()
    # The cap keeps a large radius from turning the box into a circle.
    assert img.pixelColor(0, 8).alpha() > 0 and _paint.RADIUS_MAX < 0.5


def test_focus_ring_only_on_keyboard_focus(qapp, themed):
    style = LaceStyle()

    def drawn(extra):
        from PySide6.QtWidgets import QStyleOptionFocusRect
        img = QImage(60, 30, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        opt = QStyleOptionFocusRect()
        opt.rect = QRect(6, 6, 48, 18)
        opt.palette = themed
        opt.state = S.State_Enabled | S.State_Active | S.State_HasFocus | extra
        p = QPainter(img)
        style.drawPrimitive(QStyle.PrimitiveElement.PE_FrameFocusRect, opt, p, None)
        p.end()
        return any(img.pixelColor(x, 6).alpha() for x in range(60))

    assert not drawn(S.State_None)
    assert drawn(S.State_KeyboardFocusChange)


# ---------------------------------------------------------------------------
# Bridge
# ---------------------------------------------------------------------------
def test_bridge_installs_lace_style_by_default(qapp):
    from lace.dock_theme_bridge import DockThemeBridge
    w = QWidget()
    bridge = DockThemeBridge(target=w)
    assert isinstance(w.style(), LaceStyle)
    assert bridge._style is w.style()


def test_bridge_keeps_named_style_and_skips_empty(qapp):
    from lace.dock_theme_bridge import DockThemeBridge
    w = QWidget()
    DockThemeBridge(target=w, style_name="Fusion")
    assert not isinstance(w.style(), LaceStyle)
    assert w.style().name().lower() == "fusion"
    plain = QWidget()
    before = plain.style()
    DockThemeBridge(target=plain, style_name="")
    assert plain.style() is before


def test_deleting_bridge_leaves_style_alive(qapp):
    from lace.dock_theme_bridge import DockThemeBridge
    w = QWidget()
    lay = QVBoxLayout(w)
    box = QCheckBox("x")
    lay.addWidget(box)
    bridge = DockThemeBridge(target=w)
    style = w.style()
    bridge.deleteLater()
    del bridge
    qapp.processEvents()
    gc.collect()
    assert w.style() is style
    assert isinstance(w.style(), LaceStyle)
    w.resize(80, 40)
    assert not w.grab().isNull()   # would crash on a freed style


def test_bridge_pushes_theme_tokens(qapp):
    from lace.dock_theme import DockStyleCategory
    from lace.dock_theme_bridge import DockThemeBridge
    w = QWidget()
    bridge = DockThemeBridge(target=w)
    get_dock_style_manager().update(DockStyleCategory.CORE, scrollbar="expanding",
                                    control_radius=0, contrast="high", focus_width=3.0)
    bridge.refresh_dock_palette()
    st = w.style()
    assert (st.scrollbar, st.control_radius, st.contrast, st.focus_width) == \
        ("expanding", 0, "high", 3.0)


def test_theme_spec_carries_style_knobs(qapp):
    from lace.dock_theme import DockStyleCategory, ThemeSpec, build_theme
    from lace.theme_models import ThemeJson
    spec = ThemeSpec(base=[30, 30, 34, 255], accent=[0, 120, 215, 255], text=[230, 230, 230, 255],
                     contrast="high", scrollbar="expanding", control_radius=6)
    core = build_theme(spec)[DockStyleCategory.CORE]
    assert (core["contrast"], core["scrollbar"], core["control_radius"]) == ("high", "expanding", 6)
    js = ThemeJson(base="#1e1e22", accent="#0078d7", text="#e6e6e6", scrollbar="fusion")
    assert js.to_theme_spec().scrollbar == "fusion"
    with pytest.raises(Exception):
        ThemeJson(base="#1e1e22", accent="#0078d7", text="#e6e6e6", scrollbar="wide")


def test_tree_branch_draws_without_children(qapp):
    """A branch cell with no children paints nothing (no connector lines)."""
    style = LaceStyle()
    tree = QTreeWidget()
    QTreeWidgetItem(tree, ["leaf"])
    tree.setStyle(style)
    tree.resize(120, 60)
    assert not tree.grab().isNull()
