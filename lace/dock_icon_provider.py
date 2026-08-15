# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.
#

import re
from importlib import resources
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication

from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import DockStyleCategory

import logging
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Resource Path Resolution
# ---------------------------------------------------------------------------

_ICON_PACKAGE = "lace.resources.lace_icons"


def _resolve_icon_path(
    directory: Optional[Union[str, Path]] = None,
) -> Optional[Union[Path, "resources.Traversable"]]:
    """Resolve icon directory from a filesystem path or package resources.

    Returns None if the directory cannot be found.
    """
    if directory is not None:
        p = Path(directory)
        if p.exists():
            return p
    # Fallback: use package resources (wheel-compatible)
    try:
        return resources.files(_ICON_PACKAGE)
    except (AttributeError, FileNotFoundError):
        return None


class DockIconProvider:
    """
    Theme-aware SVG icon provider for the docking framework.
    Preloads SVGs and tints them dynamically based on the DockStyleManager.

    Supports both filesystem paths (development) and package resources
    (importlib.resources, wheel-compatible).
    """

    _COLOR_PATTERN = re.compile(r'(fill|stroke)="(?!none\b)([^"]*)"')
    _FALLBACK_COLOR = "#C8CDD7"

    def __init__(self, directory: Optional[Union[str, Path]] = None):
        self._path: Optional[Union[Path, "resources.Traversable"]] = _resolve_icon_path(
            directory
        )
        self._svg_cache: Dict[str, str] = {}
        self._icon_cache: Dict[Tuple[str, str, bool, bool, int], QIcon] = {}

        # Integration with your style manager
        self._style_mgr = get_dock_style_manager()
        # Subscribe to all categories to clear cache on theme switch
        self._style_mgr.register(self, DockStyleCategory.CORE)

        if self._path is not None:
            self._preload()
        else:
            logger.warning("Icon directory not found")

    def _preload(self):
        """Read every *.svg in the icon directory into the string cache.

        Works for both filesystem paths (development) and package resources
        (importlib.resources, wheel-compatible) via the Traversable API, which
        ``pathlib.Path`` also satisfies.

        Not ``resources.as_file``: before Python 3.12 it only accepts a *file*,
        so on 3.10 and 3.11 it raised "MultiplexedPath ... is not a file" for
        the icon *directory*, every icon fell back to the untinted default, and
        the only symptom was a warning. ``iterdir`` / ``read_text`` are on
        Traversable in every supported version.
        """
        if self._path is None:
            return

        try:
            entries = sorted(self._path.iterdir(), key=lambda entry: entry.name)
        except (OSError, ModuleNotFoundError, TypeError) as exc:
            logger.warning(f"Could not read icons from {self._path}: {exc}")
            return

        for entry in entries:
            name = entry.name
            if not name.lower().endswith(".svg"):
                continue
            try:
                self._svg_cache[name[:-4].lower()] = entry.read_text(
                    encoding="utf-8"
                )
            except OSError as exc:
                logger.warning(f"Could not read icon '{name}': {exc}")

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
        dpr = QApplication.instance().devicePixelRatio() if QApplication.instance() else 1.0
        target = max(1, int(round(size * dpr)))

        # Supersample: render the SVG large, then smooth-downscale. Rendering a
        # 24px viewBox straight to ~16px rounds thin strokes asymmetrically, which
        # pushes some glyphs (e.g. the square-x tab-close) ~1px off-centre while
        # symmetric ones (plain x) land fine. Rendering at 4x and scaling down
        # keeps every glyph centred and crisp.
        ss = 4
        hi = target * ss
        big = QPixmap(QSize(hi, hi))
        big.fill(Qt.GlobalColor.transparent)

        painter = QPainter(big)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        # Explicit target rect so the viewBox scales to *fill* the pixmap and stays
        # centred.  Without it, render() draws at the SVG's native 24px in the
        # top-left corner when the target pixmap is larger than that.
        renderer.render(painter, QRectF(0, 0, hi, hi))
        painter.end()

        pixmap = big.scaled(target, target, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        pixmap.setDevicePixelRatio(dpr)
        return pixmap

    def _resolve_disabled_color(self, category: DockStyleCategory, styles: dict) -> str:
        if category == DockStyleCategory.TAB:
            color = styles.get("close_btn_bg_disable")
        elif category in (DockStyleCategory.TITLE_BAR, DockStyleCategory.SIDEPANEL):
            color = styles.get("button_disable_clr")
        elif category == DockStyleCategory.SIDEBAR:
            color = styles.get("tab_text_disabled")
        else:
            color = None

        if color is None or (isinstance(color, QColor) and not color.isValid()):
            core_styles = self._style_mgr.get_all(DockStyleCategory.CORE)
            color = core_styles.get("disabled_text_color")

        if isinstance(color, QColor) and color.isValid():
            return color.name()
        return self._FALLBACK_COLOR

    def _resolve_normal_color(self, category: DockStyleCategory, styles: dict, active: bool) -> str:
        if category == DockStyleCategory.TAB:
            color = styles.get("text_active" if active else "text_normal")
        elif category == DockStyleCategory.SIDEBAR:
            color = styles.get("tab_text_active" if active else "tab_text_normal")
        elif category in (DockStyleCategory.TITLE_BAR, DockStyleCategory.SIDEPANEL):
            color = styles.get("button_color")
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
        size: int = 16,
        token: Optional[str] = None,
    ) -> QIcon:
        """
        Get a theme-tinted icon.

        Args:
            name: SVG filename (without extension).
            category: Style category determining the tint color.
            active: Whether icon is in active/selected state.
            disabled: Whether icon is in disabled state (takes precedence over active).
            size: Icon size in pixels.
            token: Optional explicit style token name to tint with (e.g.
                ``"close_btn_color"``) instead of the category's default
                active/normal resolution.  Ignored for disabled icons.

        Returns:
            QIcon tinted with the appropriate color for the state.
        """
        key = name.lower()
        if key == "minimize":
            key = "restore"
        styles = self._style_mgr.get_all(category)
        if disabled:
            color = self._resolve_disabled_color(category, styles)
        elif token is not None:
            color = styles.get(token)
            if isinstance(color, QColor) and color.isValid():
                color = color.name()
            else:
                color = self._resolve_normal_color(category, styles, active)
        else:
            color = self._resolve_normal_color(category, styles, active)
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


def get_icon_provider(directory: Optional[Union[str, Path]] = None) -> DockIconProvider:
    """Get or create the global icon provider singleton.

    Args:
        directory: Optional filesystem path to SVG icons. If None, falls back
            to package resources (lace/resources/lace_icons/).

    Returns:
        The singleton DockIconProvider instance.

    Raises:
        ValueError: If no icon directory is found (neither filesystem nor package).
    """
    global _provider_instance
    if _provider_instance is None:
        resolved = _resolve_icon_path(directory)
        if resolved is None:
            raise ValueError(
                "Must provide a valid icon directory, or ensure "
                "lace/resources/lace_icons/ is installed with the package."
            )
        _provider_instance = DockIconProvider(directory)
    return _provider_instance
