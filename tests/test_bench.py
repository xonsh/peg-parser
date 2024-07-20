def main():
    from peg_parser.parser import XonshParser

    src_txt = "print(1)"
    return XonshParser.parse_string(src_txt, mode="eval")


def test_parse_string(benchmark):
    # benchmark something
    result = benchmark(main)

    # Extra code, to verify that the run completed correctly.
    # Sometimes you may want to check the result, fast functions
    # are no good if they return incorrect results :-)
    assert result
