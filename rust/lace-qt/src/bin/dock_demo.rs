//! Phase-3 Tier-0 demo: the full dock shell (tabs + splits + native-frame
//! floats) driven by `LaceManager`. Pass `--smoke` for the headless CI check.

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
                    "lace dock_demo: object_created null={} url={}",
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
                    "lace dock_demo: object_creation_failed url={}",
                    String::from(&url.to_string()),
                );
            })
            .release();
    }

    if let Some(engine) = engine.as_mut() {
        // LACE_QML_FILE overrides the embedded resource (iterate on the
        // shell without rebuilding).
        let url = match std::env::var("LACE_QML_FILE") {
            Ok(path) => {
                println!("lace dock_demo: loading from file {path}");
                QUrl::from_local_file(&cxx_qt_lib::QString::from(path.as_str()))
            }
            Err(_) => QUrl::from("qrc:/qt/qml/com/lace/dock/qml/Shell.qml"),
        };
        engine.load(&url);
        println!("lace dock_demo: QML load requested");
    }

    if let Some(engine) = engine.as_mut() {
        let engine: Pin<&mut QQmlEngine> = engine.upcast_pin();
        // Log only: the process exit code comes from app.exec(), so a QML
        // Qt.exit(code) verdict (see Shell.qml smoke self-test) survives.
        engine
            .on_quit(|_| {
                println!("lace dock_demo: engine quit requested");
            })
            .release();
    }

    let smoke = std::env::args().any(|a| a == "--smoke");
    println!("lace dock_demo: smoke={smoke}");

    if let Some(app) = app.as_mut() {
        println!("lace dock_demo: entering event loop");
        let code = app.exec();
        println!("lace dock_demo: event loop exited code={code}");
        std::process::exit(code);
    }
}
