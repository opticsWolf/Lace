//! Port of `tests/test_theme_json.py`: validated JSON theme loading.
//!
//! The valid payload mirrors `VALID_THEME` (hex + RGBA colours, an unknown
//! key, every override family); failures mirror the parametrized cases.

use lace_core::theme::ThemeValue;
use lace_core::theme_json::{ThemeError, ThemeJson, load_theme_json};

const VALID_THEME: &str = r##"{
    "name": "PytestTheme",
    "base": [14, 11, 28, 255],
    "accent": "#ff007f",
    "text": [245, 245, 255, 255],
    "surface": [24, 19, 44, 255],
    "focus_border_color": "#00f0ff",
    "tooltip_bg": "#1b2430",
    "tooltip_text": [225, 230, 240, 255],
    "title_mode": "darker",
    "hover_mode": "lighter",
    "corner_radius": 10,
    "border_width": 1.5,
    "title_height": 32,
    "tab_radius": 8,
    "content_margin": [8, 2],
    "indicator_width": 2.0,
    "indicator_position": "bottom",
    "tab_dimming": true,
    "future_unknown_key": "ignored"
}"##;

fn write_theme(dir: &std::path::Path, payload: &str) -> std::path::PathBuf {
    let path = dir.join("theme.json");
    std::fs::write(&path, payload).unwrap();
    path
}

#[test]
fn load_valid_json_theme() {
    let dir = std::env::temp_dir().join("lace_theme_json_valid");
    std::fs::create_dir_all(&dir).unwrap();
    let theme = ThemeJson::load(write_theme(&dir, VALID_THEME)).unwrap();
    assert_eq!(theme.name.as_deref(), Some("PytestTheme"));
    assert_eq!(theme.corner_radius, Some(10));
}

#[test]
fn unknown_keys_are_ignored() {
    let dir = std::env::temp_dir().join("lace_theme_json_unknown");
    std::fs::create_dir_all(&dir).unwrap();
    let theme = ThemeJson::load(write_theme(&dir, VALID_THEME)).unwrap();
    let dumped = serde_json::to_value(&theme).unwrap();
    assert!(dumped.get("future_unknown_key").is_none());
}

#[test]
fn build_theme_dict_covers_all_categories() {
    let dir = std::env::temp_dir().join("lace_theme_json_cats");
    std::fs::create_dir_all(&dir).unwrap();
    let theme_dict = ThemeJson::load(write_theme(&dir, VALID_THEME)).unwrap().build_theme_dict();
    let mut cats: Vec<&str> = theme_dict.keys().map(String::as_str).collect();
    cats.sort_unstable();
    assert_eq!(
        cats,
        vec!["core", "overlay", "panel", "sidebar", "sidepanel", "splitter", "tab", "title_bar"]
    );
}

#[test]
fn hex_colors_resolve_to_rgba() {
    let dir = std::env::temp_dir().join("lace_theme_json_hex");
    std::fs::create_dir_all(&dir).unwrap();
    let theme_dict = load_theme_json(write_theme(&dir, VALID_THEME)).unwrap();
    let core = &theme_dict["core"];
    assert_eq!(core["accent_color"], ThemeValue::Color(lace_core::theme::Rgba::new(255, 0, 127, 255)));
    assert_eq!(
        core["focus_border_color"],
        ThemeValue::Color(lace_core::theme::Rgba::new(0, 240, 255, 255))
    );
    assert_eq!(
        core["tooltip_bg"],
        ThemeValue::Color(lace_core::theme::Rgba::new(27, 36, 48, 255))
    );
    assert_eq!(
        core["tooltip_text"],
        ThemeValue::Color(lace_core::theme::Rgba::new(225, 230, 240, 255))
    );
}

#[test]
fn content_margin_list_loads_as_floats() {
    // Pydantic coerces `[8, 2]` to `[8.0, 2.0]`; the Rust loader agrees.
    let dir = std::env::temp_dir().join("lace_theme_json_margin");
    std::fs::create_dir_all(&dir).unwrap();
    let theme_dict = load_theme_json(write_theme(&dir, VALID_THEME)).unwrap();
    assert_eq!(
        theme_dict["panel"]["content_margin"],
        ThemeValue::NumList(vec![
            lace_core::theme::Num::Float(8.0),
            lace_core::theme::Num::Float(2.0)
        ])
    );
}

#[test]
fn invalid_payloads_raise_validation() {
    let dir = std::env::temp_dir().join("lace_theme_json_bad");
    std::fs::create_dir_all(&dir).unwrap();
    let cases = [
        VALID_THEME.replace("[14, 11, 28, 255]", "[300, 0, 0]"),
        VALID_THEME.replace("[245, 245, 255, 255]", "true"),
        VALID_THEME.replace("[245, 245, 255, 255]", "[1, 2, 3, 4, 5]"),
        VALID_THEME.replace("[245, 245, 255, 255]", "{\"r\": 1}"),
        VALID_THEME.replace("\"accent\": \"#ff007f\",\n    ", ""),
    ];
    for (i, payload) in cases.iter().enumerate() {
        let path = dir.join(format!("bad{i}.json"));
        std::fs::write(&path, payload).unwrap();
        match ThemeJson::load(&path) {
            Err(ThemeError::Validation(_)) => {}
            other => panic!("case {i}: expected Validation, got {other:?}"),
        }
    }
}

#[test]
fn malformed_json_raises_json_error() {
    let dir = std::env::temp_dir().join("lace_theme_json_malformed");
    std::fs::create_dir_all(&dir).unwrap();
    let path = dir.join("bad_syntax.json");
    std::fs::write(&path, "{ \"base\": [1, 2, 3] ").unwrap();
    match ThemeJson::load(&path) {
        Err(ThemeError::Json(_)) => {}
        other => panic!("expected Json, got {other:?}"),
    }
}

#[test]
fn missing_file_raises_io_error() {
    let dir = std::env::temp_dir().join("lace_theme_json_missing");
    std::fs::create_dir_all(&dir).unwrap();
    match ThemeJson::load(dir.join("nope.json")) {
        Err(ThemeError::Io(_)) => {}
        other => panic!("expected Io, got {other:?}"),
    }
}
