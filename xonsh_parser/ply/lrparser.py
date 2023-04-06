"""
#-----------------------------------------------------------------------------
#                        ===  LR Parsing Engine ===
#
# The following classes are used for the LR parser itself.  These are not
# used during table construction and are independent of the actual LR
# table generation algorithm
#-----------------------------------------------------------------------------
"""
import sys
from ast import Expression
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Final, NamedTuple, Optional, Protocol

from .common import PlyLogger, format_result, format_stack_entry

error_count: Final = 3  # Number of symbols that must be shifted to leave recovery mode


# This class is used to hold non-terminal grammar symbols during parsing.
# It normally has the following attributes set:
@dataclass(slots=True)
class YaccSymbol:
    type: str  # = Grammar symbol type
    value: Any = None  # = Symbol value
    lineno: int | None = None  # = Starting line number
    endlineno: int | None = None  # = Ending line number (optional, set automatically)
    lexpos: int | None = None  # = Starting lex position
    endlexpos: int | None = None  # = Ending lex position (optional, set automatically)


LexToken = YaccSymbol  # For backwards compatibility

# This class is a wrapper around the objects actually passed to each
# grammar rule.   Index lookup and assignment actually assign the
# .value attribute of the underlying YaccSymbol object.
# The lineno() method returns the line number of a given
# item (or 0 if not defined).   The linespan() method returns
# a tuple of (startline,endline) representing the range of lines
# for a symbol.  The lexspan() method returns a tuple (lexpos,endlexpos)
# representing the range of positional information for a symbol.


class YaccProduction:
    def __init__(self, s: list["YaccSymbol"] | None = None, stack: Any = None) -> None:
        self.slice = s or []
        self.stack: list["YaccSymbol"] = stack or []
        self.lexer: Any = None
        self.parser: None | "LRParser" = None

    def __getitem__(self, n: int) -> Any:
        # if isinstance(n, slice):
        #     return [s.value for s in self.slice[n]]
        if n >= 0:
            return self.slice[n].value
        return self.stack[n].value

    def __setitem__(self, n: int, v: Any) -> None:
        self.slice[n].value = v

    # def __getslice__(self, i, j):
    #     return [s.value for s in self.slice[i:j]]

    def __len__(self) -> int:
        return len(self.slice)

    def lineno(self, n: int) -> int:
        return getattr(self.slice[n], "lineno", 0)

    def set_lineno(self, n: int, lineno: int) -> None:
        self.slice[n].lineno = lineno

    def linespan(self, n: int) -> tuple[int, int]:
        startline = getattr(self.slice[n], "lineno", 0)
        endline = getattr(self.slice[n], "endlineno", startline)
        return startline, endline

    def lexpos(self, n: int) -> int:
        return getattr(self.slice[n], "lexpos", 0)

    def set_lexpos(self, n: int, lexpos: int) -> None:
        self.slice[n].lexpos = lexpos

    def lexspan(self, n: int) -> tuple[int, int]:
        startpos = getattr(self.slice[n], "lexpos", 0)
        endpos = getattr(self.slice[n], "endlexpos", startpos)
        return startpos, endpos

    def error(self) -> None:
        raise SyntaxError


CallBack = Callable[[YaccProduction], None]


class Production(NamedTuple):
    name: str
    str: str
    callable: CallBack
    len: int


class ParserProtocol(Protocol):
    def p_error(self, p: YaccProduction) -> None:
        ...


class LRParser:
    """The LR Parsing engine.  This is the core of the PLY parser generator."""

    def __init__(
        self,
        productions: tuple["Production", ...],
        action: tuple[dict[str, int]],
        goto: tuple[dict[str, int]],
        errorf: Callable[[YaccSymbol | None], None] | None,
    ) -> None:
        self.productions = productions
        # the int keys and values are very small around -2k to +2k
        self.action = action
        self.goto = goto
        self.errorfunc = errorf
        self.defaulted_states: dict[int, int] = {}
        self.set_defaulted_states()
        self.errorok = True

    def errok(self) -> None:
        self.errorok = True

    def restart(self) -> None:
        del self.statestack[:]
        del self.symstack[:]
        sym = YaccSymbol(type="$end")
        self.symstack.append(sym)
        self.statestack.append(0)

    # Defaulted state support.
    # This method identifies parser states where there is only one possible reduction action.
    # For such states, the parser can make a choose to make a rule reduction without consuming
    # the next look-ahead token.  This delayed invocation of the tokenizer can be useful in
    # certain kinds of advanced parsing situations where the lexer and parser interact with
    # each other or change states (i.e., manipulation of scope, lexer states, etc.).
    #
    # See:  http://www.gnu.org/software/bison/manual/html_node/Default-Reductions.html#Default-Reductions
    def set_defaulted_states(self) -> None:
        for state, actions in enumerate(self.action):
            rules = list(actions.values())
            if len(rules) == 1 and rules[0] < 0:
                self.defaulted_states[state] = rules[0]

    def disable_defaulted_states(self) -> None:
        self.defaulted_states.clear()

    # parse().
    #
    # This is the core parsing engine.  To operate, it requires a lexer object.
    # Two options are provided.  The logger flag turns on debugging so that you can
    # see the various rule reductions and parsing steps.  tracking turns on position
    # tracking.  In this mode, symbols will record the starting/ending line number and
    # character index.

    def parse(
        self,
        input: Optional[str] = None,
        lexer: Any = None,
        debug: int = 0,
        tracking: bool = False,
    ) -> Expression:
        # If debugging has been specified as a flag, turn it into a logging object
        logger: None | PlyLogger = None
        if isinstance(debug, int) and debug:
            logger = PlyLogger(sys.stderr)

        lookahead: None | YaccSymbol = None  # Current lookahead symbol
        lookaheadstack: list[YaccSymbol] = []  # Stack of lookahead symbols
        actions = (
            self.action
        )  # Local reference to action table (to avoid lookup on self.)
        goto = self.goto  # Local reference to goto table (to avoid lookup on self.)
        prod = (
            self.productions
        )  # Local reference to production list (to avoid lookup on self.)
        defaulted_states = self.defaulted_states  # Local reference to defaulted states
        pslice = YaccProduction(None)  # Production object passed to grammar rules
        errorcount = 0  # Used during error recovery

        if logger:
            logger.info("PLY: PARSE DEBUG START")

        # Set up the lexer and parser objects on pslice
        pslice.lexer = lexer
        pslice.parser = self

        # If input was supplied, pass to lexer
        if input is not None:
            lexer.input(input)

        # Set the token function
        get_token = self.token = lexer.token

        # Set up the state and symbol stacks
        self.statestack: list[int] = []  # Stack of parsing states
        statestack = self.statestack
        self.symstack: list[YaccSymbol] = []  # Stack of grammar symbols
        symstack = self.symstack
        pslice.stack = symstack  # Put in the production
        errtoken = None  # Err token

        # The start state is assumed to be (0,$end)

        statestack.append(0)
        sym = YaccSymbol(type="$end")
        symstack.append(sym)
        state = 0
        while True:
            # Get the next symbol on the input.  If a lookahead symbol
            # is already set, we just use that. Otherwise, we'll pull
            # the next token off of the lookaheadstack or from the lexer

            if logger:
                logger.debug("State  : %s", state)

            if state not in defaulted_states:
                if not lookahead:
                    if not lookaheadstack:
                        lookahead = get_token()  # Get the next token
                    else:
                        lookahead = lookaheadstack.pop()
                    if not lookahead:
                        lookahead = YaccSymbol(type="$end")

                # Check the action table
                ltype = lookahead.type
                t = actions[state].get(ltype)
            else:
                t = defaulted_states[state]
                if logger:
                    logger.debug("Defaulted state %s: Reduce using %d", state, -t)

            if logger:
                logger.debug(
                    "Stack  : %s",
                    (
                        "{} . {}".format(
                            " ".join([xx.type for xx in symstack][1:]), str(lookahead)
                        )
                    ).lstrip(),
                )

            if t is not None:
                if t > 0:
                    # shift a symbol on the stack
                    statestack.append(t)
                    state = t

                    if logger:
                        logger.debug("Action : Shift and goto state %s", t)

                    if lookahead is not None:
                        symstack.append(lookahead)
                    lookahead = None

                    # Decrease error count on successful shift
                    if errorcount:
                        errorcount -= 1
                    continue

                if t < 0:
                    # reduce a symbol on the stack, emit a production
                    p = prod[-t]
                    pname = p.name
                    plen = p.len

                    # Get production function
                    sym = YaccSymbol(type=pname, value=None)  # Production name

                    if logger:
                        if plen:
                            logger.info(
                                "Action : Reduce rule [%s] with %s and goto state %d",
                                p.str,
                                "["
                                + ",".join(
                                    [
                                        format_stack_entry(_v.value)
                                        for _v in symstack[-plen:]
                                    ]
                                )
                                + "]",
                                goto[statestack[-1 - plen]][pname],
                            )
                        else:
                            logger.info(
                                "Action : Reduce rule [%s] with %s and goto state %d",
                                p.str,
                                [],
                                goto[statestack[-1]][pname],
                            )

                    if plen:
                        targ = symstack[-plen - 1 :]
                        targ[0] = sym

                        if tracking:
                            t1 = targ[1]
                            sym.lineno = t1.lineno
                            sym.lexpos = t1.lexpos
                            t1 = targ[-1]
                            sym.endlineno = getattr(t1, "endlineno", t1.lineno)
                            sym.endlexpos = getattr(t1, "endlexpos", t1.lexpos)

                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                        # The code enclosed in this section is duplicated
                        # below as a performance optimization.  Make sure
                        # changes get made in both locations.

                        pslice.slice = targ

                        try:
                            # Call the grammar rule with our special slice object
                            del symstack[-plen:]
                            self.state = state
                            p.callable(pslice)
                            del statestack[-plen:]
                            if logger:
                                logger.info("Result : %s", format_result(pslice[0]))
                            symstack.append(sym)
                            state = goto[statestack[-1]][pname]
                            statestack.append(state)
                        except SyntaxError:
                            # If an error was set. Enter error recovery state
                            if lookahead:
                                lookaheadstack.append(
                                    lookahead
                                )  # Save the current lookahead token
                            symstack.extend(
                                targ[1:-1]
                            )  # Put the production slice back on the stack
                            statestack.pop()  # Pop back one state (before the reduce)
                            state = statestack[-1]
                            sym.type = "error"
                            sym.value = "error"
                            lookahead = sym
                            errorcount = error_count
                            self.errorok = False

                        continue

                    else:
                        if tracking:
                            sym.lineno = lexer.lineno
                            sym.lexpos = lexer.lexpos

                        targ = [sym]

                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                        # The code enclosed in this section is duplicated
                        # above as a performance optimization.  Make sure
                        # changes get made in both locations.

                        pslice.slice = targ

                        try:
                            # Call the grammar rule with our special slice object
                            self.state = state
                            p.callable(pslice)
                            if logger:
                                logger.info("Result : %s", format_result(pslice[0]))
                            symstack.append(sym)
                            state = goto[statestack[-1]][pname]
                            statestack.append(state)
                        except SyntaxError:
                            # If an error was set. Enter error recovery state
                            if lookahead:
                                lookaheadstack.append(
                                    lookahead
                                )  # Save the current lookahead token
                            statestack.pop()  # Pop back one state (before the reduce)
                            state = statestack[-1]
                            sym.type = "error"
                            sym.value = "error"
                            lookahead = sym
                            errorcount = error_count
                            self.errorok = False

                        continue

                if t == 0:
                    n = symstack[-1]
                    result = getattr(n, "value", None)

                    if logger:
                        logger.info("Done   : Returning %s", format_result(result))
                        logger.info("PLY: PARSE DEBUG END")

                    if isinstance(result, Expression):
                        return result
                    raise TypeError("Parser state did not return an Expression object.")

            if t is None:
                if logger:
                    logger.error(
                        "Error  : %s",
                        (
                            "{} . {}".format(
                                " ".join([xx.type for xx in symstack][1:]),
                                str(lookahead),
                            )
                        ).lstrip(),
                    )

                # We have some kind of parsing error here.  To handle
                # this, we are going to push the current token onto
                # the tokenstack and replace it with an 'error' token.
                # If there are any synchronization rules, they may
                # catch it.
                #
                # In addition to pushing the error token, we call call
                # the user defined p_error() function if this is the
                # first syntax error.  This function is only called if
                # errorcount == 0.
                if errorcount == 0 or self.errorok:
                    errorcount = error_count
                    self.errorok = False
                    if lookahead and lookahead.type == "$end":
                        errtoken = None  # End of file!
                    else:
                        errtoken = lookahead
                    if self.errorfunc:
                        # if errtoken and not hasattr(errtoken, 'lexer'):
                        #     errtoken.lexer = lexer
                        self.state = state
                        tok: None = self.errorfunc(errtoken)
                        if self.errorok:
                            # User must have done some kind of panic
                            # mode recovery on their own.  The
                            # returned token is the next lookahead
                            lookahead = tok
                            errtoken = None
                            continue
                    else:
                        if errtoken:
                            if hasattr(errtoken, "lineno"):
                                lineno = errtoken.lineno
                            else:
                                lineno = 0
                            if lineno:
                                sys.stderr.write(
                                    "yacc: Syntax error at line %d, token=%s\n"
                                    % (lineno, errtoken.type)
                                )
                            else:
                                sys.stderr.write(
                                    "yacc: Syntax error, token=%s" % errtoken.type
                                )
                        else:
                            sys.stderr.write("yacc: Parse error in input. EOF\n")
                            return Expression("EOF")

                else:
                    errorcount = error_count

                # case 1:  the statestack only has 1 entry on it.  If we're in this state, the
                # entire parse has been rolled back and we're completely hosed.   The token is
                # discarded and we just keep going.

                if len(statestack) <= 1 and lookahead and lookahead.type != "$end":
                    lookahead = None
                    errtoken = None
                    state = 0
                    # Nuke the pushback stack
                    del lookaheadstack[:]
                    continue

                # case 2: the statestack has a couple of entries on it, but we're
                # at the end of the file. nuke the top entry and generate an error token

                # Start nuking entries on the stack
                if lookahead and lookahead.type == "$end":
                    # Whoa. We're really hosed here. Bail out
                    return Expression("EOF")

                if lookahead and lookahead.type != "error":
                    sym = symstack[-1]
                    if sym.type == "error":
                        # Hmmm. Error is on top of stack, we'll just nuke input
                        # symbol and continue
                        if tracking:
                            sym.endlineno = getattr(lookahead, "lineno", sym.lineno)
                            sym.endlexpos = getattr(lookahead, "lexpos", sym.lexpos)
                        lookahead = None
                        continue

                    # Create the error symbol for the first time and make it the new lookahead symbol
                    new_error = YaccSymbol(type="error")

                    if hasattr(lookahead, "lineno"):
                        new_error.lineno = new_error.endlineno = lookahead.lineno
                    if hasattr(lookahead, "lexpos"):
                        new_error.lexpos = new_error.endlexpos = lookahead.lexpos
                    new_error.value = lookahead
                    lookaheadstack.append(lookahead)
                    lookahead = new_error
                else:
                    sym = symstack.pop()
                    if tracking and lookahead:
                        lookahead.lineno = sym.lineno
                        lookahead.lexpos = sym.lexpos
                    statestack.pop()
                    state = statestack[-1]

                continue

            # If we'r here, something really bad happened
            raise RuntimeError("yacc: internal parser error!!!\n")


def load_parser(parser_table: Path, module: ParserProtocol) -> LRParser:
    import pickle

    with parser_table.open("rb") as fr:
        lr_prods, lr_action, lr_goto = pickle.load(fr)
    prods = tuple(
        Production(
            name=name,
            str=str,
            len=len,
            callable=getattr(module, func) if func else None,
        )
        for name, len, str, func in lr_prods
    )
    del pickle

    return LRParser(prods, lr_action, lr_goto, errorf=getattr(module, "p_error", None))
