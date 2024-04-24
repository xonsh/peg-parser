"""Test identifying unsupported syntax construction in older Python versions.

Note that we can request the parser to apply stricter bounds on the parsing but
not broader since we would not be able to generate the proper ast nodes.

"""

import io
import tokenize

import pytest

from pegen.tokenizer import Tokenizer


# generic decorators 3.9
@pytest.mark.parametrize("source", ["@f[1]\ndef f():\n\tpass"])
def test_generic_decorators(python_parser_cls, source):
    temp = io.StringIO(source)
    tokengen = tokenize.generate_tokens(temp.readline)
    tokenizer = Tokenizer(tokengen, verbose=False)
    pp = python_parser_cls(tokenizer, py_version=(3, 8))
    with pytest.raises(SyntaxError) as e:
        pp.parse("file")

    assert "Generic decorator are" in e.exconly()


# parenthesized with items 3.9
@pytest.mark.parametrize("source", ["with (a, b):\n\tpass"])
def test_parenthesized_with_items(python_parser_cls, source):
    temp = io.StringIO(source)
    tokengen = tokenize.generate_tokens(temp.readline)
    tokenizer = Tokenizer(tokengen, verbose=False)
    pp = python_parser_cls(tokenizer, py_version=(3, 8))
    with pytest.raises(SyntaxError) as e:
        pp.parse("file")

    assert "Parenthesized with items" in e.exconly()


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
