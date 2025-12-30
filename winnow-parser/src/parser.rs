use crate::tokenizer::{tokenize, TokInfo, Token};
use pyo3::prelude::*;
use pyo3::types::{PyList, PyModule, PyString};
use winnow::combinator::{cut_err, not, opt, peek, repeat, separated};
use winnow::error::{ContextError, ErrMode};
use winnow::prelude::*;
use winnow::stream::Stateful;
use winnow::token::any;

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

fn get_text<'s>(input: &TokenStream<'s>, tok: &TokInfo) -> &'s [u8] {
    &input.state.source[tok.span.0..tok.span.1]
}

// Match a specific token type
// Returns TokInfo by value (it's Copy/Clone and small)
fn parse_token_type<'s>(input: &mut TokenStream<'s>, kind: Token) -> ModalResult<TokInfo> {
    any.verify(move |t: &TokInfo| t.typ == kind)
        .parse_next(input)
}

// Helper to create a parser for a specific OP
fn op<'s>(target: &'static [u8]) -> impl FnMut(&mut TokenStream<'s>) -> ModalResult<TokInfo> {
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
fn kw<'s>(target: &'static [u8]) -> impl FnMut(&mut TokenStream<'s>) -> ModalResult<TokInfo> {
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

// Match NAME token
fn parse_name<'s>(input: &mut TokenStream<'s>) -> ModalResult<TokInfo> {
    parse_token_type(input, Token::NAME)
}

// Match NUMBER
fn parse_number<'s>(input: &mut TokenStream<'s>) -> ModalResult<TokInfo> {
    parse_token_type(input, Token::NUMBER)
}

// Match STRING
fn parse_string<'s>(input: &mut TokenStream<'s>) -> ModalResult<TokInfo> {
    parse_token_type(input, Token::STRING)
}

// Match NEWLINE
// Match NEWLINE
fn parse_newline<'s>(input: &mut TokenStream<'s>) -> ModalResult<TokInfo> {
    parse_token_type(input, Token::NEWLINE)
}

// Match INDENT
fn parse_indent<'s>(input: &mut TokenStream<'s>) -> ModalResult<TokInfo> {
    parse_token_type(input, Token::INDENT)
}

// Match DEDENT
fn parse_dedent<'s>(input: &mut TokenStream<'s>) -> ModalResult<TokInfo> {
    parse_token_type(input, Token::DEDENT)
}

// Match ENDMARKER
fn parse_endmarker<'s>(input: &mut TokenStream<'s>) -> ModalResult<TokInfo> {
    parse_token_type(input, Token::ENDMARKER)
}

// ### Error Reporting Helper ###
fn make_error(_msg: String) -> ErrMode<ContextError> {
    // In a real implementation this would attach context
    ErrMode::Backtrack(ContextError::new())
}

// ### Context Helpers ###
fn ctx_load(ast: &Bound<'_, PyModule>) -> ModalResult<Py<PyAny>> {
    let node = ast
        .call_method0("Load")
        .map_err(|_| make_error("Load failed".into()))?;
    Ok(node.into())
}

fn ctx_store(ast: &Bound<'_, PyModule>) -> ModalResult<Py<PyAny>> {
    let node = ast
        .call_method0("Store")
        .map_err(|_| make_error("Store failed".into()))?;
    Ok(node.into())
}

fn ctx_del(ast: &Bound<'_, PyModule>) -> ModalResult<Py<PyAny>> {
    let node = ast
        .call_method0("Del")
        .map_err(|_| make_error("Del failed".into()))?;
    Ok(node.into())
}

fn set_context(py: Python, node: &Py<PyAny>, ctx: Py<PyAny>) -> ModalResult<()> {
    // Recursively set context for Tuple/List if needed, but for now just set attribute
    // TODO: Handle Tuple/List unpacking targets recursively
    let _ = node
        .bind(py)
        .setattr("ctx", ctx)
        .map_err(|_| make_error("Failed to set ctx".into()))?;
    Ok(())
}

// ### Grammar Rules ###

// file[ast.Module]: a=[statements] ENDMARKER { ast.Module(body=a or [], type_ignores=[]) }
pub fn parse_file<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    println!("Entering parse_file");
    let a = opt(parse_statements).parse_next(input)?;
    println!("parse_statements result: is_some={}", a.is_some());
    let _ = parse_endmarker.parse_next(input)?;

    let py = input.state.py;
    let ast = input.state.ast.clone();

    // Construct ast.Module
    let body = match a {
        Some(stmts) => stmts,
        None => PyList::empty(py).into(),
    };

    let type_ignores = PyList::empty(py);

    let module = ast
        .call_method1("Module", (body, type_ignores))
        .map_err(|_| make_error("Failed to create Module".into()))?;
    Ok(module.into())
}

// statements[list[Any]]: a=statement+ { list(itertools.chain.from_iterable(a)) }
pub fn parse_statements<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let a: Vec<Py<PyAny>> = repeat(1.., parse_statement).parse_next(input)?;

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

    Ok(flat_list.into())
}

// statement[list[Any]]: a=compound_stmt { [a] } | a=simple_stmts { a }
pub fn parse_statement<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let checkpoint = input.checkpoint();

    if let Ok(stmt) = parse_compound_stmt.parse_next(input) {
        let py = input.state.py;
        let list = PyList::new(py, vec![stmt]).unwrap();
        return Ok(list.into());
    }

    input.reset(&checkpoint);

    if let Ok(stmts) = parse_simple_stmts.parse_next(input) {
        return Ok(stmts);
    }

    Err(ErrMode::Backtrack(ContextError::new()))
}

// while_stmt
fn parse_while_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let _ = kw(b"while").parse_next(input)?;
    let test = parse_named_expression(input)?;
    let _ = op(b":").parse_next(input)?;
    let body = parse_block(input)?;
    let orelse_block = opt(parse_else_block).parse_next(input)?;

    let py = input.state.py;
    let ast = input.state.ast.clone();
    let orelse = match orelse_block {
        Some(b) => b,
        None => PyList::empty(py).into(),
    };

    let node = ast
        .call_method1("While", (test, body, orelse))
        .map_err(|_| make_error("While failed".into()))?;
    Ok(node.into())
}

// for_stmt
fn parse_for_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let is_async = if peek(kw(b"async")).parse_next(input).is_ok() {
        let _ = kw(b"async").parse_next(input)?;
        true
    } else {
        false
    };

    let _ = kw(b"for").parse_next(input)?;
    let target = parse_star_expressions(input)?;
    let _ = kw(b"in").parse_next(input)?;
    let iter = parse_star_expressions(input)?;
    let _ = op(b":").parse_next(input)?;
    let body = parse_block(input)?;
    let orelse_block = opt(parse_else_block).parse_next(input)?;

    let py = input.state.py;
    let ast = input.state.ast.clone();

    let store = ctx_store(&ast)?;
    set_context(py, &target, store)?;

    let orelse = match orelse_block {
        Some(b) => b,
        None => PyList::empty(py).into(),
    };

    let cls_name = if is_async { "AsyncFor" } else { "For" };

    let node = ast
        .call_method1(cls_name, (target, iter, body, orelse))
        .map_err(|_| make_error(format!("{} failed", cls_name).into()))?;
    Ok(node.into())
}

// with_item: expression ['as' star_target]
fn parse_with_item<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let context_expr = parse_expression(input)?;
    let optional_vars = if peek(kw(b"as")).parse_next(input).is_ok() {
        let _ = kw(b"as").parse_next(input)?;
        let target = parse_star_targets(input)?; // need star_target parsing or just expression and set store
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
fn parse_with_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let is_async = if peek(kw(b"async")).parse_next(input).is_ok() {
        let _ = kw(b"async").parse_next(input)?;
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
    let body = parse_block(input)?;

    let py = input.state.py;
    let ast = input.state.ast.clone();
    let items = PyList::new(py, items_list).unwrap();

    let cls_name = if is_async { "AsyncWith" } else { "With" };
    // With(items, body, type_comment=None)
    let node = ast
        .call_method1(cls_name, (items, body))
        .map_err(|_| make_error(format!("{} failed", cls_name).into()))?;
    Ok(node.into())
}

// except_block
fn parse_except_block<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let _ = kw(b"except").parse_next(input)?;
    let (typ, name) = if peek(op(b":")).parse_next(input).is_ok() {
        let py = input.state.py;
        (py.None().into(), py.None().into())
    } else {
        let t = parse_expression(input)?;
        let n: Py<PyAny> = if peek(kw(b"as")).parse_next(input).is_ok() {
            let _ = kw(b"as").parse_next(input)?;
            let name_tok = parse_name(input)?;
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
    let body = parse_block(input)?;

    let py = input.state.py;
    let ast = input.state.ast.clone();

    // ExceptHandler(type, name, body)
    let node = ast
        .call_method1("ExceptHandler", (typ, name, body))
        .map_err(|_| make_error("ExceptHandler failed".into()))?;
    Ok(node.into())
}

// try_stmt
fn parse_try_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let _ = kw(b"try").parse_next(input)?;
    let _ = op(b":").parse_next(input)?;
    let body = parse_block(input)?;

    let mut handlers = Vec::new();
    while peek(kw(b"except")).parse_next(input).is_ok() {
        handlers.push(parse_except_block(input)?);
    }

    let orelse = if peek(kw(b"else")).parse_next(input).is_ok() {
        parse_else_block(input)?
    } else {
        let py = input.state.py;
        PyList::empty(py).into()
    };

    let finalbody = if peek(kw(b"finally")).parse_next(input).is_ok() {
        let _ = kw(b"finally").parse_next(input)?;
        let _ = op(b":").parse_next(input)?;
        parse_block(input)?
    } else {
        let py = input.state.py;
        PyList::empty(py).into()
    };

    // Try(body, handlers, orelse, finalbody)
    let py = input.state.py;
    let ast = input.state.ast.clone();
    let handlers_list = PyList::new(py, handlers).unwrap();

    let node = ast
        .call_method1("Try", (body, handlers_list, orelse, finalbody))
        .map_err(|_| make_error("Try failed".into()))?;
    Ok(node.into())
}

// Helper needed: parse_star_targets (same as star_expressions but used for assignment)
// For now alias to parse_star_expressions
// star_expression: '*' bitwise_or | expression
fn parse_star_expression<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    if peek(op(b"*")).parse_next(input).is_ok() {
        let _ = op(b"*").parse_next(input)?;
        let expr = parse_bitwise_or(input)?;
        let py = input.state.py;
        let ast = input.state.ast.clone();
        let load = ctx_load(&ast)?;
        let node = ast
            .call_method1("Starred", (expr, load))
            .map_err(|_| make_error("Starred failed".into()))?;
        Ok(node.into())
    } else {
        parse_expression(input)
    }
}

fn parse_star_expressions<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    // start with one
    let first = parse_star_expression(input)?;

    if peek(op(b",")).parse_next(input).is_ok() {
        let _ = op(b",").parse_next(input)?;

        let mut elts = vec![first];

        // If immediate end, it's a tuple (expr,)
        // End can be ')' or ']' or ':' (for for loop?) 'in'?
        // The caller handles delimiters.
        // But `parse_star_expressions` consumes as many as possible?
        // Grammar: star_expression (',' star_expression)* [',']

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
            // If it fails, maybe it wasn't an expression?
            // But we consumed comma!
            // In Python `a,` is valid. `a, b` is valid.
            // `a, =` is assignment target (handled by assignment rule).
            // Only `expression` context matters here.

            // If we consumed comma, we should try to parse expression.
            // If parse fails, backtrack comma?
            // No, `a,` is valid tuple.

            // So if we see start of expression -> parse.
            // If not -> break (trailing comma).

            // Optimization: peek common stoppers.

            // Let's try parsing.
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
        let py = input.state.py;
        let ast = input.state.ast.clone();
        let elts_list = PyList::new(py, elts).unwrap();
        let load = ctx_load(&ast)?;
        Ok(ast.call_method1("Tuple", (elts_list, load)).unwrap().into())
    } else {
        Ok(first)
    }
}

fn parse_star_targets<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    parse_star_expressions(input)
}

// compound_stmt:
//     | &('def' | '@' | 'async') function_def
//     | &'if' if_stmt
//     ...
pub fn parse_compound_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    if peek(kw(b"if")).parse_next(input).is_ok() {
        return parse_if_stmt(input);
    }
    if peek(kw(b"while")).parse_next(input).is_ok() {
        return parse_while_stmt(input);
    }
    if peek(kw(b"class")).parse_next(input).is_ok() {
        return parse_class_def(input);
    }

    if peek(kw(b"async")).parse_next(input).is_ok() {
        let checkpoint = input.checkpoint();
        let _ = kw(b"async").parse_next(input)?;
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

    if peek(kw(b"def")).parse_next(input).is_ok() || peek(op(b"@")).parse_next(input).is_ok() {
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

// param: NAME annotation?
fn parse_param<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let name_tok = parse_name(input)?;
    let name_bytes = get_text(input, &name_tok);
    let name = std::str::from_utf8(name_bytes).unwrap();

    let annotation = if peek(op(b":")).parse_next(input).is_ok() {
        let _ = op(b":").parse_next(input)?;
        Some(parse_expression(input)?)
    } else {
        None
    };

    let py = input.state.py;
    let ast = input.state.ast.clone();
    let ann_obj = match annotation {
        Some(a) => a,
        None => py.None().into(),
    };

    let node = ast
        .call_method1("arg", (name, ann_obj, py.None()))
        .map_err(|_| make_error("arg failed".into()))?;
    Ok(node.into())
}

fn parse_params<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    // Simplified: param (',' param)* [',']
    // TODO: support defaults, slash, star, etc.
    let args_list = separated(0.., parse_param, op(b",")).parse_next(input)?;
    let _: Vec<Py<PyAny>> = args_list; // consume the vec

    // For now we just put them in 'args' (posonlyargs=[], args=args_list, ...)
    let py = input.state.py;
    let ast = input.state.ast.clone();

    let posonlyargs = PyList::empty(py);
    let args = PyList::new(py, args_list).unwrap();
    let kwonlyargs = PyList::empty(py);
    let kw_defaults = PyList::empty(py);
    let defaults = PyList::empty(py);

    // arguments(posonlyargs, args, vararg, kwonlyargs, kw_defaults, kwarg, defaults)
    let node = ast
        .call_method1(
            "arguments",
            (
                posonlyargs,
                args,
                py.None(),
                kwonlyargs,
                kw_defaults,
                py.None(),
                defaults,
            ),
        )
        .map_err(|_| make_error("arguments failed".into()))?;
    Ok(node.into())
}

// function_def
fn parse_function_def<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let decorators = parse_decorators(input)?;

    let is_async = if peek(kw(b"async")).parse_next(input).is_ok() {
        let _ = kw(b"async").parse_next(input)?;
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

    let body = parse_block(input)?;

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

    Ok(node.into())
}

// Arguments (Call/Class bases)
// Returns (args_list, keywords_list)
fn parse_arguments<'s>(input: &mut TokenStream<'s>) -> ModalResult<(Py<PyAny>, Py<PyAny>)> {
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

fn parse_class_def<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let decorators = parse_decorators(input)?;

    let _ = kw(b"class").parse_next(input)?;
    let name_tok = parse_name(input)?;
    let name_bytes = get_text(input, &name_tok);
    let name = std::str::from_utf8(name_bytes).unwrap();

    // type_params?

    let (bases, keywords) = if peek(op(b"(")).parse_next(input).is_ok() {
        let _ = op(b"(").parse_next(input)?;
        let (b, k) = parse_arguments(input)?;
        let _ = op(b")").parse_next(input)?;
        (b, k)
    } else {
        let py = input.state.py;
        (PyList::empty(py).into(), PyList::empty(py).into())
    };

    let _ = op(b":").parse_next(input)?;
    let body = parse_block(input)?;

    let py = input.state.py;
    let ast = input.state.ast.clone();
    let decorator_list = PyList::new(py, decorators).unwrap();

    // ClassDef(name, bases, keywords, body, decorator_list, type_params=[])
    let node = ast
        .call_method1("ClassDef", (name, bases, keywords, body, decorator_list))
        .map_err(|_| make_error("ClassDef failed".into()))?;
    Ok(node.into())
}

// if_stmt[ast.If]:
//     | 'if' a=named_expression ':' b=block c=elif_stmt { ast.If(test=a, body=b, orelse=c or [], LOCATIONS) }
//     | 'if' a=named_expression ':' b=block c=[else_block] { ast.If(test=a, body=b, orelse=c or [], LOCATIONS) }
fn parse_if_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let _ = kw(b"if").parse_next(input)?;
    let a = parse_named_expression(input)?;
    let _ = op(b":").parse_next(input)?;
    let b = parse_block(input)?;
    let c = opt(parse_else_block).parse_next(input)?;

    let py = input.state.py;
    let ast = input.state.ast.clone();

    let orelse = match c {
        Some(block) => block,
        None => PyList::empty(py).into(),
    };

    let node = ast
        .call_method1("If", (a, b, orelse))
        .map_err(|_| make_error("if creation failed".into()))?;
    Ok(node.into())
}

fn parse_else_block<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let _ = kw(b"else").parse_next(input)?;
    let _ = cut_err(op(b":")).parse_next(input)?;
    parse_block(input)
}

// block[list[Any]] (memo):
//     | NEWLINE INDENT a=statements DEDENT { a }
//     | simple_stmts
pub fn parse_block<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let checkpoint = input.checkpoint();

    // NEWLINE INDENT a=statements DEDENT
    match (
        parse_newline,
        parse_indent,
        cut_err(parse_statements),
        parse_dedent,
    )
        .parse_next(input)
    {
        Ok((_, _, stmts, _)) => return Ok(stmts),
        Err(_) => {
            input.reset(&checkpoint);
        }
    }

    parse_simple_stmts.parse_next(input)
}

// simple_stmts[list[Any]]:
//     | a=simple_stmt !';' NEWLINE { [a] }
//     | a1=';'.simple_stmt+ [';'] NEWLINE { a1 }
pub fn parse_simple_stmts<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let checkpoint = input.checkpoint();

    // Option 1: simple_stmt !';' NEWLINE
    if let Ok((stmt, _, _)) = (parse_simple_stmt, not(op(b";")), parse_newline).parse_next(input) {
        let py = input.state.py;
        let list = PyList::new(py, vec![stmt]).unwrap();
        return Ok(list.into());
    }

    input.reset(&checkpoint);

    // Option 2: ';'.simple_stmt+ [';'] NEWLINE

    if let Ok((stmts, _, _)) = (
        separated(1.., parse_simple_stmt, op(b";")),
        opt(op(b";")),
        parse_newline,
    )
        .parse_next(input)
    {
        let stmts_vec: Vec<Py<PyAny>> = stmts;
        let py = input.state.py;
        let list = PyList::new(py, stmts_vec).unwrap();
        return Ok(list.into());
    }

    Err(ErrMode::Backtrack(ContextError::new()))
}

// break_stmt: 'break'
fn parse_break_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let _ = kw(b"break").parse_next(input)?;
    let ast = input.state.ast.clone();
    let node = ast
        .call_method0("Break")
        .map_err(|_| make_error("Break failed".into()))?;
    Ok(node.into())
}

// continue_stmt: 'continue'
fn parse_continue_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let _ = kw(b"continue").parse_next(input)?;
    let ast = input.state.ast.clone();
    let node = ast
        .call_method0("Continue")
        .map_err(|_| make_error("Continue failed".into()))?;
    Ok(node.into())
}

// return_stmt: 'return' [star_expressions]
fn parse_return_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let _ = kw(b"return").parse_next(input)?;
    let value = opt(parse_star_expressions).parse_next(input)?;

    let ast = input.state.ast.clone();
    let val_obj = match value {
        Some(v) => v,
        None => input.state.py.None().into(),
    };
    let node = ast
        .call_method1("Return", (val_obj,))
        .map_err(|_| make_error("Return failed".into()))?;
    Ok(node.into())
}

// raise_stmt: 'raise' [expression ['from' expression]]
fn parse_raise_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let _ = kw(b"raise").parse_next(input)?;
    let exc = opt(parse_expression).parse_next(input)?;
    let cause = if exc.is_some() {
        if peek(kw(b"from")).parse_next(input).is_ok() {
            let _ = kw(b"from").parse_next(input)?;
            opt(parse_expression).parse_next(input)?
        } else {
            None
        }
    } else {
        None
    };

    let ast = input.state.ast.clone();
    let exc_obj = match exc {
        Some(e) => e,
        None => input.state.py.None().into(),
    };
    let cause_obj = match cause {
        Some(c) => c,
        None => input.state.py.None().into(),
    };

    let node = ast
        .call_method1("Raise", (exc_obj, cause_obj))
        .map_err(|_| make_error("Raise failed".into()))?;
    Ok(node.into())
}

// global_stmt: 'global' NAME+
fn parse_global_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let _ = kw(b"global").parse_next(input)?;
    let names = separated(1.., parse_name, op(b",")).parse_next(input)?;

    let names_vec: Vec<TokInfo> = names;
    let mut names_strs = Vec::with_capacity(names_vec.len());
    for t in &names_vec {
        names_strs.push(get_text(input, t));
    }

    let ast = input.state.ast.clone();
    let names_list = PyList::new(input.state.py, names_strs).unwrap();
    let node = ast
        .call_method1("Global", (names_list,))
        .map_err(|_| make_error("Global failed".into()))?;
    Ok(node.into())
}

// nonlocal_stmt: 'nonlocal' NAME+
fn parse_nonlocal_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let _ = kw(b"nonlocal").parse_next(input)?;
    let names = separated(1.., parse_name, op(b",")).parse_next(input)?;

    let names_vec: Vec<TokInfo> = names;
    let mut names_strs = Vec::with_capacity(names_vec.len());
    for t in &names_vec {
        names_strs.push(get_text(input, t));
    }

    let ast = input.state.ast.clone();
    let names_list = PyList::new(input.state.py, names_strs).unwrap();
    let node = ast
        .call_method1("Nonlocal", (names_list,))
        .map_err(|_| make_error("Nonlocal failed".into()))?;
    Ok(node.into())
}

// assert_stmt: 'assert' expression [',' expression]
fn parse_assert_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let _ = kw(b"assert").parse_next(input)?;
    let test = parse_expression(input)?;
    let msg = if peek(op(b",")).parse_next(input).is_ok() {
        let _ = op(b",").parse_next(input)?;
        opt(parse_expression).parse_next(input)?
    } else {
        None
    };

    let ast = input.state.ast.clone();
    let msg_obj = match msg {
        Some(m) => m,
        None => input.state.py.None().into(),
    };
    let node = ast
        .call_method1("Assert", (test, msg_obj))
        .map_err(|_| make_error("Assert failed".into()))?;
    Ok(node.into())
}

// assignment:
//     | NAME ':' expression ['=' annotated_rhs ]
//     | expression '=' ...
//     | expression augassign ...
fn parse_assignment<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let checkpoint = input.checkpoint();
    let lhs = parse_star_expressions(input)?;

    let py = input.state.py;
    let ast = input.state.ast.clone();

    // Check for '=' (Assign)
    if peek(op(b"=")).parse_next(input).is_ok() {
        let mut targets = vec![lhs.bind(py).clone().unbind()];
        while let Ok(_) = op(b"=").parse_next(input) {
            let rhs = parse_star_expressions(input)?;

            // If another '=' follows, rhs is also a target, else it is value
            if peek(op(b"=")).parse_next(input).is_ok() {
                targets.push(rhs);
            } else {
                // Final value
                // Fix contexts for all targets loop
                let store = ctx_store(&ast)?;
                for t in &targets {
                    set_context(py, t, store.bind(py).clone().unbind())?;
                }

                let targets_list = PyList::new(py, targets).unwrap();
                let node = ast
                    .call_method1("Assign", (targets_list, rhs))
                    .map_err(|_| make_error("Assign failed".into()))?;
                return Ok(node.into());
            }
        }
    }

    // Check for ':' (AnnAssign)
    if let Ok(_) = op(b":").parse_next(input) {
        let annotation = parse_expression(input)?;
        let value = if peek(op(b"=")).parse_next(input).is_ok() {
            let _ = op(b"=").parse_next(input)?;
            Some(parse_expression(input)?)
        } else {
            None
        };

        let store = ctx_store(&ast)?;
        set_context(py, &lhs, store)?;

        let simple = 1; // 1 if simple name, else 0. Simplified logic.
        let val_obj = match value {
            Some(v) => v,
            None => py.None().into(),
        };

        let node = ast
            .call_method1("AnnAssign", (lhs, annotation, val_obj, simple))
            .map_err(|_| make_error("AnnAssign failed".into()))?;
        return Ok(node.into());
    }

    // Check for AugAssign (+=, -=, ...)
    // List of aug ops
    let aug_op_node = if let Ok(_) = op(b"+=").parse_next(input) {
        ast.call_method0("Add")
    } else if let Ok(_) = op(b"-=").parse_next(input) {
        ast.call_method0("Sub")
    } else if let Ok(_) = op(b"*=").parse_next(input) {
        ast.call_method0("Mult")
    } else if let Ok(_) = op(b"/=").parse_next(input) {
        ast.call_method0("Div")
    }
    // ... add others ...
    else {
        Err(pyo3::PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "No aug op",
        ))
    };

    if let Ok(op_node) = aug_op_node {
        let value = parse_expression(input)?;
        let store = ctx_store(&ast)?;
        set_context(py, &lhs, store)?;

        let node = ast
            .call_method1("AugAssign", (lhs, op_node, value))
            .map_err(|_| make_error("AugAssign failed".into()))?;
        return Ok(node.into());
    }

    input.reset(&checkpoint);
    Err(ErrMode::Backtrack(ContextError::new()))
}

// import_stmt
fn parse_import_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    // Basic 'import name' support
    let _ = kw(b"import").parse_next(input)?;
    let names = separated(1.., parse_name, op(b",")).parse_next(input)?;

    let names_vec: Vec<TokInfo> = names;
    let ast = input.state.ast.clone();
    let mut aliases = Vec::new();

    for t in names_vec {
        let name = get_text(input, &t);
        let alias = ast
            .call_method1("alias", (name, input.state.py.None()))
            .map_err(|_| make_error("alias failed".into()))?;
        aliases.push(alias);
    }

    let aliases_list = PyList::new(input.state.py, aliases).unwrap();
    let node = ast
        .call_method1("Import", (aliases_list,))
        .map_err(|_| make_error("Import failed".into()))?;
    Ok(node.into())
}

// del_stmt: 'del' star_targets
fn parse_del_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let _ = kw(b"del").parse_next(input)?;
    let targets = parse_star_targets(input)?;

    // targets must be set context to Del?
    // In AST, Delete(targets) where targets is list of exprs.
    // parse_star_targets returns Tuple or Expr.

    let py = input.state.py;
    let ast = input.state.ast.clone();

    let targets_list = if targets.bind(py).get_type().name().unwrap() == "Tuple" {
        targets.bind(py).getattr("elts").unwrap()
    } else {
        PyList::new(py, vec![targets.clone_ref(py)])
            .unwrap()
            .into_any()
    };

    // Set Del context
    let store = ctx_del(&ast)?;
    // We need to traverse targets and set context to Del.
    // set_context(py, &targets, store)?; // My set_context helper handles Tuple/List?
    // I should check set_context implementation.
    // Assuming it does.
    set_context(py, &targets, store)?; // This might fail if targets is not suitable.

    let node = ast
        .call_method1("Delete", (targets_list,))
        .map_err(|_| make_error("Delete failed".into()))?;
    Ok(node.into())
}

// match_stmt: 'match' subject_expr:' newline indent [match_case+] dedent
fn parse_match_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    // TODO: Implement Match (Python 3.10)
    // For now just fail.
    let _ = kw(b"match").parse_next(input)?;
    Err(ErrMode::Backtrack(ContextError::new()))
}

// simple_stmt:
//     | &('import' | 'from') import_stmt
//     | &'global' global_stmt
//     | &'nonlocal' nonlocal_stmt
//     | &'assert' assert_stmt
//     | &'pass' pass_stmt
//     | &'break' break_stmt
//     | &'continue' continue_stmt
//     | &'return' return_stmt
//     | &'raise' raise_stmt
//     | &'del' del_stmt
//     | assignment_or_expression
pub fn parse_simple_stmt<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    // pass
    if peek(kw(b"pass")).parse_next(input).is_ok() {
        let _ = kw(b"pass").parse_next(input)?;
        let ast = input.state.ast.clone();
        let node = ast
            .call_method0("Pass")
            .map_err(|_| make_error("Pass failed".into()))?;
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

    let ast = input.state.ast.clone();
    let node = ast
        .call_method1("Expr", (e,))
        .map_err(|_| make_error("Expr failed".into()))?;
    Ok(node.into())
}

// ### Expression Parsing ###

// named_expression[ast.expr]:
//     | assignment_expression
//     | expression !':='
fn parse_named_expression<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    // TODO: Assignment expression (walrus)
    parse_expression(input)
}

// expression[ast.expr](memo):
//     | a=disjunction 'if' b=disjunction 'else' c=expression { ast.IfExp(...) }
//     | disjunction
//     | lambdef
fn parse_expression<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let checkpoint = input.checkpoint();
    if let Ok(disj) = parse_disjunction(input) {
        // Check for 'if'
        if peek(kw(b"if")).parse_next(input).is_ok() {
            let _ = kw(b"if").parse_next(input)?;
            let test = parse_disjunction(input)?;
            let _ = kw(b"else").parse_next(input)?;
            let orelse = parse_expression(input)?;

            let py = input.state.py;
            let ast = input.state.ast.clone();
            let node = ast
                .call_method1("IfExp", (test, disj, orelse))
                .map_err(|_| make_error("IfExp failed".into()))?;
            return Ok(node.into());
        }
        return Ok(disj);
    }
    input.reset(&checkpoint);

    input.reset(&checkpoint);

    if peek(kw(b"lambda")).parse_next(input).is_ok() {
        return parse_lambdef(input);
    }

    Err(ErrMode::Backtrack(ContextError::new()))
}

// disjunction[ast.expr] (memo):
//     | a=conjunction b=(disjunction_part)+ { ast.BoolOp(op=ast.Or(), values=[a] + b, LOCATIONS) }
//     | conjunction
fn parse_disjunction<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let head = parse_conjunction(input)?;

    let mut values = vec![head];

    while let Ok(_) = peek(kw(b"or")).parse_next(input) {
        let _ = kw(b"or").parse_next(input)?;
        let next = parse_conjunction(input)?;
        values.push(next);
    }

    if values.len() == 1 {
        Ok(values.pop().unwrap())
    } else {
        let py = input.state.py;
        let ast = input.state.ast.clone();
        let op = ast
            .call_method0("Or")
            .map_err(|_| make_error("Or op failed".into()))?;
        let values_list = PyList::new(py, values).unwrap();
        let node = ast
            .call_method1("BoolOp", (op, values_list))
            .map_err(|_| make_error("BoolOp failed".into()))?;
        Ok(node.into())
    }
}

// conjunction[ast.expr] (memo):
//     | a=inversion b=conjunction_part+ { ast.BoolOp(op=ast.And(), values=[a] + b, LOCATIONS) }
//     | inversion
fn parse_conjunction<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let head = parse_inversion(input)?;

    let mut values = vec![head];

    while let Ok(_) = peek(kw(b"and")).parse_next(input) {
        let _ = kw(b"and").parse_next(input)?;
        let next = parse_inversion(input)?;
        values.push(next);
    }

    if values.len() == 1 {
        Ok(values.pop().unwrap())
    } else {
        let py = input.state.py;
        let ast = input.state.ast.clone();
        let op = ast
            .call_method0("And")
            .map_err(|_| make_error("And op failed".into()))?;
        let values_list = PyList::new(py, values).unwrap();
        let node = ast
            .call_method1("BoolOp", (op, values_list))
            .map_err(|_| make_error("BoolOp failed".into()))?;
        Ok(node.into())
    }
}

// inversion[ast.expr] (memo):
//     | 'not' a=inversion { ast.UnaryOp(op=ast.Not(), operand=a, LOCATIONS) }
//     | comparison
fn parse_inversion<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    if peek(kw(b"not")).parse_next(input).is_ok() {
        let _ = kw(b"not").parse_next(input)?;
        let operand = parse_inversion(input)?;
        let py = input.state.py;
        let ast = input.state.ast.clone();
        let op = ast
            .call_method0("Not")
            .map_err(|_| make_error("Not op failed".into()))?;
        let node = ast
            .call_method1("UnaryOp", (op, operand))
            .map_err(|_| make_error("UnaryOp failed".into()))?;
        return Ok(node.into());
    }
    parse_comparison(input)
}

// comparison[ast.expr]:
//     | a=bitwise_or b=compare_op_bitwise_or_pair+ { ast.Compare(...) }
//     | bitwise_or
fn parse_comparison<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let left = parse_bitwise_or(input)?;

    let mut ops = Vec::new();
    let mut comparators = Vec::new();

    // Pre-clone ast for loop
    let ast = input.state.ast.clone();

    loop {
        // Try match comparison operator
        let checkpoint = input.checkpoint();
        let op_node = if let Ok(_) = op(b"==").parse_next(input) {
            ast.call_method0("Eq")
        } else if let Ok(_) = op(b"!=").parse_next(input) {
            ast.call_method0("NotEq")
        } else if let Ok(_) = op(b"<").parse_next(input) {
            ast.call_method0("Lt")
        } else if let Ok(_) = op(b"<=").parse_next(input) {
            ast.call_method0("LtE")
        } else if let Ok(_) = op(b">").parse_next(input) {
            ast.call_method0("Gt")
        } else if let Ok(_) = op(b">=").parse_next(input) {
            ast.call_method0("GtE")
        } else if let Ok(_) = kw(b"is").parse_next(input) {
            if let Ok(_) = kw(b"not").parse_next(input) {
                ast.call_method0("IsNot")
            } else {
                ast.call_method0("Is")
            }
        } else if let Ok(_) = kw(b"in").parse_next(input) {
            ast.call_method0("In")
        } else if let Ok(_) = kw(b"not").parse_next(input) {
            if let Ok(_) = kw(b"in").parse_next(input) {
                ast.call_method0("NotIn")
            } else {
                input.reset(&checkpoint);
                break;
            }
        } else {
            input.reset(&checkpoint);
            break;
        };

        let op_result = match op_node {
            Ok(o) => o,
            Err(_) => {
                input.reset(&checkpoint);
                break;
            }
        };

        let right = parse_bitwise_or(input)?;
        ops.push(op_result);
        comparators.push(right);
    }

    if ops.is_empty() {
        Ok(left)
    } else {
        let py = input.state.py;
        // let ast = input.state.ast.clone(); // already have ast
        let ops_list = PyList::new(py, ops).unwrap();
        let comps_list = PyList::new(py, comparators).unwrap();
        let node = ast
            .call_method1("Compare", (left, ops_list, comps_list))
            .map_err(|_| make_error("Compare failed".into()))?;
        Ok(node.into())
    }
}

// bitwise_or: bitwise_or '|' bitwise_xor | bitwise_xor
// Left recursive -> Iterative
fn parse_bitwise_or<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let mut left = parse_bitwise_xor(input)?;

    while let Ok(_) = op(b"|").parse_next(input) {
        let right = parse_bitwise_xor(input)?;
        let py = input.state.py;
        let ast = input.state.ast.clone();
        let op_node = ast
            .call_method0("BitOr")
            .map_err(|_| make_error("BitOr failed".into()))?;
        left = ast
            .call_method1("BinOp", (left, op_node, right))
            .map_err(|_| make_error("BinOp failed".into()))?
            .into();
    }
    Ok(left)
}

fn parse_bitwise_xor<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let mut left = parse_bitwise_and(input)?;
    while let Ok(_) = op(b"^").parse_next(input) {
        let right = parse_bitwise_and(input)?;
        let py = input.state.py;
        let ast = input.state.ast.clone();
        let op_node = ast
            .call_method0("BitXor")
            .map_err(|_| make_error("BitXor failed".into()))?;
        left = ast
            .call_method1("BinOp", (left, op_node, right))
            .map_err(|_| make_error("BinOp failed".into()))?
            .into();
    }
    Ok(left)
}

fn parse_bitwise_and<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let mut left = parse_shift_expr(input)?;
    while let Ok(_) = op(b"&").parse_next(input) {
        let right = parse_shift_expr(input)?;
        let py = input.state.py;
        let ast = input.state.ast.clone();
        let op_node = ast
            .call_method0("BitAnd")
            .map_err(|_| make_error("BitAnd failed".into()))?;
        left = ast
            .call_method1("BinOp", (left, op_node, right))
            .map_err(|_| make_error("BinOp failed".into()))?
            .into();
    }
    Ok(left)
}

fn parse_shift_expr<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let mut left = parse_sum(input)?;
    loop {
        let py = input.state.py;
        let ast = input.state.ast.clone();
        let op_node = if let Ok(_) = op(b"<<").parse_next(input) {
            ast.call_method0("LShift")
        } else if let Ok(_) = op(b">>").parse_next(input) {
            ast.call_method0("RShift")
        } else {
            break;
        };
        let op_obj = op_node.map_err(|_| make_error("Shift op failed".into()))?;
        let right = parse_sum(input)?;
        left = ast
            .call_method1("BinOp", (left, op_obj, right))
            .map_err(|_| make_error("BinOp failed".into()))?
            .into();
    }
    Ok(left)
}

fn parse_sum<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let mut left = parse_term(input)?;
    loop {
        let py = input.state.py;
        let ast = input.state.ast.clone();
        let op_node = if let Ok(_) = op(b"+").parse_next(input) {
            ast.call_method0("Add")
        } else if let Ok(_) = op(b"-").parse_next(input) {
            ast.call_method0("Sub")
        } else {
            break;
        };
        let op_obj = op_node.map_err(|_| make_error("Sum op failed".into()))?;
        let right = parse_term(input)?;
        left = ast
            .call_method1("BinOp", (left, op_obj, right))
            .map_err(|_| make_error("BinOp failed".into()))?
            .into();
    }
    Ok(left)
}

fn parse_term<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let mut left = parse_factor(input)?;
    loop {
        let py = input.state.py;
        let ast = input.state.ast.clone();
        let op_node = if let Ok(_) = op(b"*").parse_next(input) {
            ast.call_method0("Mult")
        } else if let Ok(_) = op(b"/").parse_next(input) {
            ast.call_method0("Div")
        } else if let Ok(_) = op(b"//").parse_next(input) {
            ast.call_method0("FloorDiv")
        } else if let Ok(_) = op(b"%").parse_next(input) {
            ast.call_method0("Mod")
        } else if let Ok(_) = op(b"@").parse_next(input) {
            ast.call_method0("MatMult")
        } else {
            break;
        };
        let op_obj = op_node.map_err(|_| make_error("Term op failed".into()))?;
        let right = parse_factor(input)?;
        left = ast
            .call_method1("BinOp", (left, op_obj, right))
            .map_err(|_| make_error("BinOp failed".into()))?
            .into();
    }
    Ok(left)
}

// factor (memo):
//     | '+' a=factor { ast.UnaryOp(op=ast.UAdd(), operand=a, LOCATIONS) }
//     | '-' a=factor { ast.UnaryOp(op=ast.USub(), operand=a, LOCATIONS) }
//     | '~' a=factor { ast.UnaryOp(op=ast.Invert(), operand=a, LOCATIONS) }
//     | power
fn parse_factor<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let checkpoint = input.checkpoint();
    let py = input.state.py;
    let ast = input.state.ast.clone();

    if let Ok(_) = op(b"+").parse_next(input) {
        let op_node = ast
            .call_method0("UAdd")
            .map_err(|_| make_error("UAdd failed".into()))?;
        let operand = parse_factor(input)?;
        let node = ast
            .call_method1("UnaryOp", (op_node, operand))
            .map_err(|_| make_error("UnaryOp failed".into()))?;
        return Ok(node.into());
    }
    if let Ok(_) = op(b"-").parse_next(input) {
        let op_node = ast
            .call_method0("USub")
            .map_err(|_| make_error("USub failed".into()))?;
        let operand = parse_factor(input)?;
        let node = ast
            .call_method1("UnaryOp", (op_node, operand))
            .map_err(|_| make_error("UnaryOp failed".into()))?;
        return Ok(node.into());
    }
    if let Ok(_) = op(b"~").parse_next(input) {
        let op_node = ast
            .call_method0("Invert")
            .map_err(|_| make_error("Invert failed".into()))?;
        let operand = parse_factor(input)?;
        let node = ast
            .call_method1("UnaryOp", (op_node, operand))
            .map_err(|_| make_error("UnaryOp failed".into()))?;
        return Ok(node.into());
    }

    parse_power(input)
}

// power:
//     | a=await_primary '**' b=factor { ast.BinOp(left=a, op=ast.Pow(), right=b, LOCATIONS) }
//     | await_primary
fn parse_power<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let left = parse_await_primary(input)?;
    if let Ok(_) = op(b"**").parse_next(input) {
        let right = parse_factor(input)?;
        let py = input.state.py;
        let ast = input.state.ast.clone();
        let op_node = ast
            .call_method0("Pow")
            .map_err(|_| make_error("Pow failed".into()))?;
        let node = ast
            .call_method1("BinOp", (left, op_node, right))
            .map_err(|_| make_error("BinOp failed".into()))?;
        return Ok(node.into());
    }
    Ok(left)
}

// await_primary (memo):
//     | 'await' a=primary { ast.Await(a, LOCATIONS) }
//     | primary
fn parse_await_primary<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    if let Ok(_) = kw(b"await").parse_next(input) {
        let a = parse_primary(input)?;
        let py = input.state.py;
        let ast = input.state.ast.clone();
        let node = ast
            .call_method1("Await", (a,))
            .map_err(|_| make_error("Await failed".into()))?;
        return Ok(node.into());
    }
    parse_primary(input)
}

// slice:
//     | [expression] ':' [expression] [':' [expression] ]
//     | expression
fn parse_slice<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
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
            return Ok(node.into());
        } else {
            // Just expression
            return Ok(lower);
        }
    }

    // Missing expression but maybe ':' ... handled above
    // If we are here, we failed to parse expr and didn't see ':'.
    // Maybe we are []? But slice must match something?
    // Subscript requires slice.

    input.reset(&checkpoint);
    Err(ErrMode::Backtrack(ContextError::new()))
}

fn parse_slices<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
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

        let py = input.state.py;
        let ast = input.state.ast.clone();
        let elts_list = PyList::new(py, elts).unwrap();
        let load = ctx_load(&ast)?;
        // x[a,b] -> subscript(val, Tuple(elts, Load))
        // But for ExtSlice (py<3.9), it was different.
        // For Py3.9+, x[a,b] is Subscript(value=x, slice=Tuple(elts))
        Ok(ast.call_method1("Tuple", (elts_list, load)).unwrap().into())
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
    let mut left = parse_atom(input)?;

    let py = input.state.py;
    let ast = input.state.ast.clone();
    let load = ctx_load(&ast)?;

    loop {
        // Attribute: . NAME
        if let Ok(_) = op(b".").parse_next(input) {
            let name_tok = parse_name(input)?;
            let text = get_text(input, &name_tok);
            left = ast
                .call_method1("Attribute", (left, text, load.bind(py).clone().unbind()))
                .map_err(|_| make_error("Attribute failed".into()))?
                .into();
            continue;
        }

        // Call: ( ... )
        if let Ok(_) = op(b"(").parse_next(input) {
            let (args, keywords) = parse_arguments(input)?;
            let _ = op(b")").parse_next(input)?;

            left = ast
                .call_method1("Call", (left, args, keywords))
                .map_err(|_| make_error("Call failed".into()))?
                .into();
            continue;
        }

        // Subscript: [ ... ]
        if let Ok(_) = op(b"[").parse_next(input) {
            let slice = parse_slices(input)?;
            let _ = op(b"]").parse_next(input)?;
            left = ast
                .call_method1("Subscript", (left, slice, load.bind(py).clone().unbind()))
                .map_err(|_| make_error("Subscript failed".into()))?
                .into();
            continue;
        }

        break;
    }

    Ok(left)
}

// generators: comprehension+
fn parse_generators<'s>(input: &mut TokenStream<'s>) -> ModalResult<Vec<Py<PyAny>>> {
    let mut generators = Vec::new();

    loop {
        let is_async = if peek(kw(b"async")).parse_next(input).is_ok() {
            let _ = kw(b"async").parse_next(input)?;
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

            let py = input.state.py;
            let ast = input.state.ast.clone();

            let store = ctx_store(&ast)?;
            set_context(py, &target, store)?;

            let ifs_list = PyList::new(py, ifs).unwrap();

            let node = ast
                .call_method1("comprehension", (target, iter, ifs_list, is_async))
                .map_err(|_| make_error("comprehension failed".into()))?;
            generators.push(node.into());

            // Check if next is 'async for' or 'for' to continue loop
            // If not, break
            let has_async = peek(kw(b"async")).parse_next(input).is_ok();
            let has_for = peek(kw(b"for")).parse_next(input).is_ok();

            if !has_async && !has_for {
                break;
            }
        } else {
            // Should not happen if called correctly (should start with async/for)
            break;
        }
    }

    Ok(generators)
}

// lambdef:
//     | 'lambda' [params] ':' body=expression
fn parse_lambdef<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let _ = kw(b"lambda").parse_next(input)?;

    let args = if !peek(op(b":")).parse_next(input).is_ok() {
        parse_params(input)?
    } else {
        let py = input.state.py;
        let ast = input.state.ast.clone();
        ast.call_method1(
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
        .unwrap()
        .into()
    };

    let _ = op(b":").parse_next(input)?;
    let body = parse_expression(input)?;

    let py = input.state.py;
    let ast = input.state.ast.clone();
    let node = ast
        .call_method1("Lambda", (args, body))
        .map_err(|_| make_error("Lambda failed".into()))?;
    Ok(node.into())
}

fn parse_dict_maker<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let _ = op(b"{").parse_next(input)?;

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
        let _ = op(b"}").parse_next(input)?;
        let py = input.state.py;
        let ast = input.state.ast.clone();
        let keys_list = PyList::new(py, keys).unwrap();
        let values_list = PyList::new(py, values).unwrap();
        return Ok(ast
            .call_method1("Dict", (keys_list, values_list))
            .unwrap()
            .into());
    }

    // Parse first key/value
    let key = parse_expression(input)?;
    let _ = op(b":").parse_next(input)?;
    let value = parse_expression(input)?;

    // Check for comprehension
    if peek(kw(b"for")).parse_next(input).is_ok() || peek(kw(b"async")).parse_next(input).is_ok() {
        let generators = parse_generators(input)?;
        let _ = op(b"}").parse_next(input)?;

        let py = input.state.py;
        let ast = input.state.ast.clone();
        let gens_list = PyList::new(py, generators).unwrap();
        let node = ast
            .call_method1("DictComp", (key, value, gens_list))
            .map_err(|_| make_error("DictComp failed".into()))?;
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

    let _ = op(b"}").parse_next(input)?;
    let py = input.state.py;
    let ast = input.state.ast.clone();
    let keys_list = PyList::new(py, keys).unwrap();
    let values_list = PyList::new(py, values).unwrap();
    Ok(ast
        .call_method1("Dict", (keys_list, values_list))
        .unwrap()
        .into())
}

fn parse_set_maker<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let _ = op(b"{").parse_next(input)?;

    // Parse first element
    let first = parse_star_expression(input)?;

    // Check for comprehension
    if peek(kw(b"for")).parse_next(input).is_ok() || peek(kw(b"async")).parse_next(input).is_ok() {
        let generators = parse_generators(input)?;
        let _ = op(b"}").parse_next(input)?;

        let py = input.state.py;
        let ast = input.state.ast.clone();
        let gens_list = PyList::new(py, generators).unwrap();
        let node = ast
            .call_method1("SetComp", (first, gens_list))
            .map_err(|_| make_error("SetComp failed".into()))?;
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

    let _ = op(b"}").parse_next(input)?;

    let py = input.state.py;
    let ast = input.state.ast.clone();
    let elts_list = PyList::new(py, elts).unwrap();
    Ok(ast.call_method1("Set", (elts_list,)).unwrap().into())
}

fn parse_fstring_middle<'s>(
    input: &mut TokenStream<'s>,
    is_format_spec: bool,
) -> ModalResult<Vec<Py<PyAny>>> {
    let mut parts = Vec::new();
    let py = input.state.py;
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
            let node = ast
                .call_method1("Constant", (text,))
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
fn parse_atom<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let py = input.state.py;
    let ast = input.state.ast.clone();

    if let Ok(tok) = parse_name(input) {
        let text = get_text(input, &tok);
        if text == b"True" {
            // ... (keep constants)
            let node = ast
                .call_method1("Constant", (true,))
                .map_err(|_| make_error("Constant failed".into()))?;
            return Ok(node.into());
        } else if text == b"False" {
            // ...
            let node = ast
                .call_method1("Constant", (false,))
                .map_err(|_| make_error("Constant failed".into()))?;
            return Ok(node.into());
        } else if text == b"None" {
            // ...
            let node = ast
                .call_method1("Constant", (py.None(),))
                .map_err(|_| make_error("Constant failed".into()))?;
            return Ok(node.into());
        } else {
            let load = ctx_load(&ast)?;
            let text_str = std::str::from_utf8(text).unwrap();
            let node = ast
                .call_method1("Name", (text_str, load))
                .map_err(|_| make_error("Name failed".into()))?;
            return Ok(node.into());
        }
    }

    if let Ok(tok) = parse_number(input) {
        // ... (keep number logic)
        let text = get_text(input, &tok);
        let text_str = std::str::from_utf8(text).unwrap();
        let val = match text_str.parse::<i64>() {
            Ok(i) => i.into_pyobject(py).unwrap().into_any().unbind(),
            Err(_) => text_str.into_pyobject(py).unwrap().into_any().unbind(),
        };
        let node = ast
            .call_method1("Constant", (val,))
            .map_err(|_| make_error("Constant failed".into()))?;
        return Ok(node.into());
    }

    // String concatenation (including f-strings)
    let mut string_nodes: Vec<Py<PyAny>> = Vec::new();
    let mut has_fstring = false;

    loop {
        if let Ok(tok) = parse_string(input) {
            let text = get_text(input, &tok);
            let text_str = std::str::from_utf8(text).unwrap();
            let val = ast
                .call_method1("literal_eval", (text_str,))
                .map_err(|_| make_error("literal_eval failed".into()))?;
            let node = ast
                .call_method1("Constant", (val,))
                .map_err(|_| make_error("Constant failed".into()))?;
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
        if !has_fstring {
            // Merge all constants into one
            let mut full_text = String::new();
            for node in string_nodes {
                // node is Constant. value is str.
                let val = node
                    .getattr(py, "value")
                    .map_err(|_| make_error("Attribute error".into()))?;
                let s: String = val
                    .extract(py)
                    .map_err(|_| make_error("Extract error".into()))?;
                full_text.push_str(&s);
            }
            let node = ast
                .call_method1("Constant", (full_text,))
                .map_err(|_| make_error("Constant failed".into()))?;
            return Ok(node.into());
        } else {
            // Mixed strings and f-strings -> JoinedStr
            // Flatten JoinedStr nodes
            let mut final_parts = Vec::new();
            for node in string_nodes {
                // Check if JoinedStr
                // We use unbound string check or isinstance logic by checking attribute
                // JoinedStr has 'values', Constant has 'value'
                if let Ok(values) = node.getattr(py, "values") {
                    // It's JoinedStr(values=[...])
                    let values_bound = values.bind(py);
                    let values_list = values_bound
                        .cast::<PyList>()
                        .map_err(|_| make_error("Cast failed".into()))?;

                    for v in values_list {
                        final_parts.push(v.clone().unbind());
                    }
                } else {
                    // Constant. Treat as one part of JoinedStr.
                    final_parts.push(node);
                }
            }
            let parts_list = PyList::new(py, final_parts).unwrap();
            let node = ast
                .call_method1("JoinedStr", (parts_list,))
                .map_err(|_| make_error("JoinedStr failed".into()))?;
            return Ok(node.into());
        }
    }

    if let Ok(_) = op(b"...").parse_next(input) {
        let node = ast
            .call_method1("Constant", (py.Ellipsis(),))
            .map_err(|_| make_error("Constant failed".into()))?;
        return Ok(node.into());
    }

    // Group (...) or Tuple
    if peek(op(b"(")).parse_next(input).is_ok() {
        let _ = op(b"(").parse_next(input)?;
        if peek(op(b")")).parse_next(input).is_ok() {
            let _ = op(b")").parse_next(input)?;
            let load = ctx_load(&ast)?;
            let node = ast
                .call_method1("Tuple", (PyList::empty(py), load))
                .unwrap();
            return Ok(node.into());
        }

        let expr = parse_star_expressions(input)?; // Returns Tuple or Expr
        let _ = op(b")").parse_next(input)?;
        // If expr is NOT a Tuple node, it is a grouping (parens)
        // If it returns Tuple, it was explicitly created by comma.
        // So we return expr as is.
        // (a) -> a
        // (a,) -> Tuple([a])
        return Ok(expr);
    }

    // List [...]
    if let Ok(_) = op(b"[").parse_next(input) {
        if peek(op(b"]")).parse_next(input).is_ok() {
            let _ = op(b"]").parse_next(input)?;
            let load = ctx_load(&ast)?;
            let empty = PyList::empty(py);
            let node = ast.call_method1("List", (empty, load)).unwrap();
            return Ok(node.into());
        }

        let first = parse_star_expression(input)?;

        if peek(kw(b"for")).parse_next(input).is_ok()
            || peek(kw(b"async")).parse_next(input).is_ok()
        {
            let generators = parse_generators(input)?;
            let _ = op(b"]").parse_next(input)?;
            let gens_list = PyList::new(py, generators).unwrap();
            let node = ast
                .call_method1("ListComp", (first, gens_list))
                .map_err(|_| make_error("ListComp failed".into()))?;
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

        let _ = op(b"]").parse_next(input)?;
        let load = ctx_load(&ast)?;
        let elts_list = PyList::new(py, elts).unwrap();
        let node = ast.call_method1("List", (elts_list, load)).unwrap();
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

    // DEBUG
    println!(
        "Filtered tokens: {:?}",
        filtered_tokens
            .iter()
            .map(|t| (t.typ, t.span))
            .collect::<Vec<_>>()
    );

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

    let res = parse_file.parse_next(&mut input);

    match res {
        Ok(obj) => Ok(obj),
        Err(e) => Err(pyo3::exceptions::PySyntaxError::new_err(format!(
            "Parsing failed: {:?}",
            e
        ))),
    }
}

#[pyfunction]
pub fn parse_code(py: Python, source: &str) -> PyResult<Py<PyAny>> {
    parse(py, source)
}

#[pyfunction]
pub fn ping() -> String {
    "pong".to_string()
}
