# for testing with monkeytype run


def main():
    from ply_parser.parser import get_parser_cls

    parser = get_parser_cls()()

    # cmd line
    print(parser.parse("ls -alh"))

    try:
        # invalid syntax
        parser.parse("print(1")
    except Exception as ex:
        print("Error:", ex)


def _write_tmp():
    from ply_parser.parser import write_parser_table

    write_parser_table(yacc_debug=True, overwrite_table=True)


if __name__ == "__main__":
    # main()
    _write_tmp()
