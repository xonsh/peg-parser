"""Test identifying unsupported syntax construction in older Python versions.

Note that we can request the parser to apply stricter bounds on the parsing but
not broader since we would not be able to generate the proper ast nodes.

"""

import io
import tokenize

import pytest

from pegen.tokenizer import Tokenizer


# match 3.10
@pytest.mark.parametrize("source", ["match a:\n\tcase 1:\n\t\tpass", "match a", "match a:\ncase b"])
def test_match_statement(python_parser_cls, source):
    temp = io.StringIO(source)
    tokengen = tokenize.generate_tokens(temp.readline)
    tokenizer = Tokenizer(tokengen, verbose=False)
    pp = python_parser_cls(tokenizer, py_version=(3, 9))
    with pytest.raises(SyntaxError) as e:
        pp.parse("file")

    assert "Pattern matching is" in e.exconly()


# try except * 3.11
@pytest.mark.parametrize("source", ["try:\n\ta = 1\nexcept *ValueError:\n\tpass"])
def test_exceptgroup_statement(python_parser_cls, source):
    temp = io.StringIO(source)
    tokengen = tokenize.generate_tokens(temp.readline)
    tokenizer = Tokenizer(tokengen, verbose=False)
    pp = python_parser_cls(tokenizer, py_version=(3, 10))
    with pytest.raises(SyntaxError) as e:
        pp.parse("file")

    assert "Exception groups are" in e.exconly()


# type alias and type vars 3.12
@pytest.mark.parametrize("source", ["type T = int", "type T[U] = tuple[U]"])
def test_type_params_statement(python_parser_cls, source):
    temp = io.StringIO(source)
    tokengen = tokenize.generate_tokens(temp.readline)
    tokenizer = Tokenizer(tokengen, verbose=False)
    pp = python_parser_cls(tokenizer, py_version=(3, 11))
    with pytest.raises(SyntaxError) as e:
        pp.parse("file")

    assert "Type statement is" in e.exconly() or "Type parameter lists are" in e.exconly()


# type alias and type vars 3.12
@pytest.mark.parametrize("source", ["def f[T]():\n\tpass", "async def f[T]():\n\tpass"])
def test_generic_function_statement(python_parser_cls, source):
    temp = io.StringIO(source)
    tokengen = tokenize.generate_tokens(temp.readline)
    tokenizer = Tokenizer(tokengen, verbose=False)
    pp = python_parser_cls(tokenizer, py_version=(3, 11))
    with pytest.raises(SyntaxError) as e:
        pp.parse("file")

    assert "Type parameter lists are" in e.exconly()


# generic classes 3.12
@pytest.mark.parametrize("source", ["class A[T]:\n\tpass"])
def test_generic_class_statement(python_parser_cls, source):
    temp = io.StringIO(source)
    tokengen = tokenize.generate_tokens(temp.readline)
    tokenizer = Tokenizer(tokengen, verbose=False)
    pp = python_parser_cls(tokenizer, py_version=(3, 11))
    with pytest.raises(SyntaxError) as e:
        pp.parse("file")

    assert "Type parameter lists are" in e.exconly()
