def test_basic():
    from xonsh_parser.parser import get_parser_cls

    p = get_parser_cls()()
    # wait for thread to finish
    p.parse("ls -alh")
