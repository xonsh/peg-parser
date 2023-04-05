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


def get_type(obj):
    def name(obj):
        return type(obj).__name__

    if isinstance(obj, (list, tuple)):
        inner = set(get_type(i) for i in obj)
        container = name(obj)
        return f"{container}[{'|'.join(inner)}]"
    elif isinstance(obj, dict):
        inner = set(f"{k}: {get_type(v)}" for k, v in obj.items())
        container = name(obj)
        return f"{container}[{'|'.join(inner)}]"
    return name(obj)
