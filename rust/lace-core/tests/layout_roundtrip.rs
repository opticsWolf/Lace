//! Phase-2 parity gate: real 0.7.x layouts validate, round-trip stably,
//! and corrupt ones fail with the documented error variant.
//!
//! Fixtures in `tests/fixtures/layouts/` come from
//! `codegen/emit_layouts.py` (positive scenarios built by a real
//! `DockManager` headless; negatives mutated by hand).

use std::collections::HashSet;

use lace_core::error::LaceError;
use lace_core::layout_doc::{LayoutDoc, validate_doc};
use lace_core::persist::PersistDir;

const POSITIVE: &[&str] = &["docked_tabs", "closed", "locked", "floating", "sidebar"];

fn fixture(name: &str) -> String {
    let path = format!(
        "{}/tests/fixtures/layouts/{name}.json",
        env!("CARGO_MANIFEST_DIR")
    );
    std::fs::read_to_string(&path).unwrap_or_else(|e| panic!("{path}: {e}"))
}

fn roster_of(doc: &LayoutDoc) -> HashSet<String> {
    doc.widget_states.keys().cloned().collect()
}

fn expect_format(name: &str) {
    match LayoutDoc::parse(&fixture(name)) {
        Err(LaceError::InvalidFormat(_)) => {}
        other => panic!("{name}: expected InvalidFormat, got {other:?}"),
    }
}

fn expect_restore_failure(name: &str) {
    let mut doc = LayoutDoc::parse(&fixture(name)).expect("must parse");
    let roster = roster_of(&doc);
    match validate_doc(&mut doc, 0, &roster) {
        Err(LaceError::RestoreFailure(_)) => {}
        other => panic!("{name}: expected RestoreFailure, got {other:?}"),
    }
}

#[test]
fn shipped_layouts_validate_clean() {
    for name in POSITIVE {
        let mut doc = LayoutDoc::parse(&fixture(name)).expect("must parse");
        assert_eq!(doc.system_type, "LaceDockingSystem", "{name}");
        assert_eq!(doc.schema, 1, "{name}");
        let roster = roster_of(&doc);
        let report = validate_doc(&mut doc, 0, &roster).expect("must validate");
        assert!(report.warnings.is_empty(), "{name}: {report:?}");
        assert!(report.pruned_widgets.is_empty(), "{name}");
    }
}

#[test]
fn save_restore_save_is_stable() {
    // The plan's exit gate: a validated document re-renders to an
    // equivalent document, formatted or compact.
    for name in POSITIVE {
        let mut doc = LayoutDoc::parse(&fixture(name)).expect("must parse");
        let roster = roster_of(&doc);
        validate_doc(&mut doc, 0, &roster).expect("must validate");
        let before = serde_json::to_value(&doc).unwrap();
        for formatted in [false, true] {
            let rendered = doc.render(formatted).unwrap();
            let after: serde_json::Value = serde_json::from_str(&rendered).unwrap();
            assert_eq!(after, before, "{name} (formatted={formatted}) drifted");
        }
    }
}

#[test]
fn legacy_layouts_warn_but_validate() {
    let mut doc = LayoutDoc::parse(&fixture("legacy")).expect("must parse");
    assert_eq!(doc.schema, 0);
    let roster = roster_of(&doc);
    let report = validate_doc(&mut doc, 0, &roster).expect("legacy must validate");
    assert_eq!(report.warnings.len(), 1);
    assert!(report.warnings[0].contains("schema v0"));
}

#[test]
fn corrupt_payloads_are_format_errors() {
    for name in [
        "wrong_type",
        "future_schema",
        "version_mismatch",
        "missing_keys",
        "bad_geometry_zero",
        "bad_geometry_huge",
        "bad_geometry_type",
    ] {
        // wrong_type / missing_keys fail at parse; the rest validate.
        match LayoutDoc::parse(&fixture(name)) {
            Err(LaceError::InvalidFormat(_)) => continue,
            Ok(mut doc) => {
                let roster = roster_of(&doc);
                match validate_doc(&mut doc, 0, &roster) {
                    Err(LaceError::InvalidFormat(_)) => {}
                    other => panic!("{name}: expected InvalidFormat, got {other:?}"),
                }
            }
            Err(other) => panic!("{name}: expected InvalidFormat, got {other:?}"),
        }
    }
    expect_format("wrong_type");
}

#[test]
fn structurally_broken_trees_are_restore_failures() {
    // The live layout must be left untouched: validation refuses before any
    // mutation, so these never get past `validate_doc`.
    expect_restore_failure("sizes_mismatch");
    expect_restore_failure("unnamed_widget");
}

#[test]
fn dropped_widgets_are_pruned_not_fatal() {
    let mut doc = LayoutDoc::parse(&fixture("docked_tabs")).expect("must parse");
    let mut roster = roster_of(&doc);
    assert!(roster.remove("Gamma"));
    let report = validate_doc(&mut doc, 0, &roster).expect("must validate");
    assert_eq!(report.pruned_widgets, vec!["Gamma".to_string()]);
    assert_eq!(report.warnings.len(), 1);
    assert!(!doc.widget_states.contains_key("Gamma"));
}

#[test]
fn golden_layout_survives_atomic_storage() {
    let dir = std::env::temp_dir()
        .join("lace_layout_golden")
        .join(std::process::id().to_string());
    let _ = std::fs::remove_dir_all(&dir);
    let persist = PersistDir::new(&dir);
    let mut doc = LayoutDoc::parse(&fixture("floating")).expect("must parse");
    let roster = roster_of(&doc);
    validate_doc(&mut doc, 0, &roster).expect("must validate");
    persist.save_layout("session", &doc, true).unwrap();
    let back = persist.load_layout("session").unwrap();
    assert_eq!(back, doc);
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn layout_error_variants_are_distinct() {
    // Port of test_layout_exceptions: the hierarchy stays disjoint and
    // messages survive.
    let format = LaceError::InvalidFormat("bad json".into());
    let failure = LaceError::RestoreFailure("missing widget".into());
    let io = LaceError::LayoutIo("disk full".into());
    assert!(matches!(format, LaceError::InvalidFormat(_)));
    assert!(matches!(failure, LaceError::RestoreFailure(_)));
    assert!(matches!(io, LaceError::LayoutIo(_)));
    assert_eq!(format.to_string(), "invalid layout format: bad json");
    assert_eq!(failure.to_string(), "layout restore failed: missing widget");
    assert_eq!(io.to_string(), "layout storage error: disk full");
}
