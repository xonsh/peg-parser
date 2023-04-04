def test_basic():
    from xonsh_parser.parser import get_parser

    p = get_parser()
    # wait for thread to finish
    p.parse("ls -alh")
