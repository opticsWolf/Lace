# -*- coding: utf-8 -*-
"""Shared helpers for the Lace demo applications."""

from typing import List, Tuple


def theme_choices() -> List[Tuple[str, str]]:
    """``(label, key)`` for every built-in theme, in definition order.

    Derived from ``DOCK_THEMES`` rather than written out: each demo used to
    carry its own literal list, and every one of them silently went stale the
    moment a preset was added — a Themes menu missing themes.

    The keys are snake_case, so ``"tokyo_night"`` becomes ``"Tokyo Night"``.
    """
    from lace.dock_custom_theme import DOCK_THEMES

    return [(key.replace("_", " ").title(), key) for key in DOCK_THEMES]


__all__ = ["theme_choices"]
