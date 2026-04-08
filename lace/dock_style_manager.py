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

from PySide6.QtGui import QColor, QFont
from PySide6.QtCore import Qt, QObject, Signal

from .dock_theme import (
    DockStyleCategory, DockCoreStyleSchema, DockTabStyleSchema, 
    DockTitleBarStyleSchema, DockSidebarStyleSchema, DockSplitterStyleSchema, 
    DockOverlayStyleSchema, BASE_DOCK_DEFAULTS
)

logger = logging.getLogger(__name__)


def _is_color_list(val: Any) -> bool:
    return (isinstance(val, (list, tuple))
            and 3 <= len(val) <= 4
            and all(isinstance(c, (int, float)) for c in val))

def to_qcolor(val) -> QColor:
    if isinstance(val, QColor):
        return val
    if isinstance(val, str) and val.startswith("#"):
        return QColor(val)
    if isinstance(val, (list, tuple)) and len(val) >= 3:
        return QColor(int(val[0]), int(val[1]), int(val[2]), int(val[3]) if len(val) > 3 else 255)
    return QColor(0, 0, 0, 255)

def _deep_convert_for_read(value: Any) -> Any:
    if isinstance(value, QColor):
        return value
    if _is_color_list(value):
        return to_qcolor(value)
    if isinstance(value, dict):
        return {k: _deep_convert_for_read(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_deep_convert_for_read(item) for item in value]
    return value

def _deep_coerce_for_storage(value: Any) -> Any:
    if isinstance(value, QColor):
        return [value.red(), value.green(), value.blue(), value.alpha()]
    if isinstance(value, dict):
        return {k: _deep_coerce_for_storage(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_deep_coerce_for_storage(item) for item in value]
    return value


_SCHEMA_MAP: Dict[DockStyleCategory, type] = {
    DockStyleCategory.CORE:      DockCoreStyleSchema,
    DockStyleCategory.TAB:       DockTabStyleSchema,
    DockStyleCategory.TITLE_BAR: DockTitleBarStyleSchema,
    DockStyleCategory.SIDEBAR:   DockSidebarStyleSchema,
    DockStyleCategory.SPLITTER:  DockSplitterStyleSchema,
    DockStyleCategory.OVERLAY:   DockOverlayStyleSchema,  # <--- Added to map
}

def _create_default_schema(category: DockStyleCategory) -> Any:
    schema = _SCHEMA_MAP[category]()
    if category in BASE_DOCK_DEFAULTS:
        for key, val in copy.deepcopy(BASE_DOCK_DEFAULTS[category]).items():
            setattr(schema, key, val)
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

    def _reset_to_defaults(self) -> None:
        """Resets all schemas back to the hardcoded defaults."""
        self._schemas = {
            cat: _create_default_schema(cat) for cat in DockStyleCategory
        }
        for cat in DockStyleCategory:
            self._dict_cache[cat] = None

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
        schema = self._schemas.get(category)
        if schema and hasattr(schema, key):
            value = getattr(schema, key)
            return _deep_convert_for_read(value) if value is not None else default
        return default
        
    def get_all(self, category: DockStyleCategory) -> Dict[str, Any]:
        if self._dict_cache[category] is None:
            schema = self._schemas[category]
            raw = {f.name: getattr(schema, f.name) for f in fields(schema)}
            self._dict_cache[category] = {k: _deep_convert_for_read(v) for k, v in raw.items()}
        return dict(self._dict_cache[category])
        
    def update(self, category: DockStyleCategory, **kwargs) -> Set[str]:
        schema = self._schemas.get(category)
        if not schema:
            return set()
            
        changed = set()
        for key, value in kwargs.items():
            if not hasattr(schema, key):
                continue
            store_value = _deep_coerce_for_storage(value)
            if getattr(schema, key) != store_value:
                setattr(schema, key, store_value)
                changed.add(key)
                
        if changed:
            self._dict_cache[category] = None
            
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
