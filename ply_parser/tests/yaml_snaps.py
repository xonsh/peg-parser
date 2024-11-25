from dataclasses import dataclass
from pathlib import Path

import pytest


@dataclass
class LineItem:
    path: Path
    exp: str
    key: str
    idx: int
    write: bool = False

    def matches(self, other: str) -> bool:
        if self.write:
            self.write_yaml(other)
            raise AssertionError("Updating snapshots")
        assert other == self.exp

    def __repr__(self):
        return repr(self.exp)

    def write_yaml(self, exp: str):
        from ruamel.yaml import YAML

        yaml = YAML()

        with self.path.open("r") as file:
            data = yaml.load(file)
        data[self.key][self.idx]["exp"] = exp
        yaml.dump(data, self.path.open("w"))


@pytest.fixture
def snapped(request):
    if request.config.getoption("--update-snaps"):
        request.param.write = True
    return request.param


def yaml_line_items(*names: str):
    for name in names:
        path = Path(__file__).parent.joinpath("data").joinpath(f"{name}.yml")
        from ruamel.yaml import YAML

        yaml = YAML()
        with path.open("r") as file:
            data = yaml.load(file)
        for case, lines in data.items():
            for idx, item in enumerate(lines):
                exp = LineItem(path, item.get("exp", ""), case, idx)
                yield pytest.param(item["inp"], exp, id=f"{path.stem}-{case}-{idx}")


def pytest_addoption(parser):
    parser.addoption(
        "--update-snaps",
        action="store_true",
        default=False,
        help="update the corresponding yaml snapshots",
    )
