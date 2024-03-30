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