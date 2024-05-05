"""Tests the xonsh parser."""

import ast
from ast import AST, Call
from pathlib import Path

import pytest

#
# Tests
#


@pytest.mark.xfail
@pytest.mark.parametrize(
    "inp",
    [
        'f"{$HOME}"',
        "f'{$XONSH_DEBUG}'",
        'F"{$PATH} and {$XONSH_DEBUG}"',
    ],
)
def test_f_env_var(inp, parse_str):
    parse_str(inp)


fstring_adaptor_parameters = [
    ('f"$HOME"', "$HOME"),
    ('f"{0} - {1}"', "0 - 1"),
    ('f"{$HOME}"', "/foo/bar"),
    ('f"{ $HOME }"', "/foo/bar"),
    ("f\"{'$HOME'}\"", "$HOME"),
    ('f"$HOME  = {$HOME}"', "$HOME  = /foo/bar"),
    ("f\"{${'HOME'}}\"", "/foo/bar"),
    ("f'{${$FOO+$BAR}}'", "/foo/bar"),
    ("f\"${$FOO}{$BAR}={f'{$HOME}'}\"", "$HOME=/foo/bar"),
    (
        '''f"""foo
{f"_{$HOME}_"}
bar"""''',
        "foo\n_/foo/bar_\nbar",
    ),
    (
        '''f"""foo
{f"_{${'HOME'}}_"}
bar"""''',
        "foo\n_/foo/bar_\nbar",
    ),
    (
        '''f"""foo
{f"_{${ $FOO + $BAR }}_"}
bar"""''',
        "foo\n_/foo/bar_\nbar",
    ),
    ("f'{$HOME=}'", "$HOME='/foo/bar'"),
]


@pytest.mark.parametrize("inp, exp", fstring_adaptor_parameters)
@pytest.mark.xfail
def test_fstring_adaptor(inp, xsh, exp, monkeypatch):
    joined_str_node = FStringAdaptor(inp, "f").run()  # noqa
    assert isinstance(joined_str_node, ast.JoinedStr)
    node = ast.Expression(body=joined_str_node)
    code = compile(node, "<test_fstring_adaptor>", mode="eval")
    xenv = {"HOME": "/foo/bar", "FOO": "HO", "BAR": "ME"}
    for key, val in xenv.items():
        monkeypatch.setitem(xsh.env, key, val)
    obs = eval(code)
    assert exp == obs


@pytest.mark.parametrize(
    "inp",
    [
        'br"hell\\o"',
        'RB"hell\\o"',
        'Br"hell\\o"',
        'rB"hell\\o"',
        "+1",
        "-1",
        "~1",
        "42 + 65",
        "42 - 65",
        "42 * 65",
        "42 / 65",
        "42 % 65",
        "42 // 65",
        "x @ y",
        "2 ** 2",
        "42 + 2 ** 2",
        "42 + 65 + 6",
        "42 + 65 - 6",
        "42 - 65 + 6",
        "42 - 65 - 6",
        "42 - 65 + 6 - 28",
        "42 * 65 + 6",
        "42 + 65 * 6",
        "42 * 65 * 6",
        "42 * 65 / 6",
        "42 * 65 / 6 % 28",
        "42 * 65 / 6 % 28 // 13",
        "\"hello\" 'mom'",
        '"hello" \'mom\'    "wow"',
        "\"hello\" + 'mom'",
        '"hello" * 20',
        '2*"hello"',
        "(42 + 65) * 20",
        "42 + (65 * 20)",
        "(42)",
        "42 < 65",
        "42 > 65",
        "42 == 65",
        "42 <= 65",
        "42 >= 65",
        "42 != 65",
        '"4" in "65"',
        "int is float",
        '"4" not in "65"',
        "float is not int",
        "42 < 65 < 105",
        "42 < 65 < 105 < 77",
        "not 0",
        "1 or 0",
        "1 or 0 or 42",
        "1 and 0",
        "1 and 0 and 2",
        "1 and 0 or 2",
        "1 or 0 and 2",
        "(1 and 0) and 2",
        "(1 and 0) or 2",
        "42 if True else 65",
        "42+5 if 1 == 2 else 65-5",
        '"hello"[0]',
        '"hello"[0:3]',
        '"hello"[0:3:1]',
        '"hello"[:]',
        '"hello"[5:]',
        '"hello"[:3]',
        '"hello"[::2]',
        '"hello"[:3:2]',
        '"hello"[3::2]',
        '"hello"[0:3,0:3]',
        '"hello"[0:3:1,0:4:2]',
    ],
)
def test_python_ast_matches(inp, check_ast):
    check_ast(inp)


def test_subscription_syntaxes(eval_code):
    assert eval_code("[1, 2, 3][-1]") == 3
    assert eval_code("[1, 2, 3][-1]") == 3
    assert eval_code("'string'[-1]") == "g"


def arr_container():
    # like numpy.r_
    class Arr:
        def __getitem__(self, item):
            return item

    return Arr()


def test_subscription_special_syntaxes(eval_code):
    assert eval_code("arr[1, 2, 3]", arr=arr_container()) == (1, 2, 3)
    # dataframe
    assert eval_code('arr[["a", "b"]]', arr=arr_container()) == ["a", "b"]


@pytest.mark.xfail
def test_subscription_special_syntaxes_2(eval_code):
    # aliases
    d = {}
    eval_code("d[arr.__name__] = True", arr=arr_container(), d=d)
    assert d == {"Arr": True}
    # extslice
    assert eval_code('arr[:, "2"]') == 2


def get_cases(path, splitter="# "):
    inp = ""
    parts = []
    for line in path.read_text().splitlines():
        if line.startswith(splitter):
            inp = line.lstrip(splitter)
        elif not line.strip():
            if parts:
                yield inp, "\n".join(parts)
                parts.clear()
        else:
            parts.append(line)
    if parts:
        yield inp, "\n".join(parts)


def glob_data_param(pattern: str):
    return [pytest.param(path, id=path.name) for path in Path(__file__).parent.joinpath("data").glob(pattern)]


@pytest.mark.parametrize("file", glob_data_param("exprs/*.py"))
def test_exprs(file, unparse_diff, subtests):
    for idx, (inp, exp) in enumerate(get_cases(file)):
        with subtests.test(idx=idx):
            unparse_diff(inp, exp)


@pytest.mark.parametrize(
    "file",
    glob_data_param("stmts/*.py"),
)
def test_stmts(file, unparse_diff, subtests):
    for idx, (inp, exp) in enumerate(get_cases(file)):
        with subtests.test(idx=idx):
            unparse_diff(inp, exp, mode="exec")


@pytest.mark.parametrize(
    "inp",
    [
        'x = "WAKKA"; ${x} = 65',
        'x = "."; $(ls @(None or x))',
        'x = "."; !(ls @(None or x))',
        '$[git commit -am "wakka jawaka" ]\n',
        '$[git commit -am "flock jawaka milwaka" ]\n',
        '$[git commit -am "wakka jawaka"]\n',
        '$[git commit -am "flock jawaka"]\n',
        '![git commit -am "wakka jawaka" ]\n',
        '![git commit -am "flock jawaka milwaka" ]\n',
        '![git commit -am "wakka jawaka"]\n',
        '![git commit -am "flock jawaka"]\n',
    ],
)
def test_statements(check_xonsh_ast, inp):
    if not inp.endswith("\n"):
        inp += "\n"
    check_xonsh_ast(inp, mode="exec")


@pytest.mark.parametrize(
    "inp, args",
    [
        ("$(ls)", ["ls"]),
        ("$(ls )", ["ls"]),
        ("$( ls )", ["ls"]),
        ("$( ls)", ["ls"]),
        ("$(ls .)", ["ls", "."]),
        ('$(ls ".")', ["ls", '"."']),
        ("$(ls -l)", ["ls", "-l"]),
        ("$(ls $WAKKA)", ["ls", "wak"]),
        ('$(ls @(None or "."))', ["ls", "."]),
        (
            '$(echo hello | @(lambda a, s=None: "hey!") foo bar baz)',
            ["echo", "hello", "|", "hey!", "foo", "bar", "baz"],
        ),
        (
            "$(echo @(i**2 for i in range(20) ) )",
            ["echo", 0, 1, 4, 9, 16, 25, 36, 49, 64, 81, 100, 121, 144, 169, 196, 225, 256, 289, 324, 361],
        ),
        ("$(echo @('a', 7))", ["echo", "a", 7]),
        pytest.param(
            "$(@$(which echo) ls | @(lambda a, s=None: $(@(s.strip()) @(a[1]))) foo -la baz)",
            "",
            marks=pytest.mark.xfail,
        ),
        ("$(ls $(ls))", ["ls", "ls"]),
        ("$(ls $(ls) -l)", ["ls", "ls", "-l"]),
        ("$[ls]", ["ls"]),
        ("![ls]", ["ls"]),
        ("![echo $WAKKA/place]", ["echo", "wak/place"]),
        ("![echo yo==yo]", ["echo", "yo==yo"]),
        ("!(ls | grep wakka)", ["ls", "|", "grep", "wakka"]),
        ("!(ls | grep wakka | grep jawaka)", ["ls", "|", "grep", "wakka", "|", "grep", "jawaka"]),
        ("!(ls > x.py)", ["ls", ">", "x.py"]),
    ],
)
def test_captured_procs(inp, args, check_xonsh_ast, xsh):
    check_xonsh_ast(inp, mode="exec", xenv={"WAKKA": "wak"})
    method_name = {
        "$[": "subproc_uncaptured",
        "$(": "subproc_captured",
        "![": "subproc_captured_hiddenobject",
        "!(": "subproc_captured_object",
    }[inp[:2]]
    method = getattr(xsh, method_name)
    method.assert_called_with(*args)


@pytest.mark.parametrize(
    "expr",
    [
        "!(ls)",
        "!(ls )",
        "!( ls)",
        "!( ls )",
        "!(ls .)",
        '!(ls @(None or "."))',
        '!(ls ".")',
        "!(ls $(ls))",
        "!(ls $(ls) -l)",
        "!(ls $WAKKA)",
        "!($LS .)",
        "$(ls `[Ff]+i*LE` -l)",
    ],
)
def test_bang_procs(expr, check_xonsh_ast):
    check_xonsh_ast(expr, xenv={"LS": "ll", "WAKKA": "wak"})


@pytest.mark.parametrize("p", ["", "p"])
@pytest.mark.parametrize("f", ["", "f"])
@pytest.mark.parametrize("glob_type", ["", "r", "g"])
@pytest.mark.xfail
def test_backtick(p, f, glob_type, check_xonsh_ast):
    check_xonsh_ast(f"print({p}{f}{glob_type}`.*`)", False)


@pytest.mark.xfail
def test_comment_only(check_xonsh_ast):
    check_xonsh_ast("# hello")


@pytest.mark.xfail
def test_redirect(check_xonsh_ast):
    assert check_xonsh_ast("$[cat < input.txt]", False)
    assert check_xonsh_ast("$[< input.txt cat]", False)


@pytest.mark.parametrize(
    "case",
    [
        "![(cat)]",
        "![(cat;)]",
        "![(cd path; ls; cd)]",
        '![(echo "abc"; sleep 1; echo "def")]',
        '![(echo "abc"; sleep 1; echo "def") | grep abc]',
        "![(if True:\n   ls\nelse:\n   echo not true)]",
    ],
)
@pytest.mark.xfail
def test_use_subshell(case, check_xonsh_ast):
    check_xonsh_ast(case)


@pytest.mark.parametrize(
    "case",
    [
        "$[cat < /path/to/input.txt]",
        "$[(cat) < /path/to/input.txt]",
        "$[< /path/to/input.txt cat]",
        "![< /path/to/input.txt]",
        "![< /path/to/input.txt > /path/to/output.txt]",
    ],
)
@pytest.mark.xfail
def test_redirect_abspath(case, check_xonsh_ast):
    assert check_xonsh_ast(case, False)


@pytest.mark.parametrize("case", ["", "o", "out", "1"])
@pytest.mark.xfail
def test_redirect_output(case, check_xonsh_ast):
    assert check_xonsh_ast(f'$[echo "test" {case}> test.txt]', False)
    assert check_xonsh_ast(f'$[< input.txt echo "test" {case}> test.txt]', False)
    assert check_xonsh_ast(f'$[echo "test" {case}> test.txt < input.txt]', False)


@pytest.mark.parametrize("case", ["e", "err", "2"])
def test_redirect_error(case, check_xonsh_ast):
    assert check_xonsh_ast(f'$[echo "test" {case}> test.txt]', False)
    assert check_xonsh_ast(f'$[< input.txt echo "test" {case}> test.txt]', False)
    assert check_xonsh_ast(f'$[echo "test" {case}> test.txt < input.txt]', False)


@pytest.mark.parametrize("case", ["a", "all", "&"])
@pytest.mark.xfail
def test_redirect_all(case, check_xonsh_ast):
    assert check_xonsh_ast(f'$[echo "test" {case}> test.txt]', False)
    assert check_xonsh_ast(f'$[< input.txt echo "test" {case}> test.txt]', False)
    assert check_xonsh_ast(f'$[echo "test" {case}> test.txt < input.txt]', False)


@pytest.mark.parametrize(
    "r",
    [
        "e>o",
        "e>out",
        "err>o",
        "2>1",
        "e>1",
        "err>1",
        "2>out",
        "2>o",
        "err>&1",
        "e>&1",
        "2>&1",
    ],
)
@pytest.mark.parametrize("o", ["", "o", "out", "1"])
def test_redirect_error_to_output(r, o, check_xonsh_ast):
    assert check_xonsh_ast(f'$[echo "test" {r} {o}> test.txt]', False)
    assert check_xonsh_ast(f'$[< input.txt echo "test" {r} {o}> test.txt]', False)
    assert check_xonsh_ast(f'$[echo "test" {r} {o}> test.txt < input.txt]', False)


@pytest.mark.parametrize(
    "r",
    [
        "o>e",
        "o>err",
        "out>e",
        "1>2",
        "o>2",
        "out>2",
        "1>err",
        "1>e",
        "out>&2",
        "o>&2",
        "1>&2",
    ],
)
@pytest.mark.parametrize("e", ["e", "err", "2"])
def test_redirect_output_to_error(r, e, check_xonsh_ast):
    assert check_xonsh_ast(f'$[echo "test" {r} {e}> test.txt]', False)
    assert check_xonsh_ast(f'$[< input.txt echo "test" {r} {e}> test.txt]', False)
    assert check_xonsh_ast(f'$[echo "test" {r} {e}> test.txt < input.txt]', False)


@pytest.mark.xfail
def test_subproc_raw_str_literal(check_xonsh_ast):
    tree = check_xonsh_ast("!(echo '$foo')", run=False, return_obs=True)
    assert isinstance(tree, AST)
    subproc = tree.body
    assert isinstance(subproc.args[0].elts[1], Call)
    assert subproc.args[0].elts[1].func.attr == "expand_path"

    tree = check_xonsh_ast("!(echo r'$foo')", run=False, return_obs=True)
    assert isinstance(tree, AST)
    subproc = tree.body
    assert isinstance(subproc.args[0].elts[1], ast.Constant)
    assert subproc.args[0].elts[1].s == "$foo"


def test_parsing(parse_str, subtests):
    file = Path(__file__).parent / "data/statements.xsh"
    for name, inp in get_cases(file):
        with subtests.test(name=name):
            parse_str(inp, mode="exec")
