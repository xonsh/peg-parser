pub mod parser;
pub mod tokenizer;

use pyo3::prelude::*;

#[pymodule]
fn winnow_parser(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<tokenizer::Token>()?;
    m.add_class::<tokenizer::TokInfo>()?;
    m.add_function(wrap_pyfunction!(tokenizer::tokenize_py, m)?)?;
    m.add_function(wrap_pyfunction!(parser::parse_code, m)?)?;
    Ok(())
}
