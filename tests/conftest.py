# -*- coding: utf-8 -*-
"""pytest bootstrap & shared fixtures.

- Puts the repo root on ``sys.path`` (for ``import lace``).
- Provides a session-scoped offscreen ``qapp`` fixture.
- Resets the DockStyleManager singleton before every test so theme state
  never leaks between tests.
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
    category to the hardcoded defaults (DOCK_THEMES["default"] == {}).
    """
    from lace.dock_style_manager import get_dock_style_manager

    get_dock_style_manager().apply_theme("default")
    yield
