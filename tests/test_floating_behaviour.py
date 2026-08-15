# -*- coding: utf-8 -*-
"""One implementation behind two floating containers — §5.1.

Lace ships a native-frame float and a frameless one. They were two 1000+ line
classes with the same name, ~900 lines duplicated verbatim, so every drag,
drop, resize or lifecycle fix had to land twice. It did not always: the null
guards added to the native container's is_closable() and its three sibling
delegators never reached the frameless one, which is the shape of bug this
whole extraction is about.

The shared half now lives in FloatingContainerBehaviour. These tests pin that
it is genuinely shared, that the mixin's Qt overrides actually run (an MRO
trap: listed after the Qt base, Qt's own closeEvent would win), and that the
two classes are distinguishable by name and by isinstance.
"""

import ast
import os
import pathlib
import sys
import textwrap

import pytest
from PySide6.QtWidgets import QLabel, QMainWindow

from lace.dock_manager import DockManager
from lace.dock_widget import DockWidget
from lace.enums import TitleBarMode
from lace.floating_behaviour import FloatingContainerBehaviour
from lace.floating_dock_container import FloatingDockContainer
from lace.util import find_floating_dock_container, is_floating_dock_container

LACE = pathlib.Path(__file__).resolve().parent.parent / "lace"

frameless = pytest.importorskip(
    "lace.floating_dock_container_frameless",
    reason="qframelesswindow is optional")
FramelessFloatingDockContainer = frameless.FramelessFloatingDockContainer

BOTH = (FloatingDockContainer, FramelessFloatingDockContainer)

#: qframelesswindow's macOS backend resolves the NSWindow behind the widget
#: (``objc_object(c_void_p=self.winId().__int__()).window()``). Offscreen there
#: is no native view, winId() is 0, and that dereference segfaults the
#: interpreter — a hard crash, not an exception, so nothing on our side can
#: guard it. Only the tests that actually build one are skipped; the source
#: inspection below is platform-independent and still runs.
FRAMELESS_SEGFAULTS = (sys.platform == "darwin"
                       and os.environ.get("QT_QPA_PLATFORM") == "offscreen")


def _skip_if_unbuildable(cls):
    if cls is FramelessFloatingDockContainer and FRAMELESS_SEGFAULTS:
        pytest.skip("frameless windows segfault on macOS under offscreen")


@pytest.fixture
def manager(qapp):
    win = QMainWindow()
    win.resize(800, 600)
    dock_manager = DockManager(win)
    win.show()
    qapp.processEvents()
    yield win, dock_manager
    win.close()


def _mk(name):
    dock_widget = DockWidget(name)
    dock_widget.set_widget(QLabel(name))
    return dock_widget


def _methods(path, cls_name):
    """``{name: source}`` for the methods a class defines itself."""
    src = (LACE / path).read_text(encoding="utf-8")
    tree = ast.parse(src)
    lines = src.splitlines()
    node = next(n for n in tree.body
                if isinstance(n, ast.ClassDef) and n.name == cls_name)
    out = {}
    for m in node.body:
        if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = min([m.lineno - 1] + [d.lineno - 1 for d in m.decorator_list])
            out[m.name] = textwrap.dedent("\n".join(lines[start:m.end_lineno]))
    return out


# ── The duplication itself ────────────────────────────────────────────────
def test_neither_class_redefines_a_shared_method_identically():
    """The regression guard: a fix copy-pasted back into both classes.

    An override that genuinely differs is fine — that is the subclass
    surface. Two identical bodies means the extraction has started to rot.
    """
    native = _methods("floating_dock_container.py", "FloatingDockContainer")
    frame = _methods("floating_dock_container_frameless.py",
                     "FramelessFloatingDockContainer")

    duplicated = [name for name in set(native) & set(frame)
                  if native[name] == frame[name]]
    assert not duplicated, f"identical in both classes: {duplicated}"


def test_the_shared_half_really_lives_in_the_mixin():
    """Not a token extraction — most of the surface must come from it."""
    native = set(_methods("floating_dock_container.py", "FloatingDockContainer"))
    frame = set(_methods("floating_dock_container_frameless.py",
                         "FramelessFloatingDockContainer"))
    shared = {name for name, value in vars(FloatingContainerBehaviour).items()
              if callable(value) and not name.startswith("__")}

    assert len(shared) > len(native), "the native class still owns most of itself"
    assert len(shared) > 25, f"only {len(shared)} methods were extracted"
    assert not (native & frame & shared), \
        "a class shadows a mixin method that the other one does not"


@pytest.mark.parametrize("cls", BOTH, ids=["native", "frameless"])
def test_both_inherit_the_shared_behaviour(cls):
    assert issubclass(cls, FloatingContainerBehaviour)


# ── The MRO trap ──────────────────────────────────────────────────────────
@pytest.mark.parametrize("cls", BOTH, ids=["native", "frameless"])
@pytest.mark.parametrize("name", ["closeEvent", "resizeEvent", "hideEvent",
                                  "deleteLater", "refresh_style"])
def test_the_mixins_qt_overrides_win_over_the_qt_base(cls, name):
    """Listed after the Qt base, QWidget's versions would resolve first.

    Nothing would raise — the float would simply stop closing its widgets,
    stop masking its corners and stop restyling, silently.
    """
    owner = getattr(cls, name).__qualname__.split(".")[0]
    assert owner == "FloatingContainerBehaviour", \
        f"{cls.__name__}.{name} resolves to {owner}"


@pytest.mark.parametrize("cls", BOTH, ids=["native", "frameless"])
def test_the_mixin_does_not_swallow_the_qt_constructor(cls):
    """It defines no __init__, so super().__init__(parent) reaches the Qt base."""
    assert "__init__" not in vars(FloatingContainerBehaviour)
    mro = cls.__mro__
    assert mro[1] is FloatingContainerBehaviour, \
        f"the mixin is not first in {cls.__name__}'s MRO: {[c.__name__ for c in mro[:4]]}"


# ── The divergence that motivated it ──────────────────────────────────────
@pytest.mark.parametrize("cls", BOTH, ids=["native", "frameless"])
def test_both_survive_a_cleared_container(manager, cls, qapp):
    """§5.6's guards reached only the native class while they were duplicated."""
    win, dock_manager = manager
    if cls is FramelessFloatingDockContainer:
        dock_manager.title_bar_mode = TitleBarMode.custom
    _skip_if_unbuildable(cls)
    floating = cls(dock_manager=dock_manager)
    qapp.processEvents()

    floating._dock_container = None

    assert floating.is_closable() is True
    assert floating.has_top_level_dock_widget() is False
    assert floating.top_level_dock_widget() is None
    assert floating.dock_widgets() == []
    floating.close()


# ── The subclass hook ─────────────────────────────────────────────────────
def test_the_native_container_has_nothing_to_do_on_area_changes(manager, qapp):
    """Its close button belongs to the OS frame, so the hook is a no-op."""
    win, dock_manager = manager
    assert (FloatingDockContainer._on_dock_areas_changed
            is FloatingContainerBehaviour._on_dock_areas_changed)


def test_the_frameless_container_resyncs_its_close_button(manager, qapp):
    """It draws its own close button, so it must re-evaluate on every change."""
    win, dock_manager = manager
    dock_manager.title_bar_mode = TitleBarMode.custom
    _skip_if_unbuildable(FramelessFloatingDockContainer)
    floating = FramelessFloatingDockContainer(dock_manager=dock_manager)
    qapp.processEvents()

    calls = []
    floating._update_close_button_state = lambda *a: calls.append("close")
    floating._sync_feature_signals = lambda *a: calls.append("signals")

    floating.on_dock_areas_added_or_removed()

    assert calls == ["close", "signals"], \
        "the hook stopped running, or ran in the wrong order"
    floating.close()


# ── Naming and identification ─────────────────────────────────────────────
def test_the_two_classes_no_longer_share_a_name():
    assert FloatingDockContainer.__name__ != FramelessFloatingDockContainer.__name__


def test_the_old_frameless_name_still_resolves():
    """Downstream code imported it as FloatingDockContainer."""
    assert frameless.FloatingDockContainer is FramelessFloatingDockContainer


@pytest.mark.parametrize("cls", BOTH, ids=["native", "frameless"])
def test_is_floating_dock_container_recognises_both(manager, cls, qapp):
    """isinstance(x, lace.FloatingDockContainer) is the wrong check.

    It is False for every float in custom-titlebar mode, which is exactly
    when a caller most needs to ask.
    """
    win, dock_manager = manager
    if cls is FramelessFloatingDockContainer:
        dock_manager.title_bar_mode = TitleBarMode.custom
    _skip_if_unbuildable(cls)
    floating = cls(dock_manager=dock_manager, dock_widget=_mk("Alpha"))
    qapp.processEvents()
    try:
        assert is_floating_dock_container(floating)
        assert not is_floating_dock_container(win)
        assert find_floating_dock_container(floating.dock_container()) is floating
    finally:
        floating.close()


def test_the_check_costs_no_optional_import():
    """It used to build a tuple by importing the frameless module.

    That drags in qframelesswindow, which is optional — the old version
    swallowed the ImportError and then answered False for frameless floats
    on any install without it.
    """
    import subprocess
    import sys

    code = ("import sys, lace; "
            "lace.is_floating_dock_container(object()); "
            "print('lace.floating_dock_container_frameless' in sys.modules)")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True,
                         text=True, cwd=str(LACE.parent))
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "False"


# ── The half-built event filter — §5.7 ────────────────────────────────────
#: Everything FramelessFloatingDockContainer.eventFilter reads before it can
#: know the object is fully built.
FILTER_STATE = ("_permanent_filter_installed", "_frameless_drag_filter",
                "_os_move_active", "_titlebar_drag_start")


@pytest.mark.parametrize("name", FILTER_STATE)
def test_the_filter_state_is_ready_before_init_runs(name):
    """qframelesswindow's Linux base installs the float as an *application*
    event filter from inside its own __init__ — i.e. from our super().__init__(),
    before __init__ assigns any of this.

    Everything after that line pumps events, so eventFilter runs in that window
    on a half-built object. An AttributeError there does not stay local: it
    escapes through Qt's dispatch, aborts the constructor, and leaves an orphan
    widget filtering the application for the rest of the process — every later
    widget then dies with "QMainWindow returned NULL without setting an
    exception". Class-level defaults are what make the filter safe that early.

    Asserted on the class, not an instance: an instance has already run
    __init__, which is exactly the state this is not about.
    """
    assert hasattr(FramelessFloatingDockContainer, name), \
        f"{name} is only assigned in __init__, so the filter can read it too early"


def test_the_filter_survives_a_half_built_object(manager, qapp):
    """The invariant above, exercised rather than inspected.

    A live float with its filter state stripped back off the instance is the
    state the Linux base leaves it in mid-construction: the C++ half is built
    and already installed as a filter, the Python attributes are not there yet.
    ``__new__`` cannot stand in for it — without the C++ base, the filter's
    super() call raises for an unrelated reason.

    ``titleBar`` is deliberately left alone: the base assigns it just before it
    installs the filter, so it is the one attribute eventFilter may assume.
    """
    from PySide6.QtCore import QEvent

    win, dock_manager = manager
    dock_manager.title_bar_mode = TitleBarMode.custom
    _skip_if_unbuildable(FramelessFloatingDockContainer)
    floating = FramelessFloatingDockContainer(dock_manager=dock_manager)
    qapp.processEvents()
    try:
        for name in FILTER_STATE:
            vars(floating).pop(name, None)
        assert floating.eventFilter(None, QEvent(QEvent.Type.User)) is False
    finally:
        floating.close()
