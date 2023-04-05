import ast

import pytest


def test_write_table(tmp_path):
    from xonsh_parser.parser import write_parser_table

    path = write_parser_table(output_path=tmp_path / "parser_table.jsonl")
    assert path.exists()


def test_basic(parser):
    expr = parser.parse("ls -alh")
    assert ast.dump(expr)


def test_invalid(parser):
    with pytest.raises(Exception):
        parser.parse("print(1")
