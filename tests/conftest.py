""" "Conftest for pure python parser."""

from __future__ import annotations

import maturin_import_hook

maturin_import_hook.install()

import ast
import contextlib
import io
import logging
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

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


def _py_lex_input(inp: str) -> list[TokenInfo]:
    from peg_parser.tokenizer import Tokenizer

    tokenizer = Tokenizer(io.StringIO(inp).readline)
    tokens = []
    while True:
        tok = tokenizer.getnext()
        # Filter WS and NL by string representation to be safe
        type_name = getattr(tok.type, "name", str(tok.type))
        if type_name in ("WS", "NL"):
            continue
        tokens.append(tok)
        if type_name == "ENDMARKER":
            break
    if tokens and getattr(tokens[-1].type, "name", str(tokens[-1].type)) == "ENDMARKER":
        tokens.pop()
    if tokens and getattr(tokens[-1].type, "name", str(tokens[-1].type)) == "NEWLINE":
        tokens.pop()
    return tokens


LEXERS = [
    # "rust",
    "py"
]


@pytest.fixture(params=LEXERS, name="lexer")
def _lexer(request):
    return _winnow_lex_input if request.param == "rust" else _py_lex_input


def build_parser(name: str):
    from peg_parser import parser

    return getattr(parser, name)


def _get_tokens(inp):
    from winnow_parser import tokenize

    return tokenize(inp)


@pytest.fixture(scope="session")
def get_tokens():
    return _get_tokens


@pytest.fixture(scope="session")
def python_parser_cls():
    return build_parser("XonshParser")


@pytest.fixture(params=LEXERS)
def python_parse_file(python_parser_cls, request):
    use_rust_tokenizer = request.param == "rust"

    def _parse(*args, **kw):
        return python_parser_cls.parse_file(*args, **kw, use_rust_tokenizer=use_rust_tokenizer)

    return _parse


@pytest.fixture(params=LEXERS)
def python_parse_str(python_parser_cls, request):
    use_rust_tokenizer = request.param == "rust"

    def _parse(*args, **kw):
        return python_parser_cls.parse_string(*args, **kw, use_rust_tokenizer=use_rust_tokenizer)

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


if __name__ == "__main__":
    build_parser("XonshParser")
