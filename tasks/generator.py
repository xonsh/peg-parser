import ast
import itertools
from pathlib import Path
from typing import IO, Any

from peg_parser.tokenize import Token
from pegen import grammar
from pegen.build import build_parser
from pegen.grammar import (
    Alt,
    Gather,
    Item,
    NamedItem,
    NameLeaf,
    NegativeLookahead,
    PositiveLookahead,
    Repeat0,
    Repeat1,
    Rhs,
    Rule,
)
from pegen.parser_generator import ParserGenerator
from pegen.python_generator import (
    MODULE_PREFIX,
    MODULE_SUFFIX,
    InvalidNodeVisitor,
    PythonCallMakerVisitor,
    PythonParserGenerator,
    UsedNamesVisitor,
)


class XonshCallMakerVisitor(PythonCallMakerVisitor):
    def __init__(self, parser_generator: "XonshParserGenerator"):
        self.gen = parser_generator
        self.cache: dict[Any, Any] = {}
        self.keywords: set[str] = set()
        self.soft_keywords: set[str] = set()

    def lookahead_call_helper(self, node: Item, nested=True) -> tuple[str, str]:
        name, call = self.visit(node.node if nested else node)
        head, tail = call.split("(", 1)
        assert tail[-1] == ")"
        tail = tail[:-1]
        return head, tail

    def visit_NameLeaf(self, node: NameLeaf) -> tuple[str | None, str]:
        name = node.value
        special = {"SOFT_KEYWORD", "KEYWORD", "NAME", "ANY_TOKEN"}
        if name in special:
            name = name.lower()
            return name, f"self.{name}()"
        if name.isupper() and (name in self.gen.tokens):
            token = self.gen.tokens_enum[name]
            return "_" + name.lower(), f"self.token('{token.name}')"
        return name, f"self.{name}()"

    def visit_Gather(self, node: Gather) -> tuple[str, str]:
        if node in self.cache:
            return self.cache[node]
        func, fn_args = self.lookahead_call_helper(node)
        assert not fn_args
        sep = ", ".join([a for a in self.lookahead_call_helper(node.separator, nested=False) if a])
        self.cache[node] = "gathered", f"self.gathered({func}, {sep})"  # No trailing comma here either!
        return self.cache[node]

    def call_helper(self, node: Item) -> str:
        return ", ".join(a for a in self.lookahead_call_helper(node) if a)

    def visit_PositiveLookahead(self, node: PositiveLookahead) -> tuple[None, str]:
        return None, f"self.positive_lookahead({self.call_helper(node)})"

    def visit_NegativeLookahead(self, node: NegativeLookahead) -> tuple[None, str]:
        return None, f"self.negative_lookahead({self.call_helper(node)})"

    def get_repeated(self, node):
        if isinstance(node.node, NameLeaf):
            args = ", ".join([a for a in self.lookahead_call_helper(node) if a])
            return f"self.repeated({args})"
        name, _ = self.visit(Rhs([Alt([NamedItem(None, node.node)])]))
        return f"self.repeated(self.{name})"

    def visit_Repeat0(self, node: Repeat0) -> tuple[str, str]:
        if node in self.cache:
            return self.cache[node]
        # Also a trailing comma! to make this a tuple result
        func = self.get_repeated(node) + ","
        self.cache[node] = "zero_or_more", func
        return self.cache[node]

    def visit_Repeat1(self, node: Repeat1) -> tuple[str, str]:
        if node in self.cache:
            return self.cache[node]
        self.cache[node] = "one_or_more", self.get_repeated(node)
        return self.cache[node]


class XonshParserGenerator(PythonParserGenerator):
    def __init__(
        self,
        grammar: grammar.Grammar,
        file: IO[str] | None,
        unreachable_formatting: str | None = None,
    ):
        self.tokens_enum = Token
        tokens = {t.name for t in Token}
        tokens.update(["SOFT_KEYWORD", "KEYWORD", "ANY_TOKEN"])
        ParserGenerator.__init__(self, grammar, tokens, file)
        self._rhs_func_cache: dict[str, tuple[str, Rhs]] = {}
        self.callmakervisitor = XonshCallMakerVisitor(self)
        self.invalidvisitor = InvalidNodeVisitor()
        self.usednamesvisitor = UsedNamesVisitor()
        self.unreachable_formatting = unreachable_formatting or "None  # pragma: no cover"
        self.location_formatting = "**self.span(_lnum, _col)"
        self.cleanup_statements: list[str] = []

    def artifical_rule_from_rhs(self, rhs: Rhs) -> str:
        self.counter += 1
        name = f"_tmp_{self.counter}"  # TODO: Pick a nicer name.
        if dup := self._rhs_func_cache.get(repr(rhs)):
            return dup[0]
        else:
            self._rhs_func_cache[repr(rhs)] = (name, rhs)
        self.todo[name] = Rule(name, None, rhs)
        return name

    def generate(self, filename: str) -> None:
        header = self.grammar.metas.get("header", MODULE_PREFIX)
        if header is not None:
            self.print(header.rstrip("\n").format(filename=filename))
        subheader = self.grammar.metas.get("subheader", "")
        if subheader:
            self.print(subheader)
        cls_name = self.grammar.metas.get("class", "GeneratedParser")
        self.print("# Keywords and soft keywords are listed at the end of the parser definition.")
        self.print(f"class {cls_name}(Parser):")
        while self.todo:
            for rulename, rule in list(self.todo.items()):
                del self.todo[rulename]
                self.print()
                with self.indent():
                    self.visit(rule)

        self.print()
        with self.indent():
            self.print(f"KEYWORDS = {tuple(sorted(self.callmakervisitor.keywords))} # fmt: skip")
            self.print(f"SOFT_KEYWORDS = {tuple(sorted(self.callmakervisitor.soft_keywords))} # fmt: skip")

        trailer = self.grammar.metas.get("trailer", MODULE_SUFFIX.format(class_name=cls_name))
        if trailer is not None:
            self.print(trailer.rstrip("\n"))

    def add_return(self, ret_val: str) -> None:
        for stmt in self.cleanup_statements:
            self.print(stmt)
        # terse representation of return values
        ret_val = ast.unparse(ast.parse(ret_val))
        self.print(f"return {ret_val}")

    def visit_Rule(self, node: Rule) -> None:
        is_loop = node.is_loop()
        is_gather = node.is_gather()
        rhs = node.flatten()
        method_args = ""
        if node.left_recursive:
            if node.leader:
                self.print("@memoize_left_rec")
            else:
                # Non-leader rules in a cycle are not memoized,
                # but they must still be logged.
                self.print("@logger")
        elif node.memo:
            self.print("@memoize")
            # method_args = ", mark: Mark"
        node_type = node.type or "Any"
        self.print(f"def {node.name}(self{method_args}) -> {node_type} | None:")
        with self.indent():
            self.print(f"# {node.name}: {rhs}")
            if node.nullable:
                self.print(f"# nullable={node.nullable}")

            if node.name.endswith("without_invalid"):
                self.print("_prev_call_invalid = self.call_invalid_rules")
                self.print("self.call_invalid_rules = False")
                self.cleanup_statements.append("self.call_invalid_rules = _prev_call_invalid")

            # special case to reduce generated code size
            if (
                len(node.rhs.alts) > 1
                and (not any(a.action for a in node.rhs.alts))
                and (not any(len(a.items) > 1 for a in node.rhs.alts))
            ):
                self.print("return self.seq_alts(")
                alt_funcs = itertools.chain.from_iterable(a.items for a in node.rhs.alts)
                for fn in alt_funcs:
                    head, tail = self.callmakervisitor.lookahead_call_helper(fn, nested=False)
                    if tail:
                        self.print(f"({head}, {tail}), ")
                    else:
                        self.print(f"{head}, ")
                self.print(")")
                return

            self.print("mark = self._mark()")
            if self.alts_uses_locations(node.rhs.alts):
                self.print("_lnum, _col = self._tokenizer.peek().start")
            if is_loop:
                self.print("children = []")
            self.visit(rhs, is_loop=is_loop, is_gather=is_gather)
            if is_loop:
                self.add_return("children")
            else:
                self.add_return("None")

        if node.name.endswith("without_invalid"):
            self.cleanup_statements.pop()

    def print_action(
        self,
        action: str | None,
        locations: bool,
        unreachable: bool,
        is_gather: bool,
        is_loop: bool,
        has_invalid: bool,
    ) -> None:
        if not action:
            if is_gather:
                assert len(self.local_variable_names) == 2
                action = f"[{self.local_variable_names[0]}] + {self.local_variable_names[1]}"
            elif has_invalid:
                assert unreachable
                assert isinstance(action, str)  # for type checker
            elif len(self.local_variable_names) == 1:
                action = f"{self.local_variable_names[0]}"
            else:
                action = f"[{', '.join(self.local_variable_names)}]"

        if is_loop:
            self.print(f"children.append({action})")
            self.print("mark = self._mark()")
        else:
            self.add_return(f"{action}")

    def print(self, *args: object) -> None:
        super().print(*args)
        self.file.flush()


def main(output_file=None, grammar_file=None):
    output_file = output_file or Path(__file__).parent.parent / "peg_parser" / "parser.py"
    grammar_file = grammar_file or Path(__file__).with_name("xonsh.gram")
    grammar, *_ = build_parser(str(grammar_file))
    with output_file.open("w") as file:
        gen = XonshParserGenerator(grammar, file)
        gen.generate(str(grammar_file))
    return gen


def cli_parser():
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("-g", type=Path)
    parser.add_argument("-o", type=Path)
    return parser


if __name__ == "__main__":
    args = cli_parser().parse_args()
    main(args.o, args.g)
