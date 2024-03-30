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


def _write_tmp(name: str):
    from pathlib import Path

    from xonsh_parser.parser import write_parser_table

    path = Path(f"/tmp/{name}")
    if path.exists():
        path.unlink()
    write_parser_table(output_path=path, yacc_debug=True)


if __name__ == "__main__":
    # main()
    _write_tmp("bytes-3.pickle")
    _write_tmp("bytes-2.py")
    _write_tmp("bytes-2.jsonl")
