# Write the benchmarking functions here.
# See "Writing benchmarks" in the asv docs for more information.


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
        from pathlib import Path

        from xonsh_parser.parser import get_parser_cls

        parser = get_parser_cls()(parser_table=Path(f))
        parser.parse("ls -alh")


class TrackLrParserSize:
    unit = "bytes"

    def setup(self):
        from xonsh_parser.parser import write_parser_table
        write_parser_table()

    def track_lr_parser_size(self):
        from pympler import asizeof

        from xonsh_parser.parser import get_parser_cls

        parser = get_parser_cls()()
        return asizeof.asizeof(parser.parser)
