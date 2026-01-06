use pyo3::{pyclass, pymethods, Py, Python};
use pyo3::prelude::*;
use pyo3::types::PyString;
use crate::token::Token;

#[pyclass]
#[derive(Debug)]
pub struct TokInfo {
    #[pyo3(get)]
    #[pyo3(name = "type")]
    pub typ: Token,
    #[pyo3(get)]
    pub span: (usize, usize),
    #[pyo3(get)]
    pub start: (usize, usize),
    #[pyo3(get)]
    pub end: (usize, usize),
    pub source: Py<PyString>,
}

#[pymethods]
impl TokInfo {
    #[new]
    pub fn new(
        typ: Token,
        span: (usize, usize),
        start: (usize, usize),
        end: (usize, usize),
        source: Py<PyString>,
    ) -> Self {
        Self {
            typ,
            span,
            start,
            end,
            source,
        }
    }

    #[getter]
    pub fn string(&self, py: Python<'_>) -> String {
        let s = self.source.bind(py).to_str().unwrap();
        s[self.span.0..self.span.1].to_string()
    }

    #[allow(deprecated)]
    pub fn is_exact_type(&self, _py: Python<'_>, typ: String) -> bool {
        self.typ == Token::OP && Python::with_gil(|py| self.string(py) == typ)
    }

    pub fn loc_start(&self) -> std::collections::HashMap<&'static str, usize> {
        let mut map = std::collections::HashMap::new();
        map.insert("lineno", self.start.0);
        map.insert("col_offset", self.start.1);
        map
    }

    pub fn loc_end(&self) -> std::collections::HashMap<&'static str, usize> {
        let mut map = std::collections::HashMap::new();
        map.insert("end_lineno", self.end.0);
        map.insert("end_col_offset", self.end.1);
        map
    }

    pub fn loc(&self) -> std::collections::HashMap<&'static str, usize> {
        let mut map = self.loc_start();
        map.insert("end_lineno", self.end.0);
        map.insert("end_col_offset", self.end.1);
        map
    }

    #[allow(deprecated)]
    fn __repr__(&self) -> String {
        Python::with_gil(|py| {
            let s = self.source.bind(py).to_str().unwrap();
            let string_val = &s[self.span.0..self.span.1];
            format!(
                "TokInfo(type={:?}, string={:?}, start={:?}, end={:?})",
                self.typ, string_val, self.start, self.end
            )
        })
    }

    fn __str__(&self) -> String {
        self.__repr__()
    }
}

impl Clone for TokInfo {
    fn clone(&self) -> Self {
        #[allow(deprecated)]
        Python::with_gil(|py| Self {
            typ: self.typ,
            span: self.span,
            start: self.start,
            end: self.end,
            source: self.source.clone_ref(py),
        })
    }
}

impl PartialEq for TokInfo {
    fn eq(&self, other: &Self) -> bool {
        self.typ == other.typ
            && self.span == other.span
            && self.start == other.start
            && self.end == other.end
            && Python::with_gil(|py| {
            self.source.bind(py).to_str().unwrap() == other.source.bind(py).to_str().unwrap()
        })
    }
}
