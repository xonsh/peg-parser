from pathlib import Path

from .yacc import LRTable


def reduce_to_default_action(actions: dict[str, int]) -> int | dict[str, int]:
    """return a list of default reductions"""
    if len(actions) == 1 and list(actions.values())[0] < 0:
        return list(actions.values())[0]
    return actions


def optimize_table(lr, reduce_actions=False):
    """return an optimized version of the LR table variables for pickling"""
    productions = tuple((p.name, p.len, p.str, p.func) for p in lr.lr_productions)
    actions = [None] * len(lr.lr_action)
    gotos = [None] * len(lr.lr_goto)
    for state_id, items in lr.lr_action.items():
        assert not actions[state_id]
        if reduce_actions:
            actions[state_id] = reduce_to_default_action(items)
        else:
            actions[state_id] = items
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


def write_to_file(lr: LRTable, output_path: Path = None) -> Path:
    import json

    if not output_path:
        output_path = "parser.out.jsonl"

    productions, actions, gotos = optimize_table(lr)

    try:
        print(
            f"data:\n{_object_size(productions)=}\n{_object_size(actions)=} {len(actions)=}\n{_object_size(gotos)=}"
        )
    except ImportError:
        pass

    if output_path.suffix == ".jsonl":
        with open(output_path, "w") as fw:
            fw.write(json.dumps(productions) + "\n")
            fw.write(json.dumps(actions) + "\n")
            fw.write(json.dumps(gotos) + "\n")
    elif output_path.suffix == ".py":
        with open(output_path, "w") as fw:
            fw.write("from typing import Final\n")
            fw.write(f"productions : Final = {productions!r}\n")
            fw.write(f"actions : Final = {actions!r}\n")
            fw.write(f"gotos : Final = {gotos!r}\n")
    else:
        # write to a pickle file
        import pickle

        data = (productions, actions, gotos)
        with open(output_path, "wb") as fw:
            pickle.dump(data, fw, protocol=5)

    # this should write to output file
    print("Wrote to", output_path, "; size: ", _file_size(output_path))
    return output_path
