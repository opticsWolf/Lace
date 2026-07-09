# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0

theme_manager — OS-Aware Auto Theme Switcher
============================================
Automatically monitors Windows registry / Qt palette changes and switches
between default dark/light themes or user-defined stylesheet overrides.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Any

from PySide6.QtCore import QObject, QSettings, QEvent, Signal, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)


class ThemeManager(QObject):
    """
    OS-Aware Auto Theme Switcher.

    Monitors system theme changes (e.g., Windows Dark/Light mode flips, Qt 6.5+
    colorSchemeChanged, or Qt PaletteChange events) and applies the corresponding
    dark/light theme to the application or target window.
    """
    theme_changed = Signal(str, bool)  # (applied_theme, is_dark_mode)

    def __init__(
        self,
        app_instance: Optional[Any] = None,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.app = app_instance
        # User-defined theme variables (paths to your QSS files or Lace theme names)
        self.user_light_theme = "light"
        self.user_dark_theme = "dark"
        self.auto_mode_enabled = True
        self._last_applied_theme: Optional[str] = None

    def is_windows_dark_mode(self) -> bool:
        """Checks if OS Dark Mode is active via Qt 6.5+ styleHints, Windows registry, or palette fallback."""
        # Check modern Qt 6.5+ styleHints colorScheme (macOS, Windows 11, Linux Portal)
        app = QGuiApplication.instance()
        if app is not None and hasattr(app, "styleHints"):
            hints = app.styleHints()
            if hasattr(hints, "colorScheme"):
                scheme = hints.colorScheme()
                if hasattr(Qt, "ColorScheme"):
                    if scheme == Qt.ColorScheme.Dark:
                        return True
                    if scheme == Qt.ColorScheme.Light:
                        return False

        if sys.platform == "win32":
            try:
                settings = QSettings(
                    r"HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                    QSettings.Format.NativeFormat,
                )
                val = settings.value("AppsUseLightTheme")
                if val is not None:
                    return int(val) == 0
            except (ValueError, TypeError, Exception) as e:
                logger.debug(f"Failed to read AppsUseLightTheme from Windows registry: {e}")

        # Fallback if registry check is unavailable or not on Windows
        target = self.app or QApplication.instance()
        if target is not None and hasattr(target, "palette"):
            pal = target.palette()
            window_color = pal.color(pal.ColorRole.Window)
            return window_color.lightness() < 128
        return False

    def sync_theme(self, force: bool = False) -> bool:
        """
        Synchronizes the application theme based on system settings and user preferences.

        Args:
            force: If True, forces re-application even if the target theme matches
                   the previously applied theme.

        Returns:
            bool: True if a theme or stylesheet was successfully applied.
        """
        if not self.auto_mode_enabled:
            return False

        theme_to_apply = (
            self.user_dark_theme
            if self.is_windows_dark_mode()
            else self.user_light_theme
        )
        if not theme_to_apply:
            return False

        if not force and self._last_applied_theme == theme_to_apply:
            return True

        applied = False

        # 1. Check if theme_to_apply is an existing QSS stylesheet file on disk
        path = Path(theme_to_apply)
        is_file = False
        try:
            is_file = path.is_file()
        except (ValueError, OSError):
            pass

        if is_file and (str(theme_to_apply).endswith((".qss", ".css")) or not str(theme_to_apply).isalnum()):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    qss_content = f.read()
                target = self.app or QApplication.instance()
                if target is not None and hasattr(target, "setStyleSheet"):
                    target.setStyleSheet(qss_content)
                    applied = True
            except Exception as e:
                logger.error(f"Failed to load theme QSS file '{theme_to_apply}': {e}")

        # 2. Check if theme_to_apply is a registered Lace theme name (e.g., "dark", "light")
        if not applied:
            try:
                from .dock_custom_theme import DOCK_THEMES
                from .dock_style_manager import apply_dock_theme

                if theme_to_apply in DOCK_THEMES:
                    if apply_dock_theme(theme_to_apply):
                        applied = True
            except ImportError:
                pass

        # 3. If neither file nor dock theme, check if it's raw QSS string or generic stylesheet file
        if not applied and is_file:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    qss_content = f.read()
                target = self.app or QApplication.instance()
                if target is not None and hasattr(target, "setStyleSheet"):
                    target.setStyleSheet(qss_content)
                    applied = True
            except Exception as e:
                logger.error(f"Failed to load theme file '{theme_to_apply}': {e}")
        elif not applied:
            target = self.app or QApplication.instance()
            if target is not None and hasattr(target, "setStyleSheet"):
                if "{" in str(theme_to_apply) and "}" in str(theme_to_apply):
                    target.setStyleSheet(str(theme_to_apply))
                    applied = True

        if applied:
            self._last_applied_theme = theme_to_apply
            self.theme_changed.emit(theme_to_apply, self.is_windows_dark_mode())
        else:
            logger.warning(
                f"Theme '{theme_to_apply}' could not be applied (not in DOCK_THEMES or not a valid QSS file)."
            )

        return applied

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """
        Event filter hook to automatically intercept QEvent.Type.PaletteChange
        when installed on QApplication or QMainWindow.
        """
        if event.type() == QEvent.Type.PaletteChange:
            self.sync_theme()
        return super().eventFilter(obj, event)

    def _on_color_scheme_changed(self, *args: Any) -> None:
        """Slot invoked when Qt 6.5+ styleHints colorSchemeChanged emits."""
        self.sync_theme()

    def install_listener(self, target: Optional[QObject] = None) -> None:
        """
        Installs this ThemeManager as an event filter on target (or self.app or
        QApplication.instance()) and connects to Qt 6.5+ colorSchemeChanged.
        """
        obj = target or self.app or QApplication.instance()
        if obj is not None and isinstance(obj, QObject):
            obj.installEventFilter(self)

        app = QGuiApplication.instance()
        if app is not None and hasattr(app, "styleHints"):
            hints = app.styleHints()
            if hasattr(hints, "colorSchemeChanged"):
                try:
                    hints.colorSchemeChanged.connect(self._on_color_scheme_changed)
                except Exception as e:
                    logger.debug(f"Could not connect to colorSchemeChanged: {e}")

    def remove_listener(self, target: Optional[QObject] = None) -> None:
        """Removes the event filter listener and colorSchemeChanged signal."""
        obj = target or self.app or QApplication.instance()
        if obj is not None and isinstance(obj, QObject):
            obj.removeEventFilter(self)

        app = QGuiApplication.instance()
        if app is not None and hasattr(app, "styleHints"):
            hints = app.styleHints()
            if hasattr(hints, "colorSchemeChanged"):
                try:
                    hints.colorSchemeChanged.disconnect(self._on_color_scheme_changed)
                except Exception:
                    pass


__all__ = ["ThemeManager"]
