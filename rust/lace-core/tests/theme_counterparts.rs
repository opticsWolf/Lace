//! Port of `tests/test_theme_counterparts.py`: the light/neutral counterparts
//! of the four edge-treatment families keep their parent's geometry exactly
//! and move only the palette. All metrics are Qt-free (WCAG luminance,
//! HSL lightness, HSV hue/saturation).

use std::collections::HashMap;

use lace_core::presets_generated::preset_specs;
use lace_core::theme::{BuiltTheme, Rgba, ThemeSpec, build_theme, contrast_ratio, hsl_lightness,
    relative_luminance};

const FAMILIES: &[(&str, &[&str])] = &[
    ("cyberpunk_edge", &["cyberpunk_edge_light", "cyberpunk_edge_neutral"]),
    ("violet_haze", &["violet_haze_light", "violet_haze_neutral"]),
    ("midnight_haze", &["midnight_haze_light", "midnight_haze_neutral"]),
    ("slate_amber", &["slate_amber_dark", "slate_amber_light"]),
];

const GEOMETRY: &[&str] = &[
    "corner_radius", "border_width", "title_height", "title_padding_left",
    "title_padding_right", "title_button_spacing", "title_margin",
    "title_border_width", "title_border_bottom", "border_below_title",
    "tab_radius", "tab_margin", "tab_border_width", "content_margin",
    "indicator_width", "indicator_position", "tab_dimming",
    "sidebar_tab_flat_edge", "sidebar_tab_radius", "sidebar_tab_border_width",
    "sidebar_indicator_width",
];

const SEMANTIC: &[&str] = &["success_color", "warning_color", "error_color", "info_color"];
const LIGHT: &[&str] = &[
    "cyberpunk_edge_light", "violet_haze_light", "midnight_haze_light", "slate_amber_light",
];
const NEUTRAL: &[&str] = &[
    "cyberpunk_edge_neutral", "violet_haze_neutral", "midnight_haze_neutral",
];

fn specs() -> HashMap<String, ThemeSpec> {
    preset_specs().into_iter().map(|(n, s)| (n.to_string(), s)).collect()
}

fn core_rgb(name: &str) -> HashMap<String, Rgba> {
    let specs = specs();
    let theme = build_theme(&specs[name]);
    theme["core"]
        .iter()
        .filter_map(|(k, v)| match v {
            lace_core::theme::ThemeValue::Color(c) => Some((k.clone(), *c)),
            _ => None,
        })
        .collect()
}

fn panel_rgb(name: &str) -> Rgba {
    let specs = specs();
    let theme = build_theme(&specs[name]);
    match &theme["panel"]["bg_normal"] {
        lace_core::theme::ThemeValue::Color(c) => *c,
        other => panic!("{name}: panel bg_normal is not a colour: {other:?}"),
    }
}

fn rgb3(c: Rgba) -> (u8, u8, u8) {
    (c.0[0], c.0[1], c.0[2])
}

fn color_of(theme: &BuiltTheme, category: &str, token: &str) -> Rgba {
    match &theme[category][token] {
        lace_core::theme::ThemeValue::Color(c) => *c,
        other => panic!("{category}.{token} is not a colour: {other:?}"),
    }
}

fn spread(c: Rgba) -> i32 {
    let (r, g, b) = (i32::from(c.0[0]), i32::from(c.0[1]), i32::from(c.0[2]));
    r.max(g).max(b) - r.min(g).min(b)
}

/// Float HSV (h in degrees), mirroring `QColor::hue/saturation` closely
/// enough for the loose counterpart bounds (x0.85, <=20 deg).
fn hsv(r: u8, g: u8, b: u8) -> (f64, f64) {
    let (rf, gf, bf) = (f64::from(r) / 255.0, f64::from(g) / 255.0, f64::from(b) / 255.0);
    let maxc = rf.max(gf).max(bf);
    let minc = rf.min(gf).min(bf);
    let delta = maxc - minc;
    let s = if maxc == 0.0 { 0.0 } else { delta / maxc };
    let h = if delta == 0.0 {
        0.0
    } else if maxc == rf {
        60.0 * (((gf - bf) / delta) % 6.0)
    } else if maxc == gf {
        60.0 * ((bf - rf) / delta + 2.0)
    } else {
        60.0 * ((rf - gf) / delta + 4.0)
    };
    (h.rem_euclid(360.0), s)
}

fn hue_shift(a: Rgba, b: Rgba) -> f64 {
    let (ha, _) = hsv(a.0[0], a.0[1], a.0[2]);
    let (hb, _) = hsv(b.0[0], b.0[1], b.0[2]);
    (ha - hb).abs().min(360.0 - (ha - hb).abs())
}

#[test]
fn every_counterpart_is_registered() {
    let specs = specs();
    for (parent, children) in FAMILIES {
        assert!(specs.contains_key(*parent));
        for child in *children {
            assert!(specs.contains_key(*child), "{child} is not a shipped preset");
        }
    }
}

#[test]
fn counterparts_keep_parents_geometry() {
    let specs = specs();
    for (parent, children) in FAMILIES {
        let p = serde_json::to_value(&specs[*parent]).unwrap();
        for child in *children {
            let c = serde_json::to_value(&specs[*child]).unwrap();
            let differing: Vec<_> = GEOMETRY
                .iter()
                .filter(|f| p[*f] != c[*f])
                .collect();
            assert!(differing.is_empty(), "{child} drifted from {parent}: {differing:?}");
        }
    }
}

#[test]
fn light_counterparts_are_actually_light() {
    let specs = specs();
    for name in LIGHT {
        assert!(specs[*name].is_light, "{name} is not flagged is_light");
        let panel = rgb3(panel_rgb(name));
        assert!(relative_luminance(panel.0, panel.1, panel.2) > 0.7);
    }
}

#[test]
fn light_counterparts_darken_accents_enough_to_read() {
    for name in LIGHT {
        let core = core_rgb(name);
        let ratio = contrast_ratio(rgb3(core["accent_color"]), rgb3(panel_rgb(name)));
        assert!(ratio >= 3.0, "{name}: accent is {ratio:.2}:1 on its own panel");
    }
}

#[test]
fn every_counterpart_keeps_body_text_legible() {
    for (_, children) in FAMILIES {
        for name in *children {
            let core = core_rgb(name);
            let ratio = contrast_ratio(rgb3(core["text_color"]), rgb3(panel_rgb(name)));
            assert!(ratio >= 7.0, "{name}: text is {ratio:.2}:1 on its own panel");
        }
    }
}

#[test]
fn neutral_counterparts_flatten_grounds() {
    let specs = specs();
    for name in NEUTRAL {
        let parent = name.replace("_neutral", "");
        for field in ["base", "surface", "title_bg"] {
            let p: Rgba = match field {
                "base" => specs[&parent].base,
                "surface" => specs[&parent].surface.expect("neutral parents set grounds"),
                _ => specs[&parent].title_bg.expect("neutral parents set grounds"),
            };
            let c: Rgba = match field {
                "base" => specs[*name].base,
                "surface" => specs[*name].surface.expect("neutral sets grounds"),
                _ => specs[*name].title_bg.expect("neutral sets grounds"),
            };
            assert!(spread(c) < spread(p), "{name}: {field} is no flatter");
            assert!(spread(c) <= 6, "{name}: {field} still reads as a colour");
        }
    }
}

#[test]
fn neutral_counterparts_are_mid_tones_leaning_light() {
    for name in NEUTRAL {
        let parent = name.replace("_neutral", "");
        let light = name.replace("_neutral", "_light");
        let lum = |n: &str| {
            let p = rgb3(panel_rgb(n));
            hsl_lightness(p.0, p.1, p.2)
        };
        let (dark, mid, pale) = (lum(&parent), lum(name), lum(&light));
        assert!(dark + 0.2 < mid && mid < pale - 0.2, "{name} at {mid:.2} is not a tier of its own");
        assert!(mid > (dark + pale) / 2.0, "{name} sits below the midpoint");
        assert!(mid > 0.6, "{name}'s panel is {mid:.2}, not a light-leaning mid");
    }
}

#[test]
fn mid_tone_neutrals_flip_to_a_light_chassis() {
    let specs = specs();
    for name in NEUTRAL {
        assert!(specs[*name].is_light);
        let core = core_rgb(name);
        let ratio = contrast_ratio(rgb3(core["text_color"]), rgb3(panel_rgb(name)));
        assert!(ratio >= 7.0);
    }
}

#[test]
fn neutral_counterparts_keep_parents_highlight() {
    let specs = specs();
    for name in NEUTRAL {
        let parent = name.replace("_neutral", "");
        let p = specs[&parent].accent;
        let c = specs[*name].accent;
        let (_, sp) = hsv(p.0[0], p.0[1], p.0[2]);
        let (_, sc) = hsv(c.0[0], c.0[1], c.0[2]);
        assert!(sc >= sp * 0.85, "{name}: accent was drained, not adjusted");
        assert!(hue_shift(p, c) <= 20.0, "{name}: accent moved hue");
    }
}

#[test]
fn neutral_counterparts_outcolour_their_ground() {
    let specs = specs();
    for name in NEUTRAL {
        let accent = spread(specs[*name].accent);
        let ground = ["base", "surface", "title_bg"]
            .iter()
            .map(|f| match *f {
                "base" => spread(specs[*name].base),
                "surface" => spread(specs[*name].surface.unwrap()),
                _ => spread(specs[*name].title_bg.unwrap()),
            })
            .max()
            .unwrap();
        assert!(accent > ground * 10, "{name}: accent spread {accent} vs ground {ground}");
    }
}

#[test]
fn neutral_counterparts_keep_semantic_colours() {
    for name in NEUTRAL {
        let core = core_rgb(name);
        let mut seen = Vec::new();
        for token in SEMANTIC {
            let c = core[*token];
            assert!(spread(c) > 40, "{name}: {token} was drained");
            seen.push((c.0[0], c.0[1], c.0[2]));
        }
        seen.sort_unstable();
        seen.dedup();
        assert_eq!(seen.len(), SEMANTIC.len(), "{name}: two status colours collide");
    }
}

#[test]
fn counterparts_move_their_accents() {
    let specs = specs();
    for (parent, children) in FAMILIES {
        for child in *children {
            assert_ne!(specs[*parent].accent, specs[*child].accent);
        }
    }
}

#[test]
fn slate_amber_ships_as_three_tiers() {
    for (i, tier) in ["slate_amber_dark", "slate_amber", "slate_amber_light"].iter().enumerate() {
        let p = rgb3(panel_rgb(tier));
        let l = relative_luminance(p.0, p.1, p.2);
        match i {
            0 => assert!(l < 0.1),
            1 => assert!(l > 0.6),
            _ => assert!(l > 0.9),
        }
    }
    let specs = specs();
    assert!(!specs["slate_amber_dark"].is_light);
    assert!(specs["slate_amber"].is_light);
    assert!(specs["slate_amber_light"].is_light);
}

#[test]
fn slate_amber_light_deepens_amber_as_ground_brightens() {
    let specs = specs();
    let (parent, brighter) = (&specs["slate_amber"], &specs["slate_amber_light"]);
    assert!(brighter.base.0.iter().map(|&x| u32::from(x)).sum::<u32>()
        > parent.base.0.iter().map(|&x| u32::from(x)).sum::<u32>());
    assert!(brighter.surface.unwrap().0.iter().map(|&x| u32::from(x)).sum::<u32>()
        > parent.surface.unwrap().0.iter().map(|&x| u32::from(x)).sum::<u32>());
    assert!(brighter.accent.0.iter().map(|&x| u32::from(x)).sum::<u32>()
        < parent.accent.0.iter().map(|&x| u32::from(x)).sum::<u32>());
    let brighter_ratio = contrast_ratio(rgb3(brighter.accent), rgb3(panel_rgb("slate_amber_light")));
    let parent_ratio = contrast_ratio(rgb3(parent.accent), rgb3(panel_rgb("slate_amber")));
    assert!(brighter_ratio > parent_ratio);
}

#[test]
fn slate_amber_light_keeps_parents_hover_direction() {
    let specs = specs();
    assert_eq!(specs["slate_amber_light"].hover_mode, "lighter");
    assert_eq!(specs["slate_amber"].hover_mode, "lighter");
    let theme = build_theme(&specs["slate_amber_light"]);
    let strip = color_of(&theme, "tab", "bg_normal");
    let hover = color_of(&theme, "tab", "bg_hover");
    let gap = (i32::from(strip.0[0]) + i32::from(strip.0[1]) + i32::from(strip.0[2])
        - i32::from(hover.0[0]) - i32::from(hover.0[1]) - i32::from(hover.0[2]))
    .abs() / 3;
    assert!(gap > 25);
}

#[test]
fn theme_spec_field_names_match_python_attributes() {
    // The geometry-equality test above serializes specs; if a Rust field
    // were renamed, its GEOMETRY key would come back null on one side.
    let p = serde_json::to_value(&specs()["cyberpunk_edge"]).unwrap();
    for field in GEOMETRY {
        assert!(p.get(*field).is_some(), "ThemeSpec missing `{field}`");
    }
}
