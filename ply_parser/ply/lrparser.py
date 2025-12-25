"""
#-----------------------------------------------------------------------------
#                        ===  LR Parsing Engine ===
#
# The following classes are used for the LR parser itself.  These are not
# used during table construction and are independent of the actual LR
# table generation algorithm
#-----------------------------------------------------------------------------
"""

import ast
import sys
from ast import AST
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    Any,
    Callable,
    Final,
    Optional,
    Protocol,
    Union,
)

from .common import PlyLogger, format_result, format_stack_entry

error_count: Final = 3  # Number of symbols that must be shifted to leave recovery mode


@dataclass(slots=True)
class LexToken:
    """keep for backward compatibility and name distinction"""

    type: str  # = Grammar symbol type
    value: str  # = token value
    lineno: int | None = None  # = Starting line number
    endlineno: int | None = None  # = Ending line number (optional, set automatically)
    lexpos: int | None = None  # = Starting lex position
    endlexpos: int | None = None  # = Ending lex position (optional, set automatically)


# This class is used to hold non-terminal grammar symbols during parsing.
# It normally has the following attributes set:
@dataclass(slots=True)
class YaccSymbol:
    type: str  # = Grammar symbol type
    value: Union[str, ast.AST, LexToken, None, "YaccSymbol"] = None  # = Symbol value
    lineno: int | None = None  # = Starting line number
    endlineno: int | None = None  # = Ending line number (optional, set automatically)
    lexpos: int | None = None  # = Starting lex position
    endlexpos: int | None = None  # = Ending lex position (optional, set automatically)


# This class is a wrapper around the objects actually passed to each
# grammar rule.   Index lookup and assignment actually assign the
# .value attribute of the underlying YaccSymbol object.
# The lineno() method returns the line number of a given
# item (or 0 if not defined).   The linespan() method returns
# a tuple of (startline,endline) representing the range of lines
# for a symbol.  The lexspan() method returns a tuple (lexpos,endlexpos)
# representing the range of positional information for a symbol.


class LexerProtocol(Protocol):
    def input(self, s: str) -> None: ...

    def __iter__(self) -> Iterator[LexToken]: ...


SliceType = Union[int, slice]


@dataclass(slots=True)
class YaccProduction:
    """A production object."""

    # The lexer that produced the token stream
    lexer: "LexerProtocol"
    # The parser that is running this production
    parser: "LRParser"
    # The slice of the input stream that is covered by this production
    slice: list["YaccSymbol"] = field(default_factory=list)
    # The stack of input symbols that is covered by this production
    stack: list["YaccSymbol"] = field(default_factory=list)

    def __getitem__(self, n: SliceType) -> Any:
        if isinstance(n, slice):
            return [s.value for s in self.slice[n]]
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

    def call(self, production):
        return getattr(self.parser.module, production.func)(self)


CallBack = Callable[[YaccProduction], None]


@dataclass(slots=True, frozen=True)
class Production:
    name: str
    len: int
    str: str
    func: str


class ParserProtocol(Protocol):
    def p_error(self, p: YaccProduction) -> None: ...


@dataclass
class ParserState:
    fsm: "StateMachine"
    statestack: list[int]  # Stack of parsing states
    symstack: list["YaccSymbol"]  # Stack of grammar symbols
    lookahead: Optional["YaccSymbol"]  # Current lookahead symbol
    lookaheadstack: list["YaccSymbol"]  # Stack of lookahead symbols
    errorcount: int  # Used during error recovery
    state: int
    errtoken: Optional["YaccSymbol"] = None
    tracking: bool = False

    def log_state(state, logger: "PlyLogger"):
        logger.debug("State  : %s", state.state)

    def log_stack(state, logger: "PlyLogger"):
        logger.debug(
            "Stack  : %s",
            (
                "{} . {}".format(" ".join([xx.type for xx in state.symstack][1:]), str(state.lookahead))
            ).lstrip(),
        )

    def _handle_shift(state, action: int, logger: Optional["PlyLogger"]) -> None:
        state.statestack.append(action)
        state.state = action

        if logger:
            logger.debug("Action : Shift and goto state %s", action)

        if state.lookahead is not None:
            state.symstack.append(state.lookahead)
        state.lookahead = None

        if state.errorcount:
            state.errorcount -= 1

    def _handle_accept(state, logger: Optional["PlyLogger"]) -> Any:
        result = getattr(state.symstack[-1], "value", None)
        if logger:
            logger.info("Done   : Returning %s", format_result(result))
            logger.info("PLY: PARSE DEBUG END")
        return result

    def _log_error_info(state, logger: "PlyLogger") -> None:
        logger.error(
            "Error  : %s",
            (
                "{} . {}".format(
                    " ".join([xx.type for xx in state.symstack][1:]),
                    str(state.lookahead),
                )
            ).lstrip(),
        )

    def _handle_error_stack(state) -> bool:
        sym = state.symstack.pop()
        if state.tracking and state.lookahead:
            state.lookahead.lineno = sym.lineno
            state.lookahead.lexpos = sym.lexpos
        state.statestack.pop()
        state.state = state.statestack[-1]
        return True

    def _handle_error_token(state) -> bool:
        sym = state.symstack[-1]
        if sym.type == "error":
            # Hmmm. Error is on top of stack, we'll just nuke input
            # symbol and continue
            if state.tracking:
                sym.endlineno = getattr(state.lookahead, "lineno", sym.lineno)
                sym.endlexpos = getattr(state.lookahead, "lexpos", sym.lexpos)
            state.lookahead = None
            return True

        new_error = YaccSymbol(type="error")
        if hasattr(state.lookahead, "lineno"):
            new_error.lineno = new_error.endlineno = state.lookahead.lineno
        if hasattr(state.lookahead, "lexpos"):
            new_error.lexpos = new_error.endlexpos = state.lookahead.lexpos
        new_error.value = state.lookahead
        state.lookaheadstack.append(state.lookahead)
        state.lookahead = new_error
        return True

    def _handle_error_recovery(state) -> bool:
        # case 1:  the statestack only has 1 entry on it.  If we're in this state, the
        # entire parse has been rolled back and we're completely hosed.   The token is
        # discarded and we just keep going.
        if len(state.statestack) <= 1 and state.lookahead and state.lookahead.type != "$end":
            state.lookahead = None
            state.errtoken = None
            state.state = 0
            state.lookaheadstack.clear()
            return True

        # case 2: the statestack has a couple of entries on it, but we're
        # at the end of the file. nuke the top entry and generate an error token

        if state.lookahead and state.lookahead.type == "$end":
            return False

        if state.lookahead and state.lookahead.type != "error":
            return state._handle_error_token()
        else:
            return state._handle_error_stack()


class LRParser:
    """The LR Parsing engine.  This is the core of the PLY parser generator."""

    def __init__(
        self,
        fsm: "StateMachine",
        errorf: Callable[[YaccSymbol | None], None] | None,
        module: ParserProtocol,
    ) -> None:
        self.fsm = fsm  # finite state machine
        self.errorfunc = errorf
        self.errorok = True
        self.module = module

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
    ) -> AST | None:
        # If debugging has been specified as a flag, turn it into a logging object
        logger = self._setup_logger(debug)
        parser_state = self._initialize_parser_state(lexer, input, tracking)

        # Production object passed to grammar rules
        pslice = YaccProduction(lexer, self)
        pslice.stack = parser_state.symstack

        while True:
            # Get the next symbol on the input.  If a lookahead symbol
            # is already set, we just use that. Otherwise, we'll pull
            # the next token off of the lookaheadstack or from the lexer

            if logger:
                parser_state.log_state(logger)
            action = self._get_next_action(parser_state, logger)

            if logger:
                parser_state.log_stack(logger)

            if action is not None:
                if action > 0:
                    parser_state._handle_shift(action, logger)
                    continue
                elif action < 0:
                    # reduce a symbol on the stack, emit a production
                    try:
                        self._handle_reduce(parser_state, action, pslice, logger)
                    except SyntaxError:
                        self._handle_syntax_error(parser_state)
                    continue
                elif action == 0:
                    return parser_state._handle_accept(logger)

            # Handle error case when action is None
            if not self._handle_error(parser_state, lexer, logger):
                return None

    @staticmethod
    def _setup_logger(debug: int) -> Optional["PlyLogger"]:
        if debug:
            logger = PlyLogger(sys.stderr)
            logger.info("PLY: PARSE DEBUG START")
            return logger
        return None

    def _initialize_parser_state(self, lexer: Any, input: Optional[str], tracking: bool) -> ParserState:
        if input is not None:
            lexer.input(input)

        self.token = lexer.token

        # The start state is assumed to be (0,$end)
        return ParserState(
            fsm=self.fsm,
            statestack=[0],
            symstack=[YaccSymbol(type="$end")],
            lookahead=None,
            lookaheadstack=[],
            errorcount=0,
            state=0,
            errtoken=None,
            tracking=tracking,
        )

    def _get_next_action(self, state: ParserState, logger: Optional["PlyLogger"]) -> Optional[int]:
        if default_action := self.fsm.get_default_action(state.state):
            if logger:
                logger.debug("Defaulted state %s: Reduce using %d", state.state, -default_action)
            return default_action

        if not state.lookahead:
            state.lookahead = self._get_lookahead_token(state)

        return self.fsm.get_action(state.state, state.lookahead.type)

    def _get_lookahead_token(self, state: ParserState) -> "YaccSymbol":
        if state.lookaheadstack:
            token = state.lookaheadstack.pop()
        else:
            token = self.token()

        if not token:
            return YaccSymbol(type="$end")
        return token

    def _handle_reduce(
        self, state: ParserState, action: int, pslice: "YaccProduction", logger: Optional["PlyLogger"]
    ) -> None:
        p = self.fsm.expect_production(-action)
        sym = YaccSymbol(type=p.name, value=None)

        if p.len:
            self._handle_production_with_length(state, p, sym, pslice, logger)
        else:
            self._handle_empty_production(state, p, sym, pslice, logger)

    def _handle_production_with_length(
        self,
        state: ParserState,
        p: Production,
        sym: "YaccSymbol",
        pslice: "YaccProduction",
        logger: Optional["PlyLogger"],
    ) -> None:
        if logger:
            logger.info(
                "Action : Reduce rule [%s] with %s and goto state %d",
                p.str,
                "[" + ",".join([format_stack_entry(_v.value) for _v in state.symstack[-p.len :]]) + "]",
                self.fsm.expect_goto(state.statestack[-1 - p.len], p.name),
            )
        targ = state.symstack[-p.len - 1 :]
        targ[0] = sym

        if state.tracking:
            self._update_tracking_info(sym, targ)

        pslice.slice = targ
        self.state = state.state
        getattr(self.module, p.func)(pslice)

        # todo: mark 1 - del before calling function above?
        del state.symstack[-p.len :]
        del state.statestack[-p.len :]

        if logger:
            logger.info("Result : %s", format_result(pslice[0]))

        state.symstack.append(sym)
        goto_state = self.fsm.expect_goto(state.statestack[-1], p.name)
        state.statestack.append(goto_state)
        state.state = goto_state

    def _handle_empty_production(
        self,
        state: ParserState,
        p: Any,
        sym: "YaccSymbol",
        pslice: "YaccProduction",
        logger: Optional["PlyLogger"],
    ) -> None:
        if logger:
            logger.info(
                "Action : Reduce rule [%s] with %s and goto state %d",
                p.str,
                [],
                self.fsm.expect_goto(state.statestack[-1], p.name),
            )
        if state.tracking:
            sym.lineno = pslice.lexer.lineno
            sym.lexpos = pslice.lexer.lexpos

        pslice.slice = [sym]
        self.state = state.state
        getattr(self.module, p.func)(pslice)

        if logger:
            logger.info("Result : %s", format_result(pslice[0]))

        state.symstack.append(sym)
        goto_state = self.fsm.expect_goto(state.statestack[-1], p.name)
        state.statestack.append(goto_state)
        state.state = goto_state

    def _handle_syntax_error(self, state: ParserState) -> None:
        if state.lookahead:
            state.lookaheadstack.append(state.lookahead)
        state.statestack.pop()
        state.state = state.statestack[-1]
        sym = YaccSymbol(type="error", value="error")
        state.lookahead = sym
        state.errorcount = error_count
        self.errorok = False

    def _handle_error(self, state: ParserState, lexer: Any, logger: Optional["PlyLogger"]) -> bool:
        if logger:
            state._log_error_info(logger)

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
        if state.errorcount == 0 or self.errorok:
            return self._handle_first_error(state, lexer)

        state.errorcount = error_count
        return state._handle_error_recovery()

    def _handle_first_error(self, state: ParserState, lexer: Any) -> bool:
        state.errorcount = error_count
        self.errorok = False

        if state.lookahead and state.lookahead.type == "$end":
            state.errtoken = None
        else:
            state.errtoken = state.lookahead

        if self.errorfunc:
            self.state = state.state
            tok = self.errorfunc(state.errtoken)
            if self.errorok:
                state.lookahead = tok
                state.errtoken = None
                return True
        else:
            self._print_error_message(state.errtoken)
            return False

        return True

    @staticmethod
    def _update_tracking_info(sym: "YaccSymbol", targ: list["YaccSymbol"]) -> None:
        t1 = targ[1]
        sym.lineno = t1.lineno
        sym.lexpos = t1.lexpos
        t1 = targ[-1]
        sym.endlineno = getattr(t1, "endlineno", t1.lineno)
        sym.endlexpos = getattr(t1, "endlexpos", t1.lexpos)

    @staticmethod
    def _print_error_message(errtoken: Optional["YaccSymbol"]) -> None:
        if errtoken:
            lineno = getattr(errtoken, "lineno", 0)
            if lineno:
                sys.stderr.write(f"yacc: Syntax error at line {lineno}, token={errtoken.type}\n")
            else:
                sys.stderr.write(f"yacc: Syntax error, token={errtoken.type}")
        else:
            sys.stderr.write("yacc: Parse error in input. EOF\n")


class StateMachine:
    __slots__ = ("productions", "actions", "gotos", "defaults")

    def __init__(self, table_path: str):
        path = Path(table_path)
        if path.suffix == ".pickle":
            self._load_pickle(path)
        else:
            self._load_jsonl(path)
        self._precompute_defaults()

    def _load_pickle(self, path: Path):
        import pickle

        with open(path, "rb") as f:
            productions, actions, gotos = pickle.load(f)
        self._init_data(productions, actions, gotos)

    def _load_jsonl(self, path: Path):
        import json

        with open(path) as f:
            lines = f.readlines()
        productions = json.loads(lines[0])
        actions = json.loads(lines[1])
        gotos = json.loads(lines[2])
        self._init_data(productions, actions, gotos)

    def _init_data(self, productions, actions, gotos):
        self.productions = [Production(name=p[0], len=p[1], str=p[2], func=p[3]) for p in productions]
        self.actions = actions
        self.gotos = gotos

    def _precompute_defaults(self):
        self.defaults = {}
        for state, act in enumerate(self.actions):
            if len(act) == 1:
                first = next(iter(act.values()))
                if first < 0:
                    self.defaults[state] = first

    def get_default_action(self, state: int) -> Optional[int]:
        return self.defaults.get(state)

    def get_action(self, state: int, sym: str) -> Optional[int]:
        return self.actions[state].get(sym)

    def expect_production(self, index: int) -> Production:
        return self.productions[index]

    def expect_goto(self, state: int, sym: str) -> int:
        return self.gotos[state][sym]


def load_parser(parser_table: Path | str, module: ParserProtocol) -> LRParser:
    if isinstance(parser_table, Path):
        parser_table = str(parser_table)

    fsm = StateMachine(parser_table)
    return LRParser(fsm, errorf=getattr(module, "p_error", None), module=module)
