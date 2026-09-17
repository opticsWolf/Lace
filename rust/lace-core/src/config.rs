//! Canonical configuration enums — the Rust twin of `lace/enums.py`.
//!
//! Discriminant values are pinned to the Python `enum.auto()` numbering so
//! that serialized layouts and theme JSON stay wire-compatible:
//! `IntFlag.auto()` starts at bit 0, plain `Enum.auto()` starts at 1.

use serde::{Deserialize, Serialize};
use bitflags::bitflags;

bitflags! {
    /// Physical regions where widgets can be docked (`DockWidgetArea`).
    #[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
    pub struct DockAreas: u32 {
        const NO_AREA = 0;
        const LEFT    = 1 << 0;
        const RIGHT   = 1 << 1;
        const TOP     = 1 << 2;
        const BOTTOM  = 1 << 3;
        const CENTER  = 1 << 4;

        const INVALID = 0;
        const OUTER   = Self::LEFT.bits() | Self::RIGHT.bits()
                      | Self::TOP.bits() | Self::BOTTOM.bits();
        const ALL     = Self::OUTER.bits() | Self::CENTER.bits();
    }

    /// Capabilities enabled for a single dock widget (`DockWidgetFeature`).
    #[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
    pub struct DockWidgetFeature: u8 {
        const NO_FEATURES = 0;
        const CLOSABLE  = 1 << 0;
        const MOVABLE   = 1 << 1;
        const FLOATABLE = 1 << 2;
        const PINNABLE  = 1 << 3;
        const ALL = Self::CLOSABLE.bits() | Self::MOVABLE.bits()
                  | Self::FLOATABLE.bits() | Self::PINNABLE.bits();
    }

    /// Manager-wide behaviour switches (`DockFlags`).
    #[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
    pub struct DockFlags: u32 {
        const NONE                         = 0;
        const OPAQUE_SPLITTER_RESIZE       = 1 << 0;
        const OPAQUE_UNDOCKING             = 1 << 1;
        const ALWAYS_SHOW_TABS             = 1 << 2;
        const SHOW_TAB_CLOSE_BUTTON        = 1 << 3;
        const ACTIVE_TAB_HAS_CLOSE_BUTTON  = 1 << 4;
        const DOCK_AREA_HAS_CLOSE_BUTTON   = 1 << 5;
        const DOCK_AREA_CLOSE_BUTTON_CLOSES_TAB = 1 << 6;
        const DOCK_AREA_HAS_UNDOCK_BUTTON  = 1 << 7;
        const DOCK_AREA_HAS_PIN_BUTTON     = 1 << 8;
        const DOCK_AREA_HAS_MAXIMIZE_BUTTON = 1 << 9;
        const SIDEBAR_AREA_HAS_MAXIMIZE_BUTTON = 1 << 10;
        const DOCK_AREA_HAS_TABS_MENU_BUTTON = 1 << 11;
        const MIDDLE_MOUSE_BUTTON_CLOSES_TAB = 1 << 12;
        const FLOATABLE_TABS               = 1 << 13;
        const PINNABLE_TABS                = 1 << 14;
        const CUSTOM_TAB_ICONS             = 1 << 15;
        const HIDE_DISABLED_TITLE_BAR_ICONS = 1 << 16;
        const CHROMELESS_FLOAT             = 1 << 17;
        const FLOATING_TASKBAR_BUTTON      = 1 << 18;
    }
}

impl DockFlags {
    /// `DockFlags.default_config` — the mask a new `DockManager` gets.
    pub const DEFAULT_CONFIG: DockFlags = DockFlags::OPAQUE_SPLITTER_RESIZE
        .union(DockFlags::OPAQUE_UNDOCKING)
        .union(DockFlags::ALWAYS_SHOW_TABS)
        .union(DockFlags::SHOW_TAB_CLOSE_BUTTON)
        .union(DockFlags::ACTIVE_TAB_HAS_CLOSE_BUTTON)
        .union(DockFlags::DOCK_AREA_HAS_CLOSE_BUTTON)
        .union(DockFlags::DOCK_AREA_HAS_UNDOCK_BUTTON)
        .union(DockFlags::DOCK_AREA_HAS_PIN_BUTTON)
        .union(DockFlags::DOCK_AREA_HAS_MAXIMIZE_BUTTON)
        .union(DockFlags::DOCK_AREA_HAS_TABS_MENU_BUTTON)
        .union(DockFlags::MIDDLE_MOUSE_BUTTON_CLOSES_TAB)
        .union(DockFlags::FLOATABLE_TABS)
        .union(DockFlags::PINNABLE_TABS)
        .union(DockFlags::HIDE_DISABLED_TITLE_BAR_ICONS)
        .union(DockFlags::SIDEBAR_AREA_HAS_MAXIMIZE_BUTTON);
}

/// Split orientation. Values mirror `Qt.Orientation`.
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum Orientation {
    Horizontal = 1,
    Vertical = 2,
}

/// How a dock widget is inserted (`DockInsertParam`).
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub struct DockInsertParam {
    pub orientation: Orientation,
    pub append: bool,
}

impl DockInsertParam {
    /// 1 when appending, 0 when prepending.
    pub const fn insert_offset(self) -> u32 {
        if self.append { 1 } else { 0 }
    }
}

macro_rules! simple_enum {
    ($name:ident { $($variant:ident = $value:expr),* $(,)? }) => {
        #[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, Serialize, Deserialize)]
        #[repr(u8)]
        pub enum $name {
            $($variant = $value),*
        }
    };
}

simple_enum!(TitleBarButton {
    TabsMenu = 1, Undock = 2, Close = 3, Pin = 4,
    Maximize = 5, Minimize = 6, Restore = 7,
});

simple_enum!(OverlayMode { DockArea = 1, Container = 2 });

simple_enum!(DragState {
    Inactive = 1, MousePressed = 2, Tab = 3, FloatingWidget = 4,
});

simple_enum!(InsertionOrder { BySpelling = 1, ByInsertion = 2 });

simple_enum!(WidgetState {
    Docked = 1, Floating = 2, PinnedShown = 3, PinnedHidden = 4,
});

simple_enum!(InsertMode {
    AutoScrollArea = 1, ForceScrollArea = 2, ForceNoScrollArea = 3,
});

simple_enum!(ToggleViewActionMode { Toggle = 1, Show = 2 });

simple_enum!(SideBarFocusBehavior {
    TakeFocusAndRestore = 1, NoFocusTransfer = 2, TakeFocusOnly = 3,
});

/// Native vs custom title bar (`TitleBarMode`). Custom chrome itself is a
/// Phase 7 concern; the enum lives here from day one so configs parse now.
simple_enum!(TitleBarMode { Native = 1, Custom = 2 });

/// Corner a sidebar tab badge anchors to (`TabBadgePosition`).
simple_enum!(TabBadgePosition {
    TopLeft = 1, TopRight = 2, BottomLeft = 3, BottomRight = 4,
});

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn dock_area_zones_match_python_auto_numbering() {
        assert_eq!(DockAreas::NO_AREA.bits(), 0);
        assert_eq!(DockAreas::LEFT.bits(), 1);
        assert_eq!(DockAreas::RIGHT.bits(), 2);
        assert_eq!(DockAreas::TOP.bits(), 4);
        assert_eq!(DockAreas::BOTTOM.bits(), 8);
        assert_eq!(DockAreas::CENTER.bits(), 16);
    }

    #[test]
    fn dock_area_masks() {
        assert_eq!(DockAreas::OUTER.bits(), 15);
        assert_eq!(DockAreas::ALL.bits(), 31);
        assert_eq!(DockAreas::INVALID.bits(), DockAreas::NO_AREA.bits());
        assert!(DockAreas::OUTER.contains(DockAreas::LEFT | DockAreas::RIGHT));
        assert!(!DockAreas::OUTER.contains(DockAreas::CENTER));
    }

    #[test]
    fn default_config_pins_to_0_7_value() {
        // tests/test_enums.py::test_default_config_matches_architecture_doc
        // Verified live: int(DockFlags.default_config) == 98239.
        assert_eq!(DockFlags::DEFAULT_CONFIG.bits(), 98239);
        for flag in [
            DockFlags::OPAQUE_SPLITTER_RESIZE,
            DockFlags::OPAQUE_UNDOCKING,
            DockFlags::ALWAYS_SHOW_TABS,
            DockFlags::SHOW_TAB_CLOSE_BUTTON,
            DockFlags::ACTIVE_TAB_HAS_CLOSE_BUTTON,
            DockFlags::DOCK_AREA_HAS_CLOSE_BUTTON,
            DockFlags::DOCK_AREA_HAS_PIN_BUTTON,
            DockFlags::DOCK_AREA_HAS_MAXIMIZE_BUTTON,
            DockFlags::DOCK_AREA_HAS_TABS_MENU_BUTTON,
            DockFlags::MIDDLE_MOUSE_BUTTON_CLOSES_TAB,
            DockFlags::FLOATABLE_TABS,
            DockFlags::PINNABLE_TABS,
            DockFlags::HIDE_DISABLED_TITLE_BAR_ICONS,
            DockFlags::DOCK_AREA_HAS_UNDOCK_BUTTON,
            DockFlags::SIDEBAR_AREA_HAS_MAXIMIZE_BUTTON,
        ] {
            assert!(DockFlags::DEFAULT_CONFIG.contains(flag), "{flag:?}");
        }
        for flag in [
            DockFlags::CUSTOM_TAB_ICONS,
            DockFlags::DOCK_AREA_CLOSE_BUTTON_CLOSES_TAB,
            DockFlags::CHROMELESS_FLOAT,
            DockFlags::FLOATING_TASKBAR_BUTTON,
        ] {
            assert!(!DockFlags::DEFAULT_CONFIG.contains(flag), "{flag:?}");
        }
    }

    #[test]
    fn widget_feature_masks() {
        assert_eq!(DockWidgetFeature::ALL.bits(), 15);
        let flags = DockWidgetFeature::CLOSABLE | DockWidgetFeature::FLOATABLE;
        assert!(flags.contains(DockWidgetFeature::CLOSABLE));
        assert!(!flags.contains(DockWidgetFeature::PINNABLE));
    }

    #[test]
    fn insert_param_offsets() {
        let p = DockInsertParam { orientation: Orientation::Horizontal, append: true };
        assert_eq!(p.insert_offset(), 1);
        let p = DockInsertParam { orientation: Orientation::Vertical, append: false };
        assert_eq!(p.insert_offset(), 0);
        assert_eq!(Orientation::Horizontal as u8, 1);
        assert_eq!(Orientation::Vertical as u8, 2);
    }

    #[test]
    fn plain_enum_discriminants_match_python() {
        assert_eq!(TitleBarButton::TabsMenu as u8, 1);
        assert_eq!(TitleBarButton::Restore as u8, 7);
        assert_eq!(OverlayMode::Container as u8, 2);
        assert_eq!(DragState::FloatingWidget as u8, 4);
        assert_eq!(InsertionOrder::ByInsertion as u8, 2);
        assert_eq!(WidgetState::PinnedHidden as u8, 4);
        assert_eq!(InsertMode::ForceNoScrollArea as u8, 3);
        assert_eq!(ToggleViewActionMode::Show as u8, 2);
        assert_eq!(SideBarFocusBehavior::TakeFocusOnly as u8, 3);
        assert_eq!(TitleBarMode::Custom as u8, 2);
        assert_eq!(TabBadgePosition::BottomRight as u8, 4);
    }
}
