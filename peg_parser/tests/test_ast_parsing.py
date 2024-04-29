"""Test pure Python parser against cpython parser."""

import ast
import difflib
import io
import textwrap
import tokenize as pytokenize
from pathlib import Path

import pytest

from peg_parser.parser import tokenize


def dump_diff(**trees: ast.AST):
    kwargs = dict(include_attributes=True, indent="  ")
    orig_name, pp_name = trees.keys()
    original, pp_ast = trees.values()
    o = ast.dump(original, **kwargs)
    p = ast.dump(pp_ast, **kwargs)
    return "\n".join(difflib.unified_diff(o.split("\n"), p.split("\n"), orig_name, pp_name))


@pytest.mark.parametrize(
    "filename",
    [
        "advanced_decorators.py",
        "assignment.py",
        "async.py",
        "call.py",
        "comprehensions.py",
        "expressions.py",
        "function_def.py",
        "imports.py",
        "lambdas.py",
        "multi_statement_per_line.py",
        "no_newline_at_end_of_file.py",
        "no_newline_at_end_of_file_with_comment.py",
        "pattern_matching.py",
        "simple_decorators.py",
        "statements.py",
        "with_statement_multi_items.py",
    ],
)
def test_parser(python_parse_file, python_parse_str, filename):
    path = Path(__file__).parent / "data" / filename
    with open(path) as f:
        source = f.read()

    kwargs = dict(include_attributes=True)
    kwargs["indent"] = "  "
    for part in source.split("\n\n\n"):
        original = ast.parse(part)

        try:
            pp_ast = python_parse_str(part, "exec")
        except Exception:
            print("Parsing failed:")
            print("Source is:")
            print(textwrap.indent(part, "  "))
            print("Token stream is:")
            for t in tokenize.generate_tokens(io.StringIO(part).readline):
                print(t)
            print()
            print("CPython ast is:")
            print(ast.dump(original, **kwargs))
            print()
            print("Python token stream is:")
            for t in pytokenize.generate_tokens(io.StringIO(part).readline):
                print(t)
            raise

        if diff := dump_diff(cpython=original, pegen=pp_ast):
            print(part)
            print(diff)
        assert not diff

    diff = dump_diff(cpython=ast.parse(source), pegen=python_parse_file(path))
    assert not diff


@pytest.mark.parametrize("inp", ['r"""some long lines\nmore lines\n"""', 'r"some \\nlong lines"'])
def test_ast_strings(inp, unparse_diff):
    unparse_diff(inp)
