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

RE_STRING_START = LazyObject(
    lambda: re.compile(_RE_STRING_START), globals(), "RE_STRING_START"
)
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


@lazyobject
def RE_COMPLETE_STRING():
    ptrn = (
        "^"
        + _RE_STRING_START
        + "(?P<quote>"
        + "|".join(_STRINGS)
        + ")"
        + ".*?(?P=quote)$"
    )
    return re.compile(ptrn, re.DOTALL)


def get_line_continuation(xsh):
    """The line continuation characters used in subproc mode. In interactive
    mode on Windows the backslash must be preceded by a space. This is because
    paths on Windows may end in a backslash.
    """
    if ON_WINDOWS:
        env = getattr(xsh, "env", None) or {}
        if env.get("XONSH_INTERACTIVE", False):
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
