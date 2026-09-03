# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


from PySide6.QtCore import QObject, Signal

class DockSignals(QObject):
    """Event bus between the floating drag path and the dock manager.

    Deep widgets used to call manager methods directly.  These signals carry
    the two events where that coupling bought nothing, and they are a genuine
    extension point: subscribe to observe a drag without patching Lace.

    Reach it as ``dock_manager.signals``.

    .. note::
       ``request_overlay_show`` used to live here and was removed in 0.6.10.
       Its only would-be call site consumes ``DockOverlay.show_overlay()``'s
       *return value* — the drop area under the cursor — inside the drag's
       mouse-move path.  A signal cannot return anything, so emitting it
       would have meant reading the result back out of band on the next
       event, which is worse code than the direct call it replaced.  It was
       never emitted in any released version.
    """

    #: Hide every drop overlay.  Emitted when a drag ends, wherever it ends:
    #: dropped, released outside any container, or cancelled.
    request_overlay_hide = Signal()

    #: A floating widget was dropped onto a container.
    #: args: floating_widget (FloatingDockContainer),
    #:       target_container (DockContainerWidget),
    #:       target_pos (QPoint, global)
    floating_widget_dropped = Signal(object, object, object)