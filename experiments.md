# from activity monitor for rust program

memory - real mem
977KB - 464KB -- basic program
8MB - 9MB  -- with objects


# rust repr
Productions: 169,372
actions: 4,449,272
gotos: 616,826


# python obj sizes

```
> asizeof.asizeof([0, 1, 3])
176
> asizeof.asizeof((0, 1, 3))
152

> asizeof.asizeof(p)
7,755,824
> asizeof.asizeof(parser.action)
6,776,520

> asizeof.asizeof('stringme' * 10)
136
> asizeof.asizeof(b'stringme' * 10)
120
```

# after using tuples instead of top-level dict

```
> asizeof.asizeof(p)
7,548,088

> write_parser_table(output_path=Path('/tmp/v1-str.pickle'))
data size: asizeof.asizeof(data)=7,322,024
PosixPath('/tmp/v1-str.pickle')
```

# using bytes for action names

```
> write_parser_table(output_path=Path('/tmp/v1-bytes.pickle'))
pickle size: asizeof.asizeof(data)=11,326,744
PosixPath('/tmp/v1-bytes.pickle')
```
- since Python strings does interning (str with same content is allocated only once), bytes dont bring any improvement

# tried using marshal

- there was not much difference with pickle

# fixing reduce/reduce conflicts

1. initial sizes

```
asizeof.asizeof(productions)=260KiB
asizeof.asizeof(actions)=6.18MiB
asizeof.asizeof(gotos)=560KiB
```

| type   | file-size |
|--------|-----------|
| pickle | 975.55KiB |
| py     | 1.61 MiB  |
| jsonl  | 1.61 MiB  |

2. merge overridden actions to base class - no change in sizes

```
_object_size(productions)='260.96 KiB'
_object_size(actions)='6.18 MiB'
_object_size(gotos)='560.97 KiB'
```

3. peak memory usage using lr-table.py type

benchmarks.PeakMemSuite.peakmem_parser_init_                                                                                 ok
[75.00%] ··· ============================ =======
                        param1
             ---------------------------- -------
              /tmp/xonsh-lr-table.pickle   31.5M
                /tmp/xonsh-lr-table.py      215M
              /tmp/xonsh-lr-table.jsonl    33.5M
             ============================ =======
 benchmarks.TrackLrParserSize.track_lr_parser_size                                                                    1/4 failed
[100.00%] ··· ============================= ========
                          param1
              ----------------------------- --------
                /tmp/xonsh-lr-table.pickle   7.54M
                  /tmp/xonsh-lr-table.py      4.8M
                /tmp/xonsh-lr-table.jsonl    7.53M
               /tmp/xonsh-lr-table.cpickle   7.54M


# with PEGen based parser
```text
current=2173.5KiB,  peak=2231.1KiB
...
Total allocated size: 2166.9 KiB
Took:  1.57s
```

but the same time PLY parsing was faster but used more memory
```
Took:  0.31s
current=2625.3KiB,  peak=9884.7KiB
...
Total allocated size: 9799.6 KiB
```

# Compiling with mypyc doesn't improve much

needed to add following to use it successfully
```py
from mypy_extensions import mypyc_attr


@mypyc_attr(allow_interpreted_subclasses=True)
class Parser():
    ...
```

with mypyc
```
current=2125.4KiB,  peak=28725.6KiB
...
1836 other: 757.9 KiB
Total allocated size: 1387.7 KiB
Took:  4.03s
```

without mypyc
```
current=1904.7KiB,  peak=1947.3KiB
...
1948 other: 596.0 KiB
Total allocated size: 1901.8 KiB
Took:  1.39s
```

# PEG parser sizes

- final `peg_parser/parser.py` sizes

| step                            | size | Uniq/Code/Lines |
|---------------------------------|------|-----------------|
| initial                         | 361K |                 |
| after removing extra spaces     | 356K |                 |
| optimize LOCATIONS              | 322K |                 |
| after repetitions deduplication | 294K |                 |
| after short location names      | 287K | 2336/9775/10083 |
| optimize gathered               | 261K | 2104/8665/8973  |

- optimized `get_last_non_whitespace_token` brought `benchmarks.PeakMemSuite.peakmem_parser_large_file` runtime to 5s from 10s

```text
ncalls  tottime  percall  cumtime  percall filename:lineno(function)

42517    6.443    0.000    6.529    0.000 tokenizer.py:169(get_last_non_whitespace_token)

# after optimization
39117    0.056    0.000    0.123    0.000 tokenizer.py:169(get_last_non_whitespace_token)
```