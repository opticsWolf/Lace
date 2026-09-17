//! Port of `tests/test_theme_grouping.py`: the presets form four labelled
//! groups, families stay together dark -> light, and the flat menu is the
//! grouped one flattened.

use lace_core::presets_generated::{THEME_GROUP_ORDER, preset_keys, preset_specs};
use lace_core::theme::{build_theme, hsl_lightness, theme_choices, theme_groups};

const FAMILIES: &[&[&str]] = &[
    &["cyberpunk_edge", "cyberpunk_edge_neutral", "cyberpunk_edge_light"],
    &["violet_haze", "violet_haze_neutral", "violet_haze_light"],
    &["midnight_haze", "midnight_haze_neutral", "midnight_haze_light"],
    &["slate_amber_dark", "slate_amber", "slate_amber_light"],
];

fn flat() -> Vec<String> {
    let keys = preset_keys();
    theme_choices(THEME_GROUP_ORDER, &keys).into_iter().map(|(_, k)| k).collect()
}

fn panel_luminance(name: &str, specs: &std::collections::HashMap<String, lace_core::theme::ThemeSpec>) -> f64 {
    let theme = build_theme(&specs[name]);
    let panel = match &theme["panel"]["bg_normal"] {
        lace_core::theme::ThemeValue::Color(c) => *c,
        _ => panic!("{name}: no panel bg"),
    };
    hsl_lightness(panel.0[0], panel.0[1], panel.0[2])
}

#[test]
fn groups_cover_every_preset_exactly_once() {
    let listed: Vec<&str> = THEME_GROUP_ORDER
        .iter()
        .flat_map(|(_, keys)| keys.iter().copied())
        .collect();
    let mut sorted = listed.clone();
    sorted.sort_unstable();
    sorted.dedup();
    assert_eq!(listed.len(), sorted.len(), "a theme is in two groups");
    let specs: std::collections::HashSet<&str> =
        preset_specs().iter().map(|(n, _)| *n).collect();
    assert_eq!(listed.into_iter().collect::<std::collections::HashSet<_>>(), specs);
}

#[test]
fn groups_place_default_rather_than_dropping_it() {
    assert!(!THEME_GROUP_ORDER.iter().flat_map(|(_, k)| k.iter()).any(|k| *k == "default"));
    let order = flat();
    assert_eq!(order.len(), 27);
    assert_eq!(order[0], "default", "the stock look should head the first group");
}

#[test]
fn no_group_is_empty_or_a_dumping_ground() {
    let keys = preset_keys();
    for (title, choices) in theme_groups(THEME_GROUP_ORDER, &keys) {
        assert!(!choices.is_empty(), "{title} is an empty submenu");
        assert!(choices.len() <= 12, "{title} holds {} — regroup it", choices.len());
    }
}

#[test]
fn flat_list_is_the_grouped_one_flattened() {
    let keys = preset_keys();
    let via_choices: Vec<String> =
        theme_choices(THEME_GROUP_ORDER, &keys).into_iter().map(|(_, k)| k).collect();
    assert_eq!(via_choices, flat());
}

#[test]
fn families_stay_together_in_order() {
    let order = flat();
    for members in FAMILIES {
        let positions: Vec<usize> =
            members.iter().map(|m| order.iter().position(|k| k == m).unwrap()).collect();
        let mut sorted = positions.clone();
        sorted.sort_unstable();
        assert_eq!(positions, sorted, "{members:?} is out of order");
        assert_eq!(positions[positions.len() - 1] - positions[0], members.len() - 1);
    }
}

#[test]
fn families_run_darkest_to_lightest() {
    let specs: std::collections::HashMap<_, _> =
        preset_specs().into_iter().map(|(n, s)| (n.to_string(), s)).collect();
    for members in FAMILIES {
        let lums: Vec<f64> = members.iter().map(|m| panel_luminance(m, &specs)).collect();
        let mut sorted = lums.clone();
        sorted.sort_by(|a, b| a.partial_cmp(b).unwrap());
        assert_eq!(lums, sorted, "{members:?} is not ordered by lightness");
        assert!(lums[0] < 0.35, "{members:?} does not start dark");
        assert!(lums[lums.len() - 1] > 0.9, "{members:?} does not end light");
        for pair in lums.windows(2) {
            assert!(pair[1] - pair[0] > 0.1, "{members:?} has two members in one tier");
        }
    }
}

#[test]
fn every_group_label_is_a_menu_title() {
    let keys = preset_keys();
    for (title, _) in theme_groups(THEME_GROUP_ORDER, &keys) {
        assert!(!title.is_empty());
        assert!(title.chars().next().unwrap().is_uppercase());
        assert!(!title.contains('_'));
    }
}
