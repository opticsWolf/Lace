# -*- coding: utf-8 -*-
"""Native frame theming (lace.native_frame) and the shared title-bar colours.

DWM is mocked: ``_has_dwm`` is forced on and ``_dwm_set`` records its calls,
so these run anywhere, offscreen included.
"""

import re

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QDialog, QMenu, QWidget

import lace.native_frame as nf
from lace.dock_style_manager import get_dock_style_manager
from lace.title_bar_colors import TitleBarColors, title_bar_colors
from tests.theme_sets import QUICK


@pytest.fixture
def dwm(qapp, monkeypatch):
    """Recorded DWM calls: a list of (hwnd, attribute, value)."""
    calls = []
    monkeypatch.setattr(nf, "_has_dwm", lambda: True)
    monkeypatch.setattr(nf, "_dwm_set", lambda h, a, v: calls.append((h, a, v)) or True)
    monkeypatch.setattr(nf, "_frame_changed", lambda h: calls.append((h, "changed", None)))
    nf.uninstall_native_frame_theme()      # one left over from a DockManager test
    yield calls
    nf.uninstall_native_frame_theme()


def _colors(**kw):
    base = dict(background=QColor(0x12, 0x34, 0x56), text=QColor(250, 250, 250),
                text_inactive=QColor(120, 120, 120), border=None, is_dark=True)
    base.update(kw)
    return TitleBarColors(**base)


def _attrs(calls, hwnd=None):
    return {a: v for h, a, v in calls if hwnd is None or h == hwnd}


def test_colorref_packs_bgr():
    assert nf.colorref(QColor(0x12, 0x34, 0x56)) == 0x563412


def test_apply_sets_the_four_attributes(dwm):
    w = QDialog()
    assert nf.apply_native_frame(w, _colors(), active=True)
    attrs = _attrs(dwm)
    assert attrs[nf.DWMWA_USE_IMMERSIVE_DARK_MODE] == 1
    assert attrs[nf.DWMWA_CAPTION_COLOR] == 0x563412
    assert attrs[nf.DWMWA_TEXT_COLOR] == nf.colorref(QColor(250, 250, 250))
    assert attrs[nf.DWMWA_BORDER_COLOR] == nf.DWMWA_COLOR_DEFAULT


def test_border_and_inactive_text(dwm):
    w = QDialog()
    nf.apply_native_frame(w, _colors(border=QColor(1, 2, 3), is_dark=False), active=False)
    attrs = _attrs(dwm)
    assert attrs[nf.DWMWA_BORDER_COLOR] == 0x030201
    assert attrs[nf.DWMWA_TEXT_COLOR] == nf.colorref(QColor(120, 120, 120))
    assert attrs[nf.DWMWA_USE_IMMERSIVE_DARK_MODE] == 0


def test_caption_alpha_is_composited(dwm):
    w = QDialog()
    see_through = QColor(255, 0, 0, 0)     # fully transparent: the backdrop shows
    nf.apply_native_frame(w, _colors(background=see_through), active=True)
    backdrop = w.palette().color(w.backgroundRole())
    assert _attrs(dwm)[nf.DWMWA_CAPTION_COLOR] == nf.colorref(backdrop)


def test_second_call_with_the_same_theme_is_cached(dwm):
    w = QDialog()
    assert nf.apply_native_frame(w, _colors(), active=True)
    n = len(dwm)
    assert not nf.apply_native_frame(w, _colors(), active=True)
    assert len(dwm) == n


def test_dark_flip_forces_a_frame_repaint(dwm):
    w = QDialog()
    nf.apply_native_frame(w, _colors(is_dark=True), active=True)
    assert not any(a == "changed" for _, a, _ in dwm)
    nf.apply_native_frame(w, _colors(is_dark=False), active=True)
    assert any(a == "changed" for _, a, _ in dwm)


def test_no_op_off_windows(dwm, monkeypatch):
    monkeypatch.setattr(nf, "_has_dwm", lambda: False)
    assert not nf.apply_native_frame(QDialog(), _colors())
    assert dwm == []


@pytest.mark.parametrize("make", [
    lambda p: QDialog(None, Qt.WindowType.FramelessWindowHint),
    lambda p: QMenu(),
    lambda p: QWidget(None, Qt.WindowType.ToolTip),
    lambda p: QWidget(None, Qt.WindowType.SplashScreen),
    lambda p: QWidget(p),                           # not a window
], ids=["frameless", "popup", "tooltip", "splash", "child"])
def test_windows_without_a_native_frame_are_skipped(dwm, make):
    parent = QWidget()
    w = make(parent)
    assert not nf.wants_native_frame(w)
    assert not nf.apply_native_frame(w, _colors())
    assert dwm == []


def test_opt_out_property(dwm):
    w = QDialog()
    w.setProperty(nf.OPT_OUT_PROPERTY, False)
    assert not nf.apply_native_frame(w, _colors())
    assert dwm == []


# -- NativeFrameTheme ---------------------------------------------------------

def test_dialog_shown_after_install_is_themed_once(dwm):
    nf.install_native_frame_theme()
    d = QDialog()
    d.show()
    hwnd = int(d.winId())
    ours = [c for c in dwm if c[0] == hwnd]
    assert len(ours) == 4
    assert _attrs(ours)[nf.DWMWA_CAPTION_COLOR] == nf.colorref(
        title_bar_colors().opaque_background(d.palette().color(d.backgroundRole())))
    d.close()


def test_install_is_idempotent(dwm):
    assert nf.install_native_frame_theme() is nf.install_native_frame_theme()


def test_theme_switch_reapplies_to_visible_windows_only(dwm):
    nf.install_native_frame_theme()
    shown, hidden = QDialog(), QDialog()
    shown.show()
    hidden.winId()
    dwm.clear()
    get_dock_style_manager().apply_theme("light")
    QApplication.processEvents()
    hwnds = {h for h, _, _ in dwm}
    assert int(shown.winId()) in hwnds
    assert int(hidden.winId()) not in hwnds
    assert _attrs(dwm, int(shown.winId()))[nf.DWMWA_USE_IMMERSIVE_DARK_MODE] == 0
    shown.close()


def test_popups_and_opted_out_windows_are_ignored_by_the_filter(dwm):
    nf.install_native_frame_theme()
    menu = QMenu()
    menu.addAction("x")
    opted = QDialog()
    opted.setProperty(nf.OPT_OUT_PROPERTY, False)
    menu.popup(menu.pos())
    opted.show()
    QApplication.processEvents()
    hwnds = {h for h, _, _ in dwm}
    assert int(menu.winId()) not in hwnds
    assert int(opted.winId()) not in hwnds
    menu.close()
    opted.close()


def test_dock_manager_installs_it_unless_told_not_to(dwm, make_desk):
    make_desk(native_frames=False)
    assert nf._installed is None
    make_desk()
    assert nf._installed is not None


# -- the custom bar reads the same colours --------------------------------------

@pytest.mark.parametrize("theme", QUICK)
def test_styler_colours_equal_title_bar_colors(qapp, theme):
    from qframelesswindow import StandardTitleBar
    from lace.frameless_titlebar import FramelessTitleBarStyler, _color_hex

    get_dock_style_manager().apply_theme(theme)
    host = QWidget()
    bar = StandardTitleBar(host)
    FramelessTitleBarStyler(bar, parent=host)
    colors = title_bar_colors()
    qss = bar.styleSheet()
    assert re.search(r"background:\s*" + re.escape(_color_hex(colors.background)) + ";", qss)
    assert re.search(r"QLabel#titleLabel\s*\{\s*color:\s*" + re.escape(_color_hex(colors.text)), qss)
