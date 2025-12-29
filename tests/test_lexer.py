"""Tests the xonsh lexer."""

import difflib
from collections.abc import Sequence

import pytest
from winnow_parser import Token as t
from winnow_parser import TokInfo as TokenInfo


def ensure_tuple(seq) -> str:
    if isinstance(seq, TokenInfo):
        seq = (seq.type, seq.string, seq.start[1])
    if isinstance(seq, Sequence):
        typ, *rest = seq
        seq = (getattr(t, typ) if isinstance(typ, str) else typ, *rest)
    return repr(tuple(seq))


def assert_tokens_equal(expected, obtained):
    """Asserts that two token sequences are equal."""
    left = [ensure_tuple(item) for item in expected]
    right = [ensure_tuple(item) for item in obtained]
    if diff := "\n".join(difflib.unified_diff(left, right, "expected", "obtained")):
        print("\n".join(difflib.ndiff(left, right)))
    return not diff


def lex_input(inp: str) -> list[TokenInfo]:
    # skip the NEWLINE, ENDMARKER tokens for easier testing
    from winnow_parser import tokenize

    tokens = tokenize(inp)
    if tokens[-1].type == t.ENDMARKER:
        tokens.pop()
    if tokens[-1].type == t.NEWLINE:
        tokens.pop()
    return tokens


def check_tokens(inp: str, *exp):
    obs = lex_input(inp)
    return assert_tokens_equal(exp, obs)


def check_tokens_subproc(inp, exp, stop=-1):
    obs = lex_input(f"$[{inp}]")[1:stop]
    return assert_tokens_equal(exp, obs)


@pytest.mark.parametrize(
    "inp, exp",
    [
        ["42", [t.NUMBER, "42", 0]],
        ["42.0", [t.NUMBER, "42.0", 0]],
        ["0x42", [t.NUMBER, "0x42", 0]],
        ["0x4_2", [t.NUMBER, "0x4_2", 0]],
        ["0o42", [t.NUMBER, "0o42", 0]],
        ["0o4_2", [t.NUMBER, "0o4_2", 0]],
        ["0b101010", [t.NUMBER, "0b101010", 0]],
        ["0b10_10_10", [t.NUMBER, "0b10_10_10", 0]],
    ],
)
def test_literals(inp, exp):
    assert check_tokens(inp, exp)


def test_indent():
    exp = [("INDENT", "  \t  ", 0), ("NUMBER", "42", 5), ("NEWLINE", "", 7), ("DEDENT", "", 0)]
    assert check_tokens("  \t  42", *exp)


def test_post_whitespace():
    inp = "42  \t  "
    exp = ("NUMBER", "42", 0)
    assert check_tokens(inp, exp)


def test_internal_whitespace():
    inp = "42  +\t65"
    exp = [("NUMBER", "42", 0), ("OP", "+", 4), ("NUMBER", "65", 6)]
    assert check_tokens(inp, *exp)


def test_indent_internal_whitespace():
    inp = " 42  +\t65"
    exp = [
        ("INDENT", " ", 0),
        ("NUMBER", "42", 1),
        ("OP", "+", 5),
        ("NUMBER", "65", 7),
        ("NEWLINE", "", 9),
        ("DEDENT", "", 0),
    ]
    assert check_tokens(inp, *exp)


def test_assignment():
    inp = "x = 42"
    exp = [("NAME", "x", 0), ("OP", "=", 2), ("NUMBER", "42", 4)]
    assert check_tokens(inp, *exp)


def test_multiline():
    inp = "x\ny"
    exp = [("NAME", "x", 0), ("NEWLINE", "\n", 1), ("NAME", "y", 0)]
    assert check_tokens(inp, *exp)


@pytest.mark.parametrize(
    "inp,exp",
    [
        ("$ENV", [[t.OP, "$", 0], [t.NAME, "ENV", 1]]),
        ("$ENV = 'val'", [[t.OP, "$", 0], [t.NAME, "ENV", 1], [t.OP, "=", 5], [t.STRING, "'val'", 7]]),
    ],
)
def test_dollar_names(inp, exp):
    assert check_tokens(inp, *exp)


def test_atdollar_expression():
    inp = "@$(which python)"
    exp = [
        (t.OP, "@$(", 0),
        ("NAME", "which", 3),
        ("NAME", "python", 9),
        ("OP", ")", 15),
    ]
    assert check_tokens(inp, *exp)


def test_and():
    # no preceding whitespace or other tokens, so this
    # resolves to NAME, since it doesn't make sense for
    # Python code to start with "and"
    assert check_tokens("and", ["NAME", "and", 0])


def test_ampersand():
    assert check_tokens("&", [t.OP, "&", 0])


def test_not_really_and_pre():
    inp = "![foo-and]"
    exp = [
        ("OP", "![", 0),
        ("NAME", "foo", 2),
        ("OP", "-", 5),
        ("NAME", "and", 6),
        ("OP", "]", 9),
    ]
    assert check_tokens(inp, *exp)


def test_not_really_and_post():
    inp = "![and-bar]"
    exp = [
        ("OP", "![", 0),
        ("NAME", "and", 2),
        ("OP", "-", 5),
        ("NAME", "bar", 6),
        ("OP", "]", 9),
    ]
    assert check_tokens(inp, *exp)


def test_not_really_and_pre_post():
    inp = "![foo-and-bar]"
    exp = [
        ("OP", "![", 0),
        ("NAME", "foo", 2),
        (t.OP, "-", 5),
        ("NAME", "and", 6),
        (t.OP, "-", 9),
        ("NAME", "bar", 10),
        ("OP", "]", 13),
    ]
    assert check_tokens(inp, *exp)


def test_not_really_or_pre():
    inp = "![foo-or]"
    exp = [
        ("OP", "![", 0),
        ("NAME", "foo", 2),
        (t.OP, "-", 5),
        ("NAME", "or", 6),
        ("OP", "]", 8),
    ]
    assert check_tokens(inp, *exp)


def test_not_really_or_post():
    inp = "![or-bar]"
    exp = [
        ("OP", "![", 0),
        ("NAME", "or", 2),
        (t.OP, "-", 4),
        ("NAME", "bar", 5),
        ("OP", "]", 8),
    ]
    assert check_tokens(inp, *exp)


def test_not_really_or_pre_post():
    inp = "![foo-or-bar]"
    exp = [
        ("OP", "![", 0),
        ("NAME", "foo", 2),
        (t.OP, "-", 5),
        ("NAME", "or", 6),
        (t.OP, "-", 8),
        ("NAME", "bar", 9),
        ("OP", "]", 12),
    ]
    assert check_tokens(inp, *exp)


def test_subproc_line_cont_space():
    inp = "![echo --option1 value1 \\\n     --option2 value2 \\\n     --optionZ valueZ]"
    exp = [
        ("OP", "![", 0),
        ("NAME", "echo", 2),
        (t.OP, "-", 7),
        (t.OP, "-", 8),
        ("NAME", "option1", 9),
        ("NAME", "value1", 17),
        (t.OP, "-", 5),
        (t.OP, "-", 6),
        ("NAME", "option2", 7),
        ("NAME", "value2", 15),
        (t.OP, "-", 5),
        (t.OP, "-", 6),
        ("NAME", "optionZ", 7),
        ("NAME", "valueZ", 15),
        ("OP", "]", 21),
    ]
    assert check_tokens(inp, *exp)


def test_subproc_line_cont_nospace():
    inp = "![echo --option1 value1\\\n     --option2 value2\\\n     --optionZ valueZ]"
    exp = [
        ("OP", "![", 0),
        ("NAME", "echo", 2),
        (t.OP, "-", 7),
        (t.OP, "-", 8),
        ("NAME", "option1", 9),
        ("NAME", "value1", 17),
        (t.OP, "-", 5),
        (t.OP, "-", 6),
        ("NAME", "option2", 7),
        ("NAME", "value2", 15),
        (t.OP, "-", 5),
        (t.OP, "-", 6),
        ("NAME", "optionZ", 7),
        ("NAME", "valueZ", 15),
        ("OP", "]", 21),
    ]
    assert check_tokens(inp, *exp)


def test_doubleamp():
    assert check_tokens("&&", ["OP", "&&", 0])


def test_pipe():
    assert check_tokens("|", [t.OP, "|", 0])


def test_doublepipe():
    assert check_tokens("||", ["OP", "||", 0])


def test_single_quote_literal():
    assert check_tokens("'yo'", ["STRING", "'yo'", 0])


def test_double_quote_literal():
    assert check_tokens('"yo"', ["STRING", '"yo"', 0])


def test_triple_single_quote_literal():
    assert check_tokens("'''yo'''", ["STRING", "'''yo'''", 0])


def test_triple_double_quote_literal():
    assert check_tokens('"""yo"""', ["STRING", '"""yo"""', 0])


def test_single_raw_string_literal():
    assert check_tokens("r'yo'", ["STRING", "r'yo'", 0])


def test_double_raw_string_literal():
    assert check_tokens('r"yo"', ["STRING", 'r"yo"', 0])


@pytest.mark.parametrize("quote", ["'", '"'])
def test_single_f_string_literal(quote):
    assert check_tokens(
        f"f{quote}{{yo}}{quote}",
        ("FSTRING_START", f"f{quote}", 0),
        ("OP", "{", 2),
        ("NAME", "yo", 3),
        ("OP", "}", 5),
        ("FSTRING_END", f"{quote}", 6),
    )


def test_single_unicode_literal():
    assert check_tokens("u'yo'", ["STRING", "u'yo'", 0])


def test_double_unicode_literal():
    assert check_tokens('u"yo"', ["STRING", 'u"yo"', 0])


def test_single_bytes_literal():
    assert check_tokens("b'yo'", ["STRING", "b'yo'", 0])


def test_path_string_literal():
    assert check_tokens("p'/foo'", ["STRING", "p'/foo'", 0])
    assert check_tokens('p"/foo"', ["STRING", 'p"/foo"', 0])
    assert check_tokens("pr'/foo'", ["STRING", "pr'/foo'", 0])
    assert check_tokens('pr"/foo"', ["STRING", 'pr"/foo"', 0])
    assert check_tokens("rp'/foo'", ["STRING", "rp'/foo'", 0])
    assert check_tokens('rp"/foo"', ["STRING", 'rp"/foo"', 0])


@pytest.mark.parametrize("quote", ["'", '"'])
@pytest.mark.parametrize("pre", ["pf", "fp", "pF", "Fp"])
def test_path_fstring_literal(pre, quote):
    assert check_tokens(
        f"{pre}{quote}/foo{quote}",
        ["FSTRING_START", f"{pre}{quote}", 0],
        ["FSTRING_MIDDLE", "/foo", 3],
        ["FSTRING_END", f"{quote}", 7],
    )


def test_regex_globs():
    for i in (".*", r"\d*", ".*#{1,2}"):
        for p in ("", "r", "g", "@somethingelse", "p", "pg"):
            c = f"{p}`{i}`"
            assert check_tokens(c, ["SEARCH_PATH", c, 0])


@pytest.mark.parametrize(
    "case",
    [
        "0.0",
        ".0",
        "0.",
        "1e10",
        "1.e42",
        "0.1e42",
        "0.5e-42",
        "5E10",
        "5e+42",
        "1_0e1_0",
    ],
)
def test_float_literals(case):
    assert check_tokens(case, ["NUMBER", case, 0])


@pytest.mark.parametrize("case", ["o>", "all>", "e>", "out>"])
def test_ioredir1(case):
    assert check_tokens_subproc(case, [("NAME", case[:-1], 2), (t.OP, case[-1], len(case) + 1)])


@pytest.mark.parametrize("case", ["2>1", "err>out", "e>o"])
def test_ioredir2(case):
    idx = case.find(">")
    assert check_tokens_subproc(
        case,
        [
            ("NUMBER" if case[:idx].isdigit() else t.NAME, case[:idx], 0 + 2),
            (t.OP, ">", idx + 2),
            ("NUMBER" if case[idx + 1].isdigit() else t.NAME, case[idx + 1 :], idx + 3),
        ],
    )


@pytest.mark.parametrize(
    "s, exp",
    [
        ("2>1", [("NUMBER", "2", 0), (t.OP, ">", 1), ("NUMBER", "1", 2)]),
        ("a>b", [("NAME", "a", 0), (t.OP, ">", 1), ("NAME", "b", 2)]),
        (
            "3>2>1",
            [
                ("NUMBER", "3", 0),
                (t.OP, ">", 1),
                ("NUMBER", "2", 2),
                (t.OP, ">", 3),
                ("NUMBER", "1", 4),
            ],
        ),
        (
            "36+2>>3",
            [
                ("NUMBER", "36", 0),
                (t.OP, "+", 2),
                ("NUMBER", "2", 3),
                (t.OP, ">>", 4),
                ("NUMBER", "3", 6),
            ],
        ),
        ("2>&1", [("NUMBER", "2", 0), ("OP", ">&", 1), ("NUMBER", "1", 3)]),
    ],
)
def test_pymode_not_ioredirect(s, exp):
    # test that Python code like `2>1` is lexed correctly
    # as opposed to being recognized as an IOREDIRECT token (issue #4994)
    assert check_tokens(s, *exp)


def test_fstring_nested_py312():
    assert check_tokens(
        "f'{a+b:.3f} more words {c+d=} final words'",
        ("FSTRING_START", "f'", 0),
        ("OP", "{", 2),
        ("NAME", "a", 3),
        ("OP", "+", 4),
        ("NAME", "b", 5),
        ("OP", ":", 6),
        ("FSTRING_MIDDLE", ".3f", 7),
        ("OP", "}", 10),
        ("FSTRING_MIDDLE", " more words ", 11),
        ("OP", "{", 23),
        ("NAME", "c", 24),
        ("OP", "+", 25),
        ("NAME", "d", 26),
        ("OP", "=", 27),
        ("OP", "}", 28),
        ("FSTRING_MIDDLE", " final words", 29),
        ("FSTRING_END", "'", 41),
    )


def test_fstring_triple():
    inp = """\
a = 10
f'''
  {a
     *
       x()}
non-important content
'''
"""

    assert check_tokens(
        inp,
        (t.NAME, "a", 0),
        (t.OP, "=", 2),
        (t.NUMBER, "10", 4),
        (t.NEWLINE, "\n", 6),
        (t.FSTRING_START, "f'''", 0),
        (t.FSTRING_MIDDLE, "\n  ", 4),
        (t.OP, "{", 2),
        (t.NAME, "a", 3),
        (t.OP, "*", 5),
        (t.NAME, "x", 7),
        (t.OP, "(", 8),
        (t.OP, ")", 9),
        (t.OP, "}", 10),
        ("FSTRING_MIDDLE", "\nnon-important content\n", 11),
        (t.FSTRING_END, "'''", 0),
    )
