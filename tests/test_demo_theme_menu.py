# -*- coding: utf-8 -*-
"""The demos' Themes menus must list every built-in theme.

Each demo used to carry its own hardcoded (label, key) list, and all of them
silently went stale when presets were added — a Themes menu missing themes,
with nothing to catch it. They now derive from DOCK_THEMES via
demos.theme_choices(); this pins that they keep doing so.
"""

import pytest

from demos import theme_choices
from lace.dock_custom_theme import DOCK_THEMES

DEMOS = ("demos.demo_app",
         "demos.demo_app_custom_titlebar",
         "demos.demo_app_custom_titlebar_menus")


def test_every_theme_is_offered():
    assert {key for _, key in theme_choices()} == set(DOCK_THEMES)


def test_labels_are_human_readable():
    labels = {key: label for label, key in theme_choices()}
    assert labels["tokyo_night"] == "Tokyo Night"
    assert labels["cyberpunk_edge"] == "Cyberpunk Edge"
    assert labels["slate_amber"] == "Slate Amber"
    assert all(label and "_" not in label and not label.islower()
               for label in labels.values())


@pytest.mark.parametrize("module_name", DEMOS)
def test_demo_hardcodes_no_theme_list(module_name):
    """A literal theme key in a demo's menu code is how this went stale."""
    import importlib
    import inspect

    module = importlib.import_module(module_name)
    source = inspect.getsource(module)
    # The initial apply_dock_theme("...") call is a deliberate starting theme,
    # not a menu; everything else naming a preset is a list going stale.
    menu_lines = [
        line for line in source.splitlines()
        if any(f'"{key}"' in line for key in DOCK_THEMES)
        and "apply_dock_theme(" not in line
        and not line.lstrip().startswith("#")
    ]
    assert not menu_lines, \
        f"{module_name} names themes directly:\n" + "\n".join(menu_lines)
