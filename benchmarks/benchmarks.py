# Write the benchmarking functions here.
# See "Writing benchmarks" in the asv docs for more information.


class TimeSuite:
    """
    An example benchmark that times the performance of various kinds
    of iterating over dictionaries in Python.
    """

    # def setup(self):
    #     self.d = {}

    def time_parser_init(self):
        from xonsh_parser.parser import get_parser_cls

        parser = get_parser_cls()()
        parser.parse("ls -alh")


class MemSuite:
    def mem_parser_init(self):
        from xonsh_parser.parser import get_parser_cls

        parser = get_parser_cls()()
        return parser.parser


class PeakMemSuite:
    def peakmem_parser_init(self):
        from xonsh_parser.parser import get_parser_cls

        parser = get_parser_cls()()
        parser.parse("ls -alh")


class TrackLrParserSize:
    unit = "bytes"

    def track_lr_parser_size(self):
        from xonsh_parser.parser import get_parser_cls
        from pympler import asizeof

        parser = get_parser_cls()()
        return asizeof.asizeof(parser.parser)
