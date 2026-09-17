//! `LaceManager` — the Phase-0 hello bridge.
//!
//! A `QObject` with one numeric property, one string property and two
//! invokables, proving the full Rust → C++ → QML path. The real manager
//! facade (add/remove/find, save/restore, themes) lands in Phase 3.
//!
//! Shape follows the upstream `qml_minimal` example verbatim: no bridge
//! namespace (it would mis-qualify the `QString` alias), `#[namespace]`
//! on the type, explicit `#[cxx_name]` for camelCase QML methods.

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
        #[namespace = "lace"]
        type LaceManager = super::LaceManagerRust;

        /// Bump the hello counter.
        #[qinvokable]
        fn increment(self: Pin<&mut Self>);

        /// Store the active theme name (Phase 0: no theme engine yet).
        /// Named `apply_*` because the `theme` property already owns the
        /// generated `set_theme()` setter.
        #[qinvokable]
        #[cxx_name = "applyTheme"]
        fn apply_theme(self: Pin<&mut Self>, name: &QString);
    }
}

use core::pin::Pin;
use cxx_qt_lib::QString;

#[derive(Default)]
pub struct LaceManagerRust {
    counter: i32,
    theme: QString,
}

impl ffi::LaceManager {
    fn increment(mut self: Pin<&mut Self>) {
        let next = self.as_ref().counter() + 1;
        self.as_mut().set_counter(next);
    }

    fn apply_theme(mut self: Pin<&mut Self>, name: &QString) {
        // Generated `set_theme` takes the value by value; clone the borrow.
        let owned: QString = name.clone();
        self.as_mut().set_theme(owned);
    }
}
