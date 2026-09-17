//! `_lace_rs`: thin PyO3 wrappers over `lace-core`.
//!
//! No logic lives here — every function delegates to `lace-core` so the
//! Python shim and the QML front-end can never disagree. Qt is deliberately
//! *not* linked into this module (see the plan §6 linkage rule).
//!
//! Boundary convention: layout documents cross as compact JSON strings
//! (parsed into Python dicts with `json.loads` when needed); colours cross
//! as `[r, g, b, a]` lists. Errors mirror `lace/layout_serializer.py`:
//! `LayoutError` with `LayoutIOError` / `InvalidFormatError` /
//! `RestoreFailureError` subclasses, plus a standalone `ValidationError`
//! for theme files (like pydantic's, it is *not* a `LayoutError`).

use pyo3::create_exception;
use pyo3::exceptions::{PyFileNotFoundError, PyValueError};
use pyo3::prelude::*;
use std::collections::HashSet;

create_exception!(_lace_rs, LayoutError, pyo3::exceptions::PyException);
create_exception!(_lace_rs, LayoutIOError, LayoutError);
create_exception!(_lace_rs, InvalidFormatError, LayoutError);
create_exception!(_lace_rs, RestoreFailureError, LayoutError);
create_exception!(_lace_rs, ValidationError, pyo3::exceptions::PyException);

fn layout_error(e: lace_core::error::LaceError) -> PyErr {
    use lace_core::error::LaceError::*;
    match e {
        InvalidFormat(_) | VersionMismatch { .. } | Json(_) => {
            InvalidFormatError::new_err(e.to_string())
        }
        RestoreFailure(_) => RestoreFailureError::new_err(e.to_string()),
        LayoutIo(_) | Io(_) => LayoutIOError::new_err(e.to_string()),
        InvalidLayout(_) => LayoutError::new_err(e.to_string()),
        InvalidTheme(_) => ValidationError::new_err(e.to_string()),
    }
}

fn theme_error(e: lace_core::theme_json::ThemeError) -> PyErr {
    use lace_core::theme_json::ThemeError::*;
    match e {
        Validation(message) => ValidationError::new_err(message),
        // Approximation: `json.JSONDecodeError` subclasses `ValueError`.
        Json(e) => PyValueError::new_err(e.to_string()),
        Io(e) if e.kind() == std::io::ErrorKind::NotFound => {
            PyFileNotFoundError::new_err(e.to_string())
        }
        Io(e) => LayoutIOError::new_err(e.to_string()),
    }
}

fn parse_doc(json: &str) -> Result<lace_core::layout_doc::LayoutDoc, PyErr> {
    lace_core::layout_doc::LayoutDoc::parse(json)
        .map_err(|e| InvalidFormatError::new_err(e.to_string()))
}

fn render_doc(doc: &lace_core::layout_doc::LayoutDoc) -> Result<String, PyErr> {
    doc.render(false).map_err(layout_error)
}

fn parse_edge(edge: &str) -> Result<lace_core::layout_ops::DockEdge, PyErr> {
    // Mirrors `dock_area_insert_parameters`: an unknown edge is a ValueError,
    // never a silent alias.
    lace_core::layout_ops::DockEdge::parse(edge)
        .ok_or_else(|| PyValueError::new_err(format!("unknown edge `{edge}`")))
}

#[pyfunction]
fn split_share(target_size: u32, handle_width: u32, n_total: u32) -> u32 {
    lace_core::split_share(target_size, handle_width, n_total)
}

#[pyfunction]
fn allowed_areas(visible_area_count: usize, target_present: bool) -> u32 {
    lace_core::allowed_areas_for(visible_area_count, target_present).bits()
}

// ---------------------------------------------------------------------------
// Themes
// ---------------------------------------------------------------------------

#[pyfunction]
fn available_themes() -> Vec<String> {
    lace_core::presets_generated::preset_keys()
        .into_iter()
        .map(str::to_string)
        .collect()
}

#[pyfunction]
fn theme_groups() -> String {
    let keys = lace_core::presets_generated::preset_keys();
    let groups = lace_core::theme::theme_groups(
        lace_core::presets_generated::THEME_GROUP_ORDER,
        &keys,
    );
    serde_json::to_string(&groups).expect("groups serialize")
}

/// Engine-shaped theme dict (like a `DOCK_THEMES` entry), as JSON.
#[pyfunction]
fn build_theme(name: &str) -> PyResult<String> {
    use lace_core::presets_generated::{default_spec, preset_specs};
    let spec = if name == "default" {
        Some(default_spec())
    } else {
        preset_specs().into_iter().find(|(key, _)| *key == name).map(|(_, spec)| spec)
    };
    match spec {
        Some(spec) => {
            let theme = lace_core::theme::build_theme(&spec);
            serde_json::to_string(&theme).map_err(|e| LayoutError::new_err(e.to_string()))
        }
        None => Err(LayoutError::new_err(format!("unknown theme `{name}`"))),
    }
}

/// `get_all()`-shaped theme dict (schema defaults under the engine output).
#[pyfunction]
fn build_merged_theme(name: &str) -> PyResult<String> {
    lace_core::style::render_merged_theme(name).map_err(LayoutError::new_err)
}

/// Load a JSON theme file and derive the full theme dict, as JSON.
#[pyfunction]
fn load_theme_file(path: &str) -> PyResult<String> {
    let theme = lace_core::theme_json::ThemeJson::load(path).map_err(theme_error)?;
    serde_json::to_string(&theme.build_theme_dict())
        .map_err(|e| ValidationError::new_err(e.to_string()))
}

// ---------------------------------------------------------------------------
// Layout documents
// ---------------------------------------------------------------------------

/// A fresh, valid empty document, as JSON.
#[pyfunction]
fn blank_layout(app_version: i64) -> PyResult<String> {
    render_doc(&lace_core::layout_ops::blank_doc(app_version))
}

/// Validate a layout document.
///
/// Returns `{"warnings": [...], "pruned": [...], "doc": "<pruned JSON>"}`.
/// Corrupt payloads raise `InvalidFormatError`; structurally broken trees
/// raise `RestoreFailureError` (the live layout must be left untouched).
#[pyfunction]
fn validate_layout(
    doc_json: &str,
    target_version: i64,
    available: Vec<String>,
) -> PyResult<String> {
    let mut doc = parse_doc(doc_json)?;
    let roster: HashSet<String> = available.into_iter().collect();
    let report = lace_core::layout_doc::validate_doc(&mut doc, target_version, &roster)
        .map_err(layout_error)?;
    let out = serde_json::json!({
        "warnings": report.warnings,
        "pruned": report.pruned_widgets,
        "doc": render_doc(&doc)?,
    });
    serde_json::to_string(&out).map_err(|e| LayoutError::new_err(e.to_string()))
}

#[pyfunction]
#[pyo3(signature = (doc_json, name, edge, target=None, closed=false))]
fn dock_widget(
    doc_json: &str,
    name: &str,
    edge: &str,
    target: Option<(usize, Vec<usize>)>,
    closed: bool,
) -> PyResult<String> {
    let mut doc = parse_doc(doc_json)?;
    lace_core::layout_ops::dock_widget(&mut doc, name, parse_edge(edge)?, target, closed)
        .map_err(layout_error)?;
    render_doc(&doc)
}

#[pyfunction]
fn move_widget(
    doc_json: &str,
    name: &str,
    edge: &str,
    container: usize,
    path: Vec<usize>,
) -> PyResult<String> {
    let mut doc = parse_doc(doc_json)?;
    lace_core::layout_ops::move_widget(&mut doc, name, parse_edge(edge)?, (container, path))
        .map_err(layout_error)?;
    render_doc(&doc)
}

#[pyfunction]
fn move_container_center(doc_json: &str, name: &str, container: usize) -> PyResult<String> {
    let mut doc = parse_doc(doc_json)?;
    lace_core::layout_ops::move_container_center(&mut doc, name, container)
        .map_err(layout_error)?;
    render_doc(&doc)
}

#[pyfunction]
fn drop_container_edge(
    doc_json: &str,
    name: &str,
    container: usize,
    edge: &str,
) -> PyResult<String> {
    let mut doc = parse_doc(doc_json)?;
    lace_core::layout_ops::drop_container_edge(&mut doc, name, container, parse_edge(edge)?)
        .map_err(layout_error)?;
    render_doc(&doc)
}

/// Returns `(new_doc_json, found)`.
#[pyfunction]
fn remove_widget(doc_json: &str, name: &str) -> PyResult<(String, bool)> {
    let mut doc = parse_doc(doc_json)?;
    let found = lace_core::layout_ops::remove_widget(&mut doc, name);
    Ok((render_doc(&doc)?, found))
}

/// Returns `(new_doc_json, found)`.
#[pyfunction]
fn set_closed(doc_json: &str, name: &str, closed: bool) -> PyResult<(String, bool)> {
    let mut doc = parse_doc(doc_json)?;
    let found = lace_core::layout_ops::set_closed(&mut doc, name, closed);
    Ok((render_doc(&doc)?, found))
}

#[pyfunction]
fn set_current(
    doc_json: &str,
    container: usize,
    path: Vec<usize>,
    name: &str,
) -> PyResult<String> {
    let mut doc = parse_doc(doc_json)?;
    lace_core::layout_ops::set_current(&mut doc, container, &path, name)
        .map_err(layout_error)?;
    render_doc(&doc)
}

/// Returns `(new_doc_json, container_id)`.
#[pyfunction]
fn float_widget(doc_json: &str, name: &str) -> PyResult<(String, String)> {
    let mut doc = parse_doc(doc_json)?;
    let id =
        lace_core::layout_ops::float_widget(&mut doc, name).map_err(layout_error)?;
    Ok((render_doc(&doc)?, id))
}

#[pyfunction]
fn dock_floating(doc_json: &str, container_id: &str) -> PyResult<String> {
    let mut doc = parse_doc(doc_json)?;
    lace_core::layout_ops::dock_floating(&mut doc, container_id).map_err(layout_error)?;
    render_doc(&doc)
}

#[pyfunction]
fn pin_widget(doc_json: &str, name: &str, area: &str) -> PyResult<String> {
    let mut doc = parse_doc(doc_json)?;
    lace_core::layout_ops::pin_widget(&mut doc, name, area).map_err(layout_error)?;
    render_doc(&doc)
}

#[pyfunction]
fn unpin_widget(doc_json: &str, name: &str) -> PyResult<String> {
    let mut doc = parse_doc(doc_json)?;
    lace_core::layout_ops::unpin_widget(&mut doc, name).map_err(layout_error)?;
    render_doc(&doc)
}

#[pyfunction]
fn drop_edges(doc_json: &str, container: usize) -> PyResult<Vec<String>> {
    let doc = parse_doc(doc_json)?;
    if container >= doc.containers.len() {
        return Err(InvalidFormatError::new_err(format!("no container {container}")));
    }
    Ok(lace_core::layout_ops::drop_edges(&doc, container)
        .iter()
        .map(|edge| {
            match edge {
                lace_core::layout_ops::DockEdge::Left => "left",
                lace_core::layout_ops::DockEdge::Right => "right",
                lace_core::layout_ops::DockEdge::Top => "top",
                lace_core::layout_ops::DockEdge::Bottom => "bottom",
                lace_core::layout_ops::DockEdge::Center => "center",
                lace_core::layout_ops::DockEdge::Float => "float",
            }
            .to_string()
        })
        .collect())
}

/// Returns `(new_doc_json, removed_ids)`.
#[pyfunction]
fn gc_empty_floats(doc_json: &str) -> PyResult<(String, Vec<String>)> {
    let mut doc = parse_doc(doc_json)?;
    let removed = lace_core::layout_ops::gc_empty_floats(&mut doc);
    Ok((render_doc(&doc)?, removed))
}

#[pymodule]
fn _lace_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(split_share, m)?)?;
    m.add_function(wrap_pyfunction!(allowed_areas, m)?)?;
    m.add_function(wrap_pyfunction!(available_themes, m)?)?;
    m.add_function(wrap_pyfunction!(theme_groups, m)?)?;
    m.add_function(wrap_pyfunction!(build_theme, m)?)?;
    m.add_function(wrap_pyfunction!(build_merged_theme, m)?)?;
    m.add_function(wrap_pyfunction!(load_theme_file, m)?)?;
    m.add_function(wrap_pyfunction!(blank_layout, m)?)?;
    m.add_function(wrap_pyfunction!(validate_layout, m)?)?;
    m.add_function(wrap_pyfunction!(dock_widget, m)?)?;
    m.add_function(wrap_pyfunction!(move_widget, m)?)?;
    m.add_function(wrap_pyfunction!(move_container_center, m)?)?;
    m.add_function(wrap_pyfunction!(drop_container_edge, m)?)?;
    m.add_function(wrap_pyfunction!(remove_widget, m)?)?;
    m.add_function(wrap_pyfunction!(set_closed, m)?)?;
    m.add_function(wrap_pyfunction!(set_current, m)?)?;
    m.add_function(wrap_pyfunction!(float_widget, m)?)?;
    m.add_function(wrap_pyfunction!(dock_floating, m)?)?;
    m.add_function(wrap_pyfunction!(pin_widget, m)?)?;
    m.add_function(wrap_pyfunction!(unpin_widget, m)?)?;
    m.add_function(wrap_pyfunction!(drop_edges, m)?)?;
    m.add_function(wrap_pyfunction!(gc_empty_floats, m)?)?;
    m.add("LayoutError", m.py().get_type::<LayoutError>())?;
    m.add("LayoutIOError", m.py().get_type::<LayoutIOError>())?;
    m.add("InvalidFormatError", m.py().get_type::<InvalidFormatError>())?;
    m.add("RestoreFailureError", m.py().get_type::<RestoreFailureError>())?;
    m.add("ValidationError", m.py().get_type::<ValidationError>())?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
