"""Tests the xonsh parser."""

from pathlib import Path

import pytest


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
        with subtests.test(idx=idx, inp=inp):
            unparse_diff(inp, exp)


@pytest.mark.parametrize("file", glob_data_param("stmts/*.py"))
def test_stmts(file, unparse_diff, subtests):
    for idx, (inp, exp) in enumerate(get_cases(file)):
        with subtests.test(idx=idx, inp=inp):
            unparse_diff(inp, exp, mode="exec")


@pytest.mark.parametrize(
    "inp",
    [
        'x = "WAKKA"; ${x} = 65',
        'x = "."; $(ls @(None or x))',
        'x = "."; !(ls @(None or x))',
        '$[git commit -am "wakka jawaka" ]',
        '$[git commit -am "flock jawaka milwaka" ]',
        '$[git commit -am "wakka jawaka"]',
        '$[git commit -am "flock jawaka"]',
        '![git commit -am "wakka jawaka" ]',
        '![git commit -am "flock jawaka milwaka" ]',
        '![git commit -am "wakka jawaka"]',
        '![git commit -am "flock jawaka"]',
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
def test_captured_procs(inp, args, check_xonsh_ast, xsh_proc_method):
    check_xonsh_ast(inp, mode="exec", xenv={"WAKKA": "wak"})
    method = xsh_proc_method(inp[:2])
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
    ],
)
def test_bang_procs(expr, check_xonsh_ast):
    check_xonsh_ast(expr, xenv={"LS": "ll", "WAKKA": "wak"})


@pytest.mark.parametrize("p", ["", "p"])
@pytest.mark.parametrize("f", ["", "f"])
@pytest.mark.parametrize("glob_type", ["", "r", "g"])
def test_backtick(p, f, glob_type, check_xonsh_ast):
    check_xonsh_ast(f"print({p}{f}{glob_type}`.*`)", False)


def test_comment_only(check_xonsh_ast):
    check_xonsh_ast("# hello", mode="exec")


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


def test_parsing(parse_str, subtests):
    file = Path(__file__).parent / "data/statements.xsh"
    for name, inp in get_cases(file):
        with subtests.test(name=name):
            parse_str(inp, mode="exec")
