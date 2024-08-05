# Write the benchmarking functions here.
# See "Writing benchmarks" in the asv docs for more information.

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from tests.benchmarks import BaseParser

small_string = "print(1)"
file = Path(__file__).parent.parent / "peg_parser" / "parser.py"



class TimeSuite:
    params = BaseParser.parsers
    def setup(self, parser):
        self.parser = parser()

    def time_parse_small_string(self, _):
        self.parser.parse_string(small_string)

    def time_large_files(self, _):
        self.parser.parse_file(file)


class PeakMemSuite:
    params = BaseParser.parsers
    def setup(self, parser):
        self.parser = parser()

    def peakmem_parser_small_string(self, _):
        self.parser.parse_string(small_string)

    def peakmem_parser_large_string(self, _):
        self.parser.parse_file(file)

def get_process_memory():
    from psutil import Process

    p = Process()
    return p.memory_info().rss

class TrackSuite:
    params = BaseParser.parsers
    units = "bytes"

    def setup(self, parser):
        self.parser = parser()


    def track_mem_small_string(self, _):
        self.parser.parse_string(small_string)
        return get_process_memory()

    def track_mem_large_file(self, _):
        self.parser.parse_file(file)
        return get_process_memory()

def timeraw_import_parser():
    return """
    from peg_parser.parser import XonshParser
    """
