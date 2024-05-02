"""Tests the xonsh lexer."""

import difflib
import io
from collections.abc import Sequence

import pytest

import peg_parser.parser.token as t
from peg_parser.parser import token, tokenize
from peg_parser.parser.tokenize import TokenInfo


def ensure_tuple(seq) -> str:
    if isinstance(seq, TokenInfo):
        seq = (seq.type, seq.string, seq.start[1])
    if isinstance(seq, Sequence):
        seq = (getattr(token, seq[0]) if isinstance(seq[0], str) else seq[0], *seq[1:])
    return repr(tuple(seq))


def assert_tokens_equal(x, y):
    """Asserts that two token sequences are equal."""
    left = [ensure_tuple(item) for item in x]
    right = [ensure_tuple(item) for item in y]
    diff = "\n".join(difflib.unified_diff(left, right, "parsed", "expected"))
    assert not diff
    return True


def lex_input(inp: str) -> list[TokenInfo]:
    # skip the NEWLINE, ENDMARKER tokens for easier testing

    tokens = list(tokenize.generate_tokens(io.StringIO(inp).readline))
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
        ("$ENV", [[t.ENVNAME, "$ENV", 0]]),
        ("$ENV = 'val'", [[t.ENVNAME, "$ENV", 0], [t.OP, "=", 5], [t.STRING, "'val'", 7]]),
    ],
)
def test_dollar_names(inp, exp):
    assert check_tokens(inp, *exp)


def test_atdollar_expression():
    inp = "@$(which python)"
    exp = [
        ("OP", "@$(", 0),
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


@pytest.mark.xfail
def test_ampersand():
    assert check_tokens("&", ["AMPERSAND", "&", 0])


@pytest.mark.xfail
def test_not_really_and_pre():
    inp = "![foo-and]"
    exp = [
        ("BANG_LBRACKET", "![", 0),
        ("NAME", "foo", 2),
        ("MINUS", "-", 5),
        ("NAME", "and", 6),
        ("RBRACKET", "]", 9),
    ]
    assert check_tokens(inp, *exp)


@pytest.mark.xfail
def test_not_really_and_post():
    inp = "![and-bar]"
    exp = [
        ("BANG_LBRACKET", "![", 0),
        ("NAME", "and", 2),
        ("MINUS", "-", 5),
        ("NAME", "bar", 6),
        ("RBRACKET", "]", 9),
    ]
    assert check_tokens(inp, *exp)


@pytest.mark.xfail
def test_not_really_and_pre_post():
    inp = "![foo-and-bar]"
    exp = [
        ("BANG_LBRACKET", "![", 0),
        ("NAME", "foo", 2),
        ("MINUS", "-", 5),
        ("NAME", "and", 6),
        ("MINUS", "-", 9),
        ("NAME", "bar", 10),
        ("RBRACKET", "]", 13),
    ]
    assert check_tokens(inp, *exp)


@pytest.mark.xfail
def test_not_really_or_pre():
    inp = "![foo-or]"
    exp = [
        ("BANG_LBRACKET", "![", 0),
        ("NAME", "foo", 2),
        ("MINUS", "-", 5),
        ("NAME", "or", 6),
        ("RBRACKET", "]", 8),
    ]
    assert check_tokens(inp, *exp)


@pytest.mark.xfail
def test_not_really_or_post():
    inp = "![or-bar]"
    exp = [
        ("BANG_LBRACKET", "![", 0),
        ("NAME", "or", 2),
        ("MINUS", "-", 4),
        ("NAME", "bar", 5),
        ("RBRACKET", "]", 8),
    ]
    assert check_tokens(inp, *exp)


@pytest.mark.xfail
def test_not_really_or_pre_post():
    inp = "![foo-or-bar]"
    exp = [
        ("BANG_LBRACKET", "![", 0),
        ("NAME", "foo", 2),
        ("MINUS", "-", 5),
        ("NAME", "or", 6),
        ("MINUS", "-", 8),
        ("NAME", "bar", 9),
        ("RBRACKET", "]", 12),
    ]
    assert check_tokens(inp, *exp)


@pytest.mark.xfail
def test_subproc_line_cont_space():
    inp = "![echo --option1 value1 \\\n" "     --option2 value2 \\\n" "     --optionZ valueZ]"
    exp = [
        ("BANG_LBRACKET", "![", 0),
        ("NAME", "echo", 2),
        ("WS", " ", 6),
        ("MINUS", "-", 7),
        ("MINUS", "-", 8),
        ("NAME", "option1", 9),
        ("WS", " ", 16),
        ("NAME", "value1", 17),
        ("WS", " ", 23),
        ("MINUS", "-", 5),
        ("MINUS", "-", 6),
        ("NAME", "option2", 7),
        ("WS", " ", 14),
        ("NAME", "value2", 15),
        ("WS", " ", 21),
        ("MINUS", "-", 5),
        ("MINUS", "-", 6),
        ("NAME", "optionZ", 7),
        ("WS", " ", 14),
        ("NAME", "valueZ", 15),
        ("RBRACKET", "]", 21),
    ]
    assert check_tokens(inp, *exp)


@pytest.mark.xfail
def test_subproc_line_cont_nospace():
    inp = "![echo --option1 value1\\\n" "     --option2 value2\\\n" "     --optionZ valueZ]"
    exp = [
        ("BANG_LBRACKET", "![", 0),
        ("NAME", "echo", 2),
        ("WS", " ", 6),
        ("MINUS", "-", 7),
        ("MINUS", "-", 8),
        ("NAME", "option1", 9),
        ("WS", " ", 16),
        ("NAME", "value1", 17),
        ("WS", "\\", 23),
        ("MINUS", "-", 5),
        ("MINUS", "-", 6),
        ("NAME", "option2", 7),
        ("WS", " ", 14),
        ("NAME", "value2", 15),
        ("WS", "\\", 21),
        ("MINUS", "-", 5),
        ("MINUS", "-", 6),
        ("NAME", "optionZ", 7),
        ("WS", " ", 14),
        ("NAME", "valueZ", 15),
        ("RBRACKET", "]", 21),
    ]
    assert check_tokens(inp, *exp)


@pytest.mark.xfail
def test_atdollar():
    assert check_tokens("@$", ["ATDOLLAR", "@$", 0])


@pytest.mark.xfail
def test_doubleamp():
    assert check_tokens("&&", ["AND", "and", 0])


@pytest.mark.xfail
def test_pipe():
    assert check_tokens("|", ["PIPE", "|", 0])


@pytest.mark.xfail
def test_doublepipe():
    assert check_tokens("||", ["OR", "or", 0])


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


def test_single_f_string_literal():
    assert check_tokens("f'{yo}'", ["STRING", "f'{yo}'", 0])


def test_double_f_string_literal():
    assert check_tokens('f"{yo}"', ["STRING", 'f"{yo}"', 0])


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


def test_path_fstring_literal():
    assert check_tokens("pf'/foo'", ["STRING", "pf'/foo'", 0])
    assert check_tokens('pf"/foo"', ["STRING", 'pf"/foo"', 0])
    assert check_tokens("fp'/foo'", ["STRING", "fp'/foo'", 0])
    assert check_tokens('fp"/foo"', ["STRING", 'fp"/foo"', 0])
    assert check_tokens("pF'/foo'", ["STRING", "pF'/foo'", 0])
    assert check_tokens('pF"/foo"', ["STRING", 'pF"/foo"', 0])
    assert check_tokens("Fp'/foo'", ["STRING", "Fp'/foo'", 0])
    assert check_tokens('Fp"/foo"', ["STRING", 'Fp"/foo"', 0])


@pytest.mark.xfail
def test_regex_globs():
    for i in (".*", r"\d*", ".*#{1,2}"):
        for p in ("", "r", "g", "@somethingelse", "p", "pg"):
            c = f"{p}`{i}`"
            assert check_tokens(c, ["SEARCHPATH", c, 0])


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


@pytest.mark.xfail
@pytest.mark.parametrize("case", ["o>", "all>", "e>", "out>"])
def test_ioredir1(case):
    assert check_tokens_subproc(case, [("IOREDIRECT1", case, 2)], stop=-2)


@pytest.mark.xfail
@pytest.mark.parametrize("case", ["2>1", "err>out", "e>o", "2>&1"])
def test_ioredir2(case):
    assert check_tokens_subproc(case, [("IOREDIRECT2", case, 2)], stop=-2)


@pytest.mark.xfail
@pytest.mark.parametrize("case", [">", ">>", "<", "e>", "> ", ">>   ", "<  ", "e> "])
def test_redir_whitespace(case):
    inp = f"![{case}/path/to/file]"
    obs = lex_input(inp)
    assert obs[2].type == "WS"


@pytest.mark.xfail
@pytest.mark.parametrize(
    "s, exp",
    [
        ("", []),
        ("   \t   \n \t  ", []),
        ("echo hello", ["echo", "hello"]),
        ('echo "hello"', ["echo", '"hello"']),
        ('![echo "hello"]', ["![echo", '"hello"]']),
        ("/usr/bin/echo hello", ["/usr/bin/echo", "hello"]),
        ("$(/usr/bin/echo hello)", ["$(/usr/bin/echo", "hello)"]),
        ("C:\\Python\\python.exe -m xonsh", ["C:\\Python\\python.exe", "-m", "xonsh"]),
        ('print("""I am a triple string""")', ['print("""I am a triple string""")']),
        (
            'print("""I am a \ntriple string""")',
            ['print("""I am a \ntriple string""")'],
        ),
        ("echo $HOME", ["echo", "$HOME"]),
        ("echo -n $HOME", ["echo", "-n", "$HOME"]),
        ("echo --go=away", ["echo", "--go=away"]),
        ("echo --go=$HOME", ["echo", "--go=$HOME"]),
    ],
)
def test_lexer_split(s, exp):
    lexer = tokenize.generate_tokens(s)
    obs = lexer.split(s)
    assert exp == obs


@pytest.mark.xfail
@pytest.mark.parametrize(
    "s",
    (
        "()",  # sanity
        "(",
        ")",
        "))",
        "'string\nliteral",
        "'''string\nliteral",
        "string\nliteral'",
        '"',
        "'",
        '"""',
    ),
)
def test_tolerant_lexer(s):
    lexer = tokenize.generate_tokens(s)
    error_tokens = list(tok for tok in lexer if tok.type == "ERRORTOKEN")
    assert all(tok.value in s for tok in error_tokens)  # no error messages


@pytest.mark.xfail
@pytest.mark.parametrize(
    "s, exp",
    [
        ("2>1", [("NUMBER", "2", 0), ("GT", ">", 1), ("NUMBER", "1", 2)]),
        ("a>b", [("NAME", "a", 0), ("GT", ">", 1), ("NAME", "b", 2)]),
        (
            "3>2>1",
            [
                ("NUMBER", "3", 0),
                ("GT", ">", 1),
                ("NUMBER", "2", 2),
                ("GT", ">", 3),
                ("NUMBER", "1", 4),
            ],
        ),
        (
            "36+2>>3",
            [
                ("NUMBER", "36", 0),
                ("PLUS", "+", 2),
                ("NUMBER", "2", 3),
                ("RSHIFT", ">>", 4),
                ("NUMBER", "3", 6),
            ],
        ),
    ],
)
def test_pymode_not_ioredirect(s, exp):
    # test that Python code like `2>1` is lexed correctly
    # as opposed to being recognized as an IOREDIRECT token (issue #4994)
    assert check_tokens(s, *exp)


@pytest.mark.xfail
def test_fstring_nested_py312():
    raise AssertionError(
        "fstring nested py312 https://github.com/psf/black/blob/main/src/blib2to3/pgen2/tokenize.py#L288"
    )
