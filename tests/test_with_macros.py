import textwrap
from ast import AST, Pass, With

import pytest

WITH_BANG_RAWSUITES = [
    "pass\n",
    "x = 42\ny = 12\n",
    'export PATH="yo:momma"\necho $PATH\n',
    ("with q as t:\n" "    v = 10\n" "\n"),
    (
        "with q as t:\n"
        "    v = 10\n"
        "\n"
        "for x in range(6):\n"
        "    if True:\n"
        "        pass\n"
        "    else:\n"
        "        ls -l\n"
        "\n"
        "a = 42\n"
    ),
]


@pytest.mark.parametrize("body", WITH_BANG_RAWSUITES)
@pytest.mark.xfail
def test_withbang_single_suite(body, check_xonsh_ast):
    code = "with! x:\n{}".format(textwrap.indent(body, "    "))
    tree = check_xonsh_ast(code, False, return_obs=True, mode="exec")
    assert isinstance(tree, AST)
    wither = tree.body[0]
    assert isinstance(wither, With)
    assert len(wither.body) == 1
    assert isinstance(wither.body[0], Pass)
    assert len(wither.items) == 1
    item = wither.items[0]
    s = item.context_expr.args[1].s
    assert s == body


@pytest.mark.parametrize("body", WITH_BANG_RAWSUITES)
@pytest.mark.xfail
def test_withbang_as_single_suite(body, check_xonsh_ast):
    code = "with! x as y:\n{}".format(textwrap.indent(body, "    "))
    tree = check_xonsh_ast(code, False, return_obs=True, mode="exec")
    assert isinstance(tree, AST)
    wither = tree.body[0]
    assert isinstance(wither, With)
    assert len(wither.body) == 1
    assert isinstance(wither.body[0], Pass)
    assert len(wither.items) == 1
    item = wither.items[0]
    assert item.optional_vars.id == "y"
    s = item.context_expr.args[1].s
    assert s == body


@pytest.mark.parametrize("body", WITH_BANG_RAWSUITES)
@pytest.mark.xfail
def test_withbang_single_suite_trailing(body, check_xonsh_ast):
    code = "with! x:\n{}\nprint(x)\n".format(textwrap.indent(body, "    "))
    tree = check_xonsh_ast(
        {},
        code,
        False,
        return_obs=True,
        mode="exec",
        # debug_level=100
    )
    assert isinstance(tree, AST)
    wither = tree.body[0]
    assert isinstance(wither, With)
    assert len(wither.body) == 1
    assert isinstance(wither.body[0], Pass)
    assert len(wither.items) == 1
    item = wither.items[0]
    s = item.context_expr.args[1].s
    assert s == body + "\n"


WITH_BANG_RAWSIMPLE = [
    "pass",
    "x = 42; y = 12",
    'export PATH="yo:momma"; echo $PATH',
    "[1,\n    2,\n    3]",
]


@pytest.mark.parametrize("body", WITH_BANG_RAWSIMPLE)
@pytest.mark.xfail
def test_withbang_single_simple(body, check_xonsh_ast):
    code = f"with! x: {body}\n"
    tree = check_xonsh_ast(code, False, return_obs=True, mode="exec")
    assert isinstance(tree, AST)
    wither = tree.body[0]
    assert isinstance(wither, With)
    assert len(wither.body) == 1
    assert isinstance(wither.body[0], Pass)
    assert len(wither.items) == 1
    item = wither.items[0]
    s = item.context_expr.args[1].s
    assert s == body


@pytest.mark.parametrize("body", WITH_BANG_RAWSIMPLE)
@pytest.mark.xfail
def test_withbang_single_simple_opt(body, check_xonsh_ast):
    code = f"with! x as y: {body}\n"
    tree = check_xonsh_ast(code, False, return_obs=True, mode="exec")
    assert isinstance(tree, AST)
    wither = tree.body[0]
    assert isinstance(wither, With)
    assert len(wither.body) == 1
    assert isinstance(wither.body[0], Pass)
    assert len(wither.items) == 1
    item = wither.items[0]
    assert item.optional_vars.id == "y"
    s = item.context_expr.args[1].s
    assert s == body


@pytest.mark.parametrize("body", WITH_BANG_RAWSUITES)
@pytest.mark.xfail
def test_withbang_as_many_suite(body, check_xonsh_ast):
    code = "with! x as a, y as b, z as c:\n{}"
    code = code.format(textwrap.indent(body, "    "))
    tree = check_xonsh_ast(code, False, return_obs=True, mode="exec")
    assert isinstance(tree, AST)
    wither = tree.body[0]
    assert isinstance(wither, With)
    assert len(wither.body) == 1
    assert isinstance(wither.body[0], Pass)
    assert len(wither.items) == 3
    for i, targ in enumerate("abc"):
        item = wither.items[i]
        assert item.optional_vars.id == targ
        s = item.context_expr.args[1].s
        assert s == body
