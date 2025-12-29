from pathlib import Path
from typing import ClassVar

import pytest


class BaseParser:
    parsers: ClassVar = []

    def __init_subclass__(cls, **kwargs):
        cls.parsers.append(cls)

    def parse_string(self, src_txt: str):
        raise NotImplementedError

    def parse_file(self, file):
        raise NotImplementedError


class PegenParser(BaseParser):
    def __init__(self):
        from peg_parser.parser import XonshParser

        self.parser = XonshParser

    def parse_string(self, src_txt):
        return self.parser.parse_string(src_txt, mode="exec")

    def parse_file(self, file):
        return self.parser.parse_file(file)


class PegenV0Parser(BaseParser):
    """Python parser generated from pegen project.
    Compare it to see if we made any improvements with our pegen iterations"""

    def __init__(self):
        import pegen.py_parser as parser

        self.parser = parser

    def parse_string(self, src_txt):
        return self.parser.parse_string(src_txt, mode="exec")

    def parse_file(self, file):
        return self.parser.parse_file(file)


class RuffParser(BaseParser):
    def __init__(self):
        try:
            from xonsh_rd_parser import Parser
        except ImportError:
            pytest.skip("xonsh_rd_parser not installed")
        self.parser = Parser

    def parse_string(self, src_txt):
        return self.parser(src_txt).parse()

    def parse_file(self, file):
        return self.parser.parse_file(str(file))


class PlyParser(BaseParser):
    def __init__(self):
        try:
            from xonsh.parsers.v310 import Parser
        except ImportError:
            pytest.skip("xonsh not installed")
        self.parser = Parser()

    def parse_string(self, src_txt):
        return self.parser.parse(src_txt)

    def parse_file(self, file):
        return self.parser.parse(file.read_text())


class TreeSitter(BaseParser):
    def __init__(self):
        try:
            import tree_sitter_python as tspython
            from tree_sitter import Language, Parser
        except ImportError:
            pytest.skip("tree_sitter not installed")
        lang = Language(tspython.language())
        self.parser = Parser(lang)

    def parse_string(self, src_txt):
        return self.parser.parse(src_txt.encode("utf-8"))

    def parse_file(self, file):
        return self.parser.parse(file.read_bytes())


@pytest.fixture(params=BaseParser.parsers)
def parser(request) -> BaseParser:
    return request.param()


@pytest.mark.benchmark(group="small-string")
def test_small_string(benchmark, parser):
    src_txt = "print(1)"
    benchmark(parser.parse_string, src_txt)


@pytest.mark.benchmark(group="large-file")
def test_large_file(benchmark, parser):
    file = Path(__file__).parent.parent / "peg_parser" / "parser.py"
    benchmark(parser.parse_file, file)
