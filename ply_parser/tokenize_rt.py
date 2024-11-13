"""The code is copied from

https://github.com/asottile/tokenize-rt/blob/c2bb6f32371408c0490e817b6dd48285d804e36d/tokenize_rt.py
"""

import io
import keyword
import re
from collections.abc import Generator, Iterable, Sequence
from re import Pattern
from typing import NamedTuple

from xonsh_parser import tokenize

ESCAPED_NL = "ESCAPED_NL"
UNIMPORTANT_WS = "UNIMPORTANT_WS"
NON_CODING_TOKENS = frozenset(("COMMENT", ESCAPED_NL, "NL", UNIMPORTANT_WS))


class Offset(NamedTuple):
    line: int | None = None
    utf8_byte_offset: int | None = None


class Token(NamedTuple):
    name: str
    src: str
    line: int | None = None
    utf8_byte_offset: int | None = None

    @property
    def offset(self) -> Offset:
        return Offset(self.line, self.utf8_byte_offset)


_string_re = re.compile("^([^'\"]*)(.*)$", re.DOTALL)
_escaped_nl_re = re.compile(r"\\(\n|\r\n|\r)")


def _re_partition(regex: Pattern[str], s: str) -> tuple[str, str, str]:
    match = regex.search(s)
    if match:
        return s[: match.start()], s[slice(*match.span())], s[match.end() :]
    else:
        return (s, "", "")


def src_to_tokens(src: str) -> list[Token]:
    tokenize_target = io.StringIO(src)
    lines = ("",) + tuple(tokenize_target)

    tokenize_target.seek(0)

    tokens = []
    last_line = 1
    last_col = 0
    end_offset = 0

    gen = tokenize.generate_tokens(tokenize_target.readline)
    for tok_type, tok_text, (sline, scol), (eline, ecol), line in gen:
        if sline > last_line:
            newtok = lines[last_line][last_col:]
            for lineno in range(last_line + 1, sline):
                newtok += lines[lineno]
            if scol > 0:
                newtok += lines[sline][:scol]

            # a multiline unimportant whitespace may contain escaped newlines
            while _escaped_nl_re.search(newtok):
                ws, nl, newtok = _re_partition(_escaped_nl_re, newtok)
                if ws:
                    tokens.append(
                        Token(UNIMPORTANT_WS, ws, last_line, end_offset),
                    )
                    end_offset += len(ws.encode())
                tokens.append(Token(ESCAPED_NL, nl, last_line, end_offset))
                end_offset = 0
                last_line += 1
            if newtok:
                tokens.append(Token(UNIMPORTANT_WS, newtok, sline, 0))
                end_offset = len(newtok.encode())
            else:
                end_offset = 0

        elif scol > last_col:
            newtok = line[last_col:scol]
            tokens.append(Token(UNIMPORTANT_WS, newtok, sline, end_offset))
            end_offset += len(newtok.encode())

        tok_name = tokenize.tok_name[tok_type]
        tokens.append(Token(tok_name, tok_text, sline, end_offset))
        last_line, last_col = eline, ecol
        if sline != eline:
            end_offset = len(lines[last_line][:last_col].encode())
        else:
            end_offset += len(tok_text.encode())

    return tokens


def tokens_to_src(tokens: Iterable[Token]) -> str:
    return "".join(tok.src for tok in tokens)


def reversed_enumerate(
    tokens: Sequence[Token],
) -> Generator[tuple[int, Token], None, None]:
    for i in reversed(range(len(tokens))):
        yield i, tokens[i]


def parse_string_literal(src: str) -> tuple[str, str]:
    """parse a string literal's source into (prefix, string)"""
    match = _string_re.match(src)
    assert match is not None
    return match.group(1), match.group(2)


def rfind_string_parts(tokens: Sequence[Token], i: int) -> tuple[int, ...]:
    """find the indicies of the string parts of a (joined) string literal

    - `i` should start at the end of the string literal
    - returns `()` (an empty tuple) for things which are not string literals
    """
    ret = []
    depth = 0
    for i in range(i, -1, -1):  # noqa
        token = tokens[i]
        if token.name == "STRING":
            ret.append(i)
        elif token.name in NON_CODING_TOKENS:
            pass
        elif token.src == ")":
            depth += 1
        elif depth and token.src == "(":
            depth -= 1
            # if we closed the paren(s) make sure it was a parenthesized string
            # and not actually a call
            if depth == 0:
                for j in range(i - 1, -1, -1):
                    tok = tokens[j]
                    if tok.name in NON_CODING_TOKENS:
                        pass
                    # this was actually a call and not a parenthesized string
                    elif tok.src in {"]", ")"} or (tok.name == "NAME" and tok.src not in keyword.kwlist):
                        return ()
                    else:
                        break
                break
        elif depth:  # it looked like a string but wasn't
            return ()
        else:
            break
    return tuple(reversed(ret))
