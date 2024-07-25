from pathlib import Path

import pytest


@pytest.mark.benchmark(group="small-string")
class TestBenchSmallString:
    def test_peg(self, benchmark):
        @benchmark
        def main():
            from peg_parser.parser import XonshParser

            src_txt = "print(1)"
            return XonshParser.parse_string(src_txt, mode="eval")

    # def test_ruff(self, benchmark):
    #     @benchmark
    #     def main():
    #         import xonsh_rd_parser as parser
    #
    #         src_txt = "print(1)"
    #         return parser.parse_string(src_txt)


@pytest.mark.benchmark(group="large-file")
class TestBenchLargeFile:
    file = Path(__file__).parent.parent / "peg_parser" / "parser.py"

    def test_pegen(self, benchmark):
        @benchmark
        def main():
            from peg_parser.parser import XonshParser

            return XonshParser.parse_file(self.file)

    # def test_ruff(self, benchmark):
    #     @benchmark
    #     def main():
    #         import xonsh_rd_parser as parser
    #         return parser.parse_file(str(self.file))
