
import cython

cdef class Tokenizer:
    cdef object _readline
    cdef list _tokens
    cdef public int _index
    cdef bint _verbose
    cdef dict _lines
    cdef str _path
    cdef list _stack
    cdef bint _call_macro
    cdef bint _proc_macro
    cdef public list _raw_tokens
    cdef public int _raw_index
    cdef dict _end_parens
    cdef public object tok_cls
    cdef public object new_tok

    cpdef getnext(self)
    cpdef peek(self)
    cpdef diagnose(self)
    cpdef get_last_non_whitespace_token(self)
