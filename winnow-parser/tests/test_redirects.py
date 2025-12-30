import pytest


def test_redirect(check_xonsh_ast):
    assert check_xonsh_ast("$[cat < input.txt]")
    assert check_xonsh_ast("$[< input.txt cat]")


@pytest.mark.parametrize(
    "case",
    [
        "$[cat < /path/to/input.txt]",
        "$[(cat) < /path/to/input.txt]",
        "$[< /path/to/input.txt cat]",
        "![< /path/to/input.txt]",
        "![< /path/to/input.txt > /path/to/output.txt]",
    ],
)
def test_redirect_abspath(case, check_xonsh_ast):
    assert check_xonsh_ast(case)


@pytest.mark.parametrize("case", ["", "o", "out", "1"])
def test_redirect_output(case, check_xonsh_ast):
    assert check_xonsh_ast(f'$[echo "test" {case}> test.txt]')
    assert check_xonsh_ast(f'$[< input.txt echo "test" {case}> test.txt]')
    assert check_xonsh_ast(f'$[echo "test" {case}> test.txt < input.txt]')


@pytest.mark.parametrize("case", ["e", "err", "2"])
def test_redirect_error(case, check_xonsh_ast):
    assert check_xonsh_ast(f'$[echo "test" {case}> test.txt]', False)
    assert check_xonsh_ast(f'$[< input.txt echo "test" {case}> test.txt]', False)
    assert check_xonsh_ast(f'$[echo "test" {case}> test.txt < input.txt]', False)


@pytest.mark.parametrize("case", ["a", "all", "&"])
def test_redirect_all(case, check_xonsh_ast):
    assert check_xonsh_ast(f'$[echo "test" {case}> test.txt]', False)
    assert check_xonsh_ast(f'$[< input.txt echo "test" {case}> test.txt]', False)
    assert check_xonsh_ast(f'$[echo "test" {case}> test.txt < input.txt]', False)


@pytest.mark.parametrize(
    "r",
    [
        "e>o",
        "e>out",
        "err>o",
        "2>1",
        "e>1",
        "err>1",
        "2>out",
        "2>o",
        "err>&1",
        "e>&1",
        "2>&1",
    ],
)
@pytest.mark.parametrize("o", ["", "o", "out", "1"])
def test_redirect_error_to_output(r, o, check_xonsh_ast):
    assert check_xonsh_ast(f'$[echo "test" {r} {o}> test.txt]', False)
    assert check_xonsh_ast(f'$[< input.txt echo "test" {r} {o}> test.txt]', False)
    assert check_xonsh_ast(f'$[echo "test" {r} {o}> test.txt < input.txt]', False)


@pytest.mark.parametrize(
    "r",
    [
        "o>e",
        "o>err",
        "out>e",
        "1>2",
        "o>2",
        "out>2",
        "1>err",
        "1>e",
        "out>&2",
        "o>&2",
        "1>&2",
    ],
)
@pytest.mark.parametrize("e", ["e", "err", "2"])
def test_redirect_output_to_error(r, e, check_xonsh_ast):
    assert check_xonsh_ast(f'$[echo "test" {r} {e}> test.txt]', False)
    assert check_xonsh_ast(f'$[< input.txt echo "test" {r} {e}> test.txt]', False)
    assert check_xonsh_ast(f'$[echo "test" {r} {e}> test.txt < input.txt]', False)
