use pyo3::exceptions::PyIndexError;
use pyo3::prelude::*;

/// This class is used to hold non-terminal grammar symbols during parsing.
/// It normally has the following attributes set:
#[pyclass(get_all, set_all)]
#[derive(Debug)]
pub struct YaccSymbol {
    pub r#type: String,
    pub value: Option<PyObject>,
    pub lineno: Option<usize>,
    pub lexpos: Option<usize>,
    pub endlineno: Option<usize>,
    pub endlexpos: Option<usize>,
}

#[pymethods]
impl YaccSymbol {
    #[new]
    #[pyo3(signature = (r#type, value=None, lineno=None, lexpos=None, endlineno=None, endlexpos=None))]
    pub fn new(
        r#type: String,
        value: Option<PyObject>,
        lineno: Option<usize>,
        lexpos: Option<usize>,
        endlineno: Option<usize>,
        endlexpos: Option<usize>,
    ) -> Self {
        YaccSymbol {
            r#type,
            value,
            lineno,
            lexpos,
            endlineno,
            endlexpos,
        }
    }

    fn __repr__(&self) -> String {
        format!("YaccSymbol(type={:?})", self.r#type)
    }

    fn __str__(&self) -> String {
        self.r#type.clone()
    }
}

#[pyclass(get_all, set_all)]
pub struct YaccProduction {
    // The lexer that produced the token stream
    pub lexer: PyObject,
    // The parser that is running this production
    pub parser: PyObject,
    // The slice of the input stream that is covered by this production
    pub slice: Vec<Py<YaccSymbol>>,
    pub stack: Vec<Py<YaccSymbol>>,
}

#[pymethods]
impl YaccProduction {
    #[new]
    pub fn new(lexer: PyObject, parser: PyObject) -> Self {
        YaccProduction {
            lexer,
            parser,
            slice: Vec::new(),
            stack: Vec::new(),
        }
    }

    fn __getitem__<'py>(&self, py: Python<'py>, n: Bound<'py, PyAny>) -> PyResult<PyObject> {
        if let Ok(index) = n.extract::<isize>() {
            let sym_py = if index >= 0 {
                self.slice.get(index as usize).ok_or_else(|| {
                    PyIndexError::new_err(format!(
                        "Index out of range in production slice: {}",
                        index
                    ))
                })?
            } else {
                let actual_index = (self.stack.len() as isize + index) as usize;
                self.stack.get(actual_index).ok_or_else(|| {
                    PyIndexError::new_err(format!(
                        "Index out of range in production stack: {}",
                        index
                    ))
                })?
            };
            let sym = sym_py.borrow(py);
            return Ok(sym
                .value
                .as_ref()
                .map(|v| v.clone_ref(py))
                .unwrap_or_else(|| py.None()));
        }

        if let Ok(sl) = n.downcast::<pyo3::types::PySlice>() {
            let indices = sl.indices(self.slice.len() as isize)?;
            let mut result = Vec::new();
            let mut cur = indices.start;
            while (indices.step > 0 && cur < indices.stop)
                || (indices.step < 0 && cur > indices.stop)
            {
                let sym_py = &self.slice[cur as usize];
                let sym = sym_py.borrow(py);
                result.push(
                    sym.value
                        .as_ref()
                        .map(|v| v.clone_ref(py))
                        .unwrap_or_else(|| py.None()),
                );
                cur += indices.step;
            }
            return Ok(result.into_py(py));
        }

        Err(pyo3::exceptions::PyTypeError::new_err(
            "Indices must be integers or slices",
        ))
    }

    fn __setitem__<'py>(
        &mut self,
        py: Python<'py>,
        index: usize,
        value: Option<PyObject>,
    ) -> PyResult<()> {
        let sym_py = self.slice.get_mut(index).ok_or_else(|| {
            PyIndexError::new_err(format!("Index out of range in production slice: {}", index))
        })?;
        let mut sym = sym_py.borrow_mut(py);
        sym.value = value;
        Ok(())
    }

    fn __len__(&self) -> usize {
        self.slice.len()
    }

    fn lineno(&self, py: Python, n: usize) -> PyResult<usize> {
        let sym_py = self.slice.get(n).ok_or_else(|| {
            PyIndexError::new_err(format!("Index out of range in production slice: {}", n))
        })?;
        Ok(sym_py.borrow(py).lineno.unwrap_or(0))
    }

    pub fn set_lineno(&mut self, py: Python, n: usize, lineno: usize) -> PyResult<()> {
        let sym_py = self.slice.get_mut(n).ok_or_else(|| {
            PyIndexError::new_err(format!("Index out of range in production slice: {}", n))
        })?;
        let mut sym = sym_py.borrow_mut(py);
        sym.lineno = Some(lineno);
        Ok(())
    }

    fn linespan<'py>(&self, py: Python<'py>, n: usize) -> PyResult<(usize, usize)> {
        let sym_py = self.slice.get(n).ok_or_else(|| {
            PyIndexError::new_err(format!("Index out of range in production slice: {}", n))
        })?;
        let borrow = sym_py.borrow(py);
        let startline = borrow.lineno.unwrap_or(0);
        let endline = borrow.endlineno.unwrap_or(startline);
        Ok((startline, endline))
    }

    pub fn lexpos(&self, py: Python, n: usize) -> PyResult<usize> {
        let sym_py = self.slice.get(n).ok_or_else(|| {
            PyIndexError::new_err(format!("Index out of range in production slice: {}", n))
        })?;
        Ok(sym_py.borrow(py).lexpos.unwrap_or(0))
    }

    pub fn set_lexpos(&mut self, py: Python, n: usize, lexpos: usize) -> PyResult<()> {
        let sym_py = self.slice.get_mut(n).ok_or_else(|| {
            PyIndexError::new_err(format!("Index out of range in production slice: {}", n))
        })?;
        let mut sym = sym_py.borrow_mut(py);
        sym.lexpos = Some(lexpos);
        Ok(())
    }

    fn lexspan<'py>(&self, py: Python<'py>, n: usize) -> PyResult<(usize, usize)> {
        let sym_py = self.slice.get(n).ok_or_else(|| {
            PyIndexError::new_err(format!("Index out of range in production slice: {}", n))
        })?;
        let borrow = sym_py.borrow(py);
        let startpos = borrow.lexpos.unwrap_or(0);
        let endpos = borrow.endlexpos.unwrap_or(startpos);
        Ok((startpos, endpos))
    }

    fn error<'py>(&self, _py: Python<'py>) -> PyResult<()> {
        Err(pyo3::exceptions::PySyntaxError::new_err("syntax error"))
    }
}
