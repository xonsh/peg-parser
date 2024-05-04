from ast import AST

import pytest

SUBPROC_MACRO_OC = [("!(", ")"), ("$(", ")"), ("![", "]"), ("$[", "]")]


@pytest.mark.parametrize("opener, closer", SUBPROC_MACRO_OC)
@pytest.mark.parametrize("body", ["echo!", "echo !", "echo ! "])
@pytest.mark.xfail
def test_empty_subprocbang(opener, closer, body, check_xonsh_ast):
    tree = check_xonsh_ast(opener + body + closer, False, return_obs=True)
    assert isinstance(tree, AST)
    cmd = tree.body.args[0].elts
    assert len(cmd) == 2
    assert cmd[1].s == ""


@pytest.mark.parametrize("opener, closer", SUBPROC_MACRO_OC)
@pytest.mark.parametrize("body", ["echo!x", "echo !x", "echo !x", "echo ! x"])
@pytest.mark.xfail
def test_single_subprocbang(opener, closer, body, check_xonsh_ast):
    tree = check_xonsh_ast(opener + body + closer, False, return_obs=True)
    assert isinstance(tree, AST)
    cmd = tree.body.args[0].elts
    assert len(cmd) == 2
    assert cmd[1].s == "x"


@pytest.mark.parametrize("opener, closer", SUBPROC_MACRO_OC)
@pytest.mark.parametrize("body", ["echo -n!x", "echo -n!x", "echo -n !x", "echo -n ! x"])
@pytest.mark.xfail
def test_arg_single_subprocbang(opener, closer, body, check_xonsh_ast):
    tree = check_xonsh_ast(opener + body + closer, False, return_obs=True)
    assert isinstance(tree, AST)
    cmd = tree.body.args[0].elts
    assert len(cmd) == 3
    assert cmd[2].s == "x"


@pytest.mark.parametrize("opener, closer", SUBPROC_MACRO_OC)
@pytest.mark.parametrize("ipener, iloser", [("$(", ")"), ("@$(", ")"), ("$[", "]")])
@pytest.mark.parametrize("body", ["echo -n!x", "echo -n!x", "echo -n !x", "echo -n ! x"])
@pytest.mark.xfail
def test_arg_single_subprocbang_nested(opener, closer, ipener, iloser, body, check_xonsh_ast):
    tree = check_xonsh_ast(opener + body + closer, False, return_obs=True)
    assert isinstance(tree, AST)
    cmd = tree.body.args[0].elts
    assert len(cmd) == 3
    assert cmd[2].s == "x"


@pytest.mark.parametrize("opener, closer", SUBPROC_MACRO_OC)
@pytest.mark.parametrize(
    "body",
    [
        "echo!x + y",
        "echo !x + y",
        "echo !x + y",
        "echo ! x + y",
        "timeit! bang! and more",
        "timeit! recurse() and more",
        "timeit! recurse[] and more",
        "timeit! recurse!() and more",
        "timeit! recurse![] and more",
        "timeit! recurse$() and more",
        "timeit! recurse$[] and more",
        "timeit! recurse!() and more",
        "timeit!!!!",
        "timeit! (!)",
        "timeit! [!]",
        "timeit!!(ls)",
        'timeit!"!)"',
    ],
)
@pytest.mark.xfail
def test_many_subprocbang(opener, closer, body, check_xonsh_ast):
    tree = check_xonsh_ast(opener + body + closer, False, return_obs=True)
    assert isinstance(tree, AST)
    cmd = tree.body.args[0].elts
    assert len(cmd) == 2
    assert cmd[1].s == body.partition("!")[-1].strip()
