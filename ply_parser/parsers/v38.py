"""Implements the xonsh parser for Python v3.8."""

from .. import xast as ast
from .base import store_ctx
from .v36 import Parser as ThreeSixParser


class Parser(ThreeSixParser):
    """A Python v3.8 compliant parser for the xonsh language."""

    def _get_optionals(self):
        return super()._get_optionals() + ["testlist_star_expr"]

    def _get_list_rules(self):
        return super()._get_list_rules() + ["comma_namedexpr_test_or_star_expr"]

    def _get_tok_rules(self):
        return super()._get_tok_rules() + ["colonequal"]

    def _set_posonly_args_def(self, argmts, vals):
        for v in vals:
            argmts.posonlyargs.append(v["arg"])
            d = v["default"]
            if d is not None:
                argmts.defaults.append(d)
            elif argmts.defaults:
                self._set_error("non-default argument follows default argument")

    def _set_posonly_args(self, p0, p1, p2, p3):
        if p2 is None and p3 is None:
            # x
            p0.posonlyargs.append(p1)
        elif p2 is not None and p3 is None:
            # x=42
            p0.posonlyargs.append(p1)
            p0.defaults.append(p2)
        elif p2 is None and p3 is not None:
            # x, y and x, y=42
            p0.posonlyargs.append(p1)
            self._set_posonly_args_def(p0, p3)
        else:
            # x=42, y=42
            p0.posonlyargs.append(p1)
            p0.defaults.append(p2)
            self._set_posonly_args_def(p0, p3)

    def p_posonlyargslist(self, p):
        """
        posonlyargslist : tfpdef equals_test_opt COMMA DIVIDE
                        | tfpdef equals_test_opt comma_tfpdef_list COMMA DIVIDE"""
        p0 = ast.arguments(
            posonlyargs=[],
            args=[],
            vararg=None,
            kwonlyargs=[],
            kw_defaults=[],
            kwarg=None,
            defaults=[],
        )
        if p[3] == ",":
            self._set_posonly_args(p0, p[1], p[2], None)
        else:
            self._set_posonly_args(p0, p[1], p[2], p[3])
        p[0] = p0

    def p_varargslist_t12(self, p):
        """
        varargslist : posonlyvarargslist comma_opt
                    | posonlyvarargslist COMMA varargslist
        """
        if len(p) == 4:
            p0 = p[3]
            p0.posonlyargs = p[1].posonlyargs
            # If posonlyargs contain default arguments, all following arguments must have defaults.
            if p[1].defaults and (len(p[3].defaults) != len(p[3].args)):
                self._set_error("non-default argument follows default argument")
        else:
            p0 = p[1]
        p[0] = p0

    def p_posonlyvarargslist(self, p):
        """
        posonlyvarargslist : vfpdef equals_test_opt COMMA DIVIDE
                           | vfpdef equals_test_opt comma_vfpdef_list COMMA DIVIDE"""
        p0 = ast.arguments(
            posonlyargs=[],
            args=[],
            vararg=None,
            kwonlyargs=[],
            kw_defaults=[],
            kwarg=None,
            defaults=[],
        )
        if p[3] == ",":
            self._set_posonly_args(p0, p[1], p[2], None)
        else:
            self._set_posonly_args(p0, p[1], p[2], p[3])
        p[0] = p0

    def p_argument_colonequal(self, p):
        """argument : test COLONEQUAL test"""
        p1 = p[1]
        store_ctx(p1)
        p[0] = ast.NamedExpr(target=p1, value=p[3], lineno=p1.lineno, col_offset=p1.col_offset)

    def p_namedexpr_test(self, p):
        """
        namedexpr_test : test
                       | test COLONEQUAL test
        """
        if len(p) == 2:
            p[0] = p[1]
        else:
            p1 = p[1]
            store_ctx(p1)
            p[0] = ast.NamedExpr(target=p1, value=p[3], lineno=p1.lineno, col_offset=p1.col_offset)

    def p_namedexpr_test_or_star_expr(self, p):
        """
        namedexpr_test_or_star_expr : namedexpr_test
                                    | star_expr
        """
        p[0] = p[1]

    def p_comma_namedexpr_test_or_star_expr(self, p):
        """comma_namedexpr_test_or_star_expr : COMMA namedexpr_test_or_star_expr"""
        p[0] = [p[2]]

    def p_yield_arg_testlist_star_expr(self, p):
        """yield_arg : testlist_star_expr"""
        p[0] = {"from": False, "val": p[1][0]}
