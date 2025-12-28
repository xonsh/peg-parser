import os
import sys

# Add the directory containing the built .so to the path
sys.path.insert(0, os.path.abspath("winnow-parser"))

try:
    from winnow_parser import Token as t
    from winnow_parser import tokenize
except ImportError as e:
    print(f"Error importing winnow_parser: {e}")
    sys.exit(1)


def print_tokens(label, s):
    print(f"--- {label}: {s!r} ---")
    tokens = tokenize(s)
    for tok in tokens:
        if tok.typ == t.ENDMARKER:
            continue
        # Use repr() to see the token type name
        print(f"  {tok.typ!r:25} {tok.get_string(s)!r:15} col:{tok.start[1]}")


print_tokens("test_pymode_not_ioredirect", "a>b")
print_tokens("test_path_fstring_literal", 'fp"/foo"')
print_tokens("test_fstring_nested_py312", "f'{a+b:.3f} more words {c+d=} final words'")
