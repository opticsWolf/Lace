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
        #[qproperty(QString, layout_json, cxx_name = "layoutJson")]
        #[qproperty(QString, last_error, cxx_name = "lastError")]
        #[qproperty(QString, theme_name, cxx_name = "themeName")]
        #[qproperty(QString, theme_json, cxx_name = "themeJson")]
        #[qproperty(QString, focused_area, cxx_name = "focusedArea")]
        #[qproperty(bool, drag_active, cxx_name = "dragActive")]
        #[qproperty(QString, drag_target_key, cxx_name = "dragTargetKey")]
        #[qproperty(QString, maximized_area, cxx_name = "maximizedArea")]
        /// `DockFlags` bitmask driving chrome visibility (buttons, tab
        /// close affordances, tabs menu). Initialized to `default_config`.
        #[qproperty(i32, dock_flags, cxx_name = "dockFlags")]
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

        /// Overwrite a splitter node's size weights after a handle drag.
        /// Silent like `setCurrentTab`: the view already shows the sizes,
        /// the document just catches up (so save/restore round-trips them).
        #[qinvokable]
        #[cxx_name = "setSplitterSizes"]
        fn set_splitter_sizes(
            self: Pin<&mut Self>,
            container_index: i32,
            area_path: &QString,
            sizes_json: &QString,
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

        /// Build the showcase layout (editors, outline, output + toolbox).
        #[qinvokable]
        #[cxx_name = "seedShowcase"]
        fn seed_showcase(self: Pin<&mut Self>);

        /// Save the current layout to the demo slot (temp dir).
        #[qinvokable]
        #[cxx_name = "saveDemoLayout"]
        fn save_demo_layout(self: Pin<&mut Self>) -> bool;

        /// Load the demo slot back (validates first; keeps current on failure).
        #[qinvokable]
        #[cxx_name = "loadDemoLayout"]
        fn load_demo_layout(self: Pin<&mut Self>) -> bool;

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

        /// Close every tab in one area (the title-bar close button with
        /// `dock_area_close_button_closes_tab` cleared). Closed tabs keep
        /// their slots with reopen affordances.
        #[qinvokable]
        #[cxx_name = "closeArea"]
        fn close_area(
            self: Pin<&mut Self>,
            container_index: i32,
            area_path: &QString,
        ) -> bool;
        /// Return a pinned widget to the main container.
        #[qinvokable]
        #[cxx_name = "unpinWidget"]
        fn unpin_widget(self: Pin<&mut Self>, name: &QString) -> bool;

        /// Zones a container offers (`"left,right,top,bottom,center"`,
        /// `"center"` for solo areas, empty when unknown).
        #[qinvokable]
        #[cxx_name = "dropEdges"]
        fn drop_edges(&self, container_index: i32) -> QString;

        /// Start dragging `name` (title-bar press-and-hold).
        #[qinvokable]
        #[cxx_name = "beginDrag"]
        fn begin_drag(self: Pin<&mut Self>, name: &QString) -> bool;

        /// Hover an area zone while dragging (drives the highlight).
        #[qinvokable]
        #[cxx_name = "overSectionDrop"]
        fn over_section_drop(
            self: Pin<&mut Self>,
            container_index: i32,
            area_path: &QString,
            edge: &QString,
        ) -> bool;

        /// Hover a container-cross zone while dragging.
        #[qinvokable]
        #[cxx_name = "overContainerDrop"]
        fn over_container_drop(self: Pin<&mut Self>, container_index: i32, zone: &QString) -> bool;

        /// Drop onto an area zone (also works without a prior hover).
        #[qinvokable]
        #[cxx_name = "commitSectionDrop"]
        fn commit_section_drop(
            self: Pin<&mut Self>,
            container_index: i32,
            area_path: &QString,
            edge: &QString,
        ) -> bool;

        /// Drop onto a container-cross zone.
        #[qinvokable]
        #[cxx_name = "commitContainerDrop"]
        fn commit_container_drop(
            self: Pin<&mut Self>,
            container_index: i32,
            zone: &QString,
        ) -> bool;

        /// Give up the drag.
        #[qinvokable]
        #[cxx_name = "cancelDrag"]
        fn cancel_drag(self: Pin<&mut Self>);

        /// Clear the hover highlight without ending the session (the
        /// pointer left every zone mid-drag).
        #[qinvokable]
        #[cxx_name = "clearDragTarget"]
        fn clear_drag_target(self: Pin<&mut Self>);

        /// Maximize an area (`"<container>/<path>"`); repeat or `""` to
        /// restore. Never reshapes the tree — siblings just hide.
        #[qinvokable]
        #[cxx_name = "toggleMaximize"]
        fn toggle_maximize(self: Pin<&mut Self>, key: &QString) -> bool;
    }
}

use core::pin::Pin;

use cxx_qt::CxxQtType;
use cxx_qt_lib::QString;
use lace_core::layout_doc::LayoutDoc;
use lace_core::layout_ops::{self, DockEdge, DragSession, DropTarget, blank_doc};

pub struct LaceManagerRust {
    counter: i32,
    theme: QString,
    layout_json: QString,
    last_error: QString,
    theme_name: QString,
    theme_json: QString,
    focused_area: QString,
    drag_active: bool,
    drag_target_key: QString,
    maximized_area: QString,
    dock_flags: i32,
    doc: LayoutDoc,
    drag: DragSession,
}

fn render_theme(name: &str) -> Result<QString, String> {    lace_core::style::render_merged_theme(name)
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
            drag_active: false,
            drag_target_key: QString::from(""),
            maximized_area: QString::from(""),
            dock_flags: lace_core::config::DockFlags::DEFAULT_CONFIG.bits() as i32,
            doc,
            drag: DragSession::default(),
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

impl LaceManagerRust {
    /// Commit the active drag session against the live document.
    /// Disjoint field borrows, so the bridge never fights the checker.
    fn commit_drag(&mut self) -> Result<(), String> {
        self.drag.commit(&mut self.doc).map_err(|e| e.to_string())
    }
}

impl ffi::LaceManager {
    /// Refresh the snapshot and emit `layoutJsonChanged` via the setter.
    fn sync_emit(mut self: Pin<&mut Self>) -> bool {
        match render(&self.as_mut().rust_mut().doc) {
            Ok(rendered) => {
                self.as_mut().set_layout_json(rendered);
                // A success clears any earlier failure message (the status
                // label would otherwise show stale errors forever).
                self.as_mut().set_last_error(QString::from(""));
                true
            }
            Err(e) => self.as_mut().fail(e),
        }
    }

    /// Refresh the snapshot silently (no `layoutJsonChanged`).
    fn sync_silent(mut self: Pin<&mut Self>) -> bool {
        match render(&self.as_mut().rust_mut().doc) {
            Ok(rendered) => {
                self.as_mut().rust_mut().layout_json = rendered;
                self.as_mut().set_last_error(QString::from(""));
                true
            }
            Err(e) => self.as_mut().fail(e),
        }
    }

    fn fail(mut self: Pin<&mut Self>, message: String) -> bool {
        self.as_mut().set_last_error(QString::from(message.as_str()));
        false
    }

    /// A structural change invalidates maximize (paths shift). Called by
    /// every reshaping op; centre-tabs and flag flips keep it.
    fn note_reshaped(mut self: Pin<&mut Self>) {
        if !String::from(self.as_ref().maximized_area()).is_empty() {
            self.as_mut().set_maximized_area(QString::from(""));
        }
    }

    fn clear_drag(mut self: Pin<&mut Self>) {
        self.as_mut().set_drag_active(false);
        self.as_mut().set_drag_target_key(QString::from(""));
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
            None => return self.as_mut().fail(format!("unknown edge `{edge}`")),
        };
        let path = match parse_path(String::from(target_path).as_str()) {
            Some(path) => path,
            None => return self.as_mut().fail(format!("bad area path `{target_path}`")),
        };
        // An empty path means "the main container's first area", resolved
        // inside the op; anything else is container 0 by construction.
        let target = if path.is_empty() { None } else { Some((0, path)) };
        let name = String::from(name);
        // Centre-tabs into a live area never reshape, so maximize survives
        // them (mirrors the drop path); everything else restores first.
        let keep_max = edge == DockEdge::Center && {
            let main = self.as_mut().rust_mut().doc.containers.iter().position(|c| c.is_main);
            match (main, &target) {
                (Some(m), None) => {
                    lace_core::layout_ops::area_paths(&self.as_mut().rust_mut().doc)
                        .iter()
                        .any(|(ci, _)| *ci == m)
                }
                (_, Some((ci, p))) => {
                    lace_core::layout_ops::area_paths(&self.as_mut().rust_mut().doc)
                        .contains(&(*ci, p.clone()))
                }
                _ => false,
            }
        };
        if let Err(e) = layout_ops::dock_widget(
            &mut self.as_mut().rust_mut().doc,
            name.as_str(),
            edge,
            target,
            closed,
        ) {
            return self.as_mut().fail(e.to_string());
        }
        if !keep_max {
            self.as_mut().note_reshaped();
        }
        self.as_mut().sync_emit()
    }

    fn remove_widget(mut self: Pin<&mut Self>, name: &QString) -> bool {
        let name = String::from(name);
        if !layout_ops::remove_widget(&mut self.as_mut().rust_mut().doc, name.as_str()) {
            return self.as_mut().fail(format!("no widget `{name}`"));
        }
        self.as_mut().note_reshaped();
        self.as_mut().sync_emit()
    }

    fn set_widget_closed(mut self: Pin<&mut Self>, name: &QString, closed: bool) -> bool {
        let name = String::from(name);
        if !layout_ops::set_closed(&mut self.as_mut().rust_mut().doc, name.as_str(), closed) {
            return self.as_mut().fail(format!("no widget `{name}`"));
        }
        self.as_mut().sync_emit()
    }

    fn close_area(
        mut self: Pin<&mut Self>,
        container_index: i32,
        area_path: &QString,
    ) -> bool {
        let path = match parse_path(String::from(area_path).as_str()) {
            Some(path) => path,
            None => return self.as_mut().fail(format!("bad area path `{area_path}`")),
        };
        let container_index = match usize::try_from(container_index) {
            Ok(index) => index,
            Err(_) => return self.as_mut().fail(format!("bad container index {container_index}")),
        };
        if let Err(e) = layout_ops::close_area(
            &mut self.as_mut().rust_mut().doc,
            container_index,
            &path,
        ) {
            return self.as_mut().fail(e.to_string());
        }
        self.as_mut().sync_emit()
    }

    fn set_current_tab(
        mut self: Pin<&mut Self>,
        container_index: i32,
        area_path: &QString,
        name: &QString,
    ) -> bool {
        let path = match parse_path(String::from(area_path).as_str()) {
            Some(path) => path,
            None => return self.as_mut().fail(format!("bad area path `{area_path}`")),
        };
        let name = String::from(name);
        let container_index = match usize::try_from(container_index) {
            Ok(index) => index,
            Err(_) => return self.as_mut().fail(format!("bad container index {container_index}")),
        };
        if let Err(e) = layout_ops::set_current(
            &mut self.as_mut().rust_mut().doc,
            container_index,
            &path,
            name.as_str(),
        ) {
            return self.as_mut().fail(e.to_string());
        }
        // Silent on purpose (see module docs).
        self.as_mut().sync_silent()
    }

    fn set_splitter_sizes(
        mut self: Pin<&mut Self>,
        container_index: i32,
        area_path: &QString,
        sizes_json: &QString,
    ) -> bool {
        let path = match parse_path(String::from(area_path).as_str()) {
            Some(path) => path,
            None => return self.as_mut().fail(format!("bad area path `{area_path}`")),
        };
        let sizes: Vec<f64> = match serde_json::from_str(String::from(sizes_json).as_str()) {
            Ok(sizes) => sizes,
            Err(_) => {
                return self
                    .as_mut()
                    .fail("splitter sizes must be a JSON number array".to_string())
            }
        };
        let container_index = match usize::try_from(container_index) {
            Ok(index) => index,
            Err(_) => return self.as_mut().fail(format!("bad container index {container_index}")),
        };
        if let Err(e) = layout_ops::set_splitter_sizes(
            &mut self.as_mut().rust_mut().doc,
            container_index,
            &path,
            &sizes,
        ) {
            return self.as_mut().fail(e.to_string());
        }
        // Silent on purpose (see the bridge docs).
        self.as_mut().sync_silent()
    }

    fn float_widget(mut self: Pin<&mut Self>, name: &QString) -> QString {
        let name = String::from(name);
        match layout_ops::float_widget(&mut self.as_mut().rust_mut().doc, name.as_str()) {
            Ok(id) => {
                self.as_mut().note_reshaped();
                if self.as_mut().sync_emit() {
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
            return self.as_mut().fail(e.to_string());
        }
        self.as_mut().note_reshaped();
        self.as_mut().sync_emit()
    }

    fn apply_layout(mut self: Pin<&mut Self>, json: &QString) -> bool {
        let text = String::from(json);
        let mut doc = match LayoutDoc::parse(text.as_str()) {
            Ok(doc) => doc,
            Err(e) => return self.as_mut().fail(e.to_string()),
        };
        let roster: std::collections::HashSet<String> =
            doc.widget_states.keys().cloned().collect();
        let app_version = doc.version;
        if let Err(e) = lace_core::layout_doc::validate_doc(&mut doc, app_version, &roster) {
            return self.as_mut().fail(e.to_string());
        }
        self.as_mut().rust_mut().doc = doc;
        self.as_mut().note_reshaped();
        self.as_mut().sync_emit()
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
        self.as_mut().sync_emit();
    }

    fn apply_theme_name(mut self: Pin<&mut Self>, name: &QString) -> bool {
        let name = String::from(name);
        let rendered = match render_theme(name.as_str()) {
            Ok(rendered) => rendered,
            Err(e) => return self.as_mut().fail(e),
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
            return self.as_mut().fail(e.to_string());
        }
        self.as_mut().note_reshaped();
        self.as_mut().sync_emit()
    }

    fn unpin_widget(mut self: Pin<&mut Self>, name: &QString) -> bool {
        let name = String::from(name);
        if let Err(e) = layout_ops::unpin_widget(&mut self.as_mut().rust_mut().doc, name.as_str())
        {
            return self.as_mut().fail(e.to_string());
        }
        self.as_mut().note_reshaped();
        self.as_mut().sync_emit()
    }

    fn parse_container(value: i32) -> Result<usize, String> {
        usize::try_from(value).map_err(|_| format!("bad container index {value}"))
    }

    fn drop_edges(&self, container_index: i32) -> QString {
        match Self::parse_container(container_index) {
            Ok(container) => {
                let edges = layout_ops::drop_edges(&self.rust().doc, container);
                let names = ["left", "right", "top", "bottom", "center"];
                let offered: Vec<&str> = edges
                    .iter()
                    .map(|edge| match edge {
                        DockEdge::Left => names[0],
                        DockEdge::Right => names[1],
                        DockEdge::Top => names[2],
                        DockEdge::Bottom => names[3],
                        DockEdge::Center => names[4],
                        DockEdge::Float => "float",
                    })
                    .collect();
                QString::from(offered.join(",").as_str())
            }
            Err(_) => QString::from(""),
        }
    }

    fn begin_drag(mut self: Pin<&mut Self>, name: &QString) -> bool {
        let name = String::from(name);
        if name.is_empty() {
            return self.as_mut().fail("cannot drag an unnamed widget".to_string());
        }
        self.as_mut().rust_mut().drag.begin(name.as_str());
        self.as_mut().set_drag_active(true);
        true
    }

    fn section_key(container: usize, path: &[usize], edge: DockEdge) -> String {
        let edge_name = match edge {
            DockEdge::Left => "left",
            DockEdge::Right => "right",
            DockEdge::Top => "top",
            DockEdge::Bottom => "bottom",
            DockEdge::Center => "center",
            DockEdge::Float => "float",
        };
        let path = path.iter().map(usize::to_string).collect::<Vec<_>>().join("/");
        format!("S:{container}/{path}/{edge_name}")
    }

    fn over_section_drop(
        mut self: Pin<&mut Self>,
        container_index: i32,
        area_path: &QString,
        edge: &QString,
    ) -> bool {
        if !self.as_ref().drag_active() {
            return false;
        }
        let container = match Self::parse_container(container_index) {
            Ok(container) => container,
            Err(e) => return self.as_mut().fail(e),
        };
        let path = match parse_path(String::from(area_path).as_str()) {
            Some(path) => path,
            None => return self.as_mut().fail(format!("bad area path `{area_path}`")),
        };
        let edge = match DockEdge::parse(String::from(edge).as_str()) {
            Some(DockEdge::Float) | None => return self.as_mut().fail(format!("bad drop edge `{edge}`")),
            Some(edge) => edge,
        };
        self.as_mut().rust_mut().drag.hover(DropTarget::Section {
            container,
            path: path.clone(),
            edge,
        });
        let key = Self::section_key(container, &path, edge);
        self.as_mut().set_drag_target_key(QString::from(key.as_str()));
        true
    }

    fn over_container_drop(
        mut self: Pin<&mut Self>,
        container_index: i32,
        zone: &QString,
    ) -> bool {
        if !self.as_ref().drag_active() {
            return false;
        }
        let container = match Self::parse_container(container_index) {
            Ok(container) => container,
            Err(e) => return self.as_mut().fail(e),
        };
        let edge = match DockEdge::parse(String::from(zone).as_str()) {
            Some(DockEdge::Float) | None => return self.as_mut().fail(format!("bad drop zone `{zone}`")),
            Some(edge) => edge,
        };
        let zone_name = String::from(zone).to_ascii_lowercase();
        self.as_mut().rust_mut().drag.hover(if edge == DockEdge::Center {
            DropTarget::ContainerCenter { container }
        } else {
            DropTarget::ContainerEdge { container, edge }
        });
        let key = format!("C:{container}/{zone_name}");
        self.as_mut().set_drag_target_key(QString::from(key.as_str()));
        true
    }

    fn cancel_drag(mut self: Pin<&mut Self>) {
        self.as_mut().rust_mut().drag.cancel();
        self.as_mut().clear_drag();
    }

    fn clear_drag_target(mut self: Pin<&mut Self>) {
        self.as_mut().set_drag_target_key(QString::from(""));
    }

    /// Centre-tabs never reshape, so maximize survives them; every other
    /// drop restores (clears) maximize first, mirroring the QWidget path.
    fn finish_drop(mut self: Pin<&mut Self>, center: bool, result: Result<(), String>) -> bool {
        match result {
            Ok(()) => {
                layout_ops::gc_empty_floats(&mut self.as_mut().rust_mut().doc);
                if !center {
                    self.as_mut().note_reshaped();
                }
                self.as_mut().clear_drag();
                self.as_mut().sync_emit()
            }
            Err(e) => {
                self.as_mut().clear_drag();
                self.as_mut().fail(e)
            }
        }
    }

    fn commit_section_drop(
        mut self: Pin<&mut Self>,
        container_index: i32,
        area_path: &QString,
        edge: &QString,
    ) -> bool {
        if !self.as_ref().drag_active() {
            return self.as_mut().fail("no active drag".to_string());
        }
        // Hover-then-commit in one step: fast drops may never send a hover.
        if !self.as_mut().over_section_drop(container_index, area_path, edge) {
            self.cancel_drag();
            return false;
        }
        let center = matches!(
            String::from(edge).to_ascii_lowercase().as_str(),
            "center" | "centre"
        );
        let result = self.as_mut().rust_mut().commit_drag();
        self.finish_drop(center, result)
    }

    fn commit_container_drop(
        mut self: Pin<&mut Self>,
        container_index: i32,
        zone: &QString,
    ) -> bool {
        if !self.as_ref().drag_active() {
            return self.as_mut().fail("no active drag".to_string());
        }
        if !self.as_mut().over_container_drop(container_index, zone) {
            self.cancel_drag();
            return false;
        }
        let center = String::from(zone).to_ascii_lowercase() == "center";
        let solo = {
            let container = Self::parse_container(container_index).unwrap_or(usize::MAX);
            layout_ops::drop_edges(&self.as_mut().rust_mut().doc, container)
                == vec![DockEdge::Center]
        };
        let result = self.as_mut().rust_mut().commit_drag();
        // A solo-container centre is a tab (no reshape); anything else
        // divides and restores maximize first.
        self.finish_drop(center && solo, result)
    }

    fn toggle_maximize(mut self: Pin<&mut Self>, key: &QString) -> bool {
        let key = String::from(key);
        let current = String::from(self.as_ref().maximized_area());
        if key.is_empty() || key == current {
            self.as_mut().set_maximized_area(QString::from(""));
            return true;
        }
        // Validate against the live tree so a stale key cannot hide areas.
        let mut parts = key.split('/');
        let container: usize = match parts.next().and_then(|c| c.parse().ok()) {
            Some(container) => container,
            None => return self.as_mut().fail(format!("bad maximized key `{key}`")),
        };
        let path: Option<Vec<usize>> =
            parts.map(|part| part.parse::<usize>().ok()).collect();
        let path = match path {
            Some(path) => path,
            None => return self.as_mut().fail(format!("bad maximized key `{key}`")),
        };
        let known = layout_ops::area_paths(&self.as_mut().rust_mut().doc)
            .contains(&(container, path));
        if !known {
            return self.as_mut().fail(format!("no area `{key}` to maximize"));
        }
        self.as_mut().set_maximized_area(QString::from(key.as_str()));
        true
    }

    fn seed_showcase(mut self: Pin<&mut Self>) {
        let doc = &mut self.as_mut().rust_mut().doc;
        *doc = blank_doc(0);
        // Failures are impossible on a blank doc with default targets.
        // Top-left tab stack: editors, lists, table.
        layout_ops::dock_widget(doc, "Outline", DockEdge::Center, None, false).expect("seed");
        layout_ops::dock_widget(doc, "Editor", DockEdge::Center, None, false).expect("seed");
        layout_ops::dock_widget(doc, "Notes", DockEdge::Center, None, false).expect("seed");
        layout_ops::dock_widget(doc, "Terminal", DockEdge::Center, None, false).expect("seed");
        layout_ops::dock_widget(doc, "Files", DockEdge::Center, None, false).expect("seed");
        layout_ops::dock_widget(doc, "Search", DockEdge::Center, None, false).expect("seed");
        layout_ops::dock_widget(doc, "Table", DockEdge::Center, None, false).expect("seed");
        // Top-right tab stack: form, canvas, palette, calendar.
        layout_ops::dock_widget(doc, "Properties", DockEdge::Right, None, false).expect("seed");
        for name in ["Plots", "Palette", "Calendar"] {
            layout_ops::dock_widget(doc, name, DockEdge::Center, Some((0, vec![1])), false)
                .expect("seed");
        }
        // Full-width bottom: split the root itself, then tab the console in.
        layout_ops::dock_widget(doc, "Output", DockEdge::Bottom, Some((0, vec![])), false)
            .expect("seed");
        layout_ops::dock_widget(doc, "Console", DockEdge::Center, Some((0, vec![1])), false)
            .expect("seed");
        layout_ops::dock_widget(doc, "Toolbox", DockEdge::Float, None, false).expect("seed");
        self.as_mut().set_focused_area(QString::from(""));
        self.as_mut().sync_emit();
    }

    fn demo_slot() -> std::path::PathBuf {
        std::env::temp_dir().join("lace_demo_layout.json")
    }

    fn save_demo_layout(mut self: Pin<&mut Self>) -> bool {
        let path = Self::demo_slot();
        let dir = match path.parent() {
            Some(parent) => parent.to_path_buf(),
            None => return self.as_mut().fail("no parent for demo slot".to_string()),
        };
        let persist = lace_core::persist::PersistDir::new(dir);
        let name = match path.file_stem().and_then(|s| s.to_str()) {
            Some(name) => name.to_string(),
            None => return self.as_mut().fail("bad demo slot name".to_string()),
        };
        let doc = &self.as_mut().rust_mut().doc;
        // Clone under the borrow: persist takes its time on disk.
        let doc = doc.clone();
        match persist.save_layout(name.as_str(), &doc, true) {
            Ok(()) => true,
            Err(e) => self.as_mut().fail(e.to_string()),
        }
    }

    fn load_demo_layout(mut self: Pin<&mut Self>) -> bool {
        let path = Self::demo_slot();
        let dir = match path.parent() {
            Some(parent) => parent.to_path_buf(),
            None => return self.as_mut().fail("no parent for demo slot".to_string()),
        };
        let persist = lace_core::persist::PersistDir::new(dir);
        let name = match path.file_stem().and_then(|s| s.to_str()) {
            Some(name) => name.to_string(),
            None => return self.as_mut().fail("bad demo slot name".to_string()),
        };
        let mut doc = match persist.load_layout(name.as_str()) {
            Ok(doc) => doc,
            Err(e) => return self.as_mut().fail(e.to_string()),
        };
        // Accept the file's own roster and version; schema/tag still enforced.
        let roster: std::collections::HashSet<String> =
            doc.widget_states.keys().cloned().collect();
        let app_version = doc.version;
        if let Err(e) = lace_core::layout_doc::validate_doc(&mut doc, app_version, &roster) {
            return self.as_mut().fail(e.to_string());
        }
        self.as_mut().rust_mut().doc = doc;
        self.as_mut().note_reshaped();
        self.as_mut().sync_emit()
    }
}
