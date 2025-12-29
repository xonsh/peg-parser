from __future__ import annotations

from typing import TYPE_CHECKING, Final, NewType

if TYPE_CHECKING:
    from collections.abc import Callable

from winnow_parser import Token, tokenize


class TokenInfo:
    """A wrapper class that can represent both Rust TokInfo and synthesized tokens."""

    __slots__ = ("end", "start", "string", "type")

    def __init__(self, typ: Token, string: str, start: tuple[int, int], end: tuple[int, int]):
        self.type = typ
        self.string = string
        self.start = start
        self.end = end

    def is_exact_type(self, typ: str) -> bool:
        return self.type == Token.OP and self.string == typ

    def loc_start(self):
        return {"lineno": self.start[0], "col_offset": self.start[1]}

    def loc_end(self):
        return {"end_lineno": self.end[0], "end_col_offset": self.end[1]}

    def loc(self):
        res = self.loc_start()
        res.update(self.loc_end())
        return res

    def __repr__(self):
        return (
            f"TokenInfo(type={self.type!r}, string={self.string!r}, start={self.start!r}, end={self.end!r})"
        )


Mark = NewType("Mark", int)


WS_TOKENS = (Token.ENDMARKER, Token.NEWLINE, Token.DEDENT, Token.INDENT)
SKIP_TOKENS = (Token.WS, Token.COMMENT, Token.NL)


class Tokenizer:
    """Caching wrapper for the tokenize module"""

    _tokens: list[TokenInfo]

    def __init__(
        self,
        readline: Callable[[], str],
        *,
        path: str = "",
        verbose: bool = False,
    ):
        self._readline = readline
        self._tokens = []
        self._index = Mark(0)
        self._verbose = verbose
        self._lines: dict[int, str] = {}
        self._path = path
        self._stack: list[TokenInfo] = []  # temporarily hold tokens
        self._call_macro = False
        self._with_macro = False
        self._proc_macro = False

        self._raw_tokens: list[TokenInfo] = []
        self._raw_index = 0

        # Read all source and tokenize
        source = ""
        while True:
            line = readline()
            if not line:
                break
            source += line
            self._lines[len(self._lines) + 1] = line
        self._raw_tokens = tokenize(source)

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
        try:
            tok = self.peek()
        except StopIteration:
            return self._tokens[-1]
        self._index = Mark(self._index + Mark(1))
        if self._verbose:
            self.report(cached, False)
        return tok

    def _fetch(self) -> TokenInfo:
        if self._raw_index >= len(self._raw_tokens):
            raise StopIteration
        tok = self._raw_tokens[self._raw_index]
        self._raw_index += 1
        return TokenInfo(tok.type, tok.string, tok.start, tok.end)

    def peek(self) -> TokenInfo:
        """Return the next token *without* updating the index."""
        try:
            while self._index == len(self._tokens):
                if self._with_macro:
                    tok = self.consume_with_macro_params()
                elif self._call_macro:
                    tok = self.consume_macro_params()
                elif self._stack:
                    tok = self._stack.pop()
                else:
                    tok = self._fetch()
                if self.is_blank(tok):
                    continue

                self._tokens.append(tok)
        except StopIteration:
            pass

        if self._index >= len(self._tokens):
            raise StopIteration
        return self._tokens[self._index]

    def is_blank(self, tok: TokenInfo) -> bool:
        if self._proc_macro and tok.type == Token.WS:
            return False
        if tok.type in SKIP_TOKENS:
            return True
        if tok.type == Token.ERRORTOKEN and tok.string.isspace():
            return True
        return bool(tok.type == Token.NEWLINE and self._tokens and self._tokens[-1].type == Token.NEWLINE)

    def consume_macro_params(self) -> TokenInfo:  # noqa: C901, PLR0912
        # loop until we get , or ) without consuming it
        start: tuple[int, int] | None = None
        end: tuple[int, int] | None = None
        paren_level: list[str] = []
        # join strings while handling whitespace
        string = ""
        while True:
            tok = self._fetch()
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
                # line = tok.line
                string = tok.string
            else:
                string += tok.string

        if (not string) and self._stack:
            # empty params
            return self._stack.pop()

        assert start is not None
        assert end is not None
        if not string.strip():
            return TokenInfo(Token.WS, string, start, end)
        return TokenInfo(Token.MACRO_PARAM, string, start, end)

    def consume_with_macro_params(self) -> TokenInfo:  # noqa: C901
        """loop until we get INDENT-DEDENT or NL"""

        is_indented: bool = False
        indent = 0
        lines = {}
        start = end = self._tokens[-1].end
        tok_idx = 0
        while True:
            tok = self._fetch()
            if (tok_idx == 0) and tok.type == Token.NEWLINE:
                tok_idx += 1
                continue
            elif tok.type == Token.INDENT:
                if (not is_indented) and tok_idx in {0, 1}:
                    is_indented = True
                    tok_idx += 1
                    continue
                indent += 1
            elif tok.type == Token.DEDENT:
                if indent:
                    indent -= 1
                    tok_idx += 1
                    continue
                else:
                    self._with_macro = False
                    break
            elif tok.type == Token.NEWLINE:
                if not is_indented:
                    break
                elif not tok.string:
                    # empty new line added by the tokenizer
                    tok_idx += 1
                    continue
            tok_idx += 1

            # update captured lines
            if tok.start[0] not in lines:
                line = self.get_lines([tok.start[0]])[0]
                lines[tok.start[0]] = line if is_indented else line[tok.start[1] :]

        string = "".join(lines.values())
        if is_indented:
            import textwrap

            string = textwrap.dedent(string)
        return TokenInfo(Token.MACRO_PARAM, string, start, end)

    def diagnose(self) -> TokenInfo:
        if not self._tokens:
            self.getnext()
        return self._tokens[-1]

    def get_last_non_whitespace_token(self) -> TokenInfo:
        idx = self._index - 1
        while idx >= 0:
            tok = self._tokens[idx]
            if tok.type not in WS_TOKENS:
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

        return [lines.get(n, "") for n in line_numbers]

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
            short = "%-25.25s" % f"{tok.start[0]}.{tok.start[1]}: {tok.type!r}:{tok.string!r}"  # noqa
            print(f"{fill} {short}")
