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
import functools
import io
import itertools as _itertools
import re
from enum import IntEnum, StrEnum, auto
from typing import NamedTuple

cookie_re = re.compile(r"^[ \t\f]*#.*?coding[:=][ \t]*([-\w.]+)", re.ASCII)
blank_re = re.compile(rb"^[ \t\f]*(?:[#\r\n]|$)", re.ASCII)


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


def capname(**kwargs) -> str:
    text = ""
    for name, pattern in kwargs.items():
        text += f"(?P<{name}>{pattern})"
    return text


def group(*choices, name="", **named_choices):
    choices += tuple(f"(?P<{name}>{pattern})" for name, pattern in named_choices.items())
    pattern = "(" + "|".join(choices) + ")"
    if name:
        pattern = capname(**{name: pattern})
    return pattern


def any(*choices):
    return group(*choices) + "*"


def maybe(*choices):
    return group(*choices) + "?"


# Note: we use unicode matching for names ("\w") but ascii matching for
# number literals.
Whitespace = r"[ \f\t]*"
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
StringPrefix = group(*_all_string_prefixes())

# Tail end of ' string.
Single = r"[^'\\]*(?:\\.[^'\\]*)*'"
# Tail end of " string.
Double = r'[^"\\]*(?:\\.[^"\\]*)*"'
# Tail end of ''' string.
Single3 = r"[^'\\]*(?:(?:\\.|'(?!''))[^'\\]*)*'''"
# Tail end of """ string.
Double3 = r'[^"\\]*(?:(?:\\.|"(?!""))[^"\\]*)*"""'
Triple = capname(pre1=StringPrefix) + group("'''", '"""', name="tquote")
# Single-line ' or " string.
String = group(StringPrefix + r"'[^\n'\\]*(?:\\.[^\n'\\]*)*'", StringPrefix + r'"[^\n"\\]*(?:\\.[^\n"\\]*)*"')

# Sorting in reverse order puts the long operators before their prefixes.
# Otherwise if = came before ==, == would get recognized as two instances
# of =.
Special = group(*map(re.escape, sorted([t.value for t in ExactToken], reverse=True)))
Funny = group(r"\r?\n", Special=Special)

# First (or only) line of ' or " string.
ContStr = capname(pre2=StringPrefix) + group(
    r"'[^\n'\\]*(?:\\.[^\n'\\]*)*" + group("'", r"\\\r?\n"),
    r'"[^\n"\\]*(?:\\.[^\n"\\]*)*' + group('"', r"\\\r?\n"),
    name="Str2",
)
SearchPath = capname(search_pre=r"([rgpf]+|@\w*)?") + capname(search_path=r"`([^\n`\\]*(?:\\.[^\n`\\]*)*)`")
PseudoExtras = group(End=r"\\\r?\n|\Z", Comment=Comment, Triple=Triple, SearchPath=SearchPath)
PseudoToken = capname(ws=Whitespace) + group(
    PseudoExtras, Number=Number, Funny=Funny, ContStr=ContStr, Name=Name
)

# For a given string prefix plus quotes, endpats maps it to a regex
#  to match the remainder of that string. _prefix can be empty, for
#  a normal single or triple quoted string (with no prefix).
endpats = {
    "'": Single,
    '"': Double,
    "'''": Single3,
    '"""': Double3,
}

tabsize = 8


class TokenError(Exception):
    pass


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


class ContStrState:
    def __init__(self):
        self.contstr = ""
        self.needcont = False
        self.contline = None  # str
        self.strstart = None  # tuple[int, int]
        self.endprog = None  # re.Pattern[str]

    def reset(self):
        self.contline = None
        self.contstr = None

    def reset_cont(self):
        self.reset()
        self.needcont = False

    def join(self, state: TokenizerState):
        self.contstr += state.line
        self.contline += state.line

    def start(self, state: TokenizerState, start: int):
        self.strstart = (state.lnum, start)  # multiple lines
        self.contstr = state.line[start:]
        self.contline = state.line


def next_cont_string(cont_str: ContStrState, state: TokenizerState):
    if not state.line:
        raise TokenError("EOF in multi-line string", cont_str.strstart)
    endmatch = cont_str.endprog.match(state.line)
    if endmatch:
        state.pos = end = endmatch.end(0)
        yield TokenInfo(
            Token.STRING,
            cont_str.contstr + state.line[:end],
            cont_str.strstart,
            (state.lnum, end),
            cont_str.contline + state.line,
        )
        cont_str.reset_cont()
    elif cont_str.needcont and state.line[-2:] != "\\\n" and state.line[-3:] != "\\\r\n":
        yield TokenInfo(
            Token.ERRORTOKEN,
            cont_str.contstr + state.line,
            cont_str.strstart,
            (state.lnum, len(state.line)),
            cont_str.contline,
        )
        cont_str.reset()
        return True
    else:
        cont_str.join(state)
        return True


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


def next_psuedo_matches(pseudomatch, state: TokenizerState, cont_str: ContStrState):
    if whitespace := pseudomatch.group("ws"):
        start, end = pseudomatch.span("ws")
        yield TokenInfo(Token.WS, whitespace, (state.lnum, start), (state.lnum, end), state.line)
    start, end = pseudomatch.span(2)
    spos, epos, state.pos = (state.lnum, start), (state.lnum, end), end
    if start == end:
        return True  # continue
    token, initial = state.line[start:end], state.line[start]

    if (
        pseudomatch.group("Number")  # ordinary number
        or (initial == "." and token != "." and token != "...")
    ):
        yield TokenInfo(Token.NUMBER, token, spos, epos, state.line)
    elif initial in "\r\n":
        if state.parenlev > 0:
            yield TokenInfo(Token.NL, token, spos, epos, state.line)
        else:
            yield TokenInfo(Token.NEWLINE, token, spos, epos, state.line)

    elif pseudomatch.group("Comment"):
        assert not token.endswith("\n")
        yield TokenInfo(Token.COMMENT, token, spos, epos, state.line)

    elif pseudomatch.group("Triple"):
        cont_str.endprog = _compile(endpats[pseudomatch.group("tquote") or "'''"])
        endmatch = cont_str.endprog.match(state.line, state.pos)
        if endmatch:  # all on one line
            state.pos = endmatch.end(0)
            token = state.line[start : state.pos]
            yield TokenInfo(Token.STRING, token, spos, (state.lnum, state.pos), state.line)
        else:
            cont_str.start(state, start)
            return False

    # Also note that single quote checking must come after
    #  triple quote checking (above).
    elif pseudomatch.group("ContStr"):
        if token[-1] == "\n":  # continued string
            cont_str.start(state, start)
            # check for matching quote
            quote = (pseudomatch.group("Str2") or "")[0]
            cont_str.endprog = _compile(endpats[quote])
            cont_str.needcont = True
            return False
        else:  # ordinary string
            yield TokenInfo(Token.STRING, token, spos, epos, state.line)
    elif pseudomatch.group("SearchPath"):
        yield TokenInfo(Token.SEARCH_PATH, token, spos, epos, state.line)
    elif pseudomatch.group("Name"):  # ordinary name
        yield TokenInfo(Token.NAME, token, spos, epos, state.line)
    elif pseudomatch.group("Special"):
        if token[-1] in "([{":
            state.parenlev += 1
        elif token in ")]}":
            state.parenlev -= 1
        yield TokenInfo(Token.OP, token, spos, epos, state.line)
    elif initial == "\\":  # continued stmt
        state.continued = True
    else:  # Funny other than Special
        raise TokenError(f"Bad token: {token!r} at line {state.lnum}", spos)
        # yield TokenInfo(t.OP, token, spos, epos, state.line)


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


def _tokenize(readline):
    state = TokenizerState()
    cont_str = ContStrState()

    while True:  # loop over lines in stream
        state.move_next_line(readline)

        if cont_str.contstr:  # continued string
            loop_action = yield from next_cont_string(cont_str, state)
            if loop_action is True:
                continue
            elif loop_action is False:
                break

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

        while state.pos < state.max:
            pseudomatch = _compile(PseudoToken).match(state.line, state.pos)
            if pseudomatch:  # scan for tokens
                loop_action = yield from next_psuedo_matches(pseudomatch, state, cont_str)
                if loop_action is True:
                    continue
                elif loop_action is False:
                    break
            else:
                yield TokenInfo(
                    Token.ERRORTOKEN,
                    state.line[state.pos],
                    (state.lnum, state.pos),
                    (state.lnum, state.pos + 1),
                    state.line,
                )
                state.pos += 1

    yield from next_end_tokens(state)


def generate_tokens(readline):
    """Tokenize a source reading Python code as unicode strings.

    This has the same API as tokenize(), except that it expects the *readline*
    callable to return str objects instead of bytes.
    """
    if isinstance(readline, str):
        readline = io.StringIO(readline).readline
    return _tokenize(readline)
