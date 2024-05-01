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
from codecs import BOM_UTF8, lookup
from typing import Callable, NamedTuple

from peg_parser.parser.token import (
    COMMENT,
    DEDENT,
    ENCODING,
    ENDMARKER,
    ENVNAME,
    ERRORTOKEN,
    EXACT_TOKEN_TYPES,
    INDENT,
    NAME,
    NEWLINE,
    NL,
    NUMBER,
    OP,
    STRING,
    tok_name,
)

cookie_re = re.compile(r"^[ \t\f]*#.*?coding[:=][ \t]*([-\w.]+)", re.ASCII)
blank_re = re.compile(rb"^[ \t\f]*(?:[#\r\n]|$)", re.ASCII)


class TokenInfo(NamedTuple):
    type: int
    string: str
    start: tuple[int, int]
    end: tuple[int, int]
    line: str

    def __repr__(self):
        annotated_type = "%d (%s)" % (self.type, tok_name[self.type])
        return f"TokenInfo(type={annotated_type}, string={self.string!r}, start={self.start!r}, end={self.end!r}, line={self.line!r})"

    @property
    def exact_type(self):
        if self.type == OP and self.string in EXACT_TOKEN_TYPES:
            return EXACT_TOKEN_TYPES[self.string]
        else:
            return self.type


def capname(name: str, pattern: str) -> str:
    return f"(?P<{name}>{pattern})"


def group(*choices, name="", **named_choices):
    choices += tuple(f"(?P<{name}>{pattern})" for name, pattern in named_choices.items())
    pattern = "(" + "|".join(choices) + ")"
    if name:
        pattern = capname(name, pattern)
    return pattern


def any(*choices):
    return group(*choices) + "*"


def maybe(*choices):
    return group(*choices) + "?"


# Note: we use unicode matching for names ("\w") but ascii matching for
# number literals.
Whitespace = r"[ \f\t]*"
Comment = r"#[^\r\n]*"
Ignore = Whitespace + any(r"\\\r?\n" + Whitespace) + maybe(Comment)
Name = r"\w+"
EnvName = r"\$\w+"

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
        for t in _itertools.permutations(prefix):
            # create a list with upper and lower versions of each
            #  character
            for u in _itertools.product(*[(c, c.upper()) for c in t]):
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
Triple = capname("pre1", StringPrefix) + group("'''", '"""', name="tquote")
# Single-line ' or " string.
String = group(StringPrefix + r"'[^\n'\\]*(?:\\.[^\n'\\]*)*'", StringPrefix + r'"[^\n"\\]*(?:\\.[^\n"\\]*)*"')

# Sorting in reverse order puts the long operators before their prefixes.
# Otherwise if = came before ==, == would get recognized as two instances
# of =.
Special = group(*map(re.escape, sorted(EXACT_TOKEN_TYPES, reverse=True)))
Funny = group(r"\r?\n", Special)

PlainToken = group(Number, Funny, String, Name)
Token = Ignore + PlainToken

# First (or only) line of ' or " string.
ContStr = capname("pre2", StringPrefix) + group(
    r"'[^\n'\\]*(?:\\.[^\n'\\]*)*" + group("'", r"\\\r?\n"),
    r'"[^\n"\\]*(?:\\.[^\n"\\]*)*' + group('"', r"\\\r?\n"),
    name="Str2",
)
PseudoExtras = group(End=r"\\\r?\n|\Z", Comment=Comment, Triple=Triple)
PseudoToken = Whitespace + group(
    PseudoExtras, Number=Number, Funny=Funny, ContStr=ContStr, Name=Name, EnvName=EnvName
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


class StopTokenizing(Exception):
    pass


def _get_normal_name(orig_enc):
    """Imitates get_normal_name in tokenizer.c."""
    # Only care about the first 12 characters.
    enc = orig_enc[:12].lower().replace("_", "-")
    if enc == "utf-8" or enc.startswith("utf-8-"):
        return "utf-8"
    if enc in ("latin-1", "iso-8859-1", "iso-latin-1") or enc.startswith(
        ("latin-1-", "iso-8859-1-", "iso-latin-1-")
    ):
        return "iso-8859-1"
    return orig_enc


def detect_encoding(readline: Callable[[], bytes]) -> tuple[str, list[bytes]]:
    """
    The detect_encoding() function is used to detect the encoding that should
    be used to decode a Python source file.  It requires one argument, readline,
    in the same way as the tokenize() generator.

    It will call readline a maximum of twice, and return the encoding used
    (as a string) and a list of any lines (left as bytes) it has read in.

    It detects the encoding from the presence of a utf-8 bom or an encoding
    cookie as specified in pep-0263.  If both a bom and a cookie are present,
    but disagree, a SyntaxError will be raised.  If the encoding cookie is an
    invalid charset, raise a SyntaxError.  Note that if a utf-8 bom is found,
    'utf-8-sig' is returned.

    If no encoding is specified, then the default of 'utf-8' will be returned.
    """
    try:
        filename = readline.__self__.name  # type: ignore
    except AttributeError:
        filename = None
    bom_found = False
    encoding = None
    default = "utf-8"

    def read_or_stop():
        try:
            return readline()
        except StopIteration:
            return b""

    def find_cookie(line):
        try:
            # Decode as UTF-8. Either the line is an encoding declaration,
            # in which case it should be pure ASCII, or it must be UTF-8
            # per default encoding.
            line_string = line.decode("utf-8")
        except UnicodeDecodeError:
            msg = "invalid or missing encoding declaration"
            if filename is not None:
                msg = f"{msg} for {filename!r}"
            raise SyntaxError(msg)

        match = cookie_re.match(line_string)
        if not match:
            return None
        encoding = _get_normal_name(match.group(1))
        try:
            lookup(encoding)
        except LookupError:
            # This behaviour mimics the Python interpreter
            if filename is None:
                msg = "unknown encoding: " + encoding
            else:
                msg = f"unknown encoding for {filename!r}: {encoding}"
            raise SyntaxError(msg)

        if bom_found:
            if encoding != "utf-8":
                # This behaviour mimics the Python interpreter
                if filename is None:
                    msg = "encoding problem: utf-8"
                else:
                    msg = f"encoding problem for {filename!r}: utf-8"
                raise SyntaxError(msg)
            encoding += "-sig"
        return encoding

    first = read_or_stop()
    if first.startswith(BOM_UTF8):
        bom_found = True
        first = first[3:]
        default = "utf-8-sig"
    if not first:
        return default, []

    encoding = find_cookie(first)
    if encoding:
        return encoding, [first]
    if not blank_re.match(first):
        return default, [first]

    second = read_or_stop()
    if not second:
        return default, [first]

    encoding = find_cookie(second)
    if encoding:
        return encoding, [first, second]

    return default, [first, second]


def tokenize(readline):
    """
    The tokenize() generator requires one argument, readline, which
    must be a callable object which provides the same interface as the
    readline() method of built-in file objects.  Each call to the function
    should return one line of input as bytes.  Alternatively, readline
    can be a callable function terminating with StopIteration:
        readline = open(myfile, 'rb').__next__  # Example of alternate readline

    The generator produces 5-tuples with these members: the token type; the
    token string; a 2-tuple (srow, scol) of ints specifying the row and
    column where the token begins in the source; a 2-tuple (erow, ecol) of
    ints specifying the row and column where the token ends in the source;
    and the line on which the token was found.  The line passed is the
    physical line.

    The first token sequence will always be an ENCODING token
    which tells you which encoding was used to decode the bytes stream.
    """
    encoding, consumed = detect_encoding(readline)
    empty = _itertools.repeat(b"")
    rl_gen = _itertools.chain(consumed, iter(readline, b""), empty)
    return _tokenize(rl_gen.__next__, encoding)


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

    def move_next_line(self, readline, encoding):
        self.last_line = self.line
        try:
            # We capture the value of the line variable here because
            # readline uses the empty string '' to signal end of input,
            # hence `line` itself will always be overwritten at the end
            # of this loop.
            self.line = readline()
        except StopIteration:
            return b""
        if encoding is not None:
            self.line = self.line.decode(encoding)
        self.lnum += 1
        self.pos = 0
        self.max = len(self.line)


class ContStrState:
    def __init__(self):
        self.contstr = ""
        self.needcont = 0
        self.contline = None
        self.strstart = None
        self.endprog = None

    def reset(self):
        self.contline = None
        self.contstr = None

    def reset_cont(self):
        self.reset()
        self.needcont = 0

    def join(self, state: TokenizerState):
        self.contstr += state.line
        self.contline += state.line


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
                COMMENT,
                comment_token,
                (state.lnum, state.pos),
                (state.lnum, state.pos + len(comment_token)),
                state.line,
            )
            state.pos += len(comment_token)

        yield TokenInfo(
            NL, state.line[state.pos :], (state.lnum, state.pos), (state.lnum, len(state.line)), state.line
        )
        return True  # continue

    if column > state.indents[-1]:  # count indents or dedents
        state.indents.append(column)
        yield TokenInfo(INDENT, state.line[: state.pos], (state.lnum, 0), (state.lnum, state.pos), state.line)
    while column < state.indents[-1]:
        if column not in state.indents:
            raise IndentationError(
                "unindent does not match any outer indentation level",
                ("<tokenize>", state.lnum, state.pos, state.line),
            )
        state.indents = state.indents[:-1]

        yield TokenInfo(DEDENT, "", (state.lnum, state.pos), (state.lnum, state.pos), state.line)


def next_psuedo_matches(pseudomatch, state: TokenizerState, cont_str: ContStrState):
    start, end = pseudomatch.span(1)
    spos, epos, state.pos = (state.lnum, start), (state.lnum, end), end
    if start == end:
        return True  # continue
    cap_groups: dict[str, str | None] = pseudomatch.groupdict()
    token, initial = state.line[start:end], state.line[start]

    if (
        cap_groups.get("Number")  # ordinary number
        or (initial == "." and token != "." and token != "...")
    ):
        yield TokenInfo(NUMBER, token, spos, epos, state.line)
    elif initial in "\r\n":
        if state.parenlev > 0:
            yield TokenInfo(NL, token, spos, epos, state.line)
        else:
            yield TokenInfo(NEWLINE, token, spos, epos, state.line)

    elif cap_groups.get("Comment"):
        assert not token.endswith("\n")
        yield TokenInfo(COMMENT, token, spos, epos, state.line)

    elif cap_groups.get("Triple"):
        cont_str.endprog = _compile(endpats[cap_groups["tquote"] or "'''"])
        endmatch = cont_str.endprog.match(state.line, state.pos)
        if endmatch:  # all on one line
            state.pos = endmatch.end(0)
            token = state.line[start : state.pos]
            yield TokenInfo(STRING, token, spos, (state.lnum, state.pos), state.line)
        else:
            cont_str.strstart = (state.lnum, start)  # multiple lines
            cont_str.contstr = state.line[start:]
            cont_str.contline = state.line
            return False

    # Also note that single quote checking must come after
    #  triple quote checking (above).
    elif cap_groups.get("ContStr"):
        if token[-1] == "\n":  # continued string
            cont_str.strstart = (state.lnum, start)
            # check for matching quote
            quote = (cap_groups["Str2"] or "")[0]
            cont_str.endprog = _compile(endpats[quote])
            cont_str.contstr, cont_str.needcont = state.line[start:], 1
            cont_str.contline = state.line
            return False
        else:  # ordinary string
            yield TokenInfo(STRING, token, spos, epos, state.line)

    elif cap_groups.get("Name"):  # ordinary name
        yield TokenInfo(NAME, token, spos, epos, state.line)
    elif cap_groups.get("EnvName"):  # ordinary name
        yield TokenInfo(ENVNAME, token, spos, epos, state.line)
    elif initial == "\\":  # continued stmt
        state.continued = True
    else:
        if initial in "([{":
            state.parenlev += 1
        elif initial in ")]}":
            state.parenlev -= 1
        yield TokenInfo(OP, token, spos, epos, state.line)


def _tokenize(readline, encoding):
    state = TokenizerState()
    cont_str = ContStrState()

    if encoding is not None:
        if encoding == "utf-8-sig":
            # BOM will already have been stripped.
            encoding = "utf-8"
        yield TokenInfo(ENCODING, encoding, (0, 0), (0, 0), "")

    while True:  # loop over lines in stream
        state.move_next_line(readline, encoding)

        if cont_str.contstr:  # continued string
            if not state.line:
                raise TokenError("EOF in multi-line string", cont_str.strstart)
            endmatch = cont_str.endprog.match(state.line)
            if endmatch:
                state.pos = end = endmatch.end(0)
                yield TokenInfo(
                    STRING,
                    cont_str.contstr + state.line[:end],
                    cont_str.strstart,
                    (state.lnum, end),
                    cont_str.contline + state.line,
                )
                cont_str.reset_cont()
            elif cont_str.needcont and state.line[-2:] != "\\\n" and state.line[-3:] != "\\\r\n":
                yield TokenInfo(
                    ERRORTOKEN,
                    cont_str.contstr + state.line,
                    cont_str.strstart,
                    (state.lnum, len(state.line)),
                    cont_str.contline,
                )
                cont_str.reset()
                continue
            else:
                cont_str.join(state)
                continue

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
                    ERRORTOKEN,
                    state.line[state.pos],
                    (state.lnum, state.pos),
                    (state.lnum, state.pos + 1),
                    state.line,
                )
                state.pos += 1

    # Add an implicit NEWLINE if the input doesn't end in one
    if state.last_line and state.last_line[-1] not in "\r\n" and not state.last_line.strip().startswith("#"):
        yield TokenInfo(
            NEWLINE,
            "",
            (state.lnum - 1, len(state.last_line)),
            (state.lnum - 1, len(state.last_line) + 1),
            "",
        )
    for _ in state.indents[1:]:  # pop remaining indent levels
        yield TokenInfo(DEDENT, "", (state.lnum, 0), (state.lnum, 0), "")
    yield TokenInfo(ENDMARKER, "", (state.lnum, 0), (state.lnum, 0), "")


def generate_tokens(readline):
    """Tokenize a source reading Python code as unicode strings.

    This has the same API as tokenize(), except that it expects the *readline*
    callable to return str objects instead of bytes.
    """
    if isinstance(readline, str):
        readline = io.StringIO(readline).readline
    return _tokenize(readline, None)
