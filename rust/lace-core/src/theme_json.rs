//! `lace-core::theme_json`: validated JSON theme files.
//!
//! Ports `lace/theme_models.py` (`ThemeJson`, `load_theme_json`). A JSON file
//! mirrors the declarative [`ThemeSpec`] format; colours are `[r,g,b(,a)]`
//! lists or `"#rrggbb"` / SVG-name strings resolved exactly like Qt's
//! `QColor` (including its `#aarrggbb` order and its silent black for
//! unknown names). Unknown keys are ignored so future metadata embeds safely.
//!
//! Error correspondence with Python: malformed JSON -> [`ThemeError::Json`]
//! (`json.JSONDecodeError`); any schema violation -> [`ThemeError::Validation`]
//! (`pydantic.ValidationError`); missing file -> [`ThemeError::Io`].

use std::path::Path;

use serde::{Deserialize, Deserializer, Serialize};
use thiserror::Error;

use crate::svg_colors_generated::svg_color;
use crate::theme::{IndicatorPosition, MarginSpec, Num, Rgba, ThemeSpec, ThemeValue, build_theme,
    BuiltTheme};

#[derive(Debug, Error)]
pub enum ThemeError {
    #[error("cannot read theme file: {0}")]
    Io(#[from] std::io::Error),
    #[error("malformed theme JSON: {0}")]
    Json(#[from] serde_json::Error),
    #[error("invalid theme: {0}")]
    Validation(String),
}

/// A colour as written in a theme file: hex/name string or channel list.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub enum ColorJson {
    Str(String),
    Rgba(Vec<u8>),
}

impl<'de> Deserialize<'de> for ColorJson {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        use serde::de::Error;
        let value = serde_json::Value::deserialize(deserializer)?;
        match value {
            serde_json::Value::String(s) => Ok(ColorJson::Str(s)),
            serde_json::Value::Array(items) => {
                if items.len() != 3 && items.len() != 4 {
                    return Err(D::Error::custom(format!(
                        "colour must have 3 or 4 channels [r, g, b(, a)], got {}",
                        items.len()
                    )));
                }
                let mut out = Vec::with_capacity(items.len());
                for item in &items {
                    match item.as_u64() {
                        Some(ch) if ch <= 255 => out.push(ch as u8),
                        _ => {
                            return Err(D::Error::custom(format!(
                                "colour channel must be an int in 0..255, got {item}"
                            )));
                        }
                    }
                }
                Ok(ColorJson::Rgba(out))
            }
            other => Err(D::Error::custom(format!(
                "colour must be a hex string or [r, g, b(, a)] list, got {other}"
            ))),
        }
    }
}

fn hex_nibble(c: char) -> Option<u8> {
    c.to_digit(16).map(|v| v as u8)
}

/// Resolve `#rgb` / `#rrggbb` / `#aarrggbb` (Qt order: alpha first).
fn parse_hex(s: &str) -> Option<Rgba> {
    let hex = s.strip_prefix('#')?;
    let d: Vec<u8> = hex.chars().map(hex_nibble).collect::<Option<Vec<_>>>()?;
    match d.len() {
        3 => Some(Rgba::new(d[0] * 17, d[1] * 17, d[2] * 17, 255)),
        6 => Some(Rgba::new(d[0] * 16 + d[1], d[2] * 16 + d[3], d[4] * 16 + d[5], 255)),
        8 => Some(Rgba::new(
            d[2] * 16 + d[3],
            d[4] * 16 + d[5],
            d[6] * 16 + d[7],
            d[0] * 16 + d[1],
        )),
        _ => None,
    }
}

impl ColorJson {
    /// Resolve to RGBA exactly like `qcolor_to_list(to_qcolor(col))`:
    /// 3-channel lists gain opaque alpha; unknown names become black
    /// (what an invalid `QColor` reports).
    pub fn resolve(&self) -> Rgba {
        match self {
            ColorJson::Rgba(ch) => match ch.as_slice() {
                [r, g, b] => Rgba::new(*r, *g, *b, 255),
                [r, g, b, a] => Rgba::new(*r, *g, *b, *a),
                _ => Rgba::new(0, 0, 0, 255),
            },
            ColorJson::Str(s) => {
                if s.starts_with('#') {
                    parse_hex(s).unwrap_or(Rgba::new(0, 0, 0, 255))
                } else {
                    svg_color(s).unwrap_or(Rgba::new(0, 0, 0, 255))
                }
            }
        }
    }
}

/// `content_margin` as written in JSON: scalar or list (pydantic coerces list
/// items to float, so `[8, 2]` loads as `[8.0, 2.0]`).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum MarginJson {
    Scalar(Num),
    List(Vec<f64>),
}

impl MarginJson {
    fn into_spec(self) -> MarginSpec {
        match self {
            MarginJson::Scalar(n) => MarginSpec::Scalar(n),
            MarginJson::List(items) => {
                MarginSpec::List(items.into_iter().map(Num::Float).collect())
            }
        }
    }
}

/// `indicator_position` as written in JSON: one edge or one per edge.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum IndicatorJson {
    Single(String),
    Multiple(Vec<String>),
}

impl IndicatorJson {
    fn into_spec(self) -> IndicatorPosition {
        match self {
            IndicatorJson::Single(s) => IndicatorPosition::Single(s),
            IndicatorJson::Multiple(items) => IndicatorPosition::Multiple(items),
        }
    }
}

/// Validated JSON representation of a declarative theme.
/// Field names and defaults match [`ThemeSpec`]; unknown keys are ignored.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ThemeJson {
    pub name: Option<String>,
    pub base: ColorJson,
    pub accent: ColorJson,
    pub text: ColorJson,
    pub surface: Option<ColorJson>,
    pub title_bg: Option<ColorJson>,
    pub border: Option<ColorJson>,
    pub focus_border_color: Option<ColorJson>,
    #[serde(default)]
    pub is_light: bool,
    #[serde(default = "default_title_mode")]
    pub title_mode: String,
    #[serde(default = "default_hover_mode")]
    pub hover_mode: String,
    pub success_color: Option<ColorJson>,
    pub warning_color: Option<ColorJson>,
    pub error_color: Option<ColorJson>,
    pub info_color: Option<ColorJson>,
    pub tooltip_bg: Option<ColorJson>,
    pub tooltip_text: Option<ColorJson>,
    pub corner_radius: Option<i64>,
    pub border_width: Option<f64>,
    pub title_height: Option<i64>,
    pub title_padding_left: Option<i64>,
    pub title_padding_right: Option<i64>,
    pub title_button_spacing: Option<i64>,
    pub title_margin: Option<i64>,
    pub title_border_width: Option<f64>,
    pub title_border_bottom: Option<f64>,
    pub title_border_color: Option<ColorJson>,
    pub tab_radius: Option<i64>,
    pub tab_margin: Option<i64>,
    pub border_below_title: Option<bool>,
    pub tab_border_width: Option<f64>,
    pub tab_border_color: Option<ColorJson>,
    pub tab_border_active_color: Option<ColorJson>,
    pub tab_border_unfocused_color: Option<ColorJson>,
    pub content_margin: Option<MarginJson>,
    #[serde(default)]
    pub tab_dimming: bool,
    pub indicator_width: Option<f64>,
    pub indicator_position: Option<IndicatorJson>,
    pub sidebar_tab_flat_edge: Option<String>,
    pub sidebar_tab_radius: Option<i64>,
    pub sidebar_tab_bg_normal: Option<ColorJson>,
    pub sidebar_tab_bg_hover_start: Option<ColorJson>,
    pub sidebar_tab_bg_hover_end: Option<ColorJson>,
    pub sidebar_tab_bg_active: Option<ColorJson>,
    pub sidebar_tab_border_width: Option<f64>,
    pub sidebar_tab_border_color: Option<ColorJson>,
    pub sidebar_tab_border_active_color: Option<ColorJson>,
    pub sidebar_tab_border_hover_color: Option<ColorJson>,
    pub sidebar_tab_border_closed: Option<bool>,
    pub sidebar_indicator_width: Option<f64>,
    pub sidebar_indicator_position: Option<String>,
}

fn default_title_mode() -> String {
    "darker".to_string()
}

fn default_hover_mode() -> String {
    "lighter".to_string()
}

impl ThemeJson {
    /// Parse and validate a JSON theme file.
    pub fn load(path: impl AsRef<Path>) -> Result<Self, ThemeError> {
        let raw = std::fs::read_to_string(path.as_ref())?;
        let value: serde_json::Value = serde_json::from_str(&raw)?;
        serde_json::from_value(value).map_err(|e| ThemeError::Validation(e.to_string()))
    }

    /// Convert into a [`ThemeSpec`], resolving every colour.
    pub fn to_theme_spec(&self) -> ThemeSpec {
        let rgba = |c: &Option<ColorJson>| c.as_ref().map(ColorJson::resolve);
        ThemeSpec {
            base: self.base.resolve(),
            accent: self.accent.resolve(),
            text: self.text.resolve(),
            surface: rgba(&self.surface),
            title_bg: rgba(&self.title_bg),
            border: rgba(&self.border),
            focus_border_color: rgba(&self.focus_border_color),
            is_light: self.is_light,
            title_mode: self.title_mode.clone(),
            hover_mode: self.hover_mode.clone(),
            success_color: rgba(&self.success_color),
            warning_color: rgba(&self.warning_color),
            error_color: rgba(&self.error_color),
            info_color: rgba(&self.info_color),
            tooltip_bg: rgba(&self.tooltip_bg),
            tooltip_text: rgba(&self.tooltip_text),
            corner_radius: self.corner_radius.map(Num::Int),
            border_width: self.border_width.map(Num::Float),
            title_height: self.title_height.map(Num::Int),
            title_padding_left: self.title_padding_left.map(Num::Int),
            title_padding_right: self.title_padding_right.map(Num::Int),
            title_button_spacing: self.title_button_spacing.map(Num::Int),
            title_margin: self.title_margin.map(Num::Int),
            title_border_width: self.title_border_width.map(Num::Float),
            title_border_bottom: self.title_border_bottom.map(Num::Float),
            title_border_color: rgba(&self.title_border_color),
            title_border_focus_color: None,
            border_below_title: self.border_below_title,
            tab_radius: self.tab_radius.map(Num::Int),
            tab_margin: self.tab_margin.map(Num::Int),
            tab_border_width: self.tab_border_width.map(Num::Float),
            tab_border_color: rgba(&self.tab_border_color),
            tab_border_active_color: rgba(&self.tab_border_active_color),
            tab_border_unfocused_color: rgba(&self.tab_border_unfocused_color),
            content_margin: self.content_margin.clone().map(MarginJson::into_spec),
            tab_dimming: self.tab_dimming,
            indicator_width: self.indicator_width.map(Num::Float),
            indicator_position: self
                .indicator_position
                .clone()
                .map(IndicatorJson::into_spec),
            sidebar_tab_flat_edge: self.sidebar_tab_flat_edge.clone(),
            sidebar_tab_radius: self.sidebar_tab_radius.map(Num::Int),
            sidebar_tab_bg_normal: rgba(&self.sidebar_tab_bg_normal),
            sidebar_tab_bg_hover_start: rgba(&self.sidebar_tab_bg_hover_start),
            sidebar_tab_bg_hover_end: rgba(&self.sidebar_tab_bg_hover_end),
            sidebar_tab_bg_active: rgba(&self.sidebar_tab_bg_active),
            sidebar_tab_border_width: self.sidebar_tab_border_width.map(Num::Float),
            sidebar_tab_border_color: rgba(&self.sidebar_tab_border_color),
            sidebar_tab_border_active_color: rgba(&self.sidebar_tab_border_active_color),
            sidebar_tab_border_hover_color: rgba(&self.sidebar_tab_border_hover_color),
            sidebar_tab_border_closed: self.sidebar_tab_border_closed,
            sidebar_indicator_width: self.sidebar_indicator_width.map(Num::Float),
            sidebar_indicator_position: self.sidebar_indicator_position.clone(),
        }
    }

    /// Derive the full theme token dict, like a `DOCK_THEMES` entry.
    pub fn build_theme_dict(&self) -> BuiltTheme {
        build_theme(&self.to_theme_spec())
    }
}

/// One-shot helper: load a JSON theme file and derive the full theme dict.
pub fn load_theme_json(path: impl AsRef<Path>) -> Result<BuiltTheme, ThemeError> {
    Ok(ThemeJson::load(path)?.build_theme_dict())
}

/// Read one token, mirroring `DockStyleManager.get` (default on missing).
pub fn get_token<'a>(theme: &'a BuiltTheme, category: &str, key: &str) -> Option<&'a ThemeValue> {
    theme.get(category)?.get(key)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hex_forms_resolve_like_qcolor() {
        assert_eq!(parse_hex("#ff007f"), Some(Rgba::new(255, 0, 127, 255)));
        assert_eq!(parse_hex("#f07"), Some(Rgba::new(255, 0, 119, 255)));
        // Qt order: #aarrggbb.
        assert_eq!(
            parse_hex("#80112233"),
            Some(Rgba::new(0x11, 0x22, 0x33, 0x80))
        );
        assert_eq!(parse_hex("#1b2430"), Some(Rgba::new(27, 36, 48, 255)));
        assert_eq!(parse_hex("nope"), None);
    }

    #[test]
    fn unknown_names_become_black_like_invalid_qcolor() {
        assert_eq!(
            ColorJson::Str("not-a-colour".to_string()).resolve(),
            Rgba::new(0, 0, 0, 255)
        );
        assert_eq!(
            ColorJson::Str("red".to_string()).resolve(),
            Rgba::new(255, 0, 0, 255)
        );
    }

    #[test]
    fn three_channel_lists_gain_opaque_alpha() {
        assert_eq!(
            ColorJson::Rgba(vec![10, 20, 30]).resolve(),
            Rgba::new(10, 20, 30, 255)
        );
    }
}
