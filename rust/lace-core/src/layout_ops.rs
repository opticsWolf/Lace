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
    ContainerData, ContainerEntry, LayoutDoc, SCHEMA_VERSION, SYSTEM_TYPE, TreeNode,
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

/// Insert an existing node at `edge` of `path` (shared by fresh docks
/// and drag moves). `Center` appends the tab and makes it current; any
/// other edge wraps the target in a new even splitter.
fn insert_at(
    root: &mut TreeNode,
    node: crate::layout_doc::WidgetNode,
    name: &str,
    edge: DockEdge,
    path: &[usize],
) -> Result<(), LaceError> {
    if edge == DockEdge::Center {
        match area_fields_mut(root, path) {
            Some(area) => {
                area.widgets.push(node);
                *area.tabs = serde_json::json!(area.widgets.len() as u64);
                *area.current = serde_json::json!(name);
                Ok(())
            }
            None => {
                // No area there (fresh main container): plant one.
                *root = new_area(name, node.closed.as_bool().unwrap_or(false));
                Ok(())
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
        let old = match get_node_mut(root, path) {
            Some(slot) => std::mem::replace(slot, TreeNode::Unknown),
            None => return Err(op_error(format!("no area at path {path:?}"))),
        };
        let old = if matches!(old, TreeNode::Unknown) {
            // Splitting thin air: the new area takes the slot alone.
            TreeNode::Area {
                tabs: serde_json::json!(1),
                current: serde_json::json!(name),
                widgets: vec![node],
                locked_name: None,
            }
        } else {
            let fresh = TreeNode::Area {
                tabs: serde_json::json!(1),
                current: serde_json::json!(name),
                widgets: vec![node],
                locked_name: None,
            };
            let (first, second) = if before { (fresh, old) } else { (old, fresh) };
            TreeNode::Splitter {
                orientation: orientation.to_string(),
                count: serde_json::json!(2),
                sizes: vec![serde_json::json!(1), serde_json::json!(1)],
                children: vec![first, second],
            }
        };
        *get_node_mut(root, path).expect("path resolved above") = old;
        Ok(())
    }
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
    insert_at(root, widget_node(name, closed), name, edge, &path)?;
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
            node_type: "Container".to_string(),
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

/// Overwrite a splitter node's size weights (from a handle drag). Length
/// must match the child count and every entry must be a positive number;
/// silent by contract — the caller already shows the sizes.
pub fn set_splitter_sizes(
    doc: &mut LayoutDoc,
    container_index: usize,
    path: &[usize],
    sizes: &[f64],
) -> Result<(), LaceError> {
    let root = doc
        .containers
        .get_mut(container_index)
        .map(|c| &mut c.data.root_splitter)
        .ok_or_else(|| op_error(format!("no container {container_index}")))?;
    match get_node_mut(root, path) {
        Some(TreeNode::Splitter {
            sizes: current,
            children,
            ..
        }) => {
            if sizes.len() != children.len() {
                return Err(op_error(format!(
                    "sizes length {} != children {}",
                    sizes.len(),
                    children.len()
                )));
            }
            if !sizes.iter().all(|s| s.is_finite() && *s > 0.0) {
                return Err(op_error("splitter sizes must be positive numbers"));
            }
            *current = sizes.iter().map(|s| serde_json::json!(s)).collect();
            Ok(())
        }
        _ => Err(op_error(format!("no splitter at path {path:?}"))),
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

/// Pin `name` to the auto-hide sidebar `area` (`"left"`, ...).
///
/// The widget leaves the dock tree (like floating, but into the sidebar
/// roster instead of a new container); re-pinning moves it between areas.
/// The roster entry is kept: pinned widgets stay registered, merely
/// homeless until unpinned.
pub fn pin_widget(doc: &mut LayoutDoc, name: &str, area: &str) -> Result<(), LaceError> {
    if !doc.widget_states.contains_key(name) {
        return Err(op_error(format!("no widget `{name}` to pin")));
    }
    for index in 0..doc.containers.len() {
        if extract_widget(&mut doc.containers[index].data.root_splitter, name).is_some() {
            prune_root(doc, index);
        }
    }
    doc.sidebars.pinned_widgets.insert(name.to_string(), area.to_string());
    if !doc.sidebars.sidebar_areas.iter().any(|a| a == area) {
        doc.sidebars.sidebar_areas.push(area.to_string());
    }
    Ok(())
}

/// Return a pinned widget to the main container's first area.
pub fn unpin_widget(doc: &mut LayoutDoc, name: &str) -> Result<(), LaceError> {
    if doc.sidebars.pinned_widgets.remove(name).is_none() {
        return Err(op_error(format!("no pinned widget `{name}`")));
    }
    let closed = doc.widget_states.get(name).map(|entry| entry.closed).unwrap_or(false);
    dock_widget(doc, name, DockEdge::Center, None, closed)
}

/// Take a widget node out of every container tree (pruning as it goes).
/// Used only where placement afterwards is infallible (`float_widget`);
/// moves use the atomic clone-insert-remove pattern below instead.
fn take_node(doc: &mut LayoutDoc, name: &str) -> Result<crate::layout_doc::WidgetNode, LaceError> {
    let mut carried = None;
    for index in 0..doc.containers.len() {
        if let Some(node) = extract_widget(&mut doc.containers[index].data.root_splitter, name) {
            carried = Some(node);
            prune_root(doc, index);
        }
    }
    carried.ok_or_else(|| op_error(format!("no widget `{name}` to move")))
}

/// First location of a widget node: `(container, path)` depth-first.
fn find_widget(doc: &LayoutDoc, name: &str) -> Option<(usize, Vec<usize>)> {
    for (ci, container) in doc.containers.iter().enumerate() {
        let mut stack = vec![(Vec::new(), &container.data.root_splitter)];
        while let Some((path, node)) = stack.pop() {
            match node {
                TreeNode::Splitter { children, .. } => {
                    for (i, child) in children.iter().enumerate().rev() {
                        let mut p = path.clone();
                        p.push(i);
                        stack.push((p, child));
                    }
                }
                TreeNode::Area { widgets, .. } => {
                    if widgets.iter().any(|w| w.node_type == "Widget" && w.name.as_deref() == Some(name)) {
                        return Some((ci, path));
                    }
                }
                TreeNode::Unknown => {}
            }
        }
    }
    None
}

/// Clone the named node where it lives (no mutation).
fn clone_widget_at(doc: &LayoutDoc, container: usize, path: &[usize], name: &str) -> Option<crate::layout_doc::WidgetNode> {
    let root = &doc.containers.get(container)?.data.root_splitter;
    match get_node(root, path)? {
        TreeNode::Area { widgets, .. } => widgets
            .iter()
            .find(|w| w.node_type == "Widget" && w.name.as_deref() == Some(name))
            .cloned(),
        _ => None,
    }
}

/// Remove the named node at an exact spot, pruning afterwards.
fn remove_at(doc: &mut LayoutDoc, container: usize, path: &[usize], name: &str) -> bool {
    let root = match doc.containers.get_mut(container) {
        Some(c) => &mut c.data.root_splitter,
        None => return false,
    };
    let removed = match get_node_mut(root, path) {
        Some(TreeNode::Area { widgets, .. }) => {
            match widgets.iter().position(|w| w.node_type == "Widget" && w.name.as_deref() == Some(name)) {
                Some(index) => {
                    widgets.remove(index);
                    true
                }
                None => false,
            }
        }
        _ => false,
    };
    if removed {
        prune_root(doc, container);
    }
    removed
}

/// A widget lifted out of the tree, ready to re-place. Lifting first and
/// resolving the target afterwards keeps every move atomic: the clone
/// survives whatever pruning the removal triggers.
struct Carried {
    node: crate::layout_doc::WidgetNode,
    closed: bool,
}

fn lift(doc: &mut LayoutDoc, name: &str) -> Result<Carried, LaceError> {
    let (source_ci, source_path) =
        find_widget(doc, name).ok_or_else(|| op_error(format!("no widget `{name}` to move")))?;
    let node = clone_widget_at(doc, source_ci, &source_path, name).expect("just found");
    let closed = node.closed.as_bool().unwrap_or(false);
    remove_at(doc, source_ci, &source_path, name);
    Ok(Carried { node, closed })
}

fn sync_roster_closed(doc: &mut LayoutDoc, name: &str, closed: bool) {
    if let Some(entry) = doc.widget_states.get_mut(name) {
        entry.closed = closed;
    }
}

/// Move an existing widget to `edge` of `target`, keeping its node (closed
/// flag, lock) intact. Section-level: centre tabs in (appended, current),
/// edges split — the same placement fresh docks use.
///
/// Atomic: a bad target fails with the tree untouched; when lifting the
/// widget collapses its old home, the root takes the drop instead.
pub fn move_widget(
    doc: &mut LayoutDoc,
    name: &str,
    edge: DockEdge,
    target: (usize, Vec<usize>),
) -> Result<(), LaceError> {
    let (container_index, path) = &target;
    let root = doc
        .containers
        .get(*container_index)
        .map(|c| &c.data.root_splitter)
        .ok_or_else(|| op_error(format!("no container {container_index}")))?;
    // Validate before lifting: a genuinely bad target fails untouched.
    if get_node(root, path).is_none() {
        return Err(op_error(format!("no area at path {path:?}")));
    }
    let carried = lift(doc, name)?;
    // The lift may have collapsed the target away (last tab out of its own
    // area); the root then takes the drop instead.
    let root = &mut doc.containers[*container_index].data.root_splitter;
    let path = if get_node(root, path).is_some() { path.clone() } else { Vec::new() };
    insert_at(root, carried.node, name, edge, &path)?;
    sync_roster_closed(doc, name, carried.closed);
    Ok(())
}

/// Split a container root around a fresh area, preserving existing sizes
/// with a fair share appended (or prepended). Wraps non-matching roots in
/// a new even splitter.
fn split_root(
    doc: &mut LayoutDoc,
    container: usize,
    node: crate::layout_doc::WidgetNode,
    name: &str,
    orientation: &str,
    before: bool,
) -> Result<(), LaceError> {
    let root = doc
        .containers
        .get_mut(container)
        .map(|c| &mut c.data.root_splitter)
        .ok_or_else(|| op_error(format!("no container {container}")))?;
    let area = TreeNode::Area {
        tabs: serde_json::json!(1),
        current: serde_json::json!(name),
        widgets: vec![node],
        locked_name: None,
    };
    let old = std::mem::replace(root, TreeNode::Unknown);
    let rebuilt = match old {
        TreeNode::Unknown => area,
        TreeNode::Splitter { orientation: o, count: _, mut sizes, mut children }
            if o == orientation =>
        {
            let total: i64 = sizes.iter().filter_map(|s| s.as_i64()).sum();
            let share = serde_json::json!((total / (children.len() as i64 + 1)).max(1));
            if before {
                children.insert(0, area);
                sizes.insert(0, share);
            } else {
                children.push(area);
                sizes.push(share);
            }
            let count = serde_json::json!(children.len() as u64);
            TreeNode::Splitter { orientation: o, count, sizes, children }
        }
        other => {
            let (first, second) = if before { (area, other) } else { (other, area) };
            TreeNode::Splitter {
                orientation: orientation.to_string(),
                count: serde_json::json!(2),
                sizes: vec![serde_json::json!(1), serde_json::json!(1)],
                children: vec![first, second],
            }
        }
    };
    *root = rebuilt;
    Ok(())
}

/// Move an existing widget to the container level. Solo containers tab the
/// widget into their single area; multi-area containers take the deliberate
/// bottom-style root split (mirrors `_drop_into_container`).
pub fn move_container_center(doc: &mut LayoutDoc, name: &str, container: usize) -> Result<(), LaceError> {
    if container >= doc.containers.len() {
        return Err(op_error(format!("no container {container}")));
    }
    let carried = lift(doc, name)?;
    // Recomputed after the lift, so collapse cannot strand the paths.
    let areas: Vec<Vec<usize>> = area_paths(doc)
        .into_iter()
        .filter(|(ci, _)| *ci == container)
        .map(|(_, path)| path)
        .collect();
    let placed = match areas.len() {
        0 => {
            doc.containers[container].data.root_splitter = TreeNode::Area {
                tabs: serde_json::json!(1),
                current: serde_json::json!(name),
                widgets: vec![carried.node],
                locked_name: None,
            };
            Ok(())
        }
        1 => {
            let root = &mut doc.containers[container].data.root_splitter;
            insert_at(root, carried.node, name, DockEdge::Center, &areas[0])
        }
        _ => split_root(doc, container, carried.node, name, "|", false),
    };
    placed?;
    sync_roster_closed(doc, name, carried.closed);
    Ok(())
}

/// Move an existing widget to a container edge (root split). `Center`
/// delegates to [`move_container_center`].
pub fn drop_container_edge(
    doc: &mut LayoutDoc,
    name: &str,
    container: usize,
    edge: DockEdge,
) -> Result<(), LaceError> {
    if container >= doc.containers.len() {
        return Err(op_error(format!("no container {container}")));
    }
    let carried = lift(doc, name)?;
    let placed = match edge {
        DockEdge::Center => {
            // Recomputed after the lift, so collapse cannot strand paths.
            let areas: Vec<Vec<usize>> = area_paths(doc)
                .into_iter()
                .filter(|(ci, _)| *ci == container)
                .map(|(_, path)| path)
                .collect();
            match areas.len() {
                0 => {
                    doc.containers[container].data.root_splitter = TreeNode::Area {
                        tabs: serde_json::json!(1),
                        current: serde_json::json!(name),
                        widgets: vec![carried.node],
                        locked_name: None,
                    };
                    Ok(())
                }
                1 => {
                    let root = &mut doc.containers[container].data.root_splitter;
                    insert_at(root, carried.node, name, DockEdge::Center, &areas[0])
                }
                _ => split_root(doc, container, carried.node, name, "|", false),
            }
        }
        DockEdge::Left => split_root(doc, container, carried.node, name, "-", true),
        DockEdge::Right => split_root(doc, container, carried.node, name, "-", false),
        DockEdge::Top => split_root(doc, container, carried.node, name, "|", true),
        DockEdge::Bottom => split_root(doc, container, carried.node, name, "|", false),
        DockEdge::Float => {
            // A cross has no float zone; tab into the container's first
            // area (planting one when the lift emptied it).
            let areas: Vec<Vec<usize>> = area_paths(doc)
                .into_iter()
                .filter(|(ci, _)| *ci == container)
                .map(|(_, path)| path)
                .collect();
            match areas.into_iter().next() {
                Some(path) => {
                    let root = &mut doc.containers[container].data.root_splitter;
                    insert_at(root, carried.node, name, DockEdge::Center, &path)
                }
                None => {
                    doc.containers[container].data.root_splitter = TreeNode::Area {
                        tabs: serde_json::json!(1),
                        current: serde_json::json!(name),
                        widgets: vec![carried.node],
                        locked_name: None,
                    };
                    Ok(())
                }
            }
        }
    };
    placed?;
    sync_roster_closed(doc, name, carried.closed);
    Ok(())
}

/// Zones a container offers: a solo area takes the centre indicator only
/// (otherwise the cross hides everything, centre included); several areas
/// offer the full set. Mirrors `allowed_areas_for` at document level.
pub fn drop_edges(doc: &LayoutDoc, container: usize) -> Vec<DockEdge> {
    use DockEdge::*;
    let full = vec![Left, Right, Top, Bottom, Center];
    let areas = area_paths(doc).into_iter().filter(|(ci, _)| *ci == container).count();
    if doc.containers.get(container).is_none() || areas == 0 {
        return Vec::new();
    }
    if areas == 1 {
        return vec![Center];
    }
    full
}

// ---------------------------------------------------------------------------
// Drag session: the state machine behind press-drag-drop.
// ---------------------------------------------------------------------------

/// Where a dragged widget hovers.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum DropTarget {
    /// An area's zone (`edge` of `path` in `container`).
    Section { container: usize, path: Vec<usize>, edge: DockEdge },
    /// The container cross centre (solo tabs in, multi takes the fallback).
    ContainerCenter { container: usize },
    /// The container cross edge (root split).
    ContainerEdge { container: usize, edge: DockEdge },
}

/// Idle → dragging → over → committed/cancelled. The payload is a widget
/// name; targets resolve against the live document at commit time, so a
/// layout that changed mid-drag fails closed instead of mis-docking.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct DragSession {
    payload: Option<String>,
    over: Option<DropTarget>,
}

impl DragSession {
    pub fn is_active(&self) -> bool {
        self.payload.is_some()
    }

    pub fn payload(&self) -> Option<&str> {
        self.payload.as_deref()
    }

    pub fn over(&self) -> Option<&DropTarget> {
        self.over.as_ref()
    }

    pub fn begin(&mut self, name: &str) {
        self.payload = Some(name.to_string());
        self.over = None;
    }

    pub fn hover(&mut self, target: DropTarget) {
        if self.is_active() {
            self.over = Some(target);
        }
    }

    pub fn cancel(&mut self) {
        self.payload = None;
        self.over = None;
    }

    /// Move the payload to the hovered target. The session ends either way.
    pub fn commit(&mut self, doc: &mut LayoutDoc) -> Result<(), LaceError> {
        let result = match (self.payload.take(), self.over.take()) {
            (Some(name), Some(target)) => match target {
                DropTarget::Section { container, path, edge } => {
                    move_widget(doc, &name, edge, (container, path))
                }
                DropTarget::ContainerCenter { container } => {
                    move_container_center(doc, &name, container)
                }
                DropTarget::ContainerEdge { container, edge } => {
                    drop_container_edge(doc, &name, container, edge)
                }
            },
            (Some(_), None) => Err(op_error("drop had no target")),
            (None, _) => Err(op_error("drop had no payload")),
        };
        self.payload = None;
        self.over = None;
        result
    }
}

/// Drop non-main containers that hold no widget nodes (and their geometry
/// copies). Dragging the last widget out of a float would otherwise leave
/// an empty window behind. Returns the removed ids.
pub fn gc_empty_floats(doc: &mut LayoutDoc) -> Vec<String> {
    fn has_widget(node: &TreeNode) -> bool {
        match node {
            TreeNode::Area { widgets, .. } => {
                widgets.iter().any(|w| w.node_type == "Widget" && w.name.is_some())
            }
            TreeNode::Splitter { children, .. } => children.iter().any(has_widget),
            TreeNode::Unknown => false,
        }
    }
    let mut removed = Vec::new();
    let mut kept = Vec::with_capacity(doc.containers.len());
    for container in doc.containers.drain(..) {
        if !container.is_main && !has_widget(&container.data.root_splitter) {
            if let Some(id) = container.id.clone() {
                doc.container_geometries.remove(&id);
                removed.push(id);
            }
        } else {
            kept.push(container);
        }
    }
    doc.containers = kept;
    removed
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
    use crate::layout_doc::validate_doc;
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
    fn splitter_sizes_round_trip() {
        let mut doc = golden("docked_tabs");
        // Root of the fixture is a splitter; overwrite then verify.
        set_splitter_sizes(&mut doc, 0, &[], &[475.0, 216.0]).unwrap();
        match &doc.containers[0].data.root_splitter {
            TreeNode::Splitter { sizes, .. } => {
                assert_eq!(sizes.len(), 2);
                assert_eq!(sizes[0], serde_json::json!(475.0));
            }
            other => panic!("expected splitter, got {other:?}"),
        }
        assert_valid(&mut doc);
        // Length mismatch and non-positive entries fail closed.
        assert!(set_splitter_sizes(&mut doc, 0, &[], &[1.0]).is_err());
        assert!(set_splitter_sizes(&mut doc, 0, &[], &[1.0, 0.0]).is_err());
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
    fn pin_and_unpin_roundtrip() {
        let mut doc = golden("docked_tabs");
        pin_widget(&mut doc, "Gamma", "left").unwrap();
        assert_eq!(doc.sidebars.pinned_widgets.get("Gamma").map(String::as_str), Some("left"));
        assert!(doc.sidebars.sidebar_areas.contains(&"left".to_string()));
        // Gamma left the tree but stays registered.
        assert!(doc.widget_states.contains_key("Gamma"));
        assert_valid(&mut doc);
        // Re-pinning moves it between areas.
        pin_widget(&mut doc, "Gamma", "right").unwrap();
        assert_eq!(doc.sidebars.pinned_widgets.get("Gamma").map(String::as_str), Some("right"));
        assert_valid(&mut doc);
        unpin_widget(&mut doc, "Gamma").unwrap();
        assert!(!doc.sidebars.pinned_widgets.contains_key("Gamma"));
        assert_valid(&mut doc);
        assert!(unpin_widget(&mut doc, "Gamma").is_err());
        assert!(pin_widget(&mut doc, "Nobody", "left").is_err());
    }

    #[test]
    fn center_is_its_own_edge_never_a_split() {
        // Port of test_center_is_not_silently_treated_as_bottom: centre
        // tabs; it must never alias to a vertical-append split.
        assert_eq!(DockEdge::parse("center"), Some(DockEdge::Center));
        assert_eq!(DockEdge::parse("centre"), Some(DockEdge::Center));
        assert_ne!(DockEdge::parse("center"), Some(DockEdge::Bottom));
        assert_eq!(DockEdge::parse("sideways"), None);
    }

    #[test]
    fn center_move_tabs_appended_and_current() {
        // Ports test_dropped_tabs_are_appended_not_prepended +
        // test_the_dropped_widget_becomes_current.
        let mut doc = golden("docked_tabs");
        let target = area_paths(&doc).into_iter().find(|(_, p)| p == &[0]).unwrap();
        move_widget(&mut doc, "Delta", DockEdge::Center, target.clone()).unwrap();
        // Delta's old area emptied, so the root collapsed to one tabbed area.
        match &doc.containers[target.0].data.root_splitter {
            TreeNode::Area { widgets, current, .. } => {
                let names: Vec<&str> =
                    widgets.iter().map(|w| w.name.as_deref().unwrap()).collect();
                assert_eq!(names, vec!["Alpha", "Beta", "Gamma", "Delta"]);
                assert_eq!(*current, serde_json::json!("Delta"));
            }
            other => panic!("expected a collapsed area, got {other:?}"),
        }
        assert_valid(&mut doc);
    }

    #[test]
    fn solo_container_center_tabs() {
        // Ports test_dropping_on_centre_of_a_solo_container_tabs.
        let mut doc = blank_doc(0);
        dock_widget(&mut doc, "Alpha", DockEdge::Center, None, false).unwrap();
        dock_widget(&mut doc, "Beta", DockEdge::Float, None, false).unwrap();
        assert_eq!(drop_edges(&doc, 0), vec![DockEdge::Center]);
        move_container_center(&mut doc, "Beta", 0).unwrap();
        assert_eq!(area_paths(&doc).iter().filter(|(ci, _)| *ci == 0).count(), 1);
        assert_valid(&mut doc);
    }

    #[test]
    fn multi_container_center_takes_the_fallback_split() {
        // Ports test_multi_area_centre_drop_still_splits: ambiguous centre
        // divides instead of tabbing.
        let mut doc = golden("docked_tabs");
        let before: Vec<i64> = match &doc.containers[0].data.root_splitter {
            TreeNode::Splitter { sizes, .. } => {
                sizes.iter().map(|s| s.as_i64().unwrap()).collect()
            }
            _ => panic!("golden root splits"),
        };
        move_container_center(&mut doc, "Gamma", 0).unwrap();
        match &doc.containers[0].data.root_splitter {
            TreeNode::Splitter { orientation, sizes, children, .. } => {
                assert_eq!(orientation, "|");
                assert_eq!(children.len(), 3);
                assert_eq!(sizes.len(), 3);
                let kept: Vec<i64> = sizes[..2].iter().map(|s| s.as_i64().unwrap()).collect();
                assert_eq!(kept, before, "existing proportions survive the append");
            }
            _ => panic!("fallback must split the root"),
        }
        assert_valid(&mut doc);
    }

    #[test]
    fn container_edge_splits_root_directionally() {
        let mut doc = golden("docked_tabs");
        drop_container_edge(&mut doc, "Delta", 0, DockEdge::Left).unwrap();
        match &doc.containers[0].data.root_splitter {
            TreeNode::Splitter { orientation, children, .. } => {
                assert_eq!(orientation, "-");
                assert_eq!(children.len(), 2);
            }
            _ => panic!("edge drop must wrap the root"),
        }
        assert_valid(&mut doc);
    }

    #[test]
    fn drop_edges_offer_center_only_to_solo_areas() {
        // Ports test_a_solo_area_offers_the_centre_indicator +
        // test_a_multi_area_container_still_offers_everything.
        let mut solo = blank_doc(0);
        dock_widget(&mut solo, "Alpha", DockEdge::Center, None, false).unwrap();
        assert_eq!(drop_edges(&solo, 0), vec![DockEdge::Center]);
        let multi = golden("docked_tabs");
        assert_eq!(
            drop_edges(&multi, 0),
            vec![
                DockEdge::Left,
                DockEdge::Right,
                DockEdge::Top,
                DockEdge::Bottom,
                DockEdge::Center
            ]
        );
        assert!(drop_edges(&multi, 9).is_empty());
    }

    #[test]
    fn drag_session_moves_through_commit() {
        let mut doc = golden("docked_tabs");
        let mut session = DragSession::default();
        assert!(!session.is_active());
        session.begin("Gamma");
        assert_eq!(session.payload(), Some("Gamma"));
        let target = area_paths(&doc).into_iter().find(|(_, p)| p == &[1]).unwrap();
        session.hover(DropTarget::Section {
            container: target.0,
            path: target.1.clone(),
            edge: DockEdge::Center,
        });
        session.commit(&mut doc).unwrap();
        assert!(!session.is_active());
        let root = &doc.containers[target.0].data.root_splitter;
        let mut probe = root.clone();
        let area = area_fields_mut(&mut probe, &target.1).unwrap();
        assert!(area.widgets.iter().any(|w| w.name.as_deref() == Some("Gamma")));
        assert_valid(&mut doc);
    }

    #[test]
    fn drag_session_fails_closed_and_ends() {
        let mut doc = golden("docked_tabs");
        let mut session = DragSession::default();
        session.begin("Gamma");
        assert!(session.commit(&mut doc).is_err(), "targetless drop must fail");
        assert!(!session.is_active(), "failed commit still ends the session");
        // Stale payload: the widget left mid-drag.
        session.begin("Nobody");
        session.hover(DropTarget::ContainerCenter { container: 0 });
        assert!(session.commit(&mut doc).is_err());
        assert_valid(&mut doc);
        // Hovering idle records nothing.
        session.hover(DropTarget::ContainerCenter { container: 0 });
        assert!(!session.is_active());
        session.begin("Gamma");
        session.cancel();
        assert!(!session.is_active());
    }

    #[test]
    fn every_zone_commits_where_previewed() {
        // Port of test_the_drop_uses_the_same_policy_as_the_preview: each
        // offered zone must accept a drop through the session.
        for edge in [DockEdge::Left, DockEdge::Right, DockEdge::Top, DockEdge::Bottom, DockEdge::Center] {
            let mut doc = golden("docked_tabs");
            let target = area_paths(&doc)[0].clone();
            let mut session = DragSession::default();
            session.begin("Delta");
            session.hover(DropTarget::Section {
                container: target.0,
                path: target.1,
                edge,
            });
            session.commit(&mut doc).unwrap_or_else(|e| panic!("{edge:?} zone refused: {e}"));
            assert_valid(&mut doc);
        }
    }

    #[test]
    fn float_drag_dock_roundtrip() {
        // Phase-5 exit, core half: float → drag → dock restores the tabs.
        let mut doc = golden("docked_tabs");
        let id = float_widget(&mut doc, "Gamma").unwrap();
        assert_valid(&mut doc);
        let target = area_paths(&doc).into_iter().find(|(_, p)| p == &[0]).unwrap();
        let mut session = DragSession::default();
        session.begin("Gamma");
        session.hover(DropTarget::Section {
            container: target.0,
            path: target.1.clone(),
            edge: DockEdge::Center,
        });
        session.commit(&mut doc).unwrap();
        dock_floating(&mut doc, &id).unwrap_or(()); // already empty; must not fail the roundtrip
        assert_valid(&mut doc);
        let names: Vec<String> = {
            let mut out = Vec::new();
            let mut path = Vec::new();
            node_widgets(&doc.containers[0].data.root_splitter, &mut out, &mut path);
            out.into_iter().map(|(_, n)| n).collect()
        };
        assert!(names.contains(&"Gamma".to_string()));
    }

    #[test]
    fn empty_floats_are_collected() {
        let mut doc = golden("floating");
        let floats_before = doc.containers.iter().filter(|c| !c.is_main).count();
        assert_eq!(floats_before, 1);
        let target = area_paths(&doc).into_iter().find(|(ci, _)| doc.containers[*ci].is_main).unwrap();
        move_widget(&mut doc, "Beta", DockEdge::Center, target).unwrap();
        let removed = gc_empty_floats(&mut doc);
        assert_eq!(removed.len(), 1);
        assert!(doc.containers.iter().all(|c| c.is_main));
        assert_valid(&mut doc);
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
