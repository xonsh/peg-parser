
import cython
from peg_parser.tokenizer cimport Tokenizer

cdef class Parser:
    cdef public Tokenizer _tokenizer
    cdef public bint _verbose
    cdef public int _level
    cdef public list _caches
    cdef public object tok_cls
    cdef public int in_recursive_rule
    cdef public object _path_token
    cdef public int _index     # index is int
    cdef public str filename
    cdef public object py_version
    cdef public bint call_invalid_rules

    cpdef _mark(self)
    cpdef _reset(self, int index)
