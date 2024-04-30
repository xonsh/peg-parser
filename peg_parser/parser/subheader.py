import ast
import sys
from pathlib import Path
from typing import Any, Callable, ClassVar, Literal, Optional, TypeVar, Union, cast

from peg_parser.parser import token, tokenize
from peg_parser.parser.tokenizer import Mark, Tokenizer, exact_token_types

# Singleton ast nodes, created once for efficiency
Load = ast.Load()
Store = ast.Store()
Del = ast.Del()

Node = TypeVar("Node")
FC = TypeVar("FC", ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)

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
P = TypeVar("P", bound="Parser")
F = TypeVar("F", bound=Callable[..., Any])


def logger(method: F) -> F:
    """For non-memoized functions that we want to be logged.

    (In practice this is only non-leader left-recursive functions.)
    """
    method_name = method.__name__

    def logger_wrapper(self: P, *args: object) -> T:
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
    return cast(F, logger_wrapper)


def memoize(method: F) -> F:
    """Memoize a symbol method."""
    method_name = method.__name__

    def memoize_wrapper(self: P, *args: object) -> T:
        mark = self._mark()
        key = mark, method_name, args
        # Fast path: cache hit, and not verbose.
        if key in self._cache and not self._verbose:
            tree, endmark = self._cache[key]
            self._reset(endmark)
            return tree
        # Slow path: no cache hit, or verbose.
        verbose = self._verbose
        argsr = ",".join(repr(arg) for arg in args)
        fill = "  " * self._level
        if key not in self._cache:
            if verbose:
                print(f"{fill}{method_name}({argsr}) ... (looking at {self.showpeek()})")
            self._level += 1
            tree = method(self, *args)
            self._level -= 1
            if verbose:
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
    return cast(F, memoize_wrapper)


def memoize_left_rec(method: Callable[[P], Optional[T]]) -> Callable[[P], Optional[T]]:
    """Memoize a left-recursive symbol method."""
    method_name = method.__name__

    def memoize_left_rec_wrapper(self: P) -> Optional[T]:
        mark = self._mark()
        key = mark, method_name, ()
        # Fast path: cache hit, and not verbose.
        if key in self._cache and not self._verbose:
            tree, endmark = self._cache[key]
            self._reset(endmark)
            return tree
        # Slow path: no cache hit, or verbose.
        verbose = self._verbose
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
            lastresult, lastmark = None, mark
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

            self._level -= 1
            if verbose:
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


def load_attribute_chain(name, lineno=None, col=None):
    """Creates an AST that loads variable name that may (or may not)
    have attribute chains. For example, "a.b.c"
    """
    names = name.split(".")
    node = ast.Name(id=names.pop(0), ctx=Load, lineno=lineno, col_offset=col)
    for attr in names:
        node = ast.Attribute(value=node, attr=attr, ctx=Load, lineno=lineno, col_offset=col)
    return node


def xonsh_call(name, args, lineno=None, col=None) -> ast.Call:
    """Creates the AST node for calling a function of a given name.
    Functions names may contain attribute access, e.g. __xonsh__.env.
    """
    return ast.Call(
        func=load_attribute_chain(name, lineno=lineno, col=col),
        args=args,
        keywords=[],
        starargs=None,
        kwargs=None,
        lineno=lineno,
        col_offset=col,
    )


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
        py_version: Optional[tuple] = None,
    ) -> None:
        self._tokenizer = tokenizer
        self._verbose = verbose
        self._level = 0
        self._cache: dict[tuple[Mark, str, tuple[Any, ...]], tuple[Any, Mark]] = {}

        # Integer tracking wether we are in a left recursive rule or not. Can be useful
        # for error reporting.
        self.in_recursive_rule = 0

        # Pass through common tokenizer methods.
        self._mark = self._tokenizer.mark
        self._reset = self._tokenizer.reset

        # Are we looking for syntax error ? When true enable matching on invalid rules
        self.call_invalid_rules = False

        self.filename = filename
        self.py_version = min(py_version, sys.version_info) if py_version else sys.version_info

    def showpeek(self) -> str:
        tok = self._tokenizer.peek()
        return f"{tok.start[0]}.{tok.start[1]}: {token.tok_name[tok.type]}:{tok.string!r}"

    @memoize
    def name(self) -> Optional[tokenize.TokenInfo]:
        tok = self._tokenizer.peek()
        if tok.type == token.NAME and tok.string not in self.KEYWORDS:
            return self._tokenizer.getnext()
        return None

    @memoize
    def token(self, typ: int) -> Optional[tokenize.TokenInfo]:
        tok = self._tokenizer.peek()
        if tok.type == typ:
            return self._tokenizer.getnext()
        return None

    @memoize
    def soft_keyword(self) -> Optional[tokenize.TokenInfo]:
        tok = self._tokenizer.peek()
        if tok.type == token.NAME and tok.string in self.SOFT_KEYWORDS:
            return self._tokenizer.getnext()
        return None

    @memoize
    def expect(self, type: str) -> Optional[tokenize.TokenInfo]:
        tok = self._tokenizer.peek()
        if tok.string == type:
            return self._tokenizer.getnext()
        if type in exact_token_types:
            if tok.type == exact_token_types[type]:
                return self._tokenizer.getnext()
        if type in token.__dict__:
            if tok.type == token.__dict__[type]:
                return self._tokenizer.getnext()
        if tok.type == token.OP and tok.string == type:
            return self._tokenizer.getnext()
        return None

    def expect_forced(self, res: Any, expectation: str) -> Optional[tokenize.TokenInfo]:
        if res is None:
            raise self.make_syntax_error(f"expected {expectation}")
        return res

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

    def parse(self, rule: str, call_invalid_rules: bool = False) -> Optional[ast.AST]:
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

            self.raise_syntax_error_starting_from("invalid syntax", last_token)

        return res

    def check_version(self, min_version: tuple[int, ...], error_msg: str, node: Node) -> Node:
        """Check that the python version is high enough for a rule to apply."""
        if self.py_version >= min_version:
            return node
        else:
            raise SyntaxError(f"{error_msg} is only supported in Python {min_version} and above.")

    def raise_indentation_error(self, msg) -> None:
        """Raise an indentation error."""
        raise IndentationError(msg)

    def get_expr_name(self, node) -> str:
        """Get a descriptive name for an expression."""
        # See https://github.com/python/cpython/blob/master/Parser/pegen.c#L161
        assert node is not None
        node_t = type(node)
        if node_t is ast.Constant:
            v = node.value
            if v in (None, True, False, Ellipsis):
                return str(v)
            else:
                return "literal"

        try:
            return EXPR_NAME_MAPPING[node_t]
        except KeyError as e:
            raise ValueError(
                f"unexpected expression in assignment {type(node).__name__} " f"(line {node.lineno})."
            ) from e

    def set_expr_context(self, node, context):
        """Set the context (Load, Store, Del) of an ast node."""
        node.ctx = context
        return node

    def ensure_real(self, number_str: str):
        number = ast.literal_eval(number_str)
        if isinstance(number, complex):
            self.raise_syntax_error("real number required in complex literal")
        return number

    def ensure_imaginary(self, number_str: str):
        number = ast.literal_eval(number_str)
        if not isinstance(number, complex):
            self.raise_syntax_error("imaginary number required in complex literal")
        return number

    @staticmethod
    def _join_str_tokens(tokens: list[tokenize.TokenInfo]) -> str:
        line = 1
        col_offset = 0
        source = ""
        for t in tokens:
            n_line = t.start[0] - line
            if n_line:
                col_offset = 0
            source += """\n""" * n_line + " " * (t.start[1] - col_offset) + t.string
            line, col_offset = t.end
        if source[0] == " ":
            source = "(" + source[1:]
        else:
            source = "(" + source
        source += ")"
        return source

    @staticmethod
    def _has_path_prefix(token: tokenize.TokenInfo) -> bool:
        text = token.string
        if not text.startswith(("'", '"')):
            prefix = text[:2].lower()
            return prefix and "p" in prefix
        return False

    def generate_ast_for_string(self, tokens: list[tokenize.TokenInfo]):
        """Generate AST nodes for strings."""
        first_token = tokens[0]
        if path_literal := self._has_path_prefix(first_token):
            tokens[0] = first_token._replace(
                string=first_token.string.replace("p", "", 1).replace("P", "", 1)
            )

        node = self._parse_pure_string(tokens)
        if path_literal:
            return xonsh_call("__xonsh__.path_literal", [node], first_token.start[0], first_token.start[1])

        return node

    def _parse_pure_string(self, tokens: list[tokenize.TokenInfo]):
        err_args = None
        source = self._join_str_tokens(tokens)

        try:
            # ast.Module
            m = ast.parse(source)
        except SyntaxError as err:
            line_offset = tokens[0].start[0]
            args = (err.filename, err.lineno + line_offset - 2, err.offset, err.text)
            if sys.version_info >= (3, 10):
                args += (err.end_lineno + line_offset - 2, err.end_offset)
            err_args = (err.msg, args)

        # Avoid getting a triple nesting in the error report that does not
        # bring anything relevant to the traceback.
        if err_args:
            raise SyntaxError(*err_args)

        return m.body[0].value

    def extract_import_level(self, tokens: list[tokenize.TokenInfo]) -> int:
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

    def set_decorators(self, target: FC, decorators: list) -> FC:
        """Set the decorators on a function or class definition."""
        target.decorator_list = decorators
        return target

    def get_comparison_ops(self, pairs):
        return [op for op, _ in pairs]

    def get_comparators(self, pairs):
        return [comp for _, comp in pairs]

    def set_arg_type_comment(self, arg, type_comment):
        if type_comment or sys.version_info < (3, 9):
            arg.type_comment = type_comment
        return arg

    def make_arguments(
        self,
        pos_only: Optional[list[tuple[ast.arg, None]]],
        pos_only_with_default: list[tuple[ast.arg, Any]],
        param_no_default: Optional[list[tuple[ast.arg, None]]],
        param_default: Optional[list[tuple[ast.arg, Any]]],
        after_star: Optional[tuple[Optional[ast.arg], list[tuple[ast.arg, Any]], Optional[ast.arg]]],
    ) -> ast.arguments:
        """Build a function definition arguments."""
        defaults = [d for _, d in pos_only_with_default if d is not None] if pos_only_with_default else []
        defaults += [d for _, d in param_default if d is not None] if param_default else []

        pos_only = pos_only or pos_only_with_default

        # Because we need to combine pos only with and without default even
        # the version with no default is a tuple
        pos_only = [p for p, _ in pos_only]
        params = (param_no_default or []) + ([p for p, _ in param_default] if param_default else [])

        # If after_star is None, make a default tuple
        after_star = after_star or (None, [], None)

        return ast.arguments(
            posonlyargs=pos_only,
            args=params,
            defaults=defaults,
            vararg=after_star[0],
            kwonlyargs=[p for p, _ in after_star[1]],
            kw_defaults=[d for _, d in after_star[1]],
            kwarg=after_star[2],
        )

    def expand_env_name(self, a: tokenize.TokenInfo, b: ast.AST = None):
        xenv = load_attribute_chain("__xonsh__.env", lineno=a.start[0], col=a.start[1])
        idx = ast.Index(value=ast.Constant(value=a.string[1:], lineno=a.start[0], col_offset=a.start[1] + 1))
        a_node = ast.Subscript(
            value=xenv, slice=idx, ctx=ast.Load(), lineno=a.start[0], col_offset=a.start[1]
        )
        if b is None:
            return a_node
        # otherwise send a = b assignment
        return ast.Assign(targets=[a_node], value=b, lineno=a.start[0], col_offset=a.start[1])

    def _build_syntax_error(
        self,
        message: str,
        start: Optional[tuple[int, int]] = None,
        end: Optional[tuple[int, int]] = None,
    ) -> None:
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

        return SyntaxError(message, (self.filename, start[0], start[1], line))

    def raise_raw_syntax_error(
        self,
        message: str,
        start: Optional[tuple[int, int]] = None,
        end: Optional[tuple[int, int]] = None,
    ) -> None:
        raise self._build_syntax_error(message, start, end)

    def make_syntax_error(self, message: str) -> None:
        return self._build_syntax_error(message)

    def raise_syntax_error(self, message: str) -> None:
        """Raise a syntax error."""
        raise self._build_syntax_error(message)

    def raise_syntax_error_known_location(self, message: str, node) -> None:
        """Raise a syntax error that occured at a given AST node."""
        if isinstance(node, tokenize.TokenInfo):
            start = node.start
            end = node.end
        else:
            start = node.lineno, node.col_offset
            end = node.end_lineno, node.end_col_offset

        raise self._build_syntax_error(message, start, end)

    def raise_syntax_error_known_range(
        self,
        message: str,
        start_node: Union[ast.AST, tokenize.TokenInfo],
        end_node: Union[ast.AST, tokenize.TokenInfo],
    ) -> None:
        if isinstance(start_node, tokenize.TokenInfo):
            start = start_node.start
        else:
            start = start_node.lineno, start_node.col_offset

        if isinstance(end_node, tokenize.TokenInfo):
            end = end_node.end
        else:
            end = end_node.end_lineno, end_node.end_col_offset

        raise self._build_syntax_error(message, start, end)

    def raise_syntax_error_starting_from(
        self, message: str, start_node: Union[ast.AST, tokenize.TokenInfo]
    ) -> None:
        if isinstance(start_node, tokenize.TokenInfo):
            start = start_node.start
        else:
            start = start_node.lineno, start_node.col_offset

        raise self._build_syntax_error(message, start, None)

    @classmethod
    def parse_file(
        cls,
        path: Path,
        py_version: Optional[tuple] = None,
        verbose: bool = False,
    ) -> ast.Module:
        """Parse a file or string."""
        with open(path) as f:
            tok_stream = tokenize.generate_tokens(f.readline)
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
        py_version: Optional[tuple] = None,
        verbose: bool = False,
    ) -> Any:
        """Parse a string."""
        import io

        tok_stream = tokenize.generate_tokens(io.StringIO(source).readline)
        tokenizer = Tokenizer(tok_stream, verbose=verbose)
        parser = cls(tokenizer, verbose=verbose, py_version=py_version)
        return parser.parse(mode if mode == "eval" else "file")
