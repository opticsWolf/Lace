# -*- coding: utf-8 -*-
"""Rounded dock areas round their content cleanly (plan Phase 0 item 8, fixed in Phase 5).

On 0.7.6 the content was clipped with an aliased QRegion mask: its edge
stepped outside the arc, and flush content leaked past the outline. Phase 5
paints an antialiased corner cap over the content instead.

Checked for the regular themes with a radius and the flush case, each with a
plain frame and with children that draw their own frame, scrollbars and grid;
and over the grid of radius x border width x corner_clip, all flush.
"""

import pytest

from tests.visual.corner_harness import CONTENTS, GRID, THEMES, corners_ok, measure


@pytest.mark.parametrize("content", CONTENTS)
@pytest.mark.parametrize("theme", THEMES + ("flush_r10",))
def test_content_corners_are_clean(qapp, theme, content):
    assert corners_ok(measure(theme, content)) == []


@pytest.mark.parametrize("case", sorted(GRID))
def test_corner_grid(qapp, case):
    assert corners_ok(measure(case)) == []
