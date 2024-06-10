from typing import NamedTuple

class TokenInfo(NamedTuple):
    type: str
    string: str
    start: tuple[int, int]
    end: tuple[int, int]

def tokenize_str(s: str) -> list[TokenInfo]: ...
