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
        from xonsh_parser.parser import get_parser

        parser = get_parser()
        parser.parse("ls -alh")


class MemSuite:
    def mem_parser_init(self):
        from xonsh_parser.parser import get_parser

        return get_parser()


class PeakMemSuite:
    def peakmem_parser_init(self):
        from xonsh_parser.parser import get_parser

        parser = get_parser()
        parser.parse("ls -alh")
