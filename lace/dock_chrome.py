# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


from typing import Iterable, Optional

from PySide6.QtCore import Qt, QEvent, QObject, QPoint, QRectF, QSize, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QAbstractButton, QFrame, QSizePolicy, QToolButton, QWidget

from lace.dock_paint import ChromeTokens, paint_panel, paint_panel_bg, paint_panel_border
from lace.util import start_drag_distance


class DragDetector(QObject):
    """Emits :attr:`drag_started` once the pointer moves past the drag
    threshold with ``button`` held, without consuming the events.

    Replaces the hand-rolled mousePress/Move/Release threshold triplets that
    were duplicated across tabs and title bars.  Because the filter returns
    ``False``, the host widget still receives every event (so clicks / toggles
    keep working); this only *observes* to fire the drag signal.
    """
    drag_started = Signal(QPoint)  # global position where the press began

    def __init__(self, widget: QWidget, button: Qt.MouseButton = Qt.LeftButton):
        super().__init__(widget)
        self._button = button
        self._press_pos = None
        widget.installEventFilter(self)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        t = event.type()
        if t == QEvent.MouseButtonPress and event.button() == self._button:
            self._press_pos = event.globalPosition().toPoint()
        elif t == QEvent.MouseMove and self._press_pos is not None:
            moved = (event.globalPosition().toPoint() - self._press_pos).manhattanLength()
            if moved >= start_drag_distance():
                pos, self._press_pos = self._press_pos, None
                self.drag_started.emit(pos)
        elif t in (QEvent.MouseButtonRelease, QEvent.Leave):
            self._press_pos = None
        return False  # never consume — observers only


def resolve_title_bar_border_color(style_mgr, focused: bool = False):
    """The title bar's border colour for the given focus state.

    Mirrors what ``paint_panel_border`` does for the dock area's own outline —
    ``focus_border`` while focused, ``border`` otherwise — so the title bar and
    the area it sits in light up together. ``TITLE_BAR`` wins over ``CORE`` for
    both, letting a theme colour the strip independently of the card.
    """
    from lace.dock_theme import DockStyleCategory

    styles = style_mgr.get_all(DockStyleCategory.TITLE_BAR)
    core = style_mgr.get_all(DockStyleCategory.CORE)

    if focused:
        color = styles.get("focus_border_color") or core.get("focus_border_color")
        if color is not None:
            return color
    return styles.get("border_color") or core.get("border_color")


def resolve_title_bar_bottom_rule(style_mgr, focused: bool = False) -> tuple:
    """The effective ``(width, colour)`` of the rule under the tab/title bar.

    Returns ``(0.0, None)`` when no rule is drawn. Two callers need the same
    answer — :class:`DockAreaTitleBar`, which paints the rule across the strip,
    and :class:`DockWidgetTab`, which continues it across an inactive tab —
    so the precedence lives here rather than in each paint site.

    Precedence, mirroring ``DockAreaTitleBar.paintEvent``:

    * ``TITLE_BAR.border_width > 0`` paints a *full outline* around the strip
      and the bottom-rule branch is never reached, so this returns no rule.
    * otherwise ``border_bottom`` gives the width.
    * the colour follows :func:`resolve_title_bar_border_color`, so the rule
      swaps to the focus colour with the rest of the area's chrome.
    """
    from lace.dock_theme import DockStyleCategory

    styles = style_mgr.get_all(DockStyleCategory.TITLE_BAR)
    if (styles.get("border_width") or 0.0) > 0:
        return 0.0, None

    width = styles.get("border_bottom") or 0.0
    if width <= 0:
        return 0.0, None

    color = resolve_title_bar_border_color(style_mgr, focused)
    if color is None:
        return 0.0, None

    return float(width), color


def _indicator_edges(position) -> frozenset:
    """Normalise ``TAB.indicator_position`` to a set of lowercase edge names.

    The token accepts a single name, a whitespace/comma separated list, or a
    sequence — the same forms ``paint_tab`` parses. Anything that is not a
    recognisable name (a ``Qt.Edge``, say) is passed through as-is so callers
    can still test membership without this rejecting it outright.
    """
    if position is None:
        return frozenset()
    if isinstance(position, str):
        parts = position.replace(",", " ").split()
    elif isinstance(position, (list, tuple, set, frozenset)):
        parts = list(position)
    else:
        parts = [position]
    return frozenset(
        p.lower().strip() if isinstance(p, str) else p
        for p in parts if p is not None
    )


def tab_has_bottom_indicator(style_mgr) -> bool:
    """Whether the active tab draws an indicator along its bottom edge.

    All three of width, colour and position have to line up: a theme turns the
    indicator off with ``indicator_position = "none"`` as readily as with a
    zero width.
    """
    from lace.dock_theme import DockStyleCategory

    styles = style_mgr.get_all(DockStyleCategory.TAB)
    if (styles.get("indicator_width") or 0.0) <= 0:
        return False
    if styles.get("indicator_color") is None:
        return False
    return "bottom" in _indicator_edges(styles.get("indicator_position", "bottom"))


def resolve_sidebar_title_bar_rule(style_mgr, focused: bool = False) -> tuple:
    """The ``(width, colour)`` of the stripe under the *sidebar* title bar.

    The sidebar overlay hosts a single widget and has no tab strip, so its
    header stands in for one. The stripe therefore tracks what a dock area
    draws along that same edge, and only appears when *both* halves of that
    edge exist:

    * the dock-area title bar draws a bottom rule
      (:func:`resolve_title_bar_bottom_rule`), which supplies the colour and
      width, and
    * tabs draw an indicator along their bottom
      (:func:`tab_has_bottom_indicator`).

    A theme with a rule but no bottom indicator — ``neon_dusk`` and
    ``violet_haze``, which mark the active tab with an outline instead — gets
    no stripe, rather than a line the rest of the theme never echoes.
    """
    if not tab_has_bottom_indicator(style_mgr):
        return 0.0, None
    return resolve_title_bar_bottom_rule(style_mgr, focused)


def _contrast_step(color: QColor, amount: float) -> QColor:
    """Shift ``color`` by ``amount`` lightness in the contrasting direction
    (lighten a dark colour, darken a light one) — the same rule the theme uses
    to derive hover, so pressed continues that direction a little further.
    """
    l = color.lightnessF()
    delta = amount if l < 0.5 else -amount
    hue = color.hueF()
    if hue < 0:                     # achromatic (grey): hue is undefined
        hue = 0.0
    out = QColor.fromHslF(hue, color.saturationF(),
                          max(0.0, min(1.0, l + delta)))
    out.setAlphaF(color.alphaF())
    return out


class ChromeToolButton(QToolButton):
    """Icon tool button that paints its own rounded hover background instead of
    a ``:hover`` stylesheet colour.

    Only the *hover fill* is painted; sizing (padding / min-size / radius) stays
    a colour-free stylesheet applied by :func:`style_title_bar_buttons`, so the
    exact button metrics are preserved.  Hover is tracked by a settable flag
    (``set_hovered``) — identical under the cursor and in offscreen pixel checks,
    the same pattern ``DockWidgetTab``/``VerticalTabButton`` already use.
    """

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setAutoRaise(True)
        self._hover_bg: Optional[QColor] = None
        self._hover_radius: float = 3.0
        self._hovered = False

    def set_hover_chrome(self, hover_bg: Optional[QColor], radius: float) -> None:
        self._hover_bg = hover_bg
        self._hover_radius = max(0.0, radius)
        self.update()

    def set_hovered(self, on: bool) -> None:
        if on != self._hovered:
            self._hovered = on
            self.update()

    def enterEvent(self, event) -> None:
        self.set_hovered(True)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.set_hovered(False)
        super().leaveEvent(event)

    def paintEvent(self, event) -> None:
        pressed = self.isDown()
        if (self.isEnabled() and (self._hovered or pressed)
                and self._hover_bg is not None and self._hover_bg.alpha() > 0):
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing, True)
            path = QPainterPath()
            path.addRoundedRect(QRectF(self.rect()), self._hover_radius, self._hover_radius)
            # Pressed continues the hover's contrasting direction 0.03 further
            # (theme-consistent, unlike a flat dark wash); hover is 0.10.
            fill = _contrast_step(self._hover_bg, 0.03) if pressed else self._hover_bg
            p.fillPath(path, fill)
            p.end()
        super().paintEvent(event)   # icon (and menu arrow) draw on top


def style_title_bar_buttons(
    buttons: Iterable[QAbstractButton],
    *,
    color: QColor = None,
    hover_bg: QColor = None,
    disabled: QColor = None,
    radius: int = 3,
    padding: int = 2,
    size: int = 18,
    icon_size: int = 16,
    expand_vertical: bool = False,
) -> None:
    """Apply the shared icon-button styling used by the dock-area and sidebar
    title bars: uniform sizing + painted rounded hover background.

    The hover background is painted by :class:`ChromeToolButton` (no more
    ``:hover`` colour QSS); the stylesheet applied here carries *sizing only*
    (no colour / no ``palette()`` role), so it neither goes stale on theme
    change nor blocks deleting the theme-bridge nudge.  ``color`` / ``disabled``
    are accepted for call-site compatibility but unused — the icons are
    pre-coloured pixmaps and disabled state greys them automatically.
    """
    css = f"""
        QToolButton {{
            background: transparent;
            border: none;
            border-radius: {radius}px;
            padding: {padding}px;
            min-width: {size}px;
            min-height: {size}px;
        }}
        QToolButton::menu-indicator {{
            image: none;
        }}
    """
    v_policy = QSizePolicy.Expanding if expand_vertical else QSizePolicy.Fixed
    icon = QSize(icon_size, icon_size)
    for btn in buttons:
        # The sheet is sizing-only, so it is usually identical across themes.
        # setStyleSheet() unpolishes and repolishes the widget subtree either
        # way, so skip it unless the text actually changed.
        if getattr(btn, "_applied_chrome_qss", None) != css:
            btn._applied_chrome_qss = css
            btn.setStyleSheet(css)
        if isinstance(btn, ChromeToolButton):
            btn.set_hover_chrome(hover_bg, radius)
        if btn.sizePolicy().verticalPolicy() != v_policy:
            btn.setSizePolicy(QSizePolicy.Fixed, v_policy)
        if btn.iconSize() != icon:
            btn.setIconSize(icon)


class _ChromeBorderOverlay(QWidget):
    """Transparent overlay widget that draws the card outline stroke on top of all child widgets
    to ensure crisp, antialiased corner curves without child clipping or mask staircases."""
    def __init__(self, parent: 'ChromeFrame'):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setAutoFillBackground(False)
        self._parent = parent

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        paint_panel_border(p, QRectF(self.rect()), self._parent._chrome, self._parent._chrome_focused)


class ChromeFrame(QFrame):
    """Container panel whose visual chrome (background fill + rounded corners
    + optional outline) is painted by :func:`paint_panel_bg` and `_ChromeBorderOverlay`
    instead of Qt StyleSheets (`QFrame.setFrameStyle` is deliberately bypassed).

    The widget is transparent to Qt's native fill, so the area outside the
    rounded corners shows the *parent's* background — corners stay clean on
    any canvas colour.  A focus outline is a pen-colour swap only, so toggling
    it never changes geometry (no layout jitter).

    Subclasses (or owners) call :meth:`set_chrome` whenever the theme changes.
    """

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setAutoFillBackground(False)
        self._chrome = ChromeTokens(bg=QColor(0, 0, 0, 0))
        self._chrome_focused = False
        self._border_overlay = _ChromeBorderOverlay(self)

    def set_chrome(self, chrome: ChromeTokens) -> None:
        """Apply new chrome tokens and inset the layout so children never
        overlap the outline or the corner arcs."""
        self._chrome = chrome
        layout = self.layout()
        if layout is not None:
            m = chrome.content_margin()
            layout.setContentsMargins(m, m, m, m)
        if hasattr(self, "_border_overlay") and self._border_overlay is not None:
            self._border_overlay.setGeometry(self.rect())
            self._border_overlay.raise_()
            self._border_overlay.update()
        self.update()

    def set_chrome_focused(self, focused: bool) -> None:
        """Swap to the focus outline colour (repaint only; margins constant)."""
        if focused != self._chrome_focused:
            self._chrome_focused = focused
            if hasattr(self, "_border_overlay") and self._border_overlay is not None:
                self._border_overlay.update()
            self.update()

    def chrome(self) -> ChromeTokens:
        return self._chrome

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if hasattr(self, "_border_overlay") and self._border_overlay is not None:
            self._border_overlay.setGeometry(self.rect())
            self._border_overlay.raise_()

    def childEvent(self, event) -> None:
        super().childEvent(event)
        if event.type() in (QEvent.ChildAdded, QEvent.ChildPolished) and hasattr(self, "_border_overlay") and self._border_overlay is not None:
            if event.child() is not self._border_overlay:
                self._border_overlay.raise_()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        paint_panel_bg(p, QRectF(self.rect()), self._chrome)
