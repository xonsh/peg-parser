import unittest

from winnow_parser import parse_code


class TestAtoms(unittest.TestCase):
    def test_name(self):
        code = "abc\n"
        tree = parse_code(code)
        assert tree.body[0].value.id == "abc"

    def test_number(self):
        code = "123\n"
        tree = parse_code(code)
        assert tree.body[0].value.value == 123

    def test_string(self):
        code = "'hello'\n"
        tree = parse_code(code)
        assert tree.body[0].value.value == "hello"

    def test_list(self):
        code = "[1, 2]\n"
        tree = parse_code(code)
        assert len(tree.body[0].value.elts) == 2

    def test_dict(self):
        code = "{'a': 1}\n"
        tree = parse_code(code)
        assert len(tree.body[0].value.keys) == 1


if __name__ == "__main__":
    unittest.main()
