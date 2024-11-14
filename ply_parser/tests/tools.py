def get_type(obj):
    def name(obj):
        return type(obj).__name__

    if isinstance(obj, (list, tuple)):
        inner = set(get_type(i) for i in obj)
        container = name(obj)
        return f"{container}[{'|'.join(inner)}]"
    elif isinstance(obj, dict):
        inner = set(f"{k}: {get_type(v)}" for k, v in obj.items())
        container = name(obj)
        return f"{container}[{'|'.join(inner)}]"
    return name(obj)


def get_size(obj, seen=None):
    """Recursively finds size of objects"""
    import sys

    size = sys.getsizeof(obj)
    if seen is None:
        seen = set()

    obj_id = id(obj)
    if obj_id in seen:
        return 0

    # Important mark as seen *before* entering recursion to gracefully handle
    # self-referential objects
    seen.add(obj_id)

    if isinstance(obj, dict):
        size += sum([get_size(v, seen) for v in obj.values()])
        size += sum([get_size(k, seen) for k in obj.keys()])
    elif hasattr(obj, "__dict__"):
        size += get_size(obj.__dict__, seen)
    elif hasattr(obj, "__iter__") and not isinstance(obj, (str, bytes, bytearray)):
        size += sum([get_size(i, seen) for i in obj])

    return size


def nodes_equal(x, y):
    import ast

    __tracebackhide__ = True
    assert type(x) == type(y), f"Ast nodes do not have the same type: '{type(x)}' != '{type(y)}' "
    if isinstance(x, ast.Constant):
        assert x.value == y.value, (
            f"Constant ast nodes do not have the same value: " f"{repr(x.value)} != {repr(y.value)}"
        )
    if isinstance(x, (ast.Expr, ast.FunctionDef, ast.ClassDef)):
        assert x.lineno == y.lineno, f"Ast nodes do not have the same line number : {x.lineno} != {y.lineno}"
        assert (
            x.col_offset == y.col_offset
        ), f"Ast nodes do not have the same column offset number : {x.col_offset} != {y.col_offset}"
    for (xname, xval), (yname, yval) in zip(ast.iter_fields(x), ast.iter_fields(y), strict=False):
        assert (
            xname == yname
        ), f"Ast nodes fields differ : {xname} (of type {type(xval)}) != {yname} (of type {type(yval)})"
        assert (
            type(xval) == type(yval)
        ), f"Ast nodes fields differ : {xname} (of type {type(xval)}: {xval}) != {yname} (of type {type(yval)}: {yval}): {ast.dump(y)}"
    for xchild, ychild in zip(ast.iter_child_nodes(x), ast.iter_child_nodes(y), strict=False):
        assert nodes_equal(xchild, ychild), "Ast node children differs"
    return True
