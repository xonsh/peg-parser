import sys

import pytest

pytest.mark.skipif(sys.version_info < (3, 8), reason="requires python3.8 or higher")


def test_yield_x_starexpr(check_stmts):
    check_stmts("yield x, *[y, z]", False)


def test_return_x_starexpr(check_stmts):
    check_stmts("return x, *[y, z]", False)


def test_lambda_x_divide_y_star_z_kwargs(check_ast):
    check_ast("lambda x, /, y, *, z, **kwargs: 42")


def test_named_expr(check_ast):
    check_ast("(x := 42)")


def test_named_expr_list(check_ast):
    check_ast("[x := 42, x + 1, x + 2]")


def test_named_expr_if(check_stmts):
    check_stmts("if (x := 42) > 0:\n  x += 1")


def test_named_expr_elif(check_stmts):
    check_stmts("if False:\n  pass\nelif x := 42:\n  x += 1")


def test_named_expr_while(check_stmts):
    check_stmts("y = 42\nwhile (x := y) < 43:\n  y += 1")


def test_func_x_divide(check_stmts):
    check_stmts("def f(x, /):\n  return 42")


def test_func_x_divide_y_star_z_kwargs(check_stmts):
    check_stmts("def f(x, /, y, *, z, **kwargs):\n  return 42")


def test_named_expr_args(check_stmts):
    check_stmts("id(x := 42)")


def test_syntax_error_bar_posonlyargs(parser):
    with pytest.raises(SyntaxError):
        parser.parse("def spam(/):\n   pass\n", mode="exec")


def test_syntax_error_bar_posonlyargs_no_comma(parser):
    with pytest.raises(SyntaxError):
        parser.parse("def spam(x /, y):\n   pass\n", mode="exec")


def test_syntax_error_posonly_nondefault_follows_default(parser):
    with pytest.raises(SyntaxError):
        parser.parse("def spam(x, y=1, /, z):\n   pass\n", mode="exec")


def test_syntax_error_lambda_posonly_nondefault_follows_default(parser):
    with pytest.raises(SyntaxError):
        parser.parse("lambda x, y=1, /, z: x", mode="exec")
