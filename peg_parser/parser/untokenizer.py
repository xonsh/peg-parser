import itertools as _itertools

from .token import (
    DEDENT,
    ENCODING,
    ENDMARKER,
    FSTRING_END,
    FSTRING_MIDDLE,
    FSTRING_START,
    INDENT,
    NAME,
    NEWLINE,
    NL,
    NUMBER,
    STRING,
)


class Untokenizer:
    def __init__(self):
        self.tokens = []
        self.prev_row = 1
        self.prev_col = 0
        self.encoding = None

    def add_whitespace(self, start):
        row, col = start
        if row < self.prev_row or row == self.prev_row and col < self.prev_col:
            raise ValueError(f"start ({row},{col}) precedes previous end ({self.prev_row},{self.prev_col})")
        row_offset = row - self.prev_row
        if row_offset:
            self.tokens.append("\\\n" * row_offset)
            self.prev_col = 0
        col_offset = col - self.prev_col
        if col_offset:
            self.tokens.append(" " * col_offset)

    def escape_brackets(self, token):
        characters = []
        consume_until_next_bracket = False
        for character in token:
            if character == "}":
                if consume_until_next_bracket:
                    consume_until_next_bracket = False
                else:
                    characters.append(character)
            if character == "{":
                n_backslashes = sum(1 for char in _itertools.takewhile("\\".__eq__, characters[-2::-1]))
                if n_backslashes % 2 == 0:
                    characters.append(character)
                else:
                    consume_until_next_bracket = True
            characters.append(character)
        return "".join(characters)

    def untokenize(self, iterable):
        it = iter(iterable)
        indents = []
        startline = False
        for t in it:
            if len(t) == 2:
                self.compat(t, it)
                break
            tok_type, token, start, end, line = t
            if tok_type == ENCODING:
                self.encoding = token
                continue
            if tok_type == ENDMARKER:
                break
            if tok_type == INDENT:
                indents.append(token)
                continue
            elif tok_type == DEDENT:
                indents.pop()
                self.prev_row, self.prev_col = end
                continue
            elif tok_type in (NEWLINE, NL):
                startline = True
            elif startline and indents:
                indent = indents[-1]
                if start[1] >= len(indent):
                    self.tokens.append(indent)
                    self.prev_col = len(indent)
                startline = False
            elif tok_type == FSTRING_MIDDLE:
                if "{" in token or "}" in token:
                    token = self.escape_brackets(token)
                    last_line = token.splitlines()[-1]
                    end_line, end_col = end
                    extra_chars = last_line.count("{{") + last_line.count("}}")
                    end = (end_line, end_col + extra_chars)
            elif tok_type in (STRING, FSTRING_START) and self.prev_type in (STRING, FSTRING_END):
                self.tokens.append(" ")

            self.add_whitespace(start)
            self.tokens.append(token)
            self.prev_row, self.prev_col = end
            if tok_type in (NEWLINE, NL):
                self.prev_row += 1
                self.prev_col = 0
            self.prev_type = tok_type
        return "".join(self.tokens)

    def compat(self, token, iterable):
        indents = []
        toks_append = self.tokens.append
        startline = token[0] in (NEWLINE, NL)
        prevstring = False
        in_fstring = 0

        for tok in _itertools.chain([token], iterable):
            toknum, tokval = tok[:2]
            if toknum == ENCODING:
                self.encoding = tokval
                continue

            if toknum in (NAME, NUMBER):
                tokval += " "

            # Insert a space between two consecutive strings
            if toknum == STRING:
                if prevstring:
                    tokval = " " + tokval
                prevstring = True
            else:
                prevstring = False

            if toknum == FSTRING_START:
                in_fstring += 1
            elif toknum == FSTRING_END:
                in_fstring -= 1
            if toknum == INDENT:
                indents.append(tokval)
                continue
            elif toknum == DEDENT:
                indents.pop()
                continue
            elif toknum in (NEWLINE, NL):
                startline = True
            elif startline and indents:
                toks_append(indents[-1])
                startline = False
            elif toknum == FSTRING_MIDDLE:
                tokval = self.escape_brackets(tokval)

            # Insert a space between two consecutive brackets if we are in an f-string
            if tokval in {"{", "}"} and self.tokens and self.tokens[-1] == tokval and in_fstring:
                tokval = " " + tokval

            # Insert a space between two consecutive f-strings
            if toknum in (STRING, FSTRING_START) and self.prev_type in (STRING, FSTRING_END):
                self.tokens.append(" ")

            toks_append(tokval)
            self.prev_type = toknum


def untokenize(iterable):
    """Transform tokens back into Python source code.
    It returns a bytes object, encoded using the ENCODING
    token, which is the first token sequence output by tokenize.

    Each element returned by the iterable must be a token sequence
    with at least two elements, a token number and token value.  If
    only two tokens are passed, the resulting output is poor.

    Round-trip invariant for full input:
        Untokenized source will match input source exactly

    Round-trip invariant for limited input:
        # Output bytes will tokenize back to the input
        t1 = [tok[:2] for tok in tokenize(f.readline)]
        newcode = untokenize(t1)
        readline = BytesIO(newcode).readline
        t2 = [tok[:2] for tok in tokenize(readline)]
        assert t1 == t2
    """
    ut = Untokenizer()
    out = ut.untokenize(iterable)
    if ut.encoding is not None:
        out = out.encode(ut.encoding)
    return out
