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


def ply_small_string():
    from ply_parser.parser import get_parser_cls

    parser = get_parser_cls()()
    ast = parser.parse("print(1)")
    print(f"PLY v2 -> ast: {ast}", type(ast))


def xonsh_ply_small_string():
    from xonsh.parser import Parser

    parser = Parser()
    ast = parser.parse("print(1)")
    print(f"Xonsh parser -> ast: {ast}", type(ast))


if __name__ == "__main__":
    from bench_utils import timeit, trace

    with timeit(), trace():
        #     main()
        #     large_file()
        #     ply_small_string()
        xonsh_ply_small_string()
