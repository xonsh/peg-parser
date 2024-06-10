mod regex;
pub mod tokenizer;

use pyo3::exceptions::PyTypeError;
use pyo3::prelude::*;
use tokenizer::{tokenize_string, TokInfo};

#[pyclass(frozen)]
#[derive(Clone)]
pub struct PyTokInfo {
    pub inner: tokenizer::TokInfo,
}

#[pymethods]
impl PyTokInfo {
    fn __repr__<'a>(&'a self) -> PyResult<String> {
        Ok(format!("Tok<{:?}:'{}'>", self.inner.typ, self.inner.string))
    }

    fn __getattr__<'py>(slf: PyRef<'py, Self>, py: Python<'py>, name: &str) -> PyResult<PyObject> {
        let obj = match name {
            "type" => format!("{:?}", slf.inner.typ).into_py(py),
            "string" => slf.inner.string.clone().into_py(py),
            "start" => slf.inner.start.clone().into_py(py),
            "end" => slf.inner.end.clone().into_py(py),
            _ => return Err(PyTypeError::new_err(format!("Unknown attribute: {}", name))),
        };
        Ok(obj)
    }
}

/// Formats the sum of two numbers as string.
#[pyfunction]
fn tokenize_str(src: &str) -> PyResult<Vec<PyTokInfo>> {
    let mut tokens = Vec::new();
    for token in tokenize_string(src) {
        if let Ok(inner) = token {
            tokens.push(PyTokInfo{inner});
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
    m.add_class::<PyTokInfo>()?;
    Ok(())
}
