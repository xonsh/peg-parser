from ast import AST

import pytest

SUBPROC_MACRO_OC = [("!(", ")"), ("$(", ")"), ("![", "]"), ("$[", "]")]


@pytest.mark.parametrize("opener, closer", SUBPROC_MACRO_OC)
@pytest.mark.parametrize(
    "body, args",
    [
        ("echo!", [""]),
        ("echo !", [""]),
        ("echo ! ", [""]),
        ("echo!x", ["x"]),
        ("echo !x", ["x"]),
        ("echo ! x", ["x"]),
        ("echo ! x ", ["x"]),
        ("echo -n!x", ["-n", "x"]),
        ("echo -n !x", ["-n", "x"]),
        ("echo -n ! x", ["-n", "x"]),
        ("echo -n ! x ", ["-n", "x"]),
    ],
)
def test_empty_subprocbang(opener, closer, body, args, check_xonsh_ast, xsh_proc_method):
    tree = check_xonsh_ast(opener + body + closer)
    assert isinstance(tree, AST)
    method = xsh_proc_method(opener)
    method.assert_called_once_with("echo", *args)


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
def test_many_subprocbang(opener, closer, body, check_xonsh_ast, xsh_proc_method):
    tree = check_xonsh_ast(opener + body + closer)
    assert isinstance(tree, AST)
    method = xsh_proc_method(opener)
    cmd, arg = body.split("!", 1)
    method.assert_called_once_with(cmd.strip(), arg.strip())
