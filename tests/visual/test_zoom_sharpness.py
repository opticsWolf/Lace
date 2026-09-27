# -*- coding: utf-8 -*-
"""Glyphs stay sharp on a zoomed canvas (plan Phase 0 item 7, fixed in Phase 4).

Every glyph fails on 0.7.6: stock Fusion paints most of them from cached
pixmaps and fills the rest with gradients. The xfails are strict, so each one
flips to a visible XPASS as Phase 4 replaces it -- then drop its mark.
"""

import pytest

from tests.visual.zoom_harness import SHARP_LIMIT, measure

THEMES = ("kilim_dark", "kilim_light_neo")
GLYPHS = (
    "combo_arrow", "spin_arrows", "dspin_arrows", "check_indicator",
    "radio_indicator", "hscrollbar", "vscrollbar", "slider_handle",
    "tree_branch_open", "tree_branch_shut", "menu_submenu_arrow",
)
#: Still painted from Fusion's pixmap cache inside its complex controls, which
#: LaceStyle redraws in 4b-2; remove entries as that lands.
NOT_YET_SHARP = {"combo_arrow", "spin_arrows", "dspin_arrows"}

_cache = {}


def _widths(theme):
    if theme not in _cache:
        _cache[theme] = measure(theme, (4,))[4]
    return _cache[theme]


@pytest.mark.parametrize("theme", THEMES)
@pytest.mark.parametrize("glyph", [
    pytest.param(g, marks=pytest.mark.xfail(strict=True, reason="0.7.6 Fusion glyph"))
    if g in NOT_YET_SHARP else g
    for g in GLYPHS
])
def test_glyph_edges_stay_sharp_at_4x(qapp, theme, glyph):
    width = _widths(theme)[glyph]
    assert 0 < width <= SHARP_LIMIT, f"{glyph} edge {width:.2f}px at 4x"
