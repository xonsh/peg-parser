import string
from pathlib import Path

from pegen.build import build_python_parser_and_generator


def main():
    grammar_path = Path(__file__).parent.parent / "parser" / "xonsh.gram"
    tmpl = string.Template(grammar_path.read_text())
    gram_content = tmpl.substitute(
        subheader=grammar_path.with_name("subheader.py").read_text(),
        trailer=grammar_path.with_name("trailer.py").read_text(),
    )
    with grammar_path.with_name("full.gram").open(mode="w") as fw:
        skip = False
        for lin in gram_content.splitlines(keepends=True):
            if lin.startswith("# <!--"):
                skip = True
            elif lin.startswith("# -->"):
                skip = False
                continue
            if skip:
                continue
            fw.write(lin)

    output = "xonsh_parser.py"

    grammar, parser, tokenizer, gen = build_python_parser_and_generator(fw.name, output)

    return grammar, parser, tokenizer, gen


if __name__ == "__main__":
    main()
