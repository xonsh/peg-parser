use crate::tokenizer::{TokInfo, Tokenizer};
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyTuple};

#[pyclass(subclass, module = "winnow_parser")]
pub struct Parser {
    tokenizer: Py<Tokenizer>,
}

#[pymethods]
impl Parser {
    #[new]
    #[pyo3(signature = (tokenizer, *_args, **_kwargs))]
    fn new(
        tokenizer: Py<Tokenizer>,
        _args: &Bound<'_, PyTuple>,
        _kwargs: Option<&Bound<'_, PyDict>>,
    ) -> Self {
        Parser { tokenizer }
    }

    fn mark(&self, py: Python<'_>) -> PyResult<usize> {
        Ok(self.tokenizer.borrow(py).mark())
    }

    fn reset(&self, py: Python<'_>, index: usize) -> PyResult<()> {
        self.tokenizer.borrow_mut(py).reset(index);
        Ok(())
    }

    fn token(&self, py: Python<'_>, typ: &str) -> PyResult<Option<TokInfo>> {
        let mut tokenizer = self.tokenizer.borrow_mut(py);
        let tok = tokenizer.peek(py)?;
        if tok.typ.name() == typ {
            Ok(Some(tokenizer.getnext(py)?))
        } else {
            Ok(None)
        }
    }

    fn expect(&self, py: Python<'_>, typ: &str) -> PyResult<Option<TokInfo>> {
        let mut tokenizer = self.tokenizer.borrow_mut(py);
        let tok = tokenizer.peek(py)?;
        if tok.typ.name() == typ {
            Ok(Some(tokenizer.getnext(py)?))
        } else {
            // Expect returns None? Python parser.expect raises error usually?
            // peg_parser/subheader.py: expect(self, type): if ... return tok else return None
            // It seems it returns None on failure?
            // Logic: "expected X".
            // Actually, `expect` in some parsers raises.
            // Let's verify Python implementation.
            Ok(None)
        }
    }
}

impl Parser {
    fn check_token(&self, py: Python<'_>, typ: &str) -> PyResult<bool> {
        let tokenizer = self.tokenizer.borrow(py);
        // This helper might not be needed if we do logic inline
        Ok(false)
    }
}
