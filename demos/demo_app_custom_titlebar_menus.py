# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.

"""Demo: custom title bars for the main window and floating dock containers.

This application shows how to:

* Use a custom main-window title bar that embeds a ``QMenuBar`` directly
  inside the frameless chrome instead of below it.
* Use a different custom title bar for floating dock containers that embeds
  a search ``QLineEdit`` in the chrome.
* Configure both title bars through :class:`.dock_manager.DockManager` so
  floating containers created by the docking system pick up the search bar
  automatically.

Run with:

    python -m demos.demo_app_custom_titlebar_menus
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QSizePolicy,
    QTextEdit,
    QWidget,
)

from lace import (
    DockManager,
    DockWidget,
    DockWidgetArea,
    DockWidgetFeature,
    DockThemeBridge,
    TitleBarMode,
    apply_dock_theme,
    get_icon_provider,
)
from lace.dock_styled import DockStyled
from lace.dock_theme import DockStyleCategory
from lace.frameless_titlebar import _color_hex
from lace.frameless_window import FramelessLaceMainWindow, LaceStandardTitleBar


# ── Custom main-window title bar with embedded menu bar ──────────────

class MenuEmbeddedTitleBar(LaceStandardTitleBar, DockStyled):
    """Standard Lace title bar with a ``QMenuBar`` embedded in the layout.

    The menu bar sits between the window title and the window-control
    buttons, giving a VS Code / browser-style unified title bar.  It styles
    itself via :class:`DockStyled` so the embedded menu bar stays in sync
    with the active dock theme.
    """

    STYLE_CATEGORIES = (
        DockStyleCategory.TITLE_BAR,
        DockStyleCategory.SIDEBAR,
        DockStyleCategory.CORE,
    )

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        # Hide the title label; the window title is not needed because the
        # embedded menu bar provides the primary chrome content.
        self.titleLabel.hide()

        self.menu_bar = QMenuBar(self)
        # Make the menu bar the same height as the title bar so it looks like
        # one continuous chrome surface and its items are vertically centered.
        self.menu_bar.setFixedHeight(self.height())

        # The base layout is: spacing, iconLabel, titleLabel, stretch, buttons.
        # Insert the menu bar right after the icon and before the title label.
        self.hBoxLayout.insertWidget(2, self.menu_bar, 0, Qt.AlignVCenter)

        self._build_menus()
        self._init_dock_style()

    def _build_menus(self) -> None:
        """Populate the embedded menu bar with demo actions."""
        file_menu = self.menu_bar.addMenu("File")
        file_menu.addAction(QAction("New", self, triggered=self._on_dummy))
        file_menu.addAction(QAction("Open...", self, triggered=self._on_dummy))
        file_menu.addSeparator()
        file_menu.addAction(QAction("Exit", self, triggered=self._on_exit))

        edit_menu = self.menu_bar.addMenu("Edit")
        edit_menu.addAction(QAction("Undo", self, triggered=self._on_dummy))
        edit_menu.addAction(QAction("Redo", self, triggered=self._on_dummy))

        view_menu = self.menu_bar.addMenu("View")
        view_menu.addAction(QAction("Explorer", self, triggered=self._on_dummy))
        view_menu.addAction(QAction("Search", self, triggered=self._on_dummy))

        help_menu = self.menu_bar.addMenu("Help")
        help_menu.addAction(QAction("About", self, triggered=self._on_about))

    def add_window_menu(self) -> QMenu:
        """Add a Window menu to the embedded menu bar and return it."""
        menu = self.menu_bar.addMenu("Window")
        menu.addAction(
            QAction("Minimize", self, triggered=self.window().showMinimized)
        )
        menu.addAction(
            QAction(
                "Toggle Maximize",
                self,
                triggered=self._toggle_maximize,
            )
        )
        return menu

    def add_themes_menu(self, themes: list[tuple[str, str]]) -> QMenu:
        """Add a Themes menu to the embedded menu bar."""
        menu = self.menu_bar.addMenu("Themes")
        for name, key in themes:
            menu.addAction(
                QAction(
                    name,
                    self,
                    triggered=lambda _=False, k=key: apply_dock_theme(k),
                )
            )
        return menu

    def _toggle_maximize(self) -> None:
        """Toggle the parent window's maximized state."""
        window = self.window()
        if window is None:
            return
        if window.isMaximized():
            window.showNormal()
        else:
            window.showMaximized()

    def _on_dummy(self) -> None:
        sender = self.sender()
        text = sender.text() if sender else "Action"
        QMessageBox.information(self.window(), "Demo", f"'{text}' triggered.")

    def _on_about(self) -> None:
        QMessageBox.about(
            self.window(),
            "About",
            "<b>Lace Custom Title Bar Demo</b><br>"
            "Main title bar embeds a menu bar; floating containers embed a search box.",
        )

    def _on_exit(self) -> None:
        window = self.window()
        if window is not None:
            window.close()

    def refresh_style(self) -> None:
        """Apply the active dock theme to the embedded menu bar.

        The menu bar itself is transparent so the title bar's own themed
        background shows through, guaranteeing an exact colour match.  Menu
        item text and hover/popup colours are pulled from the same dock
        theme tokens used by the frameless title-bar styler.
        """
        sm = self._style_mgr

        bg = sm.get(DockStyleCategory.SIDEBAR, "bg_color") or sm.get(
            DockStyleCategory.TITLE_BAR, "bg_normal"
        )
        text = sm.get(DockStyleCategory.TITLE_BAR, "text_normal")
        hover_bg = sm.get(DockStyleCategory.TITLE_BAR, "button_hover_bg")
        border = sm.get(DockStyleCategory.TITLE_BAR, "border_normal")

        bg_hex = _color_hex(bg) if bg else "transparent"
        text_hex = _color_hex(text) if text else "#cccccc"
        hover_hex = _color_hex(hover_bg) if hover_bg else "#555555"
        border_hex = _color_hex(border) if border else hover_hex

        # 7px vertical padding centers a default-sized menu item inside the
        # 32 px title bar.  No font-size is set, so the application default
        # font is used.
        self.menu_bar.setStyleSheet(f"""
            QMenuBar {{
                background: transparent;
                border: none;
                padding: 0px;
                margin: 0px;
            }}
            QMenuBar::item {{
                background: transparent;
                color: {text_hex};
                padding: 7px 12px;
                margin: 0px;
                border: none;
            }}
            QMenuBar::item:selected {{
                background: {hover_hex};
            }}
            QMenuBar::item:pressed {{
                background: {hover_hex};
            }}
            QMenu {{
                background: {bg_hex};
                color: {text_hex};
                border: 1px solid {border_hex};
                padding: 4px;
            }}
            QMenu::item {{
                padding: 4px 16px;
                background: transparent;
            }}
            QMenu::item:selected {{
                background: {hover_hex};
            }}
            QMenu::separator {{
                background: {border_hex};
                height: 1px;
                margin: 4px 8px;
            }}
        """)

    def paintEvent(self, event) -> None:
        """Paint a solid theme background before the base title bar paints.

        The qframelesswindow base class does not always render the QSS
        background set by :class:`FramelessTitleBarStyler` on the title-bar
        widget, so we fill the rect with the current dock-theme background
        explicitly.  This guarantees the embedded menu bar and the areas
        around it share the exact same colour.
        """
        try:
            sm = self._style_mgr
            bg = sm.get(DockStyleCategory.SIDEBAR, "bg_color") or sm.get(
                DockStyleCategory.TITLE_BAR, "bg_normal"
            )
        except (AttributeError, RuntimeError):
            bg = None

        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(_color_hex(bg)) if bg else QColor("#1e1e1e"))
        painter.end()

        super().paintEvent(event)

    def canDrag(self, pos) -> bool:
        """Disable dragging when the cursor is over the menu bar or buttons.

        Without this, pressing the mouse on a menu item could start a window
        drag on platforms where the frameless library initiates the OS move
        loop on press.
        """
        child = self.childAt(pos)
        while child is not None and child is not self:
            if isinstance(child, (QMenuBar, QMenu, QAbstractButton, QLineEdit)):
                return False
            child = child.parent()
        return super().canDrag(pos)


# ── Custom floating-container title bar with search input ────────────

class SearchTitleBar(LaceStandardTitleBar):
    """Standard Lace title bar with a dummy search box in the chrome.

    This title bar is used by floating dock containers.  Typing into the
    search field and pressing Enter prints the query to stdout; in a real
    application it could filter dock widgets or search project content.
    """

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search docks...")
        self.search_input.setClearButtonEnabled(True)
        # Resizable between min/max while staying centered in the title bar.
        self.search_input.setMinimumWidth(144)
        self.search_input.setMaximumWidth(800)
        self.search_input.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.search_input.returnPressed.connect(self._on_search)

        # Center the search box by placing equal stretchable space on both
        # sides.  The base layout is: spacing, icon, title, stretch, buttons.
        # No alignment flag is passed so the line edit can actually expand
        # between the two stretches while remaining centered.
        self.hBoxLayout.insertStretch(3, 1)
        self.hBoxLayout.insertWidget(4, self.search_input, 1)

        self.search_input.setStyleSheet("""
            QLineEdit {
                background: rgba(128, 128, 128, 40);
                border: 1px solid rgba(128, 128, 128, 80);
                border-radius: 4px;
                padding: 2px 6px;
                color: palette(window-text);
            }
        """)

    def _on_search(self) -> None:
        text = self.search_input.text().strip()
        print(f"[SearchTitleBar] search query: {text!r}")

    def canDrag(self, pos) -> bool:
        """Disable dragging when the cursor is over the search box or buttons."""
        child = self.childAt(pos)
        while child is not None and child is not self:
            if isinstance(child, (QLineEdit, QAbstractButton)):
                return False
            child = child.parent()
        return super().canDrag(pos)


# ── Main demo window ─────────────────────────────────────────────────

class DemoMainWindow(FramelessLaceMainWindow):
    """Demo window showcasing configurable custom title bars."""

    def __init__(self):
        # Use the menu-embedded title bar for the main window.
        super().__init__(title_bar=MenuEmbeddedTitleBar)

        self.setWindowTitle("Lace — Custom Title Bar Demo")
        self.resize(1280, 840)

        self._setup_icon()

        # Create the dock manager and tell it to use frameless chrome for
        # floating containers plus the search title bar for those floats.
        self.dock_manager = DockManager(self)
        self.dock_manager.title_bar_mode = TitleBarMode.custom
        self.dock_manager.floating_title_bar = SearchTitleBar

        # App-wide theme bridge (as in the other demos): popup menus (QMenu)
        # are top-level windows that read the application palette, not the
        # dock root's — without this the dock-area title-bar tabs menu and
        # context menus stay on the default system palette.
        self.theme_bridge = DockThemeBridge()

        # Set the central widget *after* the dock manager so the title bar
        # stays on top.
        self.setCentralWidget(self.dock_manager._root)

        # The embedded menu bar is styled by MenuEmbeddedTitleBar itself via
        # DockStyled, so no separate styler registration is needed.

        self._create_dock_widgets()
        self._create_menubar_menus()

        apply_dock_theme("cyberpunk_neon")

    def _setup_icon(self) -> None:
        """Load the application icon from the project root."""
        base_path = Path(__file__).resolve().parent          # demos/
        icon_dir = base_path.parent / "lace" / "resources" / "lace_icons"  # repo root
        try:
            get_icon_provider(icon_dir)
        except Exception as exc:
            print(f"Icon provider load skipped: {exc}")

        icon_path = base_path / "icon.ico"
        if icon_path.exists():
            app_icon = QIcon(str(icon_path.resolve()))
            if not app_icon.isNull() and not app_icon.pixmap(16, 16).isNull():
                QApplication.instance().setWindowIcon(app_icon)
                self.setWindowIcon(app_icon)
                return

        fallback = self.style().standardIcon(
            QApplication.style().SP_TitleBarMenuButton
        )
        self.setWindowIcon(fallback)
        QApplication.instance().setWindowIcon(fallback)

    def _create_dock_widgets(self) -> None:
        """Create a few dock widgets to drag and float."""
        # Center editor
        editor = DockWidget("Editor", self)
        editor.set_widget(QTextEdit())
        editor.set_features(DockWidgetFeature.all_features)
        self.dock_manager.add_dock_widget(DockWidgetArea.center, editor)

        # Bottom output panel
        output = DockWidget("Output", self)
        output_widget = QTextEdit()
        output_widget.setReadOnly(True)
        output_widget.setPlainText(
            "Drag this dock widget by its tab or title bar to float it.\n"
            "The floating window will use the search title bar.\n"
            "Try typing in the search box and pressing Enter."
        )
        output.set_widget(output_widget)
        output.set_features(DockWidgetFeature.all_features)
        self.dock_manager.add_dock_widget(DockWidgetArea.bottom, output)

        # Right properties panel
        props = DockWidget("Properties", self)
        props_widget = QTextEdit()
        props_widget.setReadOnly(True)
        props_widget.setPlainText(
            "The main window title bar above has File/Edit/View/Help menus "
            "embedded directly in the frameless chrome."
        )
        props.set_widget(props_widget)
        props.set_features(DockWidgetFeature.all_features)
        self.dock_manager.add_dock_widget(DockWidgetArea.right, props)

    def _create_menubar_menus(self) -> None:
        """Add Window and Themes menus to the embedded title-bar menu bar.

        All menus live in the custom title bar; there is no separate menu bar
        below it.
        """
        title_bar = self.titleBar
        if not isinstance(title_bar, MenuEmbeddedTitleBar):
            return

        title_bar.add_window_menu()
        title_bar.add_themes_menu([
            ("Default", "default"),
            ("Dark", "dark"),
            ("Light", "light"),
            ("Cyberpunk Neon", "cyberpunk_neon"),
            ("Nordic", "nordic"),
            ("Tokyo Night", "tokyo_night"),
        ])


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    window = DemoMainWindow()
    window.show()
    sys.exit(app.exec())
