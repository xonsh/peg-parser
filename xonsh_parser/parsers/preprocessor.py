"""Instead of using a custom parser, we preprocess the input and then use the standard Python parser."""
import ast
from collections.abc import Iterable

from xonsh_parser import tokenize_rt


def _translex(src: str) -> Iterable[str]:
    """Translates xonsh tokens into Python source code"""
    seen_dollar_square = False
    square_brackets = 0
    for token in tokenize_rt.src_to_tokens(src):
        if token.name == "ATDOLLAR":
            yield "__xonsh__"
        elif token.name == "DOLLARNAME":
            yield f"__xonsh__.env['{token.src[1:]}']"
        elif token.src == "$(":
            yield "__xonsh__.subproc_captured_stdout("
        elif token.src == "!(":
            yield "__xonsh__.subproc_captured_object("
        elif token.src == "$[":
            yield "__xonsh__.subproc_uncaptured("
            seen_dollar_square = True
        elif token.src == "![":
            yield "__xonsh__.subproc_uncaptured_object("
            seen_dollar_square = True
        elif seen_dollar_square and token.src in {"[", "]"}:
            if token.src == "[":
                square_brackets += 1
                yield token.src
            elif token.src == "]":
                if square_brackets == 0:
                    yield ")"
                    seen_dollar_square = False
                else:
                    square_brackets -= 1
                    yield token.src
        else:
            yield token.src


def translex(src: str) -> str:
    """Translates xonsh source code into Python source code"""
    return "".join(_translex(src))


class Parser:
    def parse(self, src: str, filename="<code>", mode="exec", **_):
        """Returns an abstract syntax tree of xonsh code.

        Parameters
        ----------
        s : str
            The xonsh code.
        filename : str, optional
            Name of the file.
        mode : str, optional
            Execution mode, one of: exec, eval, or single.
        debug_level : str, optional
            Debugging level passed down to yacc.

        Returns
        -------
        tree : AST
        """
        src = translex(src)
        return ast.parse(src, filename, mode)
