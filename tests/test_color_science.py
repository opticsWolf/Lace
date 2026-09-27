# -*- coding: utf-8 -*-
"""lace.color_science: OKLCH round-trips, WCAG contrast and the operations on top."""

import json
import math

import pytest
from hypothesis import given, settings, strategies as st

from lace import color_science as cs

channel = st.integers(0, 255)
rgb = st.tuples(channel, channel, channel).map(lambda t: [*t, 255])
rgba = st.tuples(channel, channel, channel, channel).map(list)


def _hue_diff(h1, h2):
    d = abs(h1 - h2) % 360
    return min(d, 360 - d)


def _delta_e(a, b):
    La, aa, ba, _ = cs.to_oklab(a)
    Lb, ab, bb, _ = cs.to_oklab(b)
    return math.dist((La, aa, ba), (Lb, ab, bb))


# --- conversions -----------------------------------------------------------
@settings(max_examples=3000)
@given(rgba)
def test_oklch_round_trip_within_one_per_channel(c):
    back = cs.from_oklch(*cs.to_oklch(c))
    assert all(abs(x - y) <= 1 for x, y in zip(back, c)), (c, back)


def test_reference_points():
    assert cs.to_oklch([255, 255, 255, 255])[0] == pytest.approx(1.0, abs=1e-4)
    assert cs.to_oklch([0, 0, 0, 255])[0] == pytest.approx(0.0, abs=1e-6)
    # Ottosson's published value for sRGB red.
    L, C, h, _ = cs.to_oklch([255, 0, 0, 255])
    assert (L, C) == pytest.approx((0.6280, 0.2577), abs=2e-3)
    assert h == pytest.approx(29.23, abs=0.01)
    # Colours given without alpha are opaque.
    assert cs.to_oklch([10, 20, 30])[3] == 255


def test_out_of_gamut_keeps_lightness_and_hue():
    L, C, h, _ = cs.to_oklch([0, 120, 255, 255])
    out = cs.from_oklch(L, C * 3, h)
    L2, _, h2, _ = cs.to_oklch(out)
    assert L2 == pytest.approx(L, abs=0.01)
    assert _hue_diff(h, h2) < 2
    # Clamping of L and C.
    assert cs.from_oklch(1.5, -1, 0) == [255, 255, 255, 255]
    assert cs.from_oklch(-0.5, 0, 0, 300) == [0, 0, 0, 255]


# --- WCAG --------------------------------------------------------------------
@pytest.mark.parametrize("fg, bg, expected", [
    ([0, 0, 0, 255], [255, 255, 255, 255], 21.0),
    ([255, 255, 255, 255], [255, 255, 255, 255], 1.0),
    ([118, 118, 118, 255], [255, 255, 255, 255], 4.54),   # the classic AA grey
    ([255, 0, 0, 255], [255, 255, 255, 255], 4.0),
    ([0, 0, 255, 255], [255, 255, 255, 255], 8.59),
])
def test_contrast_ratio_reference_values(fg, bg, expected):
    assert cs.contrast_ratio(fg, bg) == pytest.approx(expected, abs=0.01)
    assert cs.contrast_ratio(bg, fg) == pytest.approx(expected, abs=0.01)


def test_translucent_foreground_is_composited():
    half_black = [0, 0, 0, 128]
    white = [255, 255, 255, 255]
    grey = [127, 127, 127, 255]
    assert cs.contrast_ratio(half_black, white) == pytest.approx(
        cs.contrast_ratio(grey, white), abs=0.05)
    assert cs.contrast_ratio([0, 0, 0, 0], white) == pytest.approx(1.0)


def test_is_dark():
    assert cs.is_dark([20, 20, 20, 255])
    assert not cs.is_dark([240, 240, 240, 255])
    # Yellow is light, blue of the same HLS lightness is dark.
    assert not cs.is_dark([255, 255, 0, 255])
    assert cs.is_dark([0, 0, 255, 255])


# --- step ----------------------------------------------------------------------
@given(rgb, st.floats(-0.3, 0.3), st.floats(0.01, 0.2))
def test_step_is_monotonic_in_dl(c, dl, extra):
    lo = cs.to_oklch(cs.step(c, dl))[0]
    hi = cs.to_oklch(cs.step(c, dl + extra))[0]
    assert hi >= lo - 0.005


def test_step_toward_contrast_moves_away():
    dark, light = [30, 30, 40, 255], [230, 230, 220, 255]
    assert cs.to_oklch(cs.step(dark, 0.1, toward="contrast"))[0] > cs.to_oklch(dark)[0]
    assert cs.to_oklch(cs.step(light, 0.1, toward="contrast"))[0] < cs.to_oklch(light)[0]
    assert cs.step(dark, -0.1, toward="contrast") == cs.step(dark, 0.1, toward="contrast")
    with pytest.raises(ValueError):
        cs.step(dark, 0.1, toward="up")


def test_step_is_perceptually_even_across_hues():
    """The same dL looks like the same change on grey, blue and yellow."""
    bases = ([128, 128, 128, 255], [40, 70, 200, 255], [200, 180, 40, 255])
    deltas = [_delta_e(b, cs.step(b, 0.06)) for b in bases]
    assert (max(deltas) - min(deltas)) / max(deltas) < 0.25, deltas


def test_step_keeps_hue():
    blue = [40, 70, 200, 255]
    assert _hue_diff(cs.to_oklch(blue)[2], cs.to_oklch(cs.step(blue, -0.1))[2]) < 2


# --- mix -----------------------------------------------------------------------
@given(rgba, rgba)
def test_mix_endpoints(a, b):
    assert all(abs(x - y) <= 1 for x, y in zip(cs.mix(a, b, 0), a))
    assert all(abs(x - y) <= 1 for x, y in zip(cs.mix(a, b, 1), b))


def test_mix_midpoint_and_clamping():
    black, white = [0, 0, 0, 255], [255, 255, 255, 0]
    mid = cs.mix(black, white, 0.5)
    assert cs.to_oklch(mid)[0] == pytest.approx(0.5, abs=0.01)
    assert mid[3] == 128
    assert cs.mix(black, white, -1) == black
    assert cs.mix(black, white, 2) == white


# --- ensure_contrast -------------------------------------------------------------
@settings(max_examples=400)
@given(rgba, rgb, st.sampled_from([3.0, 4.5, 7.0]))
def test_ensure_contrast_meets_the_ratio_when_reachable(fg, bg, ratio):
    out = cs.ensure_contrast(fg, bg, ratio)
    reachable = max(cs.contrast_ratio(cs.from_oklch(e, 0, 0, fg[3]), bg) for e in (0.0, 1.0))
    if cs.contrast_ratio(fg, bg) >= ratio:
        assert out == fg
    elif reachable >= ratio + 0.05:
        assert cs.contrast_ratio(out, bg) >= ratio
    assert out[3] == fg[3]


@settings(max_examples=400)
@given(rgb, rgb)
def test_ensure_contrast_keeps_hue(fg, bg):
    out = cs.ensure_contrast(fg, bg, 4.5)
    _, c_in, h_in, _ = cs.to_oklch(fg)
    l_out, c_out, h_out, _ = cs.to_oklch(out)
    # Hue is only meaningful with visible chroma on both sides, and above
    # the darkest tones. Beyond that, 8-bit rounding still moves the hue of
    # dark, low-chroma colours by a degree or two ([0, 53, 52] shifts 2.04),
    # so each side is allowed the hue change of one 8-bit step.
    if c_in > 0.05 and c_out > 0.05 and l_out > 0.25:
        slack = _step_hue(fg) + _step_hue(out)
        assert _hue_diff(h_in, h_out) <= 2 + slack, (fg, out)


def _step_hue(rgba):
    """The largest hue change one 8-bit step of one channel makes at ``rgba``."""
    h = cs.to_oklch(rgba)[2]
    out = 0.0
    for i in range(3):
        for d in (-1, 1):
            n = list(rgba)
            n[i] = min(255, max(0, n[i] + d))
            out = max(out, _hue_diff(h, cs.to_oklch(n)[2]))
    return out


def test_ensure_contrast_unreachable_returns_best():
    # A mid grey on a mid grey cannot reach 21:1; the result is the better end.
    bg = [119, 119, 119, 255]
    out = cs.ensure_contrast([120, 120, 120, 255], bg, 21)
    assert out[:3] in ([0, 0, 0], [255, 255, 255])
    assert cs.contrast_ratio(out, bg) == pytest.approx(
        max(cs.contrast_ratio([0, 0, 0], bg), cs.contrast_ratio([255, 255, 255], bg)))


def test_ensure_contrast_prefers_the_smaller_shift():
    # Grey-blue text on a dark panel: lightening is the short way.
    out = cs.ensure_contrast([60, 70, 110, 255], [25, 25, 30, 255], 4.5)
    assert cs.to_oklch(out)[0] > cs.to_oklch([60, 70, 110, 255])[0]


# --- on_color --------------------------------------------------------------------
def _all_accents():
    from lace.dock_custom_theme import THEME_SPECS
    from tests.theme_sets import FIXTURES
    from PySide6.QtGui import QColor
    accents = {k: list(s.accent) for k, s in THEME_SPECS.items()}
    for f in FIXTURES.glob("kilim_*.json"):
        hexa = json.loads(f.read_text(encoding="utf-8"))["accent"]
        c = QColor(hexa)
        accents[f.stem] = [c.red(), c.green(), c.blue(), 255]
    return accents


@pytest.mark.parametrize("key, accent", sorted(_all_accents().items()))
def test_on_color_is_readable_on_every_accent(key, accent):
    assert cs.contrast_ratio(cs.on_color(accent), accent) >= 4.5


@given(rgb)
def test_on_color_default_always_passes(bg):
    assert cs.contrast_ratio(cs.on_color(bg), bg) >= 4.5


def test_on_color_uses_the_preferred_pair():
    light_text, dark_text = [235, 230, 220, 255], [30, 32, 40, 255]
    assert cs.on_color([20, 20, 30, 255], prefer=(light_text, dark_text)) == light_text
    assert cs.on_color([240, 240, 240, 255], prefer=(light_text, dark_text)) == dark_text
    # A pair that falls short on a mid tone is lifted to the ratio.
    out = cs.on_color([128, 128, 128, 255], prefer=([150, 150, 150, 255], [100, 100, 100, 255]))
    assert cs.contrast_ratio(out, [128, 128, 128, 255]) >= 4.5


# --- delta_e / toward ------------------------------------------------------------
def test_delta_e():
    assert cs.delta_e([10, 20, 30, 255], [10, 20, 30, 0]) == 0
    assert cs.delta_e([0, 0, 0, 255], [255, 255, 255, 255]) == pytest.approx(1.0, abs=1e-3)


def test_toward_caps_the_move():
    a, b = [30, 30, 40, 255], [200, 200, 220, 255]
    assert cs.toward(a, b, 1.0) == b
    capped = cs.toward(a, b, 0.05)
    assert cs.delta_e(a, capped) == pytest.approx(0.05, abs=0.005)
    assert cs.to_oklch(capped)[0] > cs.to_oklch(a)[0]


@given(rgb, rgb, st.floats(0.005, 0.1))
def test_toward_never_exceeds_the_cap(a, b, cap):
    assert cs.delta_e(a, cs.toward(a, b, cap)) <= cap + 1e-9
