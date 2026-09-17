# -*- coding: utf-8 -*-
"""`_lace_rs` package wrapper: re-export everything from the compiled
extension so ``import _lace_rs`` works identically in wheel and develop
installs (maturin mixed Rust/Python layout)."""

from _lace_rs._lace_rs import (  # noqa: F401,F403
    InvalidFormatError,
    LayoutError,
    LayoutIOError,
    RestoreFailureError,
    ValidationError,
    allowed_areas,
    available_themes,
    blank_layout,
    build_merged_theme,
    build_theme,
    dock_floating,
    dock_widget,
    drop_container_edge,
    drop_edges,
    float_widget,
    gc_empty_floats,
    load_theme_file,
    move_container_center,
    move_widget,
    pin_widget,
    remove_widget,
    set_closed,
    set_current,
    split_share,
    theme_groups,
    unpin_widget,
    validate_layout,
)

try:
    from _lace_rs._lace_rs import __version__  # noqa: F401
except ImportError:  # pragma: no cover
    __version__ = "0.0.0"
