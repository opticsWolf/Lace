//! `lace-core::persist`: atomic layout file storage.
//!
//! Ports `LayoutPersistenceManager` with zero Qt: parent directories are
//! created, the payload goes to a temp file (flushed + fsync'd), and the
//! temp file replaces the target with retries against Windows file locking.
//! A leftover temp file is unlinked on a best-effort basis.

use std::path::{Path, PathBuf};
use std::time::Duration;

use crate::error::LaceError;
use crate::layout_doc::LayoutDoc;

/// Replacement attempts before a locked file is reported.
const MAX_REPLACE_RETRIES: u32 = 4;
/// First retry delay; doubles per attempt (mirrors the Python backoff).
const REPLACE_BASE_DELAY: Duration = Duration::from_millis(100);

fn is_disk_full(error: &std::io::Error) -> bool {
    // ENOSPC on Unix, ERROR_DISK_FULL on Windows.
    error.raw_os_error() == Some(28) || error.raw_os_error() == Some(112)
}

fn is_lock_error(error: &std::io::Error) -> bool {
    // EACCES / EPERM / EBUSY on Unix surface as PermissionDenied or
    // Uncategorized with OS-specific codes; a locked destination on Windows
    // reports sharing/permission violations.
    error.kind() == std::io::ErrorKind::PermissionDenied
        || matches!(error.raw_os_error(), Some(13) | Some(1) | Some(16) | Some(32) | Some(33))
}

/// A directory that layout files live under (created on demand).
#[derive(Clone, Debug)]
pub struct PersistDir {
    base: PathBuf,
}

impl PersistDir {
    pub fn new(base: impl AsRef<Path>) -> Self {
        PersistDir { base: base.as_ref().to_path_buf() }
    }

    /// `set_default_path`: re-point the directory.
    pub fn set_path(&mut self, path: impl AsRef<Path>) {
        self.base = path.as_ref().to_path_buf();
    }

    fn resolve(&self, filename: &str) -> PathBuf {
        let mut path = self.base.join(filename);
        // MSRV 1.77: no Option::is_none_or yet.
        let needs_suffix = !matches!(path.extension(), Some(ext) if ext == "json");
        if needs_suffix {
            path.set_extension("json");
        }
        path
    }

    /// Atomically store `doc` under `filename` (`.json` appended unless
    /// present). `formatted` selects the indented rendering.
    pub fn save_layout(
        &self,
        filename: &str,
        doc: &LayoutDoc,
        formatted: bool,
    ) -> Result<(), LaceError> {
        let filepath = self.resolve(filename);
        if let Some(parent) = filepath.parent() {
            std::fs::create_dir_all(parent)
                .map_err(|e| LaceError::LayoutIo(format!("directory creation failed: {e}")))?;
        }
        let payload = doc.render(formatted)?;

        let temp_path = filepath.with_extension("tmp.json");
        // Best effort: a stale temp file from a crashed save must not block us.
        let _ = std::fs::remove_file(&temp_path);
        let write_result = (|| -> std::io::Result<()> {
            use std::io::Write;
            let mut file = std::fs::File::create(&temp_path)?;
            file.write_all(payload.as_bytes())?;
            file.flush()?;
            file.sync_all()?;
            Ok(())
        })();
        if let Err(e) = write_result {
            let _ = std::fs::remove_file(&temp_path);
            if is_disk_full(&e) {
                return Err(LaceError::LayoutIo("disk full: cannot save layout data".into()));
            }
            return Err(LaceError::LayoutIo(format!("failed to safely write layout: {e}")));
        }

        let replace_result = self.replace_with_retry(&temp_path, &filepath);
        // The temp file must never survive, success or not.
        let _ = std::fs::remove_file(&temp_path);
        replace_result
    }

    fn replace_with_retry(&self, src: &Path, dst: &Path) -> Result<(), LaceError> {
        for attempt in 0..MAX_REPLACE_RETRIES {
            match std::fs::rename(src, dst) {
                Ok(()) => return Ok(()),
                Err(e) if is_lock_error(&e) && attempt + 1 < MAX_REPLACE_RETRIES => {
                    std::thread::sleep(REPLACE_BASE_DELAY * 2_u32.pow(attempt));
                }
                Err(e) if is_lock_error(&e) => {
                    return Err(LaceError::LayoutIo(format!(
                        "file locked, atomic replace failed after {MAX_REPLACE_RETRIES} attempts"
                    )));
                }
                Err(e) => {
                    return Err(LaceError::LayoutIo(format!("failed to replace layout file: {e}")));
                }
            }
        }
        unreachable!("retry loop always returns");
    }

    /// Load and parse the layout stored under `filename`.
    pub fn load_layout(&self, filename: &str) -> Result<LayoutDoc, LaceError> {
        let filepath = self.resolve(filename);
        if !filepath.exists() {
            return Err(LaceError::LayoutIo(format!(
                "layout file not found at {}",
                filepath.display()
            )));
        }
        let text = std::fs::read_to_string(&filepath)
            .map_err(|e| LaceError::LayoutIo(format!("failed to read layout file: {e}")))?;
        LayoutDoc::parse(&text)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_doc() -> LayoutDoc {
        LayoutDoc {
            system_type: crate::layout_doc::SYSTEM_TYPE.to_string(),
            schema: crate::layout_doc::SCHEMA_VERSION,
            version: 3,
            containers: Vec::new(),
            sidebars: Default::default(),
            container_geometries: Default::default(),
            widget_states: Default::default(),
        }
    }

    fn scratch_dir(name: &str) -> PathBuf {
        // Unique per test AND per process: parallel tests must not share.
        let dir = std::env::temp_dir()
            .join("lace_persist")
            .join(format!("{}-{}", name, std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        dir
    }

    #[test]
    fn save_then_load_roundtrips() {
        let dir = PersistDir::new(scratch_dir("roundtrip"));
        dir.save_layout("session", &sample_doc(), true).unwrap();
        let back = dir.load_layout("session.json").unwrap();
        assert_eq!(back, sample_doc());
    }

    #[test]
    fn json_suffix_is_appended_when_missing() {
        let path = scratch_dir("suffix");
        let dir = PersistDir::new(&path);
        dir.save_layout("plain-name", &sample_doc(), false).unwrap();
        assert!(path.join("plain-name.json").exists());
    }

    #[test]
    fn missing_file_is_a_storage_error() {
        let dir = PersistDir::new(scratch_dir("missing"));
        match dir.load_layout("nope") {
            Err(LaceError::LayoutIo(message)) => assert!(message.contains("not found")),
            other => panic!("expected LayoutIo, got {other:?}"),
        }
    }

    #[test]
    fn corrupt_payload_is_a_format_error() {
        let path = scratch_dir("corrupt");
        let dir = PersistDir::new(&path);
        std::fs::create_dir_all(&path).unwrap();
        std::fs::write(path.join("bad.json"), "{not valid json").unwrap();
        match dir.load_layout("bad") {
            Err(LaceError::InvalidFormat(_)) => {}
            other => panic!("expected InvalidFormat, got {other:?}"),
        }
    }
}
