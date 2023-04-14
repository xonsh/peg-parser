import pytest

from xonsh_parser.parsers.preprocessor import translex


@pytest.mark.parametrize(
    "src, expected",
    [
        ("$ENV_NAME", "__xonsh__.env['ENV_NAME']"),
        ("$ENV_NAME = 1", "__xonsh__.env['ENV_NAME'] = 1"),
    ],
)
def test_env(src, expected):
    assert translex(src) == expected


@pytest.mark.parametrize(
    "src, expected",
    [
        (
            "$(cmd sub-cmd --opt)",
            "__xonsh__.subproc_captured_stdout(cmd sub-cmd --opt)",
        ),
        ("$[cmd sub-cmd --opt]", "__xonsh__.subproc_uncaptured(cmd sub-cmd --opt)"),
        (
            "![cmd sub-cmd --opt]",
            "__xonsh__.subproc_uncaptured_object(cmd sub-cmd --opt)",
        ),
        (
            "!(cmd sub-cmd --opt)",
            "__xonsh__.subproc_captured_object(cmd sub-cmd --opt)",
        ),
    ],
)
def test_subproc(src, expected):
    assert translex(src) == expected
