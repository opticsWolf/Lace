# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


import logging
import sys
from pathlib import Path
from typing import Optional, Union, Any

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
        default_theme_path: Optional[Union[str, Path]] = None,
    ):
        super().__init__(parent)
        self.app = app_instance
        # User-defined theme variables (paths to your QSS/JSON files or Lace theme names)
        self.user_light_theme = "light"
        self.user_dark_theme = "dark"
        self.auto_mode_enabled = True
        # Default location to load theme files from when sync_theme() is called
        # without an explicit ``path``. May point to a single theme file
        # (.json / .qss / .css) or to a directory containing
        # "<theme_name>.json" / ".qss" / ".css" files.
        self.default_theme_path = (
            Path(default_theme_path) if default_theme_path is not None else None
        )
        self._last_applied_theme: Optional[str] = None

    @property
    def default_theme_path(self) -> Optional[Path]:
        """Default theme file / directory, normalized to ``Path``."""
        return self._default_theme_path

    @default_theme_path.setter
    def default_theme_path(self, value: Optional[Union[str, Path]]) -> None:
        self._default_theme_path = Path(value) if value is not None else None

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

    def sync_theme(
        self,
        force: bool = False,
        path: Optional[Union[str, Path]] = None,
    ) -> bool:
        """
        Synchronizes the application theme based on system settings and user preferences.

        Args:
            force: If True, forces re-application even if the target theme matches
                   the previously applied theme.
            path:  Optional explicit theme file to load from (JSON, QSS or CSS).
                   Overrides the auto-resolved source. When omitted, the theme is
                   resolved from, in order:

                   1. ``user_dark_theme`` / ``user_light_theme`` if the value is
                      itself an existing file path,
                   2. ``default_theme_path`` (a single file, or a directory of
                      ``<theme_name>.json|.qss|.css`` files),
                   3. a registered Lace theme name (e.g. ``"dark"``), or a raw
                      QSS string.

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

        if not force and path is None and self._last_applied_theme == theme_to_apply:
            return True

        applied = False
        resolved_path = self._resolve_theme_path(path, theme_to_apply)

        # 1. File-based theme (explicit path, configured path, or default path)
        if resolved_path is not None:
            if resolved_path.suffix.lower() == ".json":
                applied = self._apply_json_theme(resolved_path)
            else:
                applied = self._apply_stylesheet_file(resolved_path)

        # 2. Registered Lace theme name (e.g. "dark", "light", "tokyo_night")
        if not applied and path is None:
            try:
                from lace.dock_custom_theme import DOCK_THEMES
                from lace.dock_style_manager import apply_dock_theme

                if theme_to_apply in DOCK_THEMES:
                    if apply_dock_theme(theme_to_apply):
                        applied = True
            except ImportError:
                pass

        # 3. Raw QSS string fallback
        if not applied and path is None:
            target = self.app or QApplication.instance()
            if target is not None and hasattr(target, "setStyleSheet"):
                if "{" in str(theme_to_apply) and "}" in str(theme_to_apply):
                    target.setStyleSheet(str(theme_to_apply))
                    applied = True

        if applied:
            self._last_applied_theme = (
                theme_to_apply if path is None else str(resolved_path)
            )
            self.theme_changed.emit(theme_to_apply, self.is_windows_dark_mode())
        else:
            logger.warning(
                f"Theme '{theme_to_apply}' could not be applied "
                f"(not in DOCK_THEMES, not a valid QSS file, and no loadable theme "
                f"file found at default_theme_path={self.default_theme_path!r})."
            )

        return applied

    # ---------------------------------------------------------------------------
    # Theme file resolution & loading
    # ---------------------------------------------------------------------------
    def _resolve_theme_path(
        self,
        explicit_path: Optional[Union[str, Path]],
        theme_to_apply: str,
    ) -> Optional[Path]:
        """Resolve the theme file to load.

        Priority: explicit ``path`` argument, then ``theme_to_apply`` itself if it
        names an existing file, then ``default_theme_path`` (a single theme file,
        or ``<dir>/<theme_name>.json|.qss|.css``). Returns ``None`` when no file
        applies.
        """
        # 1. Explicit path argument wins
        if explicit_path is not None:
            p = Path(explicit_path)
            return p if p.is_file() else None

        # 2. theme_to_apply is already a file path
        try:
            p = Path(theme_to_apply)
            if p.is_file():
                return p
        except (ValueError, OSError):
            pass

        # 3. Default theme path (single file, or a directory of theme files)
        if self.default_theme_path is not None:
            base = self.default_theme_path
            if base.is_file():
                return base
            if base.is_dir():
                for suffix in (".json", ".qss", ".css"):
                    candidate = base / f"{theme_to_apply}{suffix}"
                    if candidate.is_file():
                        return candidate
        return None

    def _apply_stylesheet_file(self, path: Path) -> bool:
        """Load a .qss/.css (or any text) theme file and apply it as a stylesheet."""
        try:
            qss_content = path.read_text(encoding="utf-8")
        except OSError as e:
            logger.error(f"Failed to read theme file '{path}': {e}")
            return False
        target = self.app or QApplication.instance()
        if target is None or not hasattr(target, "setStyleSheet"):
            return False
        try:
            target.setStyleSheet(qss_content)
        except Exception as e:
            logger.error(f"Failed to apply theme file '{path}': {e}")
            return False
        return True

    def _apply_json_theme(self, path: Path) -> bool:
        """Load a JSON theme file with pydantic validation and apply it."""
        from lace.theme_models import ThemeJson

        try:
            theme = ThemeJson.load(path)
            theme_data = theme.build_theme_dict()
        except Exception as e:
            logger.error(f"Failed to load JSON theme '{path}': {e}")
            return False

        from lace.dock_style_manager import get_dock_style_manager

        try:
            get_dock_style_manager().apply_theme_dict(theme_data)
        except Exception as e:
            logger.error(f"Failed to apply JSON theme '{path}': {e}")
            return False

        logger.info(f"Applied JSON theme '{theme.name or path.stem}' from {path}")
        return True

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
