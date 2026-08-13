# -*- coding: utf-8 -*-
"""Attributes that exist before they are needed — §5.5.

Two defensive habits the review counted across lace/: reading painted-chrome
state through ``getattr(self, "_x", default)`` because refresh_style() might
not have run, and reaching into ``DockManager._root`` through
``getattr(manager, '_root', None) or manager`` in thirteen places. Both hide
the real invariant. The attributes are set in __init__ now, and the root
container has a public accessor.

The `or manager` fallback was never even reachable as written: DockManager is
a QObject, so handing it to setParent() or mapToGlobal() would have failed.
"""

import pathlib

import pytest
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QLabel, QMainWindow

from lace.dock_manager import DockManager
from lace.dock_widget import DockWidget
from lace.enums import DockWidgetArea
from lace.sidebar_container import SideBarContainer

LACE = pathlib.Path(__file__).resolve().parent.parent / "lace"

PAINT_ATTRS = ("_bg", "_corner_radius", "_border_width", "_border_color",
               "_focus_border_color", "_sidebar_focused")


@pytest.fixture
def unstyled(qapp, monkeypatch):
    """A container whose refresh_style() never ran.

    __init__ calls it today, so a plain construction proves nothing: the
    attributes would exist either way. Suppressing it is what the getattr
    defaults were actually defending against — a paint that beats the first
    restyle, which any change to the DockStyled debounce could reintroduce.
    """
    monkeypatch.setattr(SideBarContainer, "refresh_style", lambda self: None)
    overlay = SideBarContainer()
    yield overlay
    overlay.deleteLater()


def test_sidebar_container_has_its_chrome_before_any_restyle(unstyled):
    for name in PAINT_ATTRS:
        assert hasattr(unstyled, name), f"{name} only exists after refresh_style()"


def test_it_paints_without_a_restyle(unstyled):
    """The reason the getattr defaults were there — so remove the reason."""
    unstyled.resize(200, 150)
    image = QImage(unstyled.size(), QImage.Format_ARGB32)
    image.fill(0)
    unstyled.render(image)  # must not raise AttributeError


def test_show_widget_works_before_a_restyle(unstyled, qapp):
    """_dock_manager and the focus bookkeeping were guarded the same way."""
    dock_widget = DockWidget("Alpha")
    dock_widget.set_widget(QLabel("Alpha"))
    unstyled.show_widget(dock_widget, DockWidgetArea.left, animate=False)
    assert unstyled._last_focused_dock_widget is None


def test_the_paint_path_reads_the_attributes_directly():
    """A getattr default silently survives a renamed or never-set attribute."""
    source = (LACE / "sidebar_container.py").read_text(encoding="utf-8")
    for name in PAINT_ATTRS:
        assert f'getattr(self, "{name}"' not in source, name
        assert f"getattr(self, '{name}'" not in source, name


# ── root_container() ──────────────────────────────────────────────────────
def test_nothing_reaches_into_the_private_root():
    offenders = [p.name for p in LACE.glob("*.py")
                 if "getattr(self, '_root'" in p.read_text(encoding="utf-8")
                 or "getattr(dock_manager, '_root'" in p.read_text(encoding="utf-8")
                 or "getattr(self._dock_manager, '_root'" in p.read_text(encoding="utf-8")
                 or "getattr(self._manager, '_root'" in p.read_text(encoding="utf-8")]
    assert not offenders, offenders


def test_root_container_is_the_widget_the_layout_lives_in(qapp):
    win = QMainWindow()
    dock_manager = DockManager(win)
    try:
        assert dock_manager.root_container() is dock_manager._root
        assert dock_manager.root_container() is win.centralWidget()
    finally:
        win.close()


def test_a_managerless_dock_widget_unassigns_without_a_parent(qapp):
    """flag_as_unassigned()'s fallback used to be the manager — a QObject."""
    dock_widget = DockWidget("Orphan")
    dock_widget.set_widget(QLabel("Orphan"))
    assert dock_widget._dock_manager is None

    dock_widget.flag_as_unassigned()  # must not raise

    assert dock_widget.parentWidget() is None


def test_an_assigned_dock_widget_parks_on_the_root(qapp):
    win = QMainWindow()
    win.resize(600, 400)
    dock_manager = DockManager(win)
    dock_widget = DockWidget("Alpha")
    dock_widget.set_widget(QLabel("Alpha"))
    dock_manager.add_dock_widget(DockWidgetArea.center, dock_widget)
    win.show()
    qapp.processEvents()

    try:
        dock_widget.flag_as_unassigned()
        assert dock_widget.parentWidget() is dock_manager.root_container()
        assert not dock_widget.isVisible()
    finally:
        win.close()
