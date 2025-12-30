""" "Conftest for pure python parser."""

from __future__ import annotations

from pathlib import Path

import maturin_import_hook

maturin_import_hook.install()

import ast
import contextlib
import io
import logging
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest
from winnow_parser import parse_code

from tests.tools import nodes_equal

if TYPE_CHECKING:
    from winnow_parser import TokenInfo

log = logging.getLogger(__name__)


def _winnow_lex_input(inp: str) -> list[TokenInfo]:
    # skip the NEWLINE, ENDMARKER tokens for easier testing
    from winnow_parser import tokenize

    tokens = [tok for tok in tokenize(inp) if str(tok.type.name) not in ("WS", "NL")]
    if tokens and "ENDMARKER" in str(tokens[-1].type):
        tokens.pop()
    if tokens and "NEWLINE" in str(tokens[-1].type):
        tokens.pop()
    return tokens


@pytest.fixture(name="lexer")
def _lexer():
    return _winnow_lex_input


def _get_tokens(inp):
    from winnow_parser import tokenize

    return tokenize(inp)


@pytest.fixture(scope="session")
def get_tokens():
    return _get_tokens


@pytest.fixture
def python_parse_file():
    def _parse(file):
        code = Path(file).read_text()
        return parse_code(code)

    return _parse


@pytest.fixture
def python_parse_str():
    def _parse(code: str, **kw):
        # todo: handle extra parameters
        return parse_code(code)

    return _parse


@pytest.fixture
def parse_str(python_parse_str, get_tokens):
    """Parse and print verbose output on failure"""
    session = [0]

    def factory(text, verbose=False, mode="eval", py_version: tuple | None = None):
        try:
            return python_parse_str(text, verbose=verbose, mode=mode, py_version=py_version)
        except Exception as e:
            print("Parsing failed:")
            print("Source is:")
            print(text)
            if (not verbose) and session[0] < 3:
                toks = get_tokens(text)
                log.info("Tokens are: \n %s", "\n".join(map(str, toks)))
                # log verbose output of atleast 3 failures
                log.info("Retrying with verbose=True")
                with (
                    contextlib.redirect_stdout(io.StringIO()) as stdout,
                    contextlib.suppress(Exception, SyntaxError),
                ):
                    python_parse_str(text, verbose=True, mode=mode, py_version=py_version)
                captured = stdout.getvalue()
                log.info(captured)
                log.error("Failed to parse: %s", e, exc_info=True)
                session[0] += 1
            pytest.fail(str(e))

    return factory


@pytest.fixture
def check_ast(parse_str):
    def factory(inp: str, mode="eval", verbose=False):
        # expect a Python AST
        exp = ast.parse(inp, mode=mode)
        # observe something from xonsh
        obs = parse_str(inp, mode=mode, verbose=verbose)
        # Check that they are equal
        assert nodes_equal(exp, obs)

    return factory


@pytest.fixture
def eval_code(parse_str):
    def factory(text: str, mode="eval", **locs):
        obs = parse_str(text, mode=mode)
        bytecode = compile(obs, "<test-xonsh-ast>", mode)
        return eval(bytecode, locs)

    return factory


@pytest.fixture
def unparse_diff(parse_str):
    def factory(text: str, right: str | None = None, mode="eval"):
        left = parse_str(text, mode=mode)
        left = ast.unparse(left)
        if right is None:
            right = ast.parse(text).body[0]
            right = ast.unparse(right)
        assert left == right

    return factory


@pytest.fixture
def xsh():
    obj = MagicMock()

    def list_of_strs_or_callables(x):
        """
        A simplified version of the xonsh function.
        """
        if isinstance(x, str | bytes):
            return [x]
        if callable(x):
            return [x([])]
        return x

    def subproc_captured(*cmds):
        return "-".join([str(item) for item in cmds])

    def subproc_captured_inject(*cmds):
        return cmds

    obj.list_of_strs_or_callables = MagicMock(wraps=list_of_strs_or_callables)
    obj.subproc_captured = MagicMock(wraps=subproc_captured)
    obj.subproc_captured_inject = MagicMock(wraps=subproc_captured_inject)
    return obj


@pytest.fixture
def xsh_proc_method(xsh):
    def factory(start_symbol: str):
        method_name = {
            "$[": "subproc_uncaptured",
            "$(": "subproc_captured",
            "![": "subproc_captured_hiddenobject",
            "!(": "subproc_captured_object",
        }[start_symbol]
        return getattr(xsh, method_name)

    return factory


@pytest.fixture
def check_xonsh_ast(parse_str, xsh):
    """compatibility fixture"""

    def factory(
        inp: str,
        xenv: dict | None = None,
        mode="eval",
        verbose=False,
        **locs,
    ):
        obs = parse_str(inp, mode=mode, verbose=verbose)
        if obs is None:
            return  # comment only
        bytecode = compile(obs, "<test-xonsh-ast>", mode)
        xsh.env = xenv or {}
        locs["__xonsh__"] = xsh
        exec(bytecode, {}, locs)
        return obs

    return factory
