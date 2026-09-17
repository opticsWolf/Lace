//! `_lace_rs`: thin PyO3 wrappers over `lace-core`.
//!
//! No logic lives here — every function delegates to `lace-core` so the
//! Python shim and the QML front-end can never disagree. Qt is deliberately
//! *not* linked into this module (see the plan §6 linkage rule).

use pyo3::prelude::*;

#[pyfunction]
fn split_share(target_size: u32, handle_width: u32, n_total: u32) -> u32 {
    lace_core::split_share(target_size, handle_width, n_total)
}

#[pyfunction]
fn allowed_areas(visible_area_count: usize, target_present: bool) -> u32 {
    lace_core::allowed_areas_for(visible_area_count, target_present).bits()
}

#[pymodule]
fn _lace_rs(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(split_share, m)?)?;
    m.add_function(wrap_pyfunction!(allowed_areas, m)?)?;
    m.add("__version__", env!("CARGO_PKG_VERSION"))?;
    Ok(())
}
