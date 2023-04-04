import pytest


@pytest.fixture(scope="session")
def parser_table():
    """make sure that default parser table is available for the whole test session"""
    from xonsh_parser.parser import write_parser_table

    return write_parser_table()


@pytest.fixture(scope="session")
def parser(parser_table):
    """return parser instance"""
    from xonsh_parser.parser import get_parser_cls

    inst = get_parser_cls()(parser_table)

    yield inst

    inst.reset()
