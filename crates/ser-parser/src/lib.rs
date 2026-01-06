use pyo3::prelude::*;
use pyo3::types::PyString;
use xtokens::TokInfo;

pub mod lexer;

#[pymodule]
fn ser_parser(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(tokenize, m)?)?;
    Ok(())
}

#[pyfunction]
fn tokenize(py: Python<'_>, source: Py<PyString>) -> Vec<TokInfo> {
    crate::lexer::tokenize(py, source)
}
