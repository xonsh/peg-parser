"""Xonsh AST tests."""

import pytest

from ply_parser import xast as ast
from ply_parser.xast import BinOp, Call, Name, Store, Tuple, min_line


def test_gather_names_name():
    node = Name(id="y", ctx=Store())
    exp = {"y"}
    obs = ast.gather_names(node)
    assert exp == obs


def test_gather_names_tuple():
    node = Tuple(elts=[Name(id="y", ctx=Store()), Name(id="z", ctx=Store())])
    exp = {"y", "z"}
    obs = ast.gather_names(node)
    assert exp == obs


def test_gather_load_store_names_tuple():
    node = Tuple(elts=[Name(id="y", ctx=Store()), Name(id="z", ctx=Store())])
    lexp = set()
    sexp = {"y", "z"}
    lobs, sobs = ast.gather_load_store_names(node)
    assert lexp == lobs
    assert sexp == sobs


@pytest.mark.parametrize(
    "line1",
    [
        "x = 1",  # Both, ls and l remain undefined.
        "ls = 1",  # l remains undefined.
        "l = 1",  # ls remains undefined.
    ],
)
def test_multilline_num(xonsh_execer_parse, line1):
    # Subprocess transformation happens on the second line,
    # because not all variables are known.
    code = line1 + "\nls -l\n"
    tree = xonsh_execer_parse(code)
    lsnode = tree.body[1]
    assert 2 == min_line(lsnode)
    assert isinstance(lsnode.value, Call)


def test_multilline_no_transform(xonsh_execer_parse):
    # No subprocess transformations happen here, since all variables are known.
    code = "ls = 1\nl = 1\nls -l\n"
    tree = xonsh_execer_parse(code)
    lsnode = tree.body[2]
    assert 3 == min_line(lsnode)
    assert isinstance(lsnode.value, BinOp)


@pytest.mark.parametrize(
    "inp",
    [
        """def f():
    if True:
        pass
""",
        """def f(x):
    if x:
        pass
""",
        """def f(*args):
    if not args:
        pass
""",
        """def f(*, y):
    if y:
        pass
""",
        """def f(**kwargs):
    if not kwargs:
        pass
""",
        """def f(k=42):
    if not k:
        pass
""",
        """def f(k=10, *, a, b=1, **kw):
    if not kw and b:
        pass
""",
        """import os
path = '/path/to/wakka'
paths = []
for root, dirs, files in os.walk(path):
    paths.extend(os.path.join(root, d) for d in dirs)
    paths.extend(os.path.join(root, f) for f in files)
""",
        """lambda x: x + 1
""",
        """def f(x):
    return [i for i in x if i is not None and i < 10]
    """,
    ],
)
def test_unmodified(inp, check_ast):
    # Context sensitive parsing should not modify AST
    check_ast(inp, mode="exec", run=False)


@pytest.mark.parametrize(
    "test_input",
    ["echo; echo && echo\n", "echo; echo && echo a\n", "true && false && true\n"],
)
def test_whitespace_subproc(test_input, xonsh_execer_parse):
    assert xonsh_execer_parse(test_input)
