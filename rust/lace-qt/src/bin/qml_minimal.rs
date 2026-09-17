//! Phase-0 hello: boot a `QGuiApplication`, load `qml/Main.qml` from the
//! compiled-in `com.lace.dock` module resources, run the event loop.
//! Pass `--smoke` for the headless CI check (the QML `Timer` quits).
//!
//! Note: QML `Qt.quit()` only *emits* the engine's `quit` signal — the C++
//! side must act on it, so `on_quit` terminates the process here.
//!
//! The bridge is compiled into this binary (same pattern as upstream
//! `cargo_without_cmake`): that is what pulls the generated C++ and the
//! static QML plugin into the final link on MSVC.

#[path = "../manager.rs"]
mod manager;

use cxx_qt::casting::Upcast;
use cxx_qt_lib::{QGuiApplication, QQmlApplicationEngine, QQmlEngine, QUrl};
use std::pin::Pin;

fn main() {
    let mut app = QGuiApplication::new();
    let mut engine = QQmlApplicationEngine::new();

    if let Some(engine) = engine.as_mut() {
        // Belt and braces: make sure QML errors reach stderr.
        let engine: Pin<&mut QQmlEngine> = engine.upcast_pin();
        engine.set_output_warnings_to_standard_error(true);
    }

    if let Some(engine) = engine.as_mut() {
        engine
            .on_object_created(|_, obj, url| {
                println!(
                    "lace qml_minimal: object_created null={} url={}",
                    obj.is_null(),
                    String::from(&url.to_string()),
                );
            })
            .release();
    }

    if let Some(engine) = engine.as_mut() {
        engine
            .on_object_creation_failed(|_, url| {
                println!(
                    "lace qml_minimal: object_creation_failed url={}",
                    String::from(&url.to_string()),
                );
            })
            .release();
    }

    if let Some(engine) = engine.as_mut() {
        // LACE_QML_FILE overrides the embedded resource (diagnostics).
        let url = match std::env::var("LACE_QML_FILE") {
            Ok(path) => {
                println!("lace qml_minimal: loading from file {path}");
                QUrl::from_local_file(&cxx_qt_lib::QString::from(path.as_str()))
            }
            Err(_) => QUrl::from("qrc:/qt/qml/com/lace/dock/qml/Main.qml"),
        };
        engine.load(&url);
        // A failed load prints Qt warnings; the `--smoke` quit Timer then
        // never fires, so the runner times out instead of exiting 0.
        println!("lace qml_minimal: QML load requested");
    }

    if let Some(engine) = engine.as_mut() {
        let engine: Pin<&mut QQmlEngine> = engine.upcast_pin();
        engine
            .on_quit(|_| {
                println!("lace qml_minimal: engine quit requested");
                std::process::exit(0);
            })
            .release();
    }

    let smoke = std::env::args().any(|a| a == "--smoke");
    println!("lace qml_minimal: smoke={smoke}");

    if let Some(app) = app.as_mut() {
        println!("lace qml_minimal: entering event loop");
        let code = app.exec();
        println!("lace qml_minimal: event loop exited code={code}");
    }
}
