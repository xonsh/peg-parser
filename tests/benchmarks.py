from pathlib import Path

import pytest


class BaseParser:
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


class RuffParser(BaseParser):
    def __init__(self):
        try:
            import xonsh_rd_parser as parser
        except ImportError:
            pytest.skip("xonsh_rd_parser not installed")
        self.parser = parser

    def parse_string(self, src_txt):
        return self.parser.parse_string(src_txt)

    def parse_file(self, file):
        return self.parser.parse_file(str(file))


class PlyParser(BaseParser):
    def __init__(self):
        try:
            from xonsh.parser import Parser
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


@pytest.fixture(params=[PegenParser, RuffParser, PlyParser, TreeSitter])
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
