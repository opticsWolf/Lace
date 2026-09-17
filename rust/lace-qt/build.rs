//! Build script: code-generate and compile the C++ for every
//! `#[cxx_qt::bridge]` module, and register the `com.lace.dock` QML module
//! (the `qt_add_qml_module` equivalent). CXX-Qt locates Qt via the `QMAKE`
//! env var or `qmake` on `PATH` — see `rust/README.md`.

use cxx_qt_build::{CxxQtBuilder, QmlModule};

fn main() {
    CxxQtBuilder::new_qml_module(QmlModule::new("com.lace.dock").qml_file("qml/Main.qml"))
        .files(["src/manager.rs"])
        .build();

    // MSVC discards unreferenced archive members (/OPT:REF), which drops
    // the static QML plugin, the type registrations and the QML resources
    // (plain `-l` archives only pull members for symbols the binary
    // references — the plugin has none from Rust). Force the whole
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
                && (n.contains("-cxxqt-generated") || n.contains("call-init-"))
        })
        .collect();
    archives.sort();
    assert!(
        !archives.is_empty(),
        "expected cxx-qt-build archives in OUT_DIR ({out})"
    );
    for archive in &archives {
        let path = format!("{out}/{archive}");
        if cfg!(target_os = "windows") {
            println!("cargo::rustc-link-arg=/WHOLEARCHIVE:{path}");
        } else {
            println!("cargo::rustc-link-arg=-Wl,--whole-archive,{path}");
            println!("cargo::rustc-link-arg=-Wl,--no-whole-archive");
        }
    }
}
