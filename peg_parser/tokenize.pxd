
import cython

cdef class TokenInfo:
    cdef public tuple end
    cdef public tuple start
    cdef public str string
    cdef public object type

    cpdef is_exact_type(self, str typ)
    cpdef loc_start(self)
    cpdef loc_end(self)
    cpdef loc(self)
    cpdef is_next_to(self, TokenInfo prev)
