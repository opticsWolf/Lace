//! `LaceManager` — Rust-owned layout state behind the QML shell.
//!
//! The manager holds a [`LayoutDoc`] and applies the pure [`layout_ops`]
//! mutations. QML renders the `layout_json` snapshot and calls the
//! invokables; structural ops re-emit `layoutJsonChanged` (full rebuild),
//! while `setCurrentTab` only syncs the document silently — the acting view
//! already updated itself, and a rebuild would drop tab-local state such as
//! typed text.
//!
//! Shape notes: no bridge namespace (it would mis-qualify the `QString`
//! alias), `#[namespace]` on the type, explicit `#[cxx_name]` for camelCase
//! QML methods — all per the upstream `qml_minimal` example.

#[cxx_qt::bridge]
pub mod ffi {
    unsafe extern "C++" {
        include!("cxx-qt-lib/qstring.h");
        /// An alias to the QString type.
        type QString = cxx_qt_lib::QString;
    }

    extern "RustQt" {
        #[qobject]
        #[qml_element]
        #[qproperty(i32, counter)]
        #[qproperty(QString, theme)]
        #[qproperty(QString, layout_json)]
        #[qproperty(QString, last_error)]
        #[qproperty(QString, theme_name)]
        #[qproperty(QString, theme_json)]
        #[qproperty(QString, focused_area)]
        #[namespace = "lace"]
        type LaceManager = super::LaceManagerRust;

        /// Bump the hello counter (Phase 0 demo API, kept working).
        #[qinvokable]
        fn increment(self: Pin<&mut Self>);

        /// Store the active theme name (Phase 0: no theme engine wired yet).
        #[qinvokable]
        #[cxx_name = "applyTheme"]
        fn apply_theme(self: Pin<&mut Self>, name: &QString);

        /// Dock `name` at `edge` (`left|right|top|bottom|center|float`) of
        /// `target_path` (`"0/1/2"` child indices, empty = first area).
        #[qinvokable]
        #[cxx_name = "dockWidget"]
        fn dock_widget(
            self: Pin<&mut Self>,
            name: &QString,
            edge: &QString,
            target_path: &QString,
            closed: bool,
        ) -> bool;

        /// Forget `name` entirely.
        #[qinvokable]
        #[cxx_name = "removeWidget"]
        fn remove_widget(self: Pin<&mut Self>, name: &QString) -> bool;

        /// Flip a widget's closed flag (re-emits: other views show it).
        #[qinvokable]
        #[cxx_name = "setWidgetClosed"]
        fn set_widget_closed(self: Pin<&mut Self>, name: &QString, closed: bool) -> bool;

        /// Point an area's current tab at `name`. Silent: the acting view
        /// already switched; only the document is synced.
        #[qinvokable]
        #[cxx_name = "setCurrentTab"]
        fn set_current_tab(
            self: Pin<&mut Self>,
            container_index: i32,
            area_path: &QString,
            name: &QString,
        ) -> bool;

        /// Tear `name` out into a new float. Returns the container id, or
        /// empty on failure (see `last_error`).
        #[qinvokable]
        #[cxx_name = "floatWidget"]
        fn float_widget(self: Pin<&mut Self>, name: &QString) -> QString;

        /// Bring a floating container's widgets back to the main container.
        #[qinvokable]
        #[cxx_name = "dockFloating"]
        fn dock_floating(self: Pin<&mut Self>, container_id: &QString) -> bool;

        /// Replace the whole layout after validating it (nothing is applied
        /// on failure).
        #[qinvokable]
        #[cxx_name = "applyLayout"]
        fn apply_layout(self: Pin<&mut Self>, json: &QString) -> bool;

        /// Build the Tier-0 demo layout (tabs + split + float).
        #[qinvokable]
        #[cxx_name = "seedDemo"]
        fn seed_demo(self: Pin<&mut Self>);

        /// Switch the active preset (`themeJson` follows). Unknown names fail.
        #[qinvokable]
        #[cxx_name = "applyThemeName"]
        fn apply_theme_name(self: Pin<&mut Self>, name: &QString) -> bool;

        /// Preset catalogue for menus (`preset_keys`: `"default"` first).
        #[qinvokable]
        #[cxx_name = "presetCount"]
        fn preset_count(&self) -> i32;

        /// Empty when `index` is out of range.
        #[qinvokable]
        #[cxx_name = "presetNameAt"]
        fn preset_name_at(&self, index: i32) -> QString;

        /// Pin `name` to the auto-hide sidebar `area`.
        #[qinvokable]
        #[cxx_name = "pinWidget"]
        fn pin_widget(self: Pin<&mut Self>, name: &QString, area: &QString) -> bool;

        /// Return a pinned widget to the main container.
        #[qinvokable]
        #[cxx_name = "unpinWidget"]
        fn unpin_widget(self: Pin<&mut Self>, name: &QString) -> bool;
    }
}

use core::pin::Pin;

use cxx_qt::CxxQtType;
use cxx_qt_lib::QString;
use lace_core::layout_doc::LayoutDoc;
use lace_core::layout_ops::{self, DockEdge, blank_doc};

pub struct LaceManagerRust {
    counter: i32,
    theme: QString,
    layout_json: QString,
    last_error: QString,
    theme_name: QString,
    theme_json: QString,
    focused_area: QString,
    doc: LayoutDoc,
}

fn render_theme(name: &str) -> Result<QString, String> {
    lace_core::style::render_merged_theme(name)
        .map(|json| QString::from(json.as_str()))
}

impl Default for LaceManagerRust {
    fn default() -> Self {
        let doc = blank_doc(0);
        let layout_json = render(&doc).expect("blank doc renders");
        let theme_json = render_theme("default").expect("default theme builds");
        LaceManagerRust {
            counter: 0,
            theme: QString::from(""),
            layout_json,
            last_error: QString::from(""),
            theme_name: QString::from("default"),
            theme_json,
            focused_area: QString::from(""),
            doc,
        }
    }
}

fn render(doc: &LayoutDoc) -> Result<QString, String> {
    doc.render(false)
        .map(|json| QString::from(json.as_str()))
        .map_err(|e| e.to_string())
}

fn parse_path(raw: &str) -> Option<Vec<usize>> {
    if raw.is_empty() {
        return Some(Vec::new());
    }
    raw.split('/').map(|part| part.parse::<usize>().ok()).collect()
}

impl ffi::LaceManager {
    /// Refresh the snapshot and emit `layoutJsonChanged` via the setter.
    fn sync_emit(mut self: Pin<&mut Self>) -> bool {
        match render(&self.as_mut().rust_mut().doc) {
            Ok(rendered) => {
                self.as_mut().set_layout_json(rendered);
                true
            }
            Err(e) => self.fail(e),
        }
    }

    /// Refresh the snapshot silently (no `layoutJsonChanged`).
    fn sync_silent(mut self: Pin<&mut Self>) -> bool {
        match render(&self.as_mut().rust_mut().doc) {
            Ok(rendered) => {
                self.as_mut().rust_mut().layout_json = rendered;
                true
            }
            Err(e) => self.fail(e),
        }
    }

    fn fail(mut self: Pin<&mut Self>, message: String) -> bool {
        self.as_mut().set_last_error(QString::from(message.as_str()));
        false
    }

    fn increment(mut self: Pin<&mut Self>) {
        let next = self.as_ref().counter() + 1;
        self.as_mut().set_counter(next);
    }

    fn apply_theme(mut self: Pin<&mut Self>, name: &QString) {
        let owned: QString = name.clone();
        self.as_mut().set_theme(owned);
    }

    fn dock_widget(
        mut self: Pin<&mut Self>,
        name: &QString,
        edge: &QString,
        target_path: &QString,
        closed: bool,
    ) -> bool {
        let edge = match DockEdge::parse(String::from(edge).as_str()) {
            Some(edge) => edge,
            None => return self.fail(format!("unknown edge `{edge}`")),
        };
        let path = match parse_path(String::from(target_path).as_str()) {
            Some(path) => path,
            None => return self.fail(format!("bad area path `{target_path}`")),
        };
        // An empty path means "the main container's first area", resolved
        // inside the op; anything else is container 0 by construction.
        let target = if path.is_empty() { None } else { Some((0, path)) };
        let name = String::from(name);
        if let Err(e) = layout_ops::dock_widget(
            &mut self.as_mut().rust_mut().doc,
            name.as_str(),
            edge,
            target,
            closed,
        ) {
            return self.fail(e.to_string());
        }
        self.sync_emit()
    }

    fn remove_widget(mut self: Pin<&mut Self>, name: &QString) -> bool {
        let name = String::from(name);
        if !layout_ops::remove_widget(&mut self.as_mut().rust_mut().doc, name.as_str()) {
            return self.fail(format!("no widget `{name}`"));
        }
        self.sync_emit()
    }

    fn set_widget_closed(mut self: Pin<&mut Self>, name: &QString, closed: bool) -> bool {
        let name = String::from(name);
        if !layout_ops::set_closed(&mut self.as_mut().rust_mut().doc, name.as_str(), closed) {
            return self.fail(format!("no widget `{name}`"));
        }
        self.sync_emit()
    }

    fn set_current_tab(
        mut self: Pin<&mut Self>,
        container_index: i32,
        area_path: &QString,
        name: &QString,
    ) -> bool {
        let path = match parse_path(String::from(area_path).as_str()) {
            Some(path) => path,
            None => return self.fail(format!("bad area path `{area_path}`")),
        };
        let name = String::from(name);
        let container_index = match usize::try_from(container_index) {
            Ok(index) => index,
            Err(_) => return self.fail(format!("bad container index {container_index}")),
        };
        if let Err(e) = layout_ops::set_current(
            &mut self.as_mut().rust_mut().doc,
            container_index,
            &path,
            name.as_str(),
        ) {
            return self.fail(e.to_string());
        }
        // Silent on purpose (see module docs).
        self.sync_silent()
    }

    fn float_widget(mut self: Pin<&mut Self>, name: &QString) -> QString {
        let name = String::from(name);
        match layout_ops::float_widget(&mut self.as_mut().rust_mut().doc, name.as_str()) {
            Ok(id) => {
                if self.sync_emit() {
                    QString::from(id.as_str())
                } else {
                    QString::from("")
                }
            }
            Err(e) => {
                self.as_mut().set_last_error(QString::from(e.to_string().as_str()));
                QString::from("")
            }
        }
    }

    fn dock_floating(mut self: Pin<&mut Self>, container_id: &QString) -> bool {
        let id = String::from(container_id);
        if let Err(e) = layout_ops::dock_floating(&mut self.as_mut().rust_mut().doc, id.as_str())
        {
            return self.fail(e.to_string());
        }
        self.sync_emit()
    }

    fn apply_layout(mut self: Pin<&mut Self>, json: &QString) -> bool {
        let text = String::from(json);
        let mut doc = match LayoutDoc::parse(text.as_str()) {
            Ok(doc) => doc,
            Err(e) => return self.fail(e.to_string()),
        };
        let roster: std::collections::HashSet<String> =
            doc.widget_states.keys().cloned().collect();
        let app_version = doc.version;
        if let Err(e) = lace_core::layout_doc::validate_doc(&mut doc, app_version, &roster) {
            return self.fail(e.to_string());
        }
        self.as_mut().rust_mut().doc = doc;
        self.sync_emit()
    }

    fn seed_demo(mut self: Pin<&mut Self>) {
        let doc = &mut self.as_mut().rust_mut().doc;
        *doc = blank_doc(0);
        // Failures are impossible on a blank doc with default targets.
        layout_ops::dock_widget(doc, "Alpha", DockEdge::Center, None, false).expect("seed");
        layout_ops::dock_widget(doc, "Beta", DockEdge::Center, None, false).expect("seed");
        layout_ops::dock_widget(doc, "Gamma", DockEdge::Center, None, false).expect("seed");
        layout_ops::dock_widget(doc, "Delta", DockEdge::Bottom, None, false).expect("seed");
        layout_ops::dock_widget(doc, "Epsilon", DockEdge::Float, None, false).expect("seed");
        self.as_mut().set_focused_area(QString::from(""));
        self.sync_emit();
    }

    fn apply_theme_name(mut self: Pin<&mut Self>, name: &QString) -> bool {
        let name = String::from(name);
        let rendered = match render_theme(name.as_str()) {
            Ok(rendered) => rendered,
            Err(e) => return self.fail(e),
        };
        self.as_mut().set_theme_name(QString::from(name.as_str()));
        self.as_mut().set_theme_json(rendered);
        true
    }

    fn preset_count(&self) -> i32 {
        lace_core::presets_generated::preset_keys().len() as i32
    }

    fn preset_name_at(&self, index: i32) -> QString {
        usize::try_from(index)
            .ok()
            .and_then(|i| lace_core::presets_generated::preset_keys().get(i).copied())
            .map(QString::from)
            .unwrap_or_else(|| QString::from(""))
    }

    fn pin_widget(mut self: Pin<&mut Self>, name: &QString, area: &QString) -> bool {
        let (name, area) = (String::from(name), String::from(area));
        if let Err(e) =
            layout_ops::pin_widget(&mut self.as_mut().rust_mut().doc, name.as_str(), area.as_str())
        {
            return self.fail(e.to_string());
        }
        self.sync_emit()
    }

    fn unpin_widget(mut self: Pin<&mut Self>, name: &QString) -> bool {
        let name = String::from(name);
        if let Err(e) = layout_ops::unpin_widget(&mut self.as_mut().rust_mut().doc, name.as_str())
        {
            return self.fail(e.to_string());
        }
        self.sync_emit()
    }
}
