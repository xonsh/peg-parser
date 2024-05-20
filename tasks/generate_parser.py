from pathlib import Path

from peg_parser import token
from pegen.build import build_parser
from pegen.python_generator import PythonParserGenerator


def main():
    output_file = Path(__file__).parent.parent / "peg_parser" / "parser.py"
    grammar_file = Path(__file__).with_name("xonsh.gram")

    grammar, _, _ = build_parser(str(grammar_file))
    tokens = {name: num for num, name in token.tok_name.items()}
    with output_file.open("w") as file:
        gen = PythonParserGenerator(grammar, file, token_map=tokens)
        gen.generate(str(grammar_file))
    return gen


if __name__ == "__main__":
    main()
