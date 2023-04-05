# for testing with monkeytype run

from xonsh_parser.parser import get_parser_cls

parser = get_parser_cls()()

# cmd line
parser.parse("ls -alh")

try:
    # invalid syntax
    parser.parse("print(1")
except Exception:
    pass
