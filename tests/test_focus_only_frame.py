# -*- coding: utf-8 -*-
"""TAB.border_unfocused_color — the frame as the only focus indicator.

The active tab's outline while its area is unfocused. Unset, that state is the
active colour dimmed into the tab's background; transparent drops the outline
altogether. Under CORE.border_below_title that one token governs the whole
frame, because the frame is the tab's outline continued: no outline, no sides,
and no rule to close them. midnight_haze is built on it.

Pixels for the claims about what is drawn, resolvers for the precedence — a
token that reaches the resolver but leaves one of the three lines behind is
exactly the failure this is guarding against.
"""

import pytest
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QLabel, QMainWindow

from lace.dock_chrome import (resolve_below_title_frame_color,
                              resolve_tab_outline_color,
                              resolve_title_bar_bottom_rule)
from lace.dock_custom_theme import THEME_SPECS
from lace.dock_manager import DockManager
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import DockStyleCategory, ThemeSpec, build_theme
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea


@pytest.fixture
def pair(qapp):
    """Two areas of two tabs each, so both focus states are on screen."""
    win = QMainWindow()
    win.resize(800, 600)
    dock_manager = DockManager(win)

    def mk(name):
        dock_widget = DockWidget(name)
        dock_widget.set_widget(QLabel(name))
        return dock_widget

    top = dock_manager.add_dock_widget(DockWidgetArea.center, mk("Alpha"))
    dock_manager.add_dock_widget(DockWidgetArea.center, mk("Beta"), top)
    bottom = dock_manager.add_dock_widget(DockWidgetArea.bottom, mk("Gamma"))
    dock_manager.add_dock_widget(DockWidgetArea.center, mk("Delta"), bottom)
    win.show()
    qapp.processEvents()

    yield dock_manager, top, bottom

    win.close()
    get_dock_style_manager().apply_theme("default")


def _spec(**overrides):
    base = dict(
        base=[24, 26, 35, 255],
        accent=[125, 124, 252, 255],
        text=[229, 232, 236, 255],
        border=[42, 46, 60, 255],
        focus_border_color=[125, 124, 252, 255],
        border_width=2.0,
        border_below_title=True,
        corner_radius=10,
        title_border_bottom=2.0,
        tab_border_width=2.0,
        tab_border_color=[0, 0, 0, 0],
        tab_border_active_color=[125, 124, 252, 255],
        indicator_position="none",
        tab_dimming=True,
    )
    base.update(overrides)
    return ThemeSpec(**base)


def _render(dock_area, qapp):
    qapp.processEvents()
    qapp.processEvents()
    image = QImage(dock_area.size(), QImage.Format_ARGB32)
    image.fill(0)
    dock_area.render(image)
    return image


def _lines(dock_area, qapp):
    """The frame's three lines, each with a reference pixel beside it.

    ``{edge: (on_the_line, just_off_it)}``. The pair is what makes "no line"
    testable: equal means the line is not there at all, rather than merely not
    the accent — which a dimmed outline would also satisfy.
    """
    image = _render(dock_area, qapp)
    inset = int(dock_area.chrome_border_inset() or 0)
    top = int(dock_area.chrome_border_top() or 0)
    active = next(dock_area.dock_widget(i).tab_widget()
                  for i in range(dock_area.dock_widgets_count())
                  if dock_area.dock_widget(i).tab_widget().is_active_tab())
    tab_x = active.mapTo(dock_area, active.rect().topLeft()).x() + 1
    mid = dock_area.height() // 2
    return {
        "side": (image.pixelColor(inset, mid),
                 image.pixelColor(inset + 20, mid)),
        "rule": (image.pixelColor(dock_area.width() - 40, top - 1),
                 image.pixelColor(dock_area.width() - 40, top - 10)),
        # The reference sits high in the tab, clear of the label: at the
        # outline's own height it would land on the glyphs.
        "tab": (image.pixelColor(tab_x, top - 16),
                image.pixelColor(tab_x + 8, top - 28)),
    }


# ── The token ─────────────────────────────────────────────────────────────
def test_unset_keeps_the_dimming(pair, qapp):
    """The default is unchanged: the outline fades, it does not vanish."""
    dock_manager, top, bottom = pair
    manager = get_dock_style_manager()
    manager.apply_theme_dict(build_theme(_spec()))
    dock_manager.set_active_dock_area(bottom)
    qapp.processEvents()

    unfocused = resolve_tab_outline_color(manager, active=True, focused=False)
    focused = resolve_tab_outline_color(manager, active=True, focused=True)
    assert unfocused is not None, "the outline vanished without being asked to"
    assert unfocused.getRgb() != focused.getRgb(), "it did not dim either"


def test_transparent_drops_the_outline_when_unfocused(pair, qapp):
    dock_manager, top, bottom = pair
    manager = get_dock_style_manager()
    manager.apply_theme_dict(build_theme(
        _spec(tab_border_unfocused_color=[0, 0, 0, 0])))
    qapp.processEvents()

    assert resolve_tab_outline_color(manager, active=True, focused=False) is None
    assert resolve_tab_outline_color(manager, active=True, focused=True) is not None


def test_an_opaque_value_replaces_the_dimming(pair, qapp):
    """Not only a switch: the state can be given a colour of its own."""
    dock_manager, top, bottom = pair
    manager = get_dock_style_manager()
    manager.apply_theme_dict(build_theme(
        _spec(tab_border_unfocused_color=[200, 30, 30, 255])))
    qapp.processEvents()

    unfocused = resolve_tab_outline_color(manager, active=True, focused=False)
    assert unfocused.getRgb() == (200, 30, 30, 255)


# ── What it does to the frame ─────────────────────────────────────────────
def test_the_whole_frame_goes_with_it(pair, qapp):
    """Sides, rule and tab outline: all three, or none."""
    dock_manager, top, bottom = pair
    manager = get_dock_style_manager()
    manager.apply_theme_dict(build_theme(
        _spec(tab_border_unfocused_color=[0, 0, 0, 0])))

    frame = resolve_below_title_frame_color(manager, False)
    assert frame is not None and frame.alpha() == 0, \
        "the sides fell back to border_color instead of going away"
    assert resolve_title_bar_bottom_rule(manager, False) == (0.0, None), \
        "the rule survived the frame it was closing"

    frame = resolve_below_title_frame_color(manager, True)
    assert frame is not None and frame.alpha() > 0


def test_unfocused_area_draws_no_lines(pair, qapp):
    dock_manager, top, bottom = pair
    manager = get_dock_style_manager()
    manager.apply_theme_dict(build_theme(
        _spec(tab_border_unfocused_color=[0, 0, 0, 0])))
    dock_manager.set_active_dock_area(top)
    qapp.processEvents()

    accent = (125, 124, 252, 255)
    for edge, (on_line, _off) in _lines(top, qapp).items():
        assert on_line.getRgb() == accent, f"the focused area lost its {edge}"
    for edge, (on_line, off_line) in _lines(bottom, qapp).items():
        assert on_line.getRgb() == off_line.getRgb(), \
            f"the unfocused area still draws a {edge}"


def test_focus_moves_the_frame_with_it(pair, qapp):
    """Not a one-off at startup — it follows the active area."""
    dock_manager, top, bottom = pair
    manager = get_dock_style_manager()
    manager.apply_theme_dict(build_theme(
        _spec(tab_border_unfocused_color=[0, 0, 0, 0])))
    accent = (125, 124, 252, 255)

    dock_manager.set_active_dock_area(top)
    qapp.processEvents()
    assert _lines(top, qapp)["side"][0].getRgb() == accent

    dock_manager.set_active_dock_area(bottom)
    qapp.processEvents()
    gone, beside = _lines(top, qapp)["side"]
    assert gone.getRgb() == beside.getRgb(), "the frame stayed behind"
    assert _lines(bottom, qapp)["side"][0].getRgb() == accent, "it did not arrive"


def test_a_theme_without_tab_outlines_is_untouched(pair, qapp):
    """The below-title override only speaks for themes that outline tabs."""
    dock_manager, top, bottom = pair
    manager = get_dock_style_manager()
    manager.apply_theme_dict(build_theme(_spec(tab_border_width=0.0)))
    qapp.processEvents()

    assert resolve_below_title_frame_color(manager, False) is None
    assert resolve_below_title_frame_color(manager, True) is None


# ── The preset ────────────────────────────────────────────────────────────
def test_midnight_haze_is_built_on_it():
    spec = THEME_SPECS["midnight_haze"]
    assert spec.tab_border_unfocused_color == [0, 0, 0, 0]
    assert spec.tab_border_color == [0, 0, 0, 0], "inactive tabs are outlined"
    assert spec.border_below_title is True
    assert spec.border_width and spec.title_border_bottom, \
        "there would be no frame for the token to take away"


def test_midnight_haze_keeps_violet_hazes_geometry():
    """The palette is the mix; the shape is deliberately not."""
    haze = THEME_SPECS["violet_haze"]
    mid = THEME_SPECS["midnight_haze"]
    for field in ("corner_radius", "border_width", "border_below_title",
                  "title_height", "tab_radius", "tab_margin", "content_margin",
                  "title_border_bottom", "tab_border_width",
                  "indicator_position"):
        assert getattr(mid, field) == getattr(haze, field), field


def test_midnight_haze_mixes_the_two_palettes():
    mid = THEME_SPECS["midnight_haze"]
    for field in ("base", "accent", "text"):
        low = THEME_SPECS["midnight"]
        high = THEME_SPECS["violet_haze"]
        for i, channel in enumerate(getattr(mid, field)[:3]):
            ends = sorted((getattr(low, field)[i], getattr(high, field)[i]))
            assert ends[0] <= channel <= ends[1], \
                f"{field}[{i}]={channel} is outside {ends} — not a mix of the two"
