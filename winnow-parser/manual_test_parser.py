import ast

import winnow_parser


def test_parser():
    code = """
def foo(x):
    return x + 1

if True:
    print("Hello")
    """

    print("Parsing code...")
    print(f"Code to parse:\n{code}")

    # Debug tokens
    print("Tokens:")
    try:
        tokens = winnow_parser.tokenize(code)
        for tok in tokens:
            print(f"  {tok}")
    except Exception as e:
        print(f"Tokenization failed: {e}")

    try:
        module = winnow_parser.parse_code(code)
        print("Successfully parsed!")
        print(ast.dump(module, indent=2))

        # Verify structure
        assert isinstance(module, ast.Module)
        assert len(module.body) == 2
        assert isinstance(module.body[0], ast.FunctionDef)
        assert module.body[0].name == "foo"
        assert isinstance(module.body[1], ast.If)

        print("\nVerification successful!")

    except Exception as e:
        print(f"Parsing failed: {e}")
        import traceback

        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    test_parser()
