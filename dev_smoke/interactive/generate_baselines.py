# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0

Automated baseline generator for interactive smoke test sessions S1-S4.
Executes deterministic programmatic interactions to record baseline trace logs.
"""

import sys
import os
import logging
from pathlib import Path

# Enable tracing before importing lace
os.environ["LACE_TRACE"] = "1"

from PySide6.QtCore import Qt, QPoint, QSize
from PySide6.QtWidgets import QApplication, QMenu, QWidget

# Ensure lace and demo_app can be imported
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from demo_app import DemoMainWindow
import lace._trace as _trace
_trace.TRACE_ON = True

from lace.enums import DockWidgetArea
from lace.dock_widget import DockWidget
from lace.dock_container_widget import DockContainerWidget
from lace.floating_dock_container import FloatingDockContainer


class TraceCollector(logging.Handler):
    def __init__(self):
        super().__init__()
        self.lines = []

    def emit(self, record):
        msg = self.format(record)
        if "[TRACE]" in msg:
            idx = msg.find("[TRACE]")
            self.lines.append(msg[idx:].strip())

    def clear(self):
        self.lines.clear()


def run_s1(win: DemoMainWindow, collector: TraceCollector, out_dir: Path):
    collector.clear()
    print("Running automated S1 (Manager & Composition)...")
    
    # Notice initial docked layout & save/restore
    state = win.dock_manager.save_state()
    win.dock_manager.restore_state(state)
    
    # Add and remove a dock widget
    dw = DockWidget("Temp S1", win)
    win.dock_manager.add_dock_widget(DockWidgetArea.right, dw)
    win.dock_manager.remove_dock_widget(dw)
    
    # Register and remove a container
    container = DockContainerWidget(win.dock_manager, win)
    win.dock_manager.register_dock_container(container)
    win.dock_manager.remove_dock_container(container)
    
    out_file = out_dir / "baseline_s1.log"
    out_file.write_text("\n".join(collector.lines) + "\n" if collector.lines else "", encoding="utf-8")
    print(f" -> Wrote {len(collector.lines)} lines to {out_file.name}")


def run_s2(win: DemoMainWindow, collector: TraceCollector, out_dir: Path):
    collector.clear()
    print("Running automated S2 (Drop Resolution & Insert)...")
    
    # Test drop into container
    dw1 = DockWidget("Drop Test 1", win)
    fw1 = FloatingDockContainer(dock_widget=dw1, dock_manager=win.dock_manager)
    win.dock_manager._drop_into_container(fw1, DockWidgetArea.top)
    
    # Test drop into section
    dw2 = DockWidget("Drop Test 2", win)
    fw2 = FloatingDockContainer(dock_widget=dw2, dock_manager=win.dock_manager)
    area = win.dock_manager.dock_area(0)
    win.dock_manager._drop_into_section(fw2, area, DockWidgetArea.left)
    
    # Test drop into center of section
    dw3 = DockWidget("Drop Test 3", win)
    fw3 = FloatingDockContainer(dock_widget=dw3, dock_manager=win.dock_manager)
    area = win.dock_manager.dock_area(0)
    win.dock_manager._drop_into_center_of_section(fw3, area)

    # Test drop resolve
    dw4 = DockWidget("Drop Test 4", win)
    fw4 = FloatingDockContainer(dock_widget=dw4, dock_manager=win.dock_manager)
    win.dock_manager.drop_floating_widget(fw4, QPoint(10, 10))
    
    out_file = out_dir / "baseline_s2.log"
    out_file.write_text("\n".join(collector.lines) + "\n" if collector.lines else "", encoding="utf-8")
    print(f" -> Wrote {len(collector.lines)} lines to {out_file.name}")


def run_s3(win: DemoMainWindow, collector: TraceCollector, out_dir: Path):
    collector.clear()
    print("Running automated S3 (Menu Decoupling & Actions)...")
    
    area = win.dock_manager.dock_area(0)
    menu = QMenu()
    
    # Title bar menu build & action
    tb = area._title_bar
    tb.build_dock_menu(menu)
    act = next((a for a in menu.actions() if a.data() and a.data()[0] == "float"), None)
    if act:
        tb.dispatch_dock_action(act)
        
    # Tab menu build & action
    if area._tab_bar().count() > 0:
        tab = area._tab_bar().tab(0)
        menu.clear()
        tab.build_dock_menu(menu)
        act = next((a for a in menu.actions() if a.data() and a.data()[0] == "pin"), None)
        if act:
            tab.dispatch_dock_action(act)
            
    out_file = out_dir / "baseline_s3.log"
    out_file.write_text("\n".join(collector.lines) + "\n" if collector.lines else "", encoding="utf-8")
    print(f" -> Wrote {len(collector.lines)} lines to {out_file.name}")


def run_s4(win: DemoMainWindow, collector: TraceCollector, out_dir: Path):
    collector.clear()
    print("Running automated S4 (Sidebar Controllers & Transitions)...")
    
    sm = win.dock_manager.sidebar_manager
    dws = list(win.dock_manager.dock_widgets_map().values())
    dw1 = dws[0]
    dw2 = dws[1]
    
    # Pin widget to left sidebar
    sm.pin_widget(dw1, area=DockWidgetArea.left)
    
    # Hover enter & process timer & show overlay
    bar = sm._sidebars[DockWidgetArea.left]
    if bar._buttons:
        btn = bar._buttons[0]
        sm._on_tab_hover_enter(btn)
        sm._process_pending_switch()
        
    # Resize overlay
    sm._on_resize_finished()
    
    # Hover leave & hide timeout & close overlay
    if bar._buttons:
        sm._on_tab_hover_leave(bar._buttons[0])
    sm._on_hide_timeout()
    
    # Unpin floating
    sm.unpin_widget_floating(dw1)
    
    # Pin dw2 and unpin to docked
    sm.pin_widget(dw2, area=DockWidgetArea.right)
    sm.unpin_widget(dw2)
    
    out_file = out_dir / "baseline_s4.log"
    out_file.write_text("\n".join(collector.lines) + "\n" if collector.lines else "", encoding="utf-8")
    print(f" -> Wrote {len(collector.lines)} lines to {out_file.name}")


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    
    collector = TraceCollector()
    logging.getLogger("lace.trace").addHandler(collector)
    logging.getLogger("lace.trace").setLevel(logging.INFO)
    
    win = DemoMainWindow()
    win.show()
    app.processEvents()
    
    out_dir = Path(__file__).parent
    
    run_s1(win, collector, out_dir)
    run_s2(win, collector, out_dir)
    run_s3(win, collector, out_dir)
    run_s4(win, collector, out_dir)
    
    print("\nAll baseline trace logs generated successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
