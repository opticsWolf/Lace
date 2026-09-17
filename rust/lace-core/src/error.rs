//! Structured errors for layout/theme persistence and validation.

use thiserror::Error;

#[derive(Debug, Error)]
pub enum LaceError {
    #[error("invalid layout: {0}")]
    InvalidLayout(String),

    /// Corrupt layout payload or version mismatch (`InvalidFormatError`).
    #[error("invalid layout format: {0}")]
    InvalidFormat(String),

    /// A structurally broken tree that failed the pre-restore dry-run
    /// (`RestoreFailureError`); the live layout must be left untouched.
    #[error("layout restore failed: {0}")]
    RestoreFailure(String),

    /// Disk-level persistence failure (`LayoutIOError`): missing file,
    /// unwritable directory, disk full, or a locked file that would not
    /// replace after retries.
    #[error("layout storage error: {0}")]
    LayoutIo(String),

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
