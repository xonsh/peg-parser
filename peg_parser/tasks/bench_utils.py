import time
from contextlib import contextmanager
from pathlib import Path


def get_timestamp():
    from datetime import datetime

    now = datetime.now()

    return f"{now:%Y-%m-%d-%H-%M-%S}"


def display_top(snapshot, key_type="lineno", limit=10):
    import linecache
    import tracemalloc

    # todo: display all values greater than 5KiB instead of top 10/50
    snapshot = snapshot.filter_traces(
        (
            tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
            tracemalloc.Filter(False, "<unknown>"),
        )
    )
    top_stats = snapshot.statistics(key_type)

    print(f"Top {limit} lines. {key_type=}")
    for index, stat in enumerate(top_stats[:limit], 1):
        frame = stat.traceback[0]
        print(
            f"#{index}: {frame.filename}:{frame.lineno}: {stat.size / 1024:.1f} KiB",
        )
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            print(f"    {line}")

    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        print(f"{len(other)} other: {size / 1024:.1f} KiB")
    total = sum(stat.size for stat in top_stats) / 1024
    print(f"Total allocated size: {total:.1f} KiB")


@contextmanager
def timeit():
    t = time.time()
    yield
    print(f"Took: {time.time() - t : 0.2f}s")


def get_file(name: str, out_path: Path | None = None, ts: str | None = None):
    ts = ts or get_timestamp()
    out_path = (out_path or Path.cwd()) / name
    out_path.mkdir(exist_ok=True)
    return out_path / f"{ts}.md"


@contextmanager
def trace(limit=10, show_tb=False):
    """trace memory and time"""
    import tracemalloc

    tracemalloc.start(25)
    yield
    snap = tracemalloc.take_snapshot()

    current, peak = (size / 1024 for size in tracemalloc.get_traced_memory())
    print(f"{current=:.1f}KiB,  {peak=:.1f}KiB")

    if show_tb:
        display_top(snap, limit=limit, key_type="traceback")
        print("\n\n\n===----=====")
    display_top(snap, limit=limit)
    tracemalloc.reset_peak()
    tracemalloc.stop()
