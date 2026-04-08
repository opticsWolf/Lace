# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0

DockThemeBridge — Synchronises DockStyleManager with the Qt QPalette
=====================================================================

Subscribes to CORE and TITLE_BAR dock style categories and translates
colour values into a full ``QPalette`` that is applied to either:

- The ``DockManager`` subtree (default), so all standard Qt widgets
  embedded in dock panels (spinboxes, tree-views, etc.) match the
  active dock theme, or
- The global ``QApplication``, so *every* widget matches.

The bridge works best with the **Fusion** Qt style, which strictly
honours ``QPalette`` colours on every platform.  Other platform styles
(Windows, macOS) may partially ignore palette overrides.

Usage
-----
::

    from advanced_docking.dock_theme_bridge import DockThemeBridge

    # Apply Fusion and skin the entire dock manager:
    bridge = DockThemeBridge(target=dock_manager)

    # Later, switching themes updates the palette automatically:
    dock_manager.set_theme("midnight")

    # Or skin the whole app:
    bridge = DockThemeBridge()   # targets QApplication

Architecture mirrors Weave's ``AppThemeBridge``:

    DockStyleManager  ──style_changed──▶  DockThemeBridge.on_style_changed()
                                               │
                                               ▼
                                         refresh_dock_palette()
                                               │
                                               ▼
                                       target.setPalette()
                                               │
                                               ▼
                                   All standard Qt children repaint
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Union

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QApplication, QWidget, QStyleFactory

from .dock_style_manager import get_dock_style_manager
from .dock_theme import DockStyleCategory
from .dock_palette_bridge import resolve_dock_colors, build_dock_palette

logger = logging.getLogger(__name__)

# Default base style — Fusion respects all QPalette roles on every OS.
DOCK_WIDGET_STYLE: str = "Fusion"


class DockThemeBridge(QObject):
    """Listens to ``DockStyleManager`` and pushes ``QPalette`` updates
    so that standard Qt widgets inside dock panels match the active
    dock theme.

    Parameters
    ----------
    target : QWidget | QApplication | None
        Widget (or app) whose palette is updated.  ``None`` targets
        the running ``QApplication``.
    style_name : str | None
        Qt style to apply.  ``None`` uses ``DOCK_WIDGET_STYLE``
        (Fusion).  ``""`` skips automatic style application.
    parent : QObject | None
        Optional QObject parent for preventing premature GC.
    """

    def __init__(
        self,
        target: Optional[Union[QWidget, QApplication]] = None,
        style_name: Optional[str] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)

        self._target: Union[QWidget, QApplication] = (
            target if target is not None else QApplication.instance()
        )
        if self._target is None:
            raise RuntimeError(
                "DockThemeBridge requires a running QApplication or an "
                "explicit target widget.  Create one before instantiating."
            )

        self._refresh_scheduled = False

        # Apply a palette-friendly base style before setting colours.
        resolved_style = style_name if style_name is not None else DOCK_WIDGET_STYLE
        self._apply_base_style(resolved_style)

        # Subscribe to the categories that feed the palette.
        sm = get_dock_style_manager()
        sm.register(self, DockStyleCategory.CORE)
        sm.register(self, DockStyleCategory.TITLE_BAR)
        sm.register(self, DockStyleCategory.TAB)

        # Initial palette push.
        self.refresh_dock_palette()

    # ──────────────────────────────────────────────────────────────────────
    # Base style
    # ──────────────────────────────────────────────────────────────────────

    def _apply_base_style(self, style_name: str) -> None:
        """Apply a palette-friendly Qt style to the target."""
        if not style_name:
            return

        style = QStyleFactory.create(style_name)
        if style is None:
            logger.warning(
                "QStyleFactory could not create '%s'.  "
                "Available: %s.  Dock colours may not render correctly.",
                style_name, QStyleFactory.keys(),
            )
            return

        if isinstance(self._target, QApplication):
            self._target.setStyle(style)
        else:
            self._target.setStyle(style)

        logger.debug("Applied '%s' style to %s.", style_name,
                      type(self._target).__name__)

    # ──────────────────────────────────────────────────────────────────────
    # DockStyleManager callback
    # ──────────────────────────────────────────────────────────────────────

    def on_style_changed(
        self, category: DockStyleCategory, changes: Dict[str, Any]
    ) -> None:
        """Called by ``DockStyleManager`` when subscribed categories change.

        Debounces so that if CORE, TAB, and TITLE_BAR all update in the
        same frame, the palette is rebuilt only once.
        """
        if not self._refresh_scheduled:
            self._refresh_scheduled = True
            QTimer.singleShot(0, self._execute_refresh)

    def _execute_refresh(self) -> None:
        self._refresh_scheduled = False
        self.refresh_dock_palette()

    # ──────────────────────────────────────────────────────────────────────
    # Palette construction & application
    # ──────────────────────────────────────────────────────────────────────

    def refresh_dock_palette(self) -> None:
        """Build a QPalette from the current dock theme and apply it."""
        from PySide6.QtWidgets import QWidget, QApplication
        
        colors = resolve_dock_colors()
        palette = build_dock_palette(
            window_color=colors.canvas_bg,
            base_palette=self._target.palette(),
            colors=colors,
        )
        
        # Apply palette to the main target
        self._target.setPalette(palette)
        if self._target.style():
            self._target.setStyle(self._target.style())

        # --- OPTIMIZED STYLESHEET NUDGE ---
        if isinstance(self._target, QApplication):
            # If targeting the whole app, ONLY nudge visible windows.
            # This prevents Qt from wasting CPU re-styling hundreds of hidden
            # tooltips, closed menus, and cached UI elements.
            for window in self._target.topLevelWidgets():
                if window.isVisible():
                    current_ss = window.styleSheet()
                    window.setStyleSheet("/* force style re-evaluation */")
                    window.setStyleSheet(current_ss)
                    window.update()
        else:
            # If targeting just the DockManager, nudge it directly
            current_ss = self._target.styleSheet()
            self._target.setStyleSheet("/* force style re-evaluation */")
            self._target.setStyleSheet(current_ss)
            self._target.update()
            
        # IMPORTANT: Remove QCoreApplication.processEvents() here.
        # Let Qt handle the layout/paint cycle naturally on the next frame.

        logger.debug("Dock palette refreshed (Optimized).")