# -*- coding: utf-8 -*-
"""
Lace: Advanced PySide6 Docking System
Copyright (c) 2026 opticsWolf

SPDX-License-Identifier: Apache-2.0
"""

from PySide6.QtCore import QObject, Signal

class DockSignals(QObject):
    """
    Internal global event bus for the Advanced Docking System.
    Replaces tight coupling (where deep widgets call manager methods directly)
    with a loosely coupled, signal-driven architecture.
    """
    
    # Emitted when a widget wants to trigger the drop overlays
    # args: target_container (DockContainerWidget)
    request_overlay_show = Signal(object)
    
    # Emitted to hide all active overlays
    request_overlay_hide = Signal()
    
    # Emitted when a floating widget is dropped
    # args: floating_widget (FloatingDockContainer), target_pos (QPoint)
    floating_widget_dropped = Signal(object, object)