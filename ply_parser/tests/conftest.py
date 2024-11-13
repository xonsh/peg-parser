import pytest

from .tools import nodes_equal


@pytest.fixture(scope="session")
def parser_table():
    """make sure that default parser table is available for the whole test session"""
    from ply_parser.parser import write_parser_table

    return write_parser_table()


@pytest.fixture(scope="session")
def parser(parser_table):
    """return parser instance"""
    from ply_parser.parser import get_parser_cls

    inst = get_parser_cls()(parser_table)

    yield inst

    inst.reset()


@pytest.fixture
def check_ast(parser):
    import ast

    def factory(inp: str, run=True, mode="eval", debug_level=0):
        # __tracebackhide__ = True
        # expect a Python AST
        exp = ast.parse(inp, mode=mode)
        # observe something from xonsh
        obs = parser.parse(inp, debug_level=debug_level)
        # Check that they are equal
        assert nodes_equal(exp, obs)
        # round trip by running xonsh AST via Python
        if run:
            exec(compile(obs, "<test-ast>", mode))

    return factory


@pytest.fixture
def check_stmts(check_ast):
    def factory(inp, run=True, mode="exec", debug_level=0):
        __tracebackhide__ = True
        if not inp.endswith("\n"):
            inp += "\n"
        check_ast(inp, run=run, mode=mode, debug_level=debug_level)

    return factory


@pytest.fixture
def check_xonsh_ast(xsh, parser):
    def factory(
        xenv,
        inp,
        run=True,
        mode="eval",
        debug_level=0,
        return_obs=False,
        globals=None,
        locals=None,
    ):
        xsh.env.update(xenv)
        obs = parser.parse(inp, debug_level=debug_level)
        if obs is None:
            return  # comment only
        bytecode = compile(obs, "<test-xonsh-ast>", mode)
        if run:
            exec(bytecode, globals, locals)
        return obs if return_obs else True

    return factory


@pytest.fixture
def check_xonsh(check_xonsh_ast):
    def factory(xenv, inp, run=True, mode="exec"):
        __tracebackhide__ = True
        if not inp.endswith("\n"):
            inp += "\n"
        check_xonsh_ast(xenv, inp, run=run, mode=mode)

    return factory


@pytest.fixture
def eval_code(parser):
    def factory(inp, mode="eval", **loc_vars):
        obs = parser.parse(inp, debug_level=1)
        bytecode = compile(obs, "<test-xonsh-ast>", mode)
        return eval(bytecode, loc_vars)

    return factory
