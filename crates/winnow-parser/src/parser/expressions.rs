use super::atoms::{parse_atom, parse_name, parse_newline};
use super::expr_ops::*;
use super::lambdas::parse_lambdef;
use super::{
    ctx_load, ctx_store, get_text, kw, make_error, op, parse_token_type, set_context, set_location,
    TokenStream,
};
use xtokens::{Token};
use pyo3::prelude::*;
use pyo3::types::PyList;
use winnow::combinator::{opt, peek};
use winnow::error::{ContextError, ErrMode};
use winnow::prelude::*;

// named_expression[ast.expr]:
//     | assignment_expression
//     | expression !':='
pub fn parse_named_expression<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    // TODO: Assignment expression (walrus)
    parse_expression(input)
}

// expression[ast.expr](memo):
//     | a=disjunction 'if' b=disjunction 'else' c=expression { ast.IfExp(...) }
//     | disjunction
//     | lambdef
pub fn parse_expression<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    if peek(kw(b"yield")).parse_next(input).is_ok() {
        return parse_yield_expr(input);
    }
    if peek(kw(b"lambda")).parse_next(input).is_ok() {
        return parse_lambdef(input);
    }

    let checkpoint = input.checkpoint();
    if let Ok(disj) = parse_disjunction(input) {
        // Check for 'if'
        if peek(kw(b"if")).parse_next(input).is_ok() {
            let _ = kw(b"if").parse_next(input)?;
            let test = parse_disjunction(input)?;
            let _ = kw(b"else").parse_next(input)?;
            let orelse = parse_expression(input)?;

            let _py = input.state.py;
            let ast = input.state.ast.clone();
            let node = ast
                .call_method1("IfExp", (test, disj, orelse))
                .map_err(|_| make_error("IfExp failed".into()))?;
            return Ok(node.into());
        }
        return Ok(disj);
    }
    input.reset(&checkpoint);

    Err(ErrMode::Backtrack(ContextError::new()))
}

fn parse_yield_expr<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let tokens = input.input;
    if tokens.is_empty() {
        return Err(ErrMode::Backtrack(ContextError::new()));
    }
    let start_tok = tokens[0].clone();
    let _ = kw(b"yield").parse_next(input)?;

    let py = input.state.py;
    let ast = input.state.ast.clone();

    if peek(kw(b"from")).parse_next(input).is_ok() {
        let _ = kw(b"from").parse_next(input)?;
        let value = parse_expression(input)?;
        let end_tok = tokens[tokens.len() - input.input.len() - 1].clone();
        let node = ast
            .call_method1("YieldFrom", (value,))
            .map_err(|_| make_error("YieldFrom failed".into()))?;
        set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
        Ok(node.into())
    } else {
        let value = if let Ok(v) = opt(parse_star_expressions).parse_next(input) {
            match v {
                Some(v) => v,
                None => py.None().into(),
            }
        } else {
            py.None().into()
        };
        let end_tok = tokens[tokens.len() - input.input.len() - 1].clone();
        let node = ast
            .call_method1("Yield", (value,))
            .map_err(|_| make_error("Yield failed".into()))?;
        set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
        Ok(node.into())
    }
}

// await_primary (memo):
//     | 'await' a=primary { ast.Await(a, LOCATIONS) }
//     | primary
pub fn parse_await_primary<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let tokens = input.input;
    if let Ok(_) = parse_token_type(input, Token::AWAIT) {
        let start_tok = tokens[0].clone();
        let a = parse_primary(input)?;
        let tokens_after = input.input;
        let end_tok = tokens[tokens.len() - tokens_after.len() - 1].clone();

        let _py = input.state.py;
        let ast = input.state.ast.clone();
        let node = ast
            .call_method1("Await", (a,))
            .map_err(|_| make_error("Await failed".into()))?;
        set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
        return Ok(node.into());
    }
    parse_primary(input)
}

// slice:
//     | [expression] ':' [expression] [':' [expression] ]
//     | expression
fn parse_slice<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let tokens = input.input;
    let start_tok = tokens[0].clone();
    let checkpoint = input.checkpoint();

    // Check for starting ':' -> Slice with no lower
    if peek(op(b":")).parse_next(input).is_ok() {
        let _ = op(b":").parse_next(input)?;
        let upper = if !peek(op(b":")).parse_next(input).is_ok()
            && !peek(op(b",")).parse_next(input).is_ok()
            && !peek(op(b"]")).parse_next(input).is_ok()
        {
            parse_expression(input).ok()
        } else {
            None
        };

        // Step?
        let step = if peek(op(b":")).parse_next(input).is_ok() {
            let _ = op(b":").parse_next(input)?;
            if !peek(op(b",")).parse_next(input).is_ok()
                && !peek(op(b"]")).parse_next(input).is_ok()
            {
                parse_expression(input).ok()
            } else {
                Some(input.state.py.None().into())
            }
        } else {
            None
        };

        let end_tok = tokens[tokens.len() - input.input.len() - 1].clone();
        let py = input.state.py;
        let ast = input.state.ast.clone();
        let lower = py.None();
        let upper_obj = match upper {
            Some(u) => u,
            None => py.None().into(),
        };
        let step_obj = match step {
            Some(s) => s,
            None => py.None().into(),
        };

        let node = ast
            .call_method1("Slice", (lower, upper_obj, step_obj))
            .map_err(|_| make_error("Slice failed".into()))?;
        set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
        return Ok(node.into());
    }

    // Try parse expression
    if let Ok(lower) = parse_expression(input) {
        // If followed by ':', it's a Slice
        if peek(op(b":")).parse_next(input).is_ok() {
            let _ = op(b":").parse_next(input)?;
            let upper = if !peek(op(b":")).parse_next(input).is_ok()
                && !peek(op(b",")).parse_next(input).is_ok()
                && !peek(op(b"]")).parse_next(input).is_ok()
            {
                parse_expression(input).ok()
            } else {
                None
            };

            let step = if peek(op(b":")).parse_next(input).is_ok() {
                let _ = op(b":").parse_next(input)?;
                if !peek(op(b",")).parse_next(input).is_ok()
                    && !peek(op(b"]")).parse_next(input).is_ok()
                {
                    parse_expression(input).ok()
                } else {
                    Some(input.state.py.None().into())
                }
            } else {
                None
            };

            let end_tok = tokens[tokens.len() - input.input.len() - 1].clone();
            let py = input.state.py;
            let ast = input.state.ast.clone();
            let upper_obj = match upper {
                Some(u) => u,
                None => py.None().into(),
            };
            let step_obj = match step {
                Some(s) => s,
                None => py.None().into(),
            };

            let node = ast
                .call_method1("Slice", (lower, upper_obj, step_obj))
                .map_err(|_| make_error("Slice failed".into()))?;
            set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
            return Ok(node.into());
        } else {
            // Just expression
            return Ok(lower);
        }
    }

    input.reset(&checkpoint);
    Err(ErrMode::Backtrack(ContextError::new()))
}

pub fn parse_slices<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let tokens = input.input;
    let start_tok = tokens[0].clone();
    let first = parse_slice(input)?;

    if peek(op(b",")).parse_next(input).is_ok() {
        let _ = op(b",").parse_next(input)?;
        let mut elts = vec![first];

        loop {
            if peek(op(b"]")).parse_next(input).is_ok() {
                break;
            }

            if let Ok(next_slice) = parse_slice(input) {
                elts.push(next_slice);
                if peek(op(b",")).parse_next(input).is_ok() {
                    let _ = op(b",").parse_next(input)?;
                } else {
                    break;
                }
            } else {
                break;
            }
        }

        let end_tok = tokens[tokens.len() - input.input.len() - 1].clone();
        let py = input.state.py;
        let ast = input.state.ast.clone();
        let elts_list = PyList::new(py, elts).unwrap();
        let load = ctx_load(&ast)?;
        let node = ast
            .call_method1("Tuple", (elts_list, load))
            .map_err(|_| make_error("Tuple failed".into()))?;
        set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
        Ok(node.into())
    } else {
        Ok(first)
    }
}

// primary:
//     | atom
//     | primary '.' NAME
//     | primary '(' [arguments] ')'
//     | primary '[' slices ']'
// Left recursive -> Iterative
fn parse_primary<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let tokens = input.input;
    let start_tok = tokens[0].clone();
    let mut left = parse_atom(input)?;

    let py = input.state.py;
    let ast = input.state.ast.clone();
    let load = ctx_load(&ast)?;

    loop {
        // Attribute: . NAME
        if let Ok(_) = op(b".").parse_next(input) {
            let name_tok = parse_name(input)?;
            let text = get_text(input, &name_tok);
            let text_str = std::str::from_utf8(text).unwrap();
            let end_tok = tokens[tokens.len() - input.input.len() - 1].clone();
            let node = ast
                .call_method1(
                    "Attribute",
                    (left, text_str, load.bind(py).clone().unbind()),
                )
                .map_err(|_| make_error("Attribute failed".into()))?;
            set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
            left = node.into();
            continue;
        }

        // Call: ( ... )
        if let Ok(_) = op(b"(").parse_next(input) {
            let (args, keywords) = parse_arguments(input)?;
            let _ = op(b")").parse_next(input)?;
            let end_tok = tokens[tokens.len() - input.input.len() - 1].clone();

            let node = ast
                .call_method1("Call", (left, args, keywords))
                .map_err(|_| make_error("Call failed".into()))?;
            set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
            left = node.into();
            continue;
        }

        // Subscript: [ ... ]
        if let Ok(_) = op(b"[").parse_next(input) {
            let slice = parse_slices(input)?;
            let _ = op(b"]").parse_next(input)?;
            let end_tok = tokens[tokens.len() - input.input.len() - 1].clone();

            let node = ast
                .call_method1("Subscript", (left, slice, load.bind(py).clone().unbind()))
                .map_err(|_| make_error("Subscript failed".into()))?;
            set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
            left = node.into();
            continue;
        }

        break;
    }

    Ok(left)
}

// generators: comprehension+
pub fn parse_generators<'s>(input: &mut TokenStream<'s>) -> ModalResult<Vec<Py<PyAny>>> {
    let mut generators = Vec::new();

    loop {
        let tokens = input.input;
        if tokens.is_empty() {
            break;
        }
        let start_tok = tokens[0].clone();

        let is_async = if peek(|i: &mut TokenStream<'s>| parse_token_type(i, Token::ASYNC))
            .parse_next(input)
            .is_ok()
        {
            let _ = parse_token_type(input, Token::ASYNC)?;
            1 // int for Async
        } else {
            0
        };

        if peek(kw(b"for")).parse_next(input).is_ok() {
            let _ = kw(b"for").parse_next(input)?;
            let target = parse_star_targets(input)?;
            let _ = kw(b"in").parse_next(input)?;
            let iter = parse_disjunction(input)?; // or_test

            let mut ifs = Vec::new();
            while peek(kw(b"if")).parse_next(input).is_ok() {
                let _ = kw(b"if").parse_next(input)?;
                let cond = parse_disjunction(input)?;
                ifs.push(cond);
            }

            let end_tok = tokens[tokens.len() - input.input.len() - 1].clone();
            let py = input.state.py;
            let ast = input.state.ast.clone();

            let store = ctx_store(&ast)?;
            set_context(py, &target, store)?;

            let ifs_list = PyList::new(py, ifs).unwrap();

            let node = ast
                .call_method1("comprehension", (target, iter, ifs_list, is_async))
                .map_err(|_| make_error("comprehension failed".into()))?;
            set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
            generators.push(node.into());

            // Check if next is 'async for' or 'for' to continue loop
            // If not, break
            let has_async = peek(|i: &mut TokenStream<'s>| parse_token_type(i, Token::ASYNC))
                .parse_next(input)
                .is_ok();
            let has_for = peek(kw(b"for")).parse_next(input).is_ok();

            if !has_async && !has_for {
                break;
            }
        } else {
            break;
        }
    }

    Ok(generators)
}

// Arguments (Call/Class bases)
// Returns (args_list, keywords_list)
pub fn parse_arguments<'s>(input: &mut TokenStream<'s>) -> ModalResult<(Py<PyAny>, Py<PyAny>)> {
    let mut args = Vec::new();
    let mut keywords = Vec::new();

    if peek(op(b")")).parse_next(input).is_ok() {
        let py = input.state.py;
        return Ok((PyList::empty(py).into(), PyList::empty(py).into()));
    }

    loop {
        let checkpoint = input.checkpoint();
        let py = input.state.py;
        let ast = input.state.ast.clone();

        let mut matched = false;

        // Check for **kwargs
        if let Ok(_) = op(b"**").parse_next(input) {
            let expr = parse_expression(input)?;
            let kw = ast
                .call_method1("keyword", (py.None(), expr))
                .map_err(|_| make_error("keyword failed".into()))?;
            keywords.push(kw);
            matched = true;
        } else {
            // Check for keyword arg: NAME '=' strict
            // We need to match NAME then '='
            if let Ok(name_tok) = parse_name.parse_next(input) {
                if let Ok(_) = op(b"=").parse_next(input) {
                    // It IS a keyword arg
                    let val = parse_expression(input)?;
                    let name_bytes = get_text(input, &name_tok);
                    let name = std::str::from_utf8(name_bytes).unwrap();
                    let kw = ast
                        .call_method1("keyword", (name, val))
                        .map_err(|_| make_error("keyword failed".into()))?;
                    keywords.push(kw);
                    matched = true;
                } else {
                    // Not a keyword arg, backtrack and parse as expression
                    input.reset(&checkpoint);
                }
            } else {
                input.reset(&checkpoint);
            }
        }

        if !matched {
            if let Ok(_) = op(b"*").parse_next(input) {
                let expr = parse_expression(input)?;
                let load = ctx_load(&ast)?;
                let starred = ast
                    .call_method1("Starred", (expr, load))
                    .map_err(|_| make_error("Starred failed".into()))?;
                args.push(starred.into());
            } else {
                let expr = parse_expression(input)?;
                args.push(expr);
            }
        }

        if peek(op(b",")).parse_next(input).is_ok() {
            let _ = op(b",").parse_next(input)?;
            if peek(op(b")")).parse_next(input).is_ok() {
                break;
            }
        } else {
            break;
        }
    }

    let py = input.state.py;
    let args_list = PyList::new(py, args).unwrap();
    let kw_list = PyList::new(py, keywords).unwrap();
    Ok((args_list.into(), kw_list.into()))
}

// star_expression: '*' bitwise_or | expression
pub fn parse_star_expression<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let start_input = input.clone();
    if peek(op(b"*")).parse_next(input).is_ok() {
        let start_tok = op(b"*").parse_next(input)?;
        let expr = parse_bitwise_or(input)?;
        let consumed = start_input.input.len() - input.input.len();
        let end_tok = start_input.input[consumed - 1].clone();
        let _py = input.state.py;
        let ast = input.state.ast.clone();
        let load = ctx_load(&ast)?;
        let node = ast
            .call_method1("Starred", (expr, load))
            .map_err(|_| make_error("Starred failed".into()))?;
        set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
        Ok(node.into())
    } else {
        parse_expression(input)
    }
}

pub fn parse_star_expressions<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let tokens = input.input;
    let start_tok = tokens[0].clone();
    // start with one
    let first = parse_star_expression(input)?;

    if peek(op(b",")).parse_next(input).is_ok() {
        let _ = op(b",").parse_next(input)?;

        let mut elts = vec![first];

        loop {
            // Check if we strictly have another expression
            // If next token is something that can start an expression...
            // Or simpler: if next token CANNOT start expression, break.
            // What can't? ')', ']', '}', ':', 'in', 'else', 'newline'...

            // If we see ',', we consumed it. Now we expect expression OR end.
            // If end, break (trailing comma).
            if peek(op(b")")).parse_next(input).is_ok()
                || peek(op(b"]")).parse_next(input).is_ok()
                || peek(op(b"}")).parse_next(input).is_ok()
                || peek(op(b":")).parse_next(input).is_ok()
                || peek(parse_newline).parse_next(input).is_ok()
            {
                break;
            }
            // Also 'in' for for loops? `for x, y in ...`
            if peek(kw(b"in")).parse_next(input).is_ok() {
                break;
            }

            // Try to parse next expression
            let checkpoint = input.checkpoint();
            if let Ok(next_expr) = parse_star_expression.parse_next(input) {
                elts.push(next_expr);

                // Expect comma for next?
                if peek(op(b",")).parse_next(input).is_ok() {
                    let _ = op(b",").parse_next(input)?;
                    continue;
                } else {
                    break; // no comma, end of list
                }
            } else {
                input.reset(&checkpoint);
                break;
            }
        }

        // Make Tuple
        let end_tok = tokens[tokens.len() - input.input.len() - 1].clone();
        let py = input.state.py;
        let ast = input.state.ast.clone();
        let elts_list = PyList::new(py, elts).unwrap();
        let load = ctx_load(&ast)?;
        let node = ast.call_method1("Tuple", (elts_list, load)).unwrap();
        set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
        Ok(node.into())
    } else {
        Ok(first)
    }
}

pub fn parse_star_targets<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let start_input = input.clone();
    let start_tok = start_input.input[0].clone();
    let first = parse_star_target(input)?;

    if !peek(op(b",")).parse_next(input).is_ok() {
        return Ok(first);
    }

    let mut elts = vec![first];
    let _ = op(b",").parse_next(input)?;

    loop {
        if peek(op(b")")).parse_next(input).is_ok()
            || peek(op(b"]")).parse_next(input).is_ok()
            || peek(op(b"}")).parse_next(input).is_ok()
            || peek(op(b":")).parse_next(input).is_ok()
            || peek(kw(b"in")).parse_next(input).is_ok()
        {
            break;
        }

        let checkpoint = input.checkpoint();
        if let Ok(next) = parse_star_target(input) {
            elts.push(next);
            if peek(op(b",")).parse_next(input).is_ok() {
                let _ = op(b",").parse_next(input)?;
            } else {
                break;
            }
        } else {
            input.reset(&checkpoint);
            break;
        }
    }

    let consumed = start_input.input.len() - input.input.len();
    let end_tok = start_input.input[consumed - 1].clone();

    let py = input.state.py;
    let ast = input.state.ast.clone();
    let elts_list = PyList::new(py, elts).unwrap();
    // Use Load context for targets here, similar to parse_t_primary.
    // The set_context function will handle switching to Store/Del when needed during assignment parsing.
    let ctx = ctx_load(&ast)?;

    let node = ast
        .call_method1("Tuple", (elts_list, ctx))
        .map_err(|_| make_error("Tuple failed".into()))?;
    set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
    Ok(node.into())
}

pub fn parse_star_target<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let tokens = input.input;
    if peek(op(b"*")).parse_next(input).is_ok() {
        let start_tok = op(b"*").parse_next(input)?;
        let expr = parse_star_target(input)?;
        let end_tok = tokens[tokens.len() - input.input.len() - 1].clone();
        let _py = input.state.py;
        let ast = input.state.ast.clone();
        let ctx = ctx_store(&ast)?;
        let node = ast.call_method1("Starred", (expr, ctx)).unwrap();
        set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
        return Ok(node.into());
    }
    parse_t_primary(input)
}

fn parse_t_primary<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let tokens = input.input;
    let start_tok = tokens[0].clone();
    let mut left = parse_atom(input)?;
    let py = input.state.py;
    let ast = input.state.ast.clone();
    let load = ctx_load(&ast)?;

    loop {
        if peek(op(b".")).parse_next(input).is_ok() {
            let _ = op(b".").parse_next(input)?;
            let name_tok = parse_name(input)?;
            let text = get_text(input, &name_tok);
            let text_str = std::str::from_utf8(text).unwrap();
            let end_tok = tokens[tokens.len() - input.input.len() - 1].clone();
            let node = ast
                .call_method1(
                    "Attribute",
                    (left, text_str, load.bind(py).clone().unbind()),
                )
                .map_err(|_| make_error("Attribute failed".into()))?;
            set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
            left = node.into();
            continue;
        }
        if peek(op(b"[")).parse_next(input).is_ok() {
            let _ = op(b"[").parse_next(input)?;
            let slice = parse_slices(input)?;
            let _ = op(b"]").parse_next(input)?;
            let end_tok = tokens[tokens.len() - input.input.len() - 1].clone();
            let node = ast
                .call_method1("Subscript", (left, slice, load.bind(py).clone().unbind()))
                .map_err(|_| make_error("Subscript failed".into()))?;
            set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
            left = node.into();
            continue;
        }
        break;
    }
    Ok(left)
}
