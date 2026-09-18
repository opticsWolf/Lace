// Theme-aware SVG icon loader: the Rust port of `DockIconProvider`
// (`lace/dock_icon_provider.py`) plus the `dock_icon()` memo contract from
// `lace/dock_menu.py`, adapted for QML.
//
// Python renders tinted QPixmaps (QIcon) for QtWidgets. QML cannot consume
// QIcons — instead this module tints the SVG source and encodes it as a
// `data:image/svg+xml;utf8,...` URL the QML `Image` element loads through
// QtSvg. Tint caching is intentionally NOT done here: identical (name, color)
// inputs produce identical URL strings, and Qt's image loader caches by URL,
// so re-evaluation is free after the first load.
//
// Tint resolution (which theme token picks the color for which button) is NOT
// done here either — QML passes an already-resolved `#rrggbb` string, exactly
// like the provider's `color=` override parameter. That keeps theme-token
// knowledge in one place (the QML `LaceTheme` bindings, which update live).

/// (file stem, svg source) for every bundled icon.
///
/// Stems are lowercase without extension, matching the provider's cache keys.
const ICONS: &[(&str, &str)] = &[
    ("close", include_str!("../icons/close.svg")),
    ("close_others", include_str!("../icons/close_others.svg")),
    ("close_tab", include_str!("../icons/close_tab.svg")),
    ("dock", include_str!("../icons/dock.svg")),
    ("float", include_str!("../icons/float.svg")),
    ("maximize", include_str!("../icons/maximize.svg")),
    ("pin", include_str!("../icons/pin.svg")),
    ("pin_all", include_str!("../icons/pin_all.svg")),
    ("restore", include_str!("../icons/restore.svg")),
    ("tab_list", include_str!("../icons/tab_list.svg")),
    ("tabs_menu", include_str!("../icons/tabs_menu.svg")),
    ("unpin", include_str!("../icons/unpin.svg")),
];

/// Resolve a caller-facing icon name to its SVG source.
///
/// Returns `None` for unknown names. Mirrors the provider: names are
/// case-insensitive, and `minimize` is an alias of `restore` (there is no
/// minimize.svg; the title bar shows the restore glyph in both states).
pub fn icon_source(name: &str) -> Option<&'static str> {
    let key = name.to_ascii_lowercase();
    let key = if key == "minimize" { "restore" } else { key.as_str() };
    ICONS.iter().find(|(n, _)| *n == key).map(|(_, svg)| *svg)
}

/// All bundled icon names (lowercase stems, extension stripped).
pub fn icon_names() -> Vec<&'static str> {
    ICONS.iter().map(|(n, _)| *n).collect()
}

/// Normalize a caller-supplied tint to `#rrggbb`.
///
/// QML theme colors arrive as `#rrggbb`; an `#aarrggbb` passes through with
/// its alpha stripped (Python parity: `QColor.name()` drops the alpha
/// channel). Anything else is returned unchanged.
pub fn normalize_tint(color: &str) -> String {
    let c = color.trim();
    if c.len() == 9 && c.starts_with('#') && c[1..].chars().all(|ch| ch.is_ascii_hexdigit()) {
        format!("#{}", &c[3..])
    } else {
        c.to_string()
    }
}

/// Value is protected from re-tinting when it is `none` followed by a
/// non-identifier character (end of value, `-`, space, ...), mirroring the
/// Python `(?!none\b)` lookahead.
fn is_none_value(value: &str) -> bool {
    if let Some(rest) = value.strip_prefix("none") {
        match rest.chars().next() {
            None => true,
            Some(ch) => !(ch.is_ascii_alphanumeric() || ch == '_'),
        }
    } else {
        false
    }
}

/// Tint an SVG source with `color` (a `#rrggbb` string).
///
/// Mirrors `DockIconProvider._tint_svg`: SVGs using `currentColor` (every
/// bundled icon) get a plain substitution; otherwise each `fill="..."`
/// / `stroke="..."` value except `none` is replaced.
pub fn tint_svg(svg: &str, color: &str) -> String {
    if svg.contains("currentColor") {
        return svg.replace("currentColor", color);
    }
    let mut out = String::with_capacity(svg.len());
    let bytes = svg.as_bytes();
    let mut i = 0;
    while i < bytes.len() {
        let mut matched: Option<usize> = None;
        for attr in ["fill=\"", "stroke=\""] {
            if svg[i..].starts_with(attr) {
                matched = Some(attr.len());
                break;
            }
        }
        match matched {
            None => {
                out.push(bytes[i] as char);
                i += 1;
            }
            Some(attr_len) => {
                let val_start = i + attr_len;
                let rest = &svg[val_start..];
                match rest.find('"') {
                    None => {
                        out.push_str(&svg[i..]);
                        break;
                    }
                    Some(end) => {
                        let value = &rest[..end];
                        // Re-emit the `fill="` / `stroke="` prefix verbatim.
                        out.push_str(&svg[i..val_start]);
                        if is_none_value(value) {
                            out.push_str(value);
                        } else {
                            out.push_str(color);
                        }
                        out.push('"');
                        i = val_start + end + 1;
                    }
                }
            }
        }
    }
    out
}

/// Percent-encode an SVG document for a `data:image/svg+xml;utf8,` URL.
///
/// Only unreserved characters pass through; everything else (including `#`,
/// `<`, `>`, quotes, whitespace, `/`) is `%XX`-encoded. Verbose but
/// bulletproof across Qt's data-URL parsing.
fn percent_encode(svg: &str) -> String {
    let mut out = String::with_capacity(svg.len() * 2);
    for b in svg.bytes() {
        match b {
            b'A'..=b'Z' | b'a'..=b'z' | b'0'..=b'9' | b'-' | b'_' | b'.' | b'~' => {
                out.push(b as char)
            }
            _ => out.push_str(&format!("%{b:02X}")),
        }
    }
    out
}

/// Tinted `data:image/svg+xml;utf8,...` URL for `name` at `color`.
///
/// Suitable as a QML `Image.source`. Returns `None` for unknown icon names
/// (mirroring the provider's null-icon fallback — callers show no glyph).
pub fn icon_data_url(name: &str, color: &str) -> Option<String> {
    let svg = icon_source(name)?;
    let tint = normalize_tint(color);
    let tinted = tint_svg(svg, &tint);
    Some(format!("data:image/svg+xml;utf8,{}", percent_encode(&tinted)))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn all_twelve_icons_load() {
        assert_eq!(icon_names().len(), 12);
        for name in icon_names() {
            assert!(icon_source(name).is_some(), "missing: {name}");
        }
    }

    #[test]
    fn names_are_case_insensitive() {
        assert_eq!(icon_source("PIN"), icon_source("pin"));
        assert_eq!(icon_source("Close_Tab"), icon_source("close_tab"));
    }

    #[test]
    fn minimize_aliases_restore() {
        assert_eq!(icon_source("minimize"), icon_source("restore"));
    }

    #[test]
    fn unknown_icon_is_none() {
        assert_eq!(icon_source("nope"), None);
        assert_eq!(icon_data_url("nope", "#ffffff"), None);
    }

    #[test]
    fn current_color_svg_tints() {
        let svg = icon_source("close").unwrap();
        assert!(svg.contains("currentColor"));
        let tinted = tint_svg(svg, "#ff0000");
        assert!(!tinted.contains("currentColor"));
        assert!(tinted.contains("#ff0000"));
    }

    #[test]
    fn explicit_fills_tint_but_none_survives() {
        let svg = r##"<svg><path fill="none" stroke="#123456" d="M0 0h24v24H0z"/><rect fill="#abcdef"/></svg>"##;
        let tinted = tint_svg(svg, "#ff0000");
        assert!(tinted.contains(r#"fill="none""#));
        assert!(!tinted.contains("#123456"));
        assert!(!tinted.contains("#abcdef"));
        assert_eq!(tinted.matches("#ff0000").count(), 2);
    }

    #[test]
    fn argb_tint_drops_alpha_like_qcolor_name() {
        assert_eq!(normalize_tint("#80ff0000"), "#ff0000");
        assert_eq!(normalize_tint("#ff0000"), "#ff0000");
    }

    #[test]
    fn data_url_is_safe_and_prefixed() {
        let url = icon_data_url("pin", "#c8cdd7").unwrap();
        assert!(url.starts_with("data:image/svg+xml;utf8,"));
        // No raw characters that break data-URL parsing may survive.
        for raw in ['<', '>', '"', '#', ' ', '\n'] {
            assert!(!url.contains(raw), "raw {raw:?} in url");
        }
        assert!(url.contains("%23c8cdd7"));
    }
}
