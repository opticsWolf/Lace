# -*- coding: utf-8 -*-
"""pytest bootstrap & shared fixtures.

- Puts the repo root on ``sys.path`` (for ``import lace``).
- Provides a session-scoped offscreen ``qapp`` fixture.
- Resets the DockStyleManager singleton before every test so theme state
  never leaks between tests.
- Provides ``make_desk``: a shown main window with a DockManager to dock
  labelled widgets into, closed after the test.
"""

import os
import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def pytest_addoption(parser):
    parser.addoption(
        "--themes", default=None,
        choices=("quick", "regular", "full", "all", "auto"),
        help="theme stage for theme-parametrised tests (see tests/theme_sets.py)")


def pytest_configure(config):
    stage = config.getoption("--themes")
    if stage:
        # Environment, so xdist workers and subprocesses see the same stage.
        os.environ["LACE_TEST_THEMES"] = stage


def pytest_generate_tests(metafunc):
    """Parametrise any test taking ``theme_key`` over the selected set."""
    if "theme_key" in metafunc.fixturenames:
        from tests.theme_sets import from_env
        keys = from_env()
        metafunc.parametrize("theme_key", keys, ids=keys)


@pytest.fixture(scope="session")
def qapp():
    """Session-wide offscreen QApplication (Qt requires exactly one)."""
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(autouse=True)
def _clean_style_manager():
    """Restore stock theme state before each test.

    DockStyleManager is a process-wide singleton, so tests that call
    ``update()`` / ``apply_theme()`` / ``apply_theme_dict()`` must not leak
    mutations into later tests. ``apply_theme("default")`` resets every
    category to the default theme (``dark`` unless set_default_theme says
    otherwise).
    """
    from lace.dock_style_manager import get_dock_style_manager

    get_dock_style_manager().apply_theme("default")
    yield


class Desk:
    """A QMainWindow holding a DockManager, for tests that need real dock areas."""

    def __init__(self, qapp, width: int, height: int, **manager_kwargs):
        from PySide6.QtWidgets import QMainWindow
        from lace.dock_manager import DockManager

        self._qapp = qapp
        self.win = QMainWindow()
        self.win.resize(width, height)
        self.manager = DockManager(self.win, **manager_kwargs)

    @staticmethod
    def widget(name: str, text: str = None):
        """A DockWidget titled *name* holding a QLabel (text: *text*, else *name*)."""
        from PySide6.QtWidgets import QLabel
        from lace.dock_widget import DockWidget

        dock_widget = DockWidget(name)
        dock_widget.set_widget(QLabel(name if text is None else text))
        return dock_widget

    def add(self, area, widget, target=None, text: str = None):
        """Dock *widget* (a DockWidget, or a name for :meth:`widget`); its dock area."""
        if isinstance(widget, str):
            widget = self.widget(widget, text)
        return self.manager.add_dock_widget(area, widget, target)

    def show(self, active=None) -> None:
        """Show the window, then make *active* the active dock area, if given."""
        self.win.show()
        self._qapp.processEvents()
        if active is not None:
            self.manager.set_active_dock_area(active)
            self._qapp.processEvents()


@pytest.fixture
def make_desk(qapp):
    """``make_desk(width=900, height=600, **DockManager kwargs)`` -> a :class:`Desk`.

    Every desk's window is closed after the test.
    """
    desks = []

    def make(width: int = 900, height: int = 600, **manager_kwargs) -> Desk:
        desk = Desk(qapp, width, height, **manager_kwargs)
        desks.append(desk)
        return desk

    yield make
    for desk in desks:
        desk.win.close()
