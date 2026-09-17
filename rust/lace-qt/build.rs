//! Build script: code-generate and compile the C++ for every
//! `#[cxx_qt::bridge]` module, and register the `com.lace.dock` QML module
//! (the `qt_add_qml_module` equivalent). CXX-Qt locates Qt via the `QMAKE`
//! env var or `qmake` on `PATH` — see `rust/README.md`.
//!
//! It also compiles `cpp/widget_host.cpp` (the Phase-3 QWidget-coexistence
//! spike) and links the Qt Widgets/Quick libraries it needs.

use cxx_qt_build::{CxxQtBuilder, QmlModule};

fn main() {
    CxxQtBuilder::new_qml_module(
        QmlModule::new("com.lace.dock").qml_files([
            "qml/Main.qml",
            "qml/Shell.qml",
            "qml/DockManagerView.qml",
            "qml/ContainerBuilder.qml",
            "qml/SplitterView.qml",
            "qml/AreaView.qml",
            "qml/WidgetCard.qml",
            "qml/FloatingView.qml",
        ]),
    )
    .files(["src/manager.rs"])
    .build();

    // MSVC discards unreferenced static-archive members (/OPT:REF), which
    // drops the static QML plugin, the type registrations and the QML
    // resources (plain `-l` archives only pull members for symbols the
    // binary references — the plugin has none from Rust). Force the whole
    // cxx-qt-build archives into bins/examples/tests via raw linker args.
    // (`rustc-link-arg` skips rlib builds, so the lib target is unaffected.)
    // Linux ld keeps static initializers from archives, so plain `-l` is
    // enough there — but whole-archive is harmless and keeps both linkers
    // on the same behavior, so apply it everywhere.
    let out = std::env::var("OUT_DIR").expect("OUT_DIR is always set");
    // NOTE: OUT_DIR contains both `.lib` and `.a` copies of the same
    // archives — take exactly one variant or every symbol links twice.
    let want_ext = if cfg!(target_os = "windows") { ".lib" } else { ".a" };
    let mut archives: Vec<String> = std::fs::read_dir(&out)
        .expect("OUT_DIR is readable")
        .filter_map(|e| e.ok())
        .map(|e| e.file_name().to_string_lossy().into_owned())
        .filter(|n| {
            n.ends_with(want_ext)
                && (n.contains("-cxxqt-generated")
                    || n.contains("call-init-")
                    || n.contains("lace-widget-host"))
        })
        .collect();
    archives.sort();
    assert!(!archives.is_empty(), "expected cxx-qt-build archives in OUT_DIR ({out})");
    for archive in &archives {
        let path = format!("{out}/{archive}");
        if cfg!(target_os = "windows") {
            println!("cargo::rustc-link-arg=/WHOLEARCHIVE:{path}");
        } else {
            println!("cargo::rustc-link-arg=-Wl,--whole-archive,{path}");
            println!("cargo::rustc-link-arg=-Wl,--no-whole-archive");
        }
    }

    build_widget_host();
}

/// Compile the QWidget-coexistence spike and link what it needs.
fn build_widget_host() {
    let qmake = std::env::var("QMAKE").unwrap_or_else(|_| "qmake".to_string());
    let query = |key: &str| {
        std::process::Command::new(&qmake)
            .args(["-query", key])
            .output()
            .ok()
            .filter(|output| output.status.success())
            .and_then(|output| String::from_utf8(output.stdout).ok())
            .map(|stdout| stdout.trim().to_string())
            .filter(|value| !value.is_empty())
    };
    let (Some(headers), Some(libs)) =
        (query("QT_INSTALL_HEADERS"), query("QT_INSTALL_LIBS"))
    else {
        println!(
            "cargo::warning=widget_host.cpp skipped: Qt not found via qmake; \
             the widget_host bin will not link"
        );
        return;
    };
    let mut cc_build = cc::Build::new();
    cc_build.cpp(true).std("c++17").file("cpp/widget_host.cpp");
    if cfg!(target_os = "windows") {
        // Qt demands a correct __cplusplus and conformant mode on MSVC.
        cc_build.flag("/Zc:__cplusplus");
        cc_build.flag("/permissive-");
    }
    // Like qmake: the base dir plus each module dir (aqtinstall ships no
    // top-level forward headers).
    cc_build.include(&headers);
    for module in ["QtWidgets", "QtQuick", "QtGui", "QtCore", "QtQml"] {
        cc_build.include(format!("{headers}/{module}"));
    }
    cc_build.compile("lace-widget-host");
    // Full library paths as raw linker args: unlike `rustc-link-lib` these
    // reach every bin of this package without a dependency edge (bins that
    // only `use cxx_qt_lib` never see build-script `-l` directives).
    if cfg!(target_os = "windows") {
        for lib in ["Qt6Widgets", "Qt6Quick"] {
            println!("cargo::rustc-link-arg={libs}/{lib}.lib");
        }
    } else {
        for lib in ["Qt6Widgets", "Qt6Quick"] {
            println!("cargo::rustc-link-search=native={libs}");
            println!("cargo::rustc-link-arg=-l{lib}");
        }
    }
}
