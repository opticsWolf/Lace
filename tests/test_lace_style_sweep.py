# -*- coding: utf-8 -*-
"""End-of-Phase-4 sweep: every family flat and legible under every theme of
the selected set (run with ``--themes regular`` for the plan's exit check).

Flat: inside its antialiased edge a surface is one colour -- no gradient.
Contrast: outlines, the focus outline, the selected-tab underline and the
check mark meet the Phase 2 targets (or the best any colour reaches, where a
theme puts the target out of reach); disabled text meets the disabled target.
"""

import pytest
from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPalette
from PySide6.QtWidgets import (
    QComboBox, QLineEdit, QMenu, QSpinBox, QStyle, QStyleOption, QStyleOptionButton,
    QStyleOptionComboBox, QStyleOptionFrame, QStyleOptionHeader, QStyleOptionMenuItem,
    QStyleOptionProgressBar, QStyleOptionSpinBox, QStyleOptionTab, QStyleOptionToolBox,
    QStyleOptionViewItem, QTabBar,
)

from lace import color_science as cs
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import build_dock_palette, resolve_dock_colors
from lace.lace_style import LaceStyle
from lace.theme_contrast import CONTRAST_TARGETS
from lace.style import _paint
from tests.theme_sets import load

S = QStyle.StateFlag
PE = QStyle.PrimitiveElement
CE = QStyle.ControlElement
CC = QStyle.ComplexControl
SC = QStyle.SubControl
Role = QPalette.ColorRole
G = QPalette.ColorGroup
W, H = 120, 26

_palettes = {}


def _palette(key):
    if key not in _palettes:
        get_dock_style_manager().apply_theme_dict(load(key))
        _palettes[key] = build_dock_palette(is_panel=False, colors=resolve_dock_colors())
    return _palettes[key]


def _rgb(c):
    return [c.red(), c.green(), c.blue()]


def _ratio(a, b):
    return cs.contrast_ratio(_rgb(a), _rgb(b))


def _state(extra=S.State_None):
    return S.State_Enabled | S.State_Active | extra


def _paint_into(draw, w=W, h=H):
    img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    p = QPainter(img)
    draw(p)
    p.end()
    return img


def _colours(img, x0, x1, y0, y1):
    return {img.pixelColor(x, y).rgba() for x in range(x0, x1) for y in range(y0, y1)}


def _meets(line, window, target):
    """``line`` reaches ``target`` against ``window``, or the best any colour can."""
    best = max(_ratio(c, window) for c in (line, QColor("white"), QColor("black")))
    return _ratio(line, window) >= min(target, best) - 0.01


# ---------------------------------------------------------------------------
# Flat: one surface per family, in the states that change its fill.
# Each case draws into (W, H) and names the interior to sample.
# ---------------------------------------------------------------------------
def _combo(style, pal, state):
    opt = QStyleOptionComboBox()
    opt.rect, opt.palette, opt.state = QRect(0, 0, W, H), pal, _state(state)
    opt.frame, opt.subControls = True, SC.SC_All
    img = _paint_into(lambda p: style.drawComplexControl(CC.CC_ComboBox, opt, p, QComboBox()))
    arrow = style.subControlRect(CC.CC_ComboBox, opt, SC.SC_ComboBoxArrow, QComboBox())
    return img, (4, arrow.left() - 4, 4, H - 4)


def _spin(style, pal, state):
    opt = QStyleOptionSpinBox()
    opt.rect, opt.palette, opt.state = QRect(0, 0, W, H), pal, _state(state)
    opt.frame, opt.subControls = True, SC.SC_All
    img = _paint_into(lambda p: style.drawComplexControl(CC.CC_SpinBox, opt, p, QSpinBox()))
    up = style.subControlRect(CC.CC_SpinBox, opt, SC.SC_SpinBoxUp, QSpinBox())
    return img, (4, up.left() - 4, 4, H - 4)


def _progress(part):
    def case(style, pal, state):
        opt = QStyleOptionProgressBar()
        opt.rect, opt.palette, opt.state = QRect(0, 0, W, 10), pal, _state(state | S.State_Horizontal)
        opt.minimum, opt.maximum, opt.progress = 0, 100, 100 if part == "fill" else 0

        def draw(p):
            style.drawControl(CE.CE_ProgressBarGroove, opt, p, None)
            style.drawControl(CE.CE_ProgressBarContents, opt, p, None)
        return _paint_into(draw, h=10), (8, W - 8, 2, 8)
    return case


def _header(style, pal, state):
    opt = QStyleOptionHeader()
    opt.rect, opt.palette, opt.state = QRect(0, 0, W, H), pal, _state(state)
    opt.orientation = Qt.Orientation.Horizontal
    img = _paint_into(lambda p: style.drawControl(CE.CE_HeaderSection, opt, p, None))
    return img, (2, W - 3, 1, H - 2)


def _tab(style, pal, state):
    opt = QStyleOptionTab()
    opt.rect, opt.palette = QRect(0, 0, W, H), pal
    opt.state, opt.shape = _state(state | S.State_Selected), QTabBar.Shape.RoundedNorth
    img = _paint_into(lambda p: style.drawControl(CE.CE_TabBarTabShape, opt, p, None))
    return img, (6, W - 6, 6, H - 4)


def _menu_item(style, pal, state):
    opt = QStyleOptionMenuItem()
    opt.rect, opt.palette, opt.state = QRect(0, 0, W, H), pal, _state(state | S.State_Selected)
    opt.menuItemType, opt.text = QStyleOptionMenuItem.MenuItemType.Normal, ""
    img = _paint_into(lambda p: style.drawControl(CE.CE_MenuItem, opt, p, QMenu()))
    return img, (10, W - 10, 4, H - 4)


def _item_view(style, pal, state):
    opt = QStyleOptionViewItem()
    opt.rect, opt.palette, opt.state = QRect(0, 0, W, H), pal, _state(state | S.State_Selected)
    img = _paint_into(lambda p: style.drawPrimitive(PE.PE_PanelItemViewItem, opt, p, None))
    return img, (0, W, 0, H)


def _tooltip(style, pal, state):
    opt = QStyleOption()
    opt.rect, opt.palette, opt.state = QRect(0, 0, W, H), pal, _state(state)
    img = _paint_into(lambda p: style.drawPrimitive(PE.PE_PanelTipLabel, opt, p, None))
    return img, (6, W - 6, 4, H - 4)


def _tool_box(style, pal, state):
    opt = QStyleOptionToolBox()
    opt.rect, opt.palette, opt.state = QRect(0, 0, W, H), pal, _state(state)
    img = _paint_into(lambda p: style.drawControl(CE.CE_ToolBoxTabShape, opt, p, None))
    return img, (6, W - 6, 4, H - 4)


def _check_box(style, pal, state):
    opt = QStyleOptionButton()
    opt.rect, opt.palette, opt.state = QRect(0, 0, 16, 16), pal, _state(state | S.State_Off)
    img = _paint_into(lambda p: style.drawPrimitive(PE.PE_IndicatorCheckBox, opt, p, None), 16, 16)
    return img, (4, 12, 4, 12)


FLAT = {
    "combo": _combo, "spin": _spin, "progress_track": _progress("track"),
    "progress_fill": _progress("fill"), "header": _header, "tab_selected": _tab,
    "menu_item": _menu_item, "item_view": _item_view, "tooltip": _tooltip,
    "tool_box": _tool_box, "check_box": _check_box,
}
STATES = {"normal": S.State_None, "hover": S.State_MouseOver, "pressed": S.State_Sunken | S.State_MouseOver}


@pytest.mark.parametrize("state", STATES, ids=list(STATES))
@pytest.mark.parametrize("family", FLAT, ids=list(FLAT))
def test_surface_is_flat(qapp, theme_key, family, state):
    img, (x0, x1, y0, y1) = FLAT[family](LaceStyle(), _palette(theme_key), STATES[state])
    assert len(_colours(img, x0, x1, y0, y1)) == 1


# ---------------------------------------------------------------------------
# Contrast
# ---------------------------------------------------------------------------
def _top_edge(draw_opt_draw):
    """The 1 px outline colour: the middle of the top row, fully covered."""
    img = _paint_into(draw_opt_draw)
    return img.pixelColor(W // 2, 0)


def _outline_cases(style, pal):
    def frame(opt_cls, pe, state=S.State_None, w=None):
        opt = opt_cls()
        opt.rect, opt.palette, opt.state = QRect(0, 0, W, H), pal, _state(state)
        if isinstance(opt, QStyleOptionFrame):
            opt.lineWidth = 1
        return _top_edge(lambda p: style.drawPrimitive(pe, opt, p, w))

    button = QStyleOptionButton()
    button.rect, button.palette, button.state = QRect(0, 0, W, H), pal, _state(S.State_Raised)
    combo = QStyleOptionComboBox()
    combo.rect, combo.palette, combo.state = QRect(0, 0, W, H), pal, _state()
    combo.frame, combo.subControls, combo.editable = True, SC.SC_All, True
    return {
        "button": (_top_edge(lambda p: style.drawPrimitive(PE.PE_PanelButtonCommand, button, p, None)),
                   style.border_ratio),
        "line_edit": (frame(QStyleOptionFrame, PE.PE_PanelLineEdit, w=QLineEdit()), style.border_ratio),
        "combo": (_top_edge(lambda p: style.drawComplexControl(CC.CC_ComboBox, combo, p, QComboBox())),
                  style.border_ratio),
        "frame": (frame(QStyleOptionFrame, PE.PE_Frame), style.border_ratio),
        "tooltip": (frame(QStyleOption, PE.PE_PanelTipLabel), style.border_ratio),
        "focused_line_edit": (frame(QStyleOptionFrame, PE.PE_PanelLineEdit, S.State_HasFocus, QLineEdit()),
                              style.ui_ratio),
    }


@pytest.mark.parametrize("contrast", ["low", "normal", "high"])
def test_outlines_meet_targets(qapp, theme_key, contrast):
    pal = _palette(theme_key)
    style = LaceStyle(contrast=contrast)
    window = pal.color(G.Active, Role.Window)
    failures = {name: round(_ratio(line, window), 2)
                for name, (line, target) in _outline_cases(style, pal).items()
                if not _meets(line, window, target)}
    assert not failures, failures


@pytest.mark.parametrize("contrast", ["low", "normal", "high"])
def test_selected_tab_underline_meets_ui(qapp, theme_key, contrast):
    pal = _palette(theme_key)
    style = LaceStyle(contrast=contrast)
    opt = QStyleOptionTab()
    opt.rect, opt.palette = QRect(0, 0, W, H), pal
    opt.state, opt.shape = _state(S.State_Selected), QTabBar.Shape.RoundedNorth
    img = _paint_into(lambda p: style.drawControl(CE.CE_TabBarTabShape, opt, p, None))
    assert _meets(img.pixelColor(W // 2, H - 1), pal.color(G.Active, Role.Window), style.ui_ratio)


def test_check_mark_reads_on_accent(qapp, theme_key):
    pal = _palette(theme_key)
    style = LaceStyle()
    opt = QStyleOptionButton()
    opt.rect, opt.palette, opt.state = QRect(0, 0, 16, 16), pal, _state(S.State_On)
    img = _paint_into(lambda p: style.drawPrimitive(PE.PE_IndicatorCheckBox, opt, p, None), 16, 16)
    fill = img.pixelColor(3, 3)
    best = max(_ratio(img.pixelColor(x, y), fill) for x in range(3, 13) for y in range(3, 13))
    assert best >= 3.0 - 0.05


@pytest.mark.parametrize("text, surface", [(Role.ButtonText, Role.Button), (Role.Text, Role.Base),
                                           (Role.WindowText, Role.Window)],
                         ids=["button", "field", "window"])
def test_disabled_text_meets_disabled_target(qapp, theme_key, text, surface):
    pal = _palette(theme_key)
    ratio = _ratio(pal.color(G.Disabled, text), pal.color(G.Disabled, surface))
    assert ratio >= CONTRAST_TARGETS["disabled"]["normal"] - 0.05, round(ratio, 2)


def test_disabled_outline_keeps_the_floor(qapp, theme_key):
    """Disabled keeps its own target up to the floor, never stronger than enabled:
    a field (border target 1.3) stays at 1.3, not 1.5."""
    pal = _palette(theme_key)
    style = LaceStyle()
    opt = QStyleOptionFrame()
    opt.rect, opt.palette, opt.state, opt.lineWidth = QRect(0, 0, W, H), pal, S.State_Active, 1
    line = _top_edge(lambda p: style.drawPrimitive(PE.PE_PanelLineEdit, opt, p, QLineEdit()))
    target = min(style.border_ratio, _paint.DISABLED_RATIO)
    assert _meets(line, pal.color(G.Disabled, Role.Window), target)
