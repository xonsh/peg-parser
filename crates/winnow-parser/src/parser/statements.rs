use super::atoms::{
    parse_dedent, parse_endmarker, parse_indent, parse_name, parse_newline, parse_number,
    parse_string,
};

use super::expressions::{
    parse_arguments, parse_expression, parse_named_expression, parse_star_expressions,
    parse_star_target, parse_star_targets,
};
use super::{
    ctx_del, ctx_load, ctx_store, get_text, kw, make_error, op, parse_token_type, set_context,
    set_location, TokenStream,
};
use crate::tokenizer::{TokInfo, Token};
use pyo3::prelude::*;
use pyo3::types::{PyList, PyString};
use winnow::combinator::{cut_err, not, opt, peek, repeat, separated};
use winnow::error::{ContextError, ErrMode};
use winnow::prelude::*;

// file[ast.Module]: a=[statements] ENDMARKER { ast.Module(body=a or [], type_ignores=[]) }
pub fn parse_file<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    use std::io::Write;
    if let Ok(mut f) = std::fs::OpenOptions::new()
        .append(true)
        .create(true)
        .open("/tmp/parser_entry.txt")
    {
        let _ = writeln!(f, "DEBUG: Entering parse_file");
    }
    let a = opt(parse_statements).parse_next(input)?;
    let _ = parse_endmarker.parse_next(input)?;

    let py = input.state.py;
    let ast = input.state.ast.clone();

    // Construct ast.Module
    let body = match a {
        Some((stmts, _tok)) => stmts,
        None => PyList::empty(py).into(),
    };

    let type_ignores = PyList::empty(py);

    let module = ast
        .call_method1("Module", (body, type_ignores))
        .map_err(|_| make_error("Failed to create Module".into()))?;
    Ok(module.into())
}

// statements[list[Any]]: a=statement+ { list(itertools.chain.from_iterable(a)) }
pub fn parse_statements<'s>(input: &mut TokenStream<'s>) -> ModalResult<(Py<PyAny>, TokInfo)> {
    let mut a = Vec::new();
    let mut last_tok = input.input[0].clone();

    while let Ok((stmt_list, tok)) = parse_statement(input) {
        a.push(stmt_list);
        last_tok = tok;
    }

    if a.is_empty() {
        return Err(ErrMode::Backtrack(ContextError::new()));
    }

    // Flatten the list (each statement returns a list of nodes)
    let py = input.state.py;
    let flat_list = PyList::empty(py);
    for stmt_list in a {
        // stmt_list is a list of nodes (e.g. from simple_stmts)
        let list_ref = stmt_list.bind(py);
        if let Ok(iter) = list_ref.try_iter() {
            for item in iter {
                if let Ok(i) = item {
                    flat_list
                        .append(i)
                        .map_err(|_| make_error("List append failed".into()))?;
                }
            }
        }
    }

    Ok((flat_list.into(), last_tok))
}

// statement[list[Any]]: a=compound_stmt { [a] } | a=simple_stmts { a }
pub fn parse_statement<'s>(input: &mut TokenStream<'s>) -> ModalResult<(Py<PyAny>, TokInfo)> {
    let checkpoint = input.checkpoint();

    if let Ok((stmt, tok)) = parse_compound_stmt(input) {
        let py = input.state.py;
        let list = PyList::new(py, vec![stmt]).unwrap();
        return Ok((list.into(), tok));
    }

    input.reset(&checkpoint);

    parse_simple_stmts(input)
}

// block[list[Any]] (memo):
//     | NEWLINE INDENT a=statements DEDENT { a }
//     | simple_stmts
pub fn parse_block<'s>(input: &mut TokenStream<'s>) -> ModalResult<(Py<PyAny>, TokInfo)> {
    let checkpoint = input.checkpoint();

    // NEWLINE INDENT a=statements DEDENT
    if let Ok(_) = parse_newline(input) {
        if let Ok(_) = parse_indent(input) {
            let (stmts, last_tok) = cut_err(parse_statements).parse_next(input)?;
            let _ = parse_dedent(input)?;
            return Ok((stmts, last_tok));
        }
    }

    input.reset(&checkpoint);
    parse_simple_stmts(input)
}

// simple_stmts[list[Any]]:
//     | a=simple_stmt !';' NEWLINE { [a] }
//     | a1=';'.simple_stmt+ [';'] NEWLINE { a1 }
pub fn parse_simple_stmts<'s>(input: &mut TokenStream<'s>) -> ModalResult<(Py<PyAny>, TokInfo)> {
    let start_tokens = input.input;
    let checkpoint = input.checkpoint();

    // Option 1: simple_stmt !';' NEWLINE
    if let Ok((stmt, _)) = (parse_simple_stmt, not(op(b";"))).parse_next(input) {
        let last_tok = start_tokens[start_tokens.len() - input.input.len() - 1].clone();
        if let Ok(_) = parse_newline(input) {
            let py = input.state.py;
            let list = PyList::new(py, vec![stmt]).unwrap();
            return Ok((list.into(), last_tok));
        }
    }

    input.reset(&checkpoint);

    // Option 2: ';'.simple_stmt+ [';'] NEWLINE

    if let Ok(stmts) = separated(1.., parse_simple_stmt, op(b";")).parse_next(input) {
        let mut last_tok = start_tokens[start_tokens.len() - input.input.len() - 1].clone();
        if let Ok(semi) = opt(op(b";")).parse_next(input) {
            if semi.is_some() {
                last_tok = start_tokens[start_tokens.len() - input.input.len() - 1].clone();
            }
        }
        if let Ok(_) = parse_newline(input) {
            let stmts_vec: Vec<Py<PyAny>> = stmts;
            let py = input.state.py;
            let list = PyList::new(py, stmts_vec).unwrap();
            return Ok((list.into(), last_tok));
        }
    }

    Err(ErrMode::Backtrack(ContextError::new()))
}

// compound_stmt:
//     | &('def' | '@' | 'async') function_def
//     | &'if' if_stmt
//     ...
pub fn parse_compound_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<(Py<PyAny>, TokInfo)> {
    if peek(kw(b"if")).parse_next(input).is_ok() {
        return parse_if_stmt(input);
    }
    if peek(kw(b"while")).parse_next(input).is_ok() {
        return parse_while_stmt(input);
    }
    if peek(kw(b"class")).parse_next(input).is_ok() {
        return parse_class_def(input);
    }

    if peek(|i: &mut TokenStream<'s>| parse_token_type(i, Token::ASYNC))
        .parse_next(input)
        .is_ok()
    {
        let checkpoint = input.checkpoint();
        let _ = parse_token_type(input, Token::ASYNC)?;
        if peek(kw(b"def")).parse_next(input).is_ok() {
            input.reset(&checkpoint);
            return parse_function_def(input);
        }
        if peek(kw(b"for")).parse_next(input).is_ok() {
            input.reset(&checkpoint);
            return parse_for_stmt(input);
        }
        if peek(kw(b"with")).parse_next(input).is_ok() {
            input.reset(&checkpoint);
            return parse_with_stmt(input);
        }
        input.reset(&checkpoint);
    }

    if peek(op(b"@")).parse_next(input).is_ok() {
        let checkpoint = input.checkpoint();
        let _ = parse_decorators(input)?;
        let is_class = peek(kw(b"class")).parse_next(input).is_ok();
        input.reset(&checkpoint);
        if is_class {
            return parse_class_def(input);
        } else {
            return parse_function_def(input);
        }
    }

    if peek(kw(b"def")).parse_next(input).is_ok() {
        return parse_function_def(input);
    }

    if peek(kw(b"for")).parse_next(input).is_ok() {
        return parse_for_stmt(input);
    }
    if peek(kw(b"try")).parse_next(input).is_ok() {
        return parse_try_stmt(input);
    }
    if peek(kw(b"with")).parse_next(input).is_ok() {
        return parse_with_stmt(input);
    }
    if peek(kw(b"match")).parse_next(input).is_ok() {
        return parse_match_stmt(input);
    }

    Err(ErrMode::Backtrack(ContextError::new()))
}
// decorators: ('@' named_expression NEWLINE)+
fn parse_decorators<'s>(input: &mut TokenStream<'s>) -> ModalResult<Vec<Py<PyAny>>> {
    let mut decs = Vec::new();
    while peek(op(b"@")).parse_next(input).is_ok() {
        let _ = op(b"@").parse_next(input)?;
        let expr = parse_named_expression(input)?;
        let _ = parse_newline(input)?;
        decs.push(expr);
    }
    Ok(decs)
}

// param_def: NAME annotation? ['=' expression]
fn parse_param_def<'s>(input: &mut TokenStream<'s>) -> ModalResult<(Py<PyAny>, Option<Py<PyAny>>)> {
    let start_input = input.clone();
    let name_tok = parse_name(input)?;
    let name_bytes = get_text(input, &name_tok);
    let name = std::str::from_utf8(name_bytes).unwrap();

    let annotation = if peek(op(b":")).parse_next(input).is_ok() {
        let _ = op(b":").parse_next(input)?;
        Some(parse_expression(input)?)
    } else {
        None
    };

    let consumed = start_input.input.len() - input.input.len();
    let end_tok = start_input.input[consumed - 1].clone();

    let default = if peek(op(b"=")).parse_next(input).is_ok() {
        let _ = op(b"=").parse_next(input)?;
        Some(parse_expression(input)?)
    } else {
        None
    };

    let py = input.state.py;
    let ast = input.state.ast.clone();
    let ann_obj = match annotation {
        Some(a) => a,
        None => py.None(),
    };

    let node = ast
        .call_method1("arg", (name, ann_obj, py.None()))
        .map_err(|_| make_error("arg failed".into()))?;
    set_location(&node, &name_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;

    Ok((node.into(), default))
}

fn parse_params<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let mut posonlyargs = Vec::new();
    let mut args = Vec::new();
    let mut vararg = None;
    let mut kwonlyargs = Vec::new();
    let mut kw_defaults = Vec::new();
    let mut kwarg = None;
    let mut defaults = Vec::new();

    let py = input.state.py;

    // State machine: 0=Positional, 1=KwOnly
    let mut mode = 0;

    if !peek(op(b")")).parse_next(input).is_ok() && !peek(op(b":")).parse_next(input).is_ok() {
        loop {
            if peek(op(b")")).parse_next(input).is_ok() || peek(op(b":")).parse_next(input).is_ok()
            {
                break;
            }

            if peek(op(b"**")).parse_next(input).is_ok() {
                let _ = op(b"**").parse_next(input)?;
                let (arg, _) = parse_param_def(input)?; // kwarg cannot have default
                kwarg = Some(arg);
                // End of params
                if peek(op(b",")).parse_next(input).is_ok() {
                    let _ = op(b",").parse_next(input)?;
                }
                break;
            }

            if peek(op(b"*")).parse_next(input).is_ok() {
                if mode == 1 {
                    return Err(ErrMode::Backtrack(ContextError::new())); // Double *
                }
                let _ = op(b"*").parse_next(input)?;
                mode = 1; // Switch to KwOnly

                // Check if distinct vararg name exists: *args vs *
                if peek(parse_name).parse_next(input).is_ok() {
                    let (arg, _) = parse_param_def(input)?;
                    vararg = Some(arg);
                } else {
                    // It is just *, separator. vararg remains None.
                }

                if peek(op(b",")).parse_next(input).is_ok() {
                    let _ = op(b",").parse_next(input)?;
                    continue;
                } else {
                    break;
                }
            }

            let (p_arg, p_def) = parse_param_def(input)?;

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
                // No comma. Could be end `)` OR `/` then end.
                if mode == 0 && peek(op(b"/")).parse_next(input).is_ok() {
                    let _ = op(b"/").parse_next(input)?;
                    seen_slash = true;
                    // Check for comma after slash
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

            if peek(op(b")")).parse_next(input).is_ok() {
                break;
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
    Ok(node.into())
}

// function_def
fn parse_function_def<'s>(input: &mut TokenStream<'s>) -> ModalResult<(Py<PyAny>, TokInfo)> {
    let tokens = input.input;
    let _start_tok = tokens[0].clone();

    let decorators = parse_decorators(input)?;
    let func_start_tok = tokens[tokens.len() - input.input.len()].clone();

    let is_async = if peek(|i: &mut TokenStream<'s>| parse_token_type(i, Token::ASYNC))
        .parse_next(input)
        .is_ok()
    {
        let _ = parse_token_type(input, Token::ASYNC)?;
        true
    } else {
        false
    };

    let _ = kw(b"def").parse_next(input)?;
    let name_tok = parse_name(input)?;
    let name_bytes = get_text(input, &name_tok);
    let name = std::str::from_utf8(name_bytes).unwrap();

    // TODO: type_params

    let _ = op(b"(").parse_next(input)?;
    let args = opt(parse_params).parse_next(input)?;
    let _ = op(b")").parse_next(input)?;

    let returns = if peek(op(b"->")).parse_next(input).is_ok() {
        let _ = op(b"->").parse_next(input)?;
        Some(parse_expression(input)?)
    } else {
        None
    };

    let _ = op(b":").parse_next(input)?;

    // TODO: func_type_comment

    let (body, body_end_tok) = parse_block(input)?;

    let py = input.state.py;
    let ast = input.state.ast.clone();

    let decorator_list = PyList::new(py, decorators).unwrap();

    // args default to empty if None
    let args_obj = match args {
        Some(a) => a,
        None => {
            let empty = PyList::empty(py);
            ast.call_method1(
                "arguments",
                (
                    empty.clone(),
                    empty.clone(),
                    py.None(),
                    empty.clone(),
                    empty.clone(),
                    py.None(),
                    empty,
                ),
            )
            .map_err(|_| make_error("arguments default failed".into()))?
            .into()
        }
    };

    let returns_obj = match returns {
        Some(r) => r,
        None => py.None().into(),
    };

    let func_cls_name = if is_async {
        "AsyncFunctionDef"
    } else {
        "FunctionDef"
    };

    // FunctionDef(name, args, body, decorator_list, returns, type_comment=None, type_params=[])
    let node = ast
        .call_method1(
            func_cls_name,
            (name, args_obj, body, decorator_list, returns_obj),
        )
        .map_err(|_| make_error(format!("{} failed", func_cls_name).into()))?;

    set_location(&node, &func_start_tok, &body_end_tok)
        .map_err(|e| make_error(format!("Failed to set location: {}", e).into()))?;

    Ok((node.into(), body_end_tok))
}

fn parse_class_def<'s>(input: &mut TokenStream<'s>) -> ModalResult<(Py<PyAny>, TokInfo)> {
    let tokens = input.input;
    let _start_tok = tokens[0].clone();

    let decorators = parse_decorators(input)?;
    let class_start_tok = tokens[tokens.len() - input.input.len()].clone();

    let _ = kw(b"class").parse_next(input)?;
    let name_tok = parse_name(input)?;
    let name_bytes = get_text(input, &name_tok);
    let name = std::str::from_utf8(name_bytes).unwrap();

    // type_params?

    let (args, keywords) = if peek(op(b"(")).parse_next(input).is_ok() {
        let _ = op(b"(").parse_next(input)?;
        let res = parse_arguments(input)?;
        let _ = op(b")").parse_next(input)?;
        res
    } else {
        let py = input.state.py;
        (PyList::empty(py).into(), PyList::empty(py).into())
    };

    let _ = op(b":").parse_next(input)?;
    let (body, body_end_tok) = parse_block(input)?;

    let py = input.state.py;
    let ast = input.state.ast.clone();
    let deco_list = PyList::new(py, decorators).unwrap();

    // ClassDef(name, bases, keywords, body, decorator_list, type_params=[])
    let node = ast
        .call_method1("ClassDef", (name, args, keywords, body, deco_list))
        .map_err(|_| make_error("ClassDef failed".into()))?;

    set_location(&node, &class_start_tok, &body_end_tok)
        .map_err(|e| make_error(format!("Failed to set location: {}", e).into()))?;

    Ok((node.into(), body_end_tok))
}

// if_stmt[ast.If]:
//     | 'if' a=named_expression ':' b=block c=elif_stmt { ast.If(test=a, body=b, orelse=c or [], LOCATIONS) }
//     | 'if' a=named_expression ':' b=block c=[else_block] { ast.If(test=a, body=b, orelse=c or [], LOCATIONS) }
fn parse_if_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<(Py<PyAny>, TokInfo)> {
    let tokens = input.input;
    let start_tok = tokens[0].clone();
    let _ = kw(b"if").parse_next(input)?;
    let a = parse_named_expression(input)?;
    let _ = op(b":").parse_next(input)?;
    let (b, mut end_tok) = parse_block(input)?;

    let py = input.state.py;
    let ast = input.state.ast.clone();

    let orelse = if peek(kw(b"elif")).parse_next(input).is_ok() {
        let (elif_node, elif_end) = parse_elif_stmt(input)?;
        end_tok = elif_end;
        PyList::new(py, vec![elif_node]).unwrap().into()
    } else if peek(kw(b"else")).parse_next(input).is_ok() {
        let (else_body, else_end) = parse_else_block(input)?;
        end_tok = else_end;
        else_body
    } else {
        PyList::empty(py).into()
    };

    let node = ast
        .call_method1("If", (a, b, orelse))
        .map_err(|_| make_error("if creation failed".into()))?;
    set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
    Ok((node.into(), end_tok))
}

fn parse_elif_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<(Py<PyAny>, TokInfo)> {
    let tokens = input.input;
    let start_tok = tokens[0].clone();
    let _ = kw(b"elif").parse_next(input)?;
    let a = parse_named_expression(input)?;
    let _ = op(b":").parse_next(input)?;
    let (b, mut end_tok) = parse_block(input)?;

    let py = input.state.py;
    let ast = input.state.ast.clone();

    let orelse = if peek(kw(b"elif")).parse_next(input).is_ok() {
        let (elif_node, elif_end) = parse_elif_stmt(input)?;
        end_tok = elif_end;
        PyList::new(py, vec![elif_node]).unwrap().into()
    } else if peek(kw(b"else")).parse_next(input).is_ok() {
        let (else_body, else_end) = parse_else_block(input)?;
        end_tok = else_end;
        else_body
    } else {
        PyList::empty(py).into()
    };

    let node = ast
        .call_method1("If", (a, b, orelse))
        .map_err(|_| make_error("elif creation failed".into()))?;
    set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
    Ok((node.into(), end_tok))
}

fn parse_else_block<'s>(input: &mut TokenStream<'s>) -> ModalResult<(Py<PyAny>, TokInfo)> {
    let _ = kw(b"else").parse_next(input)?;
    let _ = cut_err(op(b":")).parse_next(input)?;
    parse_block(input)
}

// while_stmt
fn parse_while_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<(Py<PyAny>, TokInfo)> {
    let tokens = input.input;
    let start_tok = tokens[0].clone();
    let _ = kw(b"while").parse_next(input)?;
    let test = parse_named_expression(input)?;
    let _ = op(b":").parse_next(input)?;
    let (body, mut body_end_tok) = parse_block(input)?;
    let orelse_block = opt(parse_else_block).parse_next(input)?;

    let py = input.state.py;
    let ast = input.state.ast.clone();
    let orelse = match orelse_block {
        Some((b, end)) => {
            body_end_tok = end;
            b
        }
        None => PyList::empty(py).into(),
    };

    let node = ast
        .call_method1("While", (test, body, orelse))
        .map_err(|_| make_error("While failed".into()))?;
    set_location(&node, &start_tok, &body_end_tok).map_err(|e| make_error(e.to_string()))?;
    Ok((node.into(), body_end_tok))
}

// for_stmt
fn parse_for_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<(Py<PyAny>, TokInfo)> {
    let tokens = input.input;
    let start_tok = tokens[0].clone();
    let is_async = if peek(|i: &mut TokenStream<'s>| parse_token_type(i, Token::ASYNC))
        .parse_next(input)
        .is_ok()
    {
        let _ = parse_token_type(input, Token::ASYNC)?;
        true
    } else {
        false
    };

    let _ = kw(b"for").parse_next(input)?;
    let target = parse_star_targets(input)?;
    let _ = kw(b"in").parse_next(input)?;
    let iter = parse_star_expressions(input)?;
    let _ = op(b":").parse_next(input)?;
    let (body, mut body_end_tok) = parse_block(input)?;
    let orelse_block = opt(parse_else_block).parse_next(input)?;

    let py = input.state.py;
    let ast = input.state.ast.clone();

    let store = ctx_store(&ast)?;
    set_context(py, &target, store)?;

    let orelse = match orelse_block {
        Some((b, end)) => {
            body_end_tok = end;
            b
        }
        None => PyList::empty(py).into(),
    };

    let cls_name = if is_async { "AsyncFor" } else { "For" };

    let node = ast
        .call_method1(cls_name, (target, iter, body, orelse))
        .map_err(|_| make_error(format!("{} failed", cls_name).into()))?;
    set_location(&node, &start_tok, &body_end_tok).map_err(|e| make_error(e.to_string()))?;
    Ok((node.into(), body_end_tok))
}

// with_item: expression ['as' star_target]
fn parse_with_item<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let context_expr = parse_expression(input)?;
    let optional_vars = if peek(kw(b"as")).parse_next(input).is_ok() {
        let _ = kw(b"as").parse_next(input)?;
        let target = parse_star_target(input)?;
        let py = input.state.py;
        let ast = input.state.ast.clone();
        set_context(py, &target, ctx_store(&ast)?)?;
        Some(target)
    } else {
        None
    };

    let py = input.state.py;
    let ast = input.state.ast.clone();
    let vars = match optional_vars {
        Some(v) => v,
        None => py.None().into(),
    };

    let node = ast
        .call_method1("withitem", (context_expr, vars))
        .map_err(|_| make_error("withitem failed".into()))?;
    Ok(node.into())
}

// with_stmt
fn parse_with_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<(Py<PyAny>, TokInfo)> {
    let tokens = input.input;
    let start_tok = tokens[0].clone();
    let is_async = if peek(|i: &mut TokenStream<'s>| parse_token_type(i, Token::ASYNC))
        .parse_next(input)
        .is_ok()
    {
        let _ = parse_token_type(input, Token::ASYNC)?;
        true
    } else {
        false
    };

    let _ = kw(b"with").parse_next(input)?;

    let items_list = if peek(op(b"(")).parse_next(input).is_ok() {
        let _ = op(b"(").parse_next(input)?;
        let items = separated(1.., parse_with_item, op(b",")).parse_next(input)?;
        let _ = opt(op(b",")).parse_next(input)?;
        let _ = op(b")").parse_next(input)?;
        items
    } else {
        separated(1.., parse_with_item, op(b",")).parse_next(input)?
    };

    let _: Vec<Py<PyAny>> = items_list;
    let _ = op(b":").parse_next(input)?;

    // type_comment?
    let (body, body_end_tok) = parse_block(input)?;

    let py = input.state.py;
    let ast = input.state.ast.clone();
    let items = PyList::new(py, items_list).unwrap();

    let cls_name = if is_async { "AsyncWith" } else { "With" };
    // With(items, body, type_comment=None)
    let node = ast
        .call_method1(cls_name, (items, body))
        .map_err(|_| make_error(format!("{} failed", cls_name).into()))?;
    set_location(&node, &start_tok, &body_end_tok).map_err(|e| make_error(e.to_string()))?;
    Ok((node.into(), body_end_tok))
}
// try_stmt
fn parse_try_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<(Py<PyAny>, TokInfo)> {
    let tokens = input.input;
    let start_tok = tokens[0].clone();
    let _ = kw(b"try").parse_next(input)?;
    let _ = op(b":").parse_next(input)?;
    let (body, mut body_end_tok) = parse_block(input)?;

    let is_try_star = peek((kw(b"except"), op(b"*"))).parse_next(input).is_ok();

    if is_try_star {
        let mut handlers = Vec::new();
        while peek((kw(b"except"), op(b"*"))).parse_next(input).is_ok() {
            let (h, hend) = parse_except_star_block(input)?;
            handlers.push(h);
            body_end_tok = hend;
        }

        let orelse = if peek(kw(b"else")).parse_next(input).is_ok() {
            let (orelse_body, end) = parse_else_block(input)?;
            body_end_tok = end;
            orelse_body
        } else {
            let py = input.state.py;
            PyList::empty(py).into()
        };

        let finalbody = if peek(kw(b"finally")).parse_next(input).is_ok() {
            let _ = kw(b"finally").parse_next(input)?;
            let _ = op(b":").parse_next(input)?;
            let (fbody, end) = parse_block(input)?;
            body_end_tok = end;
            fbody
        } else {
            let py = input.state.py;
            PyList::empty(py).into()
        };

        let py = input.state.py;
        let ast = input.state.ast.clone();
        let handlers_list = PyList::new(py, handlers).unwrap();

        let node = ast
            .call_method1("TryStar", (body, handlers_list, orelse, finalbody))
            .map_err(|_| make_error("TryStar failed".into()))?;
        set_location(&node, &start_tok, &body_end_tok).map_err(|e| make_error(e.to_string()))?;
        Ok((node.into(), body_end_tok))
    } else {
        let mut handlers = Vec::new();
        while peek(kw(b"except")).parse_next(input).is_ok() {
            let (h, hend) = parse_except_block(input)?;
            handlers.push(h);
            body_end_tok = hend;
        }

        let orelse = if peek(kw(b"else")).parse_next(input).is_ok() {
            let (orelse_body, end) = parse_else_block(input)?;
            body_end_tok = end;
            orelse_body
        } else {
            let py = input.state.py;
            PyList::empty(py).into()
        };

        let finalbody = if peek(kw(b"finally")).parse_next(input).is_ok() {
            let _ = kw(b"finally").parse_next(input)?;
            let _ = op(b":").parse_next(input)?;
            let (fbody, end) = parse_block(input)?;
            body_end_tok = end;
            fbody
        } else {
            let py = input.state.py;
            PyList::empty(py).into()
        };

        let py = input.state.py;
        let ast = input.state.ast.clone();
        let handlers_list = PyList::new(py, handlers).unwrap();

        let node = ast
            .call_method1("Try", (body, handlers_list, orelse, finalbody))
            .map_err(|_| make_error("Try failed".into()))?;
        set_location(&node, &start_tok, &body_end_tok).map_err(|e| make_error(e.to_string()))?;
        Ok((node.into(), body_end_tok))
    }
}

// except_block
fn parse_except_block<'s>(input: &mut TokenStream<'s>) -> ModalResult<(Py<PyAny>, TokInfo)> {
    let tokens = input.input;
    let start_tok = tokens[0].clone();
    let _ = kw(b"except").parse_next(input)?;
    let type_name = opt((parse_expression, opt((kw(b"as"), parse_name)))).parse_next(input)?;

    let py = input.state.py;
    let (typ, name) = match type_name {
        Some((t, n_opt)) => {
            let n = match n_opt {
                Some((_, name_tok)) => {
                    let txt_bytes = get_text(input, &name_tok);
                    let txt = std::str::from_utf8(txt_bytes).unwrap();
                    pyo3::types::PyString::new(py, txt).into()
                }
                None => py.None(),
            };
            (t, n)
        }
        None => (py.None(), py.None()),
    };

    let _ = op(b":").parse_next(input)?;
    let (body, body_end_tok) = parse_block(input)?;

    let _py = input.state.py;
    let ast = input.state.ast.clone();
    let node = ast
        .call_method1("ExceptHandler", (typ, name, body))
        .map_err(|_| make_error("ExceptHandler failed".into()))?;
    set_location(&node, &start_tok, &body_end_tok).map_err(|e| make_error(e.to_string()))?;
    Ok((node.into(), body_end_tok))
}

fn parse_except_star_block<'s>(input: &mut TokenStream<'s>) -> ModalResult<(Py<PyAny>, TokInfo)> {
    let tokens = input.input;
    let start_tok = tokens[0].clone();
    let _ = kw(b"except").parse_next(input)?;
    let _ = op(b"*").parse_next(input)?;

    let (typ, name) = {
        let (t, n_opt) = (parse_expression, opt((kw(b"as"), parse_name))).parse_next(input)?;
        let n: Py<PyAny> = if let Some((_, name_tok)) = n_opt {
            let txt_bytes = get_text(input, &name_tok);
            let txt = std::str::from_utf8(txt_bytes).unwrap();
            let py = input.state.py;
            pyo3::types::PyString::new(py, txt).into()
        } else {
            let py = input.state.py;
            py.None().into()
        };
        (t, n)
    };

    let _ = op(b":").parse_next(input)?;
    let (body, body_end_tok) = parse_block(input)?;

    let _py = input.state.py;
    let ast = input.state.ast.clone();

    let node = ast
        .call_method1("ExceptHandler", (typ, name, body))
        .map_err(|_| make_error("ExceptHandler star failed".into()))?;
    set_location(&node, &start_tok, &body_end_tok).map_err(|e| make_error(e.to_string()))?;
    Ok((node.into(), body_end_tok))
}

// match_stmt: "match" subject_expr ':' NEWLINE INDENT case_block+ DEDENT
fn parse_match_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<(Py<PyAny>, TokInfo)> {
    let tokens = input.input;
    let start_tok = tokens[0].clone();
    let _ = kw(b"match").parse_next(input)?;

    let subject = parse_testlist(input)?;

    let _ = op(b":").parse_next(input)?;
    let _ = parse_newline(input)?;
    let _ = parse_indent(input)?;

    let blocks_result: Vec<_> = repeat(1.., parse_case_block).parse_next(input)?;
    let mut blocks = Vec::new();
    let mut last_tok = start_tok.clone();
    for (b, t) in blocks_result {
        blocks.push(b);
        last_tok = t;
    }

    let _ = parse_dedent(input)?;

    let py = input.state.py;
    let ast = input.state.ast.clone();
    let cases = PyList::new(py, blocks).unwrap();

    let node = ast
        .call_method1("Match", (subject, cases))
        .map_err(|_| make_error("Match failed".into()))?;
    set_location(&node, &start_tok, &last_tok).map_err(|e| make_error(e.to_string()))?;
    Ok((node.into(), last_tok))
}

// case_block: "case" patterns [guard] ':' block
fn parse_case_block<'s>(input: &mut TokenStream<'s>) -> ModalResult<(Py<PyAny>, TokInfo)> {
    let tokens = input.input;
    let start_tok = tokens[0].clone();
    let _ = kw(b"case").parse_next(input)?;
    let pattern = parse_pattern_top(input)?;

    let guard = if peek(kw(b"if")).parse_next(input).is_ok() {
        let _ = kw(b"if").parse_next(input)?;
        Some(parse_named_expression(input)?)
    } else {
        None
    };

    let _ = op(b":").parse_next(input)?;
    let (body, body_end_tok) = parse_block(input)?;

    let py = input.state.py;
    let ast = input.state.ast.clone();
    let guard_obj = match guard {
        Some(g) => g,
        None => py.None(),
    };

    let node = ast
        .call_method1("match_case", (pattern, guard_obj, body))
        .map_err(|_| make_error("match_case failed".into()))?;
    set_location(&node, &start_tok, &body_end_tok).map_err(|e| make_error(e.to_string()))?;
    Ok((node.into(), body_end_tok))
}

// Top-level pattern (allows open sequence like 'case a, b:')
fn parse_pattern_top<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    parse_pattern(input)
}

fn parse_pattern<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let p = parse_or_pattern(input)?;

    if peek(kw(b"as")).parse_next(input).is_ok() {
        let _ = kw(b"as").parse_next(input)?;
        let name_tok = parse_name(input)?; // capture target
        let name_bytes = get_text(input, &name_tok);
        let name = std::str::from_utf8(name_bytes).unwrap();

        let _py = input.state.py;
        let ast = input.state.ast.clone();
        let node = ast.call_method1("MatchAs", (p, name)).unwrap();
        return Ok(node.into());
    }

    Ok(p)
}

fn parse_or_pattern<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let first = parse_closed_pattern(input)?;
    let mut rest = Vec::new();

    while peek(op(b"|")).parse_next(input).is_ok() {
        let _ = op(b"|").parse_next(input)?;
        let next = parse_closed_pattern(input)?;
        rest.push(next);
    }

    if rest.is_empty() {
        Ok(first)
    } else {
        let mut patterns = vec![first];
        patterns.extend(rest);
        let py = input.state.py;
        let ast = input.state.ast.clone();
        let list = PyList::new(py, patterns).unwrap();
        let node = ast.call_method1("MatchOr", (list,)).unwrap();
        Ok(node.into())
    }
}

fn parse_closed_pattern<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let py = input.state.py;
    let ast = input.state.ast.clone();

    // Check Literals
    if peek(parse_number).parse_next(input).is_ok() {
        let tok = parse_number(input)?;
        let text = get_text(input, &tok);
        let text_str = std::str::from_utf8(text).unwrap();
        let val = match text_str.parse::<i64>() {
            Ok(i) => i.into_pyobject(py).unwrap().into_any().unbind(),
            Err(_) => text_str.into_pyobject(py).unwrap().into_any().unbind(),
        };
        let const_node = ast.call_method1("Constant", (val,)).unwrap();
        let node = ast.call_method1("MatchValue", (const_node,)).unwrap();
        return Ok(node.into());
    }
    if peek(parse_string).parse_next(input).is_ok() {
        let tok = parse_string(input)?;
        let text = get_text(input, &tok);
        let text_str = std::str::from_utf8(text).unwrap();
        let val = ast.call_method1("literal_eval", (text_str,)).unwrap();
        let const_node = ast.call_method1("Constant", (val,)).unwrap();
        let node = ast.call_method1("MatchValue", (const_node,)).unwrap();
        return Ok(node.into());
    }
    if peek(kw(b"None")).parse_next(input).is_ok() {
        let _ = kw(b"None").parse_next(input)?;
        let val = py.None();
        let const_node = ast.call_method1("Constant", (val,)).unwrap();
        let node = ast.call_method1("MatchSingleton", (const_node,)).unwrap();
        return Ok(node.into());
    }
    if peek(kw(b"True")).parse_next(input).is_ok() {
        let _ = kw(b"True").parse_next(input)?;
        let val = true;
        let const_node = ast.call_method1("Constant", (val,)).unwrap();
        let node = ast.call_method1("MatchSingleton", (const_node,)).unwrap();
        return Ok(node.into());
    }
    if peek(kw(b"False")).parse_next(input).is_ok() {
        let _ = kw(b"False").parse_next(input)?;
        let val = false;
        let const_node = ast.call_method1("Constant", (val,)).unwrap();
        let node = ast.call_method1("MatchSingleton", (const_node,)).unwrap();
        return Ok(node.into());
    }

    // Check Group/Sequence [ ]
    if peek(op(b"[")).parse_next(input).is_ok() {
        let _ = op(b"[").parse_next(input)?;
        let patterns: Vec<Py<PyAny>> = separated(0.., parse_pattern, op(b",")).parse_next(input)?;
        let _ = op(b"]").parse_next(input)?;
        let list = PyList::new(py, patterns).unwrap();
        let node = ast.call_method1("MatchSequence", (list,)).unwrap();
        return Ok(node.into());
    }

    // Check Wildcard / Capture / Value
    if peek(parse_name).parse_next(input).is_ok() {
        let name_tok = parse_name(input)?;
        let name_bytes = get_text(input, &name_tok);
        let name = std::str::from_utf8(name_bytes).unwrap();

        if name == "_" {
            let node = ast.call_method1("MatchAs", (py.None(), py.None())).unwrap();
            return Ok(node.into());
        }

        let node = ast.call_method1("MatchAs", (py.None(), name)).unwrap();
        Ok(node.into())
    } else {
        Err(ErrMode::Backtrack(ContextError::new()))
    }
}

// Helpers for testlist (tuple parsing) needed for subject
fn parse_testlist<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let first = parse_expression(input)?;
    if peek(op(b",")).parse_next(input).is_ok() {
        let mut elts = vec![first];
        while peek(op(b",")).parse_next(input).is_ok() {
            let _ = op(b",").parse_next(input)?;
            if peek(parse_expression).parse_next(input).is_ok() {
                let next = parse_expression(input)?;
                elts.push(next);
            }
        }
        let py = input.state.py;
        let ast = input.state.ast.clone();
        let list = PyList::new(py, elts).unwrap();
        // Tuple(elts, Load)
        let ctx = ctx_load(&ast)?;
        let node = ast.call_method1("Tuple", (list, ctx)).unwrap();
        Ok(node.into())
    } else {
        Ok(first)
    }
}

pub fn parse_simple_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let tokens = input.input;
    let start_tok = tokens[0].clone();

    // pass
    if peek(kw(b"pass")).parse_next(input).is_ok() {
        let tok = kw(b"pass").parse_next(input)?;
        let ast = input.state.ast.clone();
        let node = ast
            .call_method0("Pass")
            .map_err(|_| make_error("Pass failed".into()))?;
        set_location(&node, &tok, &tok)
            .map_err(|e| make_error(format!("Failed to set location: {}", e).into()))?;
        return Ok(node.into());
    }

    if peek(kw(b"break")).parse_next(input).is_ok() {
        return parse_break_stmt(input);
    }
    if peek(kw(b"continue")).parse_next(input).is_ok() {
        return parse_continue_stmt(input);
    }
    if peek(kw(b"return")).parse_next(input).is_ok() {
        return parse_return_stmt(input);
    }
    if peek(kw(b"raise")).parse_next(input).is_ok() {
        return parse_raise_stmt(input);
    }
    if peek(kw(b"global")).parse_next(input).is_ok() {
        return parse_global_stmt(input);
    }
    if peek(kw(b"nonlocal")).parse_next(input).is_ok() {
        return parse_nonlocal_stmt(input);
    }
    if peek(kw(b"assert")).parse_next(input).is_ok() {
        return parse_assert_stmt(input);
    }
    if peek(kw(b"import")).parse_next(input).is_ok() {
        return parse_import_stmt(input);
    }
    if peek(kw(b"from")).parse_next(input).is_ok() {
        return parse_import_from_stmt(input);
    }
    if peek(kw(b"del")).parse_next(input).is_ok() {
        return parse_del_stmt(input);
    }

    // Assignment?
    let checkpoint = input.checkpoint();
    if let Ok(assign) = parse_assignment(input) {
        return Ok(assign);
    }
    input.reset(&checkpoint);

    // Default to star_expressions (expr)
    let e = parse_star_expressions(input)?;

    let end_tok = tokens[tokens.len() - input.input.len() - 1].clone();
    let ast = input.state.ast.clone();
    let node = ast
        .call_method1("Expr", (e,))
        .map_err(|_| make_error("Expr failed".into()))?;

    set_location(&node, &start_tok, &end_tok)
        .map_err(|e| make_error(format!("Failed to set location: {}", e).into()))?;

    Ok(node.into())
}

fn parse_break_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let tokens = input.input;
    let start_tok = tokens[0].clone();
    let _ = kw(b"break").parse_next(input)?;
    let py = input.state.py;
    let ast = input.state.ast.clone();
    let node = ast
        .call_method0("Break")
        .map_err(|_| make_error("Break failed".into()))?;
    set_location(&node, &start_tok, &start_tok).map_err(|e| make_error(e.to_string()))?;
    Ok(node.into())
}

fn parse_continue_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let tokens = input.input;
    let start_tok = tokens[0].clone();
    let _ = kw(b"continue").parse_next(input)?;
    let py = input.state.py;
    let ast = input.state.ast.clone();
    let node = ast
        .call_method0("Continue")
        .map_err(|_| make_error("Continue failed".into()))?;
    set_location(&node, &start_tok, &start_tok).map_err(|e| make_error(e.to_string()))?;
    Ok(node.into())
}

fn parse_return_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let tokens = input.input;
    let start_tok = tokens[0].clone();
    let _ = kw(b"return").parse_next(input)?;

    // return [testlist]
    // If next is newline or semi, value is None.
    let value = if !peek(parse_newline).parse_next(input).is_ok()
        && !peek(op(b";")).parse_next(input).is_ok()
        && !peek(parse_dedent).parse_next(input).is_ok()
    {
        Some(parse_star_expressions(input)?) // Logic says testlist, but effectively expression/tuple
    } else {
        None
    };

    let consumed = tokens.len() - input.input.len();
    let end_tok = tokens[consumed - 1].clone(); // approx

    let py = input.state.py;
    let ast = input.state.ast.clone();
    let val_obj = match value {
        Some(v) => v,
        None => py.None(),
    };

    let node = ast
        .call_method1("Return", (val_obj,))
        .map_err(|_| make_error("Return failed".into()))?;
    set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
    Ok(node.into())
}

fn parse_raise_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let tokens = input.input;
    let start_tok = tokens[0].clone();
    let _ = kw(b"raise").parse_next(input)?;

    let exc = if !peek(parse_newline).parse_next(input).is_ok()
        && !peek(op(b";")).parse_next(input).is_ok()
    {
        Some(parse_expression(input)?)
    } else {
        None
    };

    let cause = if exc.is_some() && peek(kw(b"from")).parse_next(input).is_ok() {
        let _ = kw(b"from").parse_next(input)?;
        Some(parse_expression(input)?)
    } else {
        None
    };

    let consumed = tokens.len() - input.input.len();
    let end_tok = tokens[consumed - 1].clone();

    let py = input.state.py;
    let ast = input.state.ast.clone();
    let exc_obj = match exc {
        Some(e) => e,
        None => py.None(),
    };
    let cause_obj_final = match cause {
        Some(c) => c,
        None => py.None(),
    };

    let node = ast
        .call_method1("Raise", (exc_obj, cause_obj_final))
        .map_err(|_| make_error("Raise failed".into()))?;
    set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
    Ok(node.into())
}

// Rewriting parse_global_stmt properly
fn parse_global_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let tokens = input.input;
    let start_tok = tokens[0].clone();
    let _ = kw(b"global").parse_next(input)?;

    let mut names = Vec::new();
    loop {
        let tok = parse_name(input)?;
        let text = get_text(input, &tok);
        let s = std::str::from_utf8(text).unwrap();
        names.push(s);
        if peek(op(b",")).parse_next(input).is_ok() {
            let _ = op(b",").parse_next(input)?;
        } else {
            break;
        }
    }

    let end_tok = tokens[tokens.len() - input.input.len() - 1].clone();

    let py = input.state.py;
    let ast = input.state.ast.clone();
    let list = PyList::new(py, names).unwrap();

    let node = ast
        .call_method1("Global", (list,))
        .map_err(|_| make_error("Global failed".into()))?;
    set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
    Ok(node.into())
}

fn parse_nonlocal_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let tokens = input.input;
    let start_tok = tokens[0].clone();
    let _ = kw(b"nonlocal").parse_next(input)?;

    let mut names = Vec::new();
    loop {
        let tok = parse_name(input)?;
        let text = get_text(input, &tok);
        let s = std::str::from_utf8(text).unwrap();
        names.push(s);
        if peek(op(b",")).parse_next(input).is_ok() {
            let _ = op(b",").parse_next(input)?;
        } else {
            break;
        }
    }

    let end_tok = tokens[tokens.len() - input.input.len() - 1].clone();

    let py = input.state.py;
    let ast = input.state.ast.clone();
    let list = PyList::new(py, names).unwrap();

    let node = ast
        .call_method1("Nonlocal", (list,))
        .map_err(|_| make_error("Nonlocal failed".into()))?;
    set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
    Ok(node.into())
}

fn parse_assert_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let tokens = input.input;
    let start_tok = tokens[0].clone();
    let _ = kw(b"assert").parse_next(input)?;
    let test = parse_expression(input)?;
    let msg = if peek(op(b",")).parse_next(input).is_ok() {
        let _ = op(b",").parse_next(input)?;
        Some(parse_expression(input)?)
    } else {
        None
    };

    let end_tok = tokens[tokens.len() - input.input.len() - 1].clone();
    let py = input.state.py;
    let ast = input.state.ast.clone();
    let msg_obj = match msg {
        Some(m) => m,
        None => py.None(),
    };

    let node = ast
        .call_method1("Assert", (test, msg_obj))
        .map_err(|_| make_error("Assert failed".into()))?;
    set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
    Ok(node.into())
}

fn parse_del_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let tokens = input.input;
    let start_tok = tokens[0].clone();
    let _ = kw(b"del").parse_next(input)?;
    let targets = parse_star_targets(input)?; // In del, targets must be loaded as Del context?
                                              // star_targets logic uses ctx_load (or store if we switch).
                                              // We need to switch context to Del.

    let py = input.state.py;
    let ast = input.state.ast.clone();
    let del_ctx = ctx_del(&ast)?;
    set_context(py, &targets, del_ctx)?;

    let end_tok = tokens[tokens.len() - input.input.len() - 1].clone();
    let node = ast
        .call_method1("Delete", (targets,))
        .map_err(|_| make_error("Delete failed".into()))?;
    set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
    Ok(node.into())
}

fn parse_dotted_name<'s>(input: &mut TokenStream<'s>) -> ModalResult<String> {
    let mut name = String::new();
    let tok = parse_name(input)?;
    let text = get_text(input, &tok);
    name.push_str(std::str::from_utf8(text).unwrap());

    while peek(op(b".")).parse_next(input).is_ok() {
        let _ = op(b".").parse_next(input)?;
        name.push('.');
        let tok = parse_name(input)?;
        let text = get_text(input, &tok);
        name.push_str(std::str::from_utf8(text).unwrap());
    }
    Ok(name)
}

fn parse_import_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let tokens = input.input;
    let start_tok = tokens[0].clone();
    let _ = kw(b"import").parse_next(input)?;

    // dotted_name [as NAME] (, ...)
    let mut names = Vec::new();
    loop {
        let name = parse_dotted_name(input)?;
        let asname = if peek(kw(b"as")).parse_next(input).is_ok() {
            let _ = kw(b"as").parse_next(input)?;
            let tok = parse_name(input)?;
            let text = get_text(input, &tok);
            Some(std::str::from_utf8(text).unwrap().to_string())
        } else {
            None
        };

        let py = input.state.py;
        let ast = input.state.ast.clone();
        let name_obj = PyString::new(py, &name);
        let asname_obj = match asname {
            Some(s) => PyString::new(py, &s).into(),
            None => py.None(),
        };

        let alias = ast
            .call_method1("alias", (name_obj, asname_obj))
            .map_err(|_| make_error("alias failed".into()))?;
        names.push(alias);

        if peek(op(b",")).parse_next(input).is_ok() {
            let _ = op(b",").parse_next(input)?;
        } else {
            break;
        }
    }

    let end_tok = tokens[tokens.len() - input.input.len() - 1].clone();
    let py = input.state.py;
    let ast = input.state.ast.clone();
    let names_list = PyList::new(py, names).unwrap();

    let node = ast
        .call_method1("Import", (names_list,))
        .map_err(|_| make_error("Import failed".into()))?;
    set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
    Ok(node.into())
}

fn parse_import_from_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let tokens = input.input;
    let start_tok = tokens[0].clone();
    let _ = kw(b"from").parse_next(input)?;

    let mut level = 0;
    while peek(op(b".")).parse_next(input).is_ok() {
        let _ = op(b".").parse_next(input)?;
        level += 1;
        level += 1;
    }

    if peek(op(b"...")).parse_next(input).is_ok() {
        let _ = op(b"...").parse_next(input)?;
        level += 3;
    } // dots?

    let module = if peek(parse_name).parse_next(input).is_ok() {
        Some(parse_dotted_name(input)?)
    } else {
        None
    };

    let _ = kw(b"import").parse_next(input)?;

    let mut names = Vec::new();
    if peek(op(b"(")).parse_next(input).is_ok() {
        let _ = op(b"(").parse_next(input)?;
        loop {
            // alias: name [as name]
            // Can handle '*' here too? No, * is only allowed if not in parens? Python allows ( * )? No.
            // But `from m import *` is distinct logic.
            // Check for *
            if peek(op(b"*")).parse_next(input).is_ok() {
                // Error: * not allowed in parens? Actually valid in grammar but usually `from m import *` is separate rule.
            }

            let name_tok = parse_name(input)?;
            let text = get_text(input, &name_tok);
            let name = std::str::from_utf8(text).unwrap();

            let asname = if peek(kw(b"as")).parse_next(input).is_ok() {
                let _ = kw(b"as").parse_next(input)?;
                let tok = parse_name(input)?;
                let text = get_text(input, &tok);
                Some(std::str::from_utf8(text).unwrap().to_string())
            } else {
                None
            };

            let py = input.state.py;
            let ast = input.state.ast.clone();
            let name_obj = PyString::new(py, name);
            let asname_obj = match asname {
                Some(s) => PyString::new(py, &s).into(),
                None => py.None(),
            };
            let alias = ast.call_method1("alias", (name_obj, asname_obj)).unwrap();
            names.push(alias);

            if peek(op(b",")).parse_next(input).is_ok() {
                let _ = op(b",").parse_next(input)?;
                if peek(op(b")")).parse_next(input).is_ok() {
                    break;
                }
            } else {
                break;
            }
        }
        let _ = op(b")").parse_next(input)?;
    } else {
        if peek(op(b"*")).parse_next(input).is_ok() {
            let _ = op(b"*").parse_next(input)?;
            let py = input.state.py;
            let ast = input.state.ast.clone();
            let alias = ast
                .call_method1("alias", (PyString::new(py, "*"), py.None()))
                .unwrap();
            names.push(alias);
        } else {
            loop {
                let name_tok = parse_name(input)?;
                let text = get_text(input, &name_tok);
                let name = std::str::from_utf8(text).unwrap();

                let asname = if peek(kw(b"as")).parse_next(input).is_ok() {
                    let _ = kw(b"as").parse_next(input)?;
                    let tok = parse_name(input)?;
                    let text = get_text(input, &tok);
                    Some(std::str::from_utf8(text).unwrap().to_string())
                } else {
                    None
                };

                let py = input.state.py;
                let ast = input.state.ast.clone();
                let name_obj = PyString::new(py, name);
                let asname_obj = match asname {
                    Some(s) => PyString::new(py, &s).into(),
                    None => py.None(),
                };
                let alias = ast.call_method1("alias", (name_obj, asname_obj)).unwrap();
                names.push(alias);

                if peek(op(b",")).parse_next(input).is_ok() {
                    let _ = op(b",").parse_next(input)?;
                } else {
                    break;
                }
            }
        }
    }

    let end_tok = tokens[tokens.len() - input.input.len() - 1].clone();
    let py = input.state.py;
    let ast = input.state.ast.clone();
    let names_list = PyList::new(py, names).unwrap();
    let mod_obj = match module {
        Some(m) => PyString::new(py, &m).into(),
        None => py.None(),
    };

    let node = ast
        .call_method1("ImportFrom", (mod_obj, names_list, level))
        .map_err(|_| make_error("ImportFrom failed".into()))?;
    set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
    Ok(node.into())
}

fn parse_assignment<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    // assignment:
    //     | NAME ':' expression ['=' expression] (AnnAssign)
    //     | (star_targets '=')+ (yield_expr | star_expressions) (Assign)
    //     | single_target augassign (yield_expr | star_expressions) (AugAssign)
    let start_input = input.clone();
    let start_tok = start_input.input[0].clone();

    // Check for AnnAssign: NAME ':'
    // Need to peek NAME then ':'
    // But NAME consumes. using checkpoint.
    let checkpoint = input.checkpoint();
    if let Ok(name_tok) = parse_name.parse_next(input) {
        if peek(op(b":")).parse_next(input).is_ok() {
            let _ = op(b":").parse_next(input)?;
            let annotation = parse_expression(input)?;
            let value = if peek(op(b"=")).parse_next(input).is_ok() {
                let _ = op(b"=").parse_next(input)?;
                Some(parse_expression(input)?)
            } else {
                None
            };
            let end_tok =
                start_input.input[start_input.input.len() - input.input.len() - 1].clone();
            let py = input.state.py;
            let ast = input.state.ast.clone();

            // Name node for target
            let name_bytes = get_text(input, &name_tok);
            let name_str = std::str::from_utf8(name_bytes).unwrap();
            let target = ast
                .call_method1("Name", (name_str, ctx_store(&ast)?))
                .unwrap();
            set_location(&target, &name_tok, &name_tok).unwrap();

            let val_obj = match value {
                Some(v) => v,
                None => py.None(),
            };
            let simple = 1; // simple if it is a single Name

            let node = ast
                .call_method1("AnnAssign", (target, annotation, val_obj, simple))
                .unwrap();
            set_location(&node, &start_tok, &end_tok).unwrap();
            return Ok(node.into());
        }
    }
    input.reset(&checkpoint);

    // Check AugAssign: single_target (+=-=...) value
    // single_target is mostly primary/atom.
    // We can parse_t_primary?
    if let Ok(target) = parse_star_target.parse_next(input) {
        // Check for aug op
        let op_node = if let Ok(_) = op(b"+=").parse_next(input) {
            Some("Add")
        } else if let Ok(_) = op(b"-=").parse_next(input) {
            Some("Sub")
        } else if let Ok(_) = op(b"*=").parse_next(input) {
            Some("Mult")
        } else if let Ok(_) = op(b"/=").parse_next(input) {
            Some("Div")
        } else if let Ok(_) = op(b"//=").parse_next(input) {
            Some("FloorDiv")
        } else if let Ok(_) = op(b"%=").parse_next(input) {
            Some("Mod")
        } else if let Ok(_) = op(b"@=").parse_next(input) {
            Some("MatMult")
        } else if let Ok(_) = op(b"&=").parse_next(input) {
            Some("BitAnd")
        } else if let Ok(_) = op(b"|=").parse_next(input) {
            Some("BitOr")
        } else if let Ok(_) = op(b"^=").parse_next(input) {
            Some("BitXor")
        } else if let Ok(_) = op(b"<<=").parse_next(input) {
            Some("LShift")
        } else if let Ok(_) = op(b">>=").parse_next(input) {
            Some("RShift")
        } else if let Ok(_) = op(b"**=").parse_next(input) {
            Some("Pow")
        } else {
            None
        };

        if let Some(op_name) = op_node {
            let value = parse_expression(input)?; // yield_expr? TODO
            let end_tok =
                start_input.input[start_input.input.len() - input.input.len() - 1].clone();
            let py = input.state.py;
            let ast = input.state.ast.clone();
            let op_obj = ast.call_method0(op_name).unwrap();

            // Ensure target context is Store
            set_context(py, &target, ctx_store(&ast)?)?;

            let node = ast
                .call_method1("AugAssign", (target, op_obj, value))
                .unwrap();
            set_location(&node, &start_tok, &end_tok).unwrap();
            return Ok(node.into());
        }
        // Not AugAssign. Could be Assign. `target = value`
        // or just expression stmt? handled in simple_stmt.
        // If we consumed target, we must match = for Assign.
        if peek(op(b"=")).parse_next(input).is_ok() {
            // It is Assign.
        } else {
            // We consumed a target but it wasn't an assignment.
            // We need to backtrack? simple_stmt calls parse_assignment FIRST.
            // If parse_assignment returns Ok, it's an assignment.
            // If it fails, simple_stmt calls parse_star_expressions.
            // So here if we don't match assignment, we error.
            input.reset(&checkpoint);
            return Err(ErrMode::Backtrack(ContextError::new()));
        }
    }
    input.reset(&checkpoint);

    // Assign: (star_targets '=')+ value
    // We parse one target, then =, then loop?
    // Complex because `a = b = c`.
    // targets = [a, b] value = c.

    // Attempt to parse list of targets followed by =

    let mut targets = Vec::new();
    loop {
        let checkpoint_loop = input.checkpoint();
        if let Ok(t) = parse_star_targets.parse_next(input) {
            if peek(op(b"=")).parse_next(input).is_ok() {
                let _ = op(b"=").parse_next(input)?;
                targets.push(t);
                // Continue loop to see if there are more targets
            } else {
                // Parsed a target but no =, so this must be the VALUE (if we have targets)
                // or it's not an assignment (if no targets).
                if targets.is_empty() {
                    // Not an assignment
                    input.reset(&checkpoint);
                    return Err(ErrMode::Backtrack(ContextError::new()));
                }
                // It's the value. But we consumed it as star_targets.
                // Value can be yield_expr or star_expressions.
                // star_targets is subset of star_expressions?
                // Actually star_targets forces Store context? No, we parse it then set context.
                // So this 't' is the value.
                let value = t;
                let end_tok =
                    start_input.input[start_input.input.len() - input.input.len() - 1].clone();
                let py = input.state.py;
                let ast = input.state.ast.clone();

                // Set context for targets
                let store = ctx_store(&ast)?;
                for tar in &targets {
                    set_context(py, tar, store.clone_ref(py))?;
                }

                let targets_list = PyList::new(py, targets).unwrap();
                let node = ast.call_method1("Assign", (targets_list, value)).unwrap();
                set_location(&node, &start_tok, &end_tok).unwrap();
                return Ok(node.into());
            }
        } else {
            // Failed to parse target. If we have targets, next comes value?
            // But we entered loop expecting target=
            // We should break and parse value?
            // If we failed to parse target, maybe it IS the value (expression).
            input.reset(&checkpoint_loop);
            break;
        }
    }

    if !targets.is_empty() {
        // Parse value
        let value = parse_star_expressions(input)?;
        let end_tok = start_input.input[start_input.input.len() - input.input.len() - 1].clone();
        let py = input.state.py;
        let ast = input.state.ast.clone();
        let store = ctx_store(&ast)?;
        for tar in &targets {
            set_context(py, tar, store.clone_ref(py))?;
        }
        let targets_list = PyList::new(py, targets).unwrap();
        let node = ast.call_method1("Assign", (targets_list, value)).unwrap();
        set_location(&node, &start_tok, &end_tok).unwrap();
        Ok(node.into())
    } else {
        Err(ErrMode::Backtrack(ContextError::new()))
    }
}
