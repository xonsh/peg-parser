def main():
    from peg_parser.parser import XonshParser

    src_txt = "print(1)"
    ast = XonshParser.parse_string(src_txt, mode="eval")
    print(f"ast: {ast}", type(ast))


def large_file():
    from pathlib import Path

    from peg_parser.parser import XonshParser

    file = Path(__file__).parent.parent / "peg_parser" / "parser.py"
    print(f"file: {file}")
    assert file.exists()
    XonshParser.parse_file(file)


if __name__ == "__main__":
    from bench_utils import timeit, trace

    with timeit(), trace():
        main()
    with timeit(), trace():
        large_file()
