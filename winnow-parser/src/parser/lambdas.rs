use super::atoms::parse_name;
use super::expressions::parse_expression;
use super::{get_text, kw, make_error, op, set_location, TokenStream};
use pyo3::prelude::*;
use pyo3::types::PyList;
use winnow::combinator::peek;
use winnow::error::{ContextError, ErrMode};
use winnow::prelude::*;

// lambda_param_def: NAME [= default] (no annotation)
fn parse_lambda_param_def<'s>(
    input: &mut TokenStream<'s>,
) -> ModalResult<(Py<PyAny>, Option<Py<PyAny>>)> {
    let name_tok = parse_name(input)?;
    let name_bytes = get_text(input, &name_tok);
    let name = std::str::from_utf8(name_bytes).unwrap();

    let default = if peek(op(b"=")).parse_next(input).is_ok() {
        let _ = op(b"=").parse_next(input)?;
        Some(parse_expression(input)?)
    } else {
        None
    };

    let py = input.state.py;
    let ast = input.state.ast.clone();

    let node = ast
        .call_method1("arg", (name, py.None(), py.None()))
        .map_err(|_| make_error("arg failed".into()))?;
    set_location(&node, &name_tok, &name_tok).map_err(|e| make_error(e.to_string()))?;

    Ok((node.into(), default))
}

fn parse_lambda_params<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let start_input = input.clone();
    let start_tok = start_input.input[0].clone();
    let mut posonlyargs = Vec::new();
    let mut args = Vec::new();
    let mut vararg = None;
    let mut kwonlyargs = Vec::new();
    let mut kw_defaults = Vec::new();
    let mut kwarg = None;
    let mut defaults = Vec::new();

    let py = input.state.py;

    let mut mode = 0;

    loop {
        if peek(op(b":")).parse_next(input).is_ok() {
            break;
        }

        if peek(op(b"**")).parse_next(input).is_ok() {
            let _ = op(b"**").parse_next(input)?;
            let (arg, _) = parse_lambda_param_def(input)?;
            kwarg = Some(arg);
            if peek(op(b",")).parse_next(input).is_ok() {
                let _ = op(b",").parse_next(input)?;
            }
            break;
        }

        if peek(op(b"*")).parse_next(input).is_ok() {
            if mode == 1 {
                return Err(ErrMode::Backtrack(ContextError::new()));
            }
            let _ = op(b"*").parse_next(input)?;
            mode = 1;

            if peek(parse_name).parse_next(input).is_ok() {
                let (arg, _) = parse_lambda_param_def(input)?;
                vararg = Some(arg);
            }

            if peek(op(b",")).parse_next(input).is_ok() {
                let _ = op(b",").parse_next(input)?;
                continue;
            } else {
                if peek(op(b":")).parse_next(input).is_ok() {
                    break;
                }
                break;
            }
        }

        let (p_arg, p_def) = parse_lambda_param_def(input)?;

        let mut seen_slash = false;

        if peek(op(b",")).parse_next(input).is_ok() {
            let _ = op(b",").parse_next(input)?;

            if mode == 0 && peek(op(b"/")).parse_next(input).is_ok() {
                let _ = op(b"/").parse_next(input)?;
                seen_slash = true;
                if peek(op(b",")).parse_next(input).is_ok() {
                    let _ = op(b",").parse_next(input)?;
                }
            }
        } else {
            if mode == 0 && peek(op(b"/")).parse_next(input).is_ok() {
                let _ = op(b"/").parse_next(input)?;
                seen_slash = true;
                if peek(op(b",")).parse_next(input).is_ok() {
                    let _ = op(b",").parse_next(input)?;
                }
            }
        }

        if mode == 0 {
            args.push(p_arg);
            if let Some(d) = p_def {
                defaults.push(d);
            }

            if seen_slash {
                posonlyargs.append(&mut args);
            }
        } else {
            kwonlyargs.push(p_arg);
            match p_def {
                Some(d) => kw_defaults.push(d),
                None => kw_defaults.push(py.None()),
            }
        }
    }

    let ast = input.state.ast.clone();
    let posonly_list = PyList::new(py, posonlyargs).unwrap();
    let args_list = PyList::new(py, args).unwrap();
    let kwonly_list = PyList::new(py, kwonlyargs).unwrap();
    let defaults_list = PyList::new(py, defaults).unwrap();
    let kw_defaults_list = PyList::new(py, kw_defaults).unwrap();

    let vararg_obj = match vararg {
        Some(v) => v,
        None => py.None(),
    };
    let kwarg_obj = match kwarg {
        Some(k) => k,
        None => py.None(),
    };

    let node = ast
        .call_method1(
            "arguments",
            (
                posonly_list,
                args_list,
                vararg_obj,
                kwonly_list,
                kw_defaults_list,
                kwarg_obj,
                defaults_list,
            ),
        )
        .map_err(|_| make_error("arguments failed".into()))?;

    let consumed = start_input.input.len() - input.input.len();
    let end_tok = start_input.input[consumed - 1].clone();
    set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;

    Ok(node.into())
}

// lambdef:
//     | 'lambda' [params] ':' body=expression
pub fn parse_lambdef<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let start_input = input.clone();
    let start_tok = start_input.input[0].clone();
    let _ = kw(b"lambda").parse_next(input)?;
    eprintln!("DEBUG: Entering parse_lambdef");

    let (args, is_empty_args) = if !peek(op(b":")).parse_next(input).is_ok() {
        (parse_lambda_params(input)?, false)
    } else {
        let py = input.state.py;
        let ast = input.state.ast.clone();
        let node = ast
            .call_method1(
                "arguments",
                (
                    PyList::empty(py),
                    PyList::empty(py),
                    py.None(),
                    PyList::empty(py),
                    PyList::empty(py),
                    py.None(),
                    PyList::empty(py),
                ),
            )
            .unwrap();
        set_location(&node, &start_tok, &start_tok).map_err(|e| make_error(e.to_string()))?;
        (node.into(), true)
    };

    let _ = op(b":").parse_next(input)?;
    let body = parse_expression(input)?;

    let py = input.state.py;
    if is_empty_args {
        eprintln!("DEBUG: Syncing empty args location from body");
        let body_bound = body.bind(py);
        let args_bound = args.bind(py);

        if let Ok(lineno) = body_bound.getattr("lineno") {
            let _ = args_bound.setattr("lineno", lineno);
        } else {
            eprintln!("DEBUG: failed to get lineno");
        }
        if let Ok(col) = body_bound.getattr("col_offset") {
            eprintln!("DEBUG: copying col_offset {:?}", col);
            let _ = args_bound.setattr("col_offset", col);
        } else {
            eprintln!("DEBUG: failed to get col_offset");
        }
        if let Ok(end_lineno) = body_bound.getattr("end_lineno") {
            let _ = args_bound.setattr("end_lineno", end_lineno);
        }
        if let Ok(end_col) = body_bound.getattr("end_col_offset") {
            let _ = args_bound.setattr("end_col_offset", end_col);
        }
    }

    let ast = input.state.ast.clone();
    let node = ast
        .call_method1("Lambda", (args, body))
        .map_err(|_| make_error("Lambda failed".into()))?;
    Ok(node.into())
}
