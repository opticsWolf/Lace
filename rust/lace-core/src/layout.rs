//! Layout math and the serializable layout tree.
//!
//! Ports `split_share()` (`lace/util.py`) and `allowed_areas_for()`
//! (`lace/floating_behaviour.py`) verbatim, plus a minimal serde tree whose
//! full schema lands in Phase 2 against 0.7.x golden files.

use serde::{Deserialize, Serialize};

use crate::config::{DockAreas, Orientation};

/// Layout format version written by this crate.
pub const LAYOUT_VERSION: u32 = 1;

/// Even split of `target_size` across `n_total` panes, minus handle gutters.
///
/// One arithmetic for "insert a sibling next to this area", shared by the
/// drop path and the programmatic path so the two cannot drift apart.
/// Sizes are non-negative, so saturating at zero (instead of Python's
/// floor-towards-negative-infinity `//`) only differs for degenerate
/// inputs where the gutter exceeds the target.
pub fn split_share(target_size: u32, handle_width: u32, n_total: u32) -> u32 {
    if n_total == 0 {
        return 0;
    }
    target_size
        .saturating_sub(handle_width.saturating_mul(n_total - 1))
        / n_total
}

/// The single source of truth for what a drag may target.
///
/// `visible_area_count` is `container.visible_dock_area_count()`;
/// `target_present` is false when the hovered dock area (or its container)
/// is gone. A lone area still accepts tabs while the container overlay owns
/// the outer four — hence `CENTER`, not `NO_AREA`, for count == 1.
pub fn allowed_areas_for(visible_area_count: usize, target_present: bool) -> DockAreas {
    if !target_present {
        return DockAreas::NO_AREA;
    }
    if visible_area_count == 1 {
        return DockAreas::CENTER;
    }
    DockAreas::ALL
}

/// Serializable layout tree (skeleton — Phase 2 ports the full
/// `layout_serializer` schema with 0.7.x golden-file compatibility).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct LayoutTree {
    pub version: u32,
    pub root: ContainerNode,
}

impl LayoutTree {
    pub fn new(root: ContainerNode) -> Self {
        Self { version: LAYOUT_VERSION, root }
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub enum ContainerNode {
    Empty,
    Splitter {
        orientation: Orientation,
        children: Vec<ContainerNode>,
    },
    Area {
        widgets: Vec<String>,
    },
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn split_share_pins_python_values() {
        // tests/test_area_insertion.py::test_split_share_subtracts_the_handle_gutters
        assert_eq!(split_share(900, 6, 2), 447);
        assert_eq!(split_share(900, 0, 3), 300);
        assert_eq!(split_share(100, 6, 1), 100);
    }

    #[test]
    fn split_share_degenerate_inputs() {
        assert_eq!(split_share(900, 6, 0), 0);
        // Gutter wider than the target saturates at zero instead of
        // going negative the way Python's `//` would.
        assert_eq!(split_share(5, 8, 2), 0);
    }

    #[test]
    fn allowed_areas_pins_python_rules() {
        assert_eq!(allowed_areas_for(3, false), DockAreas::NO_AREA);
        assert_eq!(allowed_areas_for(1, true), DockAreas::CENTER);
        assert_eq!(allowed_areas_for(2, true), DockAreas::ALL);
        assert_eq!(allowed_areas_for(5, true), DockAreas::ALL);
    }

    #[test]
    fn layout_tree_json_roundtrip() {
        let tree = LayoutTree::new(ContainerNode::Splitter {
            orientation: Orientation::Horizontal,
            children: vec![
                ContainerNode::Area { widgets: vec!["alpha".into()] },
                ContainerNode::Area { widgets: vec!["beta".into()] },
            ],
        });
        let json = serde_json::to_string(&tree).unwrap();
        let back: LayoutTree = serde_json::from_str(&json).unwrap();
        assert_eq!(tree, back);
        assert_eq!(back.version, LAYOUT_VERSION);
    }
}
