""" "Conftest for pure python parser."""

from pathlib import Path

import pytest


def nodes_equal(x, y):
    import ast

    __tracebackhide__ = True
    assert type(x) == type(y), f"Ast nodes do not have the same type: '{type(x)}' != '{type(y)}' "
    if isinstance(x, ast.Constant):
        assert x.value == y.value, (
            f"Constant ast nodes do not have the same value: " f"{repr(x.value)} != {repr(y.value)}"
        )
    if isinstance(x, (ast.Expr, ast.FunctionDef, ast.ClassDef)):
        assert x.lineno == y.lineno, f"Ast nodes do not have the same line number : {x.lineno} != {y.lineno}"
        assert (
            x.col_offset == y.col_offset
        ), f"Ast nodes do not have the same column offset number : {x.col_offset} != {y.col_offset}"
    for (xname, xval), (yname, yval) in zip(ast.iter_fields(x), ast.iter_fields(y)):
        assert (
            xname == yname
        ), f"Ast nodes fields differ : {xname} (of type {type(xval)}) != {yname} (of type {type(yval)})"
        assert type(xval) == type(
            yval
        ), f"Ast nodes fields differ : {xname} (of type {type(xval)}) != {yname} (of type {type(yval)})"
    for xchild, ychild in zip(ast.iter_child_nodes(x), ast.iter_child_nodes(y)):
        assert nodes_equal(xchild, ychild), "Ast node children differs"
    return True


def build_parser(name: str):
    from pegen.build import build_parser
    from pegen.utils import generate_parser, import_file

    grammar_path = Path(__file__).parent.parent / "parser/full.gram"
    source_path = grammar_path.with_name("parser.py")
    if not source_path.exists():
        grammar = build_parser(str(grammar_path))[0]
        generate_parser(grammar, str(source_path))
    mod = import_file("xsh_parser", str(source_path))
    return getattr(mod, name)


@pytest.fixture(scope="session")
def python_parser_cls():
    return build_parser("XonshParser")


@pytest.fixture(scope="session")
def python_parse_file():
    return build_parser("parse_file")


@pytest.fixture(scope="session")
def python_parse_str():
    return build_parser("parse_string")


@pytest.fixture(scope="session")
def parse_str():
    return build_parser("parse_string")


@pytest.fixture
def check_ast(parse_str):
    import ast

    def factory(inp: str, mode="eval", verbose=False):
        # expect a Python AST
        exp = ast.parse(inp, mode=mode)
        # observe something from xonsh
        obs = parse_str(inp, mode=mode, verbose=verbose)
        # Check that they are equal
        assert nodes_equal(exp, obs)

    return factory


@pytest.fixture
def unparse_diff(parse_str):
    def factory(text: str, right: str | None = None, mode="eval"):
        import ast

        try:
            left = parse_str(text, mode=mode)
        except Exception as e:
            print("Parsing failed:")
            print("Source is:")
            print(text)
            print("Verbose output of the parser:")
            parse_str(text, verbose=True, mode=mode)
            raise e
        left = ast.unparse(left)
        if right is None:
            right = ast.parse(text).body[0]
            right = ast.unparse(right)
        assert left == right

    return factory
