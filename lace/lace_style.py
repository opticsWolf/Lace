# -*- coding: utf-8 -*-
# Lace: Advanced PySide6 Docking System
# Copyright (c) 2026 opticsWolf
#
# SPDX-License-Identifier: Apache-2.0
#
# This file is part of Lace.
# Licensed under the Apache License, Version 2.0.


"""LaceStyle: a modern, flat Fusion.

A ``QProxyStyle`` over Fusion. Fusion keeps the layout (identical on every
OS) and paints anything LaceStyle doesn't override, reading the same palette;
LaceStyle replaces the dated drawing -- gradients, bevels, pixmap-cached
glyphs -- with flat fills, one stroke and vector paths.

Sizes stay Fusion's: ``pixelMetric``, ``sizeFromContents`` and
``subControlRect`` pass through, except the scrollbar extent and sub-control
rects in the ``thin`` and ``expanding`` scrollbar modes, a wider split
button menu arrow, a splitter handle wide enough to pad its grip, and menu
section headers tall and wide enough for their titles.

    app.setStyle(LaceStyle())               # standalone, default tokens
    DockThemeBridge()                        # installs it, tokens follow the theme
"""

from typing import Callable, Dict, Optional

from PySide6.QtWidgets import (QCalendarWidget, QComboBox, QProxyStyle, QStyle, QStyleFactory,
                               QWidget)

from lace.style import (_buttons, _chrome, _containers, _frame_cap, _inputs, _popup, _primitives,
                        _range)
from lace.theme_contrast import CONTRAST_TARGETS

SCROLLBAR_MODES = ("thin", "expanding", "fusion")
CONTRAST_LEVELS = tuple(CONTRAST_TARGETS["ui"])

PM = QStyle.PixelMetric
CC = QStyle.ComplexControl


def _merge(*tables: Dict) -> Dict:
    out: Dict = {}
    for t in tables:
        out.update(t)
    return out


class LaceStyle(QProxyStyle):
    """Flat, rounded, vector-drawn Fusion. See the module docstring."""

    #: element -> draw(style, option, painter, widget) -> bool (True = painted)
    PRIMITIVES: Dict = _merge(_primitives.PRIMITIVES, _buttons.PRIMITIVES, _inputs.PRIMITIVES,
                              _containers.PRIMITIVES, _chrome.PRIMITIVES)
    CONTROLS: Dict = _merge(_buttons.CONTROLS, _range.CONTROLS, _containers.CONTROLS,
                            _chrome.CONTROLS)
    COMPLEX: Dict = _merge(_primitives.COMPLEX, _inputs.COMPLEX, _range.COMPLEX)
    SUBCONTROL_RECTS: Dict = _merge(_primitives.SUBCONTROL_RECTS)

    def __init__(self, control_radius: int = 4, scrollbar: str = "expanding",
                 contrast: str = "normal", focus_width: float = 2.0,
                 outline_strength: float = 0.22, splitter_length: int = 50,
                 field_outline: bool = True):
        # QProxyStyle takes ownership of the base style.
        super().__init__(QStyleFactory.create("Fusion"))
        self.control_radius = 4
        self.scrollbar = "expanding"
        self.contrast = "normal"
        self.focus_width = 2.0
        self.outline_strength = 0.22
        self.splitter_length = 50
        self.field_outline = True
        self._weekend_tint = _chrome.WeekendTint(self)
        self._popup_shift = _popup.ShadowShift(self)
        self.set_tokens(control_radius=control_radius, scrollbar=scrollbar, contrast=contrast,
                        focus_width=focus_width, outline_strength=outline_strength,
                        splitter_length=splitter_length, field_outline=field_outline)

    # -- theme knobs -------------------------------------------------------------
    def set_tokens(self, control_radius: Optional[int] = None,
                   scrollbar: Optional[str] = None, contrast: Optional[str] = None,
                   focus_width: Optional[float] = None,
                   outline_strength: Optional[float] = None,
                   splitter_length: Optional[int] = None,
                   field_outline: Optional[bool] = None) -> None:
        """Update the theme knobs; widgets repaint on their next paint event.

        ``contrast`` is the theme's level: it sets the ratio the non-text UI
        (indicator outlines, focus ring, scrollbar handle) is held to.
        ``focus_width`` is the keyboard focus ring's pen width; 0 hides it.
        ``outline_strength`` (0-1) is how much text colour is mixed over a
        control's fill for its 1 px outline; the contrast floor still applies.
        ``splitter_length`` is the length of a splitter handle's grip, in px.
        ``field_outline`` False drops the outline of unfocused input fields
        and framed views; a focused field keeps its accent ring, and
        containers (group boxes, tab-widget panes) keep their frame.
        """
        if control_radius is not None:
            self.control_radius = max(0, int(control_radius))
        if scrollbar is not None:
            if scrollbar not in SCROLLBAR_MODES:
                raise ValueError(f"scrollbar must be one of {SCROLLBAR_MODES}, got {scrollbar!r}")
            self.scrollbar = scrollbar
        if contrast is not None:
            if contrast not in CONTRAST_LEVELS:
                raise ValueError(f"contrast must be one of {CONTRAST_LEVELS}, got {contrast!r}")
            self.contrast = contrast
        if focus_width is not None:
            self.focus_width = max(0.0, float(focus_width))
        if outline_strength is not None:
            self.outline_strength = min(1.0, max(0.0, float(outline_strength)))
        if splitter_length is not None:
            self.splitter_length = max(0, int(splitter_length))
        if field_outline is not None:
            self.field_outline = bool(field_outline)

    @property
    def ui_ratio(self) -> float:
        """Contrast floor for non-text UI at the current level."""
        return CONTRAST_TARGETS["ui"][self.contrast]

    @property
    def border_ratio(self) -> float:
        """Contrast floor for control outlines and frames at the current level."""
        return CONTRAST_TARGETS["border"][self.contrast]

    def _own_scrollbar(self) -> bool:
        return self.scrollbar != "fusion"

    # -- widgets -----------------------------------------------------------------
    def polish(self, *args):
        # QStyle.polish is overloaded (QWidget, QApplication, QPalette); only
        # widgets get a frame cap, weekend tint or rounded popup window.
        result = super().polish(*args)
        w = args[0] if args else None
        if isinstance(w, QWidget) and _frame_cap.wants_cap(w) and _frame_cap.cap_of(w) is None:
            _frame_cap.FrameCap(w, self)
        if isinstance(w, QCalendarWidget):
            self._weekend_tint.attach(w)
        if _popup.is_popup(w):
            _popup.round_popup(self, w, self._popup_shift)
        return result

    def unpolish(self, *args):
        w = args[0] if args else None
        cap = _frame_cap.cap_of(w) if isinstance(w, QWidget) else None
        if cap is not None:
            cap.detach()
        if isinstance(w, QCalendarWidget):
            self._weekend_tint.detach(w)
        if _popup.is_popup(w):
            _popup.unround_popup(self, w, self._popup_shift)
        return super().unpolish(*args)

    # -- dispatch ----------------------------------------------------------------
    @staticmethod
    def _run(fn: Optional[Callable], style, opt, painter, widget) -> bool:
        return fn is not None and opt is not None and bool(fn(style, opt, painter, widget))

    def drawPrimitive(self, element, option, painter, widget=None):
        if not self._run(self.PRIMITIVES.get(element), self, option, painter, widget):
            super().drawPrimitive(element, option, painter, widget)

    def drawControl(self, element, option, painter, widget=None):
        if not self._run(self.CONTROLS.get(element), self, option, painter, widget):
            super().drawControl(element, option, painter, widget)

    def drawComplexControl(self, control, option, painter, widget=None):
        fn = self.COMPLEX.get(control)
        if control == CC.CC_ScrollBar and not self._own_scrollbar():
            fn = None
        if not self._run(fn, self, option, painter, widget):
            super().drawComplexControl(control, option, painter, widget)

    def subControlRect(self, control, option, sub_control, widget=None):
        fn = self.SUBCONTROL_RECTS.get(control)
        if fn is not None and option is not None and not (
                control == CC.CC_ScrollBar and not self._own_scrollbar()):
            return fn(self, option, sub_control, widget)
        return super().subControlRect(control, option, sub_control, widget)

    def sizeFromContents(self, type_, option, size, widget=None):
        size = super().sizeFromContents(type_, option, size, widget)
        if type_ == QStyle.ContentsType.CT_MenuItem:
            return _containers.menu_section_size(self, option, size) or size
        return size

    def pixelMetric(self, metric, option=None, widget=None):
        # A combo box reserves room for its popup's scrollbar out of this
        # metric; that room is text layout, so it keeps the base width and a
        # combo never reflows under LaceStyle.
        if (metric == PM.PM_ScrollBarExtent and self._own_scrollbar()
                and not isinstance(widget, QComboBox)):
            return _primitives.SCROLLBAR_EXTENT[self.scrollbar]
        if metric == PM.PM_MenuButtonIndicator:
            # More room on each side of a split button's chevron.
            return super().pixelMetric(metric, option, widget) + 2 * _buttons.SPLIT_PAD
        if metric == PM.PM_SplitterWidth:
            return _chrome.SPLITTER_WIDTH
        if metric == PM.PM_MenuHMargin and _popup.is_rounded(widget):
            # Room for the shadow beside a rounded menu's panel.
            return super().pixelMetric(metric, option, widget) + _popup.SHADOW
        if metric == PM.PM_MenuVMargin and _popup.is_rounded(widget):
            # Room for the shadow, and rows that clear the panel's arcs.
            return super().pixelMetric(metric, option, widget) + _popup.SHADOW + _popup.pad(self)
        return super().pixelMetric(metric, option, widget)


__all__ = ["LaceStyle", "SCROLLBAR_MODES", "CONTRAST_LEVELS"]
