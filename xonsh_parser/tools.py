import functools
import re

from .lazyasd import LazyDict, LazyObject, lazyobject
from .platform import ON_WINDOWS

_RE_STRING_START = "[bBprRuUf]*"
_RE_STRING_TRIPLE_DOUBLE = '"""'
_RE_STRING_TRIPLE_SINGLE = "'''"
_RE_STRING_DOUBLE = '"'
_RE_STRING_SINGLE = "'"
_STRINGS = (
    _RE_STRING_TRIPLE_DOUBLE,
    _RE_STRING_TRIPLE_SINGLE,
    _RE_STRING_DOUBLE,
    _RE_STRING_SINGLE,
)
RE_BEGIN_STRING = LazyObject(
    lambda: re.compile("(" + _RE_STRING_START + "(" + "|".join(_STRINGS) + "))"),
    globals(),
    "RE_BEGIN_STRING",
)
"""Regular expression matching the start of a string, including quotes and
leading characters (r, b, or u)"""

RE_STRING_START = LazyObject(lambda: re.compile(_RE_STRING_START), globals(), "RE_STRING_START")
"""Regular expression matching the characters before the quotes when starting a
string (r, b, or u, case insensitive)"""

RE_STRING_CONT = LazyDict(
    {
        '"': lambda: re.compile(r'((\\(.|\n))|([^"\\]))*'),
        "'": lambda: re.compile(r"((\\(.|\n))|([^'\\]))*"),
        '"""': lambda: re.compile(r'((\\(.|\n))|([^"\\])|("(?!""))|\n)*'),
        "'''": lambda: re.compile(r"((\\(.|\n))|([^'\\])|('(?!''))|\n)*"),
    },
    globals(),
    "RE_STRING_CONT",
)
"""Dictionary mapping starting quote sequences to regular expressions that
match the contents of a string beginning with those quotes (not including the
terminating quotes)"""

BEG_TOK_SKIPS = LazyObject(lambda: frozenset(["WS", "INDENT", "NOT", "LPAREN"]), globals(), "BEG_TOK_SKIPS")
END_TOK_TYPES = LazyObject(lambda: frozenset(["SEMI", "AND", "OR", "RPAREN"]), globals(), "END_TOK_TYPES")
RE_END_TOKS = LazyObject(lambda: re.compile(r"(;|and|\&\&|or|\|\||\))"), globals(), "RE_END_TOKS")
LPARENS = LazyObject(
    lambda: frozenset(["LPAREN", "AT_LPAREN", "BANG_LPAREN", "DOLLAR_LPAREN", "ATDOLLAR_LPAREN"]),
    globals(),
    "LPARENS",
)


@lazyobject
def RE_COMPLETE_STRING():
    ptrn = "^" + _RE_STRING_START + "(?P<quote>" + "|".join(_STRINGS) + ")" + ".*?(?P=quote)$"
    return re.compile(ptrn, re.DOTALL)


def get_line_continuation(is_interactive=False):
    """The line continuation characters used in subproc mode. In interactive
    mode on Windows the backslash must be preceded by a space. This is because
    paths on Windows may end in a backslash.
    """
    if ON_WINDOWS and is_interactive:
        return " \\"

    return "\\"


def _have_open_triple_quotes(s):
    if s.count('"""') % 2 == 1:
        open_triple = '"""'
    elif s.count("'''") % 2 == 1:
        open_triple = "'''"
    else:
        open_triple = False
    return open_triple


def get_logical_line(lines, idx):
    """Returns a single logical line (i.e. one without line continuations)
    from a list of lines.  This line should begin at index idx. This also
    returns the number of physical lines the logical line spans. The lines
    should not contain newlines
    """
    n = 1
    nlines = len(lines)
    linecont = get_line_continuation()
    while idx > 0 and lines[idx - 1].endswith(linecont):
        idx -= 1
    start = idx
    line = lines[idx]
    open_triple = _have_open_triple_quotes(line)
    while (line.endswith(linecont) or open_triple) and idx < nlines - 1:
        n += 1
        idx += 1
        if line.endswith(linecont):
            line = line[:-1] + lines[idx]
        else:
            line = line + "\n" + lines[idx]
        open_triple = _have_open_triple_quotes(line)
    return line, n, start


def check_quotes(s):
    """Checks a string to make sure that if it starts with quotes, it also
    ends with quotes.
    """
    starts_as_str = RE_BEGIN_STRING.match(s) is not None
    ends_as_str = s.endswith('"') or s.endswith("'")
    if not starts_as_str and not ends_as_str:
        ok = True
    elif starts_as_str and not ends_as_str:
        ok = False
    elif not starts_as_str and ends_as_str:
        ok = False
    else:
        m = RE_COMPLETE_STRING.match(s)
        ok = m is not None
    return ok


def check_bad_str_token(tok):
    """Checks if a token is a bad string."""
    if tok.type == "ERRORTOKEN" and tok.value == "EOF in multi-line string":
        return True
    elif isinstance(tok.value, str) and not check_quotes(tok.value):
        return True
    else:
        return False


def check_for_partial_string(x):
    """Returns the starting index (inclusive), ending index (exclusive), and
    starting quote string of the most recent Python string found in the input.

    check_for_partial_string(x) -> (startix, endix, quote)

    Parameters
    ----------
    x : str
        The string to be checked (representing a line of terminal input)

    Returns
    -------
    startix : int (or None)
        The index where the most recent Python string found started
        (inclusive), or None if no strings exist in the input

    endix : int (or None)
        The index where the most recent Python string found ended (exclusive),
        or None if no strings exist in the input OR if the input ended in the
        middle of a Python string

    quote : str (or None)
        A string containing the quote used to start the string (e.g., b", ",
        '''), or None if no string was found.
    """
    string_indices = []
    starting_quote = []
    current_index = 0
    match = re.search(RE_BEGIN_STRING, x)
    while match is not None:
        # add the start in
        start = match.start()
        quote = match.group(0)
        lenquote = len(quote)
        current_index += start
        # store the starting index of the string, as well as the
        # characters in the starting quotes (e.g., ", ', """, r", etc)
        string_indices.append(current_index)
        starting_quote.append(quote)
        # determine the string that should terminate this string
        ender = re.sub(RE_STRING_START, "", quote)
        x = x[start + lenquote :]
        current_index += lenquote
        # figure out what is inside the string
        continuer = RE_STRING_CONT[ender]
        contents = re.match(continuer, x)
        inside = contents.group(0)
        leninside = len(inside)
        current_index += contents.start() + leninside + len(ender)
        # if we are not at the end of the input string, add the ending index of
        # the string to string_indices
        if contents.end() < len(x):
            string_indices.append(current_index)
        x = x[leninside + len(ender) :]
        # find the next match
        match = re.search(RE_BEGIN_STRING, x)
    numquotes = len(string_indices)
    if numquotes == 0:
        return (None, None, None)
    elif numquotes % 2:
        return (string_indices[-1], None, starting_quote[-1])
    else:
        return (string_indices[-2], string_indices[-1], starting_quote[-1])


@functools.lru_cache
def STARTING_WHITESPACE_RE():
    return re.compile(r"^(\s*)")


def starting_whitespace(s):
    """Returns the whitespace at the start of a string"""
    return STARTING_WHITESPACE_RE().match(s).group(1)


def replace_logical_line(lines, logical, idx, n, is_interactive=False) -> None:
    """Replaces lines at idx that may end in line continuation with a logical
    line that spans n lines.
    """
    linecont = get_line_continuation(is_interactive)
    if n == 1:
        lines[idx] = logical
        return
    space = " "
    for i in range(idx, idx + n - 1):
        a = len(lines[i])
        b = logical.find(space, a - 1)
        if b < 0:
            # no space found
            lines[i] = logical
            logical = ""
        else:
            # found space to split on
            lines[i] = logical[:b] + linecont
            logical = logical[b:]
    lines[idx + n - 1] = logical


def find_next_break(lexer, line, mincol=0):
    """Returns the column number of the next logical break in subproc mode.
    This function may be useful in finding the maxcol argument of
    subproc_toks().
    """
    if mincol >= 1:
        line = line[mincol:]
    if RE_END_TOKS.search(line) is None:
        return None
    maxcol = None
    lparens = []
    lexer.input(line)
    for tok in lexer:
        if tok.type in LPARENS:
            lparens.append(tok.type)
        elif tok.type in END_TOK_TYPES:
            if _is_not_lparen_and_rparen(lparens, tok):
                lparens.pop()
            else:
                maxcol = tok.lexpos + mincol + 1
                break
        elif tok.type == "ERRORTOKEN" and ")" in tok.value:
            maxcol = tok.lexpos + mincol + 1
            break
        elif tok.type == "BANG":
            maxcol = mincol + len(line) + 1
            break
    return maxcol


def subproc_toks(lexer, line, mincol=-1, maxcol=None, returnline=False, greedy=False):
    """Encapsulates tokens in a source code line in a uncaptured
    subprocess ![] starting at a minimum column. If there are no tokens
    (ie in a comment line) this returns None. If greedy is True, it will encapsulate
    normal parentheses. Greedy is False by default.
    """
    if maxcol is None:
        maxcol = len(line) + 1
    lexer.reset()
    lexer.input(line)
    toks = []
    lparens = []
    saw_macro = False
    end_offset = 0
    for tok in lexer:
        pos = tok.lexpos
        if tok.type not in END_TOK_TYPES and pos >= maxcol:
            break
        if tok.type == "BANG":
            saw_macro = True
        if saw_macro and tok.type not in ("NEWLINE", "DEDENT"):
            toks.append(tok)
            continue
        if tok.type in LPARENS:
            lparens.append(tok.type)
        if greedy and len(lparens) > 0 and "LPAREN" in lparens:
            toks.append(tok)
            if tok.type == "RPAREN":
                lparens.pop()
            continue
        if len(toks) == 0 and tok.type in BEG_TOK_SKIPS:
            continue  # handle indentation
        elif len(toks) > 0 and toks[-1].type in END_TOK_TYPES:
            if _is_not_lparen_and_rparen(lparens, toks[-1]):
                lparens.pop()  # don't continue or break
            elif pos < maxcol and tok.type not in ("NEWLINE", "DEDENT", "WS"):
                if not greedy:
                    toks.clear()
                if tok.type in BEG_TOK_SKIPS:
                    continue
            else:
                break
        if pos < mincol:
            continue
        toks.append(tok)
        if tok.type == "WS" and tok.value == "\\":
            pass  # line continuation
        elif tok.type == "NEWLINE":
            break
        elif tok.type == "DEDENT":
            # fake a newline when dedenting without a newline
            tok.type = "NEWLINE"
            tok.value = "\n"
            tok.lineno -= 1
            if len(toks) >= 2:
                prev_tok_end = toks[-2].lexpos + len(toks[-2].value)
            else:
                prev_tok_end = len(line)
            if "#" in line[prev_tok_end:]:
                tok.lexpos = prev_tok_end  # prevents wrapping comments
            else:
                tok.lexpos = len(line)
            break
        elif check_bad_str_token(tok):
            return
    else:
        if len(toks) > 0 and toks[-1].type in END_TOK_TYPES:
            if _is_not_lparen_and_rparen(lparens, toks[-1]):
                pass
            elif greedy and toks[-1].type == "RPAREN":
                pass
            else:
                toks.pop()
        if len(toks) == 0:
            return  # handle comment lines
        tok = toks[-1]
        pos = tok.lexpos
        if isinstance(tok.value, str):
            end_offset = len(tok.value.rstrip())
        else:
            el = line[pos:].split("#")[0].rstrip()
            end_offset = len(el)
    if len(toks) == 0:
        return  # handle comment lines
    elif saw_macro or greedy:
        end_offset = len(toks[-1].value.rstrip()) + 1
    if toks[0].lineno != toks[-1].lineno:
        # handle multiline cases
        end_offset += _offset_from_prev_lines(line, toks[-1].lineno)
    beg, end = toks[0].lexpos, (toks[-1].lexpos + end_offset)
    end = len(line[:end].rstrip())
    rtn = "![" + line[beg:end] + "]"
    if returnline:
        rtn = line[:beg] + rtn + line[end:]
    return rtn


def _is_not_lparen_and_rparen(lparens, rtok):
    """Tests if an RPAREN token is matched with something other than a plain old
    LPAREN type.
    """
    # note that any([]) is False, so this covers len(lparens) == 0
    return rtok.type == "RPAREN" and any(x != "LPAREN" for x in lparens)


def _offset_from_prev_lines(line, last):
    lines = line.splitlines(keepends=True)[:last]
    return sum(map(len, lines))
