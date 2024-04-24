""" "Conftest for pure python parser."""

from pathlib import Path

import pytest


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
