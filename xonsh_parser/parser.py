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


def write_parser_table(yacc_debug=False, output_path: Path = None) -> Path:
    if output_path and output_path.exists():
        return output_path

    from .ply import yacc

    cls = get_parser_cls()
    module = cls()
    py_version = ".".join(str(x) for x in PYTHON_VERSION_INFO[:2])
    format = "v1"
    filename = f"{cls.__name__}.table.{py_version}.{format}.pickle"
    if not output_path:
        output_path = Path(__file__).parent / filename
    yacc_kwargs = dict(
        module=module,
        debug=yacc_debug,
        start="start_symbols",
        output_path=str(output_path),
    )
    if not yacc_debug:
        yacc_kwargs["errorlog"] = yacc.NullLogger()
    # create parser on main thread
    return Path(yacc.yacc(**yacc_kwargs))
