//! Phase-1 parity gate: every built theme must equal the Python oracle.
//!
//! Oracles live in `tests/fixtures/themes/` (see
//! `codegen/emit_goldens.py`): 27 `build_theme` outputs, the
//! `theme_groups()` presentation order, and the eight `get_all()` maps of
//! the style manager after applying `"default"` (schema defaults merged
//! under the engine output).

use std::collections::BTreeMap;

use lace_core::presets_generated::{THEME_GROUP_ORDER, default_spec, preset_keys, preset_specs};
use lace_core::style::{declared_fields, merged_defaults};
use lace_core::theme::{BuiltTheme, StyleCategory, build_theme, theme_groups};

fn fixture(name: &str) -> serde_json::Value {
    let path = format!(
        "{}/tests/fixtures/themes/{name}.json",
        env!("CARGO_MANIFEST_DIR")
    );
    let raw = std::fs::read_to_string(&path).unwrap_or_else(|e| panic!("{path}: {e}"));
    serde_json::from_str(&raw).expect("fixture must be valid JSON")
}

fn all_built() -> BTreeMap<String, BuiltTheme> {
    let mut built = BTreeMap::new();
    built.insert("default".to_string(), build_theme(&default_spec()));
    for (name, spec) in preset_specs() {
        built.insert(name.to_string(), build_theme(&spec));
    }
    built
}

#[test]
fn registry_covers_default_plus_26_specs() {
    assert_eq!(preset_keys().len(), 27);
    assert_eq!(preset_keys()[0], "default");
}

#[test]
fn all_27_themes_match_python_oracle() {
    let built = all_built();
    assert_eq!(built.len(), 27);
    for name in preset_keys() {
        let expected = fixture(name);
        let actual = serde_json::to_value(&built[name]).expect("theme serializes");
        assert_eq!(actual, expected, "theme `{name}` diverged from Python");
    }
}

#[test]
fn engine_emits_only_declared_tokens() {
    // Port of test_build_theme_emits_only_declared_tokens: an engine token
    // no schema declares would be a "ghost" — writable but unreadable.
    let by_name: std::collections::HashMap<&str, StyleCategory> = StyleCategory::ALL
        .iter()
        .map(|c| (c.name(), *c))
        .collect();
    let mut specs = preset_specs();
    specs.push(("__default__", default_spec()));
    for (name, spec) in &specs {
        let theme = build_theme(spec);
        for (category, tokens) in &theme {
            let declared: std::collections::HashSet<&str> = declared_fields(by_name[category.as_str()])
                .iter()
                .copied()
                .collect();
            let ghosts: Vec<&str> = tokens.keys().map(String::as_str).filter(|k| !declared.contains(k)).collect();
            assert!(ghosts.is_empty(), "{name}.{category} emits undeclared tokens: {ghosts:?}");
        }
    }
}

#[test]
fn groups_match_python_presentation_order() {
    let expected = fixture("_groups");
    let keys = preset_keys();
    let actual = serde_json::to_value(theme_groups(THEME_GROUP_ORDER, &keys)).expect("groups serialize");
    assert_eq!(actual, expected);
}

#[test]
fn resolved_default_matches_manager_oracle() {
    let merged = merged_defaults();
    for category in [
        "core", "panel", "tab", "title_bar", "sidebar", "sidepanel", "splitter", "overlay",
    ] {
        let expected = fixture(&format!("_resolved_default_{category}"));
        let actual =
            serde_json::to_value(&merged[category]).expect("category serializes");
        assert_eq!(actual, expected, "resolved `{category}` diverged from get_all()");
    }
}
