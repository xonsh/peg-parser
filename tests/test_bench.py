def main():
    from peg_parser.parser import XonshParser

    src_txt = "print(1)"
    return XonshParser.parse_string(src_txt, mode="eval")


def large_file():
    from pathlib import Path

    from peg_parser.parser import XonshParser

    file = Path(__file__).parent.parent / "peg_parser" / "parser.py"
    print(f"file: {file}")
    assert file.exists()
    return XonshParser.parse_file(file)


def test_parse_string(benchmark):
    # benchmark something
    result = benchmark(main)

    # Extra code, to verify that the run completed correctly.
    # Sometimes you may want to check the result, fast functions
    # are no good if they return incorrect results :-)
    assert result


def test_parse_file(benchmark):
    # benchmark something
    result = benchmark(large_file)

    # Extra code, to verify that the run completed correctly.
    # Sometimes you may want to check the result, fast functions
    # are no good if they return incorrect results :-)
    assert result
