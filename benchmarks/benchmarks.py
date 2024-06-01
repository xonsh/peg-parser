# Write the benchmarking functions here.
# See "Writing benchmarks" in the asv docs for more information.

from pathlib import Path

small_code = "![ls -alh]"
file = Path(__file__).parent.parent / "peg_parser" / "parser.py"

def parse(code: str | Path):
    from peg_parser.parser import XonshParser
    if isinstance(code, str):
        return XonshParser.parse_string(code, mode="exec")
    return XonshParser.parse_file(code)


class TimeSuite:
    def time_parse_small_string(self):
        parse(small_code)

    def time_large_files(self):
        parse(file)


class PeakMemSuite:
    def peakmem_parse_small(self):
        parse("![ls -alh]")

    def peakmem_parser_large_file(self):
        parse(file)


def timeraw_import_parser():
    return """
    from peg_parser.parser import XonshParser
    """
