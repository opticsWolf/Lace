//! `lace-qt`: QObject bridges between `lace-core` and QML.
//!
//! Rust owns the state; QML binds properties and calls invokables. Each
//! bridge module maps to one QML-facing type in `com.lace.dock`.

pub mod manager;
