# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


from typing import Tuple

from PySide6.QtCore import QObject, QTimer

from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import DockStyleCategory


class DockStyled:
    """Mixin for widgets that consume :class:`DockStyleManager` categories."""

    #: Categories this widget re-styles on.  Declaring every category read in
    #: ``refresh_style()`` (not just one) guarantees the widget repaints when
    #: any of them change.
    STYLE_CATEGORIES: Tuple[DockStyleCategory, ...] = ()

    def _init_dock_style(self, refresh: bool = True) -> None:
        """Register for :attr:`STYLE_CATEGORIES` and apply the initial style.

        Call at the end of ``__init__``, once child widgets exist.  Pass
        ``refresh=False`` for widgets that style lazily (e.g. paint-on-demand
        overlays whose ``refresh_style`` touches state built later in
        ``__init__``); they still restyle on subsequent theme changes.
        """
        self._style_mgr = get_dock_style_manager()
        self._refresh_queued = False
        for category in self.STYLE_CATEGORIES:
            self._style_mgr.register(self, category)
        if refresh:
            self.refresh_style()

    def on_style_changed(self, category: DockStyleCategory, changes: dict) -> None:
        """Debounce refreshes so several categories changing in one frame
        (e.g. a full theme apply) rebuild the widget only once."""
        if not getattr(self, "_refresh_queued", False):
            self._refresh_queued = True
            if isinstance(self, QObject):
                # Bind the timer to this widget. Without a context object the
                # pending shot outlives the C++ widget, and _do_refresh then
                # runs against freed memory on whatever processes events next.
                # The RuntimeError guard below does not save it: shiboken only
                # invalidates the wrapper when it owns the deletion, and a
                # widget deleted as a child of a destroyed parent is not that
                # case — the call is a straight use-after-free. Qt drops a
                # context-bound single shot when the context is destroyed.
                QTimer.singleShot(0, self, self._do_refresh)
            else:
                QTimer.singleShot(0, self._do_refresh)

    def _do_refresh(self) -> None:
        self._refresh_queued = False
        try:
            self.refresh_style()
        except RuntimeError:
            # Underlying C++ widget already deleted; nothing to restyle.
            pass

    def refresh_style(self) -> None:  # pragma: no cover - overridden
        raise NotImplementedError(
            f"{type(self).__name__} must implement refresh_style()"
        )
