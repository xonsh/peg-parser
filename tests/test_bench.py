from pathlib import Path

import pytest


@pytest.fixture
def pegen_parser():
    from peg_parser.parser import XonshParser

    return XonshParser


@pytest.fixture
def ruff_parser():
    try:
        import xonsh_rd_parser as parser
    except ImportError:
        pytest.skip("xonsh_rd_parser not installed")
    return parser


@pytest.fixture
def ply_parser():
    try:
        from xonsh.parser import Parser
    except ImportError:
        pytest.skip("xonsh not installed")
    return Parser()


@pytest.mark.benchmark(group="small-string")
class TestBenchSmallString:
    src_txt = "print(1)"

    def test_peg(self, benchmark, pegen_parser):
        @benchmark
        def main():
            return pegen_parser.parse_string(self.src_txt, mode="eval")

    def test_ruff(self, benchmark, ruff_parser):
        @benchmark
        def main():
            return ruff_parser.parse_string(self.src_txt)

    def test_ply(self, benchmark, ply_parser):
        @benchmark
        def main():
            return ply_parser.parse(self.src_txt)


@pytest.mark.benchmark(group="large-file")
class TestBenchLargeFile:
    file = Path(__file__).parent.parent / "peg_parser" / "parser.py"

    def test_pegen(self, benchmark, pegen_parser):
        @benchmark
        def main():
            return pegen_parser.parse_file(self.file)

    def test_ruff(self, benchmark, ruff_parser):
        @benchmark
        def main():
            return ruff_parser.parse_file(str(self.file))

    def test_ply(self, benchmark, ply_parser):
        @benchmark
        def main():
            return ply_parser.parse(self.file.read_text(), filename=str(self.file))
