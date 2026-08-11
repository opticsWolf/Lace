# -*- coding: utf-8 -*-
"""Theme token schema regression tests — docs/CODE_REVIEW.md §3.1, §6.

The failure mode these guard against is silent: setattr() on a non-slotted
dataclass *creates* attributes that are not fields, so an undeclared token
became a "ghost" — visible to get(), invisible to get_all(), which iterates
dataclasses.fields(). get_all() has ~20 call sites, so a ghost read through
any of them was permanently None with no error anywhere.
"""

import dataclasses
import logging

import pytest
from PySide6.QtGui import QColor

from lace.dock_custom_theme import DOCK_THEMES
from lace.dock_style_manager import _SCHEMA_MAP, BASE_DOCK_DEFAULTS, get_dock_style_manager
from lace.dock_theme import DockStyleCategory, ThemeSpec, build_theme


@pytest.fixture
def manager(qapp):
    style_manager = get_dock_style_manager()
    yield style_manager
    style_manager.apply_theme("default")


def _declared(category):
    return {f.name for f in dataclasses.fields(_SCHEMA_MAP[category])}


def test_build_theme_emits_only_declared_tokens(qapp):
    spec = ThemeSpec(
        base=[24, 24, 24, 255],
        accent=[0, 120, 212, 255],
        text=[204, 204, 204, 255],
        title_border_bottom=1.5,
        title_border_color=[0, 255, 255, 255],
        content_margin=6,
    )
    ghosts = {
        category.name: sorted(set(tokens) - _declared(category))
        for category, tokens in build_theme(spec).items()
        if category in _SCHEMA_MAP and set(tokens) - _declared(category)
    }
    assert not ghosts, f"build_theme emits tokens that are not schema fields: {ghosts}"


def test_base_defaults_declare_every_token(qapp):
    ghosts = {
        category.name: sorted(set(tokens) - _declared(category))
        for category, tokens in BASE_DOCK_DEFAULTS.items()
        if category in _SCHEMA_MAP and set(tokens) - _declared(category)
    }
    assert not ghosts, f"BASE_DOCK_DEFAULTS seeds tokens that are not schema fields: {ghosts}"


@pytest.mark.parametrize("theme_name", sorted(DOCK_THEMES))
def test_shipped_themes_set_no_unknown_tokens(manager, theme_name, caplog):
    with caplog.at_level(logging.WARNING, logger="lace.dock_style_manager"):
        manager.apply_theme(theme_name)
    unknown = [r.getMessage() for r in caplog.records if "unknown token" in r.getMessage()]
    assert not unknown, f"theme '{theme_name}' sets tokens no schema declares: {unknown}"


def test_every_token_is_reachable_through_get_all(manager):
    """get() and get_all() must agree — divergence is the ghost-token symptom."""
    manager.apply_theme("cyberpunk_neon")
    for category in _SCHEMA_MAP:
        all_tokens = manager.get_all(category)
        for name in _declared(category):
            assert name in all_tokens, f"{category.name}.{name} is missing from get_all()"
            assert all_tokens[name] == manager.get(category, name, all_tokens[name]), \
                f"{category.name}.{name} differs between get() and get_all()"


def test_title_border_bottom_survives_to_the_paint_layer(manager):
    """ThemeSpec.title_border_bottom -> TITLE_BAR.border_bottom, via get_all().

    This token was dead at three independent points; cyberpunk_neon has shipped
    a 1.5px cyan rule that drew nothing.
    """
    manager.apply_theme("cyberpunk_neon")
    title_bar = manager.get_all(DockStyleCategory.TITLE_BAR)
    assert title_bar["border_bottom"] == 1.5
    assert isinstance(title_bar["border_color"], QColor)


@pytest.mark.xfail(reason="colour coercion is shape-based; fixed in 0.5.15", strict=True)
def test_content_margin_is_not_coerced_to_a_colour(manager):
    """content_margin takes list/tuple values that look like RGBA to a shape check."""
    for margin in (6, (8, 2), [6, 4, 6], [6, 4, 6, 4]):
        manager.apply_theme_dict(build_theme(ThemeSpec(
            base=[24, 24, 24, 255],
            accent=[0, 120, 212, 255],
            text=[204, 204, 204, 255],
            content_margin=margin,
        )))
        stored = manager.get(DockStyleCategory.PANEL, "content_margin")
        assert not isinstance(stored, QColor), f"{margin!r} was coerced to a colour"
