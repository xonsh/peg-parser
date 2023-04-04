def test_write_table(tmp_path):
    from xonsh_parser.parser import write_parser_table

    path = write_parser_table(output_path=tmp_path / "parser_table.jsonl")
    assert path.exists()


def test_basic(parser_table):
    from xonsh_parser.parser import get_parser_cls

    p = get_parser_cls()(parser_table)
    p.parse("ls -alh")
