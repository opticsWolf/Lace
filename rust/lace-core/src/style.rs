//! `lace-core::style`: schema defaults merged under a built theme.
//!
//! Mirrors what `DockStyleManager` holds after `apply_theme("default")`:
//! every schema field at its declared default, overlaid with the
//! `BASE_DOCK_DEFAULTS` engine output. The full stateful manager (signals,
//! subscribers, `update`) stays Python-side until Phase 6; this pure merge
//! is what QML and the bindings will read through.

use crate::presets_generated::{default_spec, preset_specs};
use crate::schema_generated::{schema_default, schema_fields};
use crate::theme::{BuiltTheme, CategoryTheme, StyleCategory, ThemeValue, build_theme};

/// Every declared token of every category: schema default, or [`ThemeValue::Null`]
/// when unset, overlaid with the stock-look engine output.
pub fn merged_defaults() -> BuiltTheme {
    merged_with(&build_theme(&default_spec()))
}

/// Schema defaults overlaid with one built theme (what `get_all()` reports
/// after applying any preset — engine tokens win, the rest are schema
/// defaults, unset colours are [`ThemeValue::Null`]).
pub fn merged_with(engine: &BuiltTheme) -> BuiltTheme {
    let mut merged = BuiltTheme::new();
    for category in StyleCategory::ALL {
        let mut tokens = CategoryTheme::new();
        for field in schema_fields(category) {
            tokens.insert(
                field.to_string(),
                schema_default(category, field).unwrap_or(ThemeValue::Null),
            );
        }
        merged.insert(category.name().to_string(), tokens);
    }
    let base = engine.clone();
    for (category, tokens) in base {
        let entry = merged
            .get_mut(&category)
            .expect("engine categories are schema categories");
        for (key, value) in tokens {
            entry.insert(key, value);
        }
    }
    merged
}

/// Render the merged theme for a preset name as compact JSON
/// (`"default"` selects the stock look). Err on unknown names.
pub fn render_merged_theme(name: &str) -> Result<String, String> {
    let spec = if name == "default" {
        Some(default_spec())
    } else {
        preset_specs().into_iter().find(|(key, _)| *key == name).map(|(_, spec)| spec)
    };
    match spec {
        Some(spec) => {
            let merged = merged_with(&build_theme(&spec));
            serde_json::to_string(&merged).map_err(|e| e.to_string())
        }
        None => Err(format!("unknown theme `{name}`")),
    }
}

/// Read one token, mirroring `DockStyleManager.get` (default on missing).
pub fn get_token<'a>(
    theme: &'a BuiltTheme,
    category: StyleCategory,
    key: &str,
) -> Option<&'a ThemeValue> {
    theme.get(category.name())?.get(key)
}

/// All declared fields of a category — the ghost-token contract's oracle.
pub fn declared_fields(category: StyleCategory) -> &'static [&'static str] {
    schema_fields(category)
}
