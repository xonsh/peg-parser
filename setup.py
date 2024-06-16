import os
import sys
from contextlib import suppress
from pathlib import Path

from setuptools import Command, setup
from setuptools.command.build import build


class CustomCommand(Command):
    def initialize_options(self) -> None:
        self.bdist_dir = None

    def finalize_options(self) -> None:
        with suppress(Exception):
            self.bdist_dir = Path(self.get_finalized_command("bdist_wheel").bdist_dir)

    def run(self) -> None:
        if self.bdist_dir:
            root_dir = os.path.abspath(os.path.dirname(__file__))
            sys.path.insert(0, root_dir)
            from tasks import generate_parser

            self.bdist_dir.mkdir(parents=True, exist_ok=True)
            generate_parser.main()


class CustomBuild(build):
    sub_commands = [("build_custom", None), *build.sub_commands]  # noqa: RUF012


options = {}

if os.environ.get("REGENERATE_PARSER"):
    cmdclass = {"build": CustomBuild, "build_custom": CustomCommand}
    options["cmdclass"] = cmdclass

if os.environ.get("COMPILE_WITH_MYPYC"):
    from mypyc.build import mypycify

    options["ext_modules"] = mypycify(
        [
            "peg_parser/tokenize.py",
            "peg_parser/tokenizer.py",
            "peg_parser/subheader.py",
            "peg_parser/parser.py",
        ]
    )


setup(**options)
