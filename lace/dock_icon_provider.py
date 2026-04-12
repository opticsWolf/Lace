# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0
"""

import re
from pathlib import Path
from typing import Dict, Optional, Tuple

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QStyle

from .dock_style_manager import get_dock_style_manager
from .dock_theme import DockStyleCategory

import logging
logger = logging.getLogger(__name__)


class DockIconProvider:
    """
    Theme-aware SVG icon provider for the docking framework.
    Preloads SVGs and tints them dynamically based on the DockStyleManager.
    """
    
    _COLOR_PATTERN = re.compile(r'(fill|stroke)="(?!none\b)([^"]*)"')
    _FALLBACK_COLOR = "#C8CDD7"

    def __init__(self, directory: str | Path):
        self._path = Path(directory)
        self._svg_cache: Dict[str, str] = {}
        self._icon_cache: Dict[Tuple[str, str, bool, bool, int], QIcon] = {}
        
        # Integration with your style manager
        self._style_mgr = get_dock_style_manager()
        # Subscribe to all categories to clear cache on theme switch
        self._style_mgr.register(self, DockStyleCategory.CORE)
        
        if self._path.exists():
            self._preload()
        else:
            logger.warning(f"Icon directory not found: {self._path}")

    def _preload(self):
        """Read every *.svg in the directory into the string cache — O(n)."""
        for file in sorted(self._path.glob("*.svg")):
            try:
                self._svg_cache[file.stem.lower()] = file.read_text(encoding="utf-8")
            except OSError as exc:
                logger.warning(f"Could not read icon '{file.name}': {exc}")

    @classmethod
    def _tint_svg(cls, svg: str, color: str) -> str:
        if "currentColor" in svg:
            return svg.replace("currentColor", color)
        return cls._COLOR_PATTERN.sub(lambda m: f'{m.group(1)}="{color}"', svg)

    @staticmethod
    def _render_svg(svg_data: bytes, size: int) -> QPixmap:
        renderer = QSvgRenderer(QByteArray(svg_data))
        if not renderer.isValid():
            fallback = QPixmap(QSize(size, size))
            fallback.fill(Qt.GlobalColor.transparent)
            return fallback

        # Account for device pixel ratio (HiDPI displays)
        from PySide6.QtWidgets import QApplication
        dpr = QApplication.instance().devicePixelRatio() if QApplication.instance() else 1.0
        
        # Create pixmap at scaled size for sharp rendering
        scaled_size = int(size * dpr)
        pixmap = QPixmap(QSize(scaled_size, scaled_size))
        pixmap.setDevicePixelRatio(dpr)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        renderer.render(painter)
        painter.end()
        
        return pixmap

    def _resolve_color(self, category: DockStyleCategory, active: bool = False, disabled: bool = False) -> str:
        """Fetch the correct tint color from the Style Manager.
        
        Args:
            category: The style category to fetch colors from.
            active: Whether the icon is in an active/selected state.
            disabled: Whether the icon is in a disabled state (takes precedence over active).
        
        Returns:
            Hex color string for tinting the icon.
        """
        styles = self._style_mgr.get_all(category)
        core_styles = self._style_mgr.get_all(DockStyleCategory.CORE)
        
        # Disabled state takes precedence
        if disabled:
            # Check for category-specific disabled color first, then fall back to CORE
            if category == DockStyleCategory.TAB:
                color = styles.get("close_btn_bg_disable")
            elif category == DockStyleCategory.TITLE_BAR:
                color = styles.get("button_disable_clr")
            elif category == DockStyleCategory.SIDEPANEL:
                color = styles.get("button_disable_clr")
            elif category == DockStyleCategory.SIDEBAR:
                color = styles.get("tab_text_disabled")
            else:
                color = None
            
            # Fall back to CORE disabled_text_color if no category-specific color
            if color is None or (isinstance(color, QColor) and not color.isValid()):
                color = core_styles.get("disabled_text_color")
            
            if isinstance(color, QColor) and color.isValid():
                return color.name()
            return self._FALLBACK_COLOR
        
        # Map category and state to the specific style key
        if category == DockStyleCategory.TAB:
            color = styles.get("text_active" if active else "text_normal")
        elif category == DockStyleCategory.SIDEBAR:
            color = styles.get("tab_text_active" if active else "tab_text_normal")
        elif category == (DockStyleCategory.TITLE_BAR):
            color = styles.get("button_color" if active else "button_color")
        elif category == (DockStyleCategory.SIDEPANEL):
            color = styles.get("button_color" if active else "button_color")
        else:
            color = styles.get("text_color")

        if isinstance(color, QColor) and color.isValid():
            return color.name()
        return self._FALLBACK_COLOR

    def get(
        self,
        name: str,
        category: DockStyleCategory,
        active: bool = False,
        disabled: bool = False,
        size: int = 16
    ) -> QIcon:
        """
        Get a theme-tinted icon.
        
        Args:
            name: SVG filename (without extension).
            category: Style category determining the tint color.
            active: Whether icon is in active/selected state.
            disabled: Whether icon is in disabled state (takes precedence over active).
            size: Icon size in pixels.
        
        Returns:
            QIcon tinted with the appropriate color for the state.
        """
        key = name.lower()
        color = self._resolve_color(category, active, disabled)
        cache_key = (key, color, active, disabled, size)

        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]

        if key not in self._svg_cache:
            # Return empty icon if missing
            return QIcon()

        tinted = self._tint_svg(self._svg_cache[key], color)
        pixmap = self._render_svg(tinted.encode("utf-8"), size)
        
        icon = QIcon()
        icon.addPixmap(pixmap)
        
        self._icon_cache[cache_key] = icon
        return icon

    def on_style_changed(self, category: DockStyleCategory, changes: dict):
        """Flush the tint cache when the theme changes."""
        self._icon_cache.clear()

# --- Singleton Access ---
_provider_instance = None

def get_icon_provider(directory: str | Path = None) -> DockIconProvider:
    global _provider_instance
    if _provider_instance is None:
        if directory is None:
            raise ValueError("Must provide directory on first initialization")
        _provider_instance = DockIconProvider(directory)
    return _provider_instance