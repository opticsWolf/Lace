# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0
"""

import copy
import logging
from dataclasses import fields
from typing import Dict, Any, Optional, Set
from weakref import WeakSet

from PySide6.QtCore import QObject, Signal

from .dock_colors import deep_to_qcolor
from .dock_theme import (
    DockStyleCategory, DockCoreStyleSchema, DockTabStyleSchema,
    DockTitleBarStyleSchema, DockSidebarStyleSchema,
    DockSidePanelStyleSchema, DockSplitterStyleSchema, DockOverlayStyleSchema,
    DockPanelStyleSchema, BASE_DOCK_DEFAULTS
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

def _create_default_schema(category: DockStyleCategory) -> Any:
    schema = _SCHEMA_MAP[category]()
    if category in BASE_DOCK_DEFAULTS:
        for key, val in copy.deepcopy(BASE_DOCK_DEFAULTS[category]).items():
            # Store colours natively as QColor (converted once here) so reads
            # are free; non-colour scalars pass through unchanged.
            setattr(schema, key, deep_to_qcolor(val))
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
        Applies a theme from dock_custom_theme.py. 
        Resets to defaults before applying overrides so that missing keys revert cleanly.
        """
        from .dock_custome_theme import DOCK_THEMES
        if theme_name not in DOCK_THEMES:
            logger.warning(f"Theme '{theme_name}' not found in DOCK_THEMES.")
            return False
            
        # Suppress signals during the piecemeal update
        self._suppress_signals = True
        try:
            self._reset_to_defaults()
            theme_data = DOCK_THEMES[theme_name]
            
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
        # Values are stored natively (QColor for colours, scalars otherwise),
        # so reads need no conversion.
        schema = self._schemas.get(category)
        if schema and hasattr(schema, key):
            value = getattr(schema, key)
            return value if value is not None else default
        return default

    def get_all(self, category: DockStyleCategory) -> Dict[str, Any]:
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
            if not hasattr(schema, key):
                continue
            # Convert colours to QColor once, on write.
            store_value = deep_to_qcolor(value)
            if getattr(schema, key) != store_value:
                setattr(schema, key, store_value)
                changed.add(key)

        if changed:
            self._dict_cache[category] = None
            self.generation += 1

            if not self._suppress_signals:
                qt_changes = {k: self.get(category, k) for k in changed}
                self._notify_subscribers(category, qt_changes)
                    
        return changed

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
            except Exception as e:
                logger.error(f"Subscriber notification failed: {e}")

# Convenience Functions
def get_dock_style_manager() -> DockStyleManager:
    return DockStyleManager.instance()

def apply_dock_theme(theme_name: str) -> bool:
    return DockStyleManager.instance().apply_theme(theme_name)