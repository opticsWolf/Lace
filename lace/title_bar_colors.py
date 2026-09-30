# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.

"""One source for a title bar's colours.

The custom title bar (:class:`FramelessTitleBarStyler`) and the native window
frame (:mod:`lace.native_frame`) both read the theme through
:func:`title_bar_colors`, so the two kinds of title bar cannot drift apart.

The token contract:

- background: ``SIDEBAR.bg_color``, falling back to ``TITLE_BAR.bg_normal``,
  so the title bar reads as the same chrome surface as the sidebars;
- text: ``TITLE_BAR.text_normal``;
- border: ``CORE.border_color`` where the theme draws a visible card outline
  (opaque colour, non-zero ``CORE.border_width``), otherwise none.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PySide6.QtGui import QColor

from lace.dock_theme import DockStyleCategory, to_qcolor

#: Inactive caption text: the text colour at this weight over the background.
INACTIVE_TEXT_ALPHA = 0.6

_FALLBACK_BG = QColor(37, 37, 38)
_FALLBACK_TEXT = QColor(204, 204, 204)


@dataclass(frozen=True)
class TitleBarColors:
    """Resolved title-bar colours for the active theme."""

    #: The bar's fill, as the theme gives it (may carry alpha).
    background: QColor
    #: Title text.
    text: QColor
    #: Title text of an inactive window, opaque.
    text_inactive: QColor
    #: The window's outline, opaque; None where the theme draws no outline.
    border: Optional[QColor]
    #: Whether the bar is dark (drives the OS dark-mode frame).
    is_dark: bool

    def opaque_background(self, backdrop: Optional[QColor] = None) -> QColor:
        """The background composited over *backdrop* (default black), for
        consumers that cannot draw alpha, such as the DWM caption."""
        return _over(self.background, backdrop or QColor(0, 0, 0))


def _over(top: QColor, bottom: QColor) -> QColor:
    """*top* composited over opaque *bottom*."""
    a = top.alphaF()
    return QColor.fromRgbF(
        top.redF() * a + bottom.redF() * (1 - a),
        top.greenF() * a + bottom.greenF() * (1 - a),
        top.blueF() * a + bottom.blueF() * (1 - a),
        1.0,
    )


def _token(sm, category: DockStyleCategory, key: str) -> Optional[QColor]:
    value = sm.get(category, key)
    if value is None:
        return None
    return QColor(value) if isinstance(value, QColor) else to_qcolor(value)


def title_bar_colors(sm=None) -> TitleBarColors:
    """The active theme's title-bar colours.

    *sm* defaults to the process-wide :class:`DockStyleManager`.
    """
    if sm is None:
        from lace.dock_style_manager import get_dock_style_manager
        sm = get_dock_style_manager()

    background = (_token(sm, DockStyleCategory.SIDEBAR, "bg_color")
                  or _token(sm, DockStyleCategory.TITLE_BAR, "bg_normal")
                  or QColor(_FALLBACK_BG))
    text = _token(sm, DockStyleCategory.TITLE_BAR, "text_normal") or QColor(_FALLBACK_TEXT)

    canvas = _token(sm, DockStyleCategory.CORE, "canvas_bg") or QColor(0, 0, 0)
    opaque_bg = _over(background, _over(canvas, QColor(0, 0, 0)))

    faded = QColor(text)
    faded.setAlphaF(text.alphaF() * INACTIVE_TEXT_ALPHA)
    text_inactive = _over(faded, opaque_bg)

    border = None
    border_color = _token(sm, DockStyleCategory.CORE, "border_color")
    border_width = sm.get(DockStyleCategory.CORE, "border_width", 0) or 0
    if border_color is not None and border_color.alpha() > 0 and border_width > 0:
        border = _over(border_color, opaque_bg)

    return TitleBarColors(
        background=background,
        text=text,
        text_inactive=text_inactive,
        border=border,
        is_dark=opaque_bg.lightnessF() < 0.5,
    )


__all__ = ["TitleBarColors", "title_bar_colors", "INACTIVE_TEXT_ALPHA"]
