# -*- coding: utf-8 -*-
"""A queued restyle must not outlive the widget it restyles.

``DockStyled.on_style_changed`` and ``DockThemeBridge.on_style_changed`` both
debounce through ``QTimer.singleShot(0, ...)``, so a theme applied in one frame
rebuilds a widget once rather than once per category. Without a context object
that shot is owned by nothing: it survives the widget and runs against freed
memory on whatever processes events next.

That is not a leak, it is a use-after-free, and the ``except RuntimeError``
guard in ``_do_refresh`` does not catch it — shiboken only invalidates the
Python wrapper when it owns the deletion, and a widget destroyed as a child of
a destroyed parent is not that case. The symptom was a segfault in an unrelated
test: applying a theme while a closed window was still alive queued the shots,
the window was then torn down, and the next ``processEvents()`` crashed.

Measured as "the refresh does not run", not as "the process survives" — a test
that only asserts the absence of a crash passes for the wrong reason on any
platform where the freed page happens to still be readable.
"""

import pytest
from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QWidget

from lace.dock_style_manager import get_dock_style_manager
from lace.dock_styled import DockStyled
from lace.dock_theme import DockStyleCategory

REFRESHED = []


class Probe(DockStyled, QWidget):
    STYLE_CATEGORIES = (DockStyleCategory.CORE,)

    def __init__(self, name):
        super().__init__()
        self._name = name
        self._init_dock_style(refresh=False)

    def refresh_style(self):
        # Deliberately touches no C++: reading objectName() here would raise
        # RuntimeError once the widget is gone, _do_refresh would swallow it,
        # and an unowned shot that *did* fire would look exactly like one that
        # was correctly dropped. A plain Python attribute records the call
        # either way, so the two are distinguishable.
        REFRESHED.append(self._name)


def _flush(qapp):
    """Run the deferred-delete queue, then the timer queue it left behind."""
    qapp.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    qapp.processEvents()


@pytest.fixture(autouse=True)
def _clear():
    REFRESHED.clear()
    yield
    REFRESHED.clear()


def test_a_queued_restyle_still_runs_for_a_live_widget(qapp):
    """The debounce must keep working — this is what the fix must not break."""
    probe = Probe("live")

    probe.on_style_changed(DockStyleCategory.CORE, {})
    _flush(qapp)

    assert REFRESHED == ["live"], "the debounced refresh never ran"


def test_a_queued_restyle_is_dropped_when_the_widget_dies(qapp):
    probe = Probe("doomed")

    probe.on_style_changed(DockStyleCategory.CORE, {})
    probe.deleteLater()
    _flush(qapp)

    assert REFRESHED == [], \
        "the queued refresh ran after the widget was destroyed"


def test_applying_a_theme_queues_nothing_that_outlives_the_widget(qapp):
    """The real path: the shot is queued by the style manager, not by hand."""
    probe = Probe("themed")

    get_dock_style_manager().apply_theme("default")
    probe.deleteLater()
    _flush(qapp)

    assert REFRESHED == [], \
        "a theme apply left a refresh queued against a destroyed widget"
