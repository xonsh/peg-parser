# Write the benchmarking functions here.
# See "Writing benchmarks" in the asv docs for more information.
from pathlib import Path


class TimeSuite:
    def setup(self):
        from xonsh_parser.parser import write_parser_table
        write_parser_table()


    def time_parser_init(self):
        from xonsh_parser.parser import get_parser_cls

        parser = get_parser_cls()()
        parser.parse("ls -alh")


class MemSuite:
    def setup(self):
        from xonsh_parser.parser import write_parser_table
        write_parser_table()

    def mem_parser_init(self):
        from xonsh_parser.parser import get_parser_cls

        parser = get_parser_cls()()
        return parser.parser


class PeakMemSuite:
    params = ["/tmp/xonsh-lr-table.pickle", "/tmp/xonsh-lr-table.py", "/tmp/xonsh-lr-table.jsonl"]
    def setup(self, f):
        from xonsh_parser.parser import write_parser_table
        write_parser_table(output_path=f)

    def peakmem_parser_init_(self, f):

        from xonsh_parser.parser import get_parser_cls

        parser = get_parser_cls()(parser_table=Path(f))
        parser.parse("ls -alh")


class TrackLrParserSize:
    unit = "bytes"
    params = ["/tmp/xonsh-lr-table.pickle", "/tmp/xonsh-lr-table.py", "/tmp/xonsh-lr-table.jsonl",
              "/tmp/xonsh-lr-table.cpickle"]

    def setup(self, f):
        from xonsh_parser.parser import write_parser_table
        write_parser_table(output_path=f)

    def track_lr_parser_size(self, f):
        from pympler import asizeof

        from xonsh_parser.parser import get_parser_cls

        parser = get_parser_cls()(parser_table=Path(f))
        return asizeof.asizeof(parser.parser)
