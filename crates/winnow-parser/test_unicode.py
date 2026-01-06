from winnow_parser import tokenize


def test_unicode_identifiers():
    code = "α = 1"
    tokens = tokenize(code)
    print(f"Tokens: {tokens}")
    for t in tokens:
        print(f"Token: type={t.type}, string='{t.string}', bytes={getattr(t, 'bytes', 'N/A')}")

    names = [t.string for t in tokens if t.type.name == "NAME"]
    print(f"Names: {names}")
    assert "α" in names
    print("Unicode identifier test passed")


def test_unicode_strings():
    code = 'x = "β"'
    tokens = tokenize(code)
    strings = [t.string for t in tokens if t.type.name == "STRING"]
    assert '"β"' in strings
    print("Unicode string test passed")


if __name__ == "__main__":
    try:
        test_unicode_identifiers()
        test_unicode_strings()
    except AssertionError as e:
        print(f"Assertion failed: {e}")
        exit(1)
