# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.

"""Theming engine for PySideSix-Frameless-Window title bars.

:class:`FramelessTitleBarStyler` is a :class:`DockStyled` consumer that
applies dock-theme colours to a ``qframelesswindow`` title bar and an
optional ``QMenuBar``.  It handles the quirks of the frameless library:

* ``StandardTitleBar`` applies its own stylesheet to ``titleLabel``,
  so we override it with a higher-specificity rule.
* Min/max/close buttons use custom painting via ``_normalColor`` /
  ``_hoverColor`` / ``_pressedColor`` and ``_normalBgColor`` /
  ``_hoverBgColor`` / ``_pressedBgColor`` attributes, which must be
  set directly instead of through QSS.
"""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QMenuBar, QWidget

from lace.dock_theme import DockStyleCategory


def _color_hex(col, alpha: Optional[float] = None) -> str:
    """Convert a QColor (or anything with red/green/blue/alpha) to '#rrggbb'."""
    if col is None:
        return "transparent"
    r, g, b = col.red(), col.green(), col.blue()
    a = col.alpha() if alpha is None else int(alpha * 255)
    if a < 255:
        return f"#{r:02x}{g:02x}{b:02x}{a:02x}"
    return f"#{r:02x}{g:02x}{b:02x}"


class FramelessTitleBarStyler:
    """Styles a ``qframelesswindow`` title bar and optional menu bar from
    the dock theme engine.

    Uses the same subscription pattern as :class:`DockStyled` but without
    inheriting from it (this class is not itself a Qt widget).

    Parameters
    ----------
    title_bar:
        The ``qframelesswindow`` title bar widget (``StandardTitleBar``,
        ``TitleBar``, or a custom replacement).
    menu_bar:
        Optional ``QMenuBar`` positioned below the title bar.  May be
        ``None`` or set later via :attr:`menu_bar`.  Additional menu bars
        can be registered with :meth:`add_menu_bar`.
    parent:
        Qt parent (typically the main window, used for lifecycle).
    """

    _STYLE_CATEGORIES = (
        DockStyleCategory.TITLE_BAR,
        DockStyleCategory.CORE,
        DockStyleCategory.PANEL,
    )

    def __init__(
        self,
        title_bar: QWidget,
        menu_bar: Optional[QMenuBar] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        from lace.dock_style_manager import get_dock_style_manager

        self._parent = parent
        self._title_bar = title_bar
        self._menu_bars: List[QMenuBar] = [menu_bar] if menu_bar is not None else []
        self._style_mgr = get_dock_style_manager()
        self._refresh_queued = False
        # Optional callback invoked after every refresh_style() pass so hosts
        # can re-apply state that styling would otherwise clobber (e.g. a
        # floating container's disabled close-button colour).
        self._after_refresh = None

        # Register with DockStyleManager and apply initial style.
        for category in self._STYLE_CATEGORIES:
            self._style_mgr.register(self, category)
        self.refresh_style()

    def on_style_changed(self, category: DockStyleCategory, changes: dict) -> None:
        """Debounce refreshes so several categories changing in one frame
        rebuild the styler only once."""
        if not self._refresh_queued:
            self._refresh_queued = True
            QTimer.singleShot(0, self._do_refresh)

    def _do_refresh(self) -> None:
        self._refresh_queued = False
        try:
            self.refresh_style()
        except RuntimeError:
            # Underlying C++ widget already deleted; nothing to restyle.
            pass

    # -- public API -------------------------------------------------------

    @property
    def title_bar(self) -> QWidget:
        """The title bar widget being styled."""
        return self._title_bar

    @title_bar.setter
    def title_bar(self, tb: QWidget) -> None:
        """Replace the title bar and re-apply the current theme."""
        self._title_bar = tb
        self.refresh_style()

    @property
    def menu_bar(self) -> Optional[QMenuBar]:
        """The first registered menu bar, or ``None`` if none are registered.

        This property exists for backward compatibility with callers that
        only need a single menu bar.
        """
        return self._menu_bars[0] if self._menu_bars else None

    @menu_bar.setter
    def menu_bar(self, mb: Optional[QMenuBar]) -> None:
        """Set or clear the menu bar and re-apply the current theme.

        Setting this replaces the entire list of registered menu bars with
        a single entry.  Use :meth:`add_menu_bar` to keep existing entries.
        """
        self._menu_bars = [mb] if mb is not None else []
        self.refresh_style()

    def add_menu_bar(self, menu_bar: QMenuBar) -> None:
        """Register an additional menu bar to receive dock-theme styling."""
        if menu_bar not in self._menu_bars:
            self._menu_bars.append(menu_bar)
            self.refresh_style()

    def remove_menu_bar(self, menu_bar: QMenuBar) -> None:
        """Unregister a menu bar from dock-theme styling."""
        if menu_bar in self._menu_bars:
            self._menu_bars.remove(menu_bar)
            self.refresh_style()

    # -- DockStyled implementation ----------------------------------------

    def refresh_style(self) -> None:
        """Apply current dock theme colours to the title bar and menu bar."""
        sm = self._style_mgr

        # -- Title bar tokens --
        tb = self._title_bar
        # StandardTitleBar is a plain QWidget subclass; Qt only paints
        # QSS backgrounds on such widgets when WA_StyledBackground is set.
        tb.setAttribute(Qt.WA_StyledBackground, True)
        # Match the sidebar strip (SIDEBAR bg_color = theme base) so the
        # title bar and menu bar read as the same chrome surface as the
        # sidebars.  Falls back to the title-bar token if a custom theme
        # omits the sidebar palette.
        bg = sm.get(DockStyleCategory.SIDEBAR, "bg_color")
        if bg is None:
            bg = sm.get(DockStyleCategory.TITLE_BAR, "bg_normal")
        text_col = sm.get(DockStyleCategory.TITLE_BAR, "text_normal")
        btn_col = sm.get(DockStyleCategory.TITLE_BAR, "button_color")
        btn_hover = sm.get(DockStyleCategory.TITLE_BAR, "button_hover_bg")
        btn_disable = sm.get(DockStyleCategory.TITLE_BAR, "button_disable_clr")
        btn_size = sm.get(DockStyleCategory.TITLE_BAR, "button_size", 18)
        btn_icon = sm.get(DockStyleCategory.TITLE_BAR, "button_icon_size", 16)
        btn_radius = sm.get(DockStyleCategory.TITLE_BAR, "button_corner_radius", 3)
        font_family = sm.get(DockStyleCategory.TITLE_BAR, "font_family", "Segoe UI")
        font_size = sm.get(DockStyleCategory.TITLE_BAR, "font_size", 13)
        font_weight = sm.get(DockStyleCategory.TITLE_BAR, "font_weight", "normal")

        # Map string font weights
        if isinstance(font_weight, str):
            font_weight = font_weight.capitalize()

        bg_hex = _color_hex(bg) if bg else "transparent"
        text_hex = _color_hex(text_col) if text_col else "#cccccc"
        btn_hex = _color_hex(btn_col) if btn_col else "#cccccc"
        btn_hover_hex = _color_hex(btn_hover) if btn_hover else "#555555"
        btn_disable_hex = _color_hex(btn_disable) if btn_disable else "#555555"

        titlebar_qss = f"""
            QWidget#titleBar,
            .TitleBar,
            .StandardTitleBar {{
                background: {bg_hex};
                border: none;
            }}
            QLabel#titleLabel {{
                color: {text_hex};
                font-family: {font_family};
                font-size: {font_size}px;
                font-weight: {font_weight};
            }}
            QLabel#iconLabel {{
                background: transparent;
            }}
            QPushButton {{
                background: transparent;
                color: {btn_hex};
                border: none;
                border-radius: {btn_radius}px;
                min-width: {btn_size}px;
                min-height: {btn_size}px;
                max-width: {btn_size}px;
                max-height: {btn_size}px;
            }}
            QPushButton:hover {{
                background: {btn_hover_hex};
            }}
            QPushButton:disabled {{
                color: {btn_disable_hex};
            }}
            QPushButton::icon {{
                width: {btn_icon}px;
                height: {btn_icon}px;
            }}
        """.strip()

        tb.setStyleSheet(titlebar_qss)

        # StandardTitleBar sets its own stylesheet on titleLabel which
        # overrides the parent widget's QSS.  Apply the theme directly.
        if hasattr(tb, "titleLabel"):
            tl = tb.titleLabel
            tl_palette = tl.palette()
            if text_col:
                tl_palette.setColor(tl_palette.ColorRole.Text, QColor(text_col))
            tl.setPalette(tl_palette)
            tl.setStyleSheet(f"""
                QLabel {{
                    background: transparent;
                    font: {font_weight} {font_size}px {font_family};
                    padding: 0 4px;
                    color: {text_hex};
                }}
            """)

        # Title bar buttons (min/max/close) use custom painting with
        # _normalColor / _hoverColor / _pressedColor for icon colours
        # and _normalBgColor / _hoverBgColor / _pressedBgColor for
        # background colours.  Set them directly so they match the theme.
        from qframelesswindow.titlebar import TitleBarButton, CloseButton
        for btn in tb.findChildren(TitleBarButton):
            if isinstance(btn, CloseButton):
                # Keep the classic system close colour (qframeless defaults:
                # red hover/pressed background with a white icon).  Only the
                # normal-state icon follows the theme so it stays visible on
                # both light and dark title bars.
                if btn_col:
                    btn._normalColor = QColor(btn_col)
                btn._normalBgColor = QColor(0, 0, 0, 0)
                btn.update()
                continue
            # Icon colours: use button_color for all states
            if btn_col:
                btn._normalColor = QColor(btn_col)
                btn._hoverColor = QColor(btn_col)
                btn._pressedColor = QColor(btn_col)
            # Background colours: transparent normal, theme hover_bg on hover
            btn._normalBgColor = QColor(0, 0, 0, 0)
            if btn_hover:
                btn._hoverBgColor = QColor(btn_hover)
                pressed_bg = QColor(btn_hover)
                pressed_bg.setAlpha(min(255, int(pressed_bg.alpha() * 1.5)))
                btn._pressedBgColor = pressed_bg
            if btn_disable:
                btn._disableColor = QColor(btn_disable)
            btn.update()

        # -- Menu bar styling (minimal) --
        #
        # Same approach as demo_app.py: a plain QMenuBar whose only
        # stylesheet rule is "no border" (Fusion draws a 1px bottom
        # shadow).  The background is pinned to the sidebar colour so it
        # matches the title bar above; text and hover/selected items
        # follow the palette.  Note: any QSS on the menu bar makes Qt
        # ignore the palette Window role, hence the explicit background.
        for menu_bar in self._menu_bars:
            if menu_bar is None:
                continue
            menu_bar.setStyleSheet(
                f"QMenuBar {{ background: {bg_hex}; border: none; }}"
            )

            # QSS polish snapshots a stale palette into the widget, so
            # set it explicitly from the current theme to keep
            # hover/pressed item colours from lagging one theme behind.
            from lace.dock_theme import build_dock_palette

            palette = build_dock_palette(is_panel=False)
            if bg is not None:
                palette.setColor(QPalette.ColorRole.Window, QColor(bg_hex))
            menu_bar.setPalette(palette)

        # Let the host re-apply anything this styling pass overwrote.
        after = getattr(self, "_after_refresh", None)
        if after is not None:
            try:
                after()
            except (RuntimeError, TypeError):
                pass


__all__ = [
    "FramelessTitleBarStyler",
]
