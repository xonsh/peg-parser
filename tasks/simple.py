def print_memstats() -> bool:
    import sys

    import psutil

    mega_bytes = 2**20
    print("Memory stats:")
    process = psutil.Process()
    meminfo = process.memory_info()
    res = {}
    res["rss"] = meminfo.rss / mega_bytes
    res["vms"] = meminfo.vms / mega_bytes
    if sys.platform == "win32":
        res["maxrss"] = meminfo.peak_wset / mega_bytes
    else:
        # See https://stackoverflow.com/questions/938733/total-memory-used-by-python-process
        import resource  # Since it doesn't exist on Windows.

        rusage = resource.getrusage(resource.RUSAGE_SELF)
        if sys.platform == "darwin":
            factor = 1
        else:
            factor = 1024  # Linux
        res["maxrss"] = rusage.ru_maxrss * factor / mega_bytes
    for key, value in res.items():
        print(f"  {key:12.12s}: {value:10.0f} MiB")
    return True


def sm():
    """The minimum program uses around 16MB memory"""
    # Memory stats:
    #   rss         :         16 MiB
    #   vms         :     401345 MiB
    #   maxrss      :         16 MiB
    import ast

    tree = ast.parse("print(1)")
    print(ast.dump(tree))


def main():
    # Memory stats:
    #   rss         :         19 MiB
    #   vms         :     401474 MiB
    #   maxrss      :         19 MiB
    from peg_parser.parser import XonshParser

    src_txt = "print(1)"
    ast = XonshParser.parse_string(src_txt, mode="exec")
    print(f"ast: {ast}", type(ast))


def parse_large_file():
    from pathlib import Path

    from peg_parser.parser import XonshParser

    file = Path(__file__).parent.parent / "peg_parser" / "parser.py"
    parser = XonshParser
    parser.parse_file(file)


if __name__ == "__main__":
    # main()
    # sm()
    # print_memstats()
    parse_large_file()
