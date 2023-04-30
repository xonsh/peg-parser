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
