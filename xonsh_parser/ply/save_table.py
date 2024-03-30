"""save LR table to file for use with mypyc

mypyc --strict xonsh_parser/ply/save_table.py
"""

import pickle
from typing import Final, NamedTuple

from pympler.asizeof import asizeof


class LRTable(NamedTuple):
    productions: tuple[tuple[str, int, str, str | None], ...]
    actions: tuple[dict[str, int], ...]
    gotos: tuple[dict[str, int], ...]


def write(
    productions: tuple[tuple[str, int, str, str | None], ...],
    actions: tuple[dict[str, int], ...],
    gotos: tuple[dict[str, int], ...],
    output_path: str,
) -> None:
    print(f"{asizeof(actions)=}")

    data = LRTable(productions, actions, gotos)
    with open(output_path, "wb") as fw:
        pickle.dump(data, fw, protocol=5)

    pickle.dump(data, open(output_path, "wb"), protocol=5)


def load(output_path: str) -> LRTable:
    with open(output_path, "rb") as fr:
        data: LRTable = pickle.load(fr)
    print(f"{asizeof(data.actions)=}")
    return data
