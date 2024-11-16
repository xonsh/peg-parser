use crate::data::Production;
use pyo3::exceptions::PyIndexError;
use pyo3::prelude::*;

/// This class is used to hold non-terminal grammar symbols during parsing.
/// It normally has the following attributes set:
#[pyclass]
#[derive(Debug)]
pub struct YaccSymbol {
    symbol_type: String,
    // Union[str, ast.AST, LexToken, None, "YaccSymbol"]
    value: Option<String>,
    lineno: Option<usize>,
    lexpos: Option<usize>,
    endlineno: Option<usize>,
    endlexpos: Option<usize>,
}

///
//     # This class is a wrapper around the objects actually passed to each
//     # grammar rule.   Index lookup and assignment actually assign the
//     # .value attribute of the underlying YaccSymbol object.
//     # The lineno() method returns the line number of a given
//     # item (or 0 if not defined).   The linespan() method returns
//     # a tuple of (startline,endline) representing the range of lines
//     # for a symbol.  The lexspan() method returns a tuple (lexpos,endlexpos)
//     # representing the range of positional information for a symbol.
#[pyclass]
#[derive(Debug)]
pub struct YaccProduction {
    // The lexer that produced the token stream
    lexer: PyObject,
    // The parser that is running this production
    parser: PyObject,
    // The slice of the input stream that is covered by this production
    slice: Vec<Py<YaccSymbol>>,
    stack: Vec<Py<YaccSymbol>>,
}

#[pymethods]
impl YaccProduction {
    #[new]
    pub fn new<'py>(
        py: Python<'py>,
        lexer: &Bound<'py, PyAny>,
        parser: &Bound<'py, PyAny>,
    ) -> Self {
        YaccProduction {
            lexer: lexer.into_py(py),
            parser: parser.into_py(py),
            slice: Vec::new(),
            stack: Vec::new(),
        }
    }
    fn get_slice<'py>(&self, py: Python<'py>, index: usize) -> PyResult<&Bound<'py, YaccSymbol>> {
        let val = self.slice.get(index as usize).ok_or_else(|| {
            PyIndexError::new_err(format!("Index not found in YaccProduction.slice: {index}"))
        })?;
        Ok(val.bind(py))
    }
    fn get_stack<'py>(&self, py: Python<'py>, index: usize) -> PyResult<&Bound<'py, YaccSymbol>> {
        let val = self.stack.get(index).ok_or_else(|| {
            PyIndexError::new_err(format!("Index not found in YaccProduction.stack: {index}"))
        })?;
        Ok(val.bind(py))
    }

    fn __getitem__<'py>(&self, py: Python, index: i8) -> PyResult<Option<String>> {
        let value = if index >= 0 {
            self.get_slice(py, index as usize)?
        } else {
            let index = self.stack.len() - (index * -1) as usize;
            self.get_stack(py, index)?
        };

        let value = value.borrow().value.clone();
        Ok(value)
    }

    fn __setitem__<'py>(&mut self, py: Python<'py>, index: u8, value: String) -> PyResult<()> {
        let slice = self.slice.get_mut(index as usize).ok_or_else(|| {
            PyIndexError::new_err(format!("Index not found in YaccProduction: {index}"))
        })?;
        let mut slice = slice.borrow_mut(py);
        slice.value = Some(value);
        Ok(())
    }

    fn __len__(&self) -> usize {
        self.slice.len()
    }

    fn linespan<'py>(&self, py: Python<'py>, n: usize) -> PyResult<(usize, usize)> {
        let startline = self.get_slice(py, n)?.borrow().lineno.unwrap_or(0);
        let endline = self
            .get_slice(py, n)?
            .borrow()
            .endlineno
            .unwrap_or(startline);
        Ok((startline, endline))
    }

    fn lexpos<'py>(&self, py: Python<'py>, n: usize) -> PyResult<usize> {
        let startline = self.get_slice(py, n)?.borrow().lexpos.unwrap_or(0);
        Ok(startline)
    }

    fn lexspan<'py>(&self, py: Python<'py>, n: usize) -> PyResult<(usize, usize)> {
        let startpos = self.get_slice(py, n)?.borrow().lexpos.unwrap_or(0);
        let endpos = self
            .get_slice(py, n)?
            .borrow()
            .endlexpos
            .unwrap_or(startpos);
        Ok((startpos, endpos))
    }
    fn error<'py>(&self, py: Python<'py>) -> PyResult<()> {
        Err(pyo3::exceptions::PySyntaxError::new_err("syntax error"))
    }

    // fn call<'py>(&self, py: Python<'py>, prod: Py<Production>) -> PyResult<()> {
    //     let attr = prod.borrow(py).func;
    //     let func = self.parser.getattr(py, attr)?;
    //     func.call1(py, (prod,))?;
    //     Ok(())
    // }
}
