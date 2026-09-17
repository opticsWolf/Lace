#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Emit Phase-2 layout oracles under `rust/lace-core/tests/fixtures/layouts/`.

Builds real `DockManager` scenarios headless, saves their `save_state()`
output, normalizes transient container ids (`uuid4` -> `float-N`), and writes
hand-made negative fixtures (corrupt geometry, broken trees, bad versions).

Usage (from repo root):
    QT_QPA_PLATFORM=offscreen .venv/Scripts/python.exe \\
        rust/lace-core/codegen/emit_layouts.py
"""

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from PySide6.QtWidgets import QApplication, QLabel, QMainWindow  # noqa: E402

from lace.dock_manager import DockManager  # noqa: E402
from lace.dock_widget import DockWidget  # noqa: E402
from lace.enums import DockWidgetArea  # noqa: E402
from lace.floating_dock_container import FloatingDockContainer  # noqa: E402

OUT_DIR = REPO / "rust" / "lace-core" / "tests" / "fixtures" / "layouts"


def _mk(name):
    dock_widget = DockWidget(name)
    dock_widget.set_widget(QLabel(name))
    return dock_widget


def _normalize(state):
    """Replace transient float-container uuids with stable `float-N` ids."""
    remap = {}
    for container in state["containers"]:
        cid = container["id"]
        if cid != "main":
            remap[cid] = f"float-{len(remap) + 1}"
            container["id"] = remap[cid]
    if remap and "container_geometries" in state:
        state["container_geometries"] = {
            remap.get(cid, cid): geo
            for cid, geo in state["container_geometries"].items()
        }
    return state


def _save(dm, name):
    state = _normalize(json.loads(dm.save_state()))
    (OUT_DIR / f"{name}.json").write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return state


def _manager():
    win = QMainWindow()
    win.resize(1000, 700)
    dm = DockManager(win)
    win.show()
    QApplication.processEvents()
    return win, dm


def scenario_docked_tabs():
    win, dm = _manager()
    try:
        left = dm.add_dock_widget(DockWidgetArea.left, _mk("Alpha"))
        dm.add_dock_widget(DockWidgetArea.center, _mk("Beta"), left)
        dm.add_dock_widget(DockWidgetArea.center, _mk("Gamma"), left)
        dm.add_dock_widget(DockWidgetArea.bottom, _mk("Delta"))
        QApplication.processEvents()
        # Exercise a non-first current tab wherever tabs exist.
        for i in range(dm.root_container().dock_area_count()):
            area = dm.root_container().dock_area(i)
            if area.dock_widgets_count() > 1:
                area.set_current_index(area.dock_widgets_count() - 1)
        QApplication.processEvents()
        return _save(dm, "docked_tabs")
    finally:
        win.close()


def scenario_closed():
    win, dm = _manager()
    try:
        left = dm.add_dock_widget(DockWidgetArea.left, _mk("Alpha"))
        beta = _mk("Beta")
        dm.add_dock_widget(DockWidgetArea.center, beta, left)
        beta.toggle_view(False)
        QApplication.processEvents()
        return _save(dm, "closed")
    finally:
        win.close()


def scenario_locked():
    win, dm = _manager()
    try:
        area = dm.add_dock_widget(DockWidgetArea.left, _mk("Alpha"))
        beta = _mk("Beta")
        dm.add_dock_widget(DockWidgetArea.center, beta, area)
        area.locked_name = "sidebar"
        beta.locked_to_area = "sidebar"
        QApplication.processEvents()
        return _save(dm, "locked")
    finally:
        win.close()


def scenario_floating():
    win, dm = _manager()
    try:
        dm.add_dock_widget(DockWidgetArea.left, _mk("Alpha"))
        beta = _mk("Beta")
        beta.set_dock_manager(dm)
        dm.dock_widgets_map()[beta.objectName()] = beta
        floating = FloatingDockContainer(dock_widget=beta)
        floating.show()
        QApplication.processEvents()
        floating.setGeometry(220, 180, 480, 360)
        QApplication.processEvents()
        return _save(dm, "floating")
    finally:
        win.close()


def scenario_sidebar():
    win, dm = _manager()
    try:
        dm.add_dock_widget(DockWidgetArea.left, _mk("Alpha"))
        beta = _mk("Beta")
        dm.add_dock_widget(DockWidgetArea.right, beta)
        dm.sidebar_manager.pin_widget(beta, area=DockWidgetArea.left)
        QApplication.processEvents()
        return _save(dm, "sidebar")
    finally:
        win.close()


def write(name, payload):
    (OUT_DIR / f"{name}.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def negatives(base):
    import copy
    state = copy.deepcopy(base)

    # Pre-schema identifier, schema field absent (schema 0 on read).
    legacy = copy.deepcopy(base)
    legacy["type"] = "QtAdvancedDockingSystem"
    del legacy["schema"]
    write("legacy", legacy)

    write("wrong_type", {"type": "NotLace", "version": 0})

    future = copy.deepcopy(base)
    future["schema"] = 999
    write("future_schema", future)

    mismatch = copy.deepcopy(base)
    mismatch["version"] = 7
    write("version_mismatch", mismatch)

    write("missing_keys", {})

    zero = copy.deepcopy(base)
    zero["container_geometries"] = {"main": {
        "x": 0, "y": 0, "width": 0, "height": 360, "is_maximized": False}}
    write("bad_geometry_zero", zero)

    huge = copy.deepcopy(base)
    huge["container_geometries"] = {"main": {
        "x": 0, "y": 0, "width": 99999, "height": 360, "is_maximized": False}}
    write("bad_geometry_huge", huge)

    typed = copy.deepcopy(base)
    typed["container_geometries"] = {"main": {
        "x": "left", "y": 0, "width": 480, "height": 360, "is_maximized": False}}
    write("bad_geometry_type", typed)

    # Splitter whose sizes list contradicts its count.
    broken = copy.deepcopy(base)
    root = broken["containers"][0]["data"]["root_splitter"]
    assert root["type"] == "Splitter", "docked_tabs must split at the root"
    root["sizes"] = root["sizes"][:-1]
    write("sizes_mismatch", broken)

    unnamed = copy.deepcopy(base)

    def blank_first_widget(node):
        if node.get("type") == "Area":
            node["widgets"][0]["name"] = ""
            return True
        for child in node.get("children", []):
            if blank_first_widget(child):
                return True
        return False

    assert blank_first_widget(unnamed["containers"][0]["data"]["root_splitter"])
    write("unnamed_widget", unnamed)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    base = scenario_docked_tabs()
    scenario_closed()
    scenario_locked()
    scenario_floating()
    scenario_sidebar()
    negatives(base)
    files = sorted(p.name for p in OUT_DIR.glob("*.json"))
    print(f"wrote {len(files)} layout fixtures to {OUT_DIR}:")
    for name in files:
        print(f"  {name}")


if __name__ == "__main__":
    main()
