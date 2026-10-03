# -*- coding: utf-8 -*-
"""DockManager(app_style=...) and DockThemeBridge(install_style=...).

The dock theme always sets the palette; the application's QStyle is the host
app's choice. DockManager leaves it alone unless ``app_style`` names one:
``"lace"`` for LaceStyle, any Qt style name otherwise.
"""

import pytest
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication, QStyleFactory, QWidget

from lace.dock_style_manager import get_dock_style_manager
from lace.dock_theme import DockStyleCategory
from lace.dock_theme_bridge import DockThemeBridge
from lace.lace_style import LaceStyle


@pytest.fixture
def app(qapp):
    """The application with its style and palette restored afterwards."""
    previous, palette = qapp.style().name(), QPalette(qapp.palette())
    qapp.setStyle(QStyleFactory.create("Windows"))
    yield qapp
    qapp.setStyle(previous)
    qapp.setPalette(palette)
    QApplication.processEvents()


def test_default_leaves_the_app_style_alone(app, make_desk):
    before = app.style()
    make_desk()
    assert app.style() is before
    assert not isinstance(app.style(), LaceStyle)


def test_lace_installs_lace_style_that_follows_the_theme(app, make_desk):
    make_desk(app_style="lace")
    style = app.style()
    assert isinstance(style, LaceStyle)
    get_dock_style_manager().update(DockStyleCategory.CORE, control_radius=9)
    QApplication.processEvents()
    assert style.control_radius == 9


def test_any_qt_style_name_works(app, make_desk):
    make_desk(app_style="Fusion")
    assert app.style().name().lower() == "fusion"


def test_the_palette_follows_the_theme_either_way(app, make_desk):
    make_desk()
    get_dock_style_manager().apply_theme("light")
    QApplication.processEvents()
    light = app.palette().color(QPalette.ColorRole.Window).lightness()
    get_dock_style_manager().apply_theme("midnight")
    QApplication.processEvents()
    assert app.palette().color(QPalette.ColorRole.Window).lightness() < light


def test_bridge_can_leave_the_style_alone(qapp):
    widget = QWidget()
    before = widget.style()
    DockThemeBridge(target=widget, parent=widget, install_style=False)
    assert widget.style() is before


def test_the_old_empty_style_name_is_refused(qapp):
    """style_name="" used to mean install_style=False; it now says so."""
    with pytest.raises(ValueError, match="install_style=False"):
        DockThemeBridge(target=QWidget(), style_name="")


def test_bridge_installs_lace_style_by_default_and_by_name(qapp):
    for kwargs in (dict(), dict(style_name="lace")):
        widget = QWidget()
        DockThemeBridge(target=widget, parent=widget, **kwargs)
        assert isinstance(widget.style(), LaceStyle), kwargs
