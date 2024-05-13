import itertools
from ast import AST
from unittest.mock import ANY

import pytest


def test_macro_call_empty(check_xonsh_ast, xsh):
    tree = check_xonsh_ast("f!()", f="f")
    assert isinstance(tree, AST)


MACRO_ARGS = [
    "x",
    "True",
    "None",
    "import os",
    "x=10",
    '"oh my kadavule!"',
    "...",
    " ... ",
    "if True:\n  pass",
    "{x: y}",
    "{x: y, 42: 5}",
    "{1, 2, 3,}",
    "(x,y)",
    "(x, y)",
    "((x, y), z)",
    "g()",
    "range(10)",
    "range(1, 10, 2)",
    "()",
    "{}",
    "[]",
    "[1, 2]",
    "@(x)",
    "!(ls -l)",
    "![ls -l]",
    "$(ls -l)",
    "${x + y}",
    "$[ls -l]",
    "@$(which xonsh)",
]


@pytest.mark.parametrize("s", MACRO_ARGS)
def test_macro_call_one_arg(check_xonsh_ast, s, xsh):
    f = f"f!({s})"

    tree = check_xonsh_ast(f, f="f", x="x", mode="exec")
    assert isinstance(tree, AST)
    xsh.call_macro.assert_called_once_with("f", (s,), ANY, ANY)


@pytest.mark.parametrize("s,t", itertools.product(MACRO_ARGS[::2], MACRO_ARGS[1::2]))
def test_macro_call_two_args(check_xonsh_ast, s, t, xsh):
    f = f"f!({s}, {t})"
    tree = check_xonsh_ast(f, f="f", x="x")
    assert isinstance(tree, AST)
    args = xsh.call_macro.call_args.args[1]
    assert [ar.strip() for ar in args] == [s.strip(), t.strip()]


@pytest.mark.parametrize("s,t,u", itertools.product(MACRO_ARGS[::3], MACRO_ARGS[1::3], MACRO_ARGS[2::3]))
def test_macro_call_three_args(check_xonsh_ast, s, t, u, xsh):
    f = f"f!({s}, {t}, {u})"
    tree = check_xonsh_ast(f, f="f", x="x")
    assert isinstance(tree, AST)
    args = xsh.call_macro.call_args.args[1]
    assert [ar.strip() for ar in args] == [s.strip(), t.strip(), u.strip()]


@pytest.mark.parametrize("s", MACRO_ARGS)
def test_macro_call_one_trailing(check_xonsh_ast, s, xsh):
    f = f"f!({s},)"
    tree = check_xonsh_ast(f, f="f", x="x")
    assert isinstance(tree, AST)
    args = xsh.call_macro.call_args.args[1]
    assert [ar.strip() for ar in args] == [s.strip()]


@pytest.mark.parametrize("s", MACRO_ARGS)
def test_macro_call_one_trailing_space(check_xonsh_ast, s, xsh):
    f = f"f!( {s}, )"
    tree = check_xonsh_ast(f, f="f", x="x")
    assert isinstance(tree, AST)
    args = xsh.call_macro.call_args.args[1]
    assert [ar.strip() for ar in args] == [s.strip()]
