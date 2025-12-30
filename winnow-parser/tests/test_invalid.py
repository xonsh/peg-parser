import itertools

import pytest


@pytest.mark.parametrize(
    "inp",
    [
        "del",
        "del 7",
        "del True",
        "del foo()",
        "del lambda x: 'yay'",
        "del x if y else z",
        "del x + y",
        "del x and y",
        "del -x",
    ],
)
def test_syntax_error_del(inp, python_parse_str):
    with pytest.raises(SyntaxError):
        python_parse_str(inp, mode="exec")


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
def test_syntax_error_del_inp(python_parse_str, exp):
    with pytest.raises(SyntaxError):
        python_parse_str(f"del {exp}", mode="exec")


def test_syntax_error_assign_literal(python_parse_str):
    with pytest.raises(SyntaxError):
        python_parse_str("7 = x", mode="exec")


def test_syntax_error_assign_constant(python_parse_str):
    with pytest.raises(SyntaxError):
        python_parse_str("True = 8", mode="exec")


def test_syntax_error_assign_call(python_parse_str):
    with pytest.raises(SyntaxError):
        python_parse_str("foo() = x", mode="exec")


def test_syntax_error_assign_lambda(python_parse_str):
    with pytest.raises(SyntaxError):
        python_parse_str('lambda x: "yay" = y', mode="exec")


def test_syntax_error_assign_ifexp(python_parse_str):
    with pytest.raises(SyntaxError):
        python_parse_str("x if y else z = 8", mode="exec")


@pytest.mark.parametrize(
    "exp",
    [
        "[i for i in foo]",
        "{i for i in foo}",
        "(i for i in foo)",
        "{k:v for k,v in d.items()}",
    ],
)
def test_syntax_error_assign_comps(python_parse_str, exp):
    with pytest.raises(SyntaxError):
        python_parse_str(f"{exp} = z", mode="exec")


@pytest.mark.parametrize("exp", ["x + y", "x and y", "-x"])
def test_syntax_error_assign_ops(python_parse_str, exp):
    with pytest.raises(SyntaxError):
        python_parse_str(f"{exp} = z", mode="exec")


@pytest.mark.parametrize("exp", ["x > y", "x > y == z"])
def test_syntax_error_assign_cmp(python_parse_str, exp):
    with pytest.raises(SyntaxError):
        python_parse_str(f"{exp} = a", mode="exec")


def test_syntax_error_augassign_literal(python_parse_str):
    with pytest.raises(SyntaxError):
        python_parse_str("7 += x", mode="exec")


def test_syntax_error_augassign_constant(python_parse_str):
    with pytest.raises(SyntaxError):
        python_parse_str("True += 8", mode="exec")


def test_syntax_error_augassign_emptytuple(python_parse_str):
    with pytest.raises(SyntaxError):
        python_parse_str("() += x", mode="exec")


def test_syntax_error_augassign_call(python_parse_str):
    with pytest.raises(SyntaxError):
        python_parse_str("foo() += x", mode="exec")


def test_syntax_error_augassign_lambda(python_parse_str):
    with pytest.raises(SyntaxError):
        python_parse_str('lambda x: "yay" += y', mode="exec")


def test_syntax_error_augassign_ifexp(python_parse_str):
    with pytest.raises(SyntaxError):
        python_parse_str("x if y else z += 8", mode="exec")


@pytest.mark.parametrize(
    "exp",
    [
        "[i for i in foo]",
        "{i for i in foo}",
        "(i for i in foo)",
        "{k:v for k,v in d.items()}",
    ],
)
def test_syntax_error_augassign_comps(python_parse_str, exp):
    with pytest.raises(SyntaxError):
        python_parse_str(f"{exp} += z", mode="exec")


@pytest.mark.parametrize("exp", ["x + y", "x and y", "-x"])
def test_syntax_error_augassign_ops(python_parse_str, exp):
    with pytest.raises(SyntaxError):
        python_parse_str(f"{exp} += z", mode="exec")


@pytest.mark.parametrize("exp", ["x > y", "x > y +=+= z"])
def test_syntax_error_augassign_cmp(python_parse_str, exp):
    with pytest.raises(SyntaxError):
        python_parse_str(f"{exp} += a", mode="exec")


def test_syntax_error_bar_kwonlyargs(python_parse_str):
    with pytest.raises(SyntaxError):
        python_parse_str("def spam(*):\n   pass\n", mode="exec")


def test_syntax_error_nondefault_follows_default(python_parse_str):
    with pytest.raises(SyntaxError):
        python_parse_str("def spam(x=1, y):\n   pass\n", mode="exec")


def test_syntax_error_lambda_nondefault_follows_default(python_parse_str):
    with pytest.raises(SyntaxError):
        python_parse_str("lambda x=1, y: x", mode="exec")


@pytest.mark.parametrize(
    ("first_prefix", "second_prefix"),
    itertools.permutations(
        [
            # "",
            "p",
            "b",
        ],
        2,
    ),
)
def test_syntax_error_literal_concat_different(first_prefix, second_prefix, python_parse_str):
    with pytest.raises((SyntaxError, TypeError)):
        python_parse_str(f"{first_prefix}'hello' {second_prefix}'world'", mode="exec")
