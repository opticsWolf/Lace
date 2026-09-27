# -*- coding: utf-8 -*-
"""Control gallery: every LaceStyle override in every state, drawn directly.

Each cell calls the style's ``drawPrimitive`` / ``drawComplexControl`` with a
hand-built option and forced ``QStyle.State`` flags, so renders need no event
simulation and are deterministic. Families extend ``ROWS`` as they land.

    <python> tests/visual/gallery.py [theme...] [--out DIR]   # LaceStyle | Fusion side by side
"""

import os
import sys
from pathlib import Path
from typing import Callable, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPalette
from PySide6.QtWidgets import (
    QApplication, QComboBox, QLineEdit, QPushButton, QSpinBox, QToolButton, QStyle,
    QStyleOptionComboBox, QStyleOptionSpinBox, QStyleFactory, QStyleOption, QStyleOptionButton,
    QStyleOptionFocusRect, QStyleOptionFrame, QStyleOptionMenuItem, QStyleOptionSlider,
    QStyleOptionToolButton,
)

S = QStyle.StateFlag
PE = QStyle.PrimitiveElement

#: Column states: (label, flags). Every cell is enabled unless it says disabled.
STATES: Tuple[Tuple[str, "QStyle.State"], ...] = (
    ("normal", S.State_None),
    ("hover", S.State_MouseOver),
    ("pressed", S.State_Sunken | S.State_MouseOver),
    ("focused", S.State_HasFocus),
    ("checked", S.State_On),
    ("disabled", S.State_None),
)

CELL = (76, 40)
LABEL_W = 120


def _base(opt: QStyleOption, rect: QRect, palette: QPalette, flags, disabled: bool):
    opt.rect = rect
    opt.palette = palette
    opt.state = flags | S.State_Active | (S.State_None if disabled else S.State_Enabled)
    if flags & S.State_HasFocus:
        opt.state |= S.State_KeyboardFocusChange
    return opt


def _centred(cell: QRect, w: int, h: int) -> QRect:
    r = QRect(0, 0, w, h)
    r.moveCenter(cell.center())
    return r


def _primitive(element, opt_cls=QStyleOption, size=(16, 16), extra=None):
    def draw(style, p, cell, pal, flags, disabled):
        opt = _base(opt_cls(), _centred(cell, *size), pal, flags, disabled)
        if extra:
            extra(opt)
        style.drawPrimitive(element, opt, p, None)
    return draw


def _branch(open_: bool):
    def extra(opt):
        opt.state |= S.State_Children | (S.State_Open if open_ else S.State_None)
    return _primitive(PE.PE_IndicatorBranch, size=(20, 20), extra=extra)


def _scrollbar(orientation, mode=None):
    def draw(style, p, cell, pal, flags, disabled):
        if mode is not None and hasattr(style, "set_tokens"):
            style = type(style)(scrollbar=mode)
        opt = QStyleOptionSlider()
        extent = style.pixelMetric(QStyle.PixelMetric.PM_ScrollBarExtent)
        horizontal = orientation == Qt.Orientation.Horizontal
        size = (cell.width() - 8, extent) if horizontal else (extent, cell.height() - 4)
        _base(opt, _centred(cell, *size), pal, flags, disabled)
        opt.orientation = orientation
        if horizontal:
            opt.state |= S.State_Horizontal
        opt.minimum, opt.maximum, opt.pageStep, opt.singleStep = 0, 100, 40, 1
        opt.sliderPosition = opt.sliderValue = 30
        opt.subControls = QStyle.SubControl.SC_All
        if flags & (S.State_MouseOver | S.State_Sunken):
            opt.activeSubControls = QStyle.SubControl.SC_ScrollBarSlider
        style.drawComplexControl(QStyle.ComplexControl.CC_ScrollBar, opt, p, None)
    return draw


_widgets = {}


def _widget(cls):
    """A stand-in widget of ``cls``: styles key some decisions off the widget type."""
    if cls not in _widgets:
        _widgets[cls] = cls()
    return _widgets[cls]


def _push(features=None, text="Button"):
    def draw(style, p, cell, pal, flags, disabled):
        opt = _base(QStyleOptionButton(), _centred(cell, cell.width() - 10, 26), pal, flags, disabled)
        opt.text = text
        opt.fontMetrics = p.fontMetrics()
        if not flags & S.State_Sunken and not flags & S.State_On:
            opt.state |= S.State_Raised
        if features is not None:
            opt.features = features
        style.drawControl(QStyle.ControlElement.CE_PushButton, opt, p, _widget(QPushButton))
    return draw


def _tool(auto_raise=False, split=False):
    def draw(style, p, cell, pal, flags, disabled):
        opt = _base(QStyleOptionToolButton(), _centred(cell, 44 if split else 30, 26), pal, flags, disabled)
        opt.text = "T"
        opt.fontMetrics = p.fontMetrics()
        opt.toolButtonStyle = Qt.ToolButtonStyle.ToolButtonTextOnly
        opt.subControls = QStyle.SubControl.SC_ToolButton
        if auto_raise:
            opt.state |= S.State_AutoRaise
        else:
            opt.state |= S.State_Raised
        if split:
            opt.subControls |= QStyle.SubControl.SC_ToolButtonMenu
            opt.features = QStyleOptionToolButton.ToolButtonFeature.MenuButtonPopup
        if flags & (S.State_Sunken | S.State_MouseOver):
            opt.activeSubControls = QStyle.SubControl.SC_ToolButton
        w = _widget(QToolButton)
        w.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup if split
                       else QToolButton.ToolButtonPopupMode.DelayedPopup)
        style.drawComplexControl(QStyle.ComplexControl.CC_ToolButton, opt, p, w)
    return draw


def _line_edit(style, p, cell, pal, flags, disabled):
    opt = _base(QStyleOptionFrame(), _centred(cell, cell.width() - 10, 24), pal, flags, disabled)
    opt.lineWidth = style.pixelMetric(QStyle.PixelMetric.PM_DefaultFrameWidth)
    style.drawPrimitive(PE.PE_PanelLineEdit, opt, p, _widget(QLineEdit))
    p.setPen(pal.color(QPalette.ColorGroup.Disabled if disabled else QPalette.ColorGroup.Active,
                       QPalette.ColorRole.Text))
    p.drawText(opt.rect.adjusted(6, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, "Text")


def _combo(editable=False):
    def draw(style, p, cell, pal, flags, disabled):
        opt = _base(QStyleOptionComboBox(), _centred(cell, cell.width() - 10, 24), pal, flags, disabled)
        opt.editable, opt.frame, opt.currentText = editable, True, "Item"
        opt.subControls = QStyle.SubControl.SC_All
        if flags & (S.State_MouseOver | S.State_Sunken):
            opt.activeSubControls = QStyle.SubControl.SC_ComboBoxArrow
        w = _widget(QComboBox)
        style.drawComplexControl(QStyle.ComplexControl.CC_ComboBox, opt, p, w)
        if editable:
            edit = style.subControlRect(QStyle.ComplexControl.CC_ComboBox, opt,
                                        QStyle.SubControl.SC_ComboBoxEditField, w)
            p.setPen(pal.color(QPalette.ColorGroup.Active, QPalette.ColorRole.Text))
            p.drawText(edit.adjusted(2, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, "Edit")
        else:
            style.drawControl(QStyle.ControlElement.CE_ComboBoxLabel, opt, p, w)
    return draw


def _spin(symbols=None):
    def draw(style, p, cell, pal, flags, disabled):
        from PySide6.QtWidgets import QAbstractSpinBox
        # Fusion's spin-box rects are widget-local: draw at the origin.
        at = _centred(cell, cell.width() - 10, 24)
        p.translate(at.topLeft())
        opt = _base(QStyleOptionSpinBox(), QRect(0, 0, at.width(), at.height()), pal, flags, disabled)
        opt.frame = True
        opt.subControls = QStyle.SubControl.SC_All
        opt.stepEnabled = (QAbstractSpinBox.StepEnabledFlag.StepUpEnabled
                           | QAbstractSpinBox.StepEnabledFlag.StepDownEnabled)
        if symbols is not None:
            opt.buttonSymbols = symbols
        if flags & (S.State_MouseOver | S.State_Sunken):
            opt.activeSubControls = QStyle.SubControl.SC_SpinBoxUp
        w = _widget(QSpinBox)
        style.drawComplexControl(QStyle.ComplexControl.CC_SpinBox, opt, p, w)
        edit = style.subControlRect(QStyle.ComplexControl.CC_SpinBox, opt,
                                    QStyle.SubControl.SC_SpinBoxEditField, w)
        p.setPen(pal.color(QPalette.ColorGroup.Active, QPalette.ColorRole.Text))
        p.drawText(edit.adjusted(2, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter, "42")
    return draw


def _menu_check(opt):
    opt.checkType = QStyleOptionMenuItem.CheckType.NonExclusive
    opt.checked = bool(opt.state & S.State_On)


#: (label, draw(style, painter, cell, palette, flags, disabled))
ROWS: List[Tuple[str, Callable]] = [
    ("push button", _push()),
    ("default button", _push(QStyleOptionButton.ButtonFeature.DefaultButton, "OK")),
    ("flat button", _push(QStyleOptionButton.ButtonFeature.Flat, "Flat")),
    ("tool button", _tool()),
    ("tool auto-raise", _tool(auto_raise=True)),
    ("tool split", _tool(split=True)),
    ("line edit", _line_edit),
    ("combo box", _combo()),
    ("combo editable", _combo(editable=True)),
    ("spin box", _spin()),
    ("check box", _primitive(PE.PE_IndicatorCheckBox, QStyleOptionButton)),
    ("partial check", _primitive(PE.PE_IndicatorCheckBox, QStyleOptionButton,
                                 extra=lambda o: setattr(o, "state", o.state | S.State_NoChange))),
    ("radio", _primitive(PE.PE_IndicatorRadioButton, QStyleOptionButton)),
    ("item check", _primitive(PE.PE_IndicatorItemViewItemCheck, QStyleOptionButton)),
    ("menu check", _primitive(PE.PE_IndicatorMenuCheckMark, QStyleOptionMenuItem, extra=_menu_check)),
    ("branch open", _branch(True)),
    ("branch shut", _branch(False)),
    ("arrow down", _primitive(PE.PE_IndicatorArrowDown, size=(12, 12))),
    ("arrow right", _primitive(PE.PE_IndicatorArrowRight, size=(12, 12))),
    ("spin up", _primitive(PE.PE_IndicatorSpinUp, size=(12, 10))),
    ("spin plus", _primitive(PE.PE_IndicatorSpinPlus, size=(12, 10))),
    ("frame", _primitive(PE.PE_Frame, QStyleOptionFrame, size=(52, 28))),
    ("line edit frame", _primitive(PE.PE_FrameLineEdit, QStyleOptionFrame, size=(52, 24))),
    ("focus rect", _primitive(PE.PE_FrameFocusRect, QStyleOptionFocusRect, size=(48, 22),
                              extra=lambda o: setattr(o, "state", o.state | S.State_KeyboardFocusChange))),
    ("scrollbar h", _scrollbar(Qt.Orientation.Horizontal)),
    ("scrollbar v", _scrollbar(Qt.Orientation.Vertical)),
    ("expanding h", _scrollbar(Qt.Orientation.Horizontal, "expanding")),
]


def render(style: QStyle, palette: QPalette, title: str = "") -> QImage:
    """One gallery sheet: ``ROWS`` down, ``STATES`` across."""
    cw, ch = CELL
    head = 22
    img = QImage(LABEL_W + cw * len(STATES), head * (2 if title else 1) + ch * len(ROWS),
                 QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(palette.color(QPalette.ColorGroup.Active, QPalette.ColorRole.Window))
    p = QPainter(img)
    font = QFont(p.font())
    font.setPixelSize(11)
    p.setFont(font)
    text = palette.color(QPalette.ColorGroup.Active, QPalette.ColorRole.WindowText)
    y0 = 0
    if title:
        p.setPen(text)
        p.drawText(QRect(6, 0, img.width(), head), Qt.AlignmentFlag.AlignVCenter, title)
        y0 = head
    for c, (label, _) in enumerate(STATES):
        p.setPen(text)
        p.drawText(QRect(LABEL_W + c * cw, y0, cw, head), Qt.AlignmentFlag.AlignCenter, label)
    y0 += head
    for r, (label, draw) in enumerate(ROWS):
        y = y0 + r * ch
        p.setPen(text)
        p.drawText(QRect(6, y, LABEL_W - 6, ch), Qt.AlignmentFlag.AlignVCenter, label)
        for c, (state, flags) in enumerate(STATES):
            cell = QRect(LABEL_W + c * cw, y, cw, ch)
            p.save()
            p.setClipRect(cell)
            draw(style, p, cell, palette, flags, state == "disabled")
            p.restore()
    p.end()
    return img


def side_by_side(theme_key: str) -> QImage:
    """LaceStyle and stock Fusion galleries for one theme, left to right."""
    from lace.dock_style_manager import get_dock_style_manager
    from lace.dock_theme import build_dock_palette, resolve_dock_colors
    from lace.lace_style import LaceStyle
    from tests.theme_sets import load

    get_dock_style_manager().apply_theme_dict(load(theme_key))
    palette = build_dock_palette(is_panel=False, colors=resolve_dock_colors())
    lace = render(LaceStyle(), palette, f"{theme_key} - LaceStyle")
    fusion = render(QStyleFactory.create("Fusion"), palette, f"{theme_key} - Fusion")
    out = QImage(lace.width() + fusion.width() + 12, max(lace.height(), fusion.height()),
                 QImage.Format.Format_ARGB32_Premultiplied)
    out.fill(QColor("#808080"))
    p = QPainter(out)
    p.drawImage(0, 0, lace)
    p.drawImage(lace.width() + 12, 0, fusion)
    p.end()
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    out_dir = Path("screenshots/gallery")
    if "--out" in args:
        i = args.index("--out")
        out_dir = Path(args[i + 1])
        del args[i:i + 2]
    themes = args or ["kilim_dark", "kilim_light_neo"]
    app = QApplication.instance() or QApplication([])
    os.makedirs(out_dir, exist_ok=True)
    for key in themes:
        path = out_dir / f"{key}.png"
        side_by_side(key).save(str(path))
        print(path)
