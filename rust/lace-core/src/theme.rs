//! `lace-core::theme`: the Qt-free theme engine.
//!
//! Ports `lace/dock_theme.py` (`ThemeSpec`, `build_theme`, the HLS colour
//! maths) without any Qt dependency — colours are plain `[u8; 4]` RGBA, so
//! both the QML front-end and the Python bindings share one implementation.
//! Qt-specific layers (`QPalette` construction, `QColor` coercion, the style
//! manager) stay on their respective sides until Phase 6.
//!
//! Float discipline: every float operation mirrors CPython's `colorsys`
//! evaluation order on IEEE-754 doubles, and `%` on floats is always
//! `rem_euclid` (Python `%` takes the divisor's sign; Rust `%` takes the
//! dividend's). Rounding is round-half-to-even (`f64::round_ties_even`),
//! matching CPython's `round()`.

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

// ---------------------------------------------------------------------------
// Value model
// ---------------------------------------------------------------------------

/// An `[r, g, b, a]` colour. Serializes as a 4-element JSON array.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct Rgba(pub [u8; 4]);

impl Rgba {
    pub const fn new(r: u8, g: u8, b: u8, a: u8) -> Self {
        Rgba([r, g, b, a])
    }

    pub fn channels(&self) -> &[u8] {
        &self.0
    }
}

/// A JSON number that preserves int-ness: `0` serializes as `0`,
/// `0.0` as `0.0`, exactly like the Python theme dicts.
#[derive(Debug, Clone, Copy, PartialEq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum Num {
    Int(i64),
    Float(f64),
}

impl From<i64> for Num {
    fn from(v: i64) -> Self {
        Num::Int(v)
    }
}

impl From<f64> for Num {
    fn from(v: f64) -> Self {
        Num::Float(v)
    }
}

/// One token value in a built theme.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum ThemeValue {
    Bool(bool),
    Num(Num),
    Str(String),
    Color(Rgba),
    StrList(Vec<String>),
    NumList(Vec<Num>),
    /// An unset token (schema default `None`), as `get_all()` reports it.
    Null,
}

impl From<bool> for ThemeValue {
    fn from(v: bool) -> Self {
        ThemeValue::Bool(v)
    }
}

impl From<Num> for ThemeValue {
    fn from(v: Num) -> Self {
        ThemeValue::Num(v)
    }
}

impl From<Rgba> for ThemeValue {
    fn from(v: Rgba) -> Self {
        ThemeValue::Color(v)
    }
}

impl From<String> for ThemeValue {
    fn from(v: String) -> Self {
        ThemeValue::Str(v)
    }
}

impl From<&str> for ThemeValue {
    fn from(v: &str) -> Self {
        ThemeValue::Str(v.to_string())
    }
}

/// `content_margin`: a scalar, or a 2-/3-/4-sided list.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum MarginSpec {
    Scalar(Num),
    List(Vec<Num>),
}

/// `indicator_position`: a single edge, or one per edge.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(untagged)]
pub enum IndicatorPosition {
    Single(String),
    Multiple(Vec<String>),
}

/// The eight style namespaces. Key names match
/// `DockStyleCategory.name.lower()` from `lace/dock_theme.py`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum StyleCategory {
    Core,
    Panel,
    Tab,
    TitleBar,
    Sidebar,
    SidePanel,
    Splitter,
    Overlay,
}

impl StyleCategory {
    pub const ALL: [StyleCategory; 8] = [
        StyleCategory::Core,
        StyleCategory::Panel,
        StyleCategory::Tab,
        StyleCategory::TitleBar,
        StyleCategory::Sidebar,
        StyleCategory::SidePanel,
        StyleCategory::Splitter,
        StyleCategory::Overlay,
    ];

    pub fn name(&self) -> &'static str {
        match self {
            StyleCategory::Core => "core",
            StyleCategory::Panel => "panel",
            StyleCategory::Tab => "tab",
            StyleCategory::TitleBar => "title_bar",
            StyleCategory::Sidebar => "sidebar",
            StyleCategory::SidePanel => "sidepanel",
            StyleCategory::Splitter => "splitter",
            StyleCategory::Overlay => "overlay",
        }
    }
}

/// One category namespace: token name -> value, sorted for deterministic JSON.
pub type CategoryTheme = BTreeMap<String, ThemeValue>;

/// A fully derived theme: category name -> tokens.
pub type BuiltTheme = BTreeMap<String, CategoryTheme>;

// ---------------------------------------------------------------------------
// Colour maths (exact port of colorsys + _adjust_color / _blend_rgba)
// ---------------------------------------------------------------------------

/// Banker's rounding: CPython `round(x)` rounds half to even.
fn py_round(x: f64) -> i64 {
    x.round_ties_even() as i64
}

/// Exact port of `colorsys.rgb_to_hls` (inputs/outputs in 0..1).
pub fn rgb_to_hls(r: f64, g: f64, b: f64) -> (f64, f64, f64) {
    let maxc = r.max(g).max(b);
    let minc = r.min(g).min(b);
    let l = (minc + maxc) / 2.0;
    if minc == maxc {
        return (0.0, l, 0.0);
    }
    let s = if l <= 0.5 {
        (maxc - minc) / (maxc + minc)
    } else {
        (maxc - minc) / (2.0 - maxc - minc)
    };
    let rc = (maxc - r) / (maxc - minc);
    let gc = (maxc - g) / (maxc - minc);
    let bc = (maxc - b) / (maxc - minc);
    let h = if r == maxc {
        bc - gc
    } else if g == maxc {
        2.0 + rc - bc
    } else {
        4.0 + gc - rc
    };
    ((h / 6.0).rem_euclid(1.0), l, s)
}

fn hls_v(m1: f64, m2: f64, hue: f64) -> f64 {
    let hue = hue.rem_euclid(1.0);
    if hue < 1.0 / 6.0 {
        m1 + (m2 - m1) * hue * 6.0
    } else if hue < 0.5 {
        m2
    } else if hue < 2.0 / 3.0 {
        m1 + (m2 - m1) * (2.0 / 3.0 - hue) * 6.0
    } else {
        m1
    }
}

/// Exact port of `colorsys.hls_to_rgb` (inputs/outputs in 0..1).
pub fn hls_to_rgb(h: f64, l: f64, s: f64) -> (f64, f64, f64) {
    if s == 0.0 {
        return (l, l, l);
    }
    let m2 = if l <= 0.5 {
        l * (1.0 + s)
    } else {
        l + s - l * s
    };
    let m1 = 2.0 * l - m2;
    (
        hls_v(m1, m2, h + 1.0 / 3.0),
        hls_v(m1, m2, h),
        hls_v(m1, m2, h - 1.0 / 3.0),
    )
}

/// Port of `_adjust_color`: shift HLS (and alpha) of an `[r,g,b(,a)]` colour.
/// Alpha passes through untouched when the input has none.
pub fn adjust_color(col: &[u8], l_off: f64, s_off: f64, h_off: f64, a_off: f64) -> Vec<u8> {
    let rgba: Vec<f64> = col.iter().map(|&x| f64::from(x) / 255.0).collect();
    let (h, l, s) = rgb_to_hls(rgba[0], rgba[1], rgba[2]);
    let h = (h + h_off).rem_euclid(1.0);
    let l = (l + l_off).clamp(0.0, 1.0);
    let s = (s + s_off).clamp(0.0, 1.0);
    let (nr, ng, nb) = hls_to_rgb(h, l, s);
    let mut out = vec![
        py_round(nr * 255.0).clamp(0, 255) as u8,
        py_round(ng * 255.0).clamp(0, 255) as u8,
        py_round(nb * 255.0).clamp(0, 255) as u8,
    ];
    if rgba.len() > 3 {
        out.push(py_round((rgba[3] + a_off).clamp(0.0, 1.0) * 255.0).clamp(0, 255) as u8);
    }
    out
}

/// Port of `_blend_rgba`: blend `c2` into `c1` by `factor` (0..1), per channel.
pub fn blend_rgba(c1: &[u8], c2: &[u8], factor: f64) -> Vec<u8> {
    let n = c1.len().min(c2.len());
    (0..n)
        .map(|i| {
            py_round(f64::from(c1[i]) * (1.0 - factor) + f64::from(c2[i]) * factor).clamp(0, 255)
                as u8
        })
        .collect()
}

/// Port of `_contrasting_hover`: lighten a dark surface, darken a light one.
pub fn contrasting_hover(col: &[u8], amount: f64) -> Vec<u8> {
    let rgb: Vec<f64> = col.iter().take(3).map(|&x| f64::from(x) / 255.0).collect();
    let (_, l, _) = rgb_to_hls(rgb[0], rgb[1], rgb[2]);
    let direction = if l < 0.5 { 1.0 } else { -1.0 };
    adjust_color(col, direction * amount, 0.0, 0.0, 0.0)
}

/// Port of `_get_contrasting_text_color`: near-black text on bright grounds,
/// white text elsewhere (WCAG relative luminance, 0.4 cut).
pub fn contrasting_text_color(r: u8, g: u8, b: u8) -> Rgba {
    fn lin(v: f64) -> f64 {
        if v <= 0.03928 {
            v / 12.92
        } else {
            ((v + 0.055) / 1.055).powf(2.4)
        }
    }
    let l = 0.2126 * lin(f64::from(r) / 255.0)
        + 0.7152 * lin(f64::from(g) / 255.0)
        + 0.0722 * lin(f64::from(b) / 255.0);
    if l > 0.4 {
        Rgba::new(20, 20, 20, 255)
    } else {
        Rgba::new(255, 255, 255, 255)
    }
}

/// HSL lightness in 0..1 (what `QColor::lightnessF` reports): `(max+min)/2`.
pub fn hsl_lightness(r: u8, g: u8, b: u8) -> f64 {
    (f64::from(r.max(g).max(b)) + f64::from(r.min(g).min(b))) / 2.0 / 255.0
}

/// WCAG relative luminance of an sRGB colour (see `test_theme_counterparts`).
pub fn relative_luminance(r: u8, g: u8, b: u8) -> f64 {
    fn lin(channel: u8) -> f64 {
        let c = f64::from(channel) / 255.0;
        if c <= 0.04045 {
            c / 12.92
        } else {
            ((c + 0.055) / 1.055).powf(2.4)
        }
    }
    0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
}

/// WCAG contrast ratio between two sRGB colours.
pub fn contrast_ratio(a: (u8, u8, u8), b: (u8, u8, u8)) -> f64 {
    let (la, lb) = (relative_luminance(a.0, a.1, a.2), relative_luminance(b.0, b.1, b.2));
    (la.max(lb) + 0.05) / (la.min(lb) + 0.05)
}

// ---------------------------------------------------------------------------
// ThemeSpec + build_theme
// ---------------------------------------------------------------------------

fn rgba_or(channels: Vec<u8>) -> Rgba {
    Rgba([channels[0], channels[1], channels[2], channels[3]])
}

/// Declarative theme input. Mirrors `lace.dock_theme.ThemeSpec` field for
/// field; colours are `[u8; 4]`, numerics keep int-ness via [`Num`].
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ThemeSpec {
    pub base: Rgba,
    pub accent: Rgba,
    pub text: Rgba,
    pub surface: Option<Rgba>,
    pub border: Option<Rgba>,
    pub focus_border_color: Option<Rgba>,
    pub is_light: bool,
    pub title_mode: String,
    pub title_bg: Option<Rgba>,
    pub hover_mode: String,
    pub success_color: Option<Rgba>,
    pub warning_color: Option<Rgba>,
    pub error_color: Option<Rgba>,
    pub info_color: Option<Rgba>,
    pub corner_radius: Option<Num>,
    pub border_width: Option<Num>,
    pub title_height: Option<Num>,
    pub title_padding_left: Option<Num>,
    pub title_padding_right: Option<Num>,
    pub title_button_spacing: Option<Num>,
    pub title_margin: Option<Num>,
    pub title_border_width: Option<Num>,
    pub title_border_bottom: Option<Num>,
    pub title_border_color: Option<Rgba>,
    pub title_border_focus_color: Option<Rgba>,
    pub border_below_title: Option<bool>,
    pub tab_radius: Option<Num>,
    pub tab_margin: Option<Num>,
    pub tab_border_width: Option<Num>,
    pub tab_border_color: Option<Rgba>,
    pub tab_border_active_color: Option<Rgba>,
    pub tab_border_unfocused_color: Option<Rgba>,
    pub content_margin: Option<MarginSpec>,
    pub tab_dimming: bool,
    pub indicator_width: Option<Num>,
    pub indicator_position: Option<IndicatorPosition>,
    pub sidebar_tab_flat_edge: Option<String>,
    pub sidebar_tab_radius: Option<Num>,
    pub sidebar_tab_bg_normal: Option<Rgba>,
    pub sidebar_tab_bg_hover_start: Option<Rgba>,
    pub sidebar_tab_bg_hover_end: Option<Rgba>,
    pub sidebar_tab_bg_active: Option<Rgba>,
    pub sidebar_tab_border_width: Option<Num>,
    pub sidebar_tab_border_color: Option<Rgba>,
    pub sidebar_tab_border_active_color: Option<Rgba>,
    pub sidebar_tab_border_hover_color: Option<Rgba>,
    pub sidebar_tab_border_closed: Option<bool>,
    pub sidebar_indicator_width: Option<Num>,
    pub sidebar_indicator_position: Option<String>,
    pub tooltip_bg: Option<Rgba>,
    pub tooltip_text: Option<Rgba>,
}

impl Default for ThemeSpec {
    /// Matches the `ThemeSpec` dataclass defaults (`title_mode="darker"`,
    /// `hover_mode="lighter"`, everything else empty/false).
    fn default() -> Self {
        ThemeSpec {
            base: Rgba::new(0, 0, 0, 255),
            accent: Rgba::new(0, 0, 0, 255),
            text: Rgba::new(0, 0, 0, 255),
            surface: None,
            border: None,
            focus_border_color: None,
            is_light: false,
            title_mode: "darker".to_string(),
            title_bg: None,
            hover_mode: "lighter".to_string(),
            success_color: None,
            warning_color: None,
            error_color: None,
            info_color: None,
            corner_radius: None,
            border_width: None,
            title_height: None,
            title_padding_left: None,
            title_padding_right: None,
            title_button_spacing: None,
            title_margin: None,
            title_border_width: None,
            title_border_bottom: None,
            title_border_color: None,
            title_border_focus_color: None,
            border_below_title: None,
            tab_radius: None,
            tab_margin: None,
            tab_border_width: None,
            tab_border_color: None,
            tab_border_active_color: None,
            tab_border_unfocused_color: None,
            content_margin: None,
            tab_dimming: false,
            indicator_width: None,
            indicator_position: None,
            sidebar_tab_flat_edge: None,
            sidebar_tab_radius: None,
            sidebar_tab_bg_normal: None,
            sidebar_tab_bg_hover_start: None,
            sidebar_tab_bg_hover_end: None,
            sidebar_tab_bg_active: None,
            sidebar_tab_border_width: None,
            sidebar_tab_border_color: None,
            sidebar_tab_border_active_color: None,
            sidebar_tab_border_hover_color: None,
            sidebar_tab_border_closed: None,
            sidebar_indicator_width: None,
            sidebar_indicator_position: None,
            tooltip_bg: None,
            tooltip_text: None,
        }
    }
}

impl ThemeSpec {
    /// Minimal constructor for the three seed colours.
    pub fn seeded(base: Rgba, accent: Rgba, text: Rgba) -> Self {
        ThemeSpec {
            base,
            accent,
            text,
            ..ThemeSpec::default()
        }
    }
}

fn adjust_rgba(col: &Rgba, l_off: f64, s_off: f64, h_off: f64, a_off: f64) -> Rgba {
    rgba_or(adjust_color(col.channels(), l_off, s_off, h_off, a_off))
}

fn hover_rgba(col: &Rgba, amount: f64) -> Rgba {
    rgba_or(contrasting_hover(col.channels(), amount))
}

/// Build a complete dock theme from a [`ThemeSpec`].
/// Direct port of `lace.dock_theme._build_theme`.
pub fn build_theme(spec: &ThemeSpec) -> BuiltTheme {
    let base = &spec.base;
    let accent = &spec.accent;
    let text = &spec.text;
    let d = if spec.is_light { -1.0 } else { 1.0 };
    let t_mode = if spec.title_mode == "darker" { -1.0 } else { 1.0 };
    let hover_amt = if spec.hover_mode == "darker" { 0.08 } else { 0.12 };

    let panel = spec
        .surface
        .unwrap_or_else(|| adjust_rgba(base, d * 0.10, 0.0, 0.0, 0.0));
    // NOTE: Python also computes `_border = border or adjust(base, -0.02)`
    // here but never uses it; not ported (goldens prove equivalence).
    let ref_col = spec.surface.unwrap_or(*base);
    let neutral_border = spec.border.unwrap_or_else(|| {
        adjust_rgba(&ref_col, if spec.is_light { -0.12 } else { 0.08 }, 0.0, 0.0, 0.0)
    });
    let focus_border = spec.focus_border_color.unwrap_or_else(|| {
        spec.border
            .unwrap_or_else(|| adjust_rgba(accent, 0.15, 0.0, 0.0, 0.0))
    });
    let title_bg = spec
        .title_bg
        .unwrap_or_else(|| adjust_rgba(&panel, t_mode * 0.06, 0.0, 0.0, 0.0));
    let tooltip_bg = spec
        .tooltip_bg
        .unwrap_or_else(|| adjust_rgba(&panel, d * 0.09, 0.0, 0.0, 0.0));
    let tooltip_text = spec.tooltip_text.unwrap_or(*text);

    let hover = hover_rgba(base, hover_amt);
    let hover_end = hover_rgba(base, (hover_amt * 0.65).max(0.04));
    let btn_hover_title = hover_rgba(&title_bg, hover_amt);
    let btn_hover_panel = hover_rgba(&panel, hover_amt);

    let input_bg = adjust_rgba(&panel, -d * 0.04, 0.0, 0.0, 0.0);
    let alternate_base = adjust_rgba(&input_bg, d * 0.06, 0.0, 0.0, 0.0);
    let button_bg = adjust_rgba(&panel, d * 0.08, 0.0, 0.0, 0.0);
    let color_light = adjust_rgba(&panel, d * 0.15, 0.0, 0.0, 0.0);
    let color_mid = adjust_rgba(&panel, -d * 0.05, 0.0, 0.0, 0.0);
    let color_dark = adjust_rgba(&panel, -d * 0.12, 0.0, 0.0, 0.0);
    let color_shadow = Rgba::new(0, 0, 0, if spec.is_light { 48 } else { 72 });

    let text_muted = adjust_rgba(text, -d * 0.10, 0.0, 0.0, 0.0);
    let text_disabled = adjust_rgba(text, -d * 0.30, 0.0, 0.0, 0.0);
    let text_active = adjust_rgba(text, d * 0.20, 0.0, 0.0, 0.0);
    let btn_disabled = adjust_rgba(base, d * 0.20, 0.05, 0.0, 0.0);
    let accent_bright = adjust_rgba(accent, 0.15, 0.0, 0.0, 0.0);
    let accent_dim = adjust_rgba(accent, 0.0, 0.0, 0.0, -0.75);

    let success = spec
        .success_color
        .unwrap_or(if spec.is_light {
            Rgba::new(34, 134, 58, 255)
        } else {
            Rgba::new(78, 201, 112, 255)
        });
    let warning = spec
        .warning_color
        .unwrap_or(if spec.is_light {
            Rgba::new(179, 134, 0, 255)
        } else {
            Rgba::new(230, 167, 0, 255)
        });
    let error = spec.error_color.unwrap_or(if spec.is_light {
        Rgba::new(203, 36, 49, 255)
    } else {
        Rgba::new(241, 76, 76, 255)
    });
    let info = spec.info_color.unwrap_or(if spec.is_light {
        Rgba::new(0, 102, 214, 255)
    } else {
        Rgba::new(55, 148, 255, 255)
    });

    let transparent = Rgba::new(0, 0, 0, 0);
    let shadow = Rgba::new(0, 0, 0, if spec.is_light { 32 } else { 64 });

    let mut theme: BuiltTheme = BTreeMap::new();

    // CORE
    theme.insert(
        StyleCategory::Core.name().to_string(),
        CategoryTheme::from([
            ("canvas_bg".to_string(), ThemeValue::from(*base)),
            ("border_color".to_string(), ThemeValue::from(neutral_border)),
            ("accent_color".to_string(), ThemeValue::from(*accent)),
            ("focus_border_color".to_string(), ThemeValue::from(focus_border)),
            ("text_color".to_string(), ThemeValue::from(*text)),
            ("disabled_text_color".to_string(), ThemeValue::from(text_disabled)),
            ("success_color".to_string(), ThemeValue::from(success)),
            ("warning_color".to_string(), ThemeValue::from(warning)),
            ("error_color".to_string(), ThemeValue::from(error)),
            ("info_color".to_string(), ThemeValue::from(info)),
            ("tooltip_bg".to_string(), ThemeValue::from(tooltip_bg)),
            ("tooltip_text".to_string(), ThemeValue::from(tooltip_text)),
        ]),
    );

    // PANEL
    theme.insert(
        StyleCategory::Panel.name().to_string(),
        CategoryTheme::from([
            ("bg_normal".to_string(), ThemeValue::from(panel)),
            ("text_color".to_string(), ThemeValue::from(*text)),
            ("input_bg".to_string(), ThemeValue::from(input_bg)),
            ("alternate_base".to_string(), ThemeValue::from(alternate_base)),
            ("button_bg".to_string(), ThemeValue::from(button_bg)),
            ("color_light".to_string(), ThemeValue::from(color_light)),
            ("color_mid".to_string(), ThemeValue::from(color_mid)),
            ("color_dark".to_string(), ThemeValue::from(color_dark)),
            ("color_shadow".to_string(), ThemeValue::from(color_shadow)),
        ]),
    );

    // SIDEBAR
    theme.insert(
        StyleCategory::Sidebar.name().to_string(),
        CategoryTheme::from([
            ("bg_color".to_string(), ThemeValue::from(*base)),
            ("tab_bg_normal".to_string(), ThemeValue::from(transparent)),
            ("tab_bg_hover_start".to_string(), ThemeValue::from(hover)),
            ("tab_bg_hover_end".to_string(), ThemeValue::from(hover_end)),
            ("tab_bg_active".to_string(), ThemeValue::from(panel)),
            ("tab_border_normal_color".to_string(), ThemeValue::from(neutral_border)),
            ("tab_border_active_color".to_string(), ThemeValue::from(*accent)),
            ("tab_text_normal".to_string(), ThemeValue::from(text_muted)),
            ("tab_text_active".to_string(), ThemeValue::from(text_active)),
            ("tab_text_disabled".to_string(), ThemeValue::from(text_disabled)),
            ("indicator_color".to_string(), ThemeValue::from(*accent)),
            ("badge_bg".to_string(), ThemeValue::from(*accent)),
            ("badge_text".to_string(), ThemeValue::from(text_muted)),
        ]),
    );

    // SIDEPANEL
    theme.insert(
        StyleCategory::SidePanel.name().to_string(),
        CategoryTheme::from([
            ("bg_normal".to_string(), ThemeValue::from(panel)),
            ("title_text_color".to_string(), ThemeValue::from(*text)),
            ("button_color".to_string(), ThemeValue::from(text_muted)),
            ("button_disable_clr".to_string(), ThemeValue::from(btn_disabled)),
            ("button_hover_bg".to_string(), ThemeValue::from(btn_hover_panel)),
            ("shadow_color".to_string(), ThemeValue::from(shadow)),
            ("border_color".to_string(), ThemeValue::from(neutral_border)),
            ("focus_border_color".to_string(), ThemeValue::from(focus_border)),
            ("border_width".to_string(), ThemeValue::from(Num::Float(1.0))),
        ]),
    );

    // TAB
    let close_btn_color = rgba_or(blend_rgba(text_active.channels(), panel.channels(), 0.30));
    theme.insert(
        StyleCategory::Tab.name().to_string(),
        CategoryTheme::from([
            ("bg_normal".to_string(), ThemeValue::from(title_bg)),
            ("bg_hover".to_string(), ThemeValue::from(hover)),
            ("bg_active".to_string(), ThemeValue::from(panel)),
            ("border_normal_color".to_string(), ThemeValue::from(neutral_border)),
            ("border_active_color".to_string(), ThemeValue::from(*accent)),
            ("text_normal".to_string(), ThemeValue::from(text_muted)),
            ("text_active".to_string(), ThemeValue::from(text_active)),
            ("indicator_color".to_string(), ThemeValue::from(*accent)),
            ("close_btn_color".to_string(), ThemeValue::from(close_btn_color)),
            ("close_btn_bg_hover".to_string(), ThemeValue::from(btn_hover_panel)),
            ("close_btn_bg_disable".to_string(), ThemeValue::from(btn_disabled)),
        ]),
    );

    // TITLE_BAR
    theme.insert(
        StyleCategory::TitleBar.name().to_string(),
        CategoryTheme::from([
            ("bg_normal".to_string(), ThemeValue::from(title_bg)),
            ("bg_active".to_string(), ThemeValue::from(title_bg)),
            ("border_color".to_string(), ThemeValue::from(neutral_border)),
            ("focus_border_color".to_string(), ThemeValue::from(focus_border)),
            ("text_normal".to_string(), ThemeValue::from(text_muted)),
            ("text_active".to_string(), ThemeValue::from(text_active)),
            ("active_edge_color".to_string(), ThemeValue::from(accent_bright)),
            ("button_color".to_string(), ThemeValue::from(text_muted)),
            ("button_disable_clr".to_string(), ThemeValue::from(btn_disabled)),
            ("button_hover_bg".to_string(), ThemeValue::from(btn_hover_title)),
        ]),
    );

    // SPLITTER
    theme.insert(
        StyleCategory::Splitter.name().to_string(),
        CategoryTheme::from([
            ("handle_color".to_string(), ThemeValue::from(*base)),
            ("handle_hover_color".to_string(), ThemeValue::from(*accent)),
        ]),
    );

    // OVERLAY
    theme.insert(
        StyleCategory::Overlay.name().to_string(),
        CategoryTheme::from([
            ("frame_color".to_string(), ThemeValue::from(accent_bright)),
            ("background_color".to_string(), ThemeValue::from(panel)),
            ("overlay_color".to_string(), ThemeValue::from(accent_dim)),
            ("arrow_color".to_string(), ThemeValue::from(*text)),
            ("shadow_color".to_string(), ThemeValue::from(shadow)),
        ]),
    );

    // --- Spec overrides (verbatim passthrough) ---
    {
        let set = |theme: &mut BuiltTheme, cat: StyleCategory, key: &str, value: ThemeValue| {
            theme
                .get_mut(cat.name())
                .expect("category always built above")
                .insert(key.to_string(), value);
        };
        if let Some(v) = spec.corner_radius {
            set(&mut theme, StyleCategory::Core, "corner_radius", v.into());
            set(&mut theme, StyleCategory::Panel, "corner_radius", v.into());
            set(&mut theme, StyleCategory::SidePanel, "corner_radius", v.into());
        }
        if let Some(v) = spec.border_width {
            set(&mut theme, StyleCategory::Core, "border_width", v.into());
            set(&mut theme, StyleCategory::Panel, "border_width", v.into());
            set(&mut theme, StyleCategory::SidePanel, "border_width", v.into());
        }
        if let Some(v) = spec.title_height {
            set(&mut theme, StyleCategory::TitleBar, "height", v.into());
        }
        if let Some(v) = spec.title_padding_left {
            set(&mut theme, StyleCategory::TitleBar, "padding_left", v.into());
        }
        if let Some(v) = spec.title_padding_right {
            set(&mut theme, StyleCategory::TitleBar, "padding_right", v.into());
        }
        if let Some(v) = spec.title_button_spacing {
            set(&mut theme, StyleCategory::TitleBar, "button_spacing", v.into());
        }
        if let Some(v) = spec.title_margin {
            set(&mut theme, StyleCategory::TitleBar, "margin", v.into());
        }
        if let Some(v) = spec.title_border_width {
            set(&mut theme, StyleCategory::TitleBar, "border_width", v.into());
        }
        if let Some(v) = spec.title_border_bottom {
            set(&mut theme, StyleCategory::TitleBar, "border_bottom", v.into());
        }
        if let Some(v) = spec.title_border_color {
            set(&mut theme, StyleCategory::TitleBar, "border_color", v.into());
        }
        if let Some(v) = spec.title_border_focus_color {
            set(&mut theme, StyleCategory::TitleBar, "focus_border_color", v.into());
        }
        if let Some(v) = spec.tab_radius {
            set(&mut theme, StyleCategory::Tab, "corner_radius", v.into());
        }
        if let Some(v) = spec.tab_margin {
            set(&mut theme, StyleCategory::Tab, "margin", v.into());
        }
        if let Some(v) = spec.border_below_title {
            set(&mut theme, StyleCategory::Core, "border_below_title", v.into());
        }
        if let Some(v) = spec.tab_border_width {
            set(&mut theme, StyleCategory::Tab, "border_width", v.into());
        }
        if let Some(v) = spec.tab_border_color {
            set(&mut theme, StyleCategory::Tab, "border_normal_color", v.into());
        }
        if let Some(v) = spec.tab_border_active_color {
            set(&mut theme, StyleCategory::Tab, "border_active_color", v.into());
        }
        if let Some(v) = spec.tab_border_unfocused_color {
            set(&mut theme, StyleCategory::Tab, "border_unfocused_color", v.into());
        }
        if let Some(v) = &spec.content_margin {
            let value = match v {
                MarginSpec::Scalar(n) => ThemeValue::from(*n),
                MarginSpec::List(items) => ThemeValue::NumList(items.clone()),
            };
            set(&mut theme, StyleCategory::Panel, "content_margin", value);
        }
        set(
            &mut theme,
            StyleCategory::Tab,
            "tab_dimming",
            ThemeValue::from(spec.tab_dimming),
        );
        if let Some(v) = spec.indicator_width {
            set(&mut theme, StyleCategory::Tab, "indicator_width", v.into());
        }
        if let Some(v) = &spec.indicator_position {
            let value = match v {
                IndicatorPosition::Single(s) => ThemeValue::from(s.as_str()),
                IndicatorPosition::Multiple(items) => ThemeValue::StrList(items.clone()),
            };
            set(&mut theme, StyleCategory::Tab, "indicator_position", value);
        }
        if let Some(v) = &spec.sidebar_tab_flat_edge {
            set(&mut theme, StyleCategory::Sidebar, "tab_flat_edge", v.as_str().into());
        }
        if let Some(v) = spec.sidebar_tab_radius {
            set(&mut theme, StyleCategory::Sidebar, "tab_corner_radius", v.into());
        }
        if let Some(v) = spec.sidebar_tab_bg_normal {
            set(&mut theme, StyleCategory::Sidebar, "tab_bg_normal", v.into());
        }
        if let Some(v) = spec.sidebar_tab_bg_hover_start {
            set(&mut theme, StyleCategory::Sidebar, "tab_bg_hover_start", v.into());
        }
        if let Some(v) = spec.sidebar_tab_bg_hover_end {
            set(&mut theme, StyleCategory::Sidebar, "tab_bg_hover_end", v.into());
        }
        if let Some(v) = spec.sidebar_tab_bg_active {
            set(&mut theme, StyleCategory::Sidebar, "tab_bg_active", v.into());
        }
        if let Some(v) = spec.sidebar_tab_border_width {
            set(&mut theme, StyleCategory::Sidebar, "tab_border_width", v.into());
        }
        if let Some(v) = spec.sidebar_tab_border_color {
            set(&mut theme, StyleCategory::Sidebar, "tab_border_normal_color", v.into());
        }
        if let Some(v) = spec.sidebar_tab_border_active_color {
            set(&mut theme, StyleCategory::Sidebar, "tab_border_active_color", v.into());
        }
        if let Some(v) = spec.sidebar_tab_border_hover_color {
            set(&mut theme, StyleCategory::Sidebar, "tab_border_hover_color", v.into());
        }
        if let Some(v) = spec.sidebar_tab_border_closed {
            set(&mut theme, StyleCategory::Sidebar, "tab_border_closed", v.into());
        }
        if let Some(v) = spec.sidebar_indicator_width {
            set(&mut theme, StyleCategory::Sidebar, "indicator_width", v.into());
        }
        if let Some(v) = &spec.sidebar_indicator_position {
            set(&mut theme, StyleCategory::Sidebar, "indicator_position", v.as_str().into());
        }
    }

    theme
}

// ---------------------------------------------------------------------------
// Theme groups (port of dock_style_manager.theme_groups/theme_choices)
// ---------------------------------------------------------------------------

/// `"tokyo_night"` -> `"Tokyo Night"`.
pub fn theme_label(key: &str) -> String {
    key.split('_')
        .map(|word| {
            let mut chars = word.chars();
            match chars.next() {
                None => String::new(),
                Some(first) => {
                    first.to_uppercase().collect::<String>() + chars.as_str()
                }
            }
        })
        .collect::<Vec<_>>()
        .join(" ")
}

/// `(group label, [(label, key), ...])` for every built-in theme.
///
/// `group_order` is `(group title, preset keys)` in presentation order;
/// `preset_keys` are all known keys (specs plus `"default"`). Ungrouped keys
/// join the first group rather than being dropped — mirroring
/// `dock_style_manager.theme_groups`.
pub fn theme_groups(
    group_order: &[(&str, &[&str])],
    preset_keys: &[&str],
) -> Vec<(String, Vec<(String, String)>)> {
    let grouped: std::collections::HashSet<&str> =
        group_order.iter().flat_map(|(_, keys)| keys.iter().copied()).collect();
    let orphans: Vec<&str> = preset_keys.iter().copied().filter(|k| !grouped.contains(k)).collect();
    group_order
        .iter()
        .enumerate()
        .map(|(index, (title, keys))| {
            let mut members: Vec<&str> = if index == 0 { orphans.clone() } else { vec![] };
            members.extend(keys.iter().copied().filter(|k| preset_keys.contains(k)));
            (
                title.to_string(),
                members.iter().map(|k| (theme_label(k), k.to_string())).collect(),
            )
        })
        .collect()
}

/// `(label, key)` for every built-in theme, groups flattened in order.
pub fn theme_choices(
    group_order: &[(&str, &[&str])],
    preset_keys: &[&str],
) -> Vec<(String, String)> {
    theme_groups(group_order, preset_keys)
        .into_iter()
        .flat_map(|(_, choices)| choices)
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn seed() -> ThemeSpec {
        ThemeSpec::seeded(
            Rgba::new(20, 23, 30, 255),
            Rgba::new(45, 85, 170, 255),
            Rgba::new(200, 205, 215, 255),
        )
    }

    #[test]
    fn covers_all_categories() {
        let theme = build_theme(&seed());
        let mut cats: Vec<&str> = theme.keys().map(String::as_str).collect();
        cats.sort_unstable();
        assert_eq!(
            cats,
            vec![
                "core", "overlay", "panel", "sidebar",
                "sidepanel", "splitter", "tab", "title_bar",
            ]
        );
        let core = &theme["core"];
        for token in [
            "canvas_bg", "border_color", "accent_color", "focus_border_color",
            "text_color", "disabled_text_color", "success_color", "warning_color",
            "error_color", "info_color", "tooltip_bg", "tooltip_text",
        ] {
            assert!(core.contains_key(token), "missing {token}");
        }
    }

    #[test]
    fn geometry_overrides_land() {
        let mut spec = ThemeSpec::seeded(
            Rgba::new(10, 10, 10, 255),
            Rgba::new(0, 120, 212, 255),
            Rgba::new(230, 230, 230, 255),
        );
        spec.corner_radius = Some(Num::Int(9));
        spec.border_width = Some(Num::Float(2.0));
        spec.title_height = Some(Num::Int(34));
        spec.tab_radius = Some(Num::Int(7));
        let theme = build_theme(&spec);
        assert_eq!(theme["core"]["corner_radius"], ThemeValue::Num(Num::Int(9)));
        assert_eq!(theme["panel"]["corner_radius"], ThemeValue::Num(Num::Int(9)));
        assert_eq!(theme["panel"]["border_width"], ThemeValue::Num(Num::Float(2.0)));
        assert_eq!(theme["title_bar"]["height"], ThemeValue::Num(Num::Int(34)));
        assert_eq!(theme["tab"]["corner_radius"], ThemeValue::Num(Num::Int(7)));
    }

    #[test]
    fn light_dark_direction_flips() {
        let dark = build_theme(&ThemeSpec::seeded(
            Rgba::new(10, 10, 10, 255),
            Rgba::new(0, 120, 212, 255),
            Rgba::new(240, 240, 240, 255),
        ));
        let mut light_spec = ThemeSpec::seeded(
            Rgba::new(240, 240, 240, 255),
            Rgba::new(0, 120, 212, 255),
            Rgba::new(20, 20, 20, 255),
        );
        light_spec.is_light = true;
        let light = build_theme(&light_spec);
        let ThemeValue::Color(dark_panel) = dark["panel"]["bg_normal"] else {
            panic!("panel bg must be a colour")
        };
        let ThemeValue::Color(light_panel) = light["panel"]["bg_normal"] else {
            panic!("panel bg must be a colour")
        };
        assert!(dark_panel.0[0] > 10);
        assert!(light_panel.0[0] < 240);
    }

    #[test]
    fn adjust_clamps_and_keeps_alpha_shape() {
        let out = adjust_color(&[255, 0, 0, 255], 5.0, 0.0, 0.0, 0.0);
        assert_eq!(out.len(), 4);
        assert!(out[0] <= 255);
        let out2 = adjust_color(&[0, 0, 0, 255], -5.0, 0.0, 0.0, 0.0);
        assert!(out2[0] >= 0);
        assert_eq!(adjust_color(&[100, 100, 100, 200], 0.0, 0.0, 0.0, 0.0).len(), 4);
        assert_eq!(adjust_color(&[100, 100, 100], 0.0, 0.0, 0.0, 0.0).len(), 3);
    }

    #[test]
    fn contrasting_hover_goes_opposite_direction() {
        let dark_hover = contrasting_hover(&[20, 20, 20, 255], 0.10);
        let light_hover = contrasting_hover(&[240, 240, 240, 255], 0.10);
        assert!(dark_hover.iter().take(3).map(|&x| u32::from(x)).sum::<u32>() > 60);
        assert!(light_hover.iter().take(3).map(|&x| u32::from(x)).sum::<u32>() < 720 - 60);
    }

    #[test]
    fn tooltip_tokens_derived_and_overridable() {
        let theme = build_theme(&seed());
        assert_ne!(theme["core"]["tooltip_bg"], theme["panel"]["bg_normal"]);
        assert_eq!(theme["core"]["tooltip_text"], ThemeValue::from(seed().text));
        let mut spec = seed();
        spec.tooltip_bg = Some(Rgba::new(10, 20, 30, 255));
        spec.tooltip_text = Some(Rgba::new(1, 2, 3, 255));
        let custom = build_theme(&spec);
        assert_eq!(custom["core"]["tooltip_bg"], ThemeValue::from(Rgba::new(10, 20, 30, 255)));
        assert_eq!(custom["core"]["tooltip_text"], ThemeValue::from(Rgba::new(1, 2, 3, 255)));
    }

    #[test]
    fn close_btn_color_is_seventy_thirty_blend() {
        let theme = build_theme(&seed());
        let tab = &theme["tab"];
        let ThemeValue::Color(active) = tab["text_active"] else { panic!() };
        let ThemeValue::Color(panel) = tab["bg_active"] else { panic!() };
        let ThemeValue::Color(close) = tab["close_btn_color"] else { panic!() };
        for i in 0..3 {
            let expected = ((f64::from(active.0[i]) * 0.7 + f64::from(panel.0[i]) * 0.3)
                .round_ties_even() as i64)
                .clamp(0, 255) as u8;
            assert_eq!(close.0[i], expected, "channel {i}");
        }
    }

    #[test]
    fn contrasting_text_picks_dark_on_bright_and_white_on_dark() {
        assert_eq!(contrasting_text_color(255, 255, 255), Rgba::new(20, 20, 20, 255));
        assert_eq!(contrasting_text_color(0, 0, 0), Rgba::new(255, 255, 255, 255));
    }

    #[test]
    fn theme_label_title_cases() {
        assert_eq!(theme_label("tokyo_night"), "Tokyo Night");
        assert_eq!(theme_label("dark"), "Dark");
    }
}
