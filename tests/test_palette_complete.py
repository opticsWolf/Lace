# -*- coding: utf-8 -*-
"""Phase 3: the dock palette sets every role in every colour group.

A role left unset falls back to the platform palette -- on Windows that is a
light palette, so a dark theme would show white fills in whatever widget
reads the missing role (Fusion's Midlight bevels, disabled fields, a
selection in an unfocused window).
"""

import pytest
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QComboBox, QLineEdit, QPushButton

from lace import color_science as cs
from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import build_dock_palette, qcolor_to_list, resolve_dock_colors
from lace.theme_contrast import CONTRAST_TARGETS
from tests.theme_sets import REGULAR, load

G = QPalette.ColorGroup
R = QPalette.ColorRole
GROUPS = (G.Active, G.Inactive, G.Disabled)
ROLES = [r for r in R if r not in (R.NoRole, R.NColorRoles)] if hasattr(R, "NColorRoles") else \
    [r for r in R if r != R.NoRole]
DISABLED = CONTRAST_TARGETS["disabled"]["normal"]


@pytest.fixture(params=REGULAR)
def palette(request, qapp):
    get_dock_style_manager().apply_theme_dict(load(request.param))
    return request.param, build_dock_palette(is_panel=True, colors=resolve_dock_colors())


def rgb(pal, group, role):
    return qcolor_to_list(pal.color(group, role))


def test_every_role_in_every_group_is_set(palette):
    name, pal = palette
    unset = [(g.name, r.name) for g in GROUPS for r in ROLES if not pal.isBrushSet(g, r)]
    assert not unset, (name, unset)


def test_disabled_text_is_legible_on_disabled_fills(palette):
    name, pal = palette
    for text, fill in ((R.Text, R.Base), (R.ButtonText, R.Button), (R.WindowText, R.Window),
                       (R.HighlightedText, R.Highlight), (R.PlaceholderText, R.Base)):
        ratio = cs.contrast_ratio(rgb(pal, G.Disabled, text), rgb(pal, G.Disabled, fill))
        assert ratio >= DISABLED - 0.01, (name, text.name, round(ratio, 2))


def test_disabled_fills_fade_toward_the_window(palette):
    name, pal = palette
    win = rgb(pal, G.Disabled, R.Window)
    for role in (R.Base, R.Button, R.Highlight):
        active, disabled = rgb(pal, G.Active, role), rgb(pal, G.Disabled, role)
        if active == win:
            continue
        assert cs.delta_e(disabled, win) < cs.delta_e(active, win), (name, role.name)


def test_inactive_selection_is_quieter(palette):
    name, pal = palette
    active, inactive = rgb(pal, G.Active, R.Highlight), rgb(pal, G.Inactive, R.Highlight)
    assert cs.to_oklch(inactive)[1] <= cs.to_oklch(active)[1] + 1e-6, name
    base = rgb(pal, G.Inactive, R.Base)
    text = rgb(pal, G.Inactive, R.HighlightedText)
    assert cs.contrast_ratio(text, cs._composite(inactive, base)) >= 4.5 - 0.01, name


def test_inactive_matches_active_outside_the_selection(palette):
    name, pal = palette
    for role in ROLES:
        if role in (R.Highlight, R.HighlightedText):
            continue
        assert pal.color(G.Inactive, role) == pal.color(G.Active, role), (name, role.name)


def test_disabled_widgets_read_the_disabled_group(qapp):
    """A live disabled line edit, button and combo box get the themed disabled colours."""
    sm = get_dock_style_manager()
    sm.apply_theme_dict(load("midnight"))
    pal = build_dock_palette(is_panel=True, colors=resolve_dock_colors())
    for cls in (QLineEdit, QPushButton, QComboBox):
        w = cls()
        w.setPalette(pal)
        w.setEnabled(False)
        got = w.palette()
        assert got.currentColorGroup() == G.Disabled or not w.isEnabled()
        for role in (R.Base, R.Button, R.Text, R.ButtonText):
            assert got.color(G.Disabled, role) == pal.color(G.Disabled, role), (cls.__name__, role)
        w.deleteLater()
