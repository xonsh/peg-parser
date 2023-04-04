def test_basic():
    from xonsh_parser.parser import get_parser_cls

    p = get_parser_cls()()
    # wait for thread to finish
    p.parse("ls -alh")

def test_write_table(tmp_path):
    from xonsh_parser.parser import write_parser_table

    path = write_parser_table(output_path=tmp_path / "parser_table.jsonl")
    assert path.exists()