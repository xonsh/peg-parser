from __future__ import annotations

from typing import TYPE_CHECKING, Final, NewType

from .tokenize import Token, TokenInfo

if TYPE_CHECKING:
    from collections.abc import Iterator

Mark = NewType("Mark", int)


class Tokenizer:
    """Caching wrapper for the tokenize module"""

    _tokens: list[TokenInfo]

    def __init__(self, tokengen: Iterator[TokenInfo], *, path: str = "", verbose: bool = False):
        self._tokengen = tokengen
        self._tokens = []
        self._index = Mark(0)
        self._verbose = verbose
        self._lines: dict[int, str] = {}
        self._path = path
        self._stack: list[TokenInfo] = []  # temporarily hold tokens
        self._call_macro = False
        self._with_macro = False
        self._proc_macro = False
        self._end_parens: Final = {
            ")": "(",
            "]": "[",
            "}": "{",
        }
        if verbose:
            self.report(False, False)

    def getnext(self) -> TokenInfo:
        """Return the next token and updates the index."""
        cached = self._index != len(self._tokens)
        tok = self.peek()
        self._index = Mark(self._index + Mark(1))
        if self._verbose:
            self.report(cached, False)
        return tok

    def peek(self) -> TokenInfo:
        """Return the next token *without* updating the index."""
        while self._index == len(self._tokens):
            if self._with_macro:
                tok = self.consume_with_macro_params()
            elif self._call_macro:
                tok = self.consume_macro_params()
            elif self._stack:
                tok = self._stack.pop()
            else:
                tok = next(self._tokengen)
            if self.is_blank(tok):
                continue

            self._tokens.append(tok)
            if not self._path and tok.start[0] not in self._lines:
                self._lines[tok.start[0]] = tok.line
        return self._tokens[self._index]

    def is_blank(self, tok: TokenInfo) -> bool:
        if self._proc_macro and tok.type == Token.WS:
            return False
        if tok.type in {Token.NL, Token.COMMENT, Token.WS}:
            return True
        if tok.type == Token.ERRORTOKEN and tok.string.isspace():
            return True
        if tok.type == Token.NEWLINE and self._tokens and self._tokens[-1].type == Token.NEWLINE:
            return True
        return False

    def consume_macro_params(self) -> TokenInfo:  # noqa: C901, PLR0912
        # loop until we get , or ) without consuming it
        start: tuple[int, int] | None = None
        end: tuple[int, int] | None = None
        paren_level: list[str] = []
        # join strings while handling whitespace
        string = ""
        line = ""
        while True:
            tok = next(self._tokengen)
            if tok.type == Token.OP and tok.string[-1] in "([{":  # push paren level
                paren_level.append(tok.string[-1])
            if paren_level:
                if (tok.type == Token.OP) and (opener := self._end_parens.get(tok.string)):
                    if paren_level[-1] == opener:
                        paren_level.pop()
                    else:
                        raise SyntaxError(f"Unmatched closing paren {tok.string} at {tok.start}")
            else:
                if tok.is_exact_type(")"):
                    self._stack.append(tok)
                    self._call_macro = False
                    break

                if tok.is_exact_type(","):
                    break
            end = tok.end
            if start is None:
                start = tok.start
                line = tok.line
                string = tok.string
            else:
                string += tok.string

        if (not string) and self._stack:
            # empty params
            return self._stack.pop()

        assert start is not None
        assert end is not None
        if not string.strip():
            return TokenInfo(Token.WS, string, start, end, line)
        return TokenInfo(Token.MACRO_PARAM, string, start, end, line)

    def consume_with_macro_params(self) -> TokenInfo:  # noqa: C901
        """loop until we get INDENT-DEDENT or NL"""

        is_indented: bool = False
        indent = 0
        lines = {}
        start = end = self._tokens[-1].end
        for idx, tok in enumerate(self._tokengen):
            if (idx == 0) and tok.type == Token.NEWLINE:
                continue
            elif tok.type == Token.INDENT:
                if (not is_indented) and (idx == 1):
                    is_indented = True
                    continue
                indent += 1
            elif tok.type == Token.DEDENT:
                if indent:
                    indent -= 1
                    continue
                else:
                    self._with_macro = False
                    break
            elif tok.type == Token.NEWLINE:
                if not is_indented:
                    break
                elif not tok.string:
                    # empty new line added by the tokenizer
                    continue

            # update captured lines
            if tok.start[0] not in lines:
                lines[tok.start[0]] = tok.line if is_indented else tok.line[tok.start[1] :]

        string = "".join(lines.values())
        if is_indented:
            import textwrap

            string = textwrap.dedent(string)
        return TokenInfo(Token.MACRO_PARAM, string, start, end, string)

    def diagnose(self) -> TokenInfo:
        if not self._tokens:
            self.getnext()
        return self._tokens[-1]

    def get_last_non_whitespace_token(self) -> TokenInfo:
        idx = self._index - 1
        while idx >= 0:
            tok = self._tokens[idx]
            if tok.type not in {Token.ENDMARKER, Token.NEWLINE, Token.DEDENT, Token.INDENT}:
                return tok
            idx -= 1
        return self._tokens[-1]

    def get_lines(self, line_numbers: list[int]) -> list[str]:
        """Retrieve source lines corresponding to line numbers."""
        if self._lines:
            lines = self._lines
        else:
            n = len(line_numbers)
            lines = {}
            count = 0
            seen = 0
            with open(self._path) as f:
                for line in f:
                    count += 1
                    if count in line_numbers:
                        seen += 1
                        lines[count] = line
                        if seen == n:
                            break

        return [lines[n] for n in line_numbers]

    def mark(self) -> Mark:
        return self._index

    def reset(self, index: Mark) -> None:
        if index == self._index:
            return
        assert 0 <= index <= len(self._tokens), (index, len(self._tokens))
        old_index = self._index
        self._index = index
        if self._verbose:
            self.report(True, index < old_index)

    def report(self, cached: bool, back: bool) -> None:
        if back:
            fill = "-" * self._index + "-"
        elif cached:
            fill = "-" * self._index + ">"
        else:
            fill = "-" * self._index + "*"
        if self._index == 0:
            print(f"{fill} (Bof)")
        else:
            tok = self._tokens[self._index - 1]
            short = "%-25.25s" % f"{tok.start[0]}.{tok.start[1]}: {tok.type!r}:{tok.string!r}"
            print(f"{fill} {short}")
