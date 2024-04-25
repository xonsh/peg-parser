import sys

import pytest

pytest.mark.skipif(sys.version_info < (3, 10), reason="requires python3.10 or higher")


def test_match_literal_pattern(check_stmts):
    check_stmts(
        """match 1:
    case 1j:
        pass
    case 2.718+3.141j:
        pass
    case -2.718-3.141j:
        pass
    case 2:
        pass
    case -2:
        pass
    case "One" 'Two':
        pass
    case None:
        pass
    case True:
        pass
    case False:
        pass
""",
        run=False,
    )


def test_match_or_pattern(check_stmts):
    check_stmts(
        """match 1:
    case 1j | 2 | "One" | 'Two' | None | True | False:
        pass
""",
        run=False,
    )


def test_match_as_pattern(check_stmts):
    check_stmts(
        """match 1:
    case 1j | 2 | "One" | 'Two' | None | True | False as target:
        pass
    case 2 as target:
        pass
""",
        run=False,
    )


def test_match_group_pattern(check_stmts):
    check_stmts(
        """match 1:
    case (None):
        pass
    case ((None)):
        pass
    case (1 | 2 as x) as x:
        pass
""",
        run=False,
    )


def test_match_capture_and_wildcard_pattern(check_stmts):
    check_stmts(
        """match 1:
    case _:
        pass
    case x:
        pass
""",
        run=False,
    )


def test_match_value_pattern(check_stmts):
    check_stmts(
        """match 1:
    case math.pi:
        pass
    case a.b.c.d:
        pass
""",
        run=False,
    )


def test_match_mapping_pattern(check_stmts):
    check_stmts(
        """match _:
    case {}:
        pass
    case {x.y:y}:
        pass
    case {x.y:y,}:
        pass
    case {x.y:y,"a":a}:
        pass
    case {x.y:y,"a":a,}:
        pass
    case {x.y:y,"a":a,**end}:
        pass
    case {x.y:y,"a":a,**end,}:
        pass
    case {**end}:
        pass
    case {**end,}:
        pass
    case {1:1, "two":two, three.three: {}, 4:None, **end}:
        pass
""",
        run=False,
    )


def test_match_class_pattern(check_stmts):
    check_stmts(
        """match _:
    case classs():
        pass
    case x.classs():
        pass
    case classs("subpattern"):
        pass
    case classs("subpattern",):
        pass
    case classs("subpattern",2):
        pass
    case classs("subpattern",2,):
        pass
    case classs(a = b):
        pass
    case classs(a = b,):
        pass
    case classs(a = b, b = c):
        pass
    case classs(a = b, b = c,):
        pass
    case classs(1,2,3,a = b):
        pass
    case classs(1,2,3,a = b,):
        pass
    case classs(1,2,3,a = b, b = c):
        pass
    case classs(1,2,3,a = b, b = c,):
        pass
""",
        run=False,
    )


def test_match_sequence_pattern(check_stmts):
    check_stmts(
        """match 1:
    case (): # empty sequence pattern
        pass
    case (1): # group pattern
        pass
    case (1,): # length one sequence
        pass
    case (1,2):
        pass
    case (1,2,):
        pass
    case (1,2,3):
        pass
    case (1,2,3,):
        pass
    case []:
        pass
    case [1]:
        pass
    case [1,]:
        pass
    case [1,2]:
        pass
    case [1,2,3]:
        pass
    case [1,2,3,]:
        pass
    case [*x, *_]: # star patterns
        pass
    case 1,: # top level sequence patterns
        pass
    case *x,:
        pass
    case *_,*_:
        pass
""",
        run=False,
    )


def test_match_subject(check_stmts):
    check_stmts(
        """
match 1:
    case 1:
        pass
match 1,:
    case 1:
        pass
match 1,2:
    case 1:
        pass
match 1,2,:
    case 1:
        pass
match (1,2):
    case 1:
        pass
match *x,:
    case 1:
        pass
match (...[...][...]):
    case 1:
        pass
""",
        run=False,
    )
