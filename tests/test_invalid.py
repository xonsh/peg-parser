import itertools

import pytest

# test invalid expressions


@pytest.mark.parametrize(
    "inp",
    [
        "del 7",
        "del True",
        "del ()",
        "del foo()",
        "del lambda x: 'yay'",
        "del x if y else z",
        "del x + y",
        "del x and y",
        "del -x",
    ],
)
@pytest.mark.xfail
def test_syntax_error_del(inp, parse_str):
    with pytest.raises(SyntaxError):
        parse_str(inp)


@pytest.mark.parametrize(
    "exp",
    [
        "[i for i in foo]",
        "{i for i in foo}",
        "(i for i in foo)",
        "{k:v for k,v in d.items()}",
        "x > y",
        "x > y == z",
    ],
)
@pytest.mark.xfail
def test_syntax_error_del_inp(parse_str, exp):
    with pytest.raises(SyntaxError):
        parse_str(f"del {exp}")


@pytest.mark.xfail
def test_syntax_error_lonely_del(parse_str):
    with pytest.raises(SyntaxError):
        parse_str("del")


@pytest.mark.xfail
def test_syntax_error_assign_literal(parse_str):
    with pytest.raises(SyntaxError):
        parse_str("7 = x")


@pytest.mark.xfail
def test_syntax_error_assign_constant(parse_str):
    with pytest.raises(SyntaxError):
        parse_str("True = 8")


@pytest.mark.xfail
def test_syntax_error_assign_emptytuple(parse_str):
    with pytest.raises(SyntaxError):
        parse_str("() = x")


@pytest.mark.xfail
def test_syntax_error_assign_call(parse_str):
    with pytest.raises(SyntaxError):
        parse_str("foo() = x")


@pytest.mark.xfail
def test_syntax_error_assign_lambda(parse_str):
    with pytest.raises(SyntaxError):
        parse_str('lambda x: "yay" = y')


@pytest.mark.xfail
def test_syntax_error_assign_ifexp(parse_str):
    with pytest.raises(SyntaxError):
        parse_str("x if y else z = 8")


@pytest.mark.parametrize(
    "exp",
    [
        "[i for i in foo]",
        "{i for i in foo}",
        "(i for i in foo)",
        "{k:v for k,v in d.items()}",
    ],
)
@pytest.mark.xfail
def test_syntax_error_assign_comps(parse_str, exp):
    with pytest.raises(SyntaxError):
        parse_str(f"{exp} = z")


@pytest.mark.parametrize("exp", ["x + y", "x and y", "-x"])
@pytest.mark.xfail
def test_syntax_error_assign_ops(parse_str, exp):
    with pytest.raises(SyntaxError):
        parse_str(f"{exp} = z")


@pytest.mark.parametrize("exp", ["x > y", "x > y == z"])
def test_syntax_error_assign_cmp(parse_str, exp):
    with pytest.raises(SyntaxError):
        parse_str(f"{exp} = a")


def test_syntax_error_augassign_literal(parse_str):
    with pytest.raises(SyntaxError):
        parse_str("7 += x")


def test_syntax_error_augassign_constant(parse_str):
    with pytest.raises(SyntaxError):
        parse_str("True += 8")


def test_syntax_error_augassign_emptytuple(parse_str):
    with pytest.raises(SyntaxError):
        parse_str("() += x")


def test_syntax_error_augassign_call(parse_str):
    with pytest.raises(SyntaxError):
        parse_str("foo() += x")


def test_syntax_error_augassign_lambda(parse_str):
    with pytest.raises(SyntaxError):
        parse_str('lambda x: "yay" += y')


def test_syntax_error_augassign_ifexp(parse_str):
    with pytest.raises(SyntaxError):
        parse_str("x if y else z += 8")


@pytest.mark.parametrize(
    "exp",
    [
        "[i for i in foo]",
        "{i for i in foo}",
        "(i for i in foo)",
        "{k:v for k,v in d.items()}",
    ],
)
def test_syntax_error_augassign_comps(parse_str, exp):
    with pytest.raises(SyntaxError):
        parse_str(f"{exp} += z")


@pytest.mark.parametrize("exp", ["x + y", "x and y", "-x"])
def test_syntax_error_augassign_ops(parse_str, exp):
    with pytest.raises(SyntaxError):
        parse_str(f"{exp} += z")


@pytest.mark.parametrize("exp", ["x > y", "x > y +=+= z"])
def test_syntax_error_augassign_cmp(parse_str, exp):
    with pytest.raises(SyntaxError):
        parse_str(f"{exp} += a")


def test_syntax_error_bar_kwonlyargs(parse_str):
    with pytest.raises(SyntaxError):
        parse_str("def spam(*):\n   pass\n", mode="exec")


def test_syntax_error_nondefault_follows_default(parse_str):
    with pytest.raises(SyntaxError):
        parse_str("def spam(x=1, y):\n   pass\n", mode="exec")


def test_syntax_error_lambda_nondefault_follows_default(parse_str):
    with pytest.raises(SyntaxError):
        parse_str("lambda x=1, y: x", mode="exec")


@pytest.mark.parametrize("first_prefix, second_prefix", itertools.permutations(["", "p", "b"], 2))
@pytest.mark.xfail
def test_syntax_error_literal_concat_different(first_prefix, second_prefix, parse_str):
    with pytest.raises(SyntaxError):
        parse_str(f"{first_prefix}'hello' {second_prefix}'world'")


@pytest.mark.xfail
def test_bad_quotes(check_xonsh_ast):
    with pytest.raises(SyntaxError):
        check_xonsh_ast('![echo """hello]')
