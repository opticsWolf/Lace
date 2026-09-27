# -*- coding: utf-8 -*-
"""Rounded dock areas round their content cleanly (plan Phase 0 item 8, fixed in Phase 5).

On 0.7.6 the content is clipped with an aliased QRegion mask: where the
content reaches the rounded corner its edge steps outside the arc, and where
it sits flush with the outline magenta leaks past it. flush_r10 (a large
radius with the content flush against the outline) is the hardest case.
The xfails are strict, so each case flips to XPASS once Phase 5's corner cap
lands -- then drop its mark.
"""

import pytest

from tests.visual.corner_harness import THEMES, VARIANTS, corners_ok, measure

#: Cases whose content still reaches a rounded corner unclipped on 0.7.6.
NOT_YET_CLEAN = {"solarized_light", "flush_r10"}


@pytest.mark.parametrize("theme", [
    pytest.param(t, marks=pytest.mark.xfail(strict=True, reason="0.7.6 QRegion mask"))
    if t in NOT_YET_CLEAN else t
    for t in THEMES + tuple(VARIANTS)
])
def test_content_corners_are_clean(qapp, theme):
    assert corners_ok(measure(theme)) == []
