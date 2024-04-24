def main():
    from parser_lib import parse_string

    src_txt = "print(1)"
    ast = parse_string(src_txt, mode="eval")
    print(f"ast: {ast}", type(ast))


if __name__ == "__main__":
    from bench_utils import timeit, trace

    with timeit(), trace():
        main()
