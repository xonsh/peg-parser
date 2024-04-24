import ast
import io
import os
import tokenize
from collections.abc import Iterator
from typing import (
    Any,
    Callable,
    Literal,
    Optional,
    Union,
)

from pegen.tokenizer import Tokenizer


def parse_file(
    path: str,
    py_version: Optional[tuple] = None,
    token_stream_factory: Optional[Callable[[Callable[[], str]], Iterator[tokenize.TokenInfo]]] = None,
    verbose: bool = False,
) -> ast.Module:
    """Parse a file."""
    with open(path) as f:
        tok_stream = (
            token_stream_factory(f.readline) if token_stream_factory else tokenize.generate_tokens(f.readline)
        )
        tokenizer = Tokenizer(tok_stream, verbose=verbose, path=path)
        parser = Parser(
            tokenizer,
            verbose=verbose,
            filename=os.path.basename(path),
            py_version=py_version,
        )
        return parser.parse("file")


def parse_string(
    source: str,
    mode: Union[Literal["eval"], Literal["exec"]],
    py_version: Optional[tuple] = None,
    token_stream_factory: Optional[Callable[[Callable[[], str]], Iterator[tokenize.TokenInfo]]] = None,
    verbose: bool = False,
) -> Any:
    """Parse a string."""
    tok_stream = (
        token_stream_factory(io.StringIO(source).readline)
        if token_stream_factory
        else tokenize.generate_tokens(io.StringIO(source).readline)
    )
    tokenizer = Tokenizer(tok_stream, verbose=verbose)
    parser = Parser(tokenizer, verbose=verbose, py_version=py_version)
    return parser.parse(mode if mode == "eval" else "file")
