"""Implements the xonsh parser."""


def get_parser():
    from .platform import PYTHON_VERSION_INFO

    if PYTHON_VERSION_INFO > (3, 10):
        from .parsers.v310 import Parser as p
    elif PYTHON_VERSION_INFO > (3, 9):
        from .parsers.v39 import Parser as p
    elif PYTHON_VERSION_INFO > (3, 8):
        from .parsers.v38 import Parser as p
    else:
        from .parsers.v36 import Parser as p
    return p()
