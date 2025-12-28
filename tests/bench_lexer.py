import io
from pathlib import Path

import pytest


@pytest.mark.benchmark(group="large-file")
def test_winnow_lexer(benchmark):
    from winnow_parser import tokenize

    file = Path(__file__).parent.parent / "peg_parser" / "parser.py"
    content = file.read_text()
    benchmark(tokenize, content)


def get_tokens(inp: str) -> list:
    from peg_parser import tokenize
    from peg_parser.tokenizer import Tokenizer

    tokenizer = Tokenizer(io.StringIO(inp).readline)

    def _iter():
        while True:
            tok = tokenizer.getnext()
            yield tok
            if tok.type == tokenize.Token.ENDMARKER:
                break

    return list(_iter())


@pytest.mark.benchmark(group="large-file")
def test_python_tokenizer(benchmark):
    file = Path(__file__).parent.parent / "peg_parser" / "parser.py"
    content = file.read_text()
    benchmark(get_tokens, content)
