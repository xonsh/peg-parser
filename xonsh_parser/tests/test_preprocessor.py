from pathlib import Path

import pytest

from xonsh_parser.parsers.preprocessor import translex


def get_pairs(dir_name: str):
    directory = Path(__file__).parent / dir_name
    for file in directory.iterdir():
        if file.suffix == ".py":
            with file.open() as f:
                case_count = 1
                while True:
                    left, right = f.readline().strip("# "), f.readline()
                    if not left or not right:
                        break

                    yield pytest.param(left, right, id=f"{file.stem}-{case_count}")
                    f.readline()  # advance to next case
                    case_count += 1


def pytest_generate_tests(metafunc):
    """load src and expected from fixtures directory"""
    if metafunc.definition.name == "test_line_items":
        metafunc.parametrize("src, expected", list(get_pairs("line-items")))


def test_line_items(src, expected):
    assert translex(src) == expected
