# Write the benchmarking functions here.
# See "Writing benchmarks" in the asv docs for more information.


def parse(code: str):
    from peg_parser.parser import XonshParser
    return XonshParser.parse_string(code, mode="exec")


class TimeSuite:
    def time_parser_init(self):
        parse("![ls -alh]")


class MemSuite:
    def mem_parser_init(self):
        parse("![ls -alh]")

class PeakMemSuite:
    def peakmem_parser_init_(self):
        parse("![ls -alh]")
