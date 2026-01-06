import unittest

from winnow_parser import parse_code


class TestStatements(unittest.TestCase):
    def test_assignment(self):
        code = "x = 1\n"
        tree = parse_code(code)
        assert tree.body[0].targets[0].id == "x"
        assert tree.body[0].value.value == 1

    def test_if(self):
        code = "if True: pass\n"
        tree = parse_code(code)
        assert tree.body[0].test.value

    def test_for(self):
        code = "for x in y: pass\n"
        tree = parse_code(code)
        assert tree.body[0].target.id == "x"

    def test_func_def(self):
        code = "def foo(): pass\n"
        tree = parse_code(code)
        assert tree.body[0].name == "foo"

    def test_class_def(self):
        code = "class Foo: pass\n"
        tree = parse_code(code)
        assert tree.body[0].name == "Foo"

    def test_import(self):
        code = "import sys\n"
        tree = parse_code(code)
        assert tree.body[0].names[0].name == "sys"

    def test_try(self):
        code = "try: pass\nexcept: pass\n"
        tree = parse_code(code)
        assert len(tree.body[0].handlers) == 1

    def test_global(self):
        code = "global x, y\n"
        tree = parse_code(code)
        # Verify it parsed (no syntax error) and is Global node
        assert tree.body[0].__class__.__name__ == "Global"
        assert tree.body[0].names == ["x", "y"]


if __name__ == "__main__":
    unittest.main()
