"""Test pure Python parser against cpython parser."""

import ast
import difflib
import sys
from pathlib import Path

import pytest


def unparse_diff(**trees: ast.AST):
    orig_name, pp_name = trees.keys()
    original, pp_ast = trees.values()
    left = ast.unparse(original)
    right = ast.unparse(pp_ast)
    return "\n".join(difflib.unified_diff(left.split("\n"), right.split("\n"), orig_name, pp_name))


def dump_diff(
    attrs=True,
    **trees: ast.AST,
):
    kwargs = {"include_attributes": attrs, "indent": "  "}
    orig_name, pp_name = trees.keys()
    original, pp_ast = trees.values()
    o = ast.dump(original, **kwargs)
    p = ast.dump(pp_ast, **kwargs)
    return "\n".join(difflib.unified_diff(o.split("\n"), p.split("\n"), orig_name, pp_name))


marks = {"marks": pytest.mark.xfail} if sys.version_info < (3, 12) else {}


@pytest.mark.parametrize(
    "filename",
    [
        "advanced_decorators.py",
        pytest.param("assignment.py", **marks),
        "async.py",
        "call.py",
        "comprehensions.py",
        "expressions.py",
        pytest.param("fstrings.py", **marks),
        "function_def.py",
        "imports.py",
        "lambdas.py",
        "multi_statement_per_line.py",
        "no_newline_at_end_of_file.py",
        "no_newline_at_end_of_file_with_comment.py",
        pytest.param("pattern_matching.py", **marks),
        "simple_decorators.py",
        "statements.py",
        "with_statement_multi_items.py",
        pytest.param(
            "try_except_group.py",
            marks=pytest.mark.skipif(
                sys.version_info <= (3, 11), reason="except* allowed only in Python 3.11+"
            ),
        ),
        pytest.param(
            "type_params.py",
            marks=pytest.mark.skipif(
                sys.version_info <= (3, 12),
                reason="type declarations allowed only in Python 3.12+",
            ),
        ),
    ],
)
def test_pure_python_parsing(python_parse_file, parse_str, filename):
    path = Path(__file__).parent / "data" / filename
    with open(path) as f:
        source = f.read()

    for part in source.split("\n\n\n"):
        original = ast.parse(part)

        pp_ast = parse_str(part, mode="exec")

        if diff := dump_diff(cpython=original, pegen=pp_ast):
            if src_diff := unparse_diff(original=original, pp_ast=pp_ast):
                print("Source diff")
                print(src_diff)
            else:
                print("Unparsed sources are the same")
            print("AST diff")
            print(diff)

        assert not diff, "mismatch in generated AST"

    diff = dump_diff(cpython=ast.parse(source), pegen=python_parse_file(path))
    assert not diff


@pytest.mark.parametrize(
    "inp",
    [
        'r"""some long lines\nmore lines\n"""',
        'r"some \\nlong lines"',
    ],
)
def test_ast_strings(inp, unparse_diff):
    unparse_diff(inp)
