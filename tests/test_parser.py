"""Tests the xonsh parser."""

import ast
import itertools
import textwrap
from ast import AST, Call, Pass, With
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


def get_cases(path):
    case_name = ""
    parts = []
    for line in path.read_text().splitlines():
        if line.startswith("## "):
            case_name = line[3:]
        elif not line.strip():
            if parts:
                yield case_name, "\n".join(parts)
                parts.clear()
        else:
            parts.append(line)


def test_statements(check_stmts, subtests):
    data = Path(__file__).parent / "data" / "x-statements.py"
    for idx, code in get_cases(data):
        with subtests.test(idx=idx):
            check_stmts(code)


#
# Xonsh specific syntax
#


@pytest.mark.parametrize(
    "inp,expanded",
    [
        ['p"/foo"', "__xonsh__.path_literal('/foo')"],
        ['pr"/foo"', "__xonsh__.path_literal('/foo')"],
        ['rp"/foo"', "__xonsh__.path_literal('/foo')"],
        ['pR"/foo"', "__xonsh__.path_literal('/foo')"],
        ['Rp"/foo"', "__xonsh__.path_literal('/foo')"],
    ],
)
def test_path_literal(inp, expanded, unparse_diff):
    unparse_diff(inp, expanded)


@pytest.mark.parametrize(
    "inp,expanded",
    [
        ['pf"/foo"', "__xonsh__.path_literal(f'/foo')"],
        ['fp"/foo"', "__xonsh__.path_literal(f'/foo')"],
        ['pF"/foo"', "__xonsh__.path_literal(f'/foo')"],
        ['Fp"/foo"', "__xonsh__.path_literal(f'/foo')"],
        ['pf"/foo{1+1}"', "__xonsh__.path_literal(f'/foo{1 + 1}')"],
        ['fp"/foo{1+1}"', "__xonsh__.path_literal(f'/foo{1 + 1}')"],
        ['pF"/foo{1+1}"', "__xonsh__.path_literal(f'/foo{1 + 1}')"],
        ['Fp"/foo{1+1}"', "__xonsh__.path_literal(f'/foo{1 + 1}')"],
    ],
)
def test_path_fstring_literal(inp, expanded, unparse_diff):
    unparse_diff(inp, expanded)


@pytest.mark.parametrize(
    "inp,expanded",
    [
        ("$WAKKA", "__xonsh__.env['WAKKA']"),
        ("$y = 'one'", "__xonsh__.env['y'] = 'one'"),
        ("y = $x", "y = __xonsh__.env['x']"),
        ("y = ${x}", "y = __xonsh__.env['x']"),
        ("y = ${'x' + 'y'}", "y = __xonsh__.env[str('x' + 'y')]"),
        ('${None or "WAKKA"}', "__xonsh__.env[str(None or 'WAKKA')]"),
        ("${$JAWAKA}", "__xonsh__.env[str(__xonsh__.env['JAWAKA'])]"),
    ],
)
def test_dollars(inp, expanded, unparse_diff):
    unparse_diff(inp, expanded, mode="exec")


def test_dollar_py_test_recursive_name(unparse_diff):
    unparse_diff("${None or $JAWAKA}", "__xonsh__.env[str(None or __xonsh__.env['JAWAKA'])]")


@pytest.mark.xfail
def test_dollar_py_test_recursive_test(unparse_diff):
    unparse_diff('${${"JAWA" + $JAWAKA[-2:]}}')


def test_dollar_name_set(check_xonsh):
    check_xonsh({"WAKKA": 42}, "$WAKKA = 42")


def test_dollar_py_set(check_xonsh):
    check_xonsh({"WAKKA": 42}, 'x = "WAKKA"; ${x} = 65')


@pytest.mark.parametrize(
    "inp",
    [
        "$(ls)",
        "$(ls )",
        "$( ls )",
        "$( ls)",
    ],
)
def test_dollar_sub(inp, check_xonsh_ast, xsh):
    check_xonsh_ast({}, inp)
    xsh.subproc_captured.assert_called_with(["ls"])


def test_ls_dot(check_xonsh_ast, xsh):
    check_xonsh_ast({}, "$(ls .)")
    xsh.subproc_captured.assert_called_with(["ls", "."])


@pytest.mark.xfail
def test_lambda_in_atparens(check_xonsh_ast):
    check_xonsh_ast({}, '$(echo hello | @(lambda a, s=None: "hey!") foo bar baz)', False)


@pytest.mark.xfail
def test_generator_in_atparens(check_xonsh_ast):
    check_xonsh_ast({}, "$(echo @(i**2 for i in range(20)))", False)


@pytest.mark.xfail
def test_bare_tuple_in_atparens(check_xonsh_ast):
    check_xonsh_ast({}, '$(echo @("a", 7))', False)


@pytest.mark.xfail
def test_nested_madness(check_xonsh_ast):
    check_xonsh_ast(
        {},
        "$(@$(which echo) ls " "| @(lambda a, s=None: $(@(s.strip()) @(a[1]))) foo -la baz)",
        False,
    )


@pytest.mark.xfail
def test_atparens_intoken(check_xonsh_ast):
    check_xonsh_ast({}, "![echo /x/@(y)/z]", False)


def test_ls_dot_nesting(check_xonsh_ast):
    check_xonsh_ast({}, '$(ls @(None or "."))', False)


def test_ls_dot_nesting_var(check_xonsh):
    check_xonsh({}, 'x = "."; $(ls @(None or x))', False)


def test_ls_dot_str(check_xonsh_ast):
    check_xonsh_ast({}, '$(ls ".")', False)


def test_ls_nest_ls(check_xonsh_ast):
    check_xonsh_ast({}, "$(ls $(ls))", False)


def test_ls_nest_ls_dashl(check_xonsh_ast):
    check_xonsh_ast({}, "$(ls $(ls) -l)", False)


def test_ls_envvar_strval(check_xonsh_ast):
    check_xonsh_ast({"WAKKA": "."}, "$(ls $WAKKA)", False)


def test_ls_envvar_listval(check_xonsh_ast):
    check_xonsh_ast({"WAKKA": [".", "."]}, "$(ls $WAKKA)", False)


def test_bang_sub(check_xonsh_ast):
    check_xonsh_ast({}, "!(ls)", False)


@pytest.mark.parametrize(
    "expr",
    [
        "!(ls )",
        "!( ls)",
        "!( ls )",
    ],
)
def test_bang_sub_space(expr, check_xonsh_ast):
    check_xonsh_ast({}, expr, False)


def test_bang_ls_dot(check_xonsh_ast):
    check_xonsh_ast({}, "!(ls .)", False)


def test_bang_ls_dot_nesting(check_xonsh_ast):
    check_xonsh_ast({}, '!(ls @(None or "."))', False)


def test_bang_ls_dot_nesting_var(check_xonsh):
    check_xonsh({}, 'x = "."; !(ls @(None or x))', False)


def test_bang_ls_dot_str(check_xonsh_ast):
    check_xonsh_ast({}, '!(ls ".")', False)


def test_bang_ls_nest_ls(check_xonsh_ast):
    check_xonsh_ast({}, "!(ls $(ls))", False)


def test_bang_ls_nest_ls_dashl(check_xonsh_ast):
    check_xonsh_ast({}, "!(ls $(ls) -l)", False)


def test_bang_ls_envvar_strval(check_xonsh_ast):
    check_xonsh_ast({"WAKKA": "."}, "!(ls $WAKKA)", False)


def test_bang_ls_envvar_listval(check_xonsh_ast):
    check_xonsh_ast({"WAKKA": [".", "."]}, "!(ls $WAKKA)", False)


def test_bang_envvar_args(check_xonsh_ast):
    check_xonsh_ast({"LS": "ls"}, "!($LS .)", False)


@pytest.mark.xfail
def test_question(check_xonsh_ast):
    check_xonsh_ast({}, "range?")


@pytest.mark.xfail
def test_dobquestion(check_xonsh_ast):
    check_xonsh_ast({}, "range??")


@pytest.mark.xfail
def test_question_chain(check_xonsh_ast):
    check_xonsh_ast({}, "range?.index?")


def test_ls_regex(check_xonsh_ast):
    check_xonsh_ast({}, "$(ls `[Ff]+i*LE` -l)", False)


@pytest.mark.parametrize("p", ["", "p"])
@pytest.mark.parametrize("f", ["", "f"])
@pytest.mark.parametrize("glob_type", ["", "r", "g"])
def test_backtick(p, f, glob_type, check_xonsh_ast):
    check_xonsh_ast({}, f"print({p}{f}{glob_type}`.*`)", False)


def test_ls_regex_octothorpe(check_xonsh_ast):
    check_xonsh_ast({}, "$(ls `#[Ff]+i*LE` -l)", False)


def test_ls_explicitregex(check_xonsh_ast):
    check_xonsh_ast({}, "$(ls r`[Ff]+i*LE` -l)", False)


def test_ls_explicitregex_octothorpe(check_xonsh_ast):
    check_xonsh_ast({}, "$(ls r`#[Ff]+i*LE` -l)", False)


def test_ls_glob(check_xonsh_ast):
    check_xonsh_ast({}, "$(ls g`[Ff]+i*LE` -l)", False)


def test_ls_glob_octothorpe(check_xonsh_ast):
    check_xonsh_ast({}, "$(ls g`#[Ff]+i*LE` -l)", False)


def test_ls_customsearch(check_xonsh_ast):
    check_xonsh_ast({}, "$(ls @foo`[Ff]+i*LE` -l)", False)


def test_custombacktick(check_xonsh_ast):
    check_xonsh_ast({}, "print(@foo`.*`)", False)


def test_ls_customsearch_octothorpe(check_xonsh_ast):
    check_xonsh_ast({}, "$(ls @foo`#[Ff]+i*LE` -l)", False)


def test_injection(check_xonsh_ast):
    check_xonsh_ast({}, "$[@$(which python)]", False)


def test_rhs_nested_injection(check_xonsh_ast):
    check_xonsh_ast({}, "$[ls @$(dirname @$(which python))]", False)


def test_merged_injection(check_xonsh_ast):
    tree = check_xonsh_ast({}, "![a@$(echo 1 2)b]", False, return_obs=True)
    assert isinstance(tree, AST)
    func = tree.body.args[0].right.func
    assert func.attr == "list_of_list_of_strs_outer_product"


def test_backtick_octothorpe(check_xonsh_ast):
    check_xonsh_ast({}, "print(`#.*`)", False)


def test_uncaptured_sub(check_xonsh_ast):
    check_xonsh_ast({}, "$[ls]", False)


def test_hiddenobj_sub(check_xonsh_ast):
    check_xonsh_ast({}, "![ls]", False)


def test_slash_envarv_echo(check_xonsh_ast):
    check_xonsh_ast({}, "![echo $HOME/place]", False)


def test_echo_double_eq(check_xonsh_ast):
    check_xonsh_ast({}, "![echo yo==yo]", False)


def test_bang_two_cmds_one_pipe(check_xonsh_ast):
    check_xonsh_ast({}, "!(ls | grep wakka)", False)


def test_bang_three_cmds_two_pipes(check_xonsh_ast):
    check_xonsh_ast({}, "!(ls | grep wakka | grep jawaka)", False)


def test_bang_one_cmd_write(check_xonsh_ast):
    check_xonsh_ast({}, "!(ls > x.py)", False)


def test_bang_one_cmd_append(check_xonsh_ast):
    check_xonsh_ast({}, "!(ls >> x.py)", False)


def test_bang_two_cmds_write(check_xonsh_ast):
    check_xonsh_ast({}, "!(ls | grep wakka > x.py)", False)


def test_bang_two_cmds_append(check_xonsh_ast):
    check_xonsh_ast({}, "!(ls | grep wakka >> x.py)", False)


def test_bang_cmd_background(check_xonsh_ast):
    check_xonsh_ast({}, "!(emacs ugggh &)", False)


def test_bang_cmd_background_nospace(check_xonsh_ast):
    check_xonsh_ast({}, "!(emacs ugggh&)", False)


def test_bang_git_quotes_no_space(check_xonsh_ast):
    check_xonsh_ast({}, '![git commit -am "wakka"]', False)


def test_bang_git_quotes_space(check_xonsh_ast):
    check_xonsh_ast({}, '![git commit -am "wakka jawaka"]', False)


def test_bang_git_two_quotes_space(check_xonsh):
    check_xonsh(
        {},
        '![git commit -am "wakka jawaka"]\n' '![git commit -am "flock jawaka"]\n',
        False,
    )


def test_bang_git_two_quotes_space_space(check_xonsh):
    check_xonsh(
        {},
        '![git commit -am "wakka jawaka" ]\n' '![git commit -am "flock jawaka milwaka" ]\n',
        False,
    )


def test_bang_ls_quotes_3_space(check_xonsh_ast):
    check_xonsh_ast({}, '![ls "wakka jawaka baraka"]', False)


def test_two_cmds_one_pipe(check_xonsh_ast):
    check_xonsh_ast({}, "$(ls | grep wakka)", False)


def test_three_cmds_two_pipes(check_xonsh_ast):
    check_xonsh_ast({}, "$(ls | grep wakka | grep jawaka)", False)


def test_two_cmds_one_and_brackets(check_xonsh_ast):
    check_xonsh_ast({}, "![ls me] and ![grep wakka]", False)


def test_three_cmds_two_ands(check_xonsh_ast):
    check_xonsh_ast({}, "![ls] and ![grep wakka] and ![grep jawaka]", False)


def test_two_cmds_one_doubleamps(check_xonsh_ast):
    check_xonsh_ast({}, "![ls] && ![grep wakka]", False)


def test_three_cmds_two_doubleamps(check_xonsh_ast):
    check_xonsh_ast({}, "![ls] && ![grep wakka] && ![grep jawaka]", False)


def test_two_cmds_one_or(check_xonsh_ast):
    check_xonsh_ast({}, "![ls] or ![grep wakka]", False)


def test_three_cmds_two_ors(check_xonsh_ast):
    check_xonsh_ast({}, "![ls] or ![grep wakka] or ![grep jawaka]", False)


def test_two_cmds_one_doublepipe(check_xonsh_ast):
    check_xonsh_ast({}, "![ls] || ![grep wakka]", False)


def test_three_cmds_two_doublepipe(check_xonsh_ast):
    check_xonsh_ast({}, "![ls] || ![grep wakka] || ![grep jawaka]", False)


def test_one_cmd_write(check_xonsh_ast):
    check_xonsh_ast({}, "$(ls > x.py)", False)


def test_one_cmd_append(check_xonsh_ast):
    check_xonsh_ast({}, "$(ls >> x.py)", False)


def test_two_cmds_write(check_xonsh_ast):
    check_xonsh_ast({}, "$(ls | grep wakka > x.py)", False)


def test_two_cmds_append(check_xonsh_ast):
    check_xonsh_ast({}, "$(ls | grep wakka >> x.py)", False)


def test_cmd_background(check_xonsh_ast):
    check_xonsh_ast({}, "$(emacs ugggh &)", False)


def test_cmd_background_nospace(check_xonsh_ast):
    check_xonsh_ast({}, "$(emacs ugggh&)", False)


def test_git_quotes_no_space(check_xonsh_ast):
    check_xonsh_ast({}, '$[git commit -am "wakka"]', False)


def test_git_quotes_space(check_xonsh_ast):
    check_xonsh_ast({}, '$[git commit -am "wakka jawaka"]', False)


def test_git_two_quotes_space(check_xonsh):
    check_xonsh(
        {},
        '$[git commit -am "wakka jawaka"]\n' '$[git commit -am "flock jawaka"]\n',
        False,
    )


def test_git_two_quotes_space_space(check_xonsh):
    check_xonsh(
        {},
        '$[git commit -am "wakka jawaka" ]\n' '$[git commit -am "flock jawaka milwaka" ]\n',
        False,
    )


def test_ls_quotes_3_space(check_xonsh_ast):
    check_xonsh_ast({}, '$[ls "wakka jawaka baraka"]', False)


def test_leading_envvar_assignment(check_xonsh_ast):
    check_xonsh_ast({}, "![$FOO='foo' $BAR=2 echo r'$BAR']", False)


def test_echo_comma(check_xonsh_ast):
    check_xonsh_ast({}, "![echo ,]", False)


def test_echo_internal_comma(check_xonsh_ast):
    check_xonsh_ast({}, "![echo 1,2]", False)


def test_comment_only(check_xonsh_ast):
    check_xonsh_ast({}, "# hello")


def test_echo_slash_question(check_xonsh_ast):
    check_xonsh_ast({}, "![echo /?]", False)


def test_bad_quotes(check_xonsh_ast):
    with pytest.raises(SyntaxError):
        check_xonsh_ast({}, '![echo """hello]', False)


def test_redirect(check_xonsh_ast):
    assert check_xonsh_ast({}, "$[cat < input.txt]", False)
    assert check_xonsh_ast({}, "$[< input.txt cat]", False)


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
def test_use_subshell(case, check_xonsh_ast):
    check_xonsh_ast({}, case, False, debug_level=0)


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
def test_redirect_abspath(case, check_xonsh_ast):
    assert check_xonsh_ast({}, case, False)


@pytest.mark.parametrize("case", ["", "o", "out", "1"])
def test_redirect_output(case, check_xonsh_ast):
    assert check_xonsh_ast({}, f'$[echo "test" {case}> test.txt]', False)
    assert check_xonsh_ast({}, f'$[< input.txt echo "test" {case}> test.txt]', False)
    assert check_xonsh_ast({}, f'$[echo "test" {case}> test.txt < input.txt]', False)


@pytest.mark.parametrize("case", ["e", "err", "2"])
def test_redirect_error(case, check_xonsh_ast):
    assert check_xonsh_ast({}, f'$[echo "test" {case}> test.txt]', False)
    assert check_xonsh_ast({}, f'$[< input.txt echo "test" {case}> test.txt]', False)
    assert check_xonsh_ast({}, f'$[echo "test" {case}> test.txt < input.txt]', False)


@pytest.mark.parametrize("case", ["a", "all", "&"])
def test_redirect_all(case, check_xonsh_ast):
    assert check_xonsh_ast({}, f'$[echo "test" {case}> test.txt]', False)
    assert check_xonsh_ast({}, f'$[< input.txt echo "test" {case}> test.txt]', False)
    assert check_xonsh_ast({}, f'$[echo "test" {case}> test.txt < input.txt]', False)


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
    assert check_xonsh_ast({}, f'$[echo "test" {r} {o}> test.txt]', False)
    assert check_xonsh_ast({}, f'$[< input.txt echo "test" {r} {o}> test.txt]', False)
    assert check_xonsh_ast({}, f'$[echo "test" {r} {o}> test.txt < input.txt]', False)


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
    assert check_xonsh_ast({}, f'$[echo "test" {r} {e}> test.txt]', False)
    assert check_xonsh_ast({}, f'$[< input.txt echo "test" {r} {e}> test.txt]', False)
    assert check_xonsh_ast({}, f'$[echo "test" {r} {e}> test.txt < input.txt]', False)


def test_macro_call_empty(check_xonsh_ast):
    assert check_xonsh_ast({}, "f!()", False)


MACRO_ARGS = [
    "x",
    "True",
    "None",
    "import os",
    "x=10",
    '"oh no, mom"',
    "...",
    " ... ",
    "if True:\n  pass",
    "{x: y}",
    "{x: y, 42: 5}",
    "{1, 2, 3,}",
    "(x,y)",
    "(x, y)",
    "((x, y), z)",
    "g()",
    "range(10)",
    "range(1, 10, 2)",
    "()",
    "{}",
    "[]",
    "[1, 2]",
    "@(x)",
    "!(ls -l)",
    "![ls -l]",
    "$(ls -l)",
    "${x + y}",
    "$[ls -l]",
    "@$(which xonsh)",
]


@pytest.mark.parametrize("s", MACRO_ARGS)
def test_macro_call_one_arg(check_xonsh_ast, s):
    f = f"f!({s})"
    tree = check_xonsh_ast({}, f, False, return_obs=True)
    assert isinstance(tree, AST)
    args = tree.body.args[1].elts
    assert len(args) == 1
    assert args[0].s == s.strip()


@pytest.mark.parametrize("s,t", itertools.product(MACRO_ARGS[::2], MACRO_ARGS[1::2]))
def test_macro_call_two_args(check_xonsh_ast, s, t):
    f = f"f!({s}, {t})"
    tree = check_xonsh_ast({}, f, False, return_obs=True)
    assert isinstance(tree, AST)
    args = tree.body.args[1].elts
    assert len(args) == 2
    assert args[0].s == s.strip()
    assert args[1].s == t.strip()


@pytest.mark.parametrize("s,t,u", itertools.product(MACRO_ARGS[::3], MACRO_ARGS[1::3], MACRO_ARGS[2::3]))
def test_macro_call_three_args(check_xonsh_ast, s, t, u):
    f = f"f!({s}, {t}, {u})"
    tree = check_xonsh_ast({}, f, False, return_obs=True)
    assert isinstance(tree, AST)
    args = tree.body.args[1].elts
    assert len(args) == 3
    assert args[0].s == s.strip()
    assert args[1].s == t.strip()
    assert args[2].s == u.strip()


@pytest.mark.parametrize("s", MACRO_ARGS)
def test_macro_call_one_trailing(check_xonsh_ast, s):
    f = f"f!({s},)"
    tree = check_xonsh_ast({}, f, False, return_obs=True)
    assert isinstance(tree, AST)
    args = tree.body.args[1].elts
    assert len(args) == 1
    assert args[0].s == s.strip()


@pytest.mark.parametrize("s", MACRO_ARGS)
def test_macro_call_one_trailing_space(check_xonsh_ast, s):
    f = f"f!( {s}, )"
    tree = check_xonsh_ast({}, f, False, return_obs=True)
    assert isinstance(tree, AST)
    args = tree.body.args[1].elts
    assert len(args) == 1
    assert args[0].s == s.strip()


SUBPROC_MACRO_OC = [("!(", ")"), ("$(", ")"), ("![", "]"), ("$[", "]")]


@pytest.mark.parametrize("opener, closer", SUBPROC_MACRO_OC)
@pytest.mark.parametrize("body", ["echo!", "echo !", "echo ! "])
def test_empty_subprocbang(opener, closer, body, check_xonsh_ast):
    tree = check_xonsh_ast({}, opener + body + closer, False, return_obs=True)
    assert isinstance(tree, AST)
    cmd = tree.body.args[0].elts
    assert len(cmd) == 2
    assert cmd[1].s == ""


@pytest.mark.parametrize("opener, closer", SUBPROC_MACRO_OC)
@pytest.mark.parametrize("body", ["echo!x", "echo !x", "echo !x", "echo ! x"])
def test_single_subprocbang(opener, closer, body, check_xonsh_ast):
    tree = check_xonsh_ast({}, opener + body + closer, False, return_obs=True)
    assert isinstance(tree, AST)
    cmd = tree.body.args[0].elts
    assert len(cmd) == 2
    assert cmd[1].s == "x"


@pytest.mark.parametrize("opener, closer", SUBPROC_MACRO_OC)
@pytest.mark.parametrize("body", ["echo -n!x", "echo -n!x", "echo -n !x", "echo -n ! x"])
def test_arg_single_subprocbang(opener, closer, body, check_xonsh_ast):
    tree = check_xonsh_ast({}, opener + body + closer, False, return_obs=True)
    assert isinstance(tree, AST)
    cmd = tree.body.args[0].elts
    assert len(cmd) == 3
    assert cmd[2].s == "x"


@pytest.mark.parametrize("opener, closer", SUBPROC_MACRO_OC)
@pytest.mark.parametrize("ipener, iloser", [("$(", ")"), ("@$(", ")"), ("$[", "]")])
@pytest.mark.parametrize("body", ["echo -n!x", "echo -n!x", "echo -n !x", "echo -n ! x"])
def test_arg_single_subprocbang_nested(opener, closer, ipener, iloser, body, check_xonsh_ast):
    tree = check_xonsh_ast({}, opener + body + closer, False, return_obs=True)
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
def test_many_subprocbang(opener, closer, body, check_xonsh_ast):
    tree = check_xonsh_ast({}, opener + body + closer, False, return_obs=True)
    assert isinstance(tree, AST)
    cmd = tree.body.args[0].elts
    assert len(cmd) == 2
    assert cmd[1].s == body.partition("!")[-1].strip()


WITH_BANG_RAWSUITES = [
    "pass\n",
    "x = 42\ny = 12\n",
    'export PATH="yo:momma"\necho $PATH\n',
    ("with q as t:\n" "    v = 10\n" "\n"),
    (
        "with q as t:\n"
        "    v = 10\n"
        "\n"
        "for x in range(6):\n"
        "    if True:\n"
        "        pass\n"
        "    else:\n"
        "        ls -l\n"
        "\n"
        "a = 42\n"
    ),
]


@pytest.mark.parametrize("body", WITH_BANG_RAWSUITES)
def test_withbang_single_suite(body, check_xonsh_ast):
    code = "with! x:\n{}".format(textwrap.indent(body, "    "))
    tree = check_xonsh_ast({}, code, False, return_obs=True, mode="exec")
    assert isinstance(tree, AST)
    wither = tree.body[0]
    assert isinstance(wither, With)
    assert len(wither.body) == 1
    assert isinstance(wither.body[0], Pass)
    assert len(wither.items) == 1
    item = wither.items[0]
    s = item.context_expr.args[1].s
    assert s == body


@pytest.mark.parametrize("body", WITH_BANG_RAWSUITES)
def test_withbang_as_single_suite(body, check_xonsh_ast):
    code = "with! x as y:\n{}".format(textwrap.indent(body, "    "))
    tree = check_xonsh_ast({}, code, False, return_obs=True, mode="exec")
    assert isinstance(tree, AST)
    wither = tree.body[0]
    assert isinstance(wither, With)
    assert len(wither.body) == 1
    assert isinstance(wither.body[0], Pass)
    assert len(wither.items) == 1
    item = wither.items[0]
    assert item.optional_vars.id == "y"
    s = item.context_expr.args[1].s
    assert s == body


@pytest.mark.parametrize("body", WITH_BANG_RAWSUITES)
def test_withbang_single_suite_trailing(body, check_xonsh_ast):
    code = "with! x:\n{}\nprint(x)\n".format(textwrap.indent(body, "    "))
    tree = check_xonsh_ast(
        {},
        code,
        False,
        return_obs=True,
        mode="exec",
        # debug_level=100
    )
    assert isinstance(tree, AST)
    wither = tree.body[0]
    assert isinstance(wither, With)
    assert len(wither.body) == 1
    assert isinstance(wither.body[0], Pass)
    assert len(wither.items) == 1
    item = wither.items[0]
    s = item.context_expr.args[1].s
    assert s == body + "\n"


WITH_BANG_RAWSIMPLE = [
    "pass",
    "x = 42; y = 12",
    'export PATH="yo:momma"; echo $PATH',
    "[1,\n    2,\n    3]",
]


@pytest.mark.parametrize("body", WITH_BANG_RAWSIMPLE)
def test_withbang_single_simple(body, check_xonsh_ast):
    code = f"with! x: {body}\n"
    tree = check_xonsh_ast({}, code, False, return_obs=True, mode="exec")
    assert isinstance(tree, AST)
    wither = tree.body[0]
    assert isinstance(wither, With)
    assert len(wither.body) == 1
    assert isinstance(wither.body[0], Pass)
    assert len(wither.items) == 1
    item = wither.items[0]
    s = item.context_expr.args[1].s
    assert s == body


@pytest.mark.parametrize("body", WITH_BANG_RAWSIMPLE)
def test_withbang_single_simple_opt(body, check_xonsh_ast):
    code = f"with! x as y: {body}\n"
    tree = check_xonsh_ast({}, code, False, return_obs=True, mode="exec")
    assert isinstance(tree, AST)
    wither = tree.body[0]
    assert isinstance(wither, With)
    assert len(wither.body) == 1
    assert isinstance(wither.body[0], Pass)
    assert len(wither.items) == 1
    item = wither.items[0]
    assert item.optional_vars.id == "y"
    s = item.context_expr.args[1].s
    assert s == body


@pytest.mark.parametrize("body", WITH_BANG_RAWSUITES)
def test_withbang_as_many_suite(body, check_xonsh_ast):
    code = "with! x as a, y as b, z as c:\n{}"
    code = code.format(textwrap.indent(body, "    "))
    tree = check_xonsh_ast({}, code, False, return_obs=True, mode="exec")
    assert isinstance(tree, AST)
    wither = tree.body[0]
    assert isinstance(wither, With)
    assert len(wither.body) == 1
    assert isinstance(wither.body[0], Pass)
    assert len(wither.items) == 3
    for i, targ in enumerate("abc"):
        item = wither.items[i]
        assert item.optional_vars.id == targ
        s = item.context_expr.args[1].s
        assert s == body


def test_subproc_raw_str_literal(check_xonsh_ast):
    tree = check_xonsh_ast({}, "!(echo '$foo')", run=False, return_obs=True)
    assert isinstance(tree, AST)
    subproc = tree.body
    assert isinstance(subproc.args[0].elts[1], Call)
    assert subproc.args[0].elts[1].func.attr == "expand_path"

    tree = check_xonsh_ast({}, "!(echo r'$foo')", run=False, return_obs=True)
    assert isinstance(tree, AST)
    subproc = tree.body
    assert isinstance(subproc.args[0].elts[1], ast.Constant)
    assert subproc.args[0].elts[1].s == "$foo"


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
def test_syntax_error_del_inp(parse_str, exp):
    with pytest.raises(SyntaxError):
        parse_str(f"del {exp}")


def test_syntax_error_lonely_del(parse_str):
    with pytest.raises(SyntaxError):
        parse_str("del")


def test_syntax_error_assign_literal(parse_str):
    with pytest.raises(SyntaxError):
        parse_str("7 = x")


def test_syntax_error_assign_constant(parse_str):
    with pytest.raises(SyntaxError):
        parse_str("True = 8")


def test_syntax_error_assign_emptytuple(parse_str):
    with pytest.raises(SyntaxError):
        parse_str("() = x")


def test_syntax_error_assign_call(parse_str):
    with pytest.raises(SyntaxError):
        parse_str("foo() = x")


def test_syntax_error_assign_lambda(parse_str):
    with pytest.raises(SyntaxError):
        parse_str('lambda x: "yay" = y')


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
def test_syntax_error_assign_comps(parse_str, exp):
    with pytest.raises(SyntaxError):
        parse_str(f"{exp} = z")


@pytest.mark.parametrize("exp", ["x + y", "x and y", "-x"])
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
def test_syntax_error_literal_concat_different(first_prefix, second_prefix, parse_str):
    with pytest.raises(SyntaxError):
        parse_str(f"{first_prefix}'hello' {second_prefix}'world'")


def test_get_repo_url(parse_str):
    parse_str(
        "def get_repo_url():\n"
        "    raw = $(git remote get-url --push origin).rstrip()\n"
        "    return raw.replace('https://github.com/', '')\n"
    )
