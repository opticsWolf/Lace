# -*- coding: utf-8 -*-
"""Control gallery: every LaceStyle override in every state, drawn directly.

Each cell calls the style's ``drawPrimitive`` / ``drawComplexControl`` with a
hand-built option and forced ``QStyle.State`` flags, so renders need no event
simulation and are deterministic. Families extend ``ROWS`` as they land.
The Theme Studio shows it live; ``tests/visual/gallery.py`` renders it to
files.
"""

from typing import Callable, List, Tuple

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QFont, QImage, QPainter, QPalette
from PySide6.QtWidgets import (
    QComboBox, QFrame, QLineEdit, QPushButton, QSpinBox, QToolButton, QStyle,
    QStyleOptionComboBox, QStyleOptionSpinBox, QStyleOption, QStyleOptionButton,
    QStyleOptionFocusRect, QStyleOptionFrame, QStyleOptionMenuItem, QStyleOptionSizeGrip,
    QStyleOptionSlider, QStyleOptionToolButton,
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
        width = 30 + (style.pixelMetric(QStyle.PixelMetric.PM_MenuButtonIndicator) if split else 0)
        opt = _base(QStyleOptionToolButton(), _centred(cell, width, 26), pal, flags, disabled)
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


def _slider(ticks=False):
    def draw(style, p, cell, pal, flags, disabled):
        from PySide6.QtWidgets import QSlider
        at = _centred(cell, cell.width() - 10, 26 if ticks else 20)
        p.translate(at.topLeft())
        opt = _base(QStyleOptionSlider(), QRect(0, 0, at.width(), at.height()), pal, flags, disabled)
        opt.orientation = Qt.Orientation.Horizontal
        opt.state |= S.State_Horizontal
        opt.minimum, opt.maximum, opt.pageStep, opt.singleStep = 0, 100, 25, 1
        opt.sliderPosition = opt.sliderValue = 40
        opt.subControls = (QStyle.SubControl.SC_SliderGroove | QStyle.SubControl.SC_SliderHandle
                           | (QStyle.SubControl.SC_SliderTickmarks if ticks else QStyle.SubControl.SC_None))
        if ticks:
            opt.tickPosition, opt.tickInterval = QSlider.TickPosition.TicksBelow, 25
        if flags & (S.State_MouseOver | S.State_Sunken):
            opt.activeSubControls = QStyle.SubControl.SC_SliderHandle
        style.drawComplexControl(QStyle.ComplexControl.CC_Slider, opt, p, _widget(QSlider))
    return draw


def _progress(busy=False):
    def draw(style, p, cell, pal, flags, disabled):
        from PySide6.QtWidgets import QStyleOptionProgressBar
        opt = _base(QStyleOptionProgressBar(), _centred(cell, cell.width() - 10, 8), pal, flags, disabled)
        opt.state |= S.State_Horizontal
        opt.minimum, opt.maximum, opt.progress = (0, 0, 0) if busy else (0, 100, 60)
        opt.textVisible = False
        style.drawControl(QStyle.ControlElement.CE_ProgressBarGroove, opt, p, None)
        style.drawControl(QStyle.ControlElement.CE_ProgressBarContents, opt, p, None)
    return draw


def _selected_on_hover(flags):
    """Menus and item views select on hover: the hover and pressed columns show it."""
    return flags | S.State_Selected if flags & S.State_MouseOver else flags


def _tab(style, p, cell, pal, flags, disabled):
    from PySide6.QtWidgets import QStyleOptionTab, QTabBar
    at = _centred(cell, cell.width() - 10, 26)
    # The "checked" column shows the selected tab.
    if flags & S.State_On:
        flags = (flags & ~S.State_On) | S.State_Selected
    opt = _base(QStyleOptionTab(), at, pal, flags, disabled)
    opt.shape, opt.text = QTabBar.Shape.RoundedNorth, "Tab"
    base = QStyleOptionTab(opt)
    style.drawPrimitive(PE.PE_FrameTabBarBase, base, p, None)
    style.drawControl(QStyle.ControlElement.CE_TabBarTab, opt, p, None)


def _header(style, p, cell, pal, flags, disabled):
    from PySide6.QtWidgets import QStyleOptionHeader
    opt = _base(QStyleOptionHeader(), _centred(cell, cell.width() - 10, 24), pal, flags, disabled)
    opt.text, opt.orientation = "Name", Qt.Orientation.Horizontal
    opt.sortIndicator = QStyleOptionHeader.SortIndicator.SortDown
    style.drawControl(QStyle.ControlElement.CE_Header, opt, p, None)


def _menu_item(style, p, cell, pal, flags, disabled):
    opt = _base(QStyleOptionMenuItem(), _centred(cell, cell.width() - 4, 24), pal,
                _selected_on_hover(flags), disabled)
    style.drawPrimitive(PE.PE_PanelMenu, QStyleOptionMenuItem(opt), p, None)
    opt.menuItemType = QStyleOptionMenuItem.MenuItemType.Normal
    opt.text, opt.maxIconWidth, opt.font = "Open", 0, p.font()
    if flags & S.State_On:
        opt.checkType, opt.checked = QStyleOptionMenuItem.CheckType.NonExclusive, True
    from PySide6.QtWidgets import QMenu
    style.drawControl(QStyle.ControlElement.CE_MenuItem, opt, p, _widget(QMenu))


def _menu_bar_item(style, p, cell, pal, flags, disabled):
    opt = _base(QStyleOptionMenuItem(), _centred(cell, 44, 24), pal, _selected_on_hover(flags), disabled)
    opt.menuItemType, opt.text = QStyleOptionMenuItem.MenuItemType.Normal, "File"
    style.drawControl(QStyle.ControlElement.CE_MenuBarItem, opt, p, None)


def _item_view(style, p, cell, pal, flags, disabled):
    from PySide6.QtWidgets import QStyleOptionViewItem
    opt = _base(QStyleOptionViewItem(), _centred(cell, cell.width() - 10, 22), pal, flags, disabled)
    if flags & S.State_On:
        opt.state |= S.State_Selected
    opt.text = "Row"
    opt.features = QStyleOptionViewItem.ViewItemFeature.HasDisplay
    opt.displayAlignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, p, None)


def _tooltip(style, p, cell, pal, flags, disabled):
    opt = _base(QStyleOption(), _centred(cell, cell.width() - 16, 22), pal, flags, disabled)
    style.drawPrimitive(PE.PE_PanelTipLabel, opt, p, None)
    p.setPen(pal.color(QPalette.ColorGroup.Active, QPalette.ColorRole.ToolTipText))
    p.drawText(opt.rect, Qt.AlignmentFlag.AlignCenter, "Tip")


def _tool_box(style, p, cell, pal, flags, disabled):
    from PySide6.QtWidgets import QStyleOptionToolBox
    opt = _base(QStyleOptionToolBox(), _centred(cell, cell.width() - 10, 24), pal, flags, disabled)
    opt.text = "Page"
    style.drawControl(QStyle.ControlElement.CE_ToolBoxTab, opt, p, None)


def _group_box(style, p, cell, pal, flags, disabled):
    from PySide6.QtWidgets import QStyleOptionGroupBox
    opt = _base(QStyleOptionGroupBox(), _centred(cell, cell.width() - 10, 34), pal, flags, disabled)
    opt.text, opt.subControls = "Group", QStyle.SubControl.SC_GroupBoxFrame | QStyle.SubControl.SC_GroupBoxLabel
    opt.textAlignment = Qt.AlignmentFlag.AlignLeft
    style.drawComplexControl(QStyle.ComplexControl.CC_GroupBox, opt, p, None)


def _splitter(style, p, cell, pal, flags, disabled):
    """A handle between side-by-side panes (a vertical grip)."""
    width = style.pixelMetric(QStyle.PixelMetric.PM_SplitterWidth)
    opt = _base(QStyleOption(), _centred(cell, width, cell.height() - 4), pal,
                flags | S.State_Horizontal, disabled)
    style.drawControl(QStyle.ControlElement.CE_Splitter, opt, p, None)


def _shaped_frame(shape, size):
    def draw(style, p, cell, pal, flags, disabled):
        opt = _base(QStyleOptionFrame(), _centred(cell, *size), pal, flags | S.State_Sunken, disabled)
        opt.frameShape, opt.lineWidth, opt.midLineWidth = shape, 1, 0
        style.drawControl(QStyle.ControlElement.CE_ShapedFrame, opt, p, _widget(QFrame))
    return draw


def _dial(style, p, cell, pal, flags, disabled):
    side = cell.height() - 2
    at = _centred(cell, side, side)
    opt = _base(QStyleOptionSlider(), at, pal, flags, disabled)
    opt.minimum, opt.maximum, opt.pageStep, opt.singleStep = 0, 100, 20, 1
    opt.sliderPosition = opt.sliderValue = 40
    opt.upsideDown = True       # QDial's default (not inverted)
    opt.subControls = (QStyle.SubControl.SC_DialGroove | QStyle.SubControl.SC_DialHandle
                       | QStyle.SubControl.SC_DialTickmarks)
    style.drawComplexControl(QStyle.ComplexControl.CC_Dial, opt, p, None)


def _size_grip(style, p, cell, pal, flags, disabled):
    opt = _base(QStyleOptionSizeGrip(), _centred(cell, 16, 16), pal, flags, disabled)
    opt.corner = Qt.Corner.BottomRightCorner
    style.drawControl(QStyle.ControlElement.CE_SizeGrip, opt, p, None)


def _toolbar_line(element):
    return _primitive(element, size=(10, 28),
                      extra=lambda o: setattr(o, "state", o.state | S.State_Horizontal))


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
    ("slider", _slider()),
    ("slider ticks", _slider(ticks=True)),
    ("progress", _progress()),
    ("progress busy", _progress(busy=True)),
    ("tab", _tab),
    ("group box", _group_box),
    ("header", _header),
    ("menu item", _menu_item),
    ("menu bar item", _menu_bar_item),
    ("item view", _item_view),
    ("tooltip", _tooltip),
    ("tool box", _tool_box),
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
    ("splitter", _splitter),
    ("dial", _dial),
    ("tab close", _primitive(PE.PE_IndicatorTabClose, size=(16, 16))),
    ("frame line", _shaped_frame(QFrame.Shape.HLine, (52, 8))),
    ("frame box", _shaped_frame(QFrame.Shape.Box, (52, 24))),
    ("toolbar handle", _toolbar_line(PE.PE_IndicatorToolBarHandle)),
    ("toolbar separator", _toolbar_line(PE.PE_IndicatorToolBarSeparator)),
    ("size grip", _size_grip),
]


def render(style: QStyle, palette: QPalette, title: str = "", scale: float = 1.0) -> QImage:
    """One gallery sheet: ``ROWS`` down, ``STATES`` across.

    ``scale`` zooms through the painter's transform, the way a
    ``QGraphicsView`` does, so glyphs show how they hold up when zoomed.
    """
    cw, ch = CELL
    head = 22
    w, h = LABEL_W + cw * len(STATES), head * (2 if title else 1) + ch * len(ROWS)
    img = QImage(round(w * scale), round(h * scale), QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(palette.color(QPalette.ColorGroup.Active, QPalette.ColorRole.Window))
    p = QPainter(img)
    p.scale(scale, scale)
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
