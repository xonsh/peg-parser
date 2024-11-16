mod data;
mod lrparser;
mod yacc_types;

use pyo3::prelude::*;

/// A Python module implemented in Rust.
#[pymodule]
fn rs_ply(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<data::StateMachine>()?;
    Ok(())
}
