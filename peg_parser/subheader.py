from __future__ import annotations

import ast
import enum
import sys
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar, Literal, ParamSpec, Protocol, TypedDict, TypeVar, cast

from peg_parser.tokenize import Token, TokenInfo, generate_tokens
from peg_parser.tokenizer import Mark, Tokenizer

if TYPE_CHECKING:
    # see - https://github.com/python/mypy/blob/master/mypy/typeshed/stdlib/_ast.pyi
    from collections.abc import Iterator
    from pathlib import Path

    FC = TypeVar("FC", bound=ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)

# Singleton ast nodes, created once for efficiency
Load = ast.Load()
Store = ast.Store()
Del = ast.Del()

# Node = TypeVar("Node", bound=ast.stmt | ast.expr)


class Node(Protocol):
    lineno: int
    col_offset: int
    end_lineno: int | None
    end_col_offset: int | None


class NodeCtx(Protocol):
    ctx: ast.expr_context


class SpanDict(TypedDict):
    lineno: int
    col_offset: int
    end_lineno: int
    end_col_offset: int


EXPR_NAME_MAPPING = {
    ast.Attribute: "attribute",
    ast.Subscript: "subscript",
    ast.Starred: "starred",
    ast.Name: "name",
    ast.List: "list",
    ast.Tuple: "tuple",
    ast.Lambda: "lambda",
    ast.Call: "function call",
    ast.BoolOp: "expression",
    ast.BinOp: "expression",
    ast.UnaryOp: "expression",
    ast.GeneratorExp: "generator expression",
    ast.Yield: "yield expression",
    ast.YieldFrom: "yield expression",
    ast.Await: "await expression",
    ast.ListComp: "list comprehension",
    ast.SetComp: "set comprehension",
    ast.DictComp: "dict comprehension",
    ast.Dict: "dict literal",
    ast.Set: "set display",
    ast.JoinedStr: "f-string expression",
    ast.FormattedValue: "f-string expression",
    ast.Compare: "comparison",
    ast.IfExp: "conditional expression",
    ast.NamedExpr: "named expression",
}

T = TypeVar("T")
TR = TypeVar("TR")  # repeated
TS = TypeVar("TS")
TG = TypeVar("TG")
P = TypeVar("P", bound="Parser")
P1 = ParamSpec("P1")
F = TypeVar("F", bound=Callable[..., Any])


def logger(method: F) -> F:
    """For non-memoized functions that we want to be logged.

    (In practice this is only non-leader left-recursive functions.)
    """
    method_name = method.__name__

    def logger_wrapper(self: P, *args: object) -> Any:
        if not self._verbose:
            return method(self, *args)
        argsr = ",".join(repr(arg) for arg in args)
        fill = "  " * self._level
        print(f"{fill}{method_name}({argsr}) .... (looking at {self.showpeek()})")
        self._level += 1
        tree = method(self, *args)
        self._level -= 1
        print(f"{fill}... {method_name}({argsr}) --> {tree!s:.200}")
        return tree

    logger_wrapper.__wrapped__ = method  # type: ignore
    return cast("F", logger_wrapper)


def memoize(method: F) -> F:
    """Memoize a symbol method."""
    method_name = method.__name__

    def memoize_wrapper(self: P) -> Any:
        mark = self._mark()
        key = mark, method_name
        # Fast path: cache hit, and not verbose.
        if key in self._cache and not self._verbose:
            tree, endmark = self._cache[key]
            self._reset(endmark)
            return tree
        # Slow path: no cache hit, or verbose.
        verbose, argsr, fill = self._verbose, "", ""
        if verbose:
            fill = "  " * self._level
        if key not in self._cache:
            if verbose:
                print(f"{fill}{method_name}({argsr}) ... (looking at {self.showpeek()})")
                self._level += 1
            tree = method(self)
            if verbose:
                self._level -= 1
                print(f"{fill}... {method_name}({argsr}) -> {tree!s:.200}")
            endmark = self._mark()
            self._cache[key] = tree, endmark
        else:
            tree, endmark = self._cache[key]
            if verbose:
                print(f"{fill}{method_name}({argsr}) -> {tree!s:.200}")
            self._reset(endmark)
        return tree

    memoize_wrapper.__wrapped__ = method  # type: ignore
    return cast("F", memoize_wrapper)


def memoize_left_rec(method: Callable[[P], T | None]) -> Callable[[P], T | None]:
    """Memoize a left-recursive symbol method."""
    method_name = method.__name__

    def memoize_left_rec_wrapper(self: P) -> T | Any | None:
        mark = self._mark()
        key = mark, method_name
        # Fast path: cache hit, and not verbose.
        if key in self._cache and not self._verbose:
            tree, endmark = self._cache[key]
            self._reset(endmark)
            return tree
        # Slow path: no cache hit, or verbose.
        verbose, fill = self._verbose, ""
        if verbose:
            fill = "  " * self._level
        if key not in self._cache:
            if verbose:
                print(f"{fill}{method_name} ... (looking at {self.showpeek()})")
                self._level += 1

            # For left-recursive rules we manipulate the cache and
            # loop until the rule shows no progress, then pick the
            # previous result.  For an explanation why this works, see
            # https://github.com/PhilippeSigaud/Pegged/wiki/Left-Recursion
            # (But we use the memoization cache instead of a static
            # variable; perhaps this is similar to a paper by Warth et al.
            # (http://web.cs.ucla.edu/~todd/research/pub.php?id=pepm08).

            # Prime the cache with a failure.
            self._cache[key] = None, mark
            lastresult: Any = None
            lastmark = mark
            depth = 0
            if verbose:
                print(f"{fill}Recursive {method_name} at {mark} depth {depth}")

            while True:
                self._reset(mark)
                self.in_recursive_rule += 1
                try:
                    result = method(self)
                finally:
                    self.in_recursive_rule -= 1
                endmark = self._mark()
                depth += 1
                if verbose:
                    print(
                        f"{fill}Recursive {method_name} at {mark} depth {depth}: {result!s:.200} to {endmark}"
                    )
                if not result:
                    if verbose:
                        print(f"{fill}Fail with {lastresult!s:.200} to {lastmark}")
                    break
                if endmark <= lastmark:
                    if verbose:
                        print(f"{fill}Bailing with {lastresult!s:.200} to {lastmark}")
                    break
                self._cache[key] = lastresult, lastmark = result, endmark

            self._reset(lastmark)
            tree = lastresult

            if verbose:
                self._level -= 1
                print(f"{fill}{method_name}() -> {tree!s:.200} [cached]")
            if tree:
                endmark = self._mark()
            else:
                endmark = mark
                self._reset(endmark)
            self._cache[key] = tree, endmark
        else:
            tree, endmark = self._cache[key]
            if verbose:
                print(f"{fill}{method_name}() -> {tree!s:.200} [fresh]")
            if tree:
                self._reset(endmark)
        return tree

    memoize_left_rec_wrapper.__wrapped__ = method  # type: ignore
    return memoize_left_rec_wrapper


def load_attribute_chain(name: str, **locs: int) -> ast.Attribute | ast.Name:
    """Creates an AST that loads variable name that may (or may not)
    have attribute chains. For example, "a.b.c"
    """
    names = name.split(".")
    node: ast.Name | ast.Attribute = ast.Name(id=names.pop(0), ctx=Load, **locs)
    for attr in names:
        node = ast.Attribute(value=node, attr=attr, ctx=Load, **locs)
    return node


def xonsh_call(name: str, *args: Node, **locs: int) -> ast.Call:
    """Creates the AST node for calling a function of a given name.
    Functions names may contain attribute access, e.g. __xonsh__.env.
    """
    return ast.Call(
        func=load_attribute_chain(name, **locs),
        args=list(args),  # type: ignore
        keywords=[],
        # starargs=None,
        # kwargs=None,
        **locs,
    )


class Target(enum.Enum):
    FOR_TARGETS = enum.auto()
    STAR_TARGETS = enum.auto()
    DEL_TARGETS = enum.auto()


class Parser:
    KEYWORDS: ClassVar[tuple[str, ...]]
    SOFT_KEYWORDS: ClassVar[tuple[str, ...]]

    #: Name of the source file, used in error reports
    filename: str

    def __init__(
        self,
        tokenizer: Tokenizer,
        *,
        verbose: bool = False,
        filename: str = "<unknown>",
        py_version: tuple[int, ...] | None = None,
    ) -> None:
        self._tokenizer = tokenizer
        self._verbose = verbose
        self._level = 0
        self._cache: dict[tuple[Mark, str], tuple[Any, Mark]] = {}

        # Integer tracking wether we are in a left recursive rule or not. Can be useful
        # for error reporting.
        self.in_recursive_rule = 0

        # handle path literal joined-str
        self._path_token: TokenInfo | None = None

        # Pass through common tokenizer methods.
        self._mark = self._tokenizer.mark
        self._reset = self._tokenizer.reset

        # Are we looking for syntax error ? When true enable matching on invalid rules
        self.call_invalid_rules = False

        self.filename = filename
        self.py_version = min(py_version, sys.version_info) if py_version else sys.version_info

    def showpeek(self) -> str:
        tok = self._tokenizer.peek()
        return f"{tok.start[0]}.{tok.start[1]}: {tok.type}:{tok.string!r}"

    def name(self) -> TokenInfo | None:
        tok = self._tokenizer.peek()
        if tok.type == Token.NAME and tok.string not in self.KEYWORDS:
            return self._tokenizer.getnext()
        return None

    def keyword(self) -> TokenInfo | None:
        tok = self._tokenizer.peek()
        if tok.type == Token.NAME and tok.string in self.KEYWORDS:
            return self._tokenizer.getnext()
        return None

    def token(self, typ: str) -> TokenInfo | None:
        tok = self._tokenizer.peek()
        if tok.type == Token[typ]:
            return self._tokenizer.getnext()
        return None

    def any_token(self) -> TokenInfo:
        return self._tokenizer.getnext()

    def soft_keyword(self) -> TokenInfo | None:
        tok = self._tokenizer.peek()
        if tok.type == Token.NAME and tok.string in self.SOFT_KEYWORDS:
            return self._tokenizer.getnext()
        return None

    def expect(self, typ: str) -> TokenInfo | None:
        tok = self._tokenizer.peek()
        if tok.string == typ:
            return self._tokenizer.getnext()
        return None

    def repeated(self, func: Callable[..., TR | None], *args: Any) -> list[TR]:
        mark = self._mark()
        children = []
        while result := func(*args):
            children.append(result)
            mark = self._mark()
        self._reset(mark)
        return children

    def sep_repeated(
        self,
        func: Callable[..., TS] | tuple[Callable[..., TS], Any],
        sep_func: Callable[..., Any],
        *sep_args: Any,
    ) -> TS | None:
        if (sep_func(*sep_args)) and (elem := self.seq_alts(func)):
            return elem
        return None

    def gathered(
        self,
        func: Callable[..., TG | None] | tuple[Callable[..., TG | None], Any],
        sep: Callable[..., Any],
        *sep_args: Any,
    ) -> list[TG] | None:
        # gather: ','.e+
        seq: list[TG]
        mark = self._mark()
        if (elem := self.seq_alts(func)) is not None and (
            seq := self.repeated(self.sep_repeated, func, sep, *sep_args)
        ) is not None:
            return [elem, *seq]
        self._reset(mark)
        return None

    def positive_lookahead(self, func: Callable[..., T], *args: object) -> T:
        mark = self._mark()
        ok = func(*args)
        self._reset(mark)
        return ok

    def negative_lookahead(self, func: Callable[..., object], *args: object) -> bool:
        mark = self._mark()
        ok = func(*args)
        self._reset(mark)
        return not ok

    def span(self, lnum: int, col: int) -> SpanDict:
        end = self._tokenizer.get_last_non_whitespace_token().end
        return {"lineno": lnum, "col_offset": col, "end_lineno": end[0], "end_col_offset": end[1]}

    def seq_alts(self, *alt: Callable[..., T] | tuple[Callable[..., T], Any]) -> T | None:
        """Handle sequence of alts that don't have action associated with them."""
        mark = self._mark()
        for arg in alt:
            if isinstance(arg, tuple):
                method, *args = arg
                res = method(*args)
            else:
                res = arg()
            if res:
                return res
            self._reset(mark)
        return None

    def parse(self, rule: str, call_invalid_rules: bool = False) -> Node | Any | None:
        self.call_invalid_rules = call_invalid_rules
        res = getattr(self, rule)()

        if res is None:
            # Grab the last token that was parsed in the first run to avoid
            # polluting a generic error reports with progress made by invalid rules.
            last_token = self._tokenizer.diagnose()

            if not call_invalid_rules:
                self.call_invalid_rules = True

                # Reset the parser cache to be able to restart parsing from the
                # beginning.
                self._reset(0)  # type: ignore
                self._cache.clear()

                res = getattr(self, rule)()

            self.raise_raw_syntax_error("invalid syntax", last_token.start, last_token.end)

        return res

    def check_version(self, min_version: tuple[int, ...], error_msg: str, node: T) -> T:
        """Check that the python version is high enough for a rule to apply."""
        if self.py_version >= min_version:
            return node
        else:
            raise SyntaxError(f"{error_msg} is only supported in Python {min_version} and above.")

    def raise_indentation_error(self, msg: str) -> None:
        """Raise an indentation error."""
        last_token = self._tokenizer.diagnose()
        args = (self.filename, last_token.start[0], last_token.start[1] + 1, last_token.line)
        args += (last_token.end[0], last_token.end[1] + 1)  # type: ignore
        raise IndentationError(msg, args)

    def get_expr_name(self, node: Any) -> str:
        """Get a descriptive name for an expression."""
        # See https://github.com/python/cpython/blob/master/Parser/pegen.c#L161
        assert node is not None
        node_t = type(node)
        if node_t is ast.Constant:
            v = node.value
            if v is Ellipsis:
                return "ellipsis"
            elif v is None or v is True or v is False:
                return str(v)
            else:
                return "literal"

        try:
            name = EXPR_NAME_MAPPING[node_t]
        except KeyError as e:
            raise ValueError(
                f"unexpected expression in assignment {type(node).__name__} (line {node.lineno})."
            ) from e
        return name

    def get_invalid_target(self, target: Target, node: Node | None) -> Node | None:
        """Get the meaningful invalid target for different assignment type."""
        if node is None:
            return None

        # We only need to visit List and Tuple nodes recursively as those
        # are the only ones that can contain valid names in targets when
        # they are parsed as expressions. Any other kind of expression
        # that is a container (like Sets or Dicts) is directly invalid and
        # we do not need to visit it recursively.
        if isinstance(node, ast.List | ast.Tuple):
            for e in node.elts:
                if (inv := self.get_invalid_target(target, e)) is not None:
                    return inv
        elif isinstance(node, ast.Starred):
            if target is Target.DEL_TARGETS:
                return node
            return self.get_invalid_target(target, node.value)
        elif isinstance(node, ast.Compare):
            # This is needed, because the `a in b` in `for a in b` gets parsed
            # as a comparison, and so we need to search the left side of the comparison
            # for invalid targets.
            if target is Target.FOR_TARGETS:
                if isinstance(node.ops[0], ast.In):
                    return self.get_invalid_target(target, node.left)
                return None

            return node
        elif isinstance(node, ast.Name | ast.Subscript | ast.Attribute):
            return None
        return node

    def set_expr_context(self, node: T, context: ast.Load | ast.Store | ast.Del) -> T:
        """Set the context (Load, Store, Del) of an ast node."""
        if hasattr(node, "ctx"):
            node.ctx = context
        return node

    def ensure_real(self, number: TokenInfo) -> float | int:
        value = ast.literal_eval(number.string)
        if not isinstance(value, float | int):
            self.raise_syntax_error_known_location("real number required in complex literal", number)
        return cast("float | int", value)

    def ensure_imaginary(self, number: TokenInfo) -> complex:
        value = ast.literal_eval(number.string)
        if not isinstance(value, complex):
            self.raise_syntax_error_known_location("imaginary number required in complex literal", number)
        return cast("complex", value)

    def check_fstring_conversion(self, name: TokenInfo) -> int:
        s = name.string
        if len(s) > 1 or s not in ("s", "r", "a"):
            self.raise_syntax_error_known_location(
                f"f-string: invalid conversion character '{s}': expected 's', 'r', or 'a'",
                name,
            )

        return s.encode()[0]

    def _concat_strings_in_constant(self, parts: list[TokenInfo]) -> ast.Constant:
        s = ast.literal_eval(parts[0].string)
        for ss in parts[1:]:
            s += ast.literal_eval(ss.string)
        args = {
            "value": s,
            "lineno": parts[0].start[0],
            "col_offset": parts[0].start[1],
            "end_lineno": parts[-1].end[0],
            "end_col_offset": parts[0].end[1],
        }
        if parts[0].string.startswith("u"):
            args["kind"] = "u"
        return ast.Constant(**args)

    def concatenate_strings(
        self, parts: list[ast.JoinedStr | TokenInfo]
    ) -> ast.Constant | ast.JoinedStr | ast.Call:
        """Concatenate multiple tokens and ast.JoinedStr"""
        # Get proper start and stop
        start = end = None
        if isinstance(parts[0], ast.JoinedStr):
            start = parts[0].lineno, parts[0].col_offset
        if isinstance(parts[-1], ast.JoinedStr):
            end = parts[-1].end_lineno, parts[-1].end_col_offset

        # Combine the different parts
        seen_joined = False
        values: list[ast.Constant | ast.FormattedValue | ast.expr] = []
        ss: list[TokenInfo] = []

        if path_tok := (self._strip_path_prefix(parts[0])):
            parts[0] = path_tok

        for p in parts:
            if isinstance(p, ast.JoinedStr):
                seen_joined = True
                if ss:
                    values.append(self._concat_strings_in_constant(ss))
                    ss.clear()

                values.extend(p.values)
            else:
                ss.append(p)

        if ss:
            values.append(self._concat_strings_in_constant(ss))

        consolidated: list[Any] = []  # ast.Constant | ast.FormattedValue
        for pv in values:
            if consolidated and isinstance(consolidated[-1], ast.Constant) and isinstance(pv, ast.Constant):
                consolidated[-1].value += pv.value  # type: ignore
                consolidated[-1].end_lineno = pv.end_lineno
                consolidated[-1].end_col_offset = pv.end_col_offset
            else:
                consolidated.append(pv)

        if not seen_joined and len(values) == 1 and isinstance(values[0], ast.Constant):
            node: ast.Constant | ast.JoinedStr | ast.Call = values[0]
        else:
            node = ast.JoinedStr(
                values=consolidated,
                lineno=start[0] if start else values[0].lineno,
                col_offset=start[1] if start else values[0].col_offset,
                end_lineno=(end[0] if end else values[-1].end_lineno) or 0,
                end_col_offset=(end[1] if end else values[-1].end_col_offset) or 0,
            )

        if path_tok := (path_tok or self._path_token):
            node = xonsh_call("__xonsh__.path_literal", node, **path_tok.loc())
            self._path_token = None
        return node

    def handle_fstring(
        self, a: TokenInfo, b: list[ast.FormattedValue | ast.Constant], **locs: int
    ) -> ast.JoinedStr:
        path_tok = self._strip_path_prefix(a)
        if path_tok:
            self._path_token = path_tok
        return ast.JoinedStr(values=b, **locs)  # type: ignore

    @staticmethod
    def _strip_path_prefix(token: TokenInfo | Node) -> TokenInfo | None:
        if not isinstance(token, TokenInfo):
            return None
        text = token.string
        idx = text.find("'") if text.find("'") >= 0 else text.find('"')
        if idx > 0:
            prefix, text = text[:idx].lower(), text[idx:]
            if "p" in prefix:
                prefix = prefix.replace("p", "", 1)
                return token._replace(string=prefix + text)
        return None

    def extract_import_level(self, tokens: list[TokenInfo]) -> int:
        """Extract the relative import level from the tokens preceding the module name.

        '.' count for one and '...' for 3.

        """
        level = 0
        for t in tokens:
            if t.string == ".":
                level += 1
            else:
                level += 3
        return level

    def set_decorators(self, target: FC, decorators: list[Node]) -> FC:
        """Set the decorators on a function or class definition."""
        target.decorator_list = decorators  # type: ignore
        return target

    def get_comparison_ops(self, pairs: list[tuple[T, T]]) -> list[T]:
        return [op for op, _ in pairs]

    def get_comparators(self, pairs: list[tuple[T, T]]) -> list[T]:
        return [comp for _, comp in pairs]

    def make_arguments(
        self,
        pos_only: list[tuple[ast.arg, None]] | None,
        pos_only_with_default: list[tuple[ast.arg, Any]],
        param_no_default: list[tuple[ast.arg]] | None,
        param_default: list[tuple[ast.arg, Any]] | None,
        after_star: tuple[ast.arg | None, list[tuple[ast.arg, Any]], ast.arg | None] | None,
    ) -> ast.arguments:
        """Build a function definition arguments."""
        defaults = [d for _, d in pos_only_with_default if d is not None] if pos_only_with_default else []
        defaults += [d for _, d in param_default if d is not None] if param_default else []

        pos_only = pos_only or pos_only_with_default

        # Because we need to combine pos only with and without default even
        # the version with no default is a tuple
        params = (param_no_default or []) + ([p for p, _ in param_default] if param_default else [])

        # If after_star is None, make a default tuple
        after_star = after_star or (None, [], None)

        return ast.arguments(
            posonlyargs=[p for p, _ in pos_only],
            args=params,  # type: ignore
            defaults=defaults,
            vararg=after_star[0],
            kwonlyargs=[p for p, _ in after_star[1]],
            kw_defaults=[d for _, d in after_star[1]],
            kwarg=after_star[2],
        )

    def expand_env_name(
        self, name: TokenInfo, ctx: ast.Load | ast.Store | None = None, **locs: int
    ) -> ast.Subscript:
        if ctx is None:
            ctx = Load
        return ast.Subscript(
            value=load_attribute_chain("__xonsh__.env", **locs),
            slice=ast.Constant(value=name.string, kind=None, **locs),
            ctx=ctx,
            **locs,
        )

    def expand_help(self, atoms: list[tuple[ast.Name, TokenInfo]], **_: int) -> ast.Call | None:
        node: ast.Call | None = None
        for atom, tok in atoms:
            fn = "superhelp" if tok.is_exact_type("??") else "help"
            if node is None:
                node = xonsh_call(f"__xonsh__.{fn}", atom, **tok.loc())
            else:
                node = xonsh_call(
                    f"__xonsh__.{fn}",
                    ast.Attribute(value=node, attr=atom.id, ctx=Load, **tok.loc()),
                    **tok.loc(),
                )
        return node

    def expand_env_expr(
        self, slices: Node, ctx: ast.Store | ast.Load | None = None, **locs: int
    ) -> ast.Subscript:
        if ctx is None:
            ctx = Load
        return ast.Subscript(
            value=load_attribute_chain("__xonsh__.env", **locs),
            slice=xonsh_call("str", slices, **locs),
            ctx=ctx,
            **locs,
        )

    @staticmethod
    def is_adjacent(prev: TokenInfo | Node, curr: TokenInfo | Node | Node) -> bool:
        end = prev.end if isinstance(prev, TokenInfo) else (prev.end_lineno, prev.end_col_offset)
        start = curr.start if isinstance(curr, TokenInfo) else (curr.lineno, curr.col_offset)
        return end == start

    def _append_node_or_token(self, tree: ast.expr | None, cmd: TokenInfo | ast.expr) -> ast.expr:
        if tree is None:
            return (
                ast.Constant(value=cmd.string, kind=None, **cmd.loc()) if isinstance(cmd, TokenInfo) else cmd
            )

        locs = {"lineno": tree.lineno, "col_offset": tree.col_offset}
        if isinstance(tree, ast.Constant) and isinstance(cmd, TokenInfo):
            return ast.Constant(value=tree.value + cmd.string, kind=None, **locs, **cmd.loc_end())

        # prefix@(...)
        if isinstance(tree, ast.Constant) and isinstance(cmd, ast.Starred):
            return ast.Tuple(
                elts=[tree, cmd],
                ctx=Load,
                **locs,
                end_lineno=cmd.end_lineno or 0,
                end_col_offset=cmd.end_col_offset or 0,
            )
        # @(...)suffix
        if isinstance(tree, ast.Starred | ast.Tuple) and isinstance(cmd, TokenInfo):
            suffix = ast.Constant(value=cmd.string, kind=None, **cmd.loc())
            elts = [*tree.elts, suffix] if isinstance(tree, ast.Tuple) else [tree, suffix]
            return ast.Tuple(elts=elts, ctx=Load, **locs, **cmd.loc_end())
        # prefix@(...)suffix
        if isinstance(tree, ast.Tuple) and isinstance(cmd, TokenInfo):
            return ast.Tuple(
                elts=[*tree.elts, ast.Constant(value=cmd.string, kind=None, **cmd.loc())],
                ctx=Load,
                **locs,
                **cmd.loc_end(),
            )
        if isinstance(cmd, TokenInfo):
            locs["end_lineno"] = cmd.end[0]
            locs["end_col_offset"] = cmd.end[1]
        elif cmd.end_lineno is not None:
            locs["end_lineno"] = cmd.end_lineno
            locs["end_col_offset"] = cmd.end_col_offset or 0
        return ast.BinOp(
            left=tree,
            op=ast.Add(),
            right=ast.Constant(value=cmd.string, kind=None, **cmd.loc())
            if isinstance(cmd, TokenInfo)
            else cmd,
            **locs,
        )

    def _proc_args(self, args: list[TokenInfo | ast.expr]) -> Iterator[ast.expr]:
        """split into chunks if they are not contiguous."""
        stash: None | ast.expr = None

        for ar in args:
            if not stash:
                stash = self._append_node_or_token(stash, ar)
                continue

            if self.is_adjacent(stash, ar):
                stash = self._append_node_or_token(stash, ar)
            else:
                yield stash
                stash = self._append_node_or_token(None, ar)

        if stash:
            yield stash

    def proc_args(self, args: list[TokenInfo | ast.expr]) -> list[ast.expr]:
        return list(self._proc_args(args))

    def handle_proc(self, method: str, args: list[Node], **locs: int) -> ast.Call:
        return xonsh_call(f"__xonsh__.{method}", *args, **locs)

    def proc_inject(self, args: list[Node], **locs: int) -> ast.Starred:
        return ast.Starred(
            value=xonsh_call("__xonsh__.subproc_captured_inject", *args, **locs),
            ctx=Load,
            **locs,
        )

    def proc_pyexpr(self, expr: Node, **locs: int) -> ast.Starred:
        return ast.Starred(
            value=xonsh_call("__xonsh__.list_of_strs_or_callables", expr, **locs),
            ctx=Load,
            **locs,
        )

    def expand_search_path(self, a: TokenInfo, **locs: int) -> ast.Call:
        return xonsh_call("__xonsh__.pathsearch", ast.Constant(value=a.string, kind=None, **locs), **locs)

    def macro_call(self, a: Node, b: list[TokenInfo], **locs: int) -> ast.Call:
        gbl_call = xonsh_call("globals", **locs)
        loc_call = xonsh_call("locals", **locs)
        positionals = ast.Tuple(
            elts=[ast.Constant(value=param.string, kind=None, **param.loc()) for param in b], ctx=Load, **locs
        )
        return xonsh_call(
            "__xonsh__.call_macro",
            a,
            positionals,
            gbl_call,
            loc_call,
            **locs,
        )

    def handle_with_macro_stmt(self, a: ast.withitem, b: TokenInfo, **locs: int) -> ast.With:
        gblcall = xonsh_call("globals", **locs)
        loccall = xonsh_call("locals", **locs)
        body = ast.Constant(value=b.string, kind=None, **b.loc())
        a.context_expr = xonsh_call("__xonsh__.enter_macro", a.context_expr, body, gblcall, loccall, **locs)
        self._tokenizer._with_macro = False
        return ast.With(items=[a], body=[ast.Pass(**locs)], type_comment=None, **locs)

    def handle_func_macro_start(self, a: Node) -> Node:
        self._tokenizer._call_macro = True
        return a

    def handle_with_macro_start(self, a: ast.withitem) -> ast.withitem:
        self._tokenizer._with_macro = True
        return a

    def handle_proc_macro_start(self, a: TokenInfo) -> TokenInfo:
        self._tokenizer._proc_macro = True
        return a

    def proc_macro_arg(self, a: list[TokenInfo | str] | Any, **locs: int) -> ast.Constant:
        locs["col_offset"] += 1  # offset `!`
        st = "".join((tok.string if isinstance(tok, TokenInfo) else tok) for tok in a).strip()
        self._tokenizer._proc_macro = False
        return ast.Constant(value=st, kind=None, **locs)

    def _build_syntax_error(
        self,
        message: str,
        start: tuple[int, int] | None = None,
        end: tuple[int, int] | None = None,
    ) -> SyntaxError:
        line_from_token = start is None and end is None
        if start is None or end is None:
            tok = self._tokenizer.diagnose()
            start = start or tok.start
            end = end or tok.end

        if line_from_token:
            line = tok.line
        else:
            # End is used only to get the proper text
            line = "\\n".join(self._tokenizer.get_lines(list(range(start[0], end[0] + 1))))

        # tokenize.py index column offset from 0 while Cpython index column
        # offset at 1 when reporting SyntaxError, so we need to increment
        # the column offset when reporting the error.
        args = (self.filename, start[0], start[1] + 1, line)
        args += (end[0], end[1] + 1)  # type: ignore

        return SyntaxError(message, args)

    def raise_raw_syntax_error(
        self,
        message: str,
        start: tuple[int, int] | None = None,
        end: tuple[int | None, int | None] | None = None,
    ) -> None:
        eloc = (end[0] or 0, end[1] or 0) if end else None
        raise self._build_syntax_error(message, start, eloc)

    def make_syntax_error(self, message: str) -> SyntaxError:
        return self._build_syntax_error(message)

    def expect_forced(self, res: TokenInfo | None, expectation: str) -> TokenInfo | None:
        if res is None:
            last_token = self._tokenizer.diagnose()
            end = last_token.start
            if sys.version_info >= (3, 12) or (
                sys.version_info >= (3, 11) and last_token.type != Token.NEWLINE
            ):  # i.e. not a \n
                end = last_token.end
            self.raise_raw_syntax_error(f"expected {expectation}", last_token.start, end)
        return res

    def raise_syntax_error(self, message: str) -> None:
        """Raise a syntax error."""
        tok = self._tokenizer.diagnose()
        raise self._build_syntax_error(
            message,
            tok.start,
            tok.end if sys.version_info >= (3, 12) or tok.type != Token.NEWLINE else tok.start,
        )

    def raise_syntax_error_known_location(self, message: str, node: Node | TokenInfo) -> None:
        """Raise a syntax error that occured at a given AST node."""
        if isinstance(node, TokenInfo):
            start = node.start
            end = node.end
        else:
            start = node.lineno, node.col_offset
            end = node.end_lineno or 0, node.end_col_offset or 0

        raise self._build_syntax_error(message, start, end)

    def raise_syntax_error_known_range(
        self,
        message: str,
        start_node: Node | TokenInfo,
        end_node: Node | TokenInfo,
    ) -> None:
        if isinstance(start_node, TokenInfo):
            start = start_node.start
        else:
            start = start_node.lineno, start_node.col_offset

        if isinstance(end_node, TokenInfo):
            end = end_node.end
        else:
            end = end_node.end_lineno or 0, end_node.end_col_offset or 0

        raise self._build_syntax_error(message, start, end)

    def raise_syntax_error_starting_from(self, message: str, start_node: Node | TokenInfo) -> None:
        if isinstance(start_node, TokenInfo):
            start = start_node.start
        else:
            start = start_node.lineno, start_node.col_offset

        last_token = self._tokenizer.diagnose()

        raise self._build_syntax_error(message, start, last_token.start)

    def raise_syntax_error_invalid_target(self, target: Target, node: Node | None) -> None:
        invalid_target = self.get_invalid_target(target, node)

        if invalid_target is None:
            return None

        if target in (Target.STAR_TARGETS, Target.FOR_TARGETS):
            msg = f"cannot assign to {self.get_expr_name(invalid_target)}"
        else:
            msg = f"cannot delete {self.get_expr_name(invalid_target)}"

        self.raise_syntax_error_known_location(msg, invalid_target)

    def raise_syntax_error_on_next_token(self, message: str) -> None:
        next_token = self._tokenizer.peek()
        raise self._build_syntax_error(message, next_token.start, next_token.end)

    @classmethod
    def parse_file(
        cls,
        path: Path,
        py_version: tuple[int, ...] | None = None,
        verbose: bool = False,
    ) -> ast.Module | Node | None:
        """Parse a file or string."""
        with open(path) as f:
            tok_stream = generate_tokens(f.readline)
            tokenizer = Tokenizer(tok_stream, verbose=verbose, path=str(path))
            parser = cls(
                tokenizer,
                verbose=verbose,
                filename=path.name,
                py_version=py_version,
            )
            return parser.parse("file")

    @classmethod
    def parse_string(
        cls,
        source: str,
        mode: Literal["eval", "exec"] = "eval",
        py_version: tuple[int, ...] | None = None,
        verbose: bool = False,
    ) -> Any:
        """Parse a string."""
        import io

        tok_stream = generate_tokens(io.StringIO(source).readline)
        tokenizer = Tokenizer(tok_stream, verbose=verbose)
        parser = cls(tokenizer, verbose=verbose, py_version=py_version)
        return parser.parse(mode if mode == "eval" else "file")
