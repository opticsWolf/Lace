# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


"""Drawing for :class:`lace.lace_style.LaceStyle`, one module per control family.

``_paint`` holds the shared helpers (colours from the option's palette,
strokes, focus rings, vector glyphs); ``_primitives`` the indicators, frames
and scrollbars every family builds on. Each family module exposes tables that
map a ``QStyle`` element to a draw function; ``LaceStyle`` merges them.
"""
