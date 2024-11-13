"""Implements the xonsh parser."""

from pathlib import Path
from typing import TYPE_CHECKING

from .platform import PYTHON_VERSION_INFO

if TYPE_CHECKING:
    from .parsers.base import BaseParser


def get_parser_cls(version: tuple[int, ...] | None = None) -> type["BaseParser"]:
    """Returns the parser class for the given Python version."""
    if version is None:
        version = PYTHON_VERSION_INFO
        if version > (3, 10):
            version = (3, 10)
    module = "v" + "".join(str(v) for v in version[:2])
    module = __package__ + ".parsers." + module

    from importlib import import_module

    return import_module(module).Parser


def write_parser_table(
    yacc_debug=False, output_path: None | Path | str = None, version=None, **kwargs
) -> Path:
    from .ply import write_utils, yacc

    cls = get_parser_cls(version)

    if output_path is None:
        output_path = cls.default_table_name()
    elif isinstance(output_path, str):
        output_path = Path(output_path)

    if output_path.exists():
        return output_path

    parser = yacc.yacc(
        debug=yacc_debug,
        start="start_symbols",
        module=cls(is_write_table=True, **kwargs),
    )
    return write_utils.write_to_file(parser, output_path=output_path)
