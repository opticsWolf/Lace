# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.

"""Frameless window wrappers around PySideSix-Frameless-Window.

Provides ``FramelessLaceMainWindow`` and ``FramelessLaceWindow`` subclasses
that inherit directly from the platform-specific frameless classes provided
by ``qframelesswindow``.

On Windows this resolves to ``WindowsFramelessMainWindow`` /
``WindowsFramelessWindow``, on macOS to ``MacFramelessMainWindow`` /
``MacFramelessWindow``, and on Linux to ``LinuxFramelessMainWindow`` /
``LinuxFramelessWindow``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QMenuBar, QVBoxLayout, QWidget
from qframelesswindow import FramelessMainWindow, FramelessWindow

if TYPE_CHECKING:
    from .dock_theme import DockStyleCategory


def _color_hex(col, alpha: Optional[float] = None) -> str:
    """Convert a QColor (or anything with red/green/blue/alpha) to '#rrggbb'."""
    if col is None:
        return "transparent"
    r, g, b = col.red(), col.green(), col.blue()
    a = col.alpha() if alpha is None else int(alpha * 255)
    if a < 255:
        return f"#{r:02x}{g:02x}{b:02x}{a:02x}"
    return f"#{r:02x}{g:02x}{b:02x}"


# ── Frameless MainWindow ───────────────────────────────────────────────

class FramelessLaceMainWindow(FramelessMainWindow):
    """A frameless main window that uses PySideSix-Frameless-Window for
    custom title bars and non-client area handling.

    Inherits from the platform-specific ``FramelessMainWindow`` which
    already provides:
    - ``Qt.FramelessWindowHint`` window flag
    - Custom ``titleBar`` widget with min/max/close buttons
    - ``nativeEvent`` handler for resize borders (WM_NCHITTEST)
    - DWM shadow and window animation effects (Windows)

    Uses a stacked container (title bar + optional menu bar) as the
    QMainWindow menu widget so the central widget is positioned below
    both.  Subscribes to ``DockStyleManager`` for automatic theme
    colour updates on the title bar and menu bar.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._menu_bar: Optional[QMenuBar] = None
        self._menu_bar_container: Optional[QWidget] = None
        # Integrate title bar into QMainWindow layout so the central
        # widget is positioned below it.
        self.setMenuWidget(self.titleBar)

    # -- title bar --------------------------------------------------------

    def setTitleBar(self, titleBar: QWidget) -> None:
        """Replace the title bar and update the QMainWindow menu widget.

        If a menu bar has already been created, rebuild the stacked
        container so the new title bar sits above the existing menu bar.
        """
        # Preserve existing menu bar before super() potentially resets
        # references.
        saved_menu_bar = self._menu_bar
        super().setTitleBar(titleBar)

        if saved_menu_bar is not None:
            # Rebuild stacked container with the new title bar.
            self._build_stacked_container(saved_menu_bar)
        else:
            self.setMenuWidget(self.titleBar)

        # Re-apply current theme colours to the new title bar.
        self._apply_titlebar_theme()

    # -- menu bar ---------------------------------------------------------

    def _build_stacked_container(self, menu_bar: QMenuBar) -> None:
        """Create (or recreate) a stacked widget with title bar + menu bar
        and set it as the QMainWindow menu widget."""
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.titleBar)
        layout.addWidget(menu_bar)

        self.setMenuWidget(container)
        self._menu_bar_container = container

    def menuBar(self) -> QMenuBar:
        """Return a separate menu bar positioned below the title bar.

        QMainWindow.menuBar() auto-creates a default QMenuBar and sets
        it as the menu widget, which would replace our custom title bar.
        Instead, we create a stacked container (title bar + menu bar)
        and set it as the menu widget so both remain visible.
        """
        if self._menu_bar is not None:
            return self._menu_bar

        menu_bar = QMenuBar(self)
        menu_bar.setStyleSheet("border: none;")
        self._menu_bar = menu_bar
        self._build_stacked_container(menu_bar)
        return menu_bar

    def setCentralWidget(self, widget: QWidget) -> None:
        """Override to keep the title bar above the central widget."""
        super().setCentralWidget(widget)
        self.titleBar.raise_()

    # -- theme integration ------------------------------------------------

    def on_style_changed(
        self, category: "DockStyleCategory", changes: Dict[str, Any]
    ) -> None:
        """Called by ``DockStyleManager`` when subscribed categories change."""
        self._apply_titlebar_theme()

    def _apply_titlebar_theme(self) -> None:
        """Apply current dock theme colours to the title bar and menu bar.

        Reads from ``DockStyleCategory.TITLE_BAR`` for the title bar and
        ``DockStyleCategory.CORE`` / ``PANEL`` for the menu bar.
        """
        try:
            from .dock_style_manager import (
                DockStyleCategory,
                get_dock_style_manager,
            )
        except ImportError:
            return  # DockStyleManager not available

        sm = get_dock_style_manager()

        # -- Title bar tokens --
        tb = self.titleBar
        bg = sm.get(DockStyleCategory.TITLE_BAR, "bg_normal")
        text_col = sm.get(DockStyleCategory.TITLE_BAR, "text_normal")
        btn_col = sm.get(DockStyleCategory.TITLE_BAR, "button_color")
        btn_hover = sm.get(DockStyleCategory.TITLE_BAR, "button_hover_bg")
        btn_disable = sm.get(DockStyleCategory.TITLE_BAR, "button_disable_clr")
        btn_size = sm.get(DockStyleCategory.TITLE_BAR, "button_size", 18)
        btn_icon = sm.get(DockStyleCategory.TITLE_BAR, "button_icon_size", 16)
        btn_radius = sm.get(DockStyleCategory.TITLE_BAR, "button_corner_radius", 3)
        font_family = sm.get(DockStyleCategory.TITLE_BAR, "font_family", "Segoe UI")
        font_size = sm.get(DockStyleCategory.TITLE_BAR, "font_size", 10)
        font_weight = sm.get(DockStyleCategory.TITLE_BAR, "font_weight", "normal")
        height = sm.get(DockStyleCategory.TITLE_BAR, "height", 30)

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

        # The StandardTitleBar sets its own stylesheet on titleLabel which
        # overrides the parent widget's QSS.  Apply the theme directly.
        if hasattr(tb, 'titleLabel'):
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
        # _normalColor / _hoverColor / _pressedColor attributes.  Set them
        # directly so they match the theme.
        from qframelesswindow.titlebar import TitleBarButton
        for btn in tb.findChildren(TitleBarButton):
            if btn._state is not None:
                if btn_col:
                    btn._normalColor = QColor(btn_col)
                if btn_hover:
                    btn._hoverColor = QColor(btn_hover)
                # Pressed colour: blend hover with background for depth
                if btn_hover and bg:
                    pressed = QColor(btn_hover)
                    pressed.setAlpha(int(pressed.alpha() * 1.5))
                    btn._pressedColor = pressed
                if btn_disable:
                    btn._disableColor = QColor(btn_disable)
                btn.update()

        # -- Menu bar tokens --
        if self._menu_bar is not None:
            panel_bg = sm.get(DockStyleCategory.PANEL, "bg_normal")
            core_text = sm.get(DockStyleCategory.CORE, "text_color")
            panel_text = sm.get(DockStyleCategory.PANEL, "text_color")
            accent = sm.get(DockStyleCategory.CORE, "accent_color")
            border_col = sm.get(DockStyleCategory.CORE, "border_color")

            panel_hex = _color_hex(panel_bg) if panel_bg else bg_hex
            mbar_text = _color_hex(panel_text or core_text)
            accent_hex = _color_hex(accent) if accent else "#0078d4"
            border_hex = _color_hex(border_col, alpha=0.3) if border_col else "transparent"

            mbar_qss = f"""
                QMenuBar {{
                    background: {panel_hex};
                    color: {mbar_text};
                    border: none;
                    border-bottom: 1px solid {border_hex};
                    font-family: {font_family};
                    font-size: {font_size}px;
                }}
                QMenuBar::item {{
                    background: transparent;
                    padding: 4px 8px;
                }}
                QMenuBar::item:selected {{
                    background: {accent_hex};
                }}
                QMenuBar::item:pressed {{
                    background: {accent_hex};
                }}
                QMenu {{
                    background: {panel_hex};
                    color: {mbar_text};
                    border: 1px solid {border_hex};
                    padding: 2px;
                }}
                QMenu::item {{
                    padding: 4px 32px 4px 8px;
                }}
                QMenu::item:selected {{
                    background: {accent_hex};
                }}
            """.strip()

            self._menu_bar.setStyleSheet(mbar_qss)

    # -- DockStyleManager registration (called by DockManager or demo) --

    def _register_titlebar_theme(self) -> None:
        """Subscribe to DockStyleManager so the title bar updates on theme changes.

        Call this once from DockManager or the application's setup code.
        """
        try:
            from .dock_style_manager import (
                DockStyleCategory,
                get_dock_style_manager,
            )
        except ImportError:
            return

        sm = get_dock_style_manager()
        sm.register(self, DockStyleCategory.TITLE_BAR)
        sm.register(self, DockStyleCategory.CORE)
        sm.register(self, DockStyleCategory.PANEL)
        self._apply_titlebar_theme()


# ── Frameless Floating Window ──────────────────────────────────────────

class FramelessLaceWindow(FramelessWindow):
    """A frameless floating window that uses PySideSix-Frameless-Window
    for custom title bars on floating dock containers.

    Inherits from the platform-specific ``FramelessWindow`` which
    provides the same frameless infrastructure as
    ``FramelessLaceMainWindow`` but for plain ``QWidget`` windows.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)


__all__ = [
    "FramelessLaceMainWindow",
    "FramelessLaceWindow",
]
