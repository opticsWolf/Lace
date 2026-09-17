//! `lace-core::layout_ops`: pure tree mutations behind the dock operations.
//!
//! The Qt side (Phases 3–5) and the bindings call these; QML renders the
//! resulting [`LayoutDoc`]. Areas are addressed by index path from their
//! container root (`Root/0/1` = root's child 0, its child 1); widgets by
//! their unique roster name. Every op preserves `validate_doc`
//! (asserted by the tests on real golden documents).
//!
//! Two pragmatics worth knowing:
//! * Fresh splits use `sizes == [1, 1]`: all-equal sizes mean "distribute
//!   evenly" to the QML shell, while restored proportions stay intact.
//! * Fresh floats carry the placeholder blob [`PLACEHOLDER_GEOMETRY`]. A new
//!   float has no window yet, so there is no Qt blob to store; the blob is
//!   opaque to everything but Qt restore, which degrades gracefully on it.
//!   The plain `container_geometries` copy (used by QML) is always exact.

use std::collections::HashSet;

use crate::error::LaceError;
use crate::layout_doc::{
    ContainerData, ContainerEntry, LayoutDoc, SCHEMA_VERSION, SYSTEM_TYPE, TreeNode, validate_doc,
};

/// Placeholder Qt geometry blob for floats with no window yet.
pub const PLACEHOLDER_GEOMETRY: &str = "00";

/// Where a widget goes.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum DockEdge {
    Left,
    Right,
    Top,
    Bottom,
    Center,
    Float,
}

impl DockEdge {
    pub fn parse(s: &str) -> Option<DockEdge> {
        match s.to_ascii_lowercase().as_str() {
            "left" => Some(DockEdge::Left),
            "right" => Some(DockEdge::Right),
            "top" => Some(DockEdge::Top),
            "bottom" => Some(DockEdge::Bottom),
            "center" | "centre" => Some(DockEdge::Center),
            "float" | "floating" => Some(DockEdge::Float),
            _ => None,
        }
    }
}

/// Mutable view of an area node's fields.
pub struct AreaFields<'a> {
    pub tabs: &'a mut serde_json::Value,
    pub current: &'a mut serde_json::Value,
    pub widgets: &'a mut Vec<crate::layout_doc::WidgetNode>,
    pub locked_name: &'a mut Option<String>,
}

fn op_error(detail: impl Into<String>) -> LaceError {
    LaceError::InvalidLayout(detail.into())
}

fn widget_node(name: &str, closed: bool) -> crate::layout_doc::WidgetNode {
    crate::layout_doc::WidgetNode {
        node_type: "Widget".to_string(),
        name: Some(name.to_string()),
        closed: serde_json::json!(closed),
        locked_to_area: None,
    }
}

fn new_area(name: &str, closed: bool) -> TreeNode {
    TreeNode::Area {
        tabs: serde_json::json!(1),
        current: serde_json::json!(name),
        widgets: vec![widget_node(name, closed)],
        locked_name: None,
    }
}

fn node_widgets(node: &TreeNode, out: &mut Vec<(Vec<usize>, String)>, path: &mut Vec<usize>) {
    match node {
        TreeNode::Splitter { children, .. } => {
            for (i, child) in children.iter().enumerate() {
                path.push(i);
                node_widgets(child, out, path);
                path.pop();
            }
        }
        TreeNode::Area { widgets, .. } => {
            for w in widgets {
                if w.node_type == "Widget" {
                    if let Some(name) = w.name.as_deref() {
                        out.push((path.clone(), name.to_string()));
                    }
                }
            }
        }
        TreeNode::Unknown => {}
    }
}

/// `(container index, area path)` for every area, depth-first.
pub fn area_paths(doc: &LayoutDoc) -> Vec<(usize, Vec<usize>)> {
    let mut out = Vec::new();
    for (ci, container) in doc.containers.iter().enumerate() {
        let mut stack = vec![(vec![], &container.data.root_splitter)];
        while let Some((path, node)) = stack.pop() {
            match node {
                TreeNode::Splitter { children, .. } => {
                    for (i, child) in children.iter().enumerate().rev() {
                        let mut p = path.clone();
                        p.push(i);
                        stack.push((p, child));
                    }
                }
                TreeNode::Area { .. } => out.push((ci, path)),
                TreeNode::Unknown => {}
            }
        }
    }
    out
}

fn get_node_mut<'a>(root: &'a mut TreeNode, path: &[usize]) -> Option<&'a mut TreeNode> {
    let mut node = root;
    for index in path {
        match node {
            TreeNode::Splitter { children, .. } => node = children.get_mut(*index)?,
            _ => return None,
        }
    }
    Some(node)
}

fn get_node<'a>(root: &'a TreeNode, path: &[usize]) -> Option<&'a TreeNode> {
    let mut node = root;
    for index in path {
        match node {
            TreeNode::Splitter { children, .. } => node = children.get(*index)?,
            _ => return None,
        }
    }
    Some(node)
}

fn area_fields_mut<'a>(root: &'a mut TreeNode, path: &[usize]) -> Option<AreaFields<'a>> {
    match get_node_mut(root, path)? {
        TreeNode::Area { tabs, current, widgets, locked_name } => Some(AreaFields {
            tabs,
            current,
            widgets,
            locked_name,
        }),
        _ => None,
    }
}

fn main_index(doc: &LayoutDoc) -> Option<usize> {
    doc.containers.iter().position(|c| c.is_main)
}

fn ensure_main(doc: &mut LayoutDoc) -> usize {
    if let Some(index) = main_index(doc) {
        return index;
    }
    doc.containers.insert(
        0,
        ContainerEntry {
            id: Some("main".to_string()),
            is_main: true,
            data: ContainerData::default(),
        },
    );
    0
}

fn first_free_float_id(doc: &LayoutDoc) -> String {
    let taken: HashSet<&str> = doc
        .containers
        .iter()
        .filter_map(|c| c.id.as_deref())
        .collect();
    let mut n = 1;
    loop {
        let id = format!("float-{n}");
        if !taken.contains(id.as_str()) {
            return id;
        }
        n += 1;
    }
}

/// Drop empty areas and collapse wanna-be splitters. Returns the surviving
/// node, if any. `sizes` are kept when they still fit, else reset to even.
fn prune(node: TreeNode) -> Option<TreeNode> {
    match node {
        TreeNode::Area { widgets, .. } if widgets.is_empty() => None,
        TreeNode::Area { .. } => Some(node),
        TreeNode::Unknown => Some(TreeNode::Unknown),
        TreeNode::Splitter { orientation, count: _, sizes, children } => {
            let kept: Vec<TreeNode> = children.into_iter().filter_map(prune).collect();
            match kept.len() {
                0 => None,
                1 => Some(kept.into_iter().next().expect("exactly one")),
                n => {
                    let sizes = if sizes.len() == n {
                        sizes
                    } else {
                        vec![serde_json::json!(1); n]
                    };
                    Some(TreeNode::Splitter {
                        orientation,
                        count: serde_json::json!(n as u64),
                        sizes,
                        children: kept,
                    })
                }
            }
        }
    }
}

/// Remove the named widget node from a tree, pruning as it goes.
/// Returns the removed node when present.
fn extract_widget(node: &mut TreeNode, name: &str) -> Option<crate::layout_doc::WidgetNode> {
    match node {
        TreeNode::Area { widgets, .. } => {
            let index = widgets.iter().position(|w| w.node_type == "Widget" && w.name.as_deref() == Some(name))?;
            Some(widgets.remove(index))
        }
        TreeNode::Splitter { children, .. } => {
            for child in children.iter_mut() {
                if let Some(found) = extract_widget(child, name) {
                    return Some(found);
                }
            }
            None
        }
        TreeNode::Unknown => None,
    }
}

fn prune_root(doc: &mut LayoutDoc, container_index: usize) {
    let root = std::mem::replace(
        &mut doc.containers[container_index].data.root_splitter,
        TreeNode::Unknown,
    );
    doc.containers[container_index].data.root_splitter = prune(root).unwrap_or(TreeNode::Unknown);
}

/// Dock `name` at `edge` of `target` (`None` = first area of the main
/// container). `Float` opens a new floating container instead.
pub fn dock_widget(
    doc: &mut LayoutDoc,
    name: &str,
    edge: DockEdge,
    target: Option<(usize, Vec<usize>)>,
    closed: bool,
) -> Result<(), LaceError> {
    if edge == DockEdge::Float {
        return float_new(doc, name, closed);
    }
    let main = ensure_main(doc);
    let (container_index, path) = match target {
        Some(t) => t,
        None => area_paths(doc)
            .into_iter()
            .find(|(ci, _)| *ci == main)
            .unwrap_or((main, Vec::new())),
    };
    if container_index >= doc.containers.len() {
        return Err(op_error(format!("no container {container_index}")));
    }
    let root = &mut doc.containers[container_index].data.root_splitter;
    if edge == DockEdge::Center {
        match area_fields_mut(root, &path) {
            Some(mut area) => {
                area.widgets.push(widget_node(name, closed));
                *area.tabs = serde_json::json!(area.widgets.len() as u64);
                *area.current = serde_json::json!(name);
            }
            None => {
                // No area there (fresh main container): plant one.
                *root = new_area(name, closed);
            }
        }
    } else {
        let (orientation, before) = match edge {
            DockEdge::Left => ("-", true),
            DockEdge::Right => ("-", false),
            DockEdge::Top => ("|", true),
            DockEdge::Bottom => ("|", false),
            _ => unreachable!("center/float handled above"),
        };
        let old = match get_node_mut(root, &path) {
            Some(slot) => std::mem::replace(slot, TreeNode::Unknown),
            None => return Err(op_error(format!("no area at path {path:?}"))),
        };
        let old = if matches!(old, TreeNode::Unknown) {
            // Splitting thin air: the new area takes the slot alone.
            new_area(name, closed)
        } else {
            let fresh = new_area(name, closed);
            let (first, second) = if before { (fresh, old) } else { (old, fresh) };
            TreeNode::Splitter {
                orientation: orientation.to_string(),
                count: serde_json::json!(2),
                sizes: vec![serde_json::json!(1), serde_json::json!(1)],
                children: vec![first, second],
            }
        };
        *get_node_mut(root, &path).expect("path resolved above") = old;
    }
    doc.widget_states.insert(
        name.to_string(),
        crate::layout_doc::WidgetStateEntry { closed },
    );
    Ok(())
}

fn float_new(doc: &mut LayoutDoc, name: &str, closed: bool) -> Result<(), LaceError> {
    let id = first_free_float_id(doc);
    doc.containers.push(ContainerEntry {
        id: Some(id.clone()),
        is_main: false,
        data: ContainerData {
            floating: true,
            geometry: PLACEHOLDER_GEOMETRY.to_string(),
            root_splitter: new_area(name, closed),
        },
    });
    doc.container_geometries.insert(
        id,
        crate::layout_doc::GeometryEntry {
            x: serde_json::json!(100),
            y: serde_json::json!(100),
            width: serde_json::json!(480),
            height: serde_json::json!(360),
            is_maximized: serde_json::json!(false),
        },
    );
    doc.widget_states.insert(
        name.to_string(),
        crate::layout_doc::WidgetStateEntry { closed },
    );
    Ok(())
}

/// Forget `name` entirely: out of the tree and out of the roster.
pub fn remove_widget(doc: &mut LayoutDoc, name: &str) -> bool {
    let mut found = false;
    for index in 0..doc.containers.len() {
        if extract_widget(&mut doc.containers[index].data.root_splitter, name).is_some() {
            found = true;
            prune_root(doc, index);
        }
    }
    if doc.widget_states.remove(name).is_some() {
        found = true;
    }
    found
}

/// Flip the closed flag on the node and the roster entry.
pub fn set_closed(doc: &mut LayoutDoc, name: &str, closed: bool) -> bool {
    let mut found = false;
    for container in doc.containers.iter_mut() {
        let mut stack = vec![&mut container.data.root_splitter];
        while let Some(node) = stack.pop() {
            match node {
                TreeNode::Splitter { children, .. } => stack.extend(children.iter_mut()),
                TreeNode::Area { widgets, .. } => {
                    for w in widgets.iter_mut() {
                        if w.node_type == "Widget" && w.name.as_deref() == Some(name) {
                            w.closed = serde_json::json!(closed);
                            found = true;
                        }
                    }
                }
                TreeNode::Unknown => {}
            }
        }
    }
    if let Some(entry) = doc.widget_states.get_mut(name) {
        entry.closed = closed;
        found = true;
    }
    found
}

/// Point an area's current tab at `name` (stored verbatim, like the Qt
/// dynamic property).
pub fn set_current(
    doc: &mut LayoutDoc,
    container_index: usize,
    path: &[usize],
    name: &str,
) -> Result<(), LaceError> {
    let root = doc
        .containers
        .get_mut(container_index)
        .map(|c| &mut c.data.root_splitter)
        .ok_or_else(|| op_error(format!("no container {container_index}")))?;
    match area_fields_mut(root, path) {
        Some(mut area) => {
            *area.current = serde_json::json!(name);
            Ok(())
        }
        None => Err(op_error(format!("no area at path {path:?}"))),
    }
}

/// Tear `name` out of its container into a new float. Returns the new id.
pub fn float_widget(doc: &mut LayoutDoc, name: &str) -> Result<String, LaceError> {
    let mut carried: Option<crate::layout_doc::WidgetNode> = None;
    for index in 0..doc.containers.len() {
        if let Some(node) = extract_widget(&mut doc.containers[index].data.root_splitter, name) {
            carried = Some(node);
            prune_root(doc, index);
        }
    }
    let node = carried.ok_or_else(|| op_error(format!("no widget `{name}` to float")))?;
    let closed = node.closed.as_bool().unwrap_or(false);
    float_new(doc, name, closed)?;
    Ok(doc.containers.last().and_then(|c| c.id.clone()).expect("just pushed"))
}

/// Bring every widget of a floating container back to the main container's
/// first area (opening one if needed), then drop the float.
pub fn dock_floating(doc: &mut LayoutDoc, container_id: &str) -> Result<(), LaceError> {
    let index = doc
        .containers
        .iter()
        .position(|c| c.id.as_deref() == Some(container_id) && !c.is_main)
        .ok_or_else(|| op_error(format!("no floating container `{container_id}`")))?;
    let container = doc.containers.remove(index);
    doc.container_geometries.remove(container_id);
    let mut stack = vec![container.data.root_splitter];
    let mut names = Vec::new();
    while let Some(node) = stack.pop() {
        match node {
            TreeNode::Splitter { children, .. } => stack.extend(children),
            TreeNode::Area { widgets, .. } => {
                for w in widgets {
                    if w.node_type == "Widget" {
                        if let Some(name) = w.name {
                            names.push((name, w.closed.as_bool().unwrap_or(false)));
                        }
                    }
                }
            }
            TreeNode::Unknown => {}
        }
    }
    for (name, closed) in names {
        dock_widget(doc, &name, DockEdge::Center, None, closed)?;
    }
    Ok(())
}

/// A fresh, valid empty document (what a new manager would save).
pub fn blank_doc(app_version: i64) -> LayoutDoc {
    LayoutDoc {
        system_type: SYSTEM_TYPE.to_string(),
        schema: SCHEMA_VERSION,
        version: app_version,
        containers: vec![ContainerEntry {
            id: Some("main".to_string()),
            is_main: true,
            data: ContainerData::default(),
        }],
        sidebars: Default::default(),
        container_geometries: Default::default(),
        widget_states: Default::default(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::layout_doc::LayoutDoc;

    fn golden(name: &str) -> LayoutDoc {
        let path = format!(
            "{}/tests/fixtures/layouts/{name}.json",
            env!("CARGO_MANIFEST_DIR")
        );
        LayoutDoc::parse(&std::fs::read_to_string(path).unwrap()).unwrap()
    }

    /// The op invariant: the result still validates with its own roster.
    fn assert_valid(doc: &mut LayoutDoc) {
        let roster: HashSet<String> = doc.widget_states.keys().cloned().collect();
        validate_doc(doc, doc.version, &roster).expect("op broke validation");
    }

    #[test]
    fn dock_center_tabs_into_first_area() {
        let mut doc = golden("docked_tabs");
        dock_widget(&mut doc, "Echo", DockEdge::Center, None, false).unwrap();
        let (ci, path) = area_paths(&doc).into_iter().next().unwrap();
        assert_eq!(ci, 0);
        let root = &mut doc.containers[ci].data.root_splitter;
        let area = area_fields_mut(root, &path).unwrap();
        assert!(area.widgets.iter().any(|w| w.name.as_deref() == Some("Echo")));
        assert_eq!(*area.current, serde_json::json!("Echo"));
        assert_valid(&mut doc);
    }

    #[test]
    fn dock_edge_splits_with_even_sizes() {
        let mut doc = golden("docked_tabs");
        let target = area_paths(&doc).into_iter().next().unwrap();
        dock_widget(&mut doc, "Echo", DockEdge::Left, Some(target.clone()), false).unwrap();
        let root = &doc.containers[target.0].data.root_splitter;
        let slot = get_node(root, &target.1).unwrap();
        match slot {
            TreeNode::Splitter { orientation, count, sizes, children } => {
                assert_eq!(orientation, "-");
                assert_eq!(*count, serde_json::json!(2));
                assert_eq!(sizes.len(), 2);
                assert_eq!(children.len(), 2);
            }
            other => panic!("expected a splitter, got {other:?}"),
        }
        assert_valid(&mut doc);
    }

    #[test]
    fn dock_into_blank_doc_plants_main_area() {
        let mut doc = blank_doc(0);
        dock_widget(&mut doc, "Alpha", DockEdge::Center, None, false).unwrap();
        assert_eq!(area_paths(&doc).len(), 1);
        assert_valid(&mut doc);
    }

    #[test]
    fn float_and_dock_back_roundtrip() {
        let mut doc = golden("docked_tabs");
        let id = float_widget(&mut doc, "Gamma").unwrap();
        assert!(id.starts_with("float-"));
        assert!(doc.container_geometries.contains_key(&id));
        assert_valid(&mut doc);
        dock_floating(&mut doc, &id).unwrap();
        assert!(!doc.container_geometries.contains_key(&id));
        assert_valid(&mut doc);
        // And Gamma is tabbed back into the main container.
        let names: Vec<String> = {
            let mut out = Vec::new();
            let mut path = Vec::new();
            node_widgets(&doc.containers[0].data.root_splitter, &mut out, &mut path);
            out.into_iter().map(|(_, n)| n).collect()
        };
        assert!(names.contains(&"Gamma".to_string()));
    }

    #[test]
    fn remove_widget_drops_roster_and_prunes() {
        let mut doc = golden("docked_tabs");
        assert!(remove_widget(&mut doc, "Delta"));
        assert!(!doc.widget_states.contains_key("Delta"));
        assert!(!remove_widget(&mut doc, "Delta"));
        assert_valid(&mut doc);
    }

    #[test]
    fn closed_flag_flips_both_places() {
        let mut doc = golden("docked_tabs");
        assert!(set_closed(&mut doc, "Beta", true));
        assert!(doc.widget_states["Beta"].closed);
        assert!(!set_closed(&mut doc, "Nobody", true));
        assert_valid(&mut doc);
    }

    #[test]
    fn current_tab_points_verbatim() {
        let mut doc = golden("docked_tabs");
        let (ci, path) = area_paths(&doc).into_iter().next().unwrap();
        set_current(&mut doc, ci, &path, "Beta").unwrap();
        let root = &doc.containers[ci].data.root_splitter;
        assert_eq!(
            get_node(root, &path).unwrap(),
            &TreeNode::Area {
                tabs: serde_json::json!(3),
                current: serde_json::json!("Beta"),
                widgets: vec![
                    widget_node("Alpha", false),
                    widget_node("Beta", false),
                    widget_node("Gamma", false),
                ],
                locked_name: None,
            }
        );
        assert!(set_current(&mut doc, 9, &[], "Beta").is_err());
        assert_valid(&mut doc);
    }

    #[test]
    fn ops_on_every_golden_stay_valid() {
        for name in ["docked_tabs", "closed", "locked", "floating", "sidebar", "legacy"] {
            let mut doc = golden(name);
            dock_widget(&mut doc, "Extra", DockEdge::Right, None, false).unwrap();
            assert!(set_closed(&mut doc, "Extra", true));
            float_widget(&mut doc, "Extra").unwrap();
            assert_valid(&mut doc);
        }
    }

    #[test]
    fn bad_targets_are_op_errors() {
        let mut doc = golden("docked_tabs");
        assert!(dock_widget(&mut doc, "X", DockEdge::Center, Some((9, vec![])), false).is_err());
        assert!(dock_widget(&mut doc, "X", DockEdge::Left, Some((0, vec![7])), false).is_err());
        assert!(float_widget(&mut doc, "Nobody").is_err());
        assert!(dock_floating(&mut doc, "float-9").is_err());
        assert!(dock_floating(&mut doc, "main").is_err());
    }
}
