# for testing with monkeytype run

from xonsh_parser.parser import get_parser_cls

parser = get_parser_cls()()
parser.parse("ls -alh")
