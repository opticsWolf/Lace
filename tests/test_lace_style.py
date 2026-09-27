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
                                    control_radius=0, contrast="high")
    bridge.refresh_dock_palette()
    assert (w.style().scrollbar, w.style().control_radius, w.style().contrast) == \
        ("expanding", 0, "high")


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
