pub mod parser;
pub mod tokenizer;

use pyo3::prelude::*;
use xtokens::{TokInfo, Token};

#[pymodule]
fn winnow_parser(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Token>()?;
    m.add_class::<TokInfo>()?;
    m.add_function(wrap_pyfunction!(tokenizer::tokenize_py, m)?)?;
    m.add_function(wrap_pyfunction!(parser::parse_code, m)?)?;
    // m.add_function(wrap_pyfunction!(parser::debug_parse, m)?)?; // debug_parse not implemented yet in parser.rs? Wait I added it? No I failed to add it due to invalid tool call in 180 and file confusion. But parse_code has the logic.
    // I will stick to parse_code modification.
    Ok(())
}
