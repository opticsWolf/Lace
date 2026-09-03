# -*- coding: utf-8 -*-
"""The DockSignals bus — IMPROVEMENT_PLAN_v0.7.md Phase 5, §4.1.

``dock_signals.py`` described itself as the event bus replacing "tight coupling
(where deep widgets call manager methods directly)". DockManager constructed it
and connected all three signals to handlers, and nothing in the package ever
emitted them — a full-package grep returned only the three connect() lines. The
direct path (FloatingDockContainer → container.drop_floating_widget()) is what
actually ran, so the bus read as a supported extension point that silently did
nothing.
"""

import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QLabel, QMainWindow

from lace.dock_manager import DockManager
from lace.dock_signals import DockSignals
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea
from lace.floating_dock_container import FloatingDockContainer


@pytest.fixture
def desk(qapp):
    win = QMainWindow()
    win.resize(900, 600)
    dock_manager = DockManager(win)
    win.show()
    qapp.processEvents()
    yield win, dock_manager
    win.close()


def _mk(name):
    dock_widget = DockWidget(name)
    dock_widget.set_widget(QLabel(name))
    return dock_widget


def test_the_bus_carries_only_signals_something_emits():
    """A signal nothing emits is worse than no signal — it reads as supported."""
    assert hasattr(DockSignals, "request_overlay_hide")
    assert hasattr(DockSignals, "floating_widget_dropped")
    assert not hasattr(DockSignals, "request_overlay_show"), \
        "request_overlay_show is back, and nothing can emit it: its call site " \
        "needs show_overlay()'s return value, which a signal cannot provide"


def test_a_drop_emits_floating_widget_dropped(desk, qapp):
    win, dock_manager = desk
    dock_manager.add_dock_widget(DockWidgetArea.center, _mk("Alpha"))
    qapp.processEvents()

    seen = []
    dock_manager.signals.floating_widget_dropped.connect(
        lambda fw, container, pos: seen.append((fw, container, pos)))

    floating = FloatingDockContainer(dock_widget=_mk("Beta"),
                                     dock_manager=dock_manager)
    floating.show()
    qapp.processEvents()

    target = dock_manager.root_container()
    dock_manager.signals.floating_widget_dropped.emit(
        floating, target, QPoint(10, 10))
    qapp.processEvents()

    assert len(seen) == 1, "the drop signal did not fire exactly once"
    got_floating, got_container, got_pos = seen[0]
    assert got_floating is floating
    assert got_container is target
    assert got_pos == QPoint(10, 10)


def test_the_bus_routes_a_drop_to_the_container_it_names(desk, qapp):
    """Not to the root container — a float can be dropped onto another float."""
    win, dock_manager = desk
    target_area = dock_manager.add_dock_widget(DockWidgetArea.center, _mk("Alpha"))
    qapp.processEvents()

    floating = FloatingDockContainer(dock_widget=_mk("Beta"),
                                     dock_manager=dock_manager)
    floating.show()
    qapp.processEvents()

    routed = []
    root = dock_manager.root_container()
    real = type(root.drop_controller()).drop_floating_widget

    def spy(self, fw, pos):
        routed.append(self._c)
        return real(self, fw, pos)

    type(root.drop_controller()).drop_floating_widget = spy
    try:
        dock_manager.signals.floating_widget_dropped.emit(
            floating, root, QPoint(10, 10))
        qapp.processEvents()
    finally:
        type(root.drop_controller()).drop_floating_widget = real

    assert routed == [root], \
        f"the drop was routed to {routed}, not the container the signal named"


def test_a_subscriber_can_observe_a_drag_end_without_patching(desk, qapp):
    win, dock_manager = desk
    dock_manager.add_dock_widget(DockWidgetArea.center, _mk("Alpha"))
    qapp.processEvents()

    hides = []
    dock_manager.signals.request_overlay_hide.connect(lambda: hides.append(True))

    floating = FloatingDockContainer(dock_widget=_mk("Beta"),
                                     dock_manager=dock_manager)
    floating.show()
    qapp.processEvents()

    # A drag that ends with no drop container is the plainest path through
    # _finalize_drag(), and it must still tell the bus the overlays are done.
    floating._drop_container = None
    floating._finalize_drag()
    qapp.processEvents()

    assert hides, "the end of a drag did not reach the bus"
    assert dock_manager.container_overlay().isHidden()
    assert dock_manager.dock_area_overlay().isHidden()


def test_the_drag_path_holds_no_direct_drop_call():
    """floating_behaviour.py must go through the bus, not the container."""
    from pathlib import Path

    import lace.floating_behaviour as module
    source = Path(module.__file__).read_text(encoding="utf-8")
    assert "drop_floating_widget(self" not in source, \
        "a direct container.drop_floating_widget() call is back in the drag path"
    assert "floating_widget_dropped.emit" in source
