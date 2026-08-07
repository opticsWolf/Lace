# -*- coding: utf-8 -*-
"""Theme engine tests — ARCHITECTURE.md §3.1 / §3.2 (dock_theme.py).

Covers the declarative ThemeSpec -> build_theme pipeline, the HSL color math
(_adjust_color / _contrasting_hover), the canonical color conversions
(to_qcolor / qcolor_to_list / deep_*), the resolved-color snapshot, and the
QPalette construction used by DockThemeBridge.
"""

from PySide6.QtGui import QColor, QPalette

from lace.dock_theme import (
    DockStyleCategory,
    ThemeSpec,
    build_theme,
    build_tooltip_palette,
    _adjust_color,
    _contrasting_hover,
    to_qcolor,
    qcolor_to_list,
    is_color_list,
    deep_to_qcolor,
    deep_to_serializable,
    resolve_dock_colors,
    build_dock_palette,
    _get_contrasting_text_color,
)

REQUIRED_CORE = {
    "canvas_bg", "border_color", "accent_color", "focus_border_color",
    "text_color", "disabled_text_color", "success_color", "warning_color",
    "error_color", "info_color", "tooltip_bg", "tooltip_text",
}
SEED = ThemeSpec(base=[20, 23, 30, 255], accent=[45, 85, 170, 255],
                 text=[200, 205, 215, 255])


# ---------------------------------------------------------------------------
# ThemeSpec / build_theme
# ---------------------------------------------------------------------------
def test_build_theme_covers_all_categories():
    theme = build_theme(SEED)
    assert set(theme) == set(DockStyleCategory)
    assert REQUIRED_CORE <= set(theme[DockStyleCategory.CORE])


def test_build_theme_values_are_rgba_lists():
    theme = build_theme(SEED)
    for category, tokens in theme.items():
        for key, value in tokens.items():
            if key.endswith("_color") or "bg" in key or key.startswith("color_"):
                assert is_color_list(value), f"{category.name}.{key} = {value!r}"


def test_theme_spec_accepts_qcolor_and_list_equivalently(qapp):
    spec_lists = ThemeSpec(*([20, 23, 30, 255], [45, 85, 170, 255], [200, 205, 215, 255]),
                           title_mode="darker", hover_mode="lighter")
    spec_qcolor = ThemeSpec(QColor(20, 23, 30), QColor(45, 85, 170), QColor(200, 205, 215),
                            title_mode="darker", hover_mode="lighter")
    assert build_theme(spec_lists) == build_theme(spec_qcolor)


def test_build_theme_honours_geometry_overrides():
    theme = build_theme(ThemeSpec(
        base=[10, 10, 10, 255], accent=[0, 120, 212, 255], text=[230, 230, 230, 255],
        corner_radius=9, border_width=2.0, title_height=34, tab_radius=7,
    ))
    assert theme[DockStyleCategory.CORE]["corner_radius"] == 9
    assert theme[DockStyleCategory.PANEL]["corner_radius"] == 9
    assert theme[DockStyleCategory.PANEL]["border_width"] == 2.0
    assert theme[DockStyleCategory.TITLE_BAR]["height"] == 34
    assert theme[DockStyleCategory.TAB]["corner_radius"] == 7


def test_build_theme_light_dark_direction_flips():
    dark = build_theme(ThemeSpec(base=[10, 10, 10, 255], accent=[0, 120, 212, 255],
                                 text=[240, 240, 240, 255]))
    light = build_theme(ThemeSpec(base=[240, 240, 240, 255], accent=[0, 120, 212, 255],
                                  text=[20, 20, 20, 255], is_light=True))
    dark_panel = dark[DockStyleCategory.PANEL]["bg_normal"]
    light_panel = light[DockStyleCategory.PANEL]["bg_normal"]
    # Dark theme: panel lightens away from base; light theme: panel darkens away.
    assert dark_panel[0] > 10
    assert light_panel[0] < 240


# ---------------------------------------------------------------------------
# Color math
# ---------------------------------------------------------------------------
def test_adjust_color_clamps_lightness():
    out = _adjust_color([255, 0, 0, 255], l_off=5.0)
    assert out[0] <= 255 and out[3] == 255
    out2 = _adjust_color([0, 0, 0, 255], l_off=-5.0)
    assert out2[0] >= 0 and out2[3] == 255


def test_adjust_color_keeps_alpha_when_present():
    assert len(_adjust_color([100, 100, 100, 200])) == 4
    assert len(_adjust_color([100, 100, 100])) == 3  # no alpha in -> no alpha out


def test_contrasting_hover_goes_opposite_direction():
    dark_hover = _contrasting_hover([20, 20, 20, 255])
    light_hover = _contrasting_hover([240, 240, 240, 255])
    assert sum(dark_hover[:3]) > 60          # dark surface -> lighter hover
    assert sum(light_hover[:3]) < 720 - 60   # light surface -> darker hover


# ---------------------------------------------------------------------------
# Canonical conversions
# ---------------------------------------------------------------------------
def test_to_qcolor_accepts_all_forms(qapp):
    assert to_qcolor("#ff8800").name() == "#ff8800"
    assert to_qcolor("red").red() == 255
    assert to_qcolor([10, 20, 30]).blue() == 30
    assert to_qcolor([10, 20, 30, 128]).alpha() == 128
    c = QColor(1, 2, 3)
    assert to_qcolor(c) is not c and to_qcolor(c) == c  # defensive copy


def test_qcolor_list_round_trip():
    assert qcolor_to_list(to_qcolor([10, 20, 30, 255])) == [10, 20, 30, 255]
    assert qcolor_to_list(to_qcolor("#00ff7f")) == [0, 255, 127, 255]


def test_is_color_list_guard():
    assert is_color_list([1, 2, 3])
    assert is_color_list([1, 2, 3, 4])
    assert not is_color_list([1, 2])          # too short
    assert not is_color_list([1, 2, 3, 4, 5]) # too long
    assert not is_color_list("#ff0000")
    assert not is_color_list([1, 2, "x"])
    assert not is_color_list({"r": 1})


def test_deep_conversion_round_trips_nested_structures(qapp):
    payload = {"core": {"canvas_bg": [1, 2, 3, 255], "accent": "#00ff7f"},
               "tabs": [[10, 20, 30], (40, 50, 60)]}
    as_qcolor = deep_to_qcolor(payload)
    assert isinstance(as_qcolor["core"]["canvas_bg"], QColor)
    assert isinstance(as_qcolor["core"]["accent"], QColor)
    assert isinstance(as_qcolor["tabs"][0], QColor)
    assert deep_to_serializable(as_qcolor) == {
        "core": {"canvas_bg": [1, 2, 3, 255], "accent": [0, 255, 127, 255]},
        "tabs": [[10, 20, 30, 255], [40, 50, 60, 255]],
    }


# ---------------------------------------------------------------------------
# Resolved colors + palette
# ---------------------------------------------------------------------------
def test_resolve_dock_colors_cache_refreshes_on_generation_change():
    from lace.dock_style_manager import get_dock_style_manager

    sm = get_dock_style_manager()
    c1 = resolve_dock_colors()
    assert resolve_dock_colors() is c1          # same generation -> cached
    sm.update(DockStyleCategory.CORE, text_color=[10, 20, 30])
    c2 = resolve_dock_colors()
    assert c2 is not c1                          # generation bumped -> fresh
    assert c2.text_color.red() == 10


def test_build_dock_palette_roles_match_resolved_colors(qapp):
    colors = resolve_dock_colors()
    pal = build_dock_palette(colors=colors)
    assert pal.window().color().rgb() == colors.canvas_bg.rgb()
    assert pal.highlight().color().rgb() == colors.accent_color.rgb()
    assert pal.base().color().rgb() == colors.input_bg.rgb()
    assert pal.text().color().rgb() == colors.text_color.rgb()
    assert pal.toolTipBase().color().rgb() == colors.tooltip_bg.rgb()
    assert pal.toolTipText().color().rgb() == colors.tooltip_text.rgb()
    panel_pal = build_dock_palette(is_panel=True, colors=colors)
    assert panel_pal.window().color().rgb() == colors.panel_bg.rgb()


def test_tooltip_palette_matches_theme_colors(qapp):
    from PySide6.QtGui import QPalette

    colors = resolve_dock_colors()
    pal = build_tooltip_palette(colors=colors)
    for group in (QPalette.ColorGroup.Active, QPalette.ColorGroup.Inactive):
        assert pal.color(group, QPalette.ColorRole.ToolTipBase).rgb() == colors.tooltip_bg.rgb()
        assert pal.color(group, QPalette.ColorRole.ToolTipText).rgb() == colors.tooltip_text.rgb()


def test_tooltip_tokens_derived_and_overridable():
    # Derived defaults: tooltip bg differs from the panel, text is full-strength.
    theme = build_theme(SEED)
    core = theme[DockStyleCategory.CORE]
    panel_bg = theme[DockStyleCategory.PANEL]["bg_normal"]
    assert core["tooltip_bg"] != panel_bg
    assert core["tooltip_text"] == SEED.text

    # Explicit ThemeSpec overrides flow through build_theme.
    custom = ThemeSpec(
        base=[20, 23, 30, 255], accent=[45, 85, 170, 255], text=[200, 205, 215, 255],
        tooltip_bg=[10, 20, 30, 255], tooltip_text=[1, 2, 3, 255],
    )
    custom_core = build_theme(custom)[DockStyleCategory.CORE]
    assert custom_core["tooltip_bg"] == [10, 20, 30, 255]
    assert custom_core["tooltip_text"] == [1, 2, 3, 255]


def test_highlighted_text_contrasts_with_accent(qapp):
    pal = build_dock_palette(colors=resolve_dock_colors())
    highlighted = pal.highlightedText().color()
    accent = pal.highlight().color()
    # White/dark text must differ from the accent it sits on.
    assert highlighted != accent
    # The pure helper agrees: bright background -> dark text, and vice versa.
    assert _get_contrasting_text_color(QColor(255, 255, 255)) == QColor(20, 20, 20)
    assert _get_contrasting_text_color(QColor(0, 0, 0)) == QColor(255, 255, 255)


def test_tab_close_btn_color_is_brighter_than_normal_text():
    """close_btn_color must be more legible than the muted text_normal so the
    close icon pops against the colored tab backgrounds."""
    theme = build_theme(SEED)
    tab = theme[DockStyleCategory.TAB]
    normal = to_qcolor(tab["text_normal"])
    close = to_qcolor(tab["close_btn_color"])
    assert close.lightness() > normal.lightness()


def test_tab_close_icon_tinted_with_close_btn_color(qapp):
    """dock_icon(..., token="close_btn_color") must tint the glyph with the
    close_btn_color token rather than the muted text_normal."""
    from collections import Counter

    from lace.dock_menu import dock_icon
    from lace.dock_style_manager import get_dock_style_manager

    sm = get_dock_style_manager()
    expected = sm.get(DockStyleCategory.TAB, "close_btn_color")
    pm = dock_icon("close_tab", DockStyleCategory.TAB, token="close_btn_color").pixmap(14, 14)
    img = pm.toImage()
    counts = Counter()
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y)
            if c.alpha() > 0:
                counts[c.name()] += 1
    dominant, _ = counts.most_common(1)[0]
    assert dominant == expected.name()
    # and it is NOT the muted text_normal
    assert dominant != sm.get(DockStyleCategory.TAB, "text_normal").name()


def test_theme_bridge_pushes_tooltip_palette_to_qtooltip(qapp):
    """DockThemeBridge must propagate theme tooltip colors to ``QToolTip``.

    Qt renders tooltips in a top-level ``QTipLabel`` that reads its palette
    from ``QToolTip::palette()`` (cached the first time a tooltip is shown) —
    never from the widget/app palette.  The bridge is therefore the only path
    that themes app-wide tooltips, and it must push a new palette on every
    theme change.
    """
    from PySide6.QtWidgets import QToolTip, QWidget

    from lace import apply_dock_theme
    from lace.dock_theme_bridge import DockThemeBridge

    # Hold a strong reference: DockManager/demos keep the bridge alive; a
    # dropped reference lets Python GC destroy the QObject and its pending
    # singleShot(0) refresh timers before they fire.
    bridge = DockThemeBridge(target=qapp)

    def tip_bg():
        p = QToolTip.palette()
        return p.color(QPalette.ColorGroup.Active, QPalette.ColorRole.ToolTipBase)

    default_bg = tip_bg()

    apply_dock_theme("dark")
    qapp.processEvents()  # flush the debounced refresh
    dark_bg = tip_bg()
    assert dark_bg != default_bg

    apply_dock_theme("light")
    qapp.processEvents()
    light_bg = tip_bg()
    assert light_bg != dark_bg
    assert light_bg.lightness() > dark_bg.lightness()  # light theme → lighter tooltip

    # The pushed palette must match the theme engine's resolved tooltip tokens.
    from lace.dock_theme import resolve_dock_colors

    assert tip_bg().rgb() == resolve_dock_colors().tooltip_bg.rgb()

    # A widget-targeted bridge also updates the global tooltip palette.
    w = QWidget()
    w.show()
    DockThemeBridge(target=w, style_name="")
    apply_dock_theme("dark")
    qapp.processEvents()
    assert tip_bg().rgb() == resolve_dock_colors().tooltip_bg.rgb()
    w.close()
