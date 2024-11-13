from pathlib import Path

from .yacc import LRTable


def optimize_table(lr):
    """return an optimized version of the LR table variables for pickling"""
    productions = tuple((p.name, p.len, p.str, p.func) for p in lr.lr_productions)
    actions = [None] * len(lr.lr_action)
    gotos = [None] * len(lr.lr_goto)
    for idx, vals in lr.lr_action.items():
        assert not actions[idx]
        actions[idx] = vals
    for idx, vals in lr.lr_goto.items():
        assert not gotos[idx]
        gotos[idx] = vals
    return productions, tuple(actions), tuple(gotos)


def _humanize_bytes(num, precision=2):
    for unit in ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]:
        if num < 1024.0 or unit == "PiB":
            break
        num /= 1024.0
    return f"{num:.{precision}f} {unit}"


def _file_size(path: str, decimal_places=2):
    """Returns a human readable string representation of bytes"""
    import os

    size = os.path.getsize(path)
    return _humanize_bytes(size, decimal_places)


def _object_size(data, decimal_places=2):
    """Returns a human readable string representation of python objects"""
    from pympler import asizeof

    size = asizeof.asizeof(data)
    return _humanize_bytes(size, decimal_places)


def write_to_file(lr: LRTable, output_path: str = None) -> Path:
    import json

    if not output_path:
        output_path = "parser.out.jsonl"

    productions, actions, gotos = optimize_table(lr)
    # print(f'data:\n{_object_size(productions)=}\n{_object_size(actions)=} {len(actions)=}\n{_object_size(gotos)=}')

    if output_path.endswith(".jsonl"):
        with open(output_path, "w") as fw:
            fw.write(json.dumps(productions) + "\n")
            fw.write(json.dumps(actions) + "\n")
            fw.write(json.dumps(gotos) + "\n")
    elif output_path.endswith(".py"):
        with open(output_path, "w") as fw:
            fw.write("from typing import Final\n")
            fw.write(f"productions : Final = {productions!r}\n")
            fw.write(f"actions : Final = {actions!r}\n")
            fw.write(f"gotos : Final = {gotos!r}\n")
    elif output_path.endswith(".cpickle"):
        from .save_table import write

        write(productions, actions, gotos, output_path)
    else:
        # write to a pickle file
        import pickle

        data = (productions, actions, gotos)
        with open(output_path, "wb") as fw:
            pickle.dump(data, fw, protocol=5)

    # this should write to output file
    print("Wrote to", output_path, "; size: ", _file_size(output_path))
    return output_path
