mod data;

use pyo3::prelude::*;
use std::io::BufRead;
use serde::{Deserialize};


/// A Python module implemented in Rust.
#[pymodule]
fn rs_ply(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<data::StateMachine>()?;
    Ok(())
}
