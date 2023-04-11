"""Implements the xonsh parser."""

from pathlib import Path

from .platform import PYTHON_VERSION_INFO


def get_parser_cls():
    if PYTHON_VERSION_INFO > (3, 10):
        from .parsers.v310 import Parser as p
    elif PYTHON_VERSION_INFO > (3, 9):
        from .parsers.v39 import Parser as p
    elif PYTHON_VERSION_INFO > (3, 8):
        from .parsers.v38 import Parser as p
    else:
        from .parsers.v36 import Parser as p
    return p


def write_parser_table(
    yacc_debug=False, output_path: None | Path = None, **kwargs
) -> Path:
    from .ply import yacc

    cls = get_parser_cls()

    output_path = output_path or cls.default_table_name()

    if output_path.exists():
        return output_path

    yacc_kwargs = dict(
        module=cls(is_write_table=True, **kwargs),
        debug=yacc_debug,
        start="start_symbols",
        output_path=str(output_path),
    )
    if not yacc_debug:
        yacc_kwargs["errorlog"] = yacc.NullLogger()
    # create parser on main thread
    return Path(yacc.yacc(**yacc_kwargs))
