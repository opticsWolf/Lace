# -*- coding: utf-8 -*-
"""The staged theme sets resolve to real, loadable themes."""

from tests import theme_sets


def test_stages_nest_and_have_their_sizes():
    assert len(theme_sets.QUICK) == 5
    assert len(theme_sets.REGULAR) == 11
    assert len(theme_sets.FULL) == 20
    assert set(theme_sets.QUICK) <= set(theme_sets.REGULAR) <= set(theme_sets.FULL)
    assert set(theme_sets.FULL) <= set(theme_sets.all_themes())


def test_all_covers_presets_and_ten_kilim_fixtures():
    assert len(theme_sets.kilim_keys()) == 10
    assert len(theme_sets.all_themes()) == 52


def test_every_theme_loads(theme_key):
    assert theme_sets.load(theme_key)
