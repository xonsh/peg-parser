import pytest


@pytest.mark.parametrize(
    "inp",
    [
        'f"{$HOME}"',
        "f'{$XONSH_DEBUG}'",
        'F"{$PATH} and {$XONSH_DEBUG}"',
        'f"{ $HOME }"',
        "f\"{'$HOME'}\"",
        "f\"{${'HOME'}}\"",
        "f'{${$FOO+$BAR}}'",
        'f"{st!r}"',
    ],
)
def test_f_env_var(inp, parse_str):
    parse_str(inp)
