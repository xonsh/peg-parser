import unittest

from winnow_parser import parse_code


class TestExpressions(unittest.TestCase):
    def test_binop(self):
        code = "1 + 2\n"
        tree = parse_code(code)
        assert tree.body[0].value.op.__class__.__name__ == "Add"

    def test_comparison(self):
        code = "1 < 2\n"
        tree = parse_code(code)
        assert tree.body[0].value.ops[0].__class__.__name__ == "Lt"

    def test_call(self):
        code = "foo(1, a=2)\n"
        tree = parse_code(code)
        assert tree.body[0].value.func.id == "foo"
        assert len(tree.body[0].value.args) == 1
        assert len(tree.body[0].value.keywords) == 1

    def test_attribute(self):
        code = "foo.bar\n"
        tree = parse_code(code)
        assert tree.body[0].value.value.id == "foo"
        assert tree.body[0].value.attr == "bar"

    def test_lambda(self):
        code = "lambda x: x+1\n"
        tree = parse_code(code)
        assert tree.body[0].value.args.args[0].arg == "x"


if __name__ == "__main__":
    unittest.main()
