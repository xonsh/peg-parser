import ast

import pytest


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
