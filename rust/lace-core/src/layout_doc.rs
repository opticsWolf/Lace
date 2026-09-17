//! `lace-core::layout_doc`: the 0.7.x layout document model + validation.
//!
//! Ports the data contract of `lace/layout_serializer.py`
//! (`LayoutStateBuilder` output shape, `LayoutEngine` pre-validation and the
//! testing-path structural dry-run) with zero Qt. Applying a validated
//! document to live widgets stays on the Qt side (Phases 3–5); everything
//! here is pure data in, verdict out.
//!
//! Deliberate deviations from Python (all covered by tests):
//! * `container_geometries` that is not a dict is rejected (`InvalidFormat`)
//!   instead of raising bare `AttributeError` mid-restore.
//! * `count` must be a JSON number (Python would compare any type against
//!   `len(sizes)` and fail closed anyway, except for boolean nonsense).
//! * `widget_states` values must be `{"closed": bool}` (Python only reads
//!   the keys; real files always write exactly this).

use std::collections::{BTreeMap, HashSet};

use serde::{Deserialize, Deserializer, Serialize};

use crate::error::LaceError;

/// `"type"` tag written by current builds.
pub const SYSTEM_TYPE: &str = "LaceDockingSystem";
/// Types accepted on read so older saved layouts keep working.
pub const LEGACY_SYSTEM_TYPES: &[&str] = &["QtAdvancedDockingSystem"];
/// Layout-format version. Bump when the tree shape changes. Distinct from
/// the `version` field, which is the calling application's own data version.
pub const SCHEMA_VERSION: u32 = 1;
/// Upper bound the validator accepts for a floating geometry edge.
pub const MAX_GEOMETRY_EDGE: i64 = 32_000;

// ---------------------------------------------------------------------------
// Document model (field names are the 0.7.x JSON contract, verbatim)
// ---------------------------------------------------------------------------

/// A floating-window geometry entry. Numbers stay `Value`s so a validated
/// document re-serializes bit-identically.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct GeometryEntry {
    pub x: serde_json::Value,
    pub y: serde_json::Value,
    pub width: serde_json::Value,
    pub height: serde_json::Value,
    #[serde(default)]
    pub is_maximized: serde_json::Value,
}

/// One widget tab inside an area.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct WidgetNode {
    #[serde(default, rename = "type")]
    pub node_type: String,
    #[serde(default)]
    pub name: Option<String>,
    #[serde(default = "default_false")]
    pub closed: serde_json::Value,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub locked_to_area: Option<serde_json::Value>,
}

fn default_false() -> serde_json::Value {
    serde_json::Value::Bool(false)
}

/// Splitter orientation tokens: `"-"` horizontal, `"|"` vertical.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum SplitOrientation {
    Horizontal,
    Vertical,
    Other(String),
}

impl SplitOrientation {
    pub fn token(&self) -> &str {
        match self {
            SplitOrientation::Horizontal => "-",
            SplitOrientation::Vertical => "|",
            SplitOrientation::Other(s) => s.as_str(),
        }
    }
}

/// One node of a container tree. Unknown or missing tags decode as
/// [`TreeNode::Unknown`] and pass structural validation — exactly like the
/// testing path, which only knows `"Splitter"` and `"Area"`.
#[derive(Clone, Debug, PartialEq)]
pub enum TreeNode {
    Splitter {
        orientation: String,
        count: serde_json::Value,
        sizes: Vec<serde_json::Value>,
        children: Vec<TreeNode>,
    },
    Area {
        tabs: serde_json::Value,
        current: serde_json::Value,
        widgets: Vec<WidgetNode>,
        locked_name: Option<String>,
    },
    Unknown,
}

impl<'de> Deserialize<'de> for TreeNode {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        let value = serde_json::Value::deserialize(deserializer)?;
        let tag = value.get("type").and_then(|t| t.as_str()).unwrap_or("");
        match tag {
            "Splitter" => {
                let orientation = value
                    .get("orientation")
                    .and_then(|o| o.as_str())
                    .unwrap_or("-")
                    .to_string();
                let count = value.get("count").cloned().unwrap_or(serde_json::Value::Null);
                let sizes = value
                    .get("sizes")
                    .and_then(|s| s.as_array())
                    .cloned()
                    .unwrap_or_default();
                let children = value
                    .get("children")
                    .and_then(|c| serde_json::from_value(c.clone()).ok())
                    .unwrap_or_default();
                Ok(TreeNode::Splitter { orientation, count, sizes, children })
            }
            "Area" => {
                let tabs = value.get("tabs").cloned().unwrap_or(serde_json::json!(0));
                let current =
                    value.get("current").cloned().unwrap_or(serde_json::json!(""));
                let widgets = value
                    .get("widgets")
                    .and_then(|w| serde_json::from_value(w.clone()).ok())
                    .unwrap_or_default();
                let locked_name = value
                    .get("locked_name")
                    .and_then(|l| l.as_str())
                    .map(str::to_string);
                Ok(TreeNode::Area { tabs, current, widgets, locked_name })
            }
            _ => Ok(TreeNode::Unknown),
        }
    }
}

impl Serialize for TreeNode {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        use serde::ser::SerializeMap;
        match self {
            TreeNode::Splitter { orientation, count, sizes, children } => {
                let mut map = serializer.serialize_map(Some(5))?;
                map.serialize_entry("type", "Splitter")?;
                map.serialize_entry("orientation", orientation)?;
                map.serialize_entry("count", count)?;
                map.serialize_entry("sizes", sizes)?;
                map.serialize_entry("children", children)?;
                map.end()
            }
            TreeNode::Area { tabs, current, widgets, locked_name } => {
                let mut map = serializer.serialize_map(None)?;
                map.serialize_entry("type", "Area")?;
                map.serialize_entry("tabs", tabs)?;
                map.serialize_entry("current", current)?;
                map.serialize_entry("widgets", widgets)?;
                if let Some(name) = locked_name {
                    map.serialize_entry("locked_name", name)?;
                }
                map.end()
            }
            // Unknown nodes only arise from documents that had no `type`;
            // re-serializing them as `{}` keeps save→restore→save stable.
            TreeNode::Unknown => {
                let map = serializer.serialize_map(Some(0))?;
                map.end()
            }
        }
    }
}

/// One entry of the `containers` roster.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct ContainerEntry {
    #[serde(default)]
    pub id: Option<String>,
    #[serde(default)]
    pub is_main: bool,
    #[serde(default)]
    pub data: ContainerData,
}

/// A container's saved tree. `geometry` is an opaque Qt blob (hex with
/// space separators); validation only requires it to decode non-empty.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct ContainerData {
    #[serde(default)]
    pub floating: bool,
    #[serde(default)]
    pub geometry: String,
    #[serde(default)]
    pub root_splitter: TreeNode,
}

impl Default for ContainerData {
    fn default() -> Self {
        ContainerData {
            floating: false,
            geometry: String::new(),
            root_splitter: TreeNode::Unknown,
        }
    }
}

impl Default for TreeNode {
    fn default() -> Self {
        TreeNode::Unknown
    }
}

/// Persistent per-sidebar overlay sizes (`SidebarState.to_dict`).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct SidebarStateData {
    pub width: i64,
    pub height: i64,
    pub expanded_tabs: Vec<String>,
}

impl Default for SidebarStateData {
    fn default() -> Self {
        SidebarStateData { width: 280, height: 250, expanded_tabs: Vec::new() }
    }
}

/// Sidebar settings block with the restore-time defaults.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct SidebarSettings {
    #[serde(default = "default_true")]
    pub auto_show_on_hover: bool,
    #[serde(default = "default_true")]
    pub animations_enabled: bool,
    #[serde(default)]
    pub keep_open: bool,
}

fn default_true() -> bool {
    true
}

impl Default for SidebarSettings {
    fn default() -> Self {
        SidebarSettings {
            auto_show_on_hover: true,
            animations_enabled: true,
            keep_open: false,
        }
    }
}

/// The `sidebars` block. Lenient on read (a corrupt block warns and drops,
/// like the `try/except` in `restore_state`), strict on write.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Default)]
pub struct SidebarDoc {
    #[serde(default)]
    pub pinned_widgets: BTreeMap<String, String>,
    #[serde(default)]
    pub overlay_sizes: BTreeMap<String, SidebarStateData>,
    #[serde(default)]
    pub active_widget: Option<String>,
    #[serde(default)]
    pub sidebar_areas: Vec<String>,
    #[serde(default)]
    pub settings: SidebarSettings,
}

impl<'de> Deserialize<'de> for SidebarDoc {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        #[derive(Deserialize)]
        struct Strict {
            #[serde(default)]
            pinned_widgets: BTreeMap<String, String>,
            #[serde(default)]
            overlay_sizes: BTreeMap<String, SidebarStateData>,
            #[serde(default)]
            active_widget: Option<String>,
            #[serde(default)]
            sidebar_areas: Vec<String>,
            #[serde(default)]
            settings: SidebarSettings,
        }
        let value = serde_json::Value::deserialize(deserializer)?;
        // Mirror `restore_state`'s tolerance: anything unparsable becomes an
        // empty block (the validator records the warning separately).
        match serde_json::from_value::<Strict>(value) {
            Ok(strict) => Ok(SidebarDoc {
                pinned_widgets: strict.pinned_widgets,
                overlay_sizes: strict.overlay_sizes,
                active_widget: strict.active_widget,
                sidebar_areas: strict.sidebar_areas,
                settings: strict.settings,
            }),
            Err(_) => Ok(SidebarDoc::default()),
        }
    }
}

/// One `widget_states` roster entry.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
pub struct WidgetStateEntry {
    #[serde(default)]
    pub closed: bool,
}

/// The whole layout document.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub struct LayoutDoc {
    #[serde(rename = "type")]
    pub system_type: String,
    /// Missing on layouts predating the field — those are schema 0.
    #[serde(default)]
    pub schema: u32,
    pub version: i64,
    pub containers: Vec<ContainerEntry>,
    #[serde(default)]
    pub sidebars: SidebarDoc,
    #[serde(default)]
    pub container_geometries: BTreeMap<String, GeometryEntry>,
    pub widget_states: BTreeMap<String, WidgetStateEntry>,
}

impl LayoutDoc {
    /// Parse a layout string. Malformed JSON and schema violations both
    /// surface as [`LaceError::InvalidFormat`], mirroring `deserialize()`
    /// raising `InvalidFormatError` for either.
    pub fn parse(text: &str) -> Result<Self, LaceError> {
        serde_json::from_str(text)
            .map_err(|e| LaceError::InvalidFormat(format!("invalid JSON data: {e}")))
    }

    /// Render back to JSON. `formatted` selects the indented form (what
    /// `LayoutPersistenceManager.save_layout(formatted=True)` writes).
    pub fn render(&self, formatted: bool) -> Result<String, LaceError> {
        if formatted {
            serde_json::to_string_pretty(self)
        } else {
            serde_json::to_string(self)
        }
        .map_err(LaceError::Json)
    }
}

// ---------------------------------------------------------------------------
// Validation (port of LayoutSerializer.deserialize guards + dry-run)
// ---------------------------------------------------------------------------

/// Outcome of [`validate_doc`]: non-fatal notes plus the roster entries the
/// document lost because the application no longer registers them.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct ValidationReport {
    pub warnings: Vec<String>,
    pub pruned_widgets: Vec<String>,
}

fn is_number(value: &serde_json::Value) -> bool {
    value.as_i64().is_some() || value.as_f64().is_some()
}

fn decode_hex_blob(blob: &str) -> Vec<u8> {
    let mut out = Vec::with_capacity(blob.len() / 2);
    let nibbles: Vec<u8> = blob
        .chars()
        .filter(|c| !c.is_whitespace())
        .map(|c| c.to_digit(16).map(|v| v as u8))
        .collect::<Option<Vec<_>>>()
        .unwrap_or_default();
    for pair in nibbles.chunks(2) {
        if pair.len() == 2 {
            out.push((pair[0] * 16 + pair[1]) as u8);
        }
    }
    out
}

fn dry_run_node(node: &TreeNode, container_index: usize, cid: &str) -> Result<(), LaceError> {
    let failure = |detail: String| {
        LaceError::RestoreFailure(format!(
            "container {container_index} ({cid}) failed structural validation: {detail}"
        ))
    };
    match node {
        TreeNode::Unknown => Ok(()),
        TreeNode::Splitter { count, sizes, children, .. } => {
            let count = count.as_u64().ok_or_else(|| failure("splitter `count` is not a number".into()))?;
            if count == 0 {
                return Err(failure("splitter `count` is zero".into()));
            }
            for child in children {
                dry_run_node(child, container_index, cid)?;
            }
            if sizes.len() as u64 != count {
                return Err(failure(format!(
                    "splitter `sizes` length {} does not match `count` {count}",
                    sizes.len()
                )));
            }
            Ok(())
        }
        TreeNode::Area { widgets, .. } => {
            for widget in widgets {
                if widget.node_type != "Widget" {
                    continue;
                }
                match widget.name.as_deref() {
                    Some(name) if !name.is_empty() => {}
                    _ => return Err(failure("dock area entry has no `name`".into())),
                }
            }
            Ok(())
        }
    }
}

/// Validate a parsed document the way `deserialize()` + the dry-run do:
/// system tag, schema window, application version, geometry bounds, widget
/// roster, then the structural dry-run per container.
///
/// `available` is the application's registered widget roster; references the
/// layout makes to anything else are pruned (with a warning), never fatal.
/// The document is mutated only by that pruning.
pub fn validate_doc(
    doc: &mut LayoutDoc,
    target_version: i64,
    available: &HashSet<String>,
) -> Result<ValidationReport, LaceError> {
    let mut report = ValidationReport::default();

    if doc.system_type != SYSTEM_TYPE && !LEGACY_SYSTEM_TYPES.contains(&doc.system_type.as_str()) {
        return Err(LaceError::InvalidFormat(format!(
            "invalid system type `{}` (expected {SYSTEM_TYPE})",
            doc.system_type
        )));
    }
    if doc.schema > SCHEMA_VERSION {
        return Err(LaceError::InvalidFormat(format!(
            "layout schema v{} was written by a newer Lace (this build reads up to v{SCHEMA_VERSION})",
            doc.schema
        )));
    }
    if doc.schema < SCHEMA_VERSION {
        report.warnings.push(format!(
            "layout uses schema v{} (current is v{SCHEMA_VERSION}); newer fields fall back to defaults",
            doc.schema
        ));
    }
    if doc.version != target_version {
        return Err(LaceError::InvalidFormat(format!(
            "layout version mismatch: file is v{}, expected v{target_version}",
            doc.version
        )));
    }

    for (cid, geo) in &doc.container_geometries {
        for key in ["x", "y", "width", "height"] {
            let value = match key {
                "x" => &geo.x,
                "y" => &geo.y,
                "width" => &geo.width,
                _ => &geo.height,
            };
            if !is_number(value) {
                return Err(LaceError::InvalidFormat(format!(
                    "invalid or missing geometry key `{key}` for container {cid}"
                )));
            }
        }
        let (width, height) = (
            geo.width.as_i64().or_else(|| geo.width.as_f64().map(|f| f as i64)),
            geo.height.as_i64().or_else(|| geo.height.as_f64().map(|f| f as i64)),
        );
        match (width, height) {
            (Some(w), Some(h)) if w > 0 && h > 0 => {
                if w > MAX_GEOMETRY_EDGE || h > MAX_GEOMETRY_EDGE {
                    return Err(LaceError::InvalidFormat(format!(
                        "geometry dimensions for {cid} exceed maximum rendering bounds"
                    )));
                }
            }
            _ => {
                return Err(LaceError::InvalidFormat(format!(
                    "geometry dimensions for {cid} must be positive integers"
                )));
            }
        }
    }

    let saved: HashSet<String> = doc.widget_states.keys().cloned().collect();
    let known: HashSet<&str> = available.iter().map(String::as_str).collect();
    let saved_refs: HashSet<&str> = saved.iter().map(String::as_str).collect();
    let mut missing: Vec<&str> = saved_refs.difference(&known).copied().collect();
    missing.sort_unstable();
    for name in &missing {
        report.warnings.push(format!(
            "layout references missing widget `{name}`; ignoring it"
        ));
        report.pruned_widgets.push((*name).to_string());
    }
    for name in &missing {
        doc.widget_states.remove(*name);
    }

    for (index, container) in doc.containers.iter().enumerate() {
        let cid = container.id.as_deref().unwrap_or("?");
        if container.data.floating {
            if container.data.geometry.is_empty() {
                return Err(LaceError::RestoreFailure(format!(
                    "container {index} ({cid}) is floating but carries no geometry"
                )));
            }
            if decode_hex_blob(&container.data.geometry).is_empty() {
                return Err(LaceError::RestoreFailure(format!(
                    "container {index} ({cid}) carries an undecodable geometry blob"
                )));
            }
        }
        dry_run_node(&container.data.root_splitter, index, cid).map_err(|e| match e {
            LaceError::RestoreFailure(detail) => {
                LaceError::RestoreFailure(format!("container {index} ({cid}) is malformed: {detail}"))
            }
            other => other,
        })?;
    }

    Ok(report)
}

// ---------------------------------------------------------------------------
// Named perspectives (port of DockManager.add/remove/open_perspective)
// ---------------------------------------------------------------------------

/// Named saved layouts. Signals stay Qt-side; this is the backing store:
/// perspective name -> layout JSON string.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct Perspectives {
    entries: BTreeMap<String, String>,
}

impl Perspectives {
    pub fn add(&mut self, name: &str, layout_json: &str) {
        self.entries.insert(name.to_string(), layout_json.to_string());
    }

    pub fn remove(&mut self, name: &str) -> bool {
        self.entries.remove(name).is_some()
    }

    pub fn remove_all(&mut self, names: &[&str]) {
        for name in names {
            self.entries.remove(*name);
        }
    }

    pub fn names(&self) -> Vec<&str> {
        self.entries.keys().map(String::as_str).collect()
    }

    pub fn get(&self, name: &str) -> Option<&str> {
        self.entries.get(name).map(String::as_str)
    }

    pub fn len(&self) -> usize {
        self.entries.len()
    }

    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn number(n: i64) -> serde_json::Value {
        serde_json::json!(n)
    }

    fn widget(name: &str, closed: bool) -> WidgetNode {
        WidgetNode {
            node_type: "Widget".to_string(),
            name: Some(name.to_string()),
            closed: serde_json::json!(closed),
            locked_to_area: None,
        }
    }

    fn minimal_doc() -> LayoutDoc {
        LayoutDoc {
            system_type: SYSTEM_TYPE.to_string(),
            schema: SCHEMA_VERSION,
            version: 0,
            containers: vec![ContainerEntry {
                id: Some("main".to_string()),
                is_main: true,
                data: ContainerData {
                    floating: false,
                    geometry: String::new(),
                    root_splitter: TreeNode::Area {
                        tabs: number(1),
                        current: serde_json::json!("Alpha"),
                        widgets: vec![widget("Alpha", false)],
                        locked_name: None,
                    },
                },
            }],
            sidebars: SidebarDoc::default(),
            container_geometries: BTreeMap::new(),
            widget_states: BTreeMap::from([(
                "Alpha".to_string(),
                WidgetStateEntry { closed: false },
            )]),
        }
    }

    fn available(names: &[&str]) -> HashSet<String> {
        names.iter().map(|s| s.to_string()).collect()
    }

    #[test]
    fn minimal_doc_validates_clean() {
        let mut doc = minimal_doc();
        let report = validate_doc(&mut doc, 0, &available(&["Alpha"])).unwrap();
        assert!(report.warnings.is_empty());
        assert!(report.pruned_widgets.is_empty());
    }

    #[test]
    fn unknown_node_types_pass_the_dry_run() {
        // Mirrors _restore_child_nodes: only Splitter/Area are inspected.
        let mut doc = minimal_doc();
        doc.containers[0].data.root_splitter = TreeNode::Unknown;
        validate_doc(&mut doc, 0, &available(&["Alpha"])).unwrap();
    }

    #[test]
    fn non_widget_entries_are_skipped_not_failed() {
        let mut doc = minimal_doc();
        let TreeNode::Area { widgets, .. } = &mut doc.containers[0].data.root_splitter else {
            panic!("fixture shape");
        };
        widgets.push(WidgetNode {
            node_type: "LegacyWidget".to_string(),
            name: None,
            closed: serde_json::json!(false),
            locked_to_area: None,
        });
        validate_doc(&mut doc, 0, &available(&["Alpha"])).unwrap();
    }

    #[test]
    fn unnamed_widget_entries_fail() {
        let mut doc = minimal_doc();
        let TreeNode::Area { widgets, .. } = &mut doc.containers[0].data.root_splitter else {
            panic!("fixture shape");
        };
        widgets.push(WidgetNode {
            node_type: "Widget".to_string(),
            name: Some(String::new()),
            closed: serde_json::json!(false),
            locked_to_area: None,
        });
        match validate_doc(&mut doc, 0, &available(&["Alpha"])) {
            Err(LaceError::RestoreFailure(_)) => {}
            other => panic!("expected RestoreFailure, got {other:?}"),
        }
    }

    #[test]
    fn splitter_sizes_must_match_count() {
        let mut doc = minimal_doc();
        doc.containers[0].data.root_splitter = TreeNode::Splitter {
            orientation: "-".to_string(),
            count: number(2),
            sizes: vec![number(400)],
            children: vec![TreeNode::Unknown, TreeNode::Unknown],
        };
        match validate_doc(&mut doc, 0, &available(&["Alpha"])) {
            Err(LaceError::RestoreFailure(_)) => {}
            other => panic!("expected RestoreFailure, got {other:?}"),
        }
    }

    #[test]
    fn zero_count_splitters_fail() {
        let mut doc = minimal_doc();
        doc.containers[0].data.root_splitter = TreeNode::Splitter {
            orientation: "-".to_string(),
            count: number(0),
            sizes: vec![],
            children: vec![],
        };
        assert!(matches!(
            validate_doc(&mut doc, 0, &available(&["Alpha"])),
            Err(LaceError::RestoreFailure(_))
        ));
    }

    #[test]
    fn floating_containers_need_decodable_geometry() {
        let mut doc = minimal_doc();
        doc.containers[0].data.floating = true;
        assert!(matches!(
            validate_doc(&mut doc, 0, &available(&["Alpha"])),
            Err(LaceError::RestoreFailure(_))
        ));
        doc.containers[0].data.geometry = "zz top".to_string();
        assert!(matches!(
            validate_doc(&mut doc, 0, &available(&["Alpha"])),
            Err(LaceError::RestoreFailure(_))
        ));
        doc.containers[0].data.geometry = "01 02 03".to_string();
        validate_doc(&mut doc, 0, &available(&["Alpha"])).unwrap();
    }

    #[test]
    fn wrong_system_type_is_rejected() {
        let mut doc = minimal_doc();
        doc.system_type = "NotLace".to_string();
        assert!(matches!(
            validate_doc(&mut doc, 0, &available(&["Alpha"])),
            Err(LaceError::InvalidFormat(_))
        ));
    }

    #[test]
    fn legacy_system_type_is_accepted() {
        let mut doc = minimal_doc();
        doc.system_type = LEGACY_SYSTEM_TYPES[0].to_string();
        doc.schema = 0;
        let report = validate_doc(&mut doc, 0, &available(&["Alpha"])).unwrap();
        assert_eq!(report.warnings.len(), 1);
    }

    #[test]
    fn future_schema_is_rejected() {
        let mut doc = minimal_doc();
        doc.schema = 999;
        assert!(matches!(
            validate_doc(&mut doc, 0, &available(&["Alpha"])),
            Err(LaceError::InvalidFormat(_))
        ));
    }

    #[test]
    fn app_version_mismatch_is_rejected() {
        let mut doc = minimal_doc();
        assert!(matches!(
            validate_doc(&mut doc, 7, &available(&["Alpha"])),
            Err(LaceError::InvalidFormat(_))
        ));
    }

    #[test]
    fn missing_widgets_are_pruned_with_a_warning() {
        let mut doc = minimal_doc();
        doc.widget_states.insert("Ghost".to_string(), WidgetStateEntry { closed: false });
        let report = validate_doc(&mut doc, 0, &available(&["Alpha"])).unwrap();
        assert_eq!(report.pruned_widgets, vec!["Ghost".to_string()]);
        assert_eq!(report.warnings.len(), 1);
        assert!(!doc.widget_states.contains_key("Ghost"));
    }

    #[test]
    fn perspectives_store_named_layouts() {
        let mut perspectives = Perspectives::default();
        assert!(perspectives.is_empty());
        perspectives.add("wide", "{\"version\": 0}");
        perspectives.add("tall", "{\"version\": 0}");
        assert_eq!(perspectives.names(), vec!["tall", "wide"]);
        assert_eq!(perspectives.get("wide"), Some("{\"version\": 0}"));
        assert!(perspectives.remove("wide"));
        assert!(!perspectives.remove("wide"));
        perspectives.remove_all(&["tall", "missing"]);
        assert!(perspectives.is_empty());
    }
}
