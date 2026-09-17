//! `lace-core`: pure-Rust heart of the Lace docking system.
//!
//! No Qt, no Python here — only data, math and (de)serialization, so that
//! both the QML front-end (`lace-qt`) and the Python bindings (`lace-py`)
//! share one implementation. Mirrors `lace/enums.py`, `lace/util.py`
//! (`split_share`), `lace/floating_behaviour.py` (`allowed_areas_for`),
//! and `lace/dock_theme.py` + `lace/dock_custom_theme.py` (theme engine,
//! presets, JSON themes).

pub mod config;
pub mod error;
pub mod layout;
pub mod presets_generated;
pub mod schema_generated;
pub mod style;
pub mod svg_colors_generated;
pub mod theme;
pub mod theme_json;

pub use config::{
    DockAreas, DockFlags, DockInsertParam, DockWidgetFeature, DragState, InsertMode,
    InsertionOrder, Orientation, OverlayMode, SideBarFocusBehavior, TabBadgePosition,
    TitleBarButton, TitleBarMode, ToggleViewActionMode, WidgetState,
};
pub use error::LaceError;
pub use layout::{allowed_areas_for, split_share, ContainerNode, LayoutTree, LAYOUT_VERSION};
