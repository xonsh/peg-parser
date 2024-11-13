"""Common utility functions for PLY"""


# This object is a stand-in for a logging object created by the
# logging module.   PLY will use this by default to create things
# such as the parser.out file.  If a user wants more detailed
# information, they can create their own logging object and pass
# it into PLY.

resultlimit = 40  # Size limit of results when running in debug mode.


class PlyLogger:
    def __init__(self, f) -> None:
        self.f = f

    def debug(self, msg, *args, **kwargs) -> None:
        self.f.write((msg % args) + "\n")

    info = debug

    def warning(self, msg, *args, **kwargs) -> None:
        self.f.write("WARNING: " + (msg % args) + "\n")

    def error(self, msg, *args, **kwargs) -> None:
        self.f.write("ERROR: " + (msg % args) + "\n")

    critical = debug


# Null logger is used when no output is generated. Does nothing.
class NullLogger:
    def __getattribute__(self, name):
        return self

    def __call__(self, *args, **kwargs):
        return self


# Format the result message that the parser produces when running in debug mode.
def format_result(r) -> str:
    repr_str = repr(r)
    if "\n" in repr_str:
        repr_str = repr(repr_str)
    if len(repr_str) > resultlimit:
        repr_str = repr_str[:resultlimit] + " ..."
    result = f"<{type(r).__name__} @ 0x{id(r):x}> ({repr_str})"
    return result


# Format stack entries when the parser is running in debug mode
def format_stack_entry(r) -> str:
    repr_str = repr(r)
    if "\n" in repr_str:
        repr_str = repr(repr_str)
    if len(repr_str) < 16:
        return repr_str
    else:
        return f"<{type(r).__name__} @ 0x{id(r):x}>"
