# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List

from .enums import DockWidgetArea

logger = logging.getLogger(__name__)


@dataclass
class SidebarState:
    """Persistent state for sidebars."""
    width: int = 280
    height: int = 250
    expanded_tabs: List[str] = None
    
    def __post_init__(self):
        if self.expanded_tabs is None:
            self.expanded_tabs = []
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


class SidebarStateManager:
    """Manages persistence of sidebar states."""
    
    def __init__(self, save_path: str = None):
        self._save_path = Path(save_path) if save_path else None
        self._states: Dict[str, SidebarState] = {}
    
    def save_state(self, key, state: SidebarState):
        # Extract the name if it's an Enum, otherwise use the string directly
        key_str = key.name if hasattr(key, 'name') else str(key)
        self._states[key_str] = state

    def load_state(self, key) -> SidebarState:
        # Extract the name if it's an Enum, otherwise use the string directly
        key_str = key.name if hasattr(key, 'name') else str(key)
        return self._states.get(key_str, SidebarState())
    
    def export_all(self) -> Dict[str, dict]:
        """Export all states as a serializable dict."""
        return {k: v.to_dict() for k, v in self._states.items()}
    
    def import_all(self, data: Dict[str, dict]):
        """Import states from a dict (e.g., from JSON deserialization)."""
        self._states.clear()
        for k, v in data.items():
            try:
                self._states[k] = SidebarState.from_dict(v)
            except Exception as e:
                logger.warning(f"Failed to import sidebar state for '{k}': {e}")
    
    def _persist(self):
        if not self._save_path:
            return
        
        try:
            data = {k: v.to_dict() for k, v in self._states.items()}
            self._save_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save sidebar state: {e}")
    
    def restore(self):
        if not self._save_path or not self._save_path.exists():
            return
        
        try:
            data = json.loads(self._save_path.read_text())
            for k, v in data.items():
                self._states[k] = SidebarState.from_dict(v)
        except Exception as e:
            logger.error(f"Failed to restore sidebar state: {e}")