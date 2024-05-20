from pathlib import Path

from peg_parser.parser import token
from pegen.build import build_parser
from pegen.python_generator import PythonParserGenerator


def main():
    grammar_file = Path(__file__).parent.parent / "parser" / "xonsh.gram"
    output_file = grammar_file.with_name("parser.py")

    grammar, _, _ = build_parser(str(grammar_file))
    tokens = {name: num for num, name in token.tok_name.items()}
    with output_file.open("w") as file:
        gen = PythonParserGenerator(grammar, file, token_map=tokens)
        gen.generate(str(grammar_file))
    return gen


if __name__ == "__main__":
    main()
