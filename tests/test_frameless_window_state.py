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
from lace.frameless_window import LaceStandardTitleBar
from lace.util import is_window_maximized, start_drag_distance

from qframelesswindow.titlebar import TitleBarButton
from qframelesswindow.titlebar.title_bar_buttons import TitleBarButtonState

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


def test_the_maximize_button_does_not_post_a_raw_window_message(
        floater, native_toggle, qapp):
    """Four entry points, one mechanism. This one used to be the odd one out.

    Lace replaced the async SC_MAXIMIZE for the *double-click*
    (LaceStandardTitleBar exists for exactly that) and left the button
    behind, so one window ended up with two disagreeing maximize states.
    LaceStandardTitleBar now disconnects the base wiring in __init__.
    """
    floater.titleBar.maxBtn.click()
    qapp.processEvents()

    assert native_toggle == []


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


@pytest.mark.parametrize("maximize_by", ["button", "double click", "dock area"])
@pytest.mark.parametrize("restore_by", ["button", "double click", "dock area"])
def test_maximize_and_restore_round_trip_across_entry_points(
        floater, native_toggle, qapp, maximize_by, restore_by):
    """The matrix that used to fail on every mixed pair.

    Same-mechanism pairs always worked; mixing them did not, because Qt's
    frameless maximize and the native one are different operations and each
    undoes only itself. There is one mechanism now, so all nine pairs are
    the same operation.
    """
    def toggle(how):
        if how == "button":
            floater.titleBar.maxBtn.click()
        elif how == "double click":
            _double_click(floater.titleBar)
        else:
            container = floater.dock_container()
            container.toggle_maximize_dock_area(container.opened_dock_areas()[0])
        qapp.processEvents()

    start = floater.geometry()

    toggle(maximize_by)
    assert floater.isMaximized(), f"{maximize_by} did not maximize"

    toggle(restore_by)
    assert not floater.isMaximized(), f"{restore_by} did not restore"
    assert floater.geometry() == start, "restore did not give the size back"


def test_the_double_click_and_the_button_share_one_toggle(
        desk, native_toggle, qapp, monkeypatch):
    """Both gestures route through LaceStandardTitleBar.toggle_max_state().

    Pinned so a future edit cannot quietly give one of them its own body
    again — that divergence is the whole defect. Patched on the class before
    the float exists, because the button's connection binds in __init__.
    """
    win, dock_manager = desk
    calls = []
    monkeypatch.setattr(LaceStandardTitleBar, "toggle_max_state",
                        lambda self: calls.append("toggle"))

    floating = _make_float(dock_manager, qapp)
    try:
        floating.titleBar.maxBtn.click()
        qapp.processEvents()
        _double_click(floating.titleBar)
        qapp.processEvents()

        assert calls == ["toggle", "toggle"]
    finally:
        floating.close()


# ── dragging out of maximize ──────────────────────────────────────────────
def test_dragging_a_maximized_float_restores_it_first(floater, os_move, qapp):
    """Grab a maximized window by the title bar and it comes loose.

    Windows implements this for native frames in the WM_NCLBUTTONDOWN
    HTCAPTION path, which a client-area title bar never receives. Asking
    the OS to SC_MOVE a maximized window instead is refused outright, so
    before the fix the drag neither restored nor moved anything.
    """
    floater.showMaximized()
    qapp.processEvents()

    _drag(floater.titleBar, qapp)

    assert not is_window_maximized(floater), \
        "the float was dragged while still maximized"
    assert len(os_move) == 1, "the move never started"


def test_the_rip_out_keeps_the_grab_where_it_was(floater, os_move, qapp):
    """Restore under the pointer, not away from it.

    Grabbing a maximized float three quarters of the way across its title
    bar should leave the pointer three quarters of the way across the
    restored one — otherwise the window jumps out from under the cursor and
    the drag continues from somewhere the user did not click.
    """
    floater.showMaximized()
    qapp.processEvents()
    grab = QPoint(int(floater.width() * 0.75), 16)
    # The rip-out anchors on the position the drag threshold was crossed at,
    # which is the move, not the press.
    released_at = grab + QPoint(start_drag_distance() + 20, 4)
    fraction_before = released_at.x() / floater.width()
    # Pin the screen position now: the window moves out from under it.
    on_screen = floater.titleBar.mapToGlobal(released_at)

    _send(floater.titleBar, QEvent.MouseButtonPress, grab)
    qapp.processEvents()
    _send(floater.titleBar, QEvent.MouseMove, released_at)
    qapp.processEvents()

    assert not is_window_maximized(floater)
    # Where that screen position now sits inside the restored window.
    local = floater.mapFromGlobal(on_screen)
    fraction_after = local.x() / floater.width()
    assert abs(fraction_after - fraction_before) < 0.05, (
        f"grab moved from {fraction_before:.2f} to {fraction_after:.2f} "
        "across the title bar")
    assert 0 <= local.y() < floater.titleBar.height(), \
        "the pointer is no longer on the title bar"


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


def test_a_completed_button_click_leaves_the_title_bar_draggable(
        desk, native_toggle, qapp, monkeypatch):
    """canDrag() is ``_isDragRegion(pos) and not _hasButtonPressed()``.

    qframelesswindow's TitleBarButton sets PRESSED in mousePressEvent and
    clears it only from enterEvent/leaveEvent, so a button stuck in PRESSED
    made the whole bar undraggable and _handle_titlebar_drag declined every
    press.

    The handler is stubbed out so the window does not resize. A maximize
    normally moves the right-aligned button away from the cursor, which
    delivers the leaveEvent that cleared the state by accident — but that is
    a side effect of the handler, not the button doing its own bookkeeping,
    and it is the difference between "always" and the "often" in the bug
    report.
    """
    win, dock_manager = desk
    monkeypatch.setattr(LaceStandardTitleBar, "toggle_max_state",
                        lambda self: None)
    floating = _make_float(dock_manager, qapp)
    try:
        button = floating.titleBar.maxBtn
        centre = button.rect().center()

        _send(button, QEvent.MouseButtonPress, centre)
        qapp.processEvents()
        assert button.isPressed()
        assert not floating.titleBar.canDrag(GRIP), \
            "precondition: a held button blocks the drag"

        _send(button, QEvent.MouseButtonRelease, centre, buttons=Qt.NoButton)
        qapp.processEvents()

        assert not button.isPressed()
        assert floating.titleBar.canDrag(GRIP)
    finally:
        floating.close()


def test_every_title_bar_button_clears_its_own_state(floater, qapp):
    """Not just the maximize button — any of them blocks the whole bar.

    _hasButtonPressed() iterates every TitleBarButton child with no
    visibility check, so the minimize button blocks the drag even in the
    default configuration where it is hidden.

    The state is set directly rather than by clicking, so no button's actual
    action fires: QAbstractButton only emits clicked() when it isDown().
    """
    title_bar = floater.titleBar
    buttons = title_bar.findChildren(TitleBarButton)
    assert len(buttons) >= 3, f"expected min/max/close, found {len(buttons)}"

    for button in buttons:
        name = type(button).__name__
        button.setState(TitleBarButtonState.PRESSED)
        assert not title_bar.canDrag(GRIP), f"precondition failed for {name}"

        _send(button, QEvent.MouseButtonRelease, button.rect().center(),
              buttons=Qt.NoButton)
        qapp.processEvents()

        assert not button.isPressed(), f"{name} stayed pressed"
        assert title_bar.canDrag(GRIP), f"{name} still blocks the drag"


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
