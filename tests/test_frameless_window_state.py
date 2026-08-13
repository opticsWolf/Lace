# -*- coding: utf-8 -*-
"""Maximize / restore / minimize on a frameless float — docs/FRAMELESS_WINDOW_STATE.md.

A frameless float has four ways to get maximized and they do not agree.
Three of them are Qt-side (``showMaximized()``/``showNormal()``): the
title-bar double-click, the dock-area maximize button, and layout restore.
The fourth — qframelesswindow's own title-bar maximize button — posts a raw
``WM_SYSCOMMAND SC_MAXIMIZE`` to the HWND.

For a frameless window those are not the same operation. Qt's maximize is a
pure geometry change that leaves the Win32 placement at ``SW_NORMAL``; the
native one sets ``SW_MAXIMIZED`` and Qt only observes it. Undoing one with
the other does not work, and undoing a native maximize with ``showNormal()``
is worse than a no-op: the second attempt flips Qt's flag to False while the
window stays maximized, after which ``isMaximized()`` lies to every caller.
That single desync produces three of the four reported symptoms — the dead
double-click, the un-rippable maximize, and the float that can no longer be
moved (Windows refuses ``SC_MOVE`` for a zoomed window, and ``SC_MOVE`` is
the only move mechanism qframelesswindow has).

The tests that currently fail are ``xfail(strict=True)``: when a fix lands
they XPASS, which fails the suite, which forces the marker out.

Nothing here may touch a real HWND — the suite runs offscreen — so the two
native entry points (``toggleMaxState`` and ``startSystemMove``) are trapped
by fixtures. Trapping them is also what makes the mechanism observable.
"""

import pytest
from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow

from lace.dock_manager import DockManager
from lace.dock_widget import DockWidget
from lace.enums import DockFlags, DragState, TitleBarMode
from lace.util import start_drag_distance

frameless = pytest.importorskip(
    "lace.floating_dock_container_frameless",
    reason="qframelesswindow is optional")
FramelessFloatingDockContainer = frameless.FramelessFloatingDockContainer

#: A point on the draggable part of the title bar: left of the min/max/close
#: buttons and inside the 32px bar.
GRIP = QPoint(60, 16)


# ── fixtures ──────────────────────────────────────────────────────────────
@pytest.fixture
def desk(qapp):
    win = QMainWindow()
    win.resize(900, 600)
    dock_manager = DockManager(win)
    dock_manager.title_bar_mode = TitleBarMode.custom
    win.show()
    qapp.processEvents()
    yield win, dock_manager
    win.close()


def _make_float(dock_manager, qapp):
    dock_widget = DockWidget("Alpha")
    dock_widget.set_widget(QLabel("Alpha"))
    floating = FramelessFloatingDockContainer(dock_manager=dock_manager,
                                              dock_widget=dock_widget)
    floating.resize(500, 400)
    floating.move(120, 120)
    floating.show()
    qapp.processEvents()
    return floating


@pytest.fixture
def floater(desk, qapp):
    """A shown frameless float at a known geometry, stock configuration."""
    win, dock_manager = desk
    floating = _make_float(dock_manager, qapp)
    yield floating
    floating.close()


@pytest.fixture
def taskbar_floater(desk, qapp):
    """A float built with DockFlags.floating_taskbar_button set."""
    win, dock_manager = desk
    dock_manager.config_flags |= DockFlags.floating_taskbar_button
    floating = _make_float(dock_manager, qapp)
    yield floating
    floating.close()


@pytest.fixture
def native_toggle(monkeypatch):
    """Trap qframelesswindow's Win32 maximize; return the list of calls.

    ``TitleBarBase.__toggleMaxState`` resolves ``toggleMaxState`` from its own
    module globals at call time, so patching it there catches the maximize
    button. Without the trap the button would PostMessage to a winId() that
    the offscreen plugin never backed with a window.
    """
    import qframelesswindow.titlebar as qf_titlebar

    calls = []
    monkeypatch.setattr(qf_titlebar, "toggleMaxState", calls.append)
    return calls


@pytest.fixture
def os_move(monkeypatch):
    """Trap the OS move loop; return the list of (window, pos) calls."""
    import qframelesswindow.utils as qf_utils

    calls = []
    monkeypatch.setattr(qf_utils, "startSystemMove",
                        lambda window, pos: calls.append((window, pos)))
    return calls


# ── event helpers ─────────────────────────────────────────────────────────
def _send(widget, event_type, pos, buttons=Qt.LeftButton):
    event = QMouseEvent(event_type, pos, widget.mapToGlobal(pos),
                        Qt.LeftButton, buttons, Qt.NoModifier)
    QApplication.sendEvent(widget, event)


def _double_click(title_bar, pos=GRIP):
    _send(title_bar, QEvent.MouseButtonDblClick, pos)


def _drag(title_bar, qapp, start=GRIP):
    """Press on the title bar and move past the drag threshold."""
    _send(title_bar, QEvent.MouseButtonPress, start)
    qapp.processEvents()
    _send(title_bar, QEvent.MouseMove,
          start + QPoint(start_drag_distance() + 20, 4))
    qapp.processEvents()


# ── one notion of "maximized" ─────────────────────────────────────────────
def test_double_clicking_the_title_bar_round_trips(floater, qapp):
    """The reference behaviour: maximize and restore, geometry included."""
    start = floater.geometry()

    _double_click(floater.titleBar)
    qapp.processEvents()
    assert floater.isMaximized()

    _double_click(floater.titleBar)
    qapp.processEvents()
    assert not floater.isMaximized()
    assert floater.geometry() == start, "restore did not give the size back"


def test_the_dock_area_button_maximizes_the_whole_float(floater, qapp):
    """A solo-area float delegates its area maximize to the window itself."""
    container = floater.dock_container()
    area = container.opened_dock_areas()[0]
    assert container.visible_dock_area_count() == 1

    container.toggle_maximize_dock_area(area)
    qapp.processEvents()
    assert floater.isMaximized()
    assert container.is_area_maximized(area)

    container.toggle_maximize_dock_area(area)
    qapp.processEvents()
    assert not floater.isMaximized()
    assert not container.is_area_maximized(area)


def test_every_reader_of_the_state_agrees_after_a_double_click(floater, qapp):
    """is_area_maximized() and the button icon both read isMaximized().

    Which is why desyncing that one flag takes the dock-area maximize icon
    and the title-bar icon down with it.
    """
    container = floater.dock_container()
    area = container.opened_dock_areas()[0]

    _double_click(floater.titleBar)
    qapp.processEvents()

    assert floater.isMaximized()
    assert container.is_area_maximized(area)
    assert floater.titleBar.maxBtn._isMax, "the title-bar icon still says 'maximize'"


@pytest.mark.xfail(strict=True, reason=(
    "the maximize button is still wired to qframelesswindow's toggleMaxState, "
    "which posts WM_SYSCOMMAND SC_MAXIMIZE instead of using Qt's maximize"))
def test_the_maximize_button_does_not_post_a_raw_window_message(
        floater, native_toggle, qapp):
    """Four entry points, one mechanism. This is the odd one out.

    Lace already replaced the async SC_MAXIMIZE for the *double-click*
    (LaceStandardTitleBar exists for exactly that); the button was left
    behind, so one window ends up with two disagreeing maximize states.
    """
    floater.titleBar.maxBtn.click()
    qapp.processEvents()

    assert native_toggle == []


@pytest.mark.xfail(strict=True, reason=(
    "the maximize button takes the native path, so Qt never learns the "
    "window was maximized and the restore click cannot undo it"))
def test_the_maximize_button_round_trips(floater, native_toggle, qapp):
    """The user-visible contract, through the button rather than the bar."""
    start = floater.geometry()

    floater.titleBar.maxBtn.click()
    qapp.processEvents()
    assert floater.isMaximized()

    floater.titleBar.maxBtn.click()
    qapp.processEvents()
    assert not floater.isMaximized()
    assert floater.geometry() == start


# ── dragging out of maximize ──────────────────────────────────────────────
@pytest.mark.xfail(strict=True, reason=(
    "nothing in the chain restores the window before starting the move; "
    "qframelesswindow has the same gap and Lace consumes the MouseMove "
    "before the title bar could do anything about it"))
def test_dragging_a_maximized_float_restores_it_first(floater, os_move, qapp):
    """Grab a maximized window by the title bar and it should come loose.

    Windows implements this for native frames in the WM_NCLBUTTONDOWN
    HTCAPTION path, which a client-area title bar never receives. Asking
    the OS to SC_MOVE a maximized window instead is refused outright.
    """
    floater.showMaximized()
    qapp.processEvents()

    _drag(floater.titleBar, qapp)

    assert not floater.isMaximized(), "the float was dragged while still maximized"


def test_dragging_a_normal_float_starts_the_os_move_loop(floater, os_move, qapp):
    """The path a restore-first fix must not break."""
    _drag(floater.titleBar, qapp)

    assert floater._dragging_state is DragState.floating_widget
    assert floater._os_move_active is True
    assert len(os_move) == 1, f"startSystemMove called {len(os_move)} times"


def test_a_maximize_restore_cycle_leaves_the_drag_machinery_clean(floater, qapp):
    """Rules the drag state machine out as the cause of the stuck float.

    It is not a stale drag, a leftover app filter or a stale mouse grab —
    the machinery finishes clean every time. The float stops moving because
    the OS refuses the move, not because Lace forgot to disarm.
    """
    _double_click(floater.titleBar)
    qapp.processEvents()
    _double_click(floater.titleBar)
    qapp.processEvents()

    assert floater._dragging_state is DragState.inactive
    assert floater._os_move_active is False
    assert floater._frameless_drag_filter is False
    assert not floater.titleBar._hasButtonPressed()
    assert floater.titleBar.canDrag(GRIP)


@pytest.mark.xfail(strict=True, reason=(
    "qframelesswindow's TitleBarButton sets PRESSED on mousePressEvent and "
    "only ever clears it from enterEvent/leaveEvent, so a completed click "
    "leaves canDrag() False until the cursor happens to cross the button"))
def test_a_completed_button_click_leaves_the_title_bar_draggable(
        floater, native_toggle, qapp):
    """canDrag() is ``_isDragRegion(pos) and not _hasButtonPressed()``.

    A button stuck in PRESSED makes the whole bar undraggable, and
    _handle_titlebar_drag then declines every press. On a real display the
    maximize usually resizes the window out from under the cursor, which
    delivers the leaveEvent that clears it — which is the "often" in the
    report rather than a second, separate bug.
    """
    button = floater.titleBar.maxBtn
    centre = button.rect().center()

    _send(button, QEvent.MouseButtonPress, centre)
    qapp.processEvents()
    assert button.isPressed()
    assert not floater.titleBar.canDrag(GRIP), "precondition: a held button blocks the drag"

    _send(button, QEvent.MouseButtonRelease, centre, buttons=Qt.NoButton)
    qapp.processEvents()

    assert not button.isPressed()
    assert floater.titleBar.canDrag(GRIP)


# ── minimize, and where the window goes ───────────────────────────────────
def _offered(floating):
    """``{button: (declared in window flags, shown in the title bar)}``."""
    flags = floating.windowFlags()
    title_bar = floating.titleBar
    return {
        "minimize": (bool(flags & Qt.WindowMinimizeButtonHint),
                     title_bar.minBtn.isVisible()),
        "maximize": (bool(flags & Qt.WindowMaximizeButtonHint),
                     title_bar.maxBtn.isVisible()),
        "close": (bool(flags & Qt.WindowCloseButtonHint),
                  title_bar.closeBtn.isVisible()),
    }


@pytest.mark.parametrize("fixture", ["floater", "taskbar_floater"])
def test_the_declared_window_buttons_match_the_ones_on_offer(fixture, request):
    """A button the title bar shows must be one the window asked for.

    The float used to show a minimize button while never requesting
    Qt.WindowMinimizeButtonHint — it worked anyway, because
    qframelesswindow's addWindowAnimation() ORs WS_MINIMIZEBOX straight onto
    the HWND. Which meant the float could be minimized into a taskbar it had
    no button in, and Alt-Tab skips owned windows too, so it was simply gone.
    """
    floating = request.getfixturevalue(fixture)
    mismatched = {name: pair for name, pair in _offered(floating).items()
                  if pair[0] != pair[1]}
    assert not mismatched, f"declared != shown: {mismatched}"


def test_a_stock_float_offers_no_way_to_minimize_itself(floater):
    """Default configuration: no taskbar button, therefore no minimize."""
    assert not floater._wants_taskbar_button()
    assert not floater.titleBar.minBtn.isVisible()
    assert not (floater.windowFlags() & Qt.WindowMinimizeButtonHint)


def test_the_flag_turns_the_minimize_button_on(taskbar_floater):
    """DockFlags.floating_taskbar_button is what buys the minimize button."""
    assert taskbar_floater._wants_taskbar_button()
    assert taskbar_floater.titleBar.minBtn.isVisible()
    assert taskbar_floater.windowFlags() & Qt.WindowMinimizeButtonHint


def test_the_flag_is_opt_in(desk):
    """Eight floating panels would otherwise mean eight taskbar entries."""
    win, dock_manager = desk
    assert DockFlags.floating_taskbar_button not in DockFlags.default_config
    assert DockFlags.floating_taskbar_button not in dock_manager.config_flags


def test_toggling_the_flag_reaches_a_float_that_already_exists(floater, desk, qapp):
    """set_config_flags() fans out through update_window_flags_from_config().

    The path that matters: the window-flag set now depends on config, so a
    float built before the flag was set has to pick it up — and give it back.
    """
    win, dock_manager = desk
    assert not floater.titleBar.minBtn.isVisible()

    dock_manager.config_flags |= DockFlags.floating_taskbar_button
    qapp.processEvents()

    assert floater.titleBar.minBtn.isVisible()
    assert floater.windowFlags() & Qt.WindowMinimizeButtonHint

    dock_manager.config_flags &= ~DockFlags.floating_taskbar_button
    qapp.processEvents()

    assert not floater.titleBar.minBtn.isVisible()
    assert not (floater.windowFlags() & Qt.WindowMinimizeButtonHint)


def test_the_float_is_an_owned_top_level_window(floater, desk):
    """Why an owned float needs the ex-style at all.

    Qt hands a parented top-level its parent's HWND as the Win32 *owner*,
    and an owned window is excluded from the taskbar unless WS_EX_APPWINDOW
    says otherwise. The parenting is deliberate — it keeps floats stacked
    above the main window — so the fix is the ex-style, not unparenting.
    """
    win, dock_manager = desk

    assert floater.isWindow()
    assert floater.parent() is dock_manager.root_container()


def test_the_window_flag_set_has_one_spelling(floater, qapp):
    """__init__ and update_window_flags_from_config() both call _window_flags().

    They used to hardcode the set twice, which stopped being merely redundant
    once the set started depending on a config flag: a refresh would have
    silently handed the window different capabilities than construction did.
    """
    before = floater.windowFlags()

    floater.update_window_flags_from_config()
    qapp.processEvents()

    assert floater.windowFlags() == before == floater._window_flags()
