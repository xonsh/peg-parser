mod data;
mod lrparser;
mod yacc_types;

use pyo3::prelude::*;

/// A Python module implemented in Rust.
#[pymodule]
fn rs_ply(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<data::Production>()?;
    m.add_class::<yacc_types::YaccSymbol>()?;
    m.add_class::<yacc_types::YaccProduction>()?;
    m.add_class::<lrparser::LRParser>()?;
    Ok(())
}
