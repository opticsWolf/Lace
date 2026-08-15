# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Union

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QApplication, QToolTip, QWidget, QStyleFactory

from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import (
    DockStyleCategory, resolve_dock_colors, build_dock_palette, build_tooltip_palette,
)

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
        #: Owns the QStyle handed to the target — see _apply_base_style().
        self._style = None

        # Apply a palette-friendly base style before setting colours.
        resolved_style = style_name if style_name is not None else DOCK_WIDGET_STYLE
        self._apply_base_style(resolved_style)

        # Subscribe to the categories that feed the palette.
        sm = get_dock_style_manager()
        sm.register(self, DockStyleCategory.CORE)
        sm.register(self, DockStyleCategory.TITLE_BAR)
        sm.register(self, DockStyleCategory.TAB)
        sm.register(self, DockStyleCategory.PANEL)
        sm.register(self, DockStyleCategory.SIDEBAR)
        sm.register(self, DockStyleCategory.SIDEPANEL)

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

        # Neither QApplication.setStyle() nor QWidget.setStyle() takes ownership
        # of the QStyle, so without a Python reference the object created above
        # is garbage-collected and the target is left pointing at freed memory.
        self._style = style
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
            # Bound to the target, not to self: the refresh writes a palette
            # into _target, and an unowned shot survives it. A theme applied
            # while a closed window is still alive queues one; the window is
            # then destroyed and whatever processes events next runs the
            # refresh against freed memory.
            QTimer.singleShot(0, self._target, self._execute_refresh)

    def _execute_refresh(self) -> None:
        self._refresh_scheduled = False
        self.refresh_dock_palette()

    # ──────────────────────────────────────────────────────────────────────
    # Palette construction & application
    # ──────────────────────────────────────────────────────────────────────

    def refresh_dock_palette(self) -> None:
        """Build a QPalette from the current dock theme and apply it."""
        colors = resolve_dock_colors()
        
        # 1. Apply the CORE palette to the application/manager (is_panel=False)
        palette = build_dock_palette(is_panel=False, colors=colors)
        self._target.setPalette(palette)

        # 2. Tooltips render in a top-level QTipLabel that reads its palette
        #    from QToolTip::palette() (cached at first show), so the app/widget
        #    palette never reaches them.  Push the theme's tooltip colors there
        #    so every tooltip in the app follows the active theme, regardless
        #    of what the bridge targets.
        QToolTip.setPalette(build_tooltip_palette(colors=colors))

        # The old "stylesheet nudge" (re-setting each window's stylesheet to force
        # QSS re-evaluation) is gone: all dock chrome is now painted or
        # palette-driven, so there is no hex/`palette()` QSS left to go stale on a
        # theme change.  Verified by dev_smoke/smoke_nudge.py.

        # No sweep over findChildren(DockWidget) here: every DockWidget
        # registers itself with the style manager in _init_dock_style(), so it
        # gets the same theme change through its own subscription (debounced to
        # one refresh per frame).  The sweep only added a third restyle per
        # theme apply, and a widget that does not update without it has a
        # missing registration, not a missing sweep.