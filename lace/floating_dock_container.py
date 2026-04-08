# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2019 Ken Lauer
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0

This file is part of Lace, adapted from qtpydocking.
Original code Copyright (c) 2019 Ken Lauer (BSD-3-Clause).
Modifications Copyright (c) 2026 opticsWolf (Apache-2.0).
"""

from typing import TYPE_CHECKING
import logging

from PySide6.QtCore import (QEvent, QObject, QPoint, QRect, QSize, Qt, QTimer)
from PySide6.QtGui import QCloseEvent, QCursor, QHideEvent, QMoveEvent, QMouseEvent
from PySide6.QtWidgets import QApplication, QBoxLayout, QWidget

from .enums import DockWidgetFeature, DragState, DockWidgetArea
from .dock_container_widget import DockContainerWidget

if TYPE_CHECKING:
    from . import DockAreaWidget, DockWidget, DockManager

logger = logging.getLogger(__name__)

_z_order_counter = 0


class FloatingDockContainer(QWidget):
    def __init__(self, *, dock_area: 'DockAreaWidget' = None,
                 dock_widget: 'DockWidget' = None,
                 dock_manager: 'DockManager' = None):
        if dock_manager is None:
            if dock_area is not None:
                dock_manager = dock_area.dock_manager()
            elif dock_widget is not None:
                dock_manager = dock_widget.dock_manager()

        if dock_manager is None:
            raise ValueError('Must pass in either dock_area, dock_widget, or dock_manager')

        super().__init__(dock_manager)
        
        # --- UPDATED: Apply the default application icon ---
        app_icon = QApplication.instance().windowIcon()
        if not app_icon.isNull():
            self.setWindowIcon(app_icon)
        
        self._dock_container: DockContainerWidget = None
        global _z_order_counter
        _z_order_counter += 1
        self._z_order_index = _z_order_counter
        
        self._dock_manager = dock_manager
        self._dragging_state = DragState.inactive
        self._drag_start_mouse_position = QPoint()
        self._drop_container: DockContainerWidget = None
        self._single_dock_area: 'DockAreaWidget' = None
        
        self._mouse_event_handler: QWidget = None

        dock_container = DockContainerWidget(dock_manager, self)
        self._dock_container = dock_container
        dock_container.destroyed.connect(self._destroyed)
        dock_container.dock_areas_added.connect(self.on_dock_areas_added_or_removed)
        dock_container.dock_areas_removed.connect(self.on_dock_areas_added_or_removed)

        self.setWindowFlags(Qt.Window | Qt.WindowMaximizeButtonHint | Qt.WindowCloseButtonHint)
        
        layout = QBoxLayout(QBoxLayout.TopToBottom)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setLayout(layout)

        layout.addWidget(dock_container, 1)

        dock_manager.register_floating_widget(self)

        if dock_area is not None:
            dock_container.add_dock_area(dock_area)
        elif dock_widget is not None:
            dock_container.add_dock_widget(DockWidgetArea.center, dock_widget)
            
        self._ignore_synthetic_release = False
        
    def __repr__(self):
        return f'<FloatingDockContainer container={self._dock_container}>'

    # ─────────────────────────────────────────────────────────────────────
    #  Drag Lifecycle
    # ─────────────────────────────────────────────────────────────────────

    def _end_programmatic_drag(self):
        """Deferred cleanup for programmatic drags (path A/C)."""
        logger.debug("[FDC._end_programmatic_drag] START")
        self.setWindowOpacity(1.0)
        logger.debug("[FDC._end_programmatic_drag] END")
        self._finalize_drag()

    def _finalize_drag(self):
        """Attempt to drop into a container, or survive as an independent window."""
        logger.debug(f"[FDC._finalize_drag] START. "
                     f"Drop container: {self._drop_container}, "
                     f"Active Window: {QApplication.activeWindow()}")

        self._set_state(DragState.inactive)

        if not self._drop_container:
            logger.debug("[FDC._finalize_drag] No drop container — surviving as independent window.")
            self._activate_window()
            return

        dock_area_overlay = self._dock_manager.dock_area_overlay()
        container_overlay = self._dock_manager.container_overlay()

        dropped = False
        if any(overlay.drop_area_under_cursor() != DockWidgetArea.invalid
               for overlay in (dock_area_overlay, container_overlay)):

            overlay = container_overlay
            if not overlay.drop_overlay_rect().isValid():
                overlay = dock_area_overlay

            rect = overlay.drop_overlay_rect()
            if not rect.isValid():
                logger.debug("[FDC._finalize_drag] Invalid overlay rect.")
            else:
                frame_width = (self.frameSize().width() - self.rect().width()) // 2
                title_bar_height = int(
                    self.frameSize().height() - self.rect().height() - frame_width)
                top_left = overlay.mapToGlobal(rect.topLeft())
                top_left.setY(top_left.y() + title_bar_height)
                geom = QRect(top_left,
                             QSize(rect.width(), rect.height() - title_bar_height))
                self.setGeometry(geom)

            logger.debug(f"[FDC._finalize_drag] Dropping into {self._drop_container}")
            self._drop_container.drop_floating_widget(self, QCursor.pos())
            dropped = True

        # Always hide overlays and clear the reference
        container_overlay.hide_overlay()
        dock_area_overlay.hide_overlay()
        self._drop_container = None

        if not dropped:
            logger.debug("[FDC._finalize_drag] Drop zone invalid — surviving as independent window.")
            self._activate_window()

    def _activate_window(self):
        """Bring this floating window to the front and give it focus."""
        logger.debug(f"[FDC._activate_window] START. "
                     f"Active Window: {QApplication.activeWindow()}, "
                     f"Mouse Grabber: {QWidget.mouseGrabber()}")
        try:
            self.raise_()
            self.activateWindow()
            if self._dock_container:
                self._dock_container.setFocus()
            logger.debug(f"[FDC._activate_window] Done. "
                         f"Active Window: {QApplication.activeWindow()}")
        except RuntimeError:
            logger.debug("[FDC._activate_window] Window was deleted before activation.")

    # ─────────────────────────────────────────────────────────────────────
    #  Drop overlay tracking (shared by both drag paths via moveEvent)
    # ─────────────────────────────────────────────────────────────────────

    def _update_drop_overlays(self, global_pos: QPoint):
        if not self.isVisible() or not self._dock_manager:
            return

        top_container = None
        for container_widget in self._dock_manager.dock_containers():
            try:
                if not container_widget.isVisible():
                    continue
                if self._dock_container is container_widget:
                    continue

                mapped_pos = container_widget.mapFromGlobal(global_pos)
                if container_widget.rect().contains(mapped_pos):
                    if not top_container or container_widget.is_in_front_of(top_container):
                        top_container = container_widget
            except RuntimeError:
                # Safely ignore containers that were deleted in C++
                pass

        self._drop_container = top_container
        container_overlay = self._dock_manager.container_overlay()
        dock_area_overlay = self._dock_manager.dock_area_overlay()
        if not top_container:
            logger.debug('update_drop_overlays: No top container')
            container_overlay.hide_overlay()
            dock_area_overlay.hide_overlay()
            return

        logger.debug('update_drop_overlays: top container=%s name=%s',
                     self._drop_container, self._drop_container.objectName())

        visible_dock_areas = top_container.visible_dock_area_count()
        container_overlay.set_allowed_areas(
            DockWidgetArea.outer_dock_areas
            if visible_dock_areas > 1
            else DockWidgetArea.all_dock_areas
        )

        container_area = container_overlay.show_overlay(top_container)
        container_overlay.enable_drop_preview(container_area != DockWidgetArea.invalid)
        dock_area = top_container.dock_area_at(global_pos)

        if dock_area and dock_area.isVisible() and visible_dock_areas > 0:
            dock_area_overlay.enable_drop_preview(True)
            dock_area_overlay.set_allowed_areas(
                DockWidgetArea.no_area
                if visible_dock_areas == 1
                else DockWidgetArea.all_dock_areas)
            area = dock_area_overlay.show_overlay(dock_area)

            if (area == DockWidgetArea.center and
                    container_area != DockWidgetArea.invalid):
                dock_area_overlay.enable_drop_preview(False)
                container_overlay.enable_drop_preview(True)
            else:
                container_overlay.enable_drop_preview(DockWidgetArea.invalid == area)
        else:
            dock_area_overlay.hide_overlay()

    # ─────────────────────────────────────────────────────────────────────
    #  Internal helpers
    # ─────────────────────────────────────────────────────────────────────

    def _set_state(self, state_id: DragState):
        self._dragging_state = state_id

    def _set_window_title(self, text: str):
        self.setWindowTitle(text)

    def _destroyed(self):
        dock_container = self._dock_container
        self._dock_container = None
        if dock_container is not None:
            self._dock_manager.remove_dock_container(dock_container)
            self._dock_manager.remove_floating_widget(self)

    def deleteLater(self):
        self._destroyed()
        super().deleteLater()

    # ─────────────────────────────────────────────────────────────────────
    #  Title / dock-area bookkeeping
    # ─────────────────────────────────────────────────────────────────────

    def on_dock_areas_added_or_removed(self):
        logger.debug('FloatingDockContainer.onDockAreasAddedOrRemoved()')
        
        try:
            top_level_dock_area = self._dock_container.top_level_dock_area()
            dock_areas = self._dock_container.opened_dock_areas()
        except RuntimeError:
            # Reached if _dock_container is unstable/deleting
            return
        
        # If the container is split, top_level_dock_area is None.
        # Ensure we always have an area (fallback to index 0) to prevent staling.
        target_area = top_level_dock_area if top_level_dock_area else (dock_areas[0] if dock_areas else None)

        try:
            is_different = self._single_dock_area != target_area
        except RuntimeError:
            # Previous reference was destroyed in C++ (common during splits)
            is_different = True

        if is_different:
            if self._single_dock_area:
                try:
                    self._single_dock_area.current_changed.disconnect(self.on_dock_area_current_changed)
                except (RuntimeError, TypeError):
                    pass
            self._single_dock_area = target_area
            if self._single_dock_area:
                try:
                    self._single_dock_area.current_changed.connect(self.on_dock_area_current_changed)
                except (RuntimeError, TypeError):
                    pass

        try:
            if self._single_dock_area:
                widget = self._single_dock_area.current_dock_widget()
                title = widget.windowTitle() if widget else QApplication.applicationDisplayName()
            else:
                title = QApplication.applicationDisplayName()
        except RuntimeError:
            title = QApplication.applicationDisplayName()
            
        self._set_window_title(title)

    def on_dock_area_current_changed(self, index: int):
        try:
            widget = self._single_dock_area.current_dock_widget()
            if widget:
                self._set_window_title(widget.windowTitle())
        except RuntimeError:
            pass

    # ─────────────────────────────────────────────────────────────────────
    #  Public drag API
    # ─────────────────────────────────────────────────────────────────────

    def start_floating(self, drag_start_mouse_pos: QPoint, size: QSize,
                       drag_state: DragState,
                       mouse_event_handler: QWidget = None):
        self.resize(size)
        self._set_state(drag_state)
        self._drag_start_mouse_position = drag_start_mouse_pos
        
        if drag_state == DragState.floating_widget:
            self.setWindowOpacity(0.6)
            self._mouse_event_handler = mouse_event_handler
            
            # Arm the guard against the OS synthetic release.
            # Using 50ms buffer instead of 0 to ensure the event loop has fully processed 
            # the grabMouse handoff before we start accepting releases.
            self._ignore_synthetic_release = True
            QTimer.singleShot(50, self._clear_synthetic_release_flag)
                
        self.move_floating()
        self.show()

        if drag_state == DragState.floating_widget:
            if self._mouse_event_handler:
                self._mouse_event_handler.grabMouse()
            QApplication.instance().installEventFilter(self)

    def _clear_synthetic_release_flag(self):
        self._ignore_synthetic_release = False

    def start_dragging(self, drag_start_mouse_pos: QPoint, size: QSize,
                       mouse_event_handler: QWidget = None):
        self.start_floating(drag_start_mouse_pos, size,
                            DragState.floating_widget, mouse_event_handler)

    def init_floating_geometry(self, drag_start_mouse_pos: QPoint, size: QSize):
        self.start_floating(drag_start_mouse_pos, size, DragState.inactive)

    def move_floating(self):
        border_size = (self.frameSize().width() - self.size().width()) / 2
        move_to_pos = QCursor.pos() - self._drag_start_mouse_position - QPoint(int(border_size), 0)
        self.move(move_to_pos)

    # ─────────────────────────────────────────────────────────────────────
    #  State persistence
    # ─────────────────────────────────────────────────────────────────────

    def restore_state(self, state: dict, testing: bool) -> bool:
        if not self._dock_container.restore_state(state, testing):
            return False
        self.on_dock_areas_added_or_removed()
        return True

    def update_window_title(self):
        try:
            top_level_dock_area = self._dock_container.top_level_dock_area()
            if top_level_dock_area is not None:
                title = top_level_dock_area.current_dock_widget().windowTitle()
            else:
                title = QApplication.applicationDisplayName()
        except RuntimeError:
            title = QApplication.applicationDisplayName()
        self._set_window_title(title)

    # ─────────────────────────────────────────────────────────────────────
    #  Qt event overrides
    # ─────────────────────────────────────────────────────────────────────

    def changeEvent(self, event: QEvent):
        super().changeEvent(event)
        if (event.type() == QEvent.ActivationChange) and self.isActiveWindow():
            logger.debug('FloatingWidget.changeEvent QEvent.ActivationChange')
            global _z_order_counter
            _z_order_counter += 1
            self._z_order_index = _z_order_counter

    def moveEvent(self, event: QMoveEvent):
        super().moveEvent(event)
        state = self._dragging_state
        if state == DragState.mouse_pressed:
            self._set_state(DragState.floating_widget)
            self._update_drop_overlays(QCursor.pos())
        elif state == DragState.floating_widget:
            self._update_drop_overlays(QCursor.pos())

    def event(self, e: QEvent) -> bool:
        """Handle native (OS) title-bar drag lifecycle (path B)."""
        state = self._dragging_state
        if state == DragState.inactive:
            if e.type() == QEvent.NonClientAreaMouseButtonPress:
                logger.debug('FloatingWidget.event Event.NonClientAreaMouseButtonPress %s', e.type())
                self._set_state(DragState.mouse_pressed)
        elif state == DragState.mouse_pressed:
            if e.type() == QEvent.NonClientAreaMouseButtonDblClick:
                logger.debug('FloatingWidget.event QEvent.NonClientAreaMouseButtonDblClick')
                self._set_state(DragState.inactive)
            elif e.type() == QEvent.Resize:
                if not self.isMaximized():
                    self._set_state(DragState.inactive)
            elif e.type() == QEvent.NonClientAreaMouseButtonRelease:
                # Add safety net so non-drag clicks don't leave window stuck in mouse_pressed
                self._set_state(DragState.inactive)
        elif state == DragState.floating_widget:
            if e.type() == QEvent.NonClientAreaMouseButtonRelease:
                logger.debug('FloatingWidget.event QEvent.NonClientAreaMouseButtonRelease')
                self._set_state(DragState.inactive)
                QTimer.singleShot(0, self._finalize_drag)

        return super().event(e)

    def closeEvent(self, event: QCloseEvent):
        logger.debug('FloatingDockContainer closeEvent')
        self._set_state(DragState.inactive)
        if not self.is_closable():
            event.ignore()
            return
            
        # Move aggressive layout cleanup from hideEvent to closeEvent
        # This prevents frameless opacity changes from accidentally destroying widgets
        if self._dock_container:
            for dock_area in self._dock_container.opened_dock_areas():
                for dock_widget in dock_area.opened_dock_widgets():
                    dock_widget.toggle_view(False)
                    
        super().closeEvent(event)

    def hideEvent(self, event: QHideEvent):
        super().hideEvent(event)
        # REMOVED: toggle_view(False) loop
        # Recreating the frameless window (e.g. via setWindowOpacity during drops) 
        # triggers QHideEvent. Closing widgets here incorrectly ripped them from the layout!

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        # Dynamically clear synthetic release block upon actual mouse movement
        if event.type() == QEvent.MouseMove:
            self._ignore_synthetic_release = False
            
        if event.type() == QEvent.MouseButtonRelease:
            
            if getattr(self, '_ignore_synthetic_release', False):
                logger.debug("[FDC] Ignoring OS synthetic mouse release during window mapping.")
                return False 
                
            if self._dragging_state == DragState.floating_widget:
                self._set_state(DragState.inactive)

                if self._mouse_event_handler is not None:
                    try:
                        self._mouse_event_handler.releaseMouse()
                    except RuntimeError:
                        pass
                    self._mouse_event_handler = None
                QApplication.instance().removeEventFilter(self)

                QTimer.singleShot(0, self._end_programmatic_drag)
                return False

        return False

    # ─────────────────────────────────────────────────────────────────────
    #  Public accessors
    # ─────────────────────────────────────────────────────────────────────

    def dock_container(self) -> 'DockContainerWidget':
        return self._dock_container

    def is_closable(self) -> bool:
        return DockWidgetFeature.closable in self._dock_container.features()

    def has_top_level_dock_widget(self) -> bool:
        return self._dock_container.has_top_level_dock_widget()

    def top_level_dock_widget(self) -> 'DockWidget':
        return self._dock_container.top_level_dock_widget()

    def dock_widgets(self) -> list:
        return self._dock_container.dock_widgets()