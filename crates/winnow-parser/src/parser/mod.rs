use crate::tokenizer::tokenize;
use pyo3::prelude::*;
use pyo3::types::{PyList, PyModule, PyString};
use winnow::error::{ContextError, ErrMode};
use winnow::prelude::*;
use winnow::stream::Stateful;
use winnow::token::any;
use xtokens::{TokInfo, Token};

pub mod atoms;
pub mod expr_ops;
pub mod expressions;
pub mod lambdas;
pub mod statements;

// Winnow requires State to be Clone and Debug.
// Python<'py> is Copy, Clone, but not Debug.
#[derive(Clone)]
pub struct PState<'s> {
    pub source: &'s [u8],
    pub py: Python<'s>,
    pub ast: Bound<'s, PyModule>, // Cached ast module
}

impl<'s> std::fmt::Debug for PState<'s> {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("PState")
            .field("source", &self.source)
            .field("py", &"Python")
            .finish()
    }
}

pub type TokenStream<'s> = Stateful<&'s [TokInfo], PState<'s>>;

// ### Helpers ###

pub fn get_text<'s>(input: &TokenStream<'s>, tok: &TokInfo) -> &'s [u8] {
    &input.state.source[tok.span.0..tok.span.1]
}

// Match a specific token type
// Returns TokInfo by value (it's Copy/Clone and small)
pub fn parse_token_type<'s>(input: &mut TokenStream<'s>, kind: Token) -> ModalResult<TokInfo> {
    any.verify(move |t: &TokInfo| t.typ == kind)
        .parse_next(input)
}

// Helper to create a parser for a specific OP
pub fn op<'s>(target: &'static [u8]) -> impl FnMut(&mut TokenStream<'s>) -> ModalResult<TokInfo> {
    move |input: &mut TokenStream<'s>| {
        let checkpoint = input.checkpoint();
        let tok = any.parse_next(input)?;

        if tok.typ == Token::OP {
            let text = get_text(input, &tok);
            if text == target {
                return Ok(tok);
            }
        }
        input.reset(&checkpoint);
        Err(ErrMode::Backtrack(ContextError::new()))
    }
}

// Helper to create a parser for a specific Keyword
pub fn kw<'s>(target: &'static [u8]) -> impl FnMut(&mut TokenStream<'s>) -> ModalResult<TokInfo> {
    move |input: &mut TokenStream<'s>| {
        let checkpoint = input.checkpoint();
        let tok = any.parse_next(input)?;
        if tok.typ == Token::NAME {
            let text = get_text(input, &tok);
            if text == target {
                return Ok(tok);
            }
        }
        input.reset(&checkpoint);
        Err(ErrMode::Backtrack(ContextError::new()))
    }
}

// ### Error Reporting Helper ###
pub fn make_error(_msg: String) -> ErrMode<ContextError> {
    // println!("Parser Error: {}", msg);
    ErrMode::Backtrack(ContextError::new())
}

// ### Context Helpers ###
pub fn ctx_load(ast: &Bound<'_, PyModule>) -> ModalResult<Py<PyAny>> {
    let node = ast
        .call_method0("Load")
        .map_err(|_| make_error("Load failed".into()))?;
    Ok(node.into())
}

pub fn ctx_store(ast: &Bound<'_, PyModule>) -> ModalResult<Py<PyAny>> {
    let node = ast
        .call_method0("Store")
        .map_err(|_| make_error("Store failed".into()))?;
    Ok(node.into())
}

pub fn ctx_del(ast: &Bound<'_, PyModule>) -> ModalResult<Py<PyAny>> {
    let node = ast
        .call_method0("Del")
        .map_err(|_| make_error("Del failed".into()))?;
    Ok(node.into())
}

pub fn set_context(py: Python, node: &Py<PyAny>, ctx: Py<PyAny>) -> ModalResult<()> {
    let bound = node.bind(py);
    let cls_name = bound.get_type().name().unwrap();
    let name_str = cls_name.to_cow().unwrap();
    match name_str.as_ref() {
        "Name" | "Attribute" | "Subscript" => {
            let _ = bound
                .setattr("ctx", ctx)
                .map_err(|_| make_error(format!("Failed to set ctx for {}", name_str).into()))?;
        }
        "Starred" => {
            let _ = bound
                .setattr("ctx", ctx.clone_ref(py))
                .map_err(|_| make_error(format!("Failed to set ctx for {}", name_str).into()))?;
            let value = bound
                .getattr("value")
                .map_err(|_| make_error("Failed to get value".into()))?;
            set_context(py, &value.unbind(), ctx)?;
        }
        "Tuple" | "List" => {
            let _ = bound
                .setattr("ctx", ctx.clone_ref(py))
                .map_err(|_| make_error(format!("Failed to set ctx for {}", name_str).into()))?;
            let elts = bound
                .getattr("elts")
                .map_err(|_| make_error("Failed to get elts".into()))?;
            let elts_list = elts
                .cast::<PyList>()
                .map_err(|_| make_error("elts is not a list".into()))?;
            for elt in elts_list {
                set_context(py, &elt.clone().unbind(), ctx.clone_ref(py))?;
            }
        }
        _ => {}
    }
    Ok(())
}

pub fn set_location(node: &Bound<'_, PyAny>, start: &TokInfo, end: &TokInfo) -> PyResult<()> {
    node.setattr("lineno", start.start.0)?;
    node.setattr("col_offset", start.start.1)?;
    node.setattr("end_lineno", end.end.0)?;
    node.setattr("end_col_offset", end.end.1)?;
    Ok(())
}

// ### Main Entry Point ###

pub fn parse<'s>(py: Python<'s>, source: &'s str) -> PyResult<Py<PyAny>> {
    let source_py = PyString::new(py, source).into();
    let tokens = tokenize(py, source_py);
    let filtered_tokens: Vec<TokInfo> = tokens
        .into_iter()
        .filter(|t| {
            !matches!(
                t.typ,
                Token::WS | Token::NL | Token::COMMENT | Token::ENCODING | Token::TYPE_COMMENT
            )
        })
        .collect();

    let input_tokens = filtered_tokens.as_slice();

    let ast = py.import("ast")?.into();

    let state = PState {
        source: source.as_bytes(),
        py,
        ast,
    };
    let mut input = Stateful {
        input: input_tokens,
        state,
    };

    let res = statements::parse_file.parse_next(&mut input);

    match res {
        Ok(obj) => Ok(obj),
        Err(e) => Err(pyo3::exceptions::PySyntaxError::new_err(format!(
            "Parsing failed: {:?}",
            e
        ))),
    }
}

#[pyfunction]
pub fn parse_code(py: Python, source: String) -> PyResult<Py<PyAny>> {
    parse(py, &source)
}
