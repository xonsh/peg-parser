# for testing with monkeytype run


def main():
    from xonsh_parser.parser import get_parser_cls

    parser = get_parser_cls()()

    # cmd line
    parser.parse("ls -alh")

    try:
        # invalid syntax
        parser.parse("print(1")
    except Exception:
        pass


if __name__ == "__main__":
    # main()
    from pathlib import Path

    from xonsh_parser.parser import write_parser_table

    write_parser_table(output_path=Path("/tmp/bytes-2.pickle"))
