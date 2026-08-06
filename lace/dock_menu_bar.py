# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.

"""Theme-driven styling for plain ``QMainWindow`` menu bars.

Fusion draws a 1px shadow row at the bottom of ``QMenuBar``.  The only
palette-compatible way to remove it is the ``QMenuBar { border: none; }``
rule — but any stylesheet on a menu bar makes Qt ignore the palette
``Window`` role, so the background must be pinned explicitly to the
sidebar colour (theme base, same as the canvas) and re-applied whenever
the theme changes.  (Using ``background: transparent`` instead resets the
menu bar's palette to the style default, breaking the theme accent on
hovered/pressed items.)
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QMenuBar, QWidget

from lace.dock_theme import DockStyleCategory, to_qcolor


class DockMenuBarStyler:
    """Keeps a ``QMenuBar`` matching the dock chrome.

    Applies ``QMenuBar { background: <sidebar bg>; border: none; }`` and
    re-applies it whenever the dock theme changes, so the bar shows the
    sidebar/canvas colour without Fusion's 1px bottom border while
    hovered/pressed items keep the theme accent.
    """

    _STYLE_CATEGORIES = (
        DockStyleCategory.SIDEBAR,
        DockStyleCategory.CORE,
    )

    def __init__(
        self,
        menu_bar: QMenuBar,
        parent: Optional[QWidget] = None,
    ) -> None:
        from lace.dock_style_manager import get_dock_style_manager

        self._parent = parent
        self._menu_bar = menu_bar
        self._style_mgr = get_dock_style_manager()

        for category in self._STYLE_CATEGORIES:
            self._style_mgr.register(self, category)
        self.refresh_style()

    # -- DockStyleManager callback --------------------------------------

    def on_style_changed(self, category: DockStyleCategory, changes: dict) -> None:
        """Re-apply the stylesheet when any subscribed category changes."""
        self.refresh_style()

    # -- public API ------------------------------------------------------

    @property
    def menu_bar(self) -> QMenuBar:
        """The menu bar being styled."""
        return self._menu_bar

    @menu_bar.setter
    def menu_bar(self, mb: QMenuBar) -> None:
        """Replace the menu bar and re-apply the current theme."""
        self._menu_bar = mb
        self.refresh_style()

    def refresh_style(self) -> None:
        """Apply ``QMenuBar { background: <sidebar bg>; border: none; }``
        with the current dock theme colours."""
        if self._menu_bar is None:
            return

        from lace.dock_theme import build_dock_palette

        bg = self._style_mgr.get(DockStyleCategory.SIDEBAR, "bg_color")
        if bg is None:
            bg = self._style_mgr.get(DockStyleCategory.CORE, "canvas_bg")
        if bg is None:
            return

        bg_hex = to_qcolor(bg).name()
        self._menu_bar.setStyleSheet(
            f"QMenuBar {{ background: {bg_hex}; border: none; }}"
        )

        # Any QSS on a menu bar makes Qt ignore the palette Window role,
        # but hovered/pressed items still come from the palette.  QSS
        # polish snapshots a stale palette into the widget, so set it
        # explicitly from the current theme to avoid a one-theme lag.
        palette = build_dock_palette(is_panel=False)
        palette.setColor(QPalette.ColorRole.Window, to_qcolor(bg))
        self._menu_bar.setPalette(palette)


__all__ = [
    "DockMenuBarStyler",
]
