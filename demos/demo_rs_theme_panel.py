# -*- coding: utf-8 -*-
"""Rust-theme-driven Qt panel — Phase 6 interop demo.

A Python-side Qt UI whose every colour comes from
``lace_rs.build_merged_theme()``: pick any of the 27 presets from the combo
box and the panel re-themes through the Rust engine, with zero Python theme
code involved. Run headed, or ``--smoke`` headless (loads each preset once
and exits nonzero on the first failure).
"""

import json
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", os.environ.get("QT_QPA_PLATFORM", ""))

from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

import lace_rs

PANEL_QML = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "demo_rs_theme_panel.qml")


class ThemeBridge(QObject):
    """Combo-box callback: re-resolves the preset through Rust and pushes it."""

    themeChanged = Signal()

    def __init__(self, engine):
        super().__init__()
        self._engine = engine

    @Slot(str)
    def applyTheme(self, name):
        try:
            theme = lace_rs.build_merged_theme(name)
        except Exception as exc:  # keep the old theme rather than blanking
            print(f"theme '{name}' failed: {exc}", file=sys.stderr)
            return
        self._engine.rootContext().setContextProperty(
            "themeJson", json.dumps(theme))
        self._engine.rootContext().setContextProperty("themeName", name)
        self.themeChanged.emit()


def main(argv):
    smoke = "--smoke" in argv
    if smoke:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    start = [a for a in argv[1:] if not a.startswith("--")]
    first = start[0] if start else "dark"

    app = QGuiApplication([])
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty(
        "themeJson", json.dumps(lace_rs.build_merged_theme(first)))
    engine.rootContext().setContextProperty("themeName", first)
    engine.rootContext().setContextProperty(
        "themeKeys", lace_rs.available_themes())
    bridge = ThemeBridge(engine)
    engine.rootContext().setContextProperty("bridge", bridge)
    engine.load(QUrl.fromLocalFile(PANEL_QML))

    if smoke:
        failures = 0
        for name in lace_rs.available_themes():
            try:
                theme = lace_rs.build_merged_theme(name)
            except Exception as exc:
                print(f"SMOKE theme '{name}': {exc}")
                failures += 1
                continue
            for token in ("core.canvas_bg", "panel.bg_normal", "tab.bg_active",
                          "title_bar.bg_normal", "sidebar.bg_color"):
                category, key = token.split(".")
                if theme.get(category, {}).get(key) is None:
                    print(f"SMOKE theme '{name}': missing {token}")
                    failures += 1
        # And the view itself must load without QML errors.
        if not engine.rootObjects():
            print("SMOKE engine produced no root object")
            failures += 1
        print(f"SMOKE {'ok' if not failures else 'FAILED'}")
        return 1 if failures else 0

    return app.exec()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
