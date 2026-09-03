# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


import copy
import logging
from dataclasses import fields
from functools import lru_cache
from typing import Dict, Any, List, Optional, Set, Tuple
from weakref import WeakSet

from PySide6.QtCore import QObject, Signal

from lace.dock_theme import (
    DockStyleCategory, DockCoreStyleSchema, DockTabStyleSchema,
    DockTitleBarStyleSchema, DockSidebarStyleSchema,
    DockSidePanelStyleSchema, DockSplitterStyleSchema, DockOverlayStyleSchema,
    DockPanelStyleSchema, BASE_DOCK_DEFAULTS, deep_to_qcolor
)

logger = logging.getLogger(__name__)


_SCHEMA_MAP: Dict[DockStyleCategory, type] = {
    DockStyleCategory.CORE:      DockCoreStyleSchema,
    DockStyleCategory.TAB:       DockTabStyleSchema,
    DockStyleCategory.TITLE_BAR: DockTitleBarStyleSchema,
    DockStyleCategory.SIDEBAR:   DockSidebarStyleSchema,
    DockStyleCategory.SIDEPANEL: DockSidePanelStyleSchema,
    DockStyleCategory.SPLITTER:  DockSplitterStyleSchema,
    DockStyleCategory.OVERLAY:   DockOverlayStyleSchema,
    DockStyleCategory.PANEL:     DockPanelStyleSchema,  # <--- Added to map
}

#: The declared type every colour token uses. Matching on the exact annotation
#: rather than a substring matters: PANEL.content_margin is declared
#: Union[int, float, List[int], Tuple[int, ...]] and *contains* List[int]
#: without being a colour.
_COLOR_ANNOTATIONS = frozenset((
    Optional[List[int]],
    "Optional[List[int]]",
    "typing.Optional[typing.List[int]]",
))


@lru_cache(maxsize=None)
def _color_fields(schema_type: type) -> frozenset:
    """Names of the fields on *schema_type* that hold a colour."""
    return frozenset(
        f.name for f in fields(schema_type)
        if f.type in _COLOR_ANNOTATIONS or str(f.type) in _COLOR_ANNOTATIONS
    )


def _coerce(schema: Any, key: str, value: Any) -> Any:
    """Convert *value* for storage, by what the field is rather than how it looks.

    deep_to_qcolor() used to run on every token, and its is_color_list() decides
    purely by shape — "a list/tuple of 3 to 4 numbers". A CSS-style
    content_margin of [6, 4, 6] is exactly that shape, so it was stored as a
    QColor and DockWidget.refresh_style() then matched neither the numeric nor
    the list branch and silently fell back to a uniform margin.
    """
    if key in _color_fields(type(schema)):
        return deep_to_qcolor(value)
    return value


def _create_default_schema(category: DockStyleCategory) -> Any:
    schema = _SCHEMA_MAP[category]()
    if category in BASE_DOCK_DEFAULTS:
        for key, val in copy.deepcopy(BASE_DOCK_DEFAULTS[category]).items():
            # setattr on a non-slotted dataclass *creates* attributes that are
            # not fields, so an undeclared token here would become a "ghost":
            # visible to get(), invisible to get_all(), which iterates fields().
            if not hasattr(schema, key):
                logger.warning(
                    "Default theme sets unknown token %s.%s — ignored. "
                    "Declare it as a field on %s.",
                    category.name, key, type(schema).__name__
                )
                continue
            # Store colours natively as QColor (converted once here) so reads
            # are free; geometry and typography pass through unchanged.
            setattr(schema, key, _coerce(schema, key, val))
    return schema


class DockStyleManager(QObject):
    """
    Central manager for visual styles across the docking framework.
    Designed to easily interface with external style systems (like Weave).
    """
    style_changed = Signal(object, dict)
    
    _instance: Optional['DockStyleManager'] = None
    
    @classmethod
    def instance(cls) -> 'DockStyleManager':
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def __init__(self):
        super().__init__()
        self._schemas: Dict[DockStyleCategory, Any] = {
            cat: _create_default_schema(cat) for cat in DockStyleCategory
        }
        self._subscribers: Dict[DockStyleCategory, WeakSet] = {
            cat: WeakSet() for cat in DockStyleCategory
        }
        self._dict_cache: Dict[DockStyleCategory, Optional[Dict[str, Any]]] = {
            cat: None for cat in DockStyleCategory
        }
        self._suppress_signals = False
        # Monotonic counter bumped on every mutation; lets consumers cache
        # resolved colour snapshots and invalidate them cheaply (see
        # dock_palette_bridge.resolve_dock_colors).
        self.generation = 0

    def _reset_to_defaults(self) -> None:
        """Resets all schemas back to the hardcoded defaults."""
        self._schemas = {
            cat: _create_default_schema(cat) for cat in DockStyleCategory
        }
        for cat in DockStyleCategory:
            self._dict_cache[cat] = None
        self.generation += 1

    def apply_theme(self, theme_name: str) -> bool:
        """
        Applies a named theme from dock_custom_theme.py. 
        Resets to defaults before applying overrides so that missing keys revert cleanly.
        """
        from lace.dock_custom_theme import DOCK_THEMES
        if theme_name not in DOCK_THEMES:
            logger.warning(f"Theme '{theme_name}' not found in DOCK_THEMES.")
            return False
        return self.apply_theme_dict(DOCK_THEMES[theme_name])

    def apply_theme_dict(self, theme_data: Dict[DockStyleCategory, Dict[str, Any]]) -> bool:
        """
        Applies a complete theme dict (``{DockStyleCategory: {token: value}}``) such as
        those produced by :func:`dock_theme.build_theme` or ``load_theme_json``.
        Resets to defaults before applying overrides so that missing keys revert cleanly.
        """
        # Suppress signals during the piecemeal update
        self._suppress_signals = True
        try:
            self._reset_to_defaults()
            for category, changes in theme_data.items():
                self.update(category, **changes)
        finally:
            self._suppress_signals = False

        # Force a single full broadcast of all categories to ensure everything refreshes
        for category in DockStyleCategory:
            qt_changes = self.get_all(category)
            self._notify_subscribers(category, qt_changes)

        return True
    
    def register(self, subscriber: Any, category: DockStyleCategory) -> None:
        self._subscribers[category].add(subscriber)
        
    def unregister(self, subscriber: Any, category: Optional[DockStyleCategory] = None) -> None:
        if category is not None:
            self._subscribers[category].discard(subscriber)
        else:
            for sub_set in self._subscribers.values():
                sub_set.discard(subscriber)
                
    def get(self, category: DockStyleCategory, key: str, default: Any = None) -> Any:
        """Read one token.

        .. warning::
           The returned ``QColor`` is the live theme object, not a copy.
           Mutating it (``setAlpha``, ``setRgb``, …) corrupts the theme for
           every consumer in the process. Wrap it — ``QColor(value)`` — before
           changing anything. Copying here instead was rejected: this sits on
           the per-widget refresh path.
        """
        # Values are stored natively (QColor for colours, scalars otherwise),
        # so reads need no conversion.
        schema = self._schemas.get(category)
        if schema and hasattr(schema, key):
            value = getattr(schema, key)
            return value if value is not None else default
        return default

    def get_all(self, category: DockStyleCategory) -> Dict[str, Any]:
        """Every token in *category* as a dict.

        The dict is a fresh copy, but its values are **not** — see the warning
        on :meth:`get`. Treat the colours as read-only.
        """
        if self._dict_cache[category] is None:
            schema = self._schemas[category]
            self._dict_cache[category] = {f.name: getattr(schema, f.name) for f in fields(schema)}
        return dict(self._dict_cache[category])

    def update(self, category: DockStyleCategory, **kwargs) -> Set[str]:
        schema = self._schemas.get(category)
        if not schema:
            return set()

        changed = set()
        for key, value in kwargs.items():
            # Grouped sugar: button={"hover_bg": x, "size": 20} expands to the flat
            # tokens button_hover_bg / button_size. Schema fields are always flat
            # scalars/colours, so a dict value unambiguously means a group.
            if isinstance(value, dict):
                for sub_key, sub_val in value.items():
                    self._set_field(schema, f"{key}_{sub_key}", sub_val, changed)
                continue
            self._set_field(schema, key, value, changed)

        if changed:
            self._dict_cache[category] = None
            self.generation += 1

            if not self._suppress_signals:
                qt_changes = {k: self.get(category, k) for k in changed}
                self._notify_subscribers(category, qt_changes)
                    
        return changed

    def _set_field(self, schema: Any, key: str, value: Any, changed: Set[str]) -> None:
        """Coerce and write one flat field; record it in ``changed`` if it moved."""
        if not hasattr(schema, key):
            logger.warning("Theme sets unknown token %s on %s — ignored.",
                           key, type(schema).__name__)
            return
        # Convert colours to QColor once, on write.
        store_value = _coerce(schema, key, value)
        if getattr(schema, key) != store_value:
            setattr(schema, key, store_value)
            changed.add(key)

    def _notify_subscribers(self, category: DockStyleCategory, changes: Dict[str, Any]) -> None:
        """Internal helper to safely broadcast updates to all listeners."""
        self.style_changed.emit(category, changes)
        for subscriber in list(self._subscribers[category]):
            # Guard against dead C++ objects
            if isinstance(subscriber, QObject):
                try:
                    _ = subscriber.objectName()
                except RuntimeError:
                    continue
            try:
                if hasattr(subscriber, 'on_style_changed'):
                    subscriber.on_style_changed(category, changes)
                elif hasattr(subscriber, 'refresh_style'):
                    subscriber.refresh_style()
            except RuntimeError as e:
                # Only the deleted-C++-object case is swallowed.  A blanket
                # ``except Exception`` here turned every bug in a
                # refresh_style() into a log line and a widget that quietly
                # kept its old colours; those propagate now.
                logger.error(f"Subscriber notification failed: {e}")

# Convenience Functions
def get_dock_style_manager() -> DockStyleManager:
    return DockStyleManager.instance()

def apply_dock_theme(theme_name: str) -> bool:
    return DockStyleManager.instance().apply_theme(theme_name)


def _label(key: str) -> str:
    """``"tokyo_night"`` -> ``"Tokyo Night"``."""
    return key.replace("_", " ").title()


def theme_choices() -> List[Tuple[str, str]]:
    """``(label, key)`` for every built-in theme, in presentation order.

    For building a flat themes menu: pair each label with
    :func:`apply_dock_theme`.  Derived from ``DOCK_THEMES`` so a menu cannot
    fall behind the presets -- every hand-written copy of this list in the
    demos had gone stale.

    The order is ``THEME_GROUPS``' order flattened, so even a flat menu keeps
    each family together and its members in dark-neutral-light order.  Prefer
    :func:`theme_groups` where submenus are an option: twenty-seven entries in
    one list is a scroll, and it hides which of them are variants of which.
    """
    return [choice for _, choices in theme_groups() for choice in choices]


def theme_groups() -> List[Tuple[str, List[Tuple[str, str]]]]:
    """``(group label, [(label, key), ...])`` for every built-in theme.

    The grouping a themes menu should be built from -- one submenu per pair,
    in order.  See ``THEME_GROUPS`` in ``dock_custom_theme`` for what the
    groups mean and why the order inside them is not alphabetical.

    ``DOCK_THEMES`` carries one key ``THEME_GROUPS`` does not: ``"default"``,
    which is the stock look rather than a preset and has no ``ThemeSpec``.  It
    heads the first group.  Anything else ungrouped joins it there rather than
    being dropped, so a preset added without a group is merely misfiled in the
    menu instead of missing from it.
    """
    from lace.dock_custom_theme import DOCK_THEMES, THEME_GROUPS

    grouped = {key for keys in THEME_GROUPS.values() for key in keys}
    orphans = [key for key in DOCK_THEMES if key not in grouped]

    out: List[Tuple[str, List[Tuple[str, str]]]] = []
    for index, (title, keys) in enumerate(THEME_GROUPS.items()):
        members = (orphans if index == 0 else []) + [
            key for key in keys if key in DOCK_THEMES]
        out.append((title, [(_label(key), key) for key in members]))
    return out


from lace.theme_manager import ThemeManager
__all__ = [
    "DockStyleCategory", "DockStyleManager", "get_dock_style_manager",
    "apply_dock_theme", "theme_choices", "theme_groups", "ThemeManager"
]