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
            "#%s: %s:%s: %.1f KiB"
            % (index, frame.filename, frame.lineno, stat.size / 1024),
        )
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            print("    %s" % line)

    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        print(f"{len(other)} other: {size / 1024:.1f} KiB")
    total = sum(stat.size for stat in top_stats) / 1024
    print("Total allocated size: %.1f KiB" % (total))


@contextmanager
def timeit():
    t = time.time()
    yield
    print(f"Took: {time.time() - t : 0.2f}s")


def get_file(name: str, out_path: Path = None, ts: str = None):
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


if __name__ == "__main__":
    from xonsh_parser.parser import get_parser_cls, write_parser_table

    with timeit(), trace():
        import tempfile

        path = Path(tempfile.gettempdir()) / "parser_table.py"
        if path.exists():
            path.unlink()
        result = write_parser_table(output_path=path)
        # Output: writing parser-table
        # current=3103.5KiB,  peak=22563.3KiB
        # Total allocated size: 5991.8 KiB
        # Took:  6.25s

    with timeit(), trace():
        parser = get_parser_cls()(parser_table=result)
        parser.parse("ls -alh")
        # Output: reading parser-table
        # current=7457.5KiB,  peak=7531.1KiB
        # Total allocated size: 7470.4 KiB
        # Took:  1.47s
