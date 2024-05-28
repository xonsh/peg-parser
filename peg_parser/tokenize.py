"""Tokenization help for Python programs.

tokenize(readline) is a generator that breaks a stream of bytes into
Python tokens.  It decodes the bytes according to PEP-0263 for
determining source file encoding.

It accepts a readline-like method which is called repeatedly to get the
next line of input (or b"" for EOF).  It generates 5-tuples with these
members:

    the token type (see token.py)
    the token (a string)
    the starting (row, column) indices of the token (a 2-tuple of ints)
    the ending (row, column) indices of the token (a 2-tuple of ints)
    the original line (string)

It is designed to match the working of the Python tokenizer exactly, except
that it produces COMMENT tokens for comments and gives type OP for all
operators.  Additionally, all token lists start with an ENCODING token
which tells you which encoding was used to decode the bytes stream.
"""

from __future__ import annotations

__author__ = "Ka-Ping Yee <ping@lfw.org>"
__credits__ = (
    "GvR, ESR, Tim Peters, Thomas Wouters, Fred Drake, "
    "Skip Montanaro, Raymond Hettinger, Trent Nelson, "
    "Michael Foord"
)

import dataclasses
import functools
import io
import itertools as _itertools
import re
from enum import IntEnum, StrEnum, auto
from typing import Final, NamedTuple


class ExactToken(StrEnum):
    NOTEQUAL = "!="
    PERCENT = "%"
    PERCENTEQUAL = "%="
    AMPER = "&"
    AMPEREQUAL = "&="
    LPAR = "("
    RPAR = ")"
    STAR = "*"
    DOUBLESTAR = "**"
    DOUBLESTAREQUAL = "**="
    STAREQUAL = "*="
    PLUS = "+"
    PLUSEQUAL = "+="
    COMMA = ","
    MINUS = "-"
    MINEQUAL = "-="
    RARROW = "->"
    DOT = "."
    ELLIPSIS = "..."
    SLASH = "/"
    DOUBLESLASH = "//"
    DOUBLESLASHEQUAL = "//="
    SLASHEQUAL = "/="
    COLON = ":"
    COLONEQUAL = ":="
    SEMI = ";"
    LESS = "<"
    LEFTSHIFT = "<<"
    LEFTSHIFTEQUAL = "<<="
    LESSEQUAL = "<="
    EQUAL = "="
    EQEQUAL = "=="
    GREATER = ">"
    GREATEREQUAL = ">="
    RIGHTSHIFT = ">>"
    RIGHTSHIFTEQUAL = ">>="
    AT = "@"
    ATEQUAL = "@="
    LSQB = "["
    RSQB = "]"
    CIRCUMFLEX = "^"
    CIRCUMFLEXEQUAL = "^="
    LBRACE = "{"
    VBAR = "|"
    VBAREQUAL = "|="
    RBRACE = "}"
    TILDE = "~"
    BANG = "!"

    # xonsh specific tokens
    DOLLAR = "$"
    QUESTION = "?"
    DOUBLE_QUESTION = "??"
    DOUBLE_PIPE = "||"
    DOUBLE_AMPER = "&&"
    AT_LPAREN = "@("
    BANG_LPAREN = "!("
    BANG_LBRACKET = "!["
    DOLLAR_LPAREN = "$("
    DOLLAR_LBRACKET = "$["
    DOLLAR_LBRACE = "${"
    AT_DOLLAR_LPAREN = "@$("


class Token(IntEnum):
    """Tokens"""

    ENDMARKER = auto()
    NAME = auto()
    NUMBER = auto()
    STRING = auto()
    NEWLINE = auto()
    INDENT = auto()
    DEDENT = auto()
    OP = auto()  # all exact tokens
    AWAIT = auto()
    ASYNC = auto()
    TYPE_IGNORE = auto()
    TYPE_COMMENT = auto()
    SOFT_KEYWORD = auto()
    FSTRING_START = auto()
    FSTRING_MIDDLE = auto()
    FSTRING_END = auto()
    ERRORTOKEN = auto()
    COMMENT = auto()
    NL = auto()
    ENCODING = auto()

    # xonsh specific tokens starting at 80
    SEARCH_PATH = auto()
    MACRO_PARAM = auto()
    WS = auto()


class TokenInfo(NamedTuple):
    type: Token
    string: str
    start: tuple[int, int]
    end: tuple[int, int]
    line: str

    def is_exact_type(self, typ: ExactToken) -> bool:
        return self.type == Token.OP and self.string == typ.value

    def loc_start(self):
        """helper method to construct AST node location"""
        return {
            "lineno": self.start[0],
            "col_offset": self.start[1],
        }

    def loc_end(self):
        return {
            "end_lineno": self.end[0],
            "end_col_offset": self.end[1],
        }

    def loc(self):
        """helper method to construct AST node location"""
        return {
            **self.loc_start(),
            **self.loc_end(),
        }

    def is_next_to(self, prev: TokenInfo) -> bool:
        """check if there is no whitespace between the end of this token and the start of the other token"""
        return prev.end == self.start


def capname(name: str, pattern: str) -> str:
    return f"(?P<{name}>{pattern})"


def choice(*choices, **named_choices) -> str:
    choices += tuple(capname(name, pattern) for name, pattern in named_choices.items())
    return "|".join(choices)


def group(*choices, name="", **named_choices):
    pattern = "(" + choice(*choices, **named_choices) + ")"
    if name:
        pattern = capname(name, pattern)
    return pattern


def maybe(*choices):
    return group(*choices) + "?"


# Note: we use unicode matching for names ("\w") but ascii matching for
# number literals.
Whitespace = r"[ \f\t]+"
Comment = r"#[^\r\n]*"
Name = r"\w+"

Hexnumber = r"0[xX](?:_?[0-9a-fA-F])+"
Binnumber = r"0[bB](?:_?[01])+"
Octnumber = r"0[oO](?:_?[0-7])+"
Decnumber = r"(?:0(?:_?0)*|[1-9](?:_?[0-9])*)"
Intnumber = group(Hexnumber, Binnumber, Octnumber, Decnumber)
Exponent = r"[eE][-+]?[0-9](?:_?[0-9])*"
Pointfloat = group(r"[0-9](?:_?[0-9])*\.(?:[0-9](?:_?[0-9])*)?", r"\.[0-9](?:_?[0-9])*") + maybe(Exponent)
Expfloat = r"[0-9](?:_?[0-9])*" + Exponent
Floatnumber = group(Pointfloat, Expfloat)
Imagnumber = group(r"[0-9](?:_?[0-9])*[jJ]", Floatnumber + r"[jJ]")
Number = group(Imagnumber, Floatnumber, Intnumber)


# Return the empty string, plus all of the valid string prefixes.
def _all_string_prefixes():
    # The valid string prefixes. Only contain the lower case versions,
    #  and don't contain any permutations (include 'fr', but not
    #  'rf'). The various permutations will be generated.
    _valid_string_prefixes = ["b", "r", "u", "f", "br", "fr", "p", "pr", "pf"]
    # if we add binary f-strings, add: ['fb', 'fbr']
    result = {""}
    for prefix in _valid_string_prefixes:
        for perm in _itertools.permutations(prefix):
            # create a list with upper and lower versions of each
            #  character
            for u in _itertools.product(*[(c, c.upper()) for c in perm]):
                result.add("".join(u))
    return result


@functools.lru_cache
def _compile(expr):
    return re.compile(expr, re.UNICODE)


# Note that since _all_string_prefixes includes the empty string,
#  StringPrefix can be the empty string (making it optional).
StringStart = group(*_all_string_prefixes(), name="StringPrefix") + group(
    group("'''", '"""', name="TripleQt"), group('"', "'", name="SingleQt"), name="Quote"
)

# Sorting in reverse order puts the long operators before their prefixes.
# Otherwise if = came before ==, == would get recognized as two instances
# of =.
Special = group(*map(re.escape, sorted([t.value for t in ExactToken], reverse=True)))

SearchPath = r"([rgpf]+|@\w*)?`([^\n`\\]*(?:\\.[^\n`\\]*)*)`"
PseudoToken = choice(
    Comment=Comment,
    StringStart=StringStart,
    End=r"\\\r?\n|\Z",
    NL=r"\r?\n",
    SearchPath=SearchPath,
    Number=Number,
    Special=Special,
    Name=Name,
    ws=Whitespace,
)

# For a given string prefix plus quotes, endpats maps it to a regex
#  to match the remainder of that string. _prefix can be empty, for
#  a normal single or triple quoted string (with no prefix).
endpats: Final = {
    "'": r"(?:[^'\\]|\\.)*'",
    '"': r'(?:[^"\\]|\\.)*"',
    "'''": r"(?:[^'\\]|\\.|'(?!''))*'''",
    '"""': r'(?:[^"\\]|\\.|"(?!""))*"""',
}
StartLBrace = r".*?(?=\{(?!\{)){"
EndRBrace = r".*?(?=\}(?!\}))}"

tabsize = 8


class TokenError(Exception):
    pass


class ModeMiddle(NamedTuple):
    # in the string portion of an f-string (outside braces)
    parenlevel: int


class ModeInBraces(NamedTuple):
    parenlevel: int


class ModeInColon(NamedTuple):
    """in the format specifier ({:*})"""

    parenlevel: int


Mode = ModeMiddle | ModeInBraces | ModeInColon


class TokenizerState:
    def __init__(self):
        self.lnum = 0
        self.parenlev = 0
        self.continued = False
        self.indents = [0]
        self.last_line = ""
        self.line = ""
        self.pos = 0
        self.max = 0
        self.end_progs: list[EndProg] = []

    def move_next_line(self, readline):
        self.last_line = self.line
        try:
            # We capture the value of the line variable here because
            # readline uses the empty string '' to signal end of input,
            # hence `line` itself will always be overwritten at the end
            # of this loop.
            self.line = readline()
        except StopIteration:
            self.line = ""
        self.lnum += 1
        self.pos = 0
        self.max = len(self.line)

    def __repr__(self):
        return f"<TokenizerState: {self.pos} in {self.line}>"

    def add_prog(self, start: int, end: int, **kwargs) -> None:
        self.end_progs.append(
            EndProg(text=self.line[start:end], contline=self.line, start=(self.lnum, start), **kwargs)
        )

    def prog_token(self, end: int, tok: Token):
        endprog = self.end_progs[-1]
        endprog.join(self, end)
        self.pos = end
        epos = (self.lnum, end)
        return TokenInfo(tok, endprog.text, endprog.start, epos, endprog.contline)

    def match(self, pattern: str | re.Pattern):
        pattern = _compile(pattern) if isinstance(pattern, str) else pattern
        return pattern.match(self.line, self.pos)

    def in_mode(self, mode: type[Mode]) -> bool:
        return bool(self.end_progs) and isinstance(self.end_progs[-1].mode, mode)

    def in_braces(self) -> bool:
        return self.in_mode(ModeInBraces)

    def in_fstring(self) -> bool:
        return self.in_mode(ModeMiddle)

    def in_colon(self) -> bool:
        return self.in_mode(ModeInColon)

    def pop_mode(self, end: tuple[int, int] | None = None):
        prog = self.end_progs.pop()
        if self.end_progs and end:
            self.end_progs[-1].reset(end)
        return prog

    def at_parenlev(self) -> bool:
        return (self.end_progs[-1].mode is not None) and self.end_progs[-1].mode.parenlevel == self.parenlev


@dataclasses.dataclass(slots=True)
class EndProg:
    mode: Mode | None = None
    pattern: re.Pattern | str = ""  # end pattern
    text: str = ""
    contline: str = ""  # str
    start: tuple[int, int] = (0, 0)
    quote: str = ""

    def join(self, state: TokenizerState, end=0):
        if state.pos == 0:
            self.text += state.line
            self.contline += state.line
        else:
            self.text += state.line[state.pos : end or len(state.line)]

    def reset(self, start: tuple[int, int]):
        self.start = start
        self.text = ""


def next_statement(state: TokenizerState):
    if not state.line:
        return False  # break parent loop
    column = 0
    while state.pos < state.max:  # measure leading whitespace
        if state.line[state.pos] == " ":
            column += 1
        elif state.line[state.pos] == "\t":
            column = (column // tabsize + 1) * tabsize
        elif state.line[state.pos] == "\f":
            column = 0
        else:
            break
        state.pos += 1

    if state.pos == state.max:
        return False  # break parent loop

    if state.line[state.pos] in "#\r\n":  # skip comments or blank lines
        if state.line[state.pos] == "#":
            comment_token = state.line[state.pos :].rstrip("\r\n")
            yield TokenInfo(
                Token.COMMENT,
                comment_token,
                (state.lnum, state.pos),
                (state.lnum, state.pos + len(comment_token)),
                state.line,
            )
            state.pos += len(comment_token)

        yield TokenInfo(
            Token.NL,
            state.line[state.pos :],
            (state.lnum, state.pos),
            (state.lnum, len(state.line)),
            state.line,
        )
        return True  # continue

    if column > state.indents[-1]:  # count indents or dedents
        state.indents.append(column)
        yield TokenInfo(
            Token.INDENT, state.line[: state.pos], (state.lnum, 0), (state.lnum, state.pos), state.line
        )
    while column < state.indents[-1]:
        if column not in state.indents:
            raise IndentationError(
                "unindent does not match any outer indentation level",
                ("<tokenize>", state.lnum, state.pos, state.line),
            )
        state.indents = state.indents[:-1]

        yield TokenInfo(Token.DEDENT, "", (state.lnum, state.pos), (state.lnum, state.pos), state.line)


def next_psuedo_matches(state: TokenizerState):
    if state.pos == state.max or state.in_fstring():
        return
    match = state.match(PseudoToken)
    if not match:
        return
    start, end = match.span(match.lastgroup)
    spos, epos, state.pos = (state.lnum, start), (state.lnum, end), end
    token = state.line[start:end]

    if match.lastgroup == "StringStart":
        quote = match.group("Quote") or '"'
        if "f" in token.lower():
            token_type = Token.FSTRING_START
            pattern = choice(LBrace=StartLBrace, End=endpats[quote])
            state.add_prog(end, end, pattern=pattern, quote=quote, mode=ModeMiddle(state.parenlev))
        else:
            pattern = endpats[quote]
            state.add_prog(start, end, pattern=pattern, quote=quote)
            return
    elif tok := {
        "ws": Token.WS,
        "Comment": Token.COMMENT,
        "SearchPath": Token.SEARCH_PATH,
        "Name": Token.NAME,
    }.get(match.lastgroup):
        token_type = tok
    elif match.lastgroup == "Number" or (token[0] == "." and token not in (".", "...")):
        token_type = Token.NUMBER
    elif match.lastgroup == "NL":
        token_type = Token.NL if state.parenlev > 0 else Token.NEWLINE
    elif match.lastgroup == "Special":
        if token[-1] in "([{":
            state.parenlev += 1
        elif token in ")]}":
            if state.in_braces() and state.at_parenlev():
                state.pop_mode((state.lnum, end))
            state.parenlev -= 1
        elif token == ":" and state.in_braces() and state.at_parenlev():
            state.add_prog(start + 1, end, mode=ModeInColon(state.parenlev), pattern=choice(RBrace=EndRBrace))
        token_type = Token.OP
    elif match.lastgroup == "End":  # // continuation
        state.continued = True
        return
    else:
        raise TokenError(f"Bad token: {token!r} at line {state.lnum}", spos)

    # Yield Token if Found
    if token_type:
        return TokenInfo(token_type, token, spos, epos, state.line)


def next_end_tokens(state: TokenizerState):
    # Add an implicit NEWLINE if the input doesn't end in one
    if state.last_line and state.last_line[-1] not in "\r\n" and not state.last_line.strip().startswith("#"):
        yield TokenInfo(
            Token.NEWLINE,
            "",
            (state.lnum - 1, len(state.last_line)),
            (state.lnum - 1, len(state.last_line) + 1),
            "",
        )
    for _ in state.indents[1:]:  # pop remaining indent levels
        yield TokenInfo(Token.DEDENT, "", (state.lnum, 0), (state.lnum, 0), "")
    yield TokenInfo(Token.ENDMARKER, "", (state.lnum, 0), (state.lnum, 0), "")


def handle_end_progs(state: TokenizerState):
    if not state.end_progs:
        return
    if state.pos == 0 and not state.line:
        raise TokenError("EOF in multi-line string", state.end_progs[-1].start)

    if state.in_braces():
        return

    endprog = state.end_progs[-1]
    if state.in_fstring() or state.in_colon():
        if endmatch := state.match(endprog.pattern):
            start, end = endmatch.span(endmatch.lastgroup)
            if endmatch.lastgroup == "End":  # quote match
                middle_end = end - len(endprog.quote)
                if middle_end > state.pos:
                    yield state.prog_token(middle_end, Token.FSTRING_MIDDLE)
                yield TokenInfo(
                    Token.FSTRING_END,
                    endprog.quote,
                    start=(state.lnum, state.pos),
                    end=(state.lnum, end),
                    line=state.line,
                )
                state.pop_mode()
            else:  # "{" or "}"
                middle_end = end - 1
                if middle_end > state.pos:  # has buffer
                    yield state.prog_token(middle_end, Token.FSTRING_MIDDLE)
                if endmatch.lastgroup == "LBrace":
                    yield TokenInfo(
                        Token.OP,
                        "{",
                        start=(state.lnum, state.pos),
                        end=(state.lnum, end),
                        line=state.line,
                    )
                    state.parenlev += 1
                    state.add_prog(end, end, mode=ModeInBraces(state.parenlev))
                else:  # rbrace
                    yield TokenInfo(
                        Token.OP,
                        "}",
                        start=(state.lnum, state.pos),
                        end=(state.lnum, end),
                        line=state.line,
                    )
                    state.parenlev -= 1
                    state.pop_mode()  # in-colon
                    state.pop_mode((state.lnum, end))  # in braces

            state.pos = end
            return
        else:
            raise TokenError(f"Expected {endprog.quote} inside f-string", (state.lnum, state.pos))

    if endmatch := state.match(endprog.pattern):  # all on one line
        end = endmatch.end(0)
        yield state.prog_token(end, Token.STRING)
        state.pop_mode()
        return

    if (
        (state.pos == 0)  # called at start of the line
        or (
            len(endprog.quote) == 3
            or (
                state.line[-2:] == "\\\n"  # single quote should have line continuation at the end
            )
            or (state.line[-3:] == "\\\r\n")
        )
    ):
        endprog.join(state)
        state.pos = state.max
    else:
        raise TokenError("Invalid string quotes")


def _tokenize(readline):
    state = TokenizerState()

    while True:  # loop over lines in stream
        state.move_next_line(readline)

        if state.end_progs:
            yield from handle_end_progs(state)

        elif state.parenlev == 0 and not state.continued:  # new statement
            loop_action = yield from next_statement(state)
            if loop_action is True:
                continue
            elif loop_action is False:
                break
            # None has no effect

        else:  # continued statement
            if not state.line:
                raise TokenError("EOF in multi-line statement", (state.lnum, 0))
            state.continued = False

        pos = state.pos
        while state.pos < state.max:
            yield from handle_end_progs(state)
            if token := next_psuedo_matches(state):
                yield token
            elif pos == state.pos:
                yield TokenInfo(
                    Token.ERRORTOKEN,
                    state.line[state.pos],
                    (state.lnum, state.pos),
                    (state.lnum, state.pos + 1),
                    state.line,
                )
                state.pos += 1
                pos = state.pos

    yield from next_end_tokens(state)


def generate_tokens(readline):
    """Tokenize a source reading Python code as unicode strings.

    This has the same API as tokenize(), except that it expects the *readline*
    callable to return str objects instead of bytes.
    """
    if isinstance(readline, str):
        readline = io.StringIO(readline).readline
    return _tokenize(readline)
