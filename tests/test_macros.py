import itertools
from ast import AST

import pytest


def test_macro_call_empty(check_xonsh_ast):
    assert check_xonsh_ast("f!()", False)


MACRO_ARGS = [
    "x",
    "True",
    "None",
    "import os",
    "x=10",
    '"oh no, mom"',
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
@pytest.mark.xfail
def test_macro_call_one_arg(check_xonsh_ast, s):
    f = f"f!({s})"
    tree = check_xonsh_ast(f, False, return_obs=True)
    assert isinstance(tree, AST)
    args = tree.body.args[1].elts
    assert len(args) == 1
    assert args[0].s == s.strip()


@pytest.mark.parametrize("s,t", itertools.product(MACRO_ARGS[::2], MACRO_ARGS[1::2]))
@pytest.mark.xfail
def test_macro_call_two_args(check_xonsh_ast, s, t):
    f = f"f!({s}, {t})"
    tree = check_xonsh_ast(f, False, return_obs=True)
    assert isinstance(tree, AST)
    args = tree.body.args[1].elts
    assert len(args) == 2
    assert args[0].s == s.strip()
    assert args[1].s == t.strip()


@pytest.mark.parametrize("s,t,u", itertools.product(MACRO_ARGS[::3], MACRO_ARGS[1::3], MACRO_ARGS[2::3]))
@pytest.mark.xfail
def test_macro_call_three_args(check_xonsh_ast, s, t, u):
    f = f"f!({s}, {t}, {u})"
    tree = check_xonsh_ast(f, False, return_obs=True)
    assert isinstance(tree, AST)
    args = tree.body.args[1].elts
    assert len(args) == 3
    assert args[0].s == s.strip()
    assert args[1].s == t.strip()
    assert args[2].s == u.strip()


@pytest.mark.parametrize("s", MACRO_ARGS)
@pytest.mark.xfail
def test_macro_call_one_trailing(check_xonsh_ast, s):
    f = f"f!({s},)"
    tree = check_xonsh_ast(f, False, return_obs=True)
    assert isinstance(tree, AST)
    args = tree.body.args[1].elts
    assert len(args) == 1
    assert args[0].s == s.strip()


@pytest.mark.parametrize("s", MACRO_ARGS)
@pytest.mark.xfail
def test_macro_call_one_trailing_space(check_xonsh_ast, s):
    f = f"f!( {s}, )"
    tree = check_xonsh_ast(f, False, return_obs=True)
    assert isinstance(tree, AST)
    args = tree.body.args[1].elts
    assert len(args) == 1
    assert args[0].s == s.strip()
