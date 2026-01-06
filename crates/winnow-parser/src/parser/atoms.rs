use super::expr_ops::parse_bitwise_or;
use super::expressions::{
    parse_expression, parse_generators, parse_star_expression, parse_star_expressions,
};
use super::{ctx_load, get_text, kw, make_error, op, parse_token_type, set_location, TokenStream};
use crate::tokenizer::{TokInfo, Token};
use pyo3::prelude::*;
use pyo3::types::PyList;
use winnow::combinator::peek;
use winnow::error::{ContextError, ErrMode};
use winnow::prelude::*;

// Match NAME token
pub fn parse_name<'s>(input: &mut TokenStream<'s>) -> ModalResult<TokInfo> {
    let checkpoint = input.checkpoint();
    let tok = parse_token_type(input, Token::NAME)?;
    let text = get_text(input, &tok);
    if text == b"lambda" {
        input.reset(&checkpoint);
        return Err(ErrMode::Backtrack(ContextError::new()));
    }
    Ok(tok)
}

// Match NUMBER
pub fn parse_number<'s>(input: &mut TokenStream<'s>) -> ModalResult<TokInfo> {
    parse_token_type(input, Token::NUMBER)
}

// Match STRING
pub fn parse_string<'s>(input: &mut TokenStream<'s>) -> ModalResult<TokInfo> {
    parse_token_type(input, Token::STRING)
}

// Match NEWLINE
pub fn parse_newline<'s>(input: &mut TokenStream<'s>) -> ModalResult<TokInfo> {
    parse_token_type(input, Token::NEWLINE)
}

// Match INDENT
pub fn parse_indent<'s>(input: &mut TokenStream<'s>) -> ModalResult<TokInfo> {
    parse_token_type(input, Token::INDENT)
}

// Match DEDENT
pub fn parse_dedent<'s>(input: &mut TokenStream<'s>) -> ModalResult<TokInfo> {
    parse_token_type(input, Token::DEDENT)
}

// Match ENDMARKER
pub fn parse_endmarker<'s>(input: &mut TokenStream<'s>) -> ModalResult<TokInfo> {
    parse_token_type(input, Token::ENDMARKER)
}

// F-String Helpers

fn parse_fstring_middle<'s>(
    input: &mut TokenStream<'s>,
    is_format_spec: bool,
) -> ModalResult<Vec<Py<PyAny>>> {
    let mut parts = Vec::new();
    let _py = input.state.py;
    let ast = input.state.ast.clone();

    loop {
        // If we are in parsing a full fstring, we end at FSTRING_END
        if !is_format_spec {
            if let Ok(_) = parse_token_type(input, Token::FSTRING_END) {
                break;
            }
        } else {
            // inside format spec, we end at '}'
            if peek(op(b"}")).parse_next(input).is_ok() {
                break;
            }
        }

        // FSTRING_MIDDLE -> Constant(str)
        if let Ok(tok) = parse_token_type(input, Token::FSTRING_MIDDLE) {
            let text = get_text(input, &tok);
            let text_str = std::str::from_utf8(text).unwrap();
            let node = ast
                .call_method1("Constant", (text_str,))
                .map_err(|_| make_error("Constant failed".into()))?;
            parts.push(node.into());
            continue;
        }

        // Replacement field { ... }
        if peek(op(b"{")).parse_next(input).is_ok() {
            let node = parse_fstring_replacement_field(input)?;
            parts.push(node);
            continue;
        }

        // If we are here and we didn't match anything:
        return Err(ErrMode::Backtrack(ContextError::new()));
    }
    Ok(parts)
}

fn parse_fstring_replacement_field<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let py = input.state.py;
    let ast = input.state.ast.clone();

    let _ = op(b"{").parse_next(input)?;
    let value = parse_expression(input)?;

    let mut conversion = -1;
    if let Ok(_) = op(b"!").parse_next(input) {
        // expect NAME ('s', 'r', 'a')
        if let Ok(tok) = parse_name(input) {
            let c = get_text(input, &tok);
            if c == b"s" {
                conversion = 115;
            } else if c == b"r" {
                conversion = 114;
            } else if c == b"a" {
                conversion = 97;
            } else {
                return Err(ErrMode::Backtrack(ContextError::new()));
            }
        } else {
            return Err(ErrMode::Backtrack(ContextError::new()));
        }
    }

    let mut format_spec: Py<PyAny> = py.None();
    if let Ok(_) = op(b":").parse_next(input) {
        let spec_parts = parse_fstring_middle(input, true)?;
        let spec_list = PyList::new(py, spec_parts).unwrap();
        let joined = ast.call_method1("JoinedStr", (spec_list,)).unwrap();
        format_spec = joined.into();
    }

    let _ = op(b"}").parse_next(input)?;

    let node = ast
        .call_method1("FormattedValue", (value, conversion, format_spec))
        .map_err(|_| make_error("FormattedValue failed".into()))?;

    Ok(node.into())
}

fn parse_fstring<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let _ = parse_token_type(input, Token::FSTRING_START)?;
    let parts = parse_fstring_middle(input, false)?;

    let py = input.state.py;
    let ast = input.state.ast.clone();
    let parts_list = PyList::new(py, parts).unwrap();
    let node = ast
        .call_method1("JoinedStr", (parts_list,))
        .map_err(|_| make_error("JoinedStr failed".into()))?;
    Ok(node.into())
}

// atom:
//     | NAME
//     | True | False | None
//     | NUMBER | STRING
//     | ...
pub fn parse_atom<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let tokens = input.input;
    let py = input.state.py;
    let ast = input.state.ast.clone();

    if let Ok(tok) = parse_name(input) {
        let text = get_text(input, &tok);
        if text == b"True" {
            let node = ast
                .call_method1("Constant", (true,))
                .map_err(|_| make_error("Constant failed".into()))?;
            set_location(&node, &tok, &tok).map_err(|e| make_error(e.to_string()))?;
            return Ok(node.into());
        } else if text == b"False" {
            let node = ast
                .call_method1("Constant", (false,))
                .map_err(|_| make_error("Constant failed".into()))?;
            set_location(&node, &tok, &tok).map_err(|e| make_error(e.to_string()))?;
            return Ok(node.into());
        } else if text == b"None" {
            let node = ast
                .call_method1("Constant", (py.None(),))
                .map_err(|_| make_error("Constant failed".into()))?;
            set_location(&node, &tok, &tok).map_err(|e| make_error(e.to_string()))?;
            return Ok(node.into());
        } else {
            let load = ctx_load(&ast)?;
            let text_str = std::str::from_utf8(text).unwrap();
            let node = ast
                .call_method1("Name", (text_str, load))
                .map_err(|_| make_error("Name failed".into()))?;
            set_location(&node, &tok, &tok).map_err(|e| make_error(e.to_string()))?;
            return Ok(node.into());
        }
    }

    if let Ok(tok) = parse_number(input) {
        let text = get_text(input, &tok);
        let text_str = std::str::from_utf8(text).unwrap();
        let val = match text_str.parse::<i64>() {
            Ok(i) => i.into_pyobject(py).unwrap().into_any().unbind(),
            Err(_) => text_str.into_pyobject(py).unwrap().into_any().unbind(),
        };
        let node = ast
            .call_method1("Constant", (val,))
            .map_err(|_| make_error("Constant failed".into()))?;
        set_location(&node, &tok, &tok).map_err(|e| make_error(e.to_string()))?;
        return Ok(node.into());
    }

    // String concatenation (including f-strings)
    let mut string_nodes: Vec<Py<PyAny>> = Vec::new();
    let mut has_fstring = false;

    let str_start_tok = input.input[0].clone();

    loop {
        if let Ok(tok) = parse_string(input) {
            let text = get_text(input, &tok);
            let text_str = std::str::from_utf8(text).unwrap();

            // ast.literal_eval should handle quotes.
            // If it fails, it might be due to incomplete string or other issue.
            // We use the Python ast module to evaluate.
            let val = ast.call_method1("literal_eval", (text_str,)).map_err(|e| {
                make_error(format!("literal_eval failed for {}: {}", text_str, e).into())
            })?;

            let node = ast
                .call_method1("Constant", (val,))
                .map_err(|_| make_error("Constant failed".into()))?;
            set_location(&node, &tok, &tok).map_err(|e| make_error(e.to_string()))?;
            string_nodes.push(node.unbind());
            continue;
        }

        if peek(|i: &mut TokenStream<'s>| parse_token_type(i, Token::FSTRING_START))
            .parse_next(input)
            .is_ok()
        {
            let fnode = parse_fstring(input)?;
            string_nodes.push(fnode);
            has_fstring = true;
            continue;
        }

        break;
    }

    if !string_nodes.is_empty() {
        let end_tok = tokens[tokens.len() - input.input.len() - 1].clone();
        if !has_fstring {
            // Merge all constants into one
            let mut full_text = String::new();
            for node in &string_nodes {
                // node is Constant. value is str.
                let val = node
                    .bind(py)
                    .getattr("value")
                    .map_err(|_| make_error("Attribute error".into()))?;
                let s: String = val
                    .extract()
                    .map_err(|_| make_error("Extract error".into()))?;
                full_text.push_str(&s);
            }
            let node = ast
                .call_method1("Constant", (full_text,))
                .map_err(|_| make_error("Constant failed".into()))?;
            set_location(&node, &str_start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
            return Ok(node.into());
        } else {
            // Mixed strings and f-strings -> JoinedStr
            let mut final_parts = Vec::new();
            for node in string_nodes {
                if let Ok(values) = node.bind(py).getattr("values") {
                    let values_list = values
                        .cast::<PyList>()
                        .map_err(|_| make_error("Cast failed".into()))?;
                    for v in values_list {
                        final_parts.push(v.clone().unbind());
                    }
                } else {
                    final_parts.push(node);
                }
            }
            let parts_list = PyList::new(py, final_parts).unwrap();
            let node = ast
                .call_method1("JoinedStr", (parts_list,))
                .map_err(|_| make_error("JoinedStr failed".into()))?;
            set_location(&node, &str_start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
            return Ok(node.into());
        }
    }

    if let Ok(tok) = op(b"...").parse_next(input) {
        let node = ast
            .call_method1("Constant", (py.Ellipsis(),))
            .map_err(|_| make_error("Constant failed".into()))?;
        set_location(&node, &tok, &tok).map_err(|e| make_error(e.to_string()))?;
        return Ok(node.into());
    }

    // Group (...) or Tuple
    if peek(op(b"(")).parse_next(input).is_ok() {
        let start_tok = op(b"(").parse_next(input)?;
        if peek(op(b")")).parse_next(input).is_ok() {
            let end_tok = op(b")").parse_next(input)?;
            let load = ctx_load(&ast)?;
            let node = ast
                .call_method1("Tuple", (PyList::empty(py), load))
                .unwrap();
            set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
            return Ok(node.into());
        }

        let expr = parse_star_expressions(input)?; // Returns Tuple or Expr
        let end_tok = op(b")").parse_next(input)?;
        // If it's a Tuple, update its location to include the parentheses
        if expr.bind(py).get_type().name().unwrap() == "Tuple" {
            set_location(&expr.bind(py), &start_tok, &end_tok)
                .map_err(|e| make_error(e.to_string()))?;
        }
        return Ok(expr);
    }

    // List [...]
    if let Ok(start_tok) = op(b"[").parse_next(input) {
        if peek(op(b"]")).parse_next(input).is_ok() {
            let end_tok = op(b"]").parse_next(input)?;
            let load = ctx_load(&ast)?;
            let empty = PyList::empty(py);
            let node = ast.call_method1("List", (empty, load)).unwrap();
            set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
            return Ok(node.into());
        }

        let first = parse_star_expression(input)?;

        if peek(kw(b"for")).parse_next(input).is_ok()
            || peek(|i: &mut TokenStream<'s>| parse_token_type(i, Token::ASYNC))
                .parse_next(input)
                .is_ok()
        {
            let generators = parse_generators(input)?;
            let end_tok = op(b"]").parse_next(input)?;
            let gens_list = PyList::new(py, generators).unwrap();
            let node = ast
                .call_method1("ListComp", (first, gens_list))
                .map_err(|_| make_error("ListComp failed".into()))?;
            set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
            return Ok(node.into());
        }

        let mut elts = vec![first];
        if peek(op(b",")).parse_next(input).is_ok() {
            let _ = op(b",").parse_next(input)?;
            loop {
                if peek(op(b"]")).parse_next(input).is_ok() {
                    break;
                }

                let expr = parse_star_expression(input)?;
                elts.push(expr);

                if peek(op(b",")).parse_next(input).is_ok() {
                    let _ = op(b",").parse_next(input)?;
                } else {
                    break;
                }
            }
        }

        let end_tok = op(b"]").parse_next(input)?;
        let load = ctx_load(&ast)?;
        let elts_list = PyList::new(py, elts).unwrap();
        let node = ast.call_method1("List", (elts_list, load)).unwrap();
        set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
        return Ok(node.into());
    }

    // Dict/Set {...}
    if peek(op(b"{")).parse_next(input).is_ok() {
        // Check for empty
        let checkpoint = input.checkpoint();
        let _ = op(b"{").parse_next(input)?;
        if peek(op(b"}")).parse_next(input).is_ok() {
            let _ = op(b"}").parse_next(input)?;
            return Ok(ast
                .call_method1("Dict", (PyList::empty(py), PyList::empty(py)))
                .unwrap()
                .into());
        }
        input.reset(&checkpoint);

        // Helper to distinguish
        return parse_dict_or_set_atom(input);
    }

    Err(ErrMode::Backtrack(ContextError::new()))
}

fn parse_dict_or_set_atom<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let checkpoint = input.checkpoint();
    let _ = op(b"{").parse_next(input)?;

    // Lookahead
    if peek(op(b"**")).parse_next(input).is_ok() {
        input.reset(&checkpoint);
        return parse_dict_maker(input);
    }

    if let Ok(_) = parse_expression(input) {
        if peek(op(b":")).parse_next(input).is_ok() {
            input.reset(&checkpoint);
            return parse_dict_maker(input);
        } else {
            input.reset(&checkpoint);
            return parse_set_maker(input);
        }
    }

    input.reset(&checkpoint);
    Err(ErrMode::Backtrack(ContextError::new()))
}

fn parse_dict_maker<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let start_tok = op(b"{").parse_next(input)?;

    // Check for DictComp
    // dict_comprehension: key ':' value comp_for
    // But also normal dict starts with key ':' value ...
    // Or **kwargs.

    // If **kwargs, it must be dict, not comp.
    if peek(op(b"**")).parse_next(input).is_ok() {
        // Normal dict loop (start with **)
        let mut keys = Vec::new();
        let mut values = Vec::new();

        loop {
            if peek(op(b"}")).parse_next(input).is_ok() {
                break;
            }

            if peek(op(b"**")).parse_next(input).is_ok() {
                let _ = op(b"**").parse_next(input)?;
                let expr = parse_bitwise_or(input)?;
                let py = input.state.py;
                keys.push(py.None().into());
                values.push(expr);
            } else {
                let key = parse_expression(input)?;
                let _ = op(b":").parse_next(input)?;
                let value = parse_expression(input)?;
                keys.push(key);
                values.push(value);
            }

            if peek(op(b",")).parse_next(input).is_ok() {
                let _ = op(b",").parse_next(input)?;
            } else {
                break;
            }
        }
        let end_tok = op(b"}").parse_next(input)?;
        let py = input.state.py;
        let ast = input.state.ast.clone();
        let keys_list = PyList::new(py, keys).unwrap();
        let values_list = PyList::new(py, values).unwrap();
        let node = ast.call_method1("Dict", (keys_list, values_list)).unwrap();
        set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
        return Ok(node.into());
    }

    // Parse first key/value
    let key = parse_expression(input)?;
    let _ = op(b":").parse_next(input)?;
    let value = parse_expression(input)?;

    // Check for comprehension
    if peek(kw(b"for")).parse_next(input).is_ok() || peek(kw(b"async")).parse_next(input).is_ok() {
        let generators = parse_generators(input)?;
        let end_tok = op(b"}").parse_next(input)?;

        let py = input.state.py;
        let ast = input.state.ast.clone();
        let gens_list = PyList::new(py, generators).unwrap();
        let node = ast
            .call_method1("DictComp", (key, value, gens_list))
            .map_err(|_| make_error("DictComp failed".into()))?;
        set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
        return Ok(node.into());
    }

    // Normal dict
    let mut keys = vec![key];
    let mut values = vec![value];

    if peek(op(b",")).parse_next(input).is_ok() {
        let _ = op(b",").parse_next(input)?;

        loop {
            if peek(op(b"}")).parse_next(input).is_ok() {
                break;
            }

            if peek(op(b"**")).parse_next(input).is_ok() {
                let _ = op(b"**").parse_next(input)?;
                let expr = parse_bitwise_or(input)?;
                let py = input.state.py;
                keys.push(py.None().into());
                values.push(expr);
            } else {
                let k = parse_expression(input)?;
                let _ = op(b":").parse_next(input)?;
                let v = parse_expression(input)?;
                keys.push(k);
                values.push(v);
            }

            if peek(op(b",")).parse_next(input).is_ok() {
                let _ = op(b",").parse_next(input)?;
            } else {
                break;
            }
        }
    }

    let end_tok = op(b"}").parse_next(input)?;
    let py = input.state.py;
    let ast = input.state.ast.clone();
    let keys_list = PyList::new(py, keys).unwrap();
    let values_list = PyList::new(py, values).unwrap();
    let node = ast.call_method1("Dict", (keys_list, values_list)).unwrap();
    set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
    Ok(node.into())
}

fn parse_set_maker<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let start_tok = op(b"{").parse_next(input)?;

    // Parse first element
    let first = parse_star_expression(input)?;

    // Check for comprehension
    if peek(kw(b"for")).parse_next(input).is_ok()
        || peek(|i: &mut TokenStream<'s>| parse_token_type(i, Token::ASYNC))
            .parse_next(input)
            .is_ok()
    {
        let generators = parse_generators(input)?;
        let end_tok = op(b"}").parse_next(input)?;

        let py = input.state.py;
        let ast = input.state.ast.clone();
        let gens_list = PyList::new(py, generators).unwrap();
        let node = ast
            .call_method1("SetComp", (first, gens_list))
            .map_err(|_| make_error("SetComp failed".into()))?;
        set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
        return Ok(node.into());
    }

    let mut elts = vec![first];

    if peek(op(b",")).parse_next(input).is_ok() {
        let _ = op(b",").parse_next(input)?;

        loop {
            if peek(op(b"}")).parse_next(input).is_ok() {
                break;
            }

            let expr = parse_star_expression(input)?;
            elts.push(expr);

            if peek(op(b",")).parse_next(input).is_ok() {
                let _ = op(b",").parse_next(input)?;
            } else {
                break;
            }
        }
    }

    let end_tok = op(b"}").parse_next(input)?;

    let py = input.state.py;
    let ast = input.state.ast.clone();
    let elts_list = PyList::new(py, elts).unwrap();
    let node = ast.call_method1("Set", (elts_list,)).unwrap();
    set_location(&node, &start_tok, &end_tok).map_err(|e| make_error(e.to_string()))?;
    Ok(node.into())
}
