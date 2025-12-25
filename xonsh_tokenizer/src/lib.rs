mod regex;
pub mod tokenizer;

use crate::regex::consts::OPERATORS;
use crate::tokenizer::main::{tokenize_file as tok_file, tokenize_string};
use crate::tokenizer::tok::{TokInfo, Token};
use heck::ToShoutySnakeCase;
use pyo3::exceptions::PyTypeError;
use pyo3::prelude::*;
use std::collections::HashMap;

#[pyclass(frozen, module = "xonsh_tokenizer", name = "TokenInfo")]
#[derive(Clone)]
pub struct PyTokInfo {
    pub inner: TokInfo,
}

#[pymethods]
impl PyTokInfo {
    #[new]
    fn __init__(
        typ: &str,
        span: (usize, usize),
        start: (usize, usize),
        end: (usize, usize),
    ) -> PyResult<Self> {
        let tok = match typ {
            "WS" => Token::WS,
            "MACRO_PARAM" => Token::MacroParam,
            _ => panic!("Unknown token type: {}", typ),
        };
        let inner = TokInfo::new(tok, span, start, end);
        Ok(Self { inner })
    }

    fn __repr__<'a>(&'a self) -> PyResult<String> {
        Ok(format!(
            "Tok<{:?}:{}-{}>",
            self.inner.typ, self.inner.span.0, self.inner.span.1
        ))
    }

    fn __getattr__<'py>(slf: PyRef<'py, Self>, py: Python<'py>, name: &str) -> PyResult<PyObject> {
        let obj = match name {
            "type" => format!("{:?}", slf.inner.typ)
                .to_shouty_snake_case()
                .into_py(py),
            "start" => slf.inner.start.clone().into_py(py),
            "end" => slf.inner.end.clone().into_py(py),
            "span" => slf.inner.span.clone().into_py(py),
            _ => return Err(PyTypeError::new_err(format!("Unknown attribute: {}", name))),
        };
        Ok(obj)
    }

    fn is_exact_type(&self, typ: &str) -> bool {
        self.inner.typ == Token::OP && OPERATORS.contains(&typ)
    }

    fn loc_start(&self) -> HashMap<String, usize> {
        let mut map = HashMap::new();
        map.insert("lineno".to_string(), self.inner.start.0);
        map.insert("col_offset".to_string(), self.inner.start.1);
        map
    }

    fn loc_end(&self) -> HashMap<String, usize> {
        let mut map = HashMap::new();
        map.insert("end_lineno".to_string(), self.inner.end.0);
        map.insert("end_col_offset".to_string(), self.inner.end.1);
        map
    }

    fn loc(&self) -> HashMap<String, usize> {
        // merge loc_start and loc_end outputs
        let mut map = HashMap::new();
        map.extend(self.loc_start());
        map.extend(self.loc_end());
        map
    }

    fn get_string<'a>(&self, src: &'a str) -> &'a str {
        &src[self.inner.span.0..self.inner.span.1]
    }
}

#[pyfunction]
fn tokenize_str(src: &str) -> PyResult<Vec<PyTokInfo>> {
    let mut tokens = Vec::new();
    for token in tokenize_string(src) {
        if let Ok(inner) = token {
            tokens.push(PyTokInfo { inner });
        } else {
            return Err(PyTypeError::new_err(token.unwrap_err()));
        }
    }
    Ok(tokens)
}

#[pyfunction]
fn tokenize_file(file_path: &str) -> PyResult<Vec<PyTokInfo>> {
    let mut tokens = Vec::new();
    for token in tok_file(file_path)? {
        if let Ok(inner) = token {
            tokens.push(PyTokInfo { inner });
        } else {
            return Err(PyTypeError::new_err(token.unwrap_err()));
        }
    }
    Ok(tokens)
}

/// A Python module implemented in Rust.
#[pymodule]
fn xonsh_tokenizer(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(tokenize_str, m)?)?;
    m.add_function(wrap_pyfunction!(tokenize_file, m)?)?;
    m.add_class::<PyTokInfo>()?;
    Ok(())
}
