# -*- coding: utf-8 -*-
"""LaceStyle 4b-1, buttons: flat faces, readable default button, focus on the face."""

import pytest
from PySide6.QtCore import QRect
from PySide6.QtGui import QImage, QPainter, QPalette
from PySide6.QtWidgets import QPushButton, QStyle, QStyleOptionButton

from lace import color_science as cs
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import build_dock_palette, resolve_dock_colors
from lace.lace_style import LaceStyle
from lace.style import _buttons
from tests.theme_sets import load

S = QStyle.StateFlag
F = QStyleOptionButton.ButtonFeature
W, H = 90, 28


def _palette(theme_key):
    get_dock_style_manager().apply_theme_dict(load(theme_key))
    return build_dock_palette(is_panel=False, colors=resolve_dock_colors())


def _option(palette, state=S.State_None, features=F.None_, text=""):
    opt = QStyleOptionButton()
    opt.rect = QRect(0, 0, W, H)
    opt.palette = palette
    opt.state = S.State_Enabled | S.State_Active | state
    opt.features = features
    opt.text = text
    return opt


def _render(style, opt, element=QStyle.PrimitiveElement.PE_PanelButtonCommand):
    img = QImage(W, H, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(0)
    p = QPainter(img)
    if isinstance(element, QStyle.ControlElement):
        style.drawControl(element, opt, p, QPushButton())
    else:
        style.drawPrimitive(element, opt, p, QPushButton())
    p.end()
    return img


def _rgb(c):
    return [c.red(), c.green(), c.blue()]


CASES = {
    "normal": (S.State_None, F.None_),
    "hover": (S.State_MouseOver, F.None_),
    "pressed": (S.State_Sunken | S.State_MouseOver, F.None_),
    "checked": (S.State_On, F.None_),
    "default": (S.State_None, F.DefaultButton),
}


@pytest.mark.parametrize("case", CASES)
def test_button_face_is_flat(qapp, theme_key, case):
    """Inside its antialiased edge, a face is a single colour: no gradient."""
    state, features = CASES[case]
    img = _render(LaceStyle(), _option(_palette(theme_key), state, features))
    inner = {img.pixelColor(x, y).rgba() for x in range(4, W - 4) for y in range(4, H - 4)}
    assert len(inner) == 1


@pytest.mark.parametrize("state", [S.State_None, S.State_MouseOver, S.State_Sunken],
                         ids=["normal", "hover", "pressed"])
def test_default_button_text_reads_on_accent(qapp, theme_key, state):
    style = LaceStyle()
    pal = _palette(theme_key)
    opt = _option(pal, state, F.DefaultButton, "OK")
    fill, _ = _buttons.face_colors(style, opt)
    face = _rgb(fill)
    # The label drawn by the style, sampled at the darkest/lightest pixel of the text.
    img = _render(style, opt, QStyle.ControlElement.CE_PushButton)
    best = max(cs.contrast_ratio(_rgb(img.pixelColor(x, y)), face)
               for x in range(W // 2 - 10, W // 2 + 10) for y in range(8, H - 8))
    # on_color targets 3:1 for glyphs; readable against the accent either way.
    assert best >= 3.0 - 0.05


def test_flat_and_auto_raise_show_no_face_at_rest(qapp):
    pal = _palette("kilim_dark")
    style = LaceStyle()
    for opt in (_option(pal, features=F.Flat), _option(pal, S.State_AutoRaise)):
        img = _render(style, opt)
        assert all(img.pixelColor(x, H // 2).alpha() == 0 for x in range(W))
        opt.state |= S.State_MouseOver
        assert _render(style, opt).pixelColor(W // 2, H // 2).alpha() == 255


def test_keyboard_focus_rings_the_face(qapp):
    pal = _palette("kilim_dark")
    style = LaceStyle()
    accent = _rgb(pal.color(QPalette.ColorGroup.Active, QPalette.ColorRole.Accent))
    plain = _render(style, _option(pal, S.State_HasFocus))
    ringed = _render(style, _option(pal, S.State_HasFocus | S.State_KeyboardFocusChange))
    edge = (W // 2, 1)
    assert _rgb(ringed.pixelColor(*edge)) != _rgb(plain.pixelColor(*edge))
    assert cs.contrast_ratio(_rgb(ringed.pixelColor(*edge)), accent) < 1.3
