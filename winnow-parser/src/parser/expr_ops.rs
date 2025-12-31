use super::expressions::parse_await_primary;
use super::{kw, make_error, op, TokenStream};

use pyo3::prelude::*;
use pyo3::types::PyList;
use winnow::combinator::peek;
use winnow::prelude::*;

// disjunction[ast.expr] (memo):
//     | a=conjunction b=(disjunction_part)+ { ast.BoolOp(op=ast.Or(), values=[a] + b, LOCATIONS) }
//     | conjunction
pub fn parse_disjunction<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
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
pub fn parse_conjunction<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
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
pub fn parse_inversion<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    if peek(kw(b"not")).parse_next(input).is_ok() {
        let _ = kw(b"not").parse_next(input)?;
        let operand = parse_inversion(input)?;
        let _py = input.state.py;
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
pub fn parse_comparison<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
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
pub fn parse_bitwise_or<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let mut left = parse_bitwise_xor(input)?;

    while let Ok(_) = op(b"|").parse_next(input) {
        let right = parse_bitwise_xor(input)?;
        let _py = input.state.py;
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

pub fn parse_bitwise_xor<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let mut left = parse_bitwise_and(input)?;
    while let Ok(_) = op(b"^").parse_next(input) {
        let right = parse_bitwise_and(input)?;
        let _py = input.state.py;
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

pub fn parse_bitwise_and<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let mut left = parse_shift_expr(input)?;
    while let Ok(_) = op(b"&").parse_next(input) {
        let right = parse_shift_expr(input)?;
        let _py = input.state.py;
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

pub fn parse_shift_expr<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let mut left = parse_sum(input)?;
    loop {
        let _py = input.state.py;
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

pub fn parse_sum<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let mut left = parse_term(input)?;
    loop {
        let _py = input.state.py;
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

pub fn parse_term<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let mut left = parse_factor(input)?;
    loop {
        let _py = input.state.py;
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
pub fn parse_factor<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let _checkpoint = input.checkpoint();
    let _py = input.state.py;
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
pub fn parse_power<'s>(input: &mut TokenStream<'s>) -> ModalResult<Py<PyAny>> {
    let left = parse_await_primary(input)?;
    if let Ok(_) = op(b"**").parse_next(input) {
        let right = parse_factor(input)?;
        let _py = input.state.py;
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
