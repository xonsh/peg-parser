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


def _write_tmp(name: str = "xonsh-lr-table", ext="py"):
    from pathlib import Path

    from xonsh_parser.parser import write_parser_table

    path = Path(f"/tmp/{name}.{ext}")
    if path.exists():
        path.unlink()
    write_parser_table(output_path=path, yacc_debug=True)


if __name__ == "__main__":
    # main()
    _write_tmp(ext="pickle")
    _write_tmp(ext="cpickle")
    _write_tmp(ext="jsonl")
    _write_tmp(ext="py")
