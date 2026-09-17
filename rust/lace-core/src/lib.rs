//! `lace-core`: pure-Rust heart of the Lace docking system.
//!
//! No Qt, no Python here — only data, math and (de)serialization, so that
//! both the QML front-end (`lace-qt`) and the Python bindings (`lace-py`)
//! share one implementation. Mirrors `lace/enums.py`, `lace/util.py`
//! (`split_share`) and `lace/floating_behaviour.py` (`allowed_areas_for`).

pub mod config;
pub mod error;
pub mod layout;

pub use config::{
    DockAreas, DockFlags, DockInsertParam, DockWidgetFeature, DragState, InsertMode,
    InsertionOrder, Orientation, OverlayMode, SideBarFocusBehavior, TabBadgePosition,
    TitleBarButton, TitleBarMode, ToggleViewActionMode, WidgetState,
};
pub use error::LaceError;
pub use layout::{allowed_areas_for, split_share, ContainerNode, LayoutTree, LAYOUT_VERSION};
