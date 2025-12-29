import ast
from pathlib import Path

from winnow_parser import parse_code as parse


def test_parse_pass():
    code = Path(__file__).read_text()
    tree = parse(code)
    print(f"Parsed: {tree}")
    assert isinstance(tree, ast.Module)
    assert len(tree.body) == 1
    assert isinstance(tree.body[0], ast.Pass)
    print("SUCCESS: Parsed 'pass' correctly")


if __name__ == "__main__":
    test_parse_pass()
