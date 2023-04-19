# Write the benchmarking functions here.
# See "Writing benchmarks" in the asv docs for more information.


class TimeSuite:
    """
    An example benchmark that times the performance of various kinds
    of iterating over dictionaries in Python.
    """

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
    def setup(self):
        from xonsh_parser.parser import write_parser_table

        write_parser_table()

    def peakmem_parser_init(self):
        from xonsh_parser.parser import get_parser_cls

        parser = get_parser_cls()()
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
