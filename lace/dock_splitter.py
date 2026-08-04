# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2019 Ken Lauer
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace, adapted from qtpydocking.
# Original code Copyright (c) 2019 Ken Lauer (BSD-3-Clause).
# Modifications Copyright (c) 2026 opticsWolf (Apache-2.0).


import logging
from typing import Optional

from PySide6.QtCore import Qt, QEvent, QSize, QRect, QPointF
from PySide6.QtGui import QPainter, QColor, QMouseEvent, QCursor
from PySide6.QtWidgets import QSplitter, QSplitterHandle, QWidget

from .dock_styled import DockStyled
from .dock_theme import DockStyleCategory

logger = logging.getLogger(__name__)


class DockSplitterHandle(QSplitterHandle, DockStyled):
    """
    Custom resize handle for the DockSplitter.

    Reacts to hover events and dynamically reads its colors and thickness
    from the global DockStyleManager.

    Multi-junction resize: when nested splitters meet (e.g. a 2x2 dock grid),
    a handle can cross a perpendicular handle at a junction.  Dragging the
    handle then *co-drags* the perpendicular handle so the whole junction
    resizes in both directions at once.  The perpendicular handles receive
    synthetic press/move/release events (with the same global position
    remapped into their own coordinate space), so each splitter keeps its own
    native Qt drag behaviour — including per-splitter rubber bands when
    opaque resize is disabled.
    """

    STYLE_CATEGORIES = (DockStyleCategory.SPLITTER,)

    #: Handles currently being co-dragged (pressed handle + perpendicular
    #: junction handles).  Class-level so every handle can paint its "active"
    #: state during the drag.
    active_drag_handles = set()

    #: The handle that started the active junction drag (for cleanup).
    _active_drag_owner: Optional['DockSplitterHandle'] = None

    def __init__(self, orientation: Qt.Orientation, parent: 'DockSplitter'):
        super().__init__(orientation, parent)
        self.setAttribute(Qt.WA_Hover, True)
        self._is_hovered = False

        # Junction state
        self._intersecting_handles: list = []   # perpendicular handles co-dragged
        self._hovered_intersecting_handles: list = []
        self._is_forwarding_event = False
        self._junction_drag_active = False

        # New: Space for layout vs visual thickness
        self._total_width = 6   # The physical clickable/gap area
        self._handle_width = 2  # The visual colored line

        self._init_dock_style()

    # ─────────────────────────────────────────────────────────────────────
    #  Junction detection
    # ─────────────────────────────────────────────────────────────────────

    def _find_intersecting_handles(self, global_pos) -> list:
        """Return all visible handles in this container whose hitbox contains
        *global_pos* (excluding ``self``)."""
        from .dock_container_widget import DockContainerWidget
        from .util import find_parent

        container = find_parent(DockContainerWidget, self)
        if container is None:
            container = self.window()

        intersecting = []
        if container is None:
            return intersecting

        hitbox_radius = 8
        for h in container.findChildren(DockSplitterHandle):
            if not h.isVisible() or h is self:
                continue
            # Get global rect
            rect = h.rect()
            top_left = h.mapToGlobal(rect.topLeft())
            bottom_right = h.mapToGlobal(rect.bottomRight())
            global_rect = QRect(top_left, bottom_right).adjusted(
                -hitbox_radius, -hitbox_radius, hitbox_radius, hitbox_radius)
            if global_rect.contains(global_pos):
                intersecting.append(h)
        return intersecting

    def _perpendicular_handles(self, global_pos) -> list:
        """Intersecting handles whose orientation differs from ours (i.e. the
        ones that actually cross us and can be co-dragged)."""
        return [h for h in self._find_intersecting_handles(global_pos)
                if h.orientation() != self.orientation()]

    # ─────────────────────────────────────────────────────────────────────
    #  Junction drag lifecycle
    # ─────────────────────────────────────────────────────────────────────

    def _begin_junction_drag(self, event: QMouseEvent):
        """Record the perpendicular handles under the cursor and arm them."""
        global_pos = event.globalPosition().toPoint()
        perpendicular = self._perpendicular_handles(global_pos)
        if not perpendicular:
            return

        # Defensive: a new press while another handle still owns a drag —
        # end the stale drag first so class state cannot mix two drags.
        owner = DockSplitterHandle._active_drag_owner
        if owner is not None and owner is not self:
            try:
                owner._end_junction_drag()
            except RuntimeError:
                pass

        self._intersecting_handles = perpendicular
        self._junction_drag_active = True
        DockSplitterHandle.active_drag_handles = {self}.union(perpendicular)
        DockSplitterHandle._active_drag_owner = self

        for h in perpendicular:
            h.setCursor(Qt.SizeAllCursor)
            self._forward_event(h, event)

    def _forward_event(self, h: 'DockSplitterHandle', event: QMouseEvent):
        """Deliver a synthetic copy of *event* to handle *h*, remapped into
        *h*'s local coordinates.  The ``_is_forwarding_event`` flag prevents
        re-entrant forwarding."""
        h._is_forwarding_event = True
        try:
            local_pos = QPointF(h.mapFromGlobal(event.globalPosition().toPoint()))
            forwarded = QMouseEvent(event.type(), local_pos,
                                    event.globalPosition(),
                                    event.button(), event.buttons(),
                                    event.modifiers())
            if event.type() == QEvent.MouseButtonPress:
                h.mousePressEvent(forwarded)
            elif event.type() == QEvent.MouseMove:
                h.mouseMoveEvent(forwarded)
            elif event.type() == QEvent.MouseButtonRelease:
                h.mouseReleaseEvent(forwarded)
        finally:
            h._is_forwarding_event = False

    def _end_junction_drag(self):
        """Tear down junction-drag state.

        Called on mouse release *and* on any interrupted drag (grab loss /
        window deactivation via ``QEvent.UngrabMouse``) so the shared
        ``active_drag_handles`` set and cursors can never stay stuck.
        """
        for h in list(self._intersecting_handles):
            try:
                h._restore_split_cursor()
            except RuntimeError:
                pass  # handle destroyed mid-drag
        self._intersecting_handles = []
        self._junction_drag_active = False
        if DockSplitterHandle._active_drag_owner is self:
            DockSplitterHandle._active_drag_owner = None
        DockSplitterHandle.active_drag_handles.clear()

    # ─────────────────────────────────────────────────────────────────────
    #  Mouse events
    # ─────────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent):
        if not self._is_forwarding_event and event.button() == Qt.LeftButton:
            self._begin_junction_drag(event)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if (not self._is_forwarding_event
                and event.buttons() & Qt.LeftButton
                and self._junction_drag_active):
            for h in list(self._intersecting_handles):
                self._forward_event(h, event)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if not self._is_forwarding_event and event.button() == Qt.LeftButton:
            if self._junction_drag_active:
                for h in list(self._intersecting_handles):
                    self._forward_event(h, event)
            self._end_junction_drag()
        super().mouseReleaseEvent(event)

    def event(self, event: QEvent):
        """Junction hover highlighting + SizeAll cursor, and cleanup when an
        active drag is interrupted (mouse grab lost)."""
        if event.type() in (QEvent.HoverMove, QEvent.HoverEnter):
            # Prefer the event's own position (deterministic); fall back to the
            # global cursor for platforms where hover positions are unreliable.
            try:
                global_pos = self.mapToGlobal(event.position().toPoint())
            except AttributeError:
                global_pos = QCursor.pos()
            perpendicular = self._perpendicular_handles(global_pos)
            has_cross = bool(perpendicular)

            # Diff against the previous hover set: un-highlight and restore
            # cursors on handles that are no longer intersecting.
            for h in self._hovered_intersecting_handles:
                if h not in perpendicular:
                    h._is_hovered = False
                    h._restore_split_cursor()
                    h.update()
            for h in perpendicular:
                if not h._is_hovered:
                    h._is_hovered = True
                    h.update()
                h.setCursor(Qt.SizeAllCursor)
            self._hovered_intersecting_handles = perpendicular

            # The handle under the cursor gets the cross cursor at a junction.
            self.setCursor(Qt.SizeAllCursor if has_cross
                           else self._split_cursor())

        elif event.type() == QEvent.HoverLeave:
            for h in self._hovered_intersecting_handles:
                h._is_hovered = False
                h._restore_split_cursor()
                h.update()
            self._hovered_intersecting_handles.clear()
            self._restore_split_cursor()

        elif event.type() == QEvent.UngrabMouse:
            # Alt-Tab / window deactivation can end a drag without a release
            # event — clean up so nothing stays highlighted or half-armed.
            if DockSplitterHandle._active_drag_owner is self:
                self._end_junction_drag()

        return super().event(event)

    # ─────────────────────────────────────────────────────────────────────
    #  Cursor helpers
    # ─────────────────────────────────────────────────────────────────────

    def _split_cursor(self) -> Qt.CursorShape:
        return (Qt.SplitHCursor if self.orientation() == Qt.Horizontal
                else Qt.SplitVCursor)

    def _restore_split_cursor(self):
        self.setCursor(self._split_cursor())

    # ─────────────────────────────────────────────────────────────────────
    #  Styling
    # ─────────────────────────────────────────────────────────────────────

    def refresh_style(self):
        """Fetches the latest splitter styles from the active theme."""
        styles = self._style_mgr.get_all(DockStyleCategory.SPLITTER)

        self._c_handle = styles.get("handle_color", QColor(45, 45, 45))
        self._c_hover = styles.get("handle_hover_color", QColor(0, 122, 204))
        self._handle_width = styles.get("handle_width", 2)
        self._total_width = styles.get("total_width", 6)
        self._handle_margin = styles.get("handle_margin", 4)  # <--- Load the margin

        self.update()

    def enterEvent(self, event: QEvent):
        """Triggered when the mouse hovers over the resize handle."""
        self._is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent):
        """Triggered when the mouse leaves the resize handle."""
        self._is_hovered = False
        self.update()
        super().leaveEvent(event)

    def sizeHint(self) -> QSize:
        """Sets the physical layout width of the splitter."""
        size = super().sizeHint()
        if self.orientation() == Qt.Horizontal:
            size.setWidth(self._total_width)
        else:
            size.setHeight(self._total_width)
        return size

    def paintEvent(self, event):
        """Paints a themed rounded-cap handle centered within a wider gap."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        is_hovered = self._is_hovered
        if DockSplitterHandle.active_drag_handles:
            try:
                is_hovered = self in DockSplitterHandle.active_drag_handles
            except RuntimeError:
                pass  # deleted handle lingering in the shared set

        color = self._c_hover if is_hovered else self._c_handle
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)

        full_rect = self.rect()
        radius = self._handle_width / 2
        m = self._handle_margin

        if self.orientation() == Qt.Horizontal:
            # Center horizontally, apply margin to top/bottom
            offset = (full_rect.width() - self._handle_width) // 2
            draw_rect = full_rect.adjusted(offset, m,
                                           -(full_rect.width() - self._handle_width - offset),
                                           -m)
        else:
            # Center vertically, apply margin to left/right
            offset = (full_rect.height() - self._handle_width) // 2
            draw_rect = full_rect.adjusted(m, offset,
                                           -m,
                                           -(full_rect.height() - self._handle_width - offset))

        painter.drawRoundedRect(draw_rect, radius, radius)


class DockSplitter(QSplitter):
    """
    The core layout divider for the docking framework.
    Manages nested child visibility and spawns customized, theme-aware handles.
    """
    def __init__(self, orientation: Qt.Orientation = Qt.Horizontal, parent: Optional[QWidget] = None):
        super().__init__(orientation, parent)
        self.setProperty("dock_splitter", True)

    def createHandle(self) -> QSplitterHandle:
        """Overrides default handle creation to inject our themed handle."""
        return DockSplitterHandle(self.orientation(), self)

    def has_visible_content(self) -> bool:
        """
        Recursively checks if this splitter contains any actually visible widgets.
        Used by the utility functions to dynamically hide empty layout branches.
        """
        for i in range(self.count()):
            widget = self.widget(i)
            if widget and not widget.isHidden():
                # If the child is also a DockSplitter, we must check it recursively
                if isinstance(widget, DockSplitter):
                    if widget.has_visible_content():
                        return True
                else:
                    return True
        return False
