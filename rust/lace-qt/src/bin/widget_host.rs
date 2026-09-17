//! Phase-3 QWidget-coexistence spike: one native frame holding a `QTextEdit`
//! beside a QML scene. The window is built in `cpp/widget_host.cpp`; this
//! binary only forwards argv and the panel path. Pass `--smoke` for the
//! headless CI check (the C++ side quits after ~1.5 s).

use std::ffi::CString;
use std::os::raw::{c_char, c_int};

extern "C" {
    fn run_widget_host(
        argc: c_int,
        argv: *mut *mut c_char,
        qml_path: *const c_char,
        smoke: bool,
    ) -> c_int;
}

fn main() {
    // Reference the bridge so this bin links the same Qt world as the
    // other lace-qt targets (the whole-archive QML plugin members expect
    // the cxx-qt initializers and Qt libraries to be present).
    let _ = lace_qt::manager::LaceManagerRust::default();

    let smoke = std::env::args().any(|a| a == "--smoke");
    let panel = std::env::var("LACE_WIDGET_QML").unwrap_or_else(|_| {
        format!(
            "{}/qml_widget/HostPanel.qml",
            env!("CARGO_MANIFEST_DIR")
        )
    });
    println!("lace widget_host: panel={panel} smoke={smoke}");

    let arg0 = CString::new(std::env::args().next().unwrap_or_else(|| "widget_host".into()))
        .expect("argv[0] converts");
    let panel_c = CString::new(panel).expect("panel path converts");
    let mut argv = vec![arg0.as_ptr() as *mut c_char];
    let code = unsafe { run_widget_host(1, argv.as_mut_ptr(), panel_c.as_ptr(), smoke) };
    println!("lace widget_host: exited code={code}");
    std::process::exit(code);
}
