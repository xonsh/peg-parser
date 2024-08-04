""" "Conftest for pure python parser."""

from __future__ import annotations

import maturin_import_hook

maturin_import_hook.install()

import ast
import contextlib
import io
import logging
from unittest.mock import MagicMock

import pytest

log = logging.getLogger(__name__)


def nodes_equal(x, y):
    assert type(x) == type(y), f"Ast nodes do not have the same type: '{type(x)}' != '{type(y)}' "
    if isinstance(x, ast.Constant):
        assert x.value == y.value, (
            f"Constant ast nodes do not have the same value: " f"{x.value!r} != {y.value!r}"
        )
    if isinstance(x, ast.Expr | ast.FunctionDef | ast.ClassDef):
        assert x.lineno == y.lineno, f"Ast nodes do not have the same line number : {x.lineno} != {y.lineno}"
        assert (
            x.col_offset == y.col_offset
        ), f"Ast nodes do not have the same column offset number : {x.col_offset} != {y.col_offset}"
    for (xname, xval), (yname, yval) in zip(ast.iter_fields(x), ast.iter_fields(y), strict=False):
        assert (
            xname == yname
        ), f"Ast nodes fields differ : {xname} (of type {type(xval)}) != {yname} (of type {type(yval)})"
        assert type(xval) == type(
            yval
        ), f"Ast nodes fields differ : {xname} (of type {type(xval)}) != {yname} (of type {type(yval)})"
    for xchild, ychild in zip(ast.iter_child_nodes(x), ast.iter_child_nodes(y), strict=False):
        assert nodes_equal(xchild, ychild), "Ast node children differs"
    return True


def build_parser(name: str):
    from peg_parser import parser

    return getattr(parser, name)


def _get_tokens(inp):
    from peg_parser import tokenize
    from peg_parser.tokenizer import Tokenizer

    gen = tokenize.generate_tokens(io.StringIO(inp).readline)
    tokenizer = Tokenizer(gen)
    tokens = []
    while True:
        tok = tokenizer.getnext()
        tokens.append(tok)
        if tok.type == tokenize.Token.ENDMARKER:
            break
    return tokens


@pytest.fixture(scope="session")
def get_tokens():
    return _get_tokens


@pytest.fixture(scope="session")
def python_parser_cls():
    return build_parser("XonshParser")


@pytest.fixture(scope="session")
def python_parse_file(python_parser_cls):
    return python_parser_cls.parse_file


@pytest.fixture(scope="session")
def python_parse_str(python_parser_cls):
    return python_parser_cls.parse_string


@pytest.fixture(scope="session")
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
