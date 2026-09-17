//! Structured errors for layout/theme persistence and validation.

use thiserror::Error;

#[derive(Debug, Error)]
pub enum LaceError {
    #[error("invalid layout: {0}")]
    InvalidLayout(String),

    #[error("unsupported layout version {found} (this build reads up to {supported})")]
    VersionMismatch {
        found: u32,
        supported: u32,
    },

    #[error("invalid theme: {0}")]
    InvalidTheme(String),

    #[error("io error: {0}")]
    Io(#[from] std::io::Error),

    #[error("json error: {0}")]
    Json(#[from] serde_json::Error),
}
