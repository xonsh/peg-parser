def main():
    from peg_parser.parser import XonshParser

    src_txt = "print(1)"
    ast = XonshParser.parse_string(src_txt, mode="eval")
    print(f"ast: {ast}", type(ast))


if __name__ == "__main__":
    from bench_utils import timeit, trace

    with timeit(), trace():
        main()
