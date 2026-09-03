# -*- coding: utf-8 -*-
"""The demos' Themes menus must list every built-in theme.

Each demo used to carry its own hardcoded (label, key) list, and all of them
silently went stale when presets were added — a Themes menu missing themes,
with nothing to catch it. They now derive from DOCK_THEMES via
lace.theme_choices(); this pins that they keep doing so.
"""

import pytest

from lace import theme_choices, theme_groups
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
def test_demo_runs_as_a_script(module_name):
    """`python demos/demo_app.py` puts demos/ on sys.path, not the repo root.

    A sibling-package import then raises ModuleNotFoundError before the window
    ever opens — which is exactly how these demos are meant to be run. Shared
    helpers therefore have to come from lace, not from the demos package.
    """
    import importlib
    import inspect

    module = importlib.import_module(module_name)
    offenders = [
        line for line in inspect.getsource(module).splitlines()
        if line.startswith(("from demos", "import demos"))
    ]
    assert not offenders, \
        f"{module_name} imports its own package, so it cannot run as a script:\n" \
        + "\n".join(offenders)


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


@pytest.mark.parametrize("module_name", DEMOS)
def test_demo_builds_grouped_submenus(module_name):
    """A flat column of twenty-seven ran off the bottom of the short title bar.

    theme_choices() still exists and still works; what a demo must not do is
    iterate it straight into addAction() and call that a menu.
    """
    import importlib
    import inspect

    source = inspect.getsource(importlib.import_module(module_name))
    assert "theme_groups()" in source,         f"{module_name} builds a flat themes menu"
    assert "for name, key in theme_choices()" not in source


def test_the_groups_reach_the_demos_intact():
    """The demos add one submenu per group, so an empty group is an empty menu."""
    assert all(choices for _, choices in theme_groups())
    assert sum(len(choices) for _, choices in theme_groups()) == len(theme_choices())
