from pathlib import Path
from typing import IO, Any

from peg_parser.tokenize import Token
from pegen import grammar
from pegen.build import build_parser
from pegen.grammar import (
    NameLeaf,
)
from pegen.parser_generator import ParserGenerator
from pegen.python_generator import (
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

    def visit_NameLeaf(self, node: NameLeaf) -> tuple[str | None, str]:
        name = node.value
        special = {"SOFT_KEYWORD", "KEYWORD", "NAME", "ANY_TOKEN"}
        if name in special:
            name = name.lower()
            return name, f"self.{name}()"
        if name.isupper() and (name in self.gen.tokens):
            token = self.gen.tokens_enum[name]
            return "_" + name.lower(), f"self.token({token.__class__.__name__}.{token.name})"
        return name, f"self.{name}()"


class XonshParserGenerator(PythonParserGenerator):
    def __init__(
        self,
        grammar: grammar.Grammar,
        file: IO[str] | None,
        location_formatting: str | None = None,
        unreachable_formatting: str | None = None,
    ):
        self.tokens_enum = Token
        tokens = {t.name for t in Token}
        tokens.update(["SOFT_KEYWORD", "KEYWORD", "ANY_TOKEN"])
        ParserGenerator.__init__(self, grammar, tokens, file)
        self.callmakervisitor = XonshCallMakerVisitor(self)
        self.invalidvisitor = InvalidNodeVisitor()
        self.usednamesvisitor = UsedNamesVisitor()
        self.unreachable_formatting = unreachable_formatting or "None  # pragma: no cover"
        self.location_formatting = (
            location_formatting
            or "lineno=start_lineno, col_offset=start_col_offset, "
            "end_lineno=end_lineno, end_col_offset=end_col_offset"
        )
        self.cleanup_statements: list[str] = []


def main(output_file: Path, grammar_file: Path):
    grammar, *_ = build_parser(str(grammar_file))
    with output_file.open("w") as file:
        gen = XonshParserGenerator(grammar, file)
        gen.generate(str(grammar_file))
    return gen


def cli_parser():
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument("-g", type=Path, default=Path(__file__).with_name("xonsh.gram"))
    parser.add_argument("-o", type=Path, default=Path(__file__).parent.parent / "peg_parser" / "parser.py")
    return parser


if __name__ == "__main__":
    args = cli_parser().parse_args()
    main(args.o, args.g)
