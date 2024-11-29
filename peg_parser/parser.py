from __future__ import annotations

import ast
import itertools
import sys
from typing import TYPE_CHECKING, Any, cast

from peg_parser.subheader import Del, Load, Node, Parser, Store, Target, logger, memoize, memoize_left_rec

if TYPE_CHECKING:
    from peg_parser.tokenize import TokenInfo


# Keywords and soft keywords are listed at the end of the parser definition.
class XonshParser(Parser):
    @memoize
    def file(self) -> ast.Module | None:
        # file: statements? $
        mark = self._mark()
        if (a := self.statements(),) and (self.token("ENDMARKER")):
            return ast.Module(body=a or [], type_ignores=[])
        self._reset(mark)
        return None

    @memoize
    def interactive(self) -> ast.Interactive | None:
        # interactive: statement_newline
        mark = self._mark()
        if a := self.statement_newline():
            return ast.Interactive(body=a)
        self._reset(mark)
        return None

    @memoize
    def eval(self) -> ast.Expression | None:
        # eval: expressions NEWLINE* $
        mark = self._mark()
        if (
            (a := self.expressions())
            and (self.repeated(self.token, "NEWLINE"),)
            and (self.token("ENDMARKER"))
        ):
            return ast.Expression(body=a)
        self._reset(mark)
        return None

    @memoize
    def fstring(self) -> ast.JoinedStr | None:
        # fstring: FSTRING_START fstring_mid* FSTRING_END
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (
            (a := self.token("FSTRING_START"))
            and (b := self.repeated(self.fstring_mid),)
            and (self.token("FSTRING_END"))
        ):
            return self.handle_fstring(a, b, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def statements(self) -> list[Any] | None:
        # statements: statement+
        mark = self._mark()
        if a := self.repeated(self.statement):
            return list(itertools.chain.from_iterable(a))
        self._reset(mark)
        return None

    @memoize
    def statement(self) -> list[Any] | None:
        # statement: compound_stmt | simple_stmts
        mark = self._mark()
        if a := self.compound_stmt():
            return [a]
        self._reset(mark)
        if a := self.simple_stmts():
            return a
        self._reset(mark)
        return None

    @memoize
    def statement_newline(self) -> list[Any] | None:
        # statement_newline: compound_stmt NEWLINE | simple_stmts | NEWLINE | $
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (a := self.compound_stmt()) and (self.token("NEWLINE")):
            return [a]
        self._reset(mark)
        if simple_stmts := self.simple_stmts():
            return simple_stmts
        self._reset(mark)
        if self.token("NEWLINE"):
            return [ast.Pass(**self.span(_lnum, _col))]
        self._reset(mark)
        if self.token("ENDMARKER"):
            return None
        self._reset(mark)
        return None

    @memoize
    def simple_stmts(self) -> list[Any] | None:
        # simple_stmts: simple_stmt !';' NEWLINE | ';'.simple_stmt+ ';'? NEWLINE
        mark = self._mark()
        if (
            (a := self.simple_stmt())
            and (self.negative_lookahead(self.expect, ";"))
            and (self.token("NEWLINE"))
        ):
            return [a]
        self._reset(mark)
        if (
            (a1 := self.gathered(self.simple_stmt, self.expect, ";"))
            and (self.expect(";"),)
            and (self.token("NEWLINE"))
        ):
            return a1
        self._reset(mark)
        return None

    @memoize
    def simple_stmt(self) -> ast.stmt | None:
        # simple_stmt: assignment | &"type" type_alias | star_expressions | &'return' return_stmt | &('import' | 'from') import_stmt | &'raise' raise_stmt | 'pass' | &'del' del_stmt | &'yield' yield_stmt | &'assert' assert_stmt | 'break' | 'continue' | &'global' global_stmt | &'nonlocal' nonlocal_stmt
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if assignment := self.assignment():
            return assignment
        self._reset(mark)
        if (self.positive_lookahead(self.expect, "type")) and (type_alias := self.type_alias()):
            return type_alias
        self._reset(mark)
        if e := self.star_expressions():
            return ast.Expr(value=e, **self.span(_lnum, _col))
        self._reset(mark)
        if (self.positive_lookahead(self.expect, "return")) and (return_stmt := self.return_stmt()):
            return return_stmt
        self._reset(mark)
        if (self.positive_lookahead(self._tmp_1)) and (import_stmt := self.import_stmt()):
            return import_stmt
        self._reset(mark)
        if (self.positive_lookahead(self.expect, "raise")) and (raise_stmt := self.raise_stmt()):
            return raise_stmt
        self._reset(mark)
        if self.expect("pass"):
            return ast.Pass(**self.span(_lnum, _col))
        self._reset(mark)
        if (self.positive_lookahead(self.expect, "del")) and (del_stmt := self.del_stmt()):
            return del_stmt
        self._reset(mark)
        if (self.positive_lookahead(self.expect, "yield")) and (yield_stmt := self.yield_stmt()):
            return yield_stmt
        self._reset(mark)
        if (self.positive_lookahead(self.expect, "assert")) and (assert_stmt := self.assert_stmt()):
            return assert_stmt
        self._reset(mark)
        if self.expect("break"):
            return ast.Break(**self.span(_lnum, _col))
        self._reset(mark)
        if self.expect("continue"):
            return ast.Continue(**self.span(_lnum, _col))
        self._reset(mark)
        if (self.positive_lookahead(self.expect, "global")) and (global_stmt := self.global_stmt()):
            return global_stmt
        self._reset(mark)
        if (self.positive_lookahead(self.expect, "nonlocal")) and (nonlocal_stmt := self.nonlocal_stmt()):
            return nonlocal_stmt
        self._reset(mark)
        return None

    @memoize
    def compound_stmt(self) -> Any | None:
        # compound_stmt: &('def' | '@' | 'async') function_def | &'if' if_stmt | &('class' | '@') class_def | &('with' | 'async') with_stmt | &('for' | 'async') for_stmt | &'try' try_stmt | &'while' while_stmt | match_stmt
        mark = self._mark()
        if (self.positive_lookahead(self._tmp_2)) and (function_def := self.function_def()):
            return function_def
        self._reset(mark)
        if (self.positive_lookahead(self.expect, "if")) and (if_stmt := self.if_stmt()):
            return if_stmt
        self._reset(mark)
        if (self.positive_lookahead(self._tmp_3)) and (class_def := self.class_def()):
            return class_def
        self._reset(mark)
        if (self.positive_lookahead(self._tmp_4)) and (with_stmt := self.with_stmt()):
            return with_stmt
        self._reset(mark)
        if (self.positive_lookahead(self._tmp_5)) and (for_stmt := self.for_stmt()):
            return for_stmt
        self._reset(mark)
        if (self.positive_lookahead(self.expect, "try")) and (try_stmt := self.try_stmt()):
            return try_stmt
        self._reset(mark)
        if (self.positive_lookahead(self.expect, "while")) and (while_stmt := self.while_stmt()):
            return while_stmt
        self._reset(mark)
        if match_stmt := self.match_stmt():
            return match_stmt
        self._reset(mark)
        return None

    @memoize
    def assignment(self) -> ast.stmt | None:
        # assignment: NAME ':' expression ['=' annotated_rhs] | ('(' single_target ')' | single_subscript_attribute_target) ':' expression ['=' annotated_rhs] | (assignment_lhs)+ annotated_rhs !'=' type_comment_str? | single_target augassign ~ annotated_rhs | invalid_assignment
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (a := self.name()) and (self.expect(":")) and (b := self.expression()) and (c := self._tmp_6(),):
            return ast.AnnAssign(
                target=ast.Name(
                    id=a.string,
                    ctx=Store,
                    lineno=a.start[0],
                    col_offset=a.start[1],
                    end_lineno=a.end[0],
                    end_col_offset=a.end[1],
                ),
                annotation=b,
                value=c,
                simple=1,
                **self.span(_lnum, _col),
            )
        self._reset(mark)
        if (
            (a1 := self._tmp_7())
            and (self.expect(":"))
            and (b1 := self.expression())
            and (c1 := self._tmp_8(),)
        ):
            return ast.AnnAssign(target=a1, annotation=b1, value=c1, simple=0, **self.span(_lnum, _col))
        self._reset(mark)
        if (
            (a2 := self.repeated(self.assignment_lhs))
            and (b2 := self.annotated_rhs())
            and (self.negative_lookahead(self.expect, "="))
            and (tc := self.type_comment_str(),)
        ):
            return ast.Assign(targets=a2, value=b2, type_comment=tc, **self.span(_lnum, _col))
        self._reset(mark)
        cut = False
        if (
            (a3 := self.single_target())
            and (b3 := self.augassign())
            and (cut := True)
            and (c3 := self.annotated_rhs())
        ):
            return ast.AugAssign(target=a3, op=b3, value=c3, **self.span(_lnum, _col))
        self._reset(mark)
        if cut:
            return None
        if self.call_invalid_rules and (self.invalid_assignment()):
            return None
        self._reset(mark)
        return None

    @memoize
    def assignment_lhs(self) -> ast.expr | None:
        # assignment_lhs: star_targets '='
        mark = self._mark()
        if (z := self.star_targets()) and (self.expect("=")):
            return z
        self._reset(mark)
        return None

    @memoize
    def annotated_rhs(self) -> Any | None:
        # annotated_rhs: yield_expr | star_expressions
        return self.seq_alts(
            self.yield_expr,
            self.star_expressions,
        )

    @memoize
    def augassign(self) -> Any | None:
        # augassign: '+=' | '-=' | '*=' | '@=' | '/=' | '%=' | '&=' | '|=' | '^=' | '<<=' | '>>=' | '**=' | '//='
        mark = self._mark()
        if self.expect("+="):
            return ast.Add()
        self._reset(mark)
        if self.expect("-="):
            return ast.Sub()
        self._reset(mark)
        if self.expect("*="):
            return ast.Mult()
        self._reset(mark)
        if self.expect("@="):
            return ast.MatMult()
        self._reset(mark)
        if self.expect("/="):
            return ast.Div()
        self._reset(mark)
        if self.expect("%="):
            return ast.Mod()
        self._reset(mark)
        if self.expect("&="):
            return ast.BitAnd()
        self._reset(mark)
        if self.expect("|="):
            return ast.BitOr()
        self._reset(mark)
        if self.expect("^="):
            return ast.BitXor()
        self._reset(mark)
        if self.expect("<<="):
            return ast.LShift()
        self._reset(mark)
        if self.expect(">>="):
            return ast.RShift()
        self._reset(mark)
        if self.expect("**="):
            return ast.Pow()
        self._reset(mark)
        if self.expect("//="):
            return ast.FloorDiv()
        self._reset(mark)
        return None

    @memoize
    def return_stmt(self) -> ast.Return | None:
        # return_stmt: 'return' star_expressions?
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (self.expect("return")) and (a := self.star_expressions(),):
            return ast.Return(value=a, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def raise_stmt(self) -> ast.Raise | None:
        # raise_stmt: 'raise' expression ['from' expression] | 'raise'
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (self.expect("raise")) and (a := self.expression()) and (b := self._tmp_9(),):
            return ast.Raise(exc=a, cause=b, **self.span(_lnum, _col))
        self._reset(mark)
        if self.expect("raise"):
            return ast.Raise(exc=None, cause=None, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def global_stmt(self) -> ast.Global | None:
        # global_stmt: 'global' ','.NAME+
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (self.expect("global")) and (a := self.gathered(self.name, self.expect, ",")):
            return ast.Global(names=[n.string for n in a], **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def nonlocal_stmt(self) -> ast.Nonlocal | None:
        # nonlocal_stmt: 'nonlocal' ','.NAME+
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (self.expect("nonlocal")) and (a := self.gathered(self.name, self.expect, ",")):
            return ast.Nonlocal(names=[n.string for n in a], **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def del_stmt(self) -> ast.Delete | None:
        # del_stmt: 'del' del_targets &(';' | NEWLINE) | invalid_del_stmt
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (self.expect("del")) and (a := self.del_targets()) and (self.positive_lookahead(self._tmp_10)):
            return ast.Delete(targets=a, **self.span(_lnum, _col))
        self._reset(mark)
        if self.call_invalid_rules and (self.invalid_del_stmt()):
            return None
        self._reset(mark)
        return None

    @memoize
    def yield_stmt(self) -> ast.Expr | None:
        # yield_stmt: yield_expr
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if y := self.yield_expr():
            return ast.Expr(value=y, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def assert_stmt(self) -> ast.Assert | None:
        # assert_stmt: 'assert' expression [',' expression]
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (self.expect("assert")) and (a := self.expression()) and (b := self._tmp_11(),):
            return ast.Assert(test=a, msg=b, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def import_stmt(self) -> ast.Import | ast.ImportFrom | None:
        # import_stmt: invalid_import | import_name | import_from
        return self.seq_alts(
            self.invalid_import,
            self.import_name,
            self.import_from,
        )

    @memoize
    def import_name(self) -> ast.Import | None:
        # import_name: 'import' dotted_as_names
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (self.expect("import")) and (a := self.dotted_as_names()):
            return ast.Import(names=a, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def import_from(self) -> ast.ImportFrom | Any | None:
        # import_from: 'from' dot_or_ellipsis* dotted_name 'import' import_from_targets | 'from' dot_or_ellipsis+ 'import' import_from_targets
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (
            (self.expect("from"))
            and (a := self.repeated(self.dot_or_ellipsis),)
            and (b := self.dotted_name())
            and (self.expect("import"))
            and (c := self.import_from_targets())
        ):
            return ast.ImportFrom(
                module=b, names=c, level=self.extract_import_level(a), **self.span(_lnum, _col)
            )
        self._reset(mark)
        if (
            (self.expect("from"))
            and (a1 := self.repeated(self.dot_or_ellipsis))
            and (self.expect("import"))
            and (b1 := self.import_from_targets())
        ):
            return ast.ImportFrom(names=b1, level=self.extract_import_level(a1), **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def dot_or_ellipsis(self) -> TokenInfo | None:
        # dot_or_ellipsis: '.' | '...'
        return self.seq_alts(
            (self.expect, "."),
            (self.expect, "..."),
        )

    @memoize
    def import_from_targets(self) -> list[ast.alias] | None:
        # import_from_targets: '(' import_from_as_names ','? ')' | import_from_as_names !',' | '*' | invalid_import_from_targets
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (
            (self.expect("("))
            and (a := self.import_from_as_names())
            and (self.expect(","),)
            and (self.expect(")"))
        ):
            return a
        self._reset(mark)
        if (import_from_as_names := self.import_from_as_names()) and (
            self.negative_lookahead(self.expect, ",")
        ):
            return import_from_as_names
        self._reset(mark)
        if self.expect("*"):
            return [ast.alias(name="*", asname=None, **self.span(_lnum, _col))]
        self._reset(mark)
        if self.call_invalid_rules and (self.invalid_import_from_targets()):
            return None
        self._reset(mark)
        return None

    @memoize
    def import_from_as_names(self) -> list[ast.alias] | None:
        # import_from_as_names: ','.import_from_as_name+
        mark = self._mark()
        if a := self.gathered(self.import_from_as_name, self.expect, ","):
            return a
        self._reset(mark)
        return None

    @memoize
    def import_from_as_name(self) -> ast.alias | None:
        # import_from_as_name: NAME ['as' NAME]
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (a := self.name()) and (b := self._tmp_12(),):
            return ast.alias(name=a.string, asname=b, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def dotted_as_names(self) -> list[ast.alias] | None:
        # dotted_as_names: ','.dotted_as_name+
        mark = self._mark()
        if a := self.gathered(self.dotted_as_name, self.expect, ","):
            return a
        self._reset(mark)
        return None

    @memoize
    def dotted_as_name(self) -> ast.alias | None:
        # dotted_as_name: dotted_name ['as' NAME]
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (a := self.dotted_name()) and (b := self._tmp_12(),):
            return ast.alias(name=a, asname=b, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize_left_rec
    def dotted_name(self) -> str | None:
        # dotted_name: dotted_name '.' NAME | NAME
        mark = self._mark()
        if (a := self.dotted_name()) and (self.expect(".")) and (b := self.name()):
            return a + "." + b.string
        self._reset(mark)
        if a1 := self.name():
            return a1.string
        self._reset(mark)
        return None

    @memoize
    def block(self) -> list[Any] | None:
        # block: NEWLINE INDENT statements DEDENT | simple_stmts | invalid_block
        mark = self._mark()
        if (
            (self.token("NEWLINE"))
            and (self.token("INDENT"))
            and (a := self.statements())
            and (self.token("DEDENT"))
        ):
            return a
        self._reset(mark)
        if simple_stmts := self.simple_stmts():
            return simple_stmts
        self._reset(mark)
        if self.call_invalid_rules and (self.invalid_block()):
            return None
        self._reset(mark)
        return None

    @memoize
    def decorators(self) -> Any | None:
        # decorators: decorator+
        mark = self._mark()
        if one_or_more := self.repeated(self.decorator):
            return one_or_more
        self._reset(mark)
        return None

    @memoize
    def decorator(self) -> ast.expr | None:
        # decorator: '@' named_expression NEWLINE
        mark = self._mark()
        if (self.expect("@")) and (f := self.named_expression()) and (self.token("NEWLINE")):
            return f
        self._reset(mark)
        return None

    @memoize
    def class_def(self) -> ast.ClassDef | None:
        # class_def: decorators class_def_raw | class_def_raw
        mark = self._mark()
        if (a := self.decorators()) and (b := self.class_def_raw()):
            return self.set_decorators(b, a)
        self._reset(mark)
        if class_def_raw := self.class_def_raw():
            return class_def_raw
        self._reset(mark)
        return None

    @memoize
    def class_def_raw(self) -> ast.ClassDef | None:
        # class_def_raw: invalid_class_def_raw | 'class' NAME type_params? ['(' arguments? ')'] &&':' block
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if self.call_invalid_rules and (self.invalid_class_def_raw()):
            return None
        self._reset(mark)
        if (
            (self.expect("class"))
            and (a := self.name())
            and (t := self.type_params(),)
            and (b := self._tmp_14(),)
            and (self.expect_forced(self.expect(":"), "':'"))
            and (c := self.block())
        ):
            return ast.ClassDef(
                a.string,
                bases=b[0] if b else [],
                keywords=b[1] if b else [],
                body=c,
                decorator_list=[],
                **{"type_params": t or []} if sys.version_info >= (3, 12) else {},
                **self.span(_lnum, _col),
            )
        self._reset(mark)
        return None

    @memoize
    def function_def(self) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
        # function_def: decorators function_def_raw | function_def_raw
        mark = self._mark()
        if (d := self.decorators()) and (f := self.function_def_raw()):
            return self.set_decorators(f, d)
        self._reset(mark)
        if f := self.function_def_raw():
            return self.set_decorators(f, [])
        self._reset(mark)
        return None

    @memoize
    def function_def_raw(self) -> ast.FunctionDef | ast.AsyncFunctionDef | Any | None:
        # function_def_raw: invalid_def_raw | 'def' NAME type_params? &&'(' params? ')' return_expr? &&':' func_type_comment? block | 'async' 'def' NAME type_params? &&'(' params? ')' return_expr? &&':' func_type_comment? block
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if self.call_invalid_rules and (self.invalid_def_raw()):
            return None
        self._reset(mark)
        if (
            (self.expect("def"))
            and (n := self.name())
            and (t := self.type_params(),)
            and (self.expect_forced(self.expect("("), "'('"))
            and (params := self.params(),)
            and (self.expect(")"))
            and (a := self.return_expr(),)
            and (self.expect_forced(self.expect(":"), "':'"))
            and (tc := self.func_type_comment(),)
            and (b := self.block())
        ):
            return ast.FunctionDef(
                name=n.string,
                args=params or self.make_arguments(None, [], None, [], None),
                returns=a,
                body=b,
                type_comment=tc,
                **{"type_params": t or []} if sys.version_info >= (3, 12) else {},
                **self.span(_lnum, _col),
            )
        self._reset(mark)
        if (
            (self.expect("async"))
            and (self.expect("def"))
            and (n := self.name())
            and (t := self.type_params(),)
            and (self.expect_forced(self.expect("("), "'('"))
            and (params := self.params(),)
            and (self.expect(")"))
            and (a := self.return_expr(),)
            and (self.expect_forced(self.expect(":"), "':'"))
            and (tc := self.func_type_comment(),)
            and (b := self.block())
        ):
            return ast.AsyncFunctionDef(
                name=n.string,
                args=params or self.make_arguments(None, [], None, [], None),
                returns=a,
                body=b,
                type_comment=tc,
                **{"type_params": t or []} if sys.version_info >= (3, 12) else {},
                **self.span(_lnum, _col),
            )
        self._reset(mark)
        return None

    @memoize
    def return_expr(self) -> ast.expr | None:
        # return_expr: '->' expression
        mark = self._mark()
        if (self.expect("->")) and (z := self.expression()):
            return z
        self._reset(mark)
        return None

    @memoize
    def params(self) -> ast.arguments | None:
        # params: invalid_parameters | parameters
        return self.seq_alts(
            self.invalid_parameters,
            self.parameters,
        )

    @memoize
    def parameters(self) -> ast.arguments | None:
        # parameters: slash_no_default param_no_default* param_with_default* star_etc? | slash_with_default param_with_default* star_etc? | param_no_default+ param_with_default* star_etc? | param_with_default+ star_etc? | star_etc
        mark = self._mark()
        if (
            (a := self.slash_no_default())
            and (b := self.repeated(self.param_no_default),)
            and (c := self.repeated(self.param_with_default),)
            and (d := self.star_etc(),)
        ):
            return self.make_arguments(a, [], b, c, d)
        self._reset(mark)
        if (
            (a1 := self.slash_with_default())
            and (b1 := self.repeated(self.param_with_default),)
            and (c1 := self.star_etc(),)
        ):
            return self.make_arguments(None, a1, None, b1, c1)
        self._reset(mark)
        if (
            (a2 := self.repeated(self.param_no_default))
            and (b2 := self.repeated(self.param_with_default),)
            and (c2 := self.star_etc(),)
        ):
            return self.make_arguments(None, [], a2, b2, c2)
        self._reset(mark)
        if (a3 := self.repeated(self.param_with_default)) and (b3 := self.star_etc(),):
            return self.make_arguments(None, [], None, a3, b3)
        self._reset(mark)
        if a4 := self.star_etc():
            return self.make_arguments(None, [], None, None, a4)
        self._reset(mark)
        return None

    @memoize
    def slash_no_default(self) -> list[tuple[ast.arg, None]] | None:
        # slash_no_default: param_no_default+ '/' ',' | param_no_default+ '/' &')'
        mark = self._mark()
        if (a := self.repeated(self.param_no_default)) and (self.expect("/")) and (self.expect(",")):
            return [(p, None) for p in a]
        self._reset(mark)
        if (
            (a := self.repeated(self.param_no_default))
            and (self.expect("/"))
            and (self.positive_lookahead(self.expect, ")"))
        ):
            return [(p, None) for p in a]
        self._reset(mark)
        return None

    @memoize
    def slash_with_default(self) -> list[tuple[ast.arg, Any]] | None:
        # slash_with_default: param_no_default* param_with_default+ '/' ',' | param_no_default* param_with_default+ '/' &')'
        mark = self._mark()
        if (
            (a := self.repeated(self.param_no_default),)
            and (b := self.repeated(self.param_with_default))
            and (self.expect("/"))
            and (self.expect(","))
        ):
            return ([(p, None) for p in a] if a else []) + b
        self._reset(mark)
        if (
            (a := self.repeated(self.param_no_default),)
            and (b := self.repeated(self.param_with_default))
            and (self.expect("/"))
            and (self.positive_lookahead(self.expect, ")"))
        ):
            return ([(p, None) for p in a] if a else []) + b
        self._reset(mark)
        return None

    @memoize
    def star_etc(self) -> tuple[ast.arg | None, list[tuple[ast.arg, Any]], ast.arg | None] | None:
        # star_etc: invalid_star_etc | '*' param_no_default param_maybe_default* kwds? | '*' param_no_default_star_annotation param_maybe_default* kwds? | '*' ',' param_maybe_default+ kwds? | kwds
        mark = self._mark()
        if self.call_invalid_rules and (self.invalid_star_etc()):
            return None
        self._reset(mark)
        if (
            (self.expect("*"))
            and (a := self.param_no_default())
            and (b := self.repeated(self.param_maybe_default),)
            and (c := self.kwds(),)
        ):
            return (a, b, c)
        self._reset(mark)
        if (
            (self.expect("*"))
            and (a := self.param_no_default_star_annotation())
            and (b := self.repeated(self.param_maybe_default),)
            and (c := self.kwds(),)
        ):
            return (a, b, c)
        self._reset(mark)
        if (
            (self.expect("*"))
            and (self.expect(","))
            and (b := self.repeated(self.param_maybe_default))
            and (c := self.kwds(),)
        ):
            return (None, b, c)
        self._reset(mark)
        if a := self.kwds():
            return (None, [], a)
        self._reset(mark)
        return None

    @memoize
    def kwds(self) -> ast.arg | None:
        # kwds: invalid_kwds | '**' param_no_default
        mark = self._mark()
        if self.call_invalid_rules and (self.invalid_kwds()):
            return None
        self._reset(mark)
        if (self.expect("**")) and (a := self.param_no_default()):
            return a
        self._reset(mark)
        return None

    @memoize
    def param_no_default(self) -> ast.arg | None:
        # param_no_default: param ',' TYPE_COMMENT? | param TYPE_COMMENT? &')'
        mark = self._mark()
        if (a := self.param()) and (self.expect(",")) and (self.token("TYPE_COMMENT"),):
            return a
        self._reset(mark)
        if (
            (a := self.param())
            and (self.token("TYPE_COMMENT"),)
            and (self.positive_lookahead(self.expect, ")"))
        ):
            return a
        self._reset(mark)
        return None

    @memoize
    def param_no_default_star_annotation(self) -> ast.arg | None:
        # param_no_default_star_annotation: param_star_annotation ',' TYPE_COMMENT? | param_star_annotation TYPE_COMMENT? &')'
        mark = self._mark()
        if (a := self.param_star_annotation()) and (self.expect(",")) and (self.token("TYPE_COMMENT"),):
            return a
        self._reset(mark)
        if (
            (a := self.param_star_annotation())
            and (self.token("TYPE_COMMENT"),)
            and (self.positive_lookahead(self.expect, ")"))
        ):
            return a
        self._reset(mark)
        return None

    @memoize
    def param_with_default(self) -> tuple[ast.arg, Any] | None:
        # param_with_default: param default ',' TYPE_COMMENT? | param default TYPE_COMMENT? &')'
        mark = self._mark()
        if (
            (a := self.param())
            and (c := self.default())
            and (self.expect(","))
            and (self.token("TYPE_COMMENT"),)
        ):
            return (a, c)
        self._reset(mark)
        if (
            (a := self.param())
            and (c := self.default())
            and (self.token("TYPE_COMMENT"),)
            and (self.positive_lookahead(self.expect, ")"))
        ):
            return (a, c)
        self._reset(mark)
        return None

    @memoize
    def param_maybe_default(self) -> tuple[ast.arg, Any] | None:
        # param_maybe_default: param default? ',' TYPE_COMMENT? | param default? TYPE_COMMENT? &')'
        mark = self._mark()
        if (
            (a := self.param())
            and (c := self.default(),)
            and (self.expect(","))
            and (self.token("TYPE_COMMENT"),)
        ):
            return (a, c)
        self._reset(mark)
        if (
            (a := self.param())
            and (c := self.default(),)
            and (self.token("TYPE_COMMENT"),)
            and (self.positive_lookahead(self.expect, ")"))
        ):
            return (a, c)
        self._reset(mark)
        return None

    @memoize
    def param(self) -> ast.arg | None:
        # param: NAME annotation?
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (a := self.name()) and (b := self.annotation(),):
            return ast.arg(arg=a.string, annotation=b, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def param_star_annotation(self) -> ast.arg | None:
        # param_star_annotation: NAME star_annotation
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (a := self.name()) and (b := self.star_annotation()):
            return ast.arg(arg=a.string, annotation=b, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def annotation(self) -> ast.expr | None:
        # annotation: ':' expression
        mark = self._mark()
        if (self.expect(":")) and (a := self.expression()):
            return a
        self._reset(mark)
        return None

    @memoize
    def star_annotation(self) -> Any | None:
        # star_annotation: ':' star_expression
        mark = self._mark()
        if (self.expect(":")) and (a := self.star_expression()):
            return a
        self._reset(mark)
        return None

    @memoize
    def default(self) -> ast.expr | None:
        # default: '=' expression | invalid_default
        mark = self._mark()
        if (self.expect("=")) and (a := self.expression()):
            return a
        self._reset(mark)
        if self.call_invalid_rules and (self.invalid_default()):
            return None
        self._reset(mark)
        return None

    @memoize
    def if_stmt(self) -> ast.If | None:
        # if_stmt: invalid_if_stmt | 'if' named_expression ':' block elif_stmt | 'if' named_expression ':' block else_block?
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if self.call_invalid_rules and (self.invalid_if_stmt()):
            return None
        self._reset(mark)
        if (
            (self.expect("if"))
            and (a := self.named_expression())
            and (self.expect(":"))
            and (b := self.block())
            and (c := self.elif_stmt())
        ):
            return ast.If(test=a, body=b, orelse=c or [], **self.span(_lnum, _col))
        self._reset(mark)
        if (
            (self.expect("if"))
            and (a := self.named_expression())
            and (self.expect(":"))
            and (b := self.block())
            and (c := self.else_block(),)
        ):
            return ast.If(test=a, body=b, orelse=c or [], **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def elif_stmt(self) -> list[ast.If] | None:
        # elif_stmt: invalid_elif_stmt | 'elif' named_expression ':' block elif_stmt | 'elif' named_expression ':' block else_block?
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if self.call_invalid_rules and (self.invalid_elif_stmt()):
            return None
        self._reset(mark)
        if (
            (self.expect("elif"))
            and (a := self.named_expression())
            and (self.expect(":"))
            and (b := self.block())
            and (c := self.elif_stmt())
        ):
            return [ast.If(test=a, body=b, orelse=c, **self.span(_lnum, _col))]
        self._reset(mark)
        if (
            (self.expect("elif"))
            and (a := self.named_expression())
            and (self.expect(":"))
            and (b := self.block())
            and (c := self.else_block(),)
        ):
            return [ast.If(test=a, body=b, orelse=c or [], **self.span(_lnum, _col))]
        self._reset(mark)
        return None

    @memoize
    def else_block(self) -> list[Any] | None:
        # else_block: invalid_else_stmt | 'else' &&':' block
        mark = self._mark()
        if self.call_invalid_rules and (self.invalid_else_stmt()):
            return None
        self._reset(mark)
        if (self.expect("else")) and (self.expect_forced(self.expect(":"), "':'")) and (b := self.block()):
            return b
        self._reset(mark)
        return None

    @memoize
    def while_stmt(self) -> ast.While | None:
        # while_stmt: invalid_while_stmt | 'while' named_expression ':' block else_block?
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if self.call_invalid_rules and (self.invalid_while_stmt()):
            return None
        self._reset(mark)
        if (
            (self.expect("while"))
            and (a := self.named_expression())
            and (self.expect(":"))
            and (b := self.block())
            and (c := self.else_block(),)
        ):
            return ast.While(test=a, body=b, orelse=c or [], **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def for_stmt(self) -> ast.For | ast.AsyncFor | None:
        # for_stmt: invalid_for_stmt | 'for' star_targets 'in' ~ star_expressions &&':' type_comment_str? block else_block? | 'async' 'for' star_targets 'in' ~ star_expressions ':' type_comment_str? block else_block? | invalid_for_target
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if self.call_invalid_rules and (self.invalid_for_stmt()):
            return None
        self._reset(mark)
        cut = False
        if (
            (self.expect("for"))
            and (t := self.star_targets())
            and (self.expect("in"))
            and (cut := True)
            and (ex := self.star_expressions())
            and (self.expect_forced(self.expect(":"), "':'"))
            and (tc := self.type_comment_str(),)
            and (b := self.block())
            and (el := self.else_block(),)
        ):
            return ast.For(
                target=t, iter=ex, body=b, orelse=el or [], type_comment=tc, **self.span(_lnum, _col)
            )
        self._reset(mark)
        if cut:
            return None
        cut = False
        if (
            (self.expect("async"))
            and (self.expect("for"))
            and (t := self.star_targets())
            and (self.expect("in"))
            and (cut := True)
            and (ex := self.star_expressions())
            and (self.expect(":"))
            and (tc := self.type_comment_str(),)
            and (b := self.block())
            and (el := self.else_block(),)
        ):
            return ast.AsyncFor(
                target=t, iter=ex, body=b, orelse=el or [], type_comment=tc, **self.span(_lnum, _col)
            )
        self._reset(mark)
        if cut:
            return None
        if self.call_invalid_rules and (self.invalid_for_target()):
            return None
        self._reset(mark)
        return None

    @memoize
    def with_stmt(self) -> ast.With | ast.AsyncWith | None:
        # with_stmt: invalid_with_stmt_indent | &with_macro_start ~ with_macro_stmt | 'with' '(' ','.with_item+ ','? ')' ':' block | 'with' ','.with_item+ ':' type_comment_str? block | 'async' 'with' '(' ','.with_item+ ','? ')' ':' block | 'async' 'with' ','.with_item+ ':' type_comment_str? block | invalid_with_stmt
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if self.call_invalid_rules and (self.invalid_with_stmt_indent()):
            return None
        self._reset(mark)
        cut = False
        if (
            (self.positive_lookahead(self.with_macro_start))
            and (cut := True)
            and (with_macro_stmt := self.with_macro_stmt())
        ):
            return with_macro_stmt
        self._reset(mark)
        if cut:
            return None
        if (
            (self.expect("with"))
            and (self.expect("("))
            and (a := self.gathered(self.with_item, self.expect, ","))
            and (self.expect(","),)
            and (self.expect(")"))
            and (self.expect(":"))
            and (b := self.block())
        ):
            return ast.With(items=a, body=b, **self.span(_lnum, _col))
        self._reset(mark)
        if (
            (self.expect("with"))
            and (a := self.gathered(self.with_item, self.expect, ","))
            and (self.expect(":"))
            and (tc := self.type_comment_str(),)
            and (b := self.block())
        ):
            return ast.With(items=a, body=b, type_comment=tc, **self.span(_lnum, _col))
        self._reset(mark)
        if (
            (self.expect("async"))
            and (self.expect("with"))
            and (self.expect("("))
            and (a := self.gathered(self.with_item, self.expect, ","))
            and (self.expect(","),)
            and (self.expect(")"))
            and (self.expect(":"))
            and (b := self.block())
        ):
            return ast.AsyncWith(items=a, body=b, **self.span(_lnum, _col))
        self._reset(mark)
        if (
            (self.expect("async"))
            and (self.expect("with"))
            and (a := self.gathered(self.with_item, self.expect, ","))
            and (self.expect(":"))
            and (tc := self.type_comment_str(),)
            and (b := self.block())
        ):
            return ast.AsyncWith(items=a, body=b, type_comment=tc, **self.span(_lnum, _col))
        self._reset(mark)
        if self.call_invalid_rules and (self.invalid_with_stmt()):
            return None
        self._reset(mark)
        return None

    @memoize
    def with_item(self) -> ast.withitem | None:
        # with_item: expression 'as' star_target &(',' | ')' | ':') | invalid_with_item | expression
        mark = self._mark()
        if (
            (e := self.expression())
            and (self.expect("as"))
            and (t := self.star_target())
            and (self.positive_lookahead(self._tmp_15))
        ):
            return ast.withitem(context_expr=e, optional_vars=t)
        self._reset(mark)
        if self.call_invalid_rules and (self.invalid_with_item()):
            return None
        self._reset(mark)
        if e := self.expression():
            return ast.withitem(context_expr=e, optional_vars=None)
        self._reset(mark)
        return None

    @memoize
    def with_macro_stmt(self) -> ast.With | None:
        # with_macro_stmt: with_macro_start MACRO_PARAM
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (a := self.with_macro_start()) and (b := self.token("MACRO_PARAM")):
            return self.handle_with_macro_stmt(a, b, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def with_macro_start(self) -> Any | None:
        # with_macro_start: 'with' '!' ~ with_item ':'
        mark = self._mark()
        cut = False
        if (
            (self.expect("with"))
            and (self.expect("!"))
            and (cut := True)
            and (a := self.with_item())
            and (self.expect(":"))
        ):
            return self.handle_with_macro_start(a)
        self._reset(mark)
        if cut:
            return None
        return None

    @memoize
    def try_stmt(self) -> ast.Try | ast.TryStar | None:
        # try_stmt: invalid_try_stmt | 'try' &&':' block finally_block | 'try' &&':' block except_block+ else_block? finally_block? | 'try' &&':' block except_star_block+ else_block? finally_block?
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if self.call_invalid_rules and (self.invalid_try_stmt()):
            return None
        self._reset(mark)
        if (
            (self.expect("try"))
            and (self.expect_forced(self.expect(":"), "':'"))
            and (b := self.block())
            and (f := self.finally_block())
        ):
            return ast.Try(body=b, handlers=[], orelse=[], finalbody=f, **self.span(_lnum, _col))
        self._reset(mark)
        if (
            (self.expect("try"))
            and (self.expect_forced(self.expect(":"), "':'"))
            and (b := self.block())
            and (ex := self.repeated(self.except_block))
            and (el := self.else_block(),)
            and (f := self.finally_block(),)
        ):
            return ast.Try(body=b, handlers=ex, orelse=el or [], finalbody=f or [], **self.span(_lnum, _col))
        self._reset(mark)
        if (
            (self.expect("try"))
            and (self.expect_forced(self.expect(":"), "':'"))
            and (b := self.block())
            and (ex := self.repeated(self.except_star_block))
            and (el := self.else_block(),)
            and (f := self.finally_block(),)
        ):
            return self.check_version(
                (3, 11),
                "Exception groups are",
                ast.TryStar(body=b, handlers=ex, orelse=el or [], finalbody=f or [], **self.span(_lnum, _col))
                if sys.version_info >= (3, 11)
                else None,
            )
        self._reset(mark)
        return None

    @memoize
    def except_block(self) -> ast.ExceptHandler | None:
        # except_block: invalid_except_stmt_indent | 'except' expression ['as' NAME] ':' block | 'except' ':' block | invalid_except_stmt
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if self.call_invalid_rules and (self.invalid_except_stmt_indent()):
            return None
        self._reset(mark)
        if (
            (self.expect("except"))
            and (e := self.expression())
            and (t := self._tmp_12(),)
            and (self.expect(":"))
            and (b := self.block())
        ):
            return ast.ExceptHandler(type=e, name=t, body=b, **self.span(_lnum, _col))
        self._reset(mark)
        if (self.expect("except")) and (self.expect(":")) and (b := self.block()):
            return ast.ExceptHandler(type=None, name=None, body=b, **self.span(_lnum, _col))
        self._reset(mark)
        if self.call_invalid_rules and (self.invalid_except_stmt()):
            return None
        self._reset(mark)
        return None

    @memoize
    def except_star_block(self) -> ast.ExceptHandler | None:
        # except_star_block: invalid_except_star_stmt_indent | 'except' '*' expression ['as' NAME] ':' block | invalid_except_stmt
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if self.call_invalid_rules and (self.invalid_except_star_stmt_indent()):
            return None
        self._reset(mark)
        if (
            (self.expect("except"))
            and (self.expect("*"))
            and (e := self.expression())
            and (t := self._tmp_12(),)
            and (self.expect(":"))
            and (b := self.block())
        ):
            return ast.ExceptHandler(type=e, name=t, body=b, **self.span(_lnum, _col))
        self._reset(mark)
        if self.call_invalid_rules and (self.invalid_except_stmt()):
            return None
        self._reset(mark)
        return None

    @memoize
    def finally_block(self) -> list[Any] | None:
        # finally_block: invalid_finally_stmt | 'finally' &&':' block
        mark = self._mark()
        if self.call_invalid_rules and (self.invalid_finally_stmt()):
            return None
        self._reset(mark)
        if (self.expect("finally")) and (self.expect_forced(self.expect(":"), "':'")) and (a := self.block()):
            return a
        self._reset(mark)
        return None

    @memoize
    def match_stmt(self) -> ast.Match | None:
        # match_stmt: "match" subject_expr ':' NEWLINE INDENT case_block+ DEDENT | invalid_match_stmt
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (
            (self.expect("match"))
            and (subject := self.subject_expr())
            and (self.expect(":"))
            and (self.token("NEWLINE"))
            and (self.token("INDENT"))
            and (cases := self.repeated(self.case_block))
            and (self.token("DEDENT"))
        ):
            return ast.Match(subject=subject, cases=cases, **self.span(_lnum, _col))
        self._reset(mark)
        if self.call_invalid_rules and (self.invalid_match_stmt()):
            return None
        self._reset(mark)
        return None

    @memoize
    def subject_expr(self) -> Any | None:
        # subject_expr: star_named_expression ',' star_named_expressions? | named_expression
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (
            (value := self.star_named_expression())
            and (self.expect(","))
            and (values := self.star_named_expressions(),)
        ):
            return ast.Tuple(elts=[value] + (values or []), ctx=Load, **self.span(_lnum, _col))
        self._reset(mark)
        if e := self.named_expression():
            return e
        self._reset(mark)
        return None

    @memoize
    def case_block(self) -> ast.match_case | None:
        # case_block: invalid_case_block | "case" patterns guard? ':' block
        mark = self._mark()
        if self.call_invalid_rules and (self.invalid_case_block()):
            return None
        self._reset(mark)
        if (
            (self.expect("case"))
            and (pattern := self.patterns())
            and (guard := self.guard(),)
            and (self.expect(":"))
            and (body := self.block())
        ):
            return ast.match_case(pattern=pattern, guard=guard, body=body)
        self._reset(mark)
        return None

    @memoize
    def guard(self) -> Any | None:
        # guard: 'if' named_expression
        mark = self._mark()
        if (self.expect("if")) and (guard := self.named_expression()):
            return guard
        self._reset(mark)
        return None

    @memoize
    def patterns(self) -> Any | None:
        # patterns: open_sequence_pattern | pattern
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if patterns := self.open_sequence_pattern():
            return ast.MatchSequence(patterns=patterns, **self.span(_lnum, _col))
        self._reset(mark)
        if pattern := self.pattern():
            return pattern
        self._reset(mark)
        return None

    @memoize
    def pattern(self) -> ast.pattern | None:
        # pattern: as_pattern | or_pattern
        return self.seq_alts(
            self.as_pattern,
            self.or_pattern,
        )

    @memoize
    def as_pattern(self) -> ast.pattern | None:
        # as_pattern: or_pattern 'as' pattern_capture_target | invalid_as_pattern
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (
            (pattern := self.or_pattern())
            and (self.expect("as"))
            and (target := self.pattern_capture_target())
        ):
            return ast.MatchAs(pattern=pattern, name=target, **self.span(_lnum, _col))
        self._reset(mark)
        if self.call_invalid_rules and (self.invalid_as_pattern()):
            return None
        self._reset(mark)
        return None

    @memoize
    def or_pattern(self) -> ast.pattern | None:
        # or_pattern: '|'.closed_pattern+
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if patterns := self.gathered(self.closed_pattern, self.expect, "|"):
            return (
                ast.MatchOr(patterns=patterns, **self.span(_lnum, _col)) if len(patterns) > 1 else patterns[0]
            )
        self._reset(mark)
        return None

    @memoize
    def closed_pattern(self) -> ast.pattern | None:
        # closed_pattern: literal_pattern | capture_pattern | wildcard_pattern | value_pattern | group_pattern | sequence_pattern | mapping_pattern | class_pattern
        return self.seq_alts(
            self.literal_pattern,
            self.capture_pattern,
            self.wildcard_pattern,
            self.value_pattern,
            self.group_pattern,
            self.sequence_pattern,
            self.mapping_pattern,
            self.class_pattern,
        )

    @memoize
    def literal_pattern(self) -> Any | None:
        # literal_pattern: signed_number !('+' | '-') | complex_number | strings | 'None' | 'True' | 'False'
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (value := self.signed_number()) and (self.negative_lookahead(self._tmp_18)):
            return ast.MatchValue(value=value, **self.span(_lnum, _col))
        self._reset(mark)
        if value := self.complex_number():
            return ast.MatchValue(value=value, **self.span(_lnum, _col))
        self._reset(mark)
        if value := self.strings():
            return ast.MatchValue(value=value, **self.span(_lnum, _col))
        self._reset(mark)
        if self.expect("None"):
            return ast.MatchSingleton(value=None, **self.span(_lnum, _col))
        self._reset(mark)
        if self.expect("True"):
            return ast.MatchSingleton(value=True, **self.span(_lnum, _col))
        self._reset(mark)
        if self.expect("False"):
            return ast.MatchSingleton(value=False, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def literal_expr(self) -> Any | None:
        # literal_expr: signed_number !('+' | '-') | complex_number | strings | 'None' | 'True' | 'False'
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (signed_number := self.signed_number()) and (self.negative_lookahead(self._tmp_18)):
            return signed_number
        self._reset(mark)
        if complex_number := self.complex_number():
            return complex_number
        self._reset(mark)
        if strings := self.strings():
            return strings
        self._reset(mark)
        if self.expect("None"):
            return ast.Constant(value=None, **self.span(_lnum, _col))
        self._reset(mark)
        if self.expect("True"):
            return ast.Constant(value=True, **self.span(_lnum, _col))
        self._reset(mark)
        if self.expect("False"):
            return ast.Constant(value=False, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def complex_number(self) -> Any | None:
        # complex_number: signed_real_number '+' imaginary_number | signed_real_number '-' imaginary_number
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (real := self.signed_real_number()) and (self.expect("+")) and (imag := self.imaginary_number()):
            return ast.BinOp(left=real, op=ast.Add(), right=imag, **self.span(_lnum, _col))
        self._reset(mark)
        if (real := self.signed_real_number()) and (self.expect("-")) and (imag := self.imaginary_number()):
            return ast.BinOp(left=real, op=ast.Sub(), right=imag, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def signed_number(self) -> Any | None:
        # signed_number: NUMBER | '-' NUMBER
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if a := self.token("NUMBER"):
            return ast.Constant(value=ast.literal_eval(a.string), **self.span(_lnum, _col))
        self._reset(mark)
        if (self.expect("-")) and (a := self.token("NUMBER")):
            return ast.UnaryOp(
                op=ast.USub(),
                operand=ast.Constant(
                    value=ast.literal_eval(a.string),
                    lineno=a.start[0],
                    col_offset=a.start[1],
                    end_lineno=a.end[0],
                    end_col_offset=a.end[1],
                ),
                **self.span(_lnum, _col),
            )
        self._reset(mark)
        return None

    @memoize
    def signed_real_number(self) -> Any | None:
        # signed_real_number: real_number | '-' real_number
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if real_number := self.real_number():
            return real_number
        self._reset(mark)
        if (self.expect("-")) and (real := self.real_number()):
            return ast.UnaryOp(op=ast.USub(), operand=real, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def real_number(self) -> ast.Constant | None:
        # real_number: NUMBER
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if real := self.token("NUMBER"):
            return ast.Constant(value=self.ensure_real(real), **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def imaginary_number(self) -> ast.Constant | None:
        # imaginary_number: NUMBER
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if imag := self.token("NUMBER"):
            return ast.Constant(value=self.ensure_imaginary(imag), **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def capture_pattern(self) -> Any | None:
        # capture_pattern: pattern_capture_target
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if target := self.pattern_capture_target():
            return ast.MatchAs(pattern=None, name=target, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def pattern_capture_target(self) -> str | None:
        # pattern_capture_target: !"_" NAME !('.' | '(' | '=')
        mark = self._mark()
        if (
            (self.negative_lookahead(self.expect, "_"))
            and (name := self.name())
            and (self.negative_lookahead(self._tmp_20))
        ):
            return name.string
        self._reset(mark)
        return None

    @memoize
    def wildcard_pattern(self) -> ast.MatchAs | None:
        # wildcard_pattern: "_"
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if self.expect("_"):
            return ast.MatchAs(pattern=None, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def value_pattern(self) -> ast.MatchValue | None:
        # value_pattern: attr !('.' | '(' | '=')
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (attr := self.attr()) and (self.negative_lookahead(self._tmp_20)):
            return ast.MatchValue(value=attr, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize_left_rec
    def attr(self) -> ast.Attribute | None:
        # attr: name_or_attr '.' NAME
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (value := self.name_or_attr()) and (self.expect(".")) and (attr := self.name()):
            return ast.Attribute(value=value, attr=attr.string, ctx=Load, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @logger
    def name_or_attr(self) -> Any | None:
        # name_or_attr: attr | NAME
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if attr := self.attr():
            return attr
        self._reset(mark)
        if name := self.name():
            return ast.Name(id=name.string, ctx=Load, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def group_pattern(self) -> Any | None:
        # group_pattern: '(' pattern ')'
        mark = self._mark()
        if (self.expect("(")) and (pattern := self.pattern()) and (self.expect(")")):
            return pattern
        self._reset(mark)
        return None

    @memoize
    def sequence_pattern(self) -> ast.MatchSequence | None:
        # sequence_pattern: '[' maybe_sequence_pattern? ']' | '(' open_sequence_pattern? ')'
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (self.expect("[")) and (patterns := self.maybe_sequence_pattern(),) and (self.expect("]")):
            return ast.MatchSequence(patterns=patterns or [], **self.span(_lnum, _col))
        self._reset(mark)
        if (self.expect("(")) and (patterns := self.open_sequence_pattern(),) and (self.expect(")")):
            return ast.MatchSequence(patterns=patterns or [], **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def open_sequence_pattern(self) -> Any | None:
        # open_sequence_pattern: maybe_star_pattern ',' maybe_sequence_pattern?
        mark = self._mark()
        if (
            (pattern := self.maybe_star_pattern())
            and (self.expect(","))
            and (patterns := self.maybe_sequence_pattern(),)
        ):
            return [pattern] + (patterns or [])
        self._reset(mark)
        return None

    @memoize
    def maybe_sequence_pattern(self) -> list[ast.pattern] | None:
        # maybe_sequence_pattern: ','.maybe_star_pattern+ ','?
        mark = self._mark()
        if (patterns := self.gathered(self.maybe_star_pattern, self.expect, ",")) and (self.expect(","),):
            return patterns
        self._reset(mark)
        return None

    @memoize
    def maybe_star_pattern(self) -> ast.pattern | None:
        # maybe_star_pattern: star_pattern | pattern
        return self.seq_alts(
            self.star_pattern,
            self.pattern,
        )

    @memoize
    def star_pattern(self) -> Any | None:
        # star_pattern: '*' pattern_capture_target | '*' wildcard_pattern
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (self.expect("*")) and (target := self.pattern_capture_target()):
            return ast.MatchStar(name=target, **self.span(_lnum, _col))
        self._reset(mark)
        if (self.expect("*")) and (self.wildcard_pattern()):
            return ast.MatchStar(name=None, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def mapping_pattern(self) -> Any | None:
        # mapping_pattern: '{' '}' | '{' double_star_pattern ','? '}' | '{' items_pattern ',' double_star_pattern ','? '}' | '{' items_pattern ','? '}'
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (self.expect("{")) and (self.expect("}")):
            return ast.MatchMapping(keys=[], patterns=[], rest=None, **self.span(_lnum, _col))
        self._reset(mark)
        if (
            (self.expect("{"))
            and (rest := self.double_star_pattern())
            and (self.expect(","),)
            and (self.expect("}"))
        ):
            return ast.MatchMapping(keys=[], patterns=[], rest=rest, **self.span(_lnum, _col))
        self._reset(mark)
        if (
            (self.expect("{"))
            and (items := self.items_pattern())
            and (self.expect(","))
            and (rest := self.double_star_pattern())
            and (self.expect(","),)
            and (self.expect("}"))
        ):
            return ast.MatchMapping(
                keys=[k for (k, _) in items],
                patterns=[p for (_, p) in items],
                rest=rest,
                **self.span(_lnum, _col),
            )
        self._reset(mark)
        if (
            (self.expect("{"))
            and (items := self.items_pattern())
            and (self.expect(","),)
            and (self.expect("}"))
        ):
            return ast.MatchMapping(
                keys=[k for (k, _) in items],
                patterns=[p for (_, p) in items],
                rest=None,
                **self.span(_lnum, _col),
            )
        self._reset(mark)
        return None

    @memoize
    def items_pattern(self) -> Any | None:
        # items_pattern: ','.key_value_pattern+
        mark = self._mark()
        if gathered := self.gathered(self.key_value_pattern, self.expect, ","):
            return gathered
        self._reset(mark)
        return None

    @memoize
    def key_value_pattern(self) -> tuple[ast.expr, ast.pattern] | None:
        # key_value_pattern: (literal_expr | attr) ':' pattern
        mark = self._mark()
        if (key := self._tmp_22()) and (self.expect(":")) and (pattern := self.pattern()):
            return (key, pattern)
        self._reset(mark)
        return None

    @memoize
    def double_star_pattern(self) -> Any | None:
        # double_star_pattern: '**' pattern_capture_target
        mark = self._mark()
        if (self.expect("**")) and (target := self.pattern_capture_target()):
            return target
        self._reset(mark)
        return None

    @memoize
    def class_pattern(self) -> ast.MatchClass | None:
        # class_pattern: name_or_attr '(' ')' | name_or_attr '(' positional_patterns ','? ')' | name_or_attr '(' keyword_patterns ','? ')' | name_or_attr '(' positional_patterns ',' keyword_patterns ','? ')' | invalid_class_pattern
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (cls := self.name_or_attr()) and (self.expect("(")) and (self.expect(")")):
            return ast.MatchClass(
                cls=cls, patterns=[], kwd_attrs=[], kwd_patterns=[], **self.span(_lnum, _col)
            )
        self._reset(mark)
        if (
            (cls := self.name_or_attr())
            and (self.expect("("))
            and (patterns := self.positional_patterns())
            and (self.expect(","),)
            and (self.expect(")"))
        ):
            return ast.MatchClass(
                cls=cls, patterns=patterns, kwd_attrs=[], kwd_patterns=[], **self.span(_lnum, _col)
            )
        self._reset(mark)
        if (
            (cls := self.name_or_attr())
            and (self.expect("("))
            and (keywords := self.keyword_patterns())
            and (self.expect(","),)
            and (self.expect(")"))
        ):
            return ast.MatchClass(
                cls=cls,
                patterns=[],
                kwd_attrs=[k for (k, _) in keywords],
                kwd_patterns=[p for (_, p) in keywords],
                **self.span(_lnum, _col),
            )
        self._reset(mark)
        if (
            (cls := self.name_or_attr())
            and (self.expect("("))
            and (patterns := self.positional_patterns())
            and (self.expect(","))
            and (keywords := self.keyword_patterns())
            and (self.expect(","),)
            and (self.expect(")"))
        ):
            return ast.MatchClass(
                cls=cls,
                patterns=patterns,
                kwd_attrs=[k for (k, _) in keywords],
                kwd_patterns=[p for (_, p) in keywords],
                **self.span(_lnum, _col),
            )
        self._reset(mark)
        if self.call_invalid_rules and (self.invalid_class_pattern()):
            return None
        self._reset(mark)
        return None

    @memoize
    def positional_patterns(self) -> list[ast.pattern] | None:
        # positional_patterns: ','.pattern+
        mark = self._mark()
        if args := self.gathered(self.pattern, self.expect, ","):
            return args
        self._reset(mark)
        return None

    @memoize
    def keyword_patterns(self) -> Any | None:
        # keyword_patterns: ','.keyword_pattern+
        mark = self._mark()
        if gathered := self.gathered(self.keyword_pattern, self.expect, ","):
            return gathered
        self._reset(mark)
        return None

    @memoize
    def keyword_pattern(self) -> tuple[str, ast.pattern] | None:
        # keyword_pattern: NAME '=' pattern
        mark = self._mark()
        if (arg := self.name()) and (self.expect("=")) and (value := self.pattern()):
            return (arg.string, value)
        self._reset(mark)
        return None

    @memoize
    def type_alias(self) -> ast.TypeAlias | None:
        # type_alias: "type" NAME type_params? '=' expression
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (
            (self.expect("type"))
            and (n := self.name())
            and (t := self.type_params(),)
            and (self.expect("="))
            and (b := self.expression())
        ):
            return self.check_version(
                (3, 12),
                "Type statement is",
                ast.TypeAlias(
                    name=ast.Name(
                        id=n.string,
                        ctx=Store,
                        lineno=n.start[0],
                        col_offset=n.start[1],
                        end_lineno=n.end[0],
                        end_col_offset=n.end[1],
                    ),
                    type_params=t or [],
                    value=b,
                    **self.span(_lnum, _col),
                ),
            )
        self._reset(mark)
        return None

    @memoize
    def type_params(self) -> list[Any] | None:
        # type_params: '[' type_param_seq ']'
        mark = self._mark()
        if (self.expect("[")) and (t := self.type_param_seq()) and (self.expect("]")):
            return self.check_version((3, 12), "Type parameter lists are", t)
        self._reset(mark)
        return None

    @memoize
    def type_param_seq(self) -> list[Any] | None:
        # type_param_seq: ','.type_param+ ','?
        mark = self._mark()
        if (a := self.gathered(self.type_param, self.expect, ",")) and (self.expect(","),):
            return a
        self._reset(mark)
        return None

    @memoize
    def type_param(self) -> ast.type_param | None:
        # type_param: NAME type_param_bound? | '*' NAME ':' expression | '*' NAME | '**' NAME ':' expression | '**' NAME
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (a := self.name()) and (b := self.type_param_bound(),):
            return ast.TypeVar(name=a.string, bound=b, **self.span(_lnum, _col))
        self._reset(mark)
        if (self.expect("*")) and (self.name()) and (colon := self.expect(":")) and (e := self.expression()):
            self.raise_syntax_error_starting_from(
                "cannot use constraints with TypeVarTuple"
                if isinstance(e, ast.Tuple)
                else "cannot use bound with TypeVarTuple",
                colon,
            )
        self._reset(mark)
        if (self.expect("*")) and (a := self.name()):
            return ast.TypeVarTuple(name=a.string, **self.span(_lnum, _col))
        self._reset(mark)
        if (self.expect("**")) and (self.name()) and (colon := self.expect(":")) and (e := self.expression()):
            self.raise_syntax_error_starting_from(
                "cannot use constraints with ParamSpec"
                if isinstance(e, ast.Tuple)
                else "cannot use bound with ParamSpec",
                colon,
            )
        self._reset(mark)
        if (self.expect("**")) and (a := self.name()):
            return ast.ParamSpec(name=a.string, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def type_param_bound(self) -> Any | None:
        # type_param_bound: ':' expression
        mark = self._mark()
        if (self.expect(":")) and (e := self.expression()):
            return e
        self._reset(mark)
        return None

    @memoize
    def expressions(self) -> ast.expr | None:
        # expressions: expression (comma_expression)+ ','? | expression ',' | expression
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (a := self.expression()) and (b := self.repeated(self.comma_expression)) and (self.expect(","),):
            return ast.Tuple(elts=[a] + b, ctx=Load, **self.span(_lnum, _col))
        self._reset(mark)
        if (a := self.expression()) and (self.expect(",")):
            return ast.Tuple(elts=[a], ctx=Load, **self.span(_lnum, _col))
        self._reset(mark)
        if expression := self.expression():
            return expression
        self._reset(mark)
        return None

    @memoize
    def comma_expression(self) -> ast.expr | None:
        # comma_expression: ',' expression
        mark = self._mark()
        if (self.expect(",")) and (c := self.expression()):
            return c
        self._reset(mark)
        return None

    @memoize
    def expression(self) -> ast.expr | None:
        # expression: invalid_expression | invalid_legacy_expression | disjunction 'if' disjunction 'else' expression | disjunction | lambdef
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if self.call_invalid_rules and (self.invalid_expression()):
            return None
        self._reset(mark)
        if self.call_invalid_rules and (self.invalid_legacy_expression()):
            return None
        self._reset(mark)
        if (
            (a := self.disjunction())
            and (self.expect("if"))
            and (b := self.disjunction())
            and (self.expect("else"))
            and (c := self.expression())
        ):
            return ast.IfExp(body=a, test=b, orelse=c, **self.span(_lnum, _col))
        self._reset(mark)
        if disjunction := self.disjunction():
            return disjunction
        self._reset(mark)
        if lambdef := self.lambdef():
            return lambdef
        self._reset(mark)
        return None

    @memoize
    def yield_expr(self) -> Any | None:
        # yield_expr: 'yield' 'from' expression | 'yield' star_expressions?
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (self.expect("yield")) and (self.expect("from")) and (a := self.expression()):
            return ast.YieldFrom(value=a, **self.span(_lnum, _col))
        self._reset(mark)
        if (self.expect("yield")) and (a := self.star_expressions(),):
            return ast.Yield(value=a, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def star_expressions(self) -> ast.expr | None:
        # star_expressions: star_expression (comma_star_expr)+ ','? | star_expression ',' | star_expression
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (
            (a := self.star_expression())
            and (b := self.repeated(self.comma_star_expr))
            and (self.expect(","),)
        ):
            return ast.Tuple(elts=[a] + b, ctx=Load, **self.span(_lnum, _col))
        self._reset(mark)
        if (a := self.star_expression()) and (self.expect(",")):
            return ast.Tuple(elts=[a], ctx=Load, **self.span(_lnum, _col))
        self._reset(mark)
        if star_expression := self.star_expression():
            return star_expression
        self._reset(mark)
        return None

    @memoize
    def comma_star_expr(self) -> ast.expr | None:
        # comma_star_expr: ',' star_expression
        mark = self._mark()
        if (self.expect(",")) and (c := self.star_expression()):
            return c
        self._reset(mark)
        return None

    @memoize
    def star_expression(self) -> ast.expr | None:
        # star_expression: '*' bitwise_or | expression
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (self.expect("*")) and (a := self.bitwise_or()):
            return ast.Starred(value=a, ctx=Load, **self.span(_lnum, _col))
        self._reset(mark)
        if expression := self.expression():
            return expression
        self._reset(mark)
        return None

    @memoize
    def star_named_expressions(self) -> Any | None:
        # star_named_expressions: ','.star_named_expression+ ','?
        mark = self._mark()
        if (a := self.gathered(self.star_named_expression, self.expect, ",")) and (self.expect(","),):
            return a
        self._reset(mark)
        return None

    @memoize
    def star_named_expression(self) -> ast.Starred | ast.expr | None:
        # star_named_expression: '*' bitwise_or | named_expression
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (self.expect("*")) and (a := self.bitwise_or()):
            return ast.Starred(value=a, ctx=Load, **self.span(_lnum, _col))
        self._reset(mark)
        if named_expression := self.named_expression():
            return named_expression
        self._reset(mark)
        return None

    @memoize
    def assignment_expression(self) -> ast.expr | None:
        # assignment_expression: NAME ':=' ~ expression
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        cut = False
        if (a := self.name()) and (self.expect(":=")) and (cut := True) and (b := self.expression()):
            return ast.NamedExpr(
                target=ast.Name(
                    id=a.string,
                    ctx=Store,
                    lineno=a.start[0],
                    col_offset=a.start[1],
                    end_lineno=a.end[0],
                    end_col_offset=a.end[1],
                ),
                value=b,
                **self.span(_lnum, _col),
            )
        self._reset(mark)
        if cut:
            return None
        return None

    @memoize
    def named_expression(self) -> ast.expr | None:
        # named_expression: assignment_expression | invalid_named_expression | expression !':='
        mark = self._mark()
        if assignment_expression := self.assignment_expression():
            return assignment_expression
        self._reset(mark)
        if self.call_invalid_rules and (self.invalid_named_expression()):
            return None
        self._reset(mark)
        if (a := self.expression()) and (self.negative_lookahead(self.expect, ":=")):
            return a
        self._reset(mark)
        return None

    @memoize
    def disjunction(self) -> ast.expr | None:
        # disjunction: conjunction (disjunction_part)+ | conjunction
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (a := self.conjunction()) and (b := self.repeated(self.disjunction_part)):
            return ast.BoolOp(op=ast.Or(), values=[a] + b, **self.span(_lnum, _col))
        self._reset(mark)
        if conjunction := self.conjunction():
            return conjunction
        self._reset(mark)
        return None

    @memoize
    def disjunction_part(self) -> ast.expr | None:
        # disjunction_part: ('or' | '||') conjunction
        mark = self._mark()
        if (self._tmp_23()) and (c := self.conjunction()):
            return c
        self._reset(mark)
        return None

    @memoize
    def conjunction(self) -> ast.expr | None:
        # conjunction: inversion conjunction_part+ | inversion
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (a := self.inversion()) and (b := self.repeated(self.conjunction_part)):
            return ast.BoolOp(op=ast.And(), values=[a] + b, **self.span(_lnum, _col))
        self._reset(mark)
        if inversion := self.inversion():
            return inversion
        self._reset(mark)
        return None

    @memoize
    def conjunction_part(self) -> ast.expr | None:
        # conjunction_part: ('and' | '&&') inversion
        mark = self._mark()
        if (self._tmp_24()) and (c := self.inversion()):
            return c
        self._reset(mark)
        return None

    @memoize
    def inversion(self) -> ast.expr | None:
        # inversion: 'not' inversion | comparison
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (self.expect("not")) and (a := self.inversion()):
            return ast.UnaryOp(op=ast.Not(), operand=a, **self.span(_lnum, _col))
        self._reset(mark)
        if comparison := self.comparison():
            return comparison
        self._reset(mark)
        return None

    @memoize
    def comparison(self) -> ast.expr | None:
        # comparison: bitwise_or compare_op_bitwise_or_pair+ | bitwise_or
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (a := self.bitwise_or()) and (b := self.repeated(self.compare_op_bitwise_or_pair)):
            return ast.Compare(
                left=a,
                ops=self.get_comparison_ops(b),
                comparators=self.get_comparators(b),
                **self.span(_lnum, _col),
            )
        self._reset(mark)
        if bitwise_or := self.bitwise_or():
            return bitwise_or
        self._reset(mark)
        return None

    @memoize
    def compare_op_bitwise_or_pair(self) -> tuple[ast.cmpop, ast.expr] | None:
        # compare_op_bitwise_or_pair: eq_bitwise_or | noteq_bitwise_or | lte_bitwise_or | lt_bitwise_or | gte_bitwise_or | gt_bitwise_or | notin_bitwise_or | in_bitwise_or | isnot_bitwise_or | is_bitwise_or
        return self.seq_alts(
            self.eq_bitwise_or,
            self.noteq_bitwise_or,
            self.lte_bitwise_or,
            self.lt_bitwise_or,
            self.gte_bitwise_or,
            self.gt_bitwise_or,
            self.notin_bitwise_or,
            self.in_bitwise_or,
            self.isnot_bitwise_or,
            self.is_bitwise_or,
        )

    @memoize
    def eq_bitwise_or(self) -> tuple[ast.cmpop, ast.expr] | None:
        # eq_bitwise_or: '==' bitwise_or
        mark = self._mark()
        if (self.expect("==")) and (a := self.bitwise_or()):
            return (ast.Eq(), a)
        self._reset(mark)
        return None

    @memoize
    def noteq_bitwise_or(self) -> tuple[ast.NotEq, Any] | None:
        # noteq_bitwise_or: '!=' bitwise_or
        mark = self._mark()
        if (self.expect("!=")) and (a := self.bitwise_or()):
            return (ast.NotEq(), a)
        self._reset(mark)
        return None

    @memoize
    def lte_bitwise_or(self) -> tuple[ast.cmpop, ast.expr] | None:
        # lte_bitwise_or: '<=' bitwise_or
        mark = self._mark()
        if (self.expect("<=")) and (a := self.bitwise_or()):
            return (ast.LtE(), a)
        self._reset(mark)
        return None

    @memoize
    def lt_bitwise_or(self) -> tuple[ast.cmpop, ast.expr] | None:
        # lt_bitwise_or: '<' bitwise_or
        mark = self._mark()
        if (self.expect("<")) and (a := self.bitwise_or()):
            return (ast.Lt(), a)
        self._reset(mark)
        return None

    @memoize
    def gte_bitwise_or(self) -> tuple[ast.cmpop, ast.expr] | None:
        # gte_bitwise_or: '>=' bitwise_or
        mark = self._mark()
        if (self.expect(">=")) and (a := self.bitwise_or()):
            return (ast.GtE(), a)
        self._reset(mark)
        return None

    @memoize
    def gt_bitwise_or(self) -> tuple[ast.cmpop, ast.expr] | None:
        # gt_bitwise_or: '>' bitwise_or
        mark = self._mark()
        if (self.expect(">")) and (a := self.bitwise_or()):
            return (ast.Gt(), a)
        self._reset(mark)
        return None

    @memoize
    def notin_bitwise_or(self) -> tuple[ast.cmpop, ast.expr] | None:
        # notin_bitwise_or: 'not' 'in' bitwise_or
        mark = self._mark()
        if (self.expect("not")) and (self.expect("in")) and (a := self.bitwise_or()):
            return (ast.NotIn(), a)
        self._reset(mark)
        return None

    @memoize
    def in_bitwise_or(self) -> tuple[ast.cmpop, ast.expr] | None:
        # in_bitwise_or: 'in' bitwise_or
        mark = self._mark()
        if (self.expect("in")) and (a := self.bitwise_or()):
            return (ast.In(), a)
        self._reset(mark)
        return None

    @memoize
    def isnot_bitwise_or(self) -> tuple[ast.cmpop, ast.expr] | None:
        # isnot_bitwise_or: 'is' 'not' bitwise_or
        mark = self._mark()
        if (self.expect("is")) and (self.expect("not")) and (a := self.bitwise_or()):
            return (ast.IsNot(), a)
        self._reset(mark)
        return None

    @memoize
    def is_bitwise_or(self) -> tuple[ast.cmpop, ast.expr] | None:
        # is_bitwise_or: 'is' bitwise_or
        mark = self._mark()
        if (self.expect("is")) and (a := self.bitwise_or()):
            return (ast.Is(), a)
        self._reset(mark)
        return None

    @memoize_left_rec
    def bitwise_or(self) -> Any | None:
        # bitwise_or: bitwise_or '|' bitwise_xor | bitwise_xor
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (a := self.bitwise_or()) and (self.expect("|")) and (b := self.bitwise_xor()):
            return ast.BinOp(left=a, op=ast.BitOr(), right=b, **self.span(_lnum, _col))
        self._reset(mark)
        if bitwise_xor := self.bitwise_xor():
            return bitwise_xor
        self._reset(mark)
        return None

    @memoize_left_rec
    def bitwise_xor(self) -> Any | None:
        # bitwise_xor: bitwise_xor '^' bitwise_and | bitwise_and
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (a := self.bitwise_xor()) and (self.expect("^")) and (b := self.bitwise_and()):
            return ast.BinOp(left=a, op=ast.BitXor(), right=b, **self.span(_lnum, _col))
        self._reset(mark)
        if bitwise_and := self.bitwise_and():
            return bitwise_and
        self._reset(mark)
        return None

    @memoize_left_rec
    def bitwise_and(self) -> Any | None:
        # bitwise_and: bitwise_and '&' shift_expr | shift_expr
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (a := self.bitwise_and()) and (self.expect("&")) and (b := self.shift_expr()):
            return ast.BinOp(left=a, op=ast.BitAnd(), right=b, **self.span(_lnum, _col))
        self._reset(mark)
        if shift_expr := self.shift_expr():
            return shift_expr
        self._reset(mark)
        return None

    @memoize_left_rec
    def shift_expr(self) -> Any | None:
        # shift_expr: shift_expr '<<' sum | shift_expr '>>' sum | sum
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (a := self.shift_expr()) and (self.expect("<<")) and (b := self.sum()):
            return ast.BinOp(left=a, op=ast.LShift(), right=b, **self.span(_lnum, _col))
        self._reset(mark)
        if (a := self.shift_expr()) and (self.expect(">>")) and (b := self.sum()):
            return ast.BinOp(left=a, op=ast.RShift(), right=b, **self.span(_lnum, _col))
        self._reset(mark)
        if sum := self.sum():
            return sum
        self._reset(mark)
        return None

    @memoize_left_rec
    def sum(self) -> Any | None:
        # sum: sum '+' term | sum '-' term | term
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (a := self.sum()) and (self.expect("+")) and (b := self.term()):
            return ast.BinOp(left=a, op=ast.Add(), right=b, **self.span(_lnum, _col))
        self._reset(mark)
        if (a := self.sum()) and (self.expect("-")) and (b := self.term()):
            return ast.BinOp(left=a, op=ast.Sub(), right=b, **self.span(_lnum, _col))
        self._reset(mark)
        if term := self.term():
            return term
        self._reset(mark)
        return None

    @memoize_left_rec
    def term(self) -> Any | None:
        # term: term '*' factor | term '/' factor | term '//' factor | term '%' factor | term '@' factor | factor
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (a := self.term()) and (self.expect("*")) and (b := self.factor()):
            return ast.BinOp(left=a, op=ast.Mult(), right=b, **self.span(_lnum, _col))
        self._reset(mark)
        if (a := self.term()) and (self.expect("/")) and (b := self.factor()):
            return ast.BinOp(left=a, op=ast.Div(), right=b, **self.span(_lnum, _col))
        self._reset(mark)
        if (a := self.term()) and (self.expect("//")) and (b := self.factor()):
            return ast.BinOp(left=a, op=ast.FloorDiv(), right=b, **self.span(_lnum, _col))
        self._reset(mark)
        if (a := self.term()) and (self.expect("%")) and (b := self.factor()):
            return ast.BinOp(left=a, op=ast.Mod(), right=b, **self.span(_lnum, _col))
        self._reset(mark)
        if (a := self.term()) and (self.expect("@")) and (b := self.factor()):
            return ast.BinOp(left=a, op=ast.MatMult(), right=b, **self.span(_lnum, _col))
        self._reset(mark)
        if factor := self.factor():
            return factor
        self._reset(mark)
        return None

    @memoize
    def factor(self) -> Any | None:
        # factor: '+' factor | '-' factor | '~' factor | power
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (self.expect("+")) and (a := self.factor()):
            return ast.UnaryOp(op=ast.UAdd(), operand=a, **self.span(_lnum, _col))
        self._reset(mark)
        if (self.expect("-")) and (a := self.factor()):
            return ast.UnaryOp(op=ast.USub(), operand=a, **self.span(_lnum, _col))
        self._reset(mark)
        if (self.expect("~")) and (a := self.factor()):
            return ast.UnaryOp(op=ast.Invert(), operand=a, **self.span(_lnum, _col))
        self._reset(mark)
        if power := self.power():
            return power
        self._reset(mark)
        return None

    @memoize
    def power(self) -> Any | None:
        # power: await_primary '**' factor | await_primary
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (a := self.await_primary()) and (self.expect("**")) and (b := self.factor()):
            return ast.BinOp(left=a, op=ast.Pow(), right=b, **self.span(_lnum, _col))
        self._reset(mark)
        if await_primary := self.await_primary():
            return await_primary
        self._reset(mark)
        return None

    @memoize
    def await_primary(self) -> Any | None:
        # await_primary: 'await' primary | primary
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (self.expect("await")) and (a := self.primary()):
            return ast.Await(a, **self.span(_lnum, _col))
        self._reset(mark)
        if primary := self.primary():
            return primary
        self._reset(mark)
        return None

    @memoize_left_rec
    def primary(self) -> Any | None:
        # primary: primary '.' NAME | primary genexp | func_macro_start ~ MACRO_PARAM*? &&')' | primary '(' arguments? ')' | primary '[' slices ']' | &('$(' | '$[' | '![' | '!(') ~ sub_procs | env_atom | (".".help_atom+) | atom
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (a := self.primary()) and (self.expect(".")) and (b := self.name()):
            return ast.Attribute(value=a, attr=b.string, ctx=Load, **self.span(_lnum, _col))
        self._reset(mark)
        if (a1 := self.primary()) and (b1 := self.genexp()):
            return ast.Call(func=a1, args=[b1], keywords=[], **self.span(_lnum, _col))
        self._reset(mark)
        cut = False
        if (
            (a2 := self.func_macro_start())
            and (cut := True)
            and (b2 := self.repeated(self.token, "MACRO_PARAM"),)
            and (self.expect_forced(self.expect(")"), "')'"))
        ):
            return self.macro_call(a2, b2, **self.span(_lnum, _col))
        self._reset(mark)
        if cut:
            return None
        if (a3 := self.primary()) and (self.expect("(")) and (b3 := self.arguments(),) and (self.expect(")")):
            return ast.Call(
                func=a3, args=b3[0] if b3 else [], keywords=b3[1] if b3 else [], **self.span(_lnum, _col)
            )
        self._reset(mark)
        if (a4 := self.primary()) and (self.expect("[")) and (b4 := self.slices()) and (self.expect("]")):
            return ast.Subscript(value=a4, slice=b4, ctx=Load, **self.span(_lnum, _col))
        self._reset(mark)
        cut = False
        if (self.positive_lookahead(self._tmp_25)) and (cut := True) and (sub_procs := self.sub_procs()):
            return sub_procs
        self._reset(mark)
        if cut:
            return None
        if env_atom := self.env_atom():
            return env_atom
        self._reset(mark)
        if a5 := self.gathered(self.help_atom, self.expect, "."):
            return self.expand_help(a5, **self.span(_lnum, _col))
        self._reset(mark)
        if atom := self.atom():
            return atom
        self._reset(mark)
        return None

    @logger
    def func_macro_start(self) -> Any | None:
        # func_macro_start: primary '!('
        mark = self._mark()
        if (a := self.primary()) and (self.expect("!(")):
            return self.handle_func_macro_start(a)
        self._reset(mark)
        return None

    @memoize
    def sub_procs(self) -> ast.Call | None:
        # sub_procs: '$(' ~ proc_cmds ')' | '$[' ~ proc_cmds ']' | '![' ~ proc_cmds ']' | '!(' ~ proc_cmds ')'
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        cut = False
        if (self.expect("$(")) and (cut := True) and (args := self.proc_cmds()) and (self.expect(")")):
            return self.handle_proc("subproc_captured", args, **self.span(_lnum, _col))
        self._reset(mark)
        if cut:
            return None
        cut = False
        if (self.expect("$[")) and (cut := True) and (args := self.proc_cmds()) and (self.expect("]")):
            return self.handle_proc("subproc_uncaptured", args, **self.span(_lnum, _col))
        self._reset(mark)
        if cut:
            return None
        cut = False
        if (self.expect("![")) and (cut := True) and (args := self.proc_cmds()) and (self.expect("]")):
            return self.handle_proc("subproc_captured_hiddenobject", args, **self.span(_lnum, _col))
        self._reset(mark)
        if cut:
            return None
        cut = False
        if (self.expect("!(")) and (cut := True) and (args := self.proc_cmds()) and (self.expect(")")):
            return self.handle_proc("subproc_captured_object", args, **self.span(_lnum, _col))
        self._reset(mark)
        if cut:
            return None
        return None

    @memoize
    def help_atom(self) -> tuple[ast.Name, TokenInfo] | None:
        # help_atom: atom ('??' | '?')
        mark = self._mark()
        if (a := self.atom()) and (b := self._tmp_26()):
            return (a, b)
        self._reset(mark)
        return None

    @memoize
    def env_atom(self) -> ast.Subscript | None:
        # env_atom: '$' NAME | '${' slices '}'
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (self.expect("$")) and (a := self.name()):
            return self.expand_env_name(a, **self.span(_lnum, _col))
        self._reset(mark)
        if (self.expect("${")) and (a := self.slices()) and (self.expect("}")):
            return self.expand_env_expr(a, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def proc_cmds(self) -> Any | None:
        # proc_cmds: proc_cmd+
        mark = self._mark()
        if a := self.repeated(self.proc_cmd):
            return self.proc_args(a)
        self._reset(mark)
        return None

    @memoize
    def proc_cmd(self) -> ast.expr | TokenInfo | None:
        # proc_cmd: sub_procs | '@(' ~ (bare_genexp | expressions) ')' | '@$(' ~ proc_cmds ')' | env_atom | search_path | proc_macro_start ~ ((cmd_group | any_cmd))* | cmd_group | cmd_name
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if sub_procs := self.sub_procs():
            return sub_procs
        self._reset(mark)
        cut = False
        if (self.expect("@(")) and (cut := True) and (a := self._tmp_27()) and (self.expect(")")):
            return self.proc_pyexpr(a, **self.span(_lnum, _col))
        self._reset(mark)
        if cut:
            return None
        cut = False
        if (self.expect("@$(")) and (cut := True) and (a := self.proc_cmds()) and (self.expect(")")):
            return self.proc_inject(a, **self.span(_lnum, _col))
        self._reset(mark)
        if cut:
            return None
        if env_atom := self.env_atom():
            return env_atom
        self._reset(mark)
        if search_path := self.search_path():
            return search_path
        self._reset(mark)
        cut = False
        if (self.proc_macro_start()) and (cut := True) and (a := self.repeated(self._tmp_28),):
            return self.proc_macro_arg(a, **self.span(_lnum, _col))
        self._reset(mark)
        if cut:
            return None
        if a := self.cmd_group():
            return self.proc_macro_arg(a, **self.span(_lnum, _col))
        self._reset(mark)
        if cmd_name := self.cmd_name():
            return cmd_name
        self._reset(mark)
        return None

    @memoize
    def proc_macro_start(self) -> Any | None:
        # proc_macro_start: &cmd_name '!'
        mark = self._mark()
        if (self.positive_lookahead(self.cmd_name)) and (a := self.expect("!")):
            return self.handle_proc_macro_start(a)
        self._reset(mark)
        return None

    @memoize
    def cmd_name(self) -> TokenInfo | None:
        # cmd_name: NAME | NUMBER | STRING | !']' !')' !'}' OP
        mark = self._mark()
        if name := self.name():
            return name
        self._reset(mark)
        if _number := self.token("NUMBER"):
            return _number
        self._reset(mark)
        if _string := self.token("STRING"):
            return _string
        self._reset(mark)
        if (
            (self.negative_lookahead(self.expect, "]"))
            and (self.negative_lookahead(self.expect, ")"))
            and (self.negative_lookahead(self.expect, "}"))
            and (_op := self.token("OP"))
        ):
            return _op
        self._reset(mark)
        return None

    @memoize
    def any_cmd(self) -> TokenInfo | None:
        # any_cmd: cmd_name | WS | KEYWORD
        return self.seq_alts(
            self.cmd_name,
            (self.token, "WS"),
            self.keyword,
        )

    @memoize
    def cmd_group(self) -> str | None:
        # cmd_group: ('(' | '!(' | '$(') any_cmd* ')' | ('[' | '![' | '$[') any_cmd* ']'
        mark = self._mark()
        if (a := self._tmp_29()) and (b := self.repeated(self.any_cmd),) and (c := self.expect(")")):
            return "".join(i.string for i in [a, *b, c])
        self._reset(mark)
        if (a := self._tmp_30()) and (b := self.repeated(self.any_cmd),) and (c := self.expect("]")):
            return "".join(i.string for i in [a, *b, c])
        self._reset(mark)
        return None

    @memoize
    def slices(self) -> Any | None:
        # slices: slice !',' | ','.(slice | starred_expression)+ ','?
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (a := self.slice()) and (self.negative_lookahead(self.expect, ",")):
            return a
        self._reset(mark)
        if (a := self.gathered(self._tmp_31, self.expect, ",")) and (self.expect(","),):
            return ast.Tuple(elts=a, ctx=Load, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def slice(self) -> Any | None:
        # slice: expression? ':' expression? [':' expression?] | named_expression
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (
            (a := self.expression(),)
            and (self.expect(":"))
            and (b := self.expression(),)
            and (c := self._tmp_32(),)
        ):
            return ast.Slice(lower=a, upper=b, step=c, **self.span(_lnum, _col))
        self._reset(mark)
        if a := self.named_expression():
            return a
        self._reset(mark)
        return None

    @memoize
    def atom(self) -> Any | None:
        # atom: search_path | NAME | 'True' | 'False' | 'None' | &(STRING | FSTRING_START) strings | NUMBER | &'(' (ptuple | group | genexp) | &'[' (plist | listcomp) | &'{' (dict | set | dictcomp | setcomp) | '...'
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if search_path := self.search_path():
            return search_path
        self._reset(mark)
        if a := self.name():
            return ast.Name(id=a.string, ctx=Load, **self.span(_lnum, _col))
        self._reset(mark)
        if self.expect("True"):
            return ast.Constant(value=True, **self.span(_lnum, _col))
        self._reset(mark)
        if self.expect("False"):
            return ast.Constant(value=False, **self.span(_lnum, _col))
        self._reset(mark)
        if self.expect("None"):
            return ast.Constant(value=None, **self.span(_lnum, _col))
        self._reset(mark)
        if (self.positive_lookahead(self._tmp_33)) and (strings := self.strings()):
            return strings
        self._reset(mark)
        if a := self.token("NUMBER"):
            return ast.Constant(value=ast.literal_eval(a.string), **self.span(_lnum, _col))
        self._reset(mark)
        if (self.positive_lookahead(self.expect, "(")) and (_tmp_34 := self._tmp_34()):
            return _tmp_34
        self._reset(mark)
        if (self.positive_lookahead(self.expect, "[")) and (_tmp_35 := self._tmp_35()):
            return _tmp_35
        self._reset(mark)
        if (self.positive_lookahead(self.expect, "{")) and (_tmp_36 := self._tmp_36()):
            return _tmp_36
        self._reset(mark)
        if self.expect("..."):
            return ast.Constant(value=Ellipsis, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def search_path(self) -> ast.Call | None:
        # search_path: SEARCH_PATH
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if a := self.token("SEARCH_PATH"):
            return self.expand_search_path(a, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def group(self) -> Any | None:
        # group: '(' (yield_expr | named_expression) ')' | invalid_group
        mark = self._mark()
        if (self.expect("(")) and (a := self._tmp_37()) and (self.expect(")")):
            return a
        self._reset(mark)
        if self.call_invalid_rules and (self.invalid_group()):
            return None
        self._reset(mark)
        return None

    @memoize
    def lambdef(self) -> ast.Lambda | None:
        # lambdef: 'lambda' lambda_params? ':' expression
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (
            (self.expect("lambda"))
            and (a := self.lambda_params(),)
            and (self.expect(":"))
            and (b := self.expression())
        ):
            return ast.Lambda(
                args=a or self.make_arguments(None, [], None, [], (None, [], None)),
                body=b,
                **self.span(_lnum, _col),
            )
        self._reset(mark)
        return None

    @memoize
    def lambda_params(self) -> Any | None:
        # lambda_params: invalid_lambda_parameters | lambda_parameters
        return self.seq_alts(
            self.invalid_lambda_parameters,
            self.lambda_parameters,
        )

    @memoize
    def lambda_parameters(self) -> ast.arguments | None:
        # lambda_parameters: lambda_slash_no_default lambda_param_no_default* lambda_param_with_default* lambda_star_etc? | lambda_slash_with_default lambda_param_with_default* lambda_star_etc? | lambda_param_no_default+ lambda_param_with_default* lambda_star_etc? | lambda_param_with_default+ lambda_star_etc? | lambda_star_etc
        mark = self._mark()
        if (
            (a := self.lambda_slash_no_default())
            and (b := self.repeated(self.lambda_param_no_default),)
            and (c := self.repeated(self.lambda_param_with_default),)
            and (d := self.lambda_star_etc(),)
        ):
            return self.make_arguments(a, [], b, c, d)
        self._reset(mark)
        if (
            (a1 := self.lambda_slash_with_default())
            and (b1 := self.repeated(self.lambda_param_with_default),)
            and (c1 := self.lambda_star_etc(),)
        ):
            return self.make_arguments(None, a1, None, b1, c1)
        self._reset(mark)
        if (
            (a2 := self.repeated(self.lambda_param_no_default))
            and (b2 := self.repeated(self.lambda_param_with_default),)
            and (c2 := self.lambda_star_etc(),)
        ):
            return self.make_arguments(None, [], a2, b2, c2)
        self._reset(mark)
        if (a3 := self.repeated(self.lambda_param_with_default)) and (b3 := self.lambda_star_etc(),):
            return self.make_arguments(None, [], None, a3, b3)
        self._reset(mark)
        if a4 := self.lambda_star_etc():
            return self.make_arguments(None, [], None, [], a4)
        self._reset(mark)
        return None

    @memoize
    def lambda_slash_no_default(self) -> list[tuple[ast.arg, None]] | None:
        # lambda_slash_no_default: lambda_param_no_default+ '/' ',' | lambda_param_no_default+ '/' &':'
        mark = self._mark()
        if (a := self.repeated(self.lambda_param_no_default)) and (self.expect("/")) and (self.expect(",")):
            return [(p, None) for p in a]
        self._reset(mark)
        if (
            (a := self.repeated(self.lambda_param_no_default))
            and (self.expect("/"))
            and (self.positive_lookahead(self.expect, ":"))
        ):
            return [(p, None) for p in a]
        self._reset(mark)
        return None

    @memoize
    def lambda_slash_with_default(self) -> list[tuple[ast.arg, Any]] | None:
        # lambda_slash_with_default: lambda_param_no_default* lambda_param_with_default+ '/' ',' | lambda_param_no_default* lambda_param_with_default+ '/' &':'
        mark = self._mark()
        if (
            (a := self.repeated(self.lambda_param_no_default),)
            and (b := self.repeated(self.lambda_param_with_default))
            and (self.expect("/"))
            and (self.expect(","))
        ):
            return ([(p, None) for p in a] if a else []) + b
        self._reset(mark)
        if (
            (a := self.repeated(self.lambda_param_no_default),)
            and (b := self.repeated(self.lambda_param_with_default))
            and (self.expect("/"))
            and (self.positive_lookahead(self.expect, ":"))
        ):
            return ([(p, None) for p in a] if a else []) + b
        self._reset(mark)
        return None

    @memoize
    def lambda_star_etc(self) -> tuple[ast.arg | None, list[tuple[ast.arg, Any]], ast.arg | None] | None:
        # lambda_star_etc: invalid_lambda_star_etc | '*' lambda_param_no_default lambda_param_maybe_default* lambda_kwds? | '*' ',' lambda_param_maybe_default+ lambda_kwds? | lambda_kwds
        mark = self._mark()
        if self.call_invalid_rules and (self.invalid_lambda_star_etc()):
            return None
        self._reset(mark)
        if (
            (self.expect("*"))
            and (a := self.lambda_param_no_default())
            and (b := self.repeated(self.lambda_param_maybe_default),)
            and (c := self.lambda_kwds(),)
        ):
            return (a, b, c)
        self._reset(mark)
        if (
            (self.expect("*"))
            and (self.expect(","))
            and (b := self.repeated(self.lambda_param_maybe_default))
            and (c := self.lambda_kwds(),)
        ):
            return (None, b, c)
        self._reset(mark)
        if a := self.lambda_kwds():
            return (None, [], a)
        self._reset(mark)
        return None

    @memoize
    def lambda_kwds(self) -> ast.arg | None:
        # lambda_kwds: invalid_lambda_kwds | '**' lambda_param_no_default
        mark = self._mark()
        if self.call_invalid_rules and (self.invalid_lambda_kwds()):
            return None
        self._reset(mark)
        if (self.expect("**")) and (a := self.lambda_param_no_default()):
            return a
        self._reset(mark)
        return None

    @memoize
    def lambda_param_no_default(self) -> ast.arg | None:
        # lambda_param_no_default: lambda_param ',' | lambda_param &':'
        mark = self._mark()
        if (a := self.lambda_param()) and (self.expect(",")):
            return a
        self._reset(mark)
        if (a := self.lambda_param()) and (self.positive_lookahead(self.expect, ":")):
            return a
        self._reset(mark)
        return None

    @memoize
    def lambda_param_with_default(self) -> tuple[ast.arg, Any] | None:
        # lambda_param_with_default: lambda_param default ',' | lambda_param default &':'
        mark = self._mark()
        if (a := self.lambda_param()) and (c := self.default()) and (self.expect(",")):
            return (a, c)
        self._reset(mark)
        if (
            (a := self.lambda_param())
            and (c := self.default())
            and (self.positive_lookahead(self.expect, ":"))
        ):
            return (a, c)
        self._reset(mark)
        return None

    @memoize
    def lambda_param_maybe_default(self) -> tuple[ast.arg, Any] | None:
        # lambda_param_maybe_default: lambda_param default? ',' | lambda_param default? &':'
        mark = self._mark()
        if (a := self.lambda_param()) and (c := self.default(),) and (self.expect(",")):
            return (a, c)
        self._reset(mark)
        if (
            (a := self.lambda_param())
            and (c := self.default(),)
            and (self.positive_lookahead(self.expect, ":"))
        ):
            return (a, c)
        self._reset(mark)
        return None

    @memoize
    def lambda_param(self) -> ast.arg | None:
        # lambda_param: NAME
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if a := self.name():
            return ast.arg(arg=a.string, annotation=None, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def fstring_mid(self) -> ast.FormattedValue | ast.Constant | None:
        # fstring_mid: fstring_replacement_field | FSTRING_MIDDLE
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if fstring_replacement_field := self.fstring_replacement_field():
            return fstring_replacement_field
        self._reset(mark)
        if t := self.token("FSTRING_MIDDLE"):
            return ast.Constant(value=t.string, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def fstring_replacement_field(self) -> ast.FormattedValue | None:
        # fstring_replacement_field: '{' annotated_rhs '='? fstring_conversion? fstring_full_format_spec? '}' | invalid_replacement_field
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (
            (self.expect("{"))
            and (a := self.annotated_rhs())
            and (debug_expr := self.expect("="),)
            and (conver := self.fstring_conversion(),)
            and (format := self.fstring_full_format_spec(),)
            and (self.expect("}"))
        ):
            return ast.FormattedValue(
                value=a,
                conversion=conver if conver else b"r"[0] if debug_expr else -1,
                format_spec=format,
                **self.span(_lnum, _col),
            )
        self._reset(mark)
        if self.call_invalid_rules and (self.invalid_replacement_field()):
            return None
        self._reset(mark)
        return None

    @memoize
    def fstring_conversion(self) -> int | None:
        # fstring_conversion: '!' NAME
        mark = self._mark()
        if (self.expect("!")) and (conv := self.name()):
            return self.check_fstring_conversion(conv)
        self._reset(mark)
        return None

    @memoize
    def fstring_full_format_spec(self) -> ast.JoinedStr | None:
        # fstring_full_format_spec: ':' fstring_format_spec*
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (self.expect(":")) and (spec := self.repeated(self.fstring_format_spec),):
            return ast.JoinedStr(
                values=spec if spec and (len(spec) > 1 or cast(ast.Constant, spec[0]).value) else [],
                **self.span(_lnum, _col),
            )
        self._reset(mark)
        return None

    @memoize
    def fstring_format_spec(self) -> ast.Constant | ast.FormattedValue | None:
        # fstring_format_spec: FSTRING_MIDDLE | fstring_replacement_field
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if t := self.token("FSTRING_MIDDLE"):
            return ast.Constant(value=t.string, **self.span(_lnum, _col))
        self._reset(mark)
        if fstring_replacement_field := self.fstring_replacement_field():
            return fstring_replacement_field
        self._reset(mark)
        return None

    @memoize
    def strings(self) -> Any | None:
        # strings: (anystr)+
        mark = self._mark()
        if a := self.repeated(self.anystr):
            return self.concatenate_strings(a)
        self._reset(mark)
        return None

    @memoize
    def anystr(self) -> ast.JoinedStr | TokenInfo | None:
        # anystr: fstring | STRING
        return self.seq_alts(
            self.fstring,
            (self.token, "STRING"),
        )

    @memoize
    def plist(self) -> ast.List | None:
        # plist: '[' star_named_expressions? ']'
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (self.expect("[")) and (a := self.star_named_expressions(),) and (self.expect("]")):
            return ast.List(elts=a or [], ctx=Load, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def ptuple(self) -> ast.Tuple | None:
        # ptuple: '(' [star_named_expression ',' star_named_expressions?] ')'
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (self.expect("(")) and (a := self._tmp_38(),) and (self.expect(")")):
            return ast.Tuple(elts=a or [], ctx=Load, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def set(self) -> ast.Set | None:
        # set: '{' star_named_expressions '}'
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (self.expect("{")) and (a := self.star_named_expressions()) and (self.expect("}")):
            return ast.Set(elts=a, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def dict(self) -> ast.Dict | None:
        # dict: '{' double_starred_kvpairs? '}' | '{' invalid_double_starred_kvpairs '}'
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (self.expect("{")) and (a := self.double_starred_kvpairs(),) and (self.expect("}")):
            return ast.Dict(
                keys=[kv[0] for kv in a or []], values=[kv[1] for kv in a or []], **self.span(_lnum, _col)
            )
        self._reset(mark)
        if (
            self.call_invalid_rules
            and (self.expect("{"))
            and (self.invalid_double_starred_kvpairs())
            and (self.expect("}"))
        ):
            return None
        self._reset(mark)
        return None

    @memoize
    def double_starred_kvpairs(self) -> list[Any] | None:
        # double_starred_kvpairs: ','.double_starred_kvpair+ ','?
        mark = self._mark()
        if (a := self.gathered(self.double_starred_kvpair, self.expect, ",")) and (self.expect(","),):
            return a
        self._reset(mark)
        return None

    @memoize
    def double_starred_kvpair(self) -> tuple[ast.expr, ast.expr] | None:
        # double_starred_kvpair: '**' bitwise_or | kvpair
        mark = self._mark()
        if (self.expect("**")) and (a := self.bitwise_or()):
            return (None, a)
        self._reset(mark)
        if kvpair := self.kvpair():
            return kvpair
        self._reset(mark)
        return None

    @memoize
    def kvpair(self) -> tuple[ast.expr, ast.expr] | None:
        # kvpair: expression ':' expression
        mark = self._mark()
        if (a := self.expression()) and (self.expect(":")) and (b := self.expression()):
            return (a, b)
        self._reset(mark)
        return None

    @memoize
    def for_if_clauses(self) -> list[ast.comprehension] | None:
        # for_if_clauses: for_if_clause+
        mark = self._mark()
        if a := self.repeated(self.for_if_clause):
            return a
        self._reset(mark)
        return None

    @memoize
    def for_if_clause(self) -> ast.comprehension | None:
        # for_if_clause: 'async' 'for' star_targets 'in' ~ disjunction (for_if_disjunction)* | 'for' star_targets 'in' ~ disjunction (for_if_disjunction)* | invalid_for_target
        mark = self._mark()
        cut = False
        if (
            (self.expect("async"))
            and (self.expect("for"))
            and (a := self.star_targets())
            and (self.expect("in"))
            and (cut := True)
            and (b := self.disjunction())
            and (c := self.repeated(self.for_if_disjunction),)
        ):
            return ast.comprehension(target=a, iter=b, ifs=c, is_async=1)
        self._reset(mark)
        if cut:
            return None
        cut = False
        if (
            (self.expect("for"))
            and (a := self.star_targets())
            and (self.expect("in"))
            and (cut := True)
            and (b := self.disjunction())
            and (c := self.repeated(self.for_if_disjunction),)
        ):
            return ast.comprehension(target=a, iter=b, ifs=c, is_async=0)
        self._reset(mark)
        if cut:
            return None
        if self.call_invalid_rules and (self.invalid_for_target()):
            return None
        self._reset(mark)
        return None

    @memoize
    def for_if_disjunction(self) -> ast.expr | None:
        # for_if_disjunction: 'if' disjunction
        mark = self._mark()
        if (self.expect("if")) and (z := self.disjunction()):
            return z
        self._reset(mark)
        return None

    @memoize
    def listcomp(self) -> ast.ListComp | None:
        # listcomp: '[' named_expression for_if_clauses ']' | invalid_comprehension
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (
            (self.expect("["))
            and (a := self.named_expression())
            and (b := self.for_if_clauses())
            and (self.expect("]"))
        ):
            return ast.ListComp(elt=a, generators=b, **self.span(_lnum, _col))
        self._reset(mark)
        if self.call_invalid_rules and (self.invalid_comprehension()):
            return None
        self._reset(mark)
        return None

    @memoize
    def setcomp(self) -> ast.SetComp | None:
        # setcomp: '{' named_expression for_if_clauses '}' | invalid_comprehension
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (
            (self.expect("{"))
            and (a := self.named_expression())
            and (b := self.for_if_clauses())
            and (self.expect("}"))
        ):
            return ast.SetComp(elt=a, generators=b, **self.span(_lnum, _col))
        self._reset(mark)
        if self.call_invalid_rules and (self.invalid_comprehension()):
            return None
        self._reset(mark)
        return None

    @memoize
    def genexp(self) -> ast.GeneratorExp | None:
        # genexp: '(' (assignment_expression | expression !':=') for_if_clauses ')' | invalid_comprehension
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (
            (self.expect("("))
            and (a := self._tmp_39())
            and (b := self.for_if_clauses())
            and (self.expect(")"))
        ):
            return ast.GeneratorExp(elt=a, generators=b, **self.span(_lnum, _col))
        self._reset(mark)
        if self.call_invalid_rules and (self.invalid_comprehension()):
            return None
        self._reset(mark)
        return None

    @memoize
    def bare_genexp(self) -> Any | None:
        # bare_genexp: (assignment_expression | expression !':=') for_if_clauses
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (a := self._tmp_39()) and (b := self.for_if_clauses()):
            return ast.GeneratorExp(elt=a, generators=b, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def dictcomp(self) -> ast.DictComp | None:
        # dictcomp: '{' kvpair for_if_clauses '}' | invalid_dict_comprehension
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (
            (self.expect("{"))
            and (a := self.kvpair())
            and (b := self.for_if_clauses())
            and (self.expect("}"))
        ):
            return ast.DictComp(key=a[0], value=a[1], generators=b, **self.span(_lnum, _col))
        self._reset(mark)
        if self.call_invalid_rules and (self.invalid_dict_comprehension()):
            return None
        self._reset(mark)
        return None

    @memoize
    def arguments(self) -> tuple[list[Any], list[Any]] | None:
        # arguments: args ','? &')' | invalid_arguments
        mark = self._mark()
        if (a := self.args()) and (self.expect(","),) and (self.positive_lookahead(self.expect, ")")):
            return a
        self._reset(mark)
        if self.call_invalid_rules and (self.invalid_arguments()):
            return None
        self._reset(mark)
        return None

    @memoize
    def args(self) -> tuple[list[Any], list[Any]] | None:
        # args: ','.args_arg+ [',' kwargs] | kwargs
        mark = self._mark()
        if (a := self.gathered(self.args_arg, self.expect, ",")) and (b := self._tmp_41(),):
            return (
                a + ([e for e in b if isinstance(e, ast.Starred)] if b else []),
                [e for e in b if not isinstance(e, ast.Starred)] if b else [],
            )
        self._reset(mark)
        if a := self.kwargs():
            return (
                [e for e in a if isinstance(e, ast.Starred)],
                [e for e in a if not isinstance(e, ast.Starred)],
            )
        self._reset(mark)
        return None

    @memoize
    def args_arg(self) -> ast.expr | Any | None:
        # args_arg: starred_expression | (assignment_expression | expression !':=') !'='
        mark = self._mark()
        if starred_expression := self.starred_expression():
            return starred_expression
        self._reset(mark)
        if (_tmp_39 := self._tmp_39()) and (self.negative_lookahead(self.expect, "=")):
            return _tmp_39
        self._reset(mark)
        return None

    @memoize
    def kwargs(self) -> list[Any] | None:
        # kwargs: ','.kwarg_or_starred+ ',' ','.kwarg_or_double_starred+ | ','.kwarg_or_starred+ | ','.kwarg_or_double_starred+
        mark = self._mark()
        if (
            (a := self.gathered(self.kwarg_or_starred, self.expect, ","))
            and (self.expect(","))
            and (b := self.gathered(self.kwarg_or_double_starred, self.expect, ","))
        ):
            return a + b
        self._reset(mark)
        if gathered := self.gathered(self.kwarg_or_starred, self.expect, ","):
            return gathered
        self._reset(mark)
        if gathered := self.gathered(self.kwarg_or_double_starred, self.expect, ","):
            return gathered
        self._reset(mark)
        return None

    @memoize
    def starred_expression(self) -> ast.Starred | None:
        # starred_expression: invalid_starred_expression | '*' expression
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if self.call_invalid_rules and (self.invalid_starred_expression()):
            return None
        self._reset(mark)
        if (self.expect("*")) and (a := self.expression()):
            return ast.Starred(value=a, ctx=Load, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def kwarg_or_starred(self) -> ast.keyword | ast.Starred | None:
        # kwarg_or_starred: invalid_kwarg | NAME '=' expression | starred_expression
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if self.call_invalid_rules and (self.invalid_kwarg()):
            return None
        self._reset(mark)
        if (a := self.name()) and (self.expect("=")) and (b := self.expression()):
            return ast.keyword(arg=a.string, value=b, **self.span(_lnum, _col))
        self._reset(mark)
        if a1 := self.starred_expression():
            return a1
        self._reset(mark)
        return None

    @memoize
    def kwarg_or_double_starred(self) -> ast.keyword | ast.Starred | None:
        # kwarg_or_double_starred: invalid_kwarg | NAME '=' expression | '**' expression
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if self.call_invalid_rules and (self.invalid_kwarg()):
            return None
        self._reset(mark)
        if (a := self.name()) and (self.expect("=")) and (b := self.expression()):
            return ast.keyword(arg=a.string, value=b, **self.span(_lnum, _col))
        self._reset(mark)
        if (self.expect("**")) and (a1 := self.expression()):
            return ast.keyword(arg=None, value=a1, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def star_targets(self) -> ast.expr | None:
        # star_targets: star_target !',' | star_target star_target_a* ','?
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (a := self.star_target()) and (self.negative_lookahead(self.expect, ",")):
            return a
        self._reset(mark)
        if (a := self.star_target()) and (b := self.repeated(self.star_target_a),) and (self.expect(","),):
            return ast.Tuple(elts=[a] + b, ctx=Store, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def star_targets_list_seq(self) -> list[Any] | None:
        # star_targets_list_seq: ','.star_target+ ','?
        mark = self._mark()
        if (a := self.gathered(self.star_target, self.expect, ",")) and (self.expect(","),):
            return a
        self._reset(mark)
        return None

    @memoize
    def star_targets_tuple_seq(self) -> list[Any] | None:
        # star_targets_tuple_seq: star_target star_target_a+ ','? | star_target ','
        mark = self._mark()
        if (a := self.star_target()) and (b := self.repeated(self.star_target_a)) and (self.expect(","),):
            return [a] + b
        self._reset(mark)
        if (a := self.star_target()) and (self.expect(",")):
            return [a]
        self._reset(mark)
        return None

    @memoize
    def star_target_a(self) -> ast.expr | None:
        # star_target_a: ',' star_target
        mark = self._mark()
        if (self.expect(",")) and (c := self.star_target()):
            return c
        self._reset(mark)
        return None

    @memoize
    def star_target(self) -> ast.expr | None:
        # star_target: '*' (!'*' star_target) | target_with_star_atom
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (self.expect("*")) and (a := self._tmp_43()):
            return ast.Starred(value=self.set_expr_context(a, Store), ctx=Store, **self.span(_lnum, _col))
        self._reset(mark)
        if target_with_star_atom := self.target_with_star_atom():
            return target_with_star_atom
        self._reset(mark)
        return None

    @memoize
    def target_with_star_atom(self) -> ast.expr | None:
        # target_with_star_atom: t_primary '.' NAME !t_lookahead | t_primary '[' slices ']' !t_lookahead | '$' NAME | '${' slices '}' | star_atom
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (
            (a := self.t_primary())
            and (self.expect("."))
            and (b := self.name())
            and (self.negative_lookahead(self.t_lookahead))
        ):
            return ast.Attribute(value=a, attr=b.string, ctx=Store, **self.span(_lnum, _col))
        self._reset(mark)
        if (
            (a := self.t_primary())
            and (self.expect("["))
            and (b := self.slices())
            and (self.expect("]"))
            and (self.negative_lookahead(self.t_lookahead))
        ):
            return ast.Subscript(value=a, slice=b, ctx=Store, **self.span(_lnum, _col))
        self._reset(mark)
        if (self.expect("$")) and (a := self.name()):
            return self.expand_env_name(a, ctx=Store, **self.span(_lnum, _col))
        self._reset(mark)
        if (self.expect("${")) and (a := self.slices()) and (self.expect("}")):
            return self.expand_env_expr(a, ctx=Store, **self.span(_lnum, _col))
        self._reset(mark)
        if star_atom := self.star_atom():
            return star_atom
        self._reset(mark)
        return None

    @memoize
    def star_atom(self) -> ast.expr | None:
        # star_atom: NAME | '(' target_with_star_atom ')' | '(' star_targets_tuple_seq? ')' | '[' star_targets_list_seq? ']'
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if a := self.name():
            return ast.Name(id=a.string, ctx=Store, **self.span(_lnum, _col))
        self._reset(mark)
        if (self.expect("(")) and (a1 := self.target_with_star_atom()) and (self.expect(")")):
            return self.set_expr_context(a1, Store)
        self._reset(mark)
        if (self.expect("(")) and (a2 := self.star_targets_tuple_seq(),) and (self.expect(")")):
            return ast.Tuple(elts=a2 or [], ctx=Store, **self.span(_lnum, _col))
        self._reset(mark)
        if (self.expect("[")) and (a3 := self.star_targets_list_seq(),) and (self.expect("]")):
            return ast.List(elts=a3 or [], ctx=Store, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def single_target(self) -> Any | None:
        # single_target: single_subscript_attribute_target | NAME | '(' single_target ')'
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if single_subscript_attribute_target := self.single_subscript_attribute_target():
            return single_subscript_attribute_target
        self._reset(mark)
        if a := self.name():
            return ast.Name(id=a.string, ctx=Store, **self.span(_lnum, _col))
        self._reset(mark)
        if (self.expect("(")) and (a := self.single_target()) and (self.expect(")")):
            return a
        self._reset(mark)
        return None

    @memoize
    def single_subscript_attribute_target(self) -> Any | None:
        # single_subscript_attribute_target: t_primary '.' NAME !t_lookahead | t_primary '[' slices ']' !t_lookahead
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (
            (a := self.t_primary())
            and (self.expect("."))
            and (b := self.name())
            and (self.negative_lookahead(self.t_lookahead))
        ):
            return ast.Attribute(value=a, attr=b.string, ctx=Store, **self.span(_lnum, _col))
        self._reset(mark)
        if (
            (a := self.t_primary())
            and (self.expect("["))
            and (b := self.slices())
            and (self.expect("]"))
            and (self.negative_lookahead(self.t_lookahead))
        ):
            return ast.Subscript(value=a, slice=b, ctx=Store, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize_left_rec
    def t_primary(self) -> Any | None:
        # t_primary: t_primary '.' NAME &t_lookahead | t_primary '[' slices ']' &t_lookahead | t_primary genexp &t_lookahead | t_primary '(' arguments? ')' &t_lookahead | atom &t_lookahead
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (
            (a := self.t_primary())
            and (self.expect("."))
            and (b := self.name())
            and (self.positive_lookahead(self.t_lookahead))
        ):
            return ast.Attribute(value=a, attr=b.string, ctx=Load, **self.span(_lnum, _col))
        self._reset(mark)
        if (
            (a := self.t_primary())
            and (self.expect("["))
            and (b := self.slices())
            and (self.expect("]"))
            and (self.positive_lookahead(self.t_lookahead))
        ):
            return ast.Subscript(value=a, slice=b, ctx=Load, **self.span(_lnum, _col))
        self._reset(mark)
        if (a := self.t_primary()) and (b := self.genexp()) and (self.positive_lookahead(self.t_lookahead)):
            return ast.Call(func=a, args=[b], keywords=[], **self.span(_lnum, _col))
        self._reset(mark)
        if (
            (a := self.t_primary())
            and (self.expect("("))
            and (b := self.arguments(),)
            and (self.expect(")"))
            and (self.positive_lookahead(self.t_lookahead))
        ):
            return ast.Call(
                func=a, args=b[0] if b else [], keywords=b[1] if b else [], **self.span(_lnum, _col)
            )
        self._reset(mark)
        if (a := self.atom()) and (self.positive_lookahead(self.t_lookahead)):
            return a
        self._reset(mark)
        return None

    @memoize
    def t_lookahead(self) -> Any | None:
        # t_lookahead: '(' | '[' | '.'
        return self.seq_alts(
            (self.expect, "("),
            (self.expect, "["),
            (self.expect, "."),
        )

    @memoize
    def del_targets(self) -> list[ast.expr] | None:
        # del_targets: ','.del_target+ ','?
        mark = self._mark()
        if (a := self.gathered(self.del_target, self.expect, ",")) and (self.expect(","),):
            return a
        self._reset(mark)
        return None

    @memoize
    def del_target(self) -> ast.expr | None:
        # del_target: t_primary '.' NAME !t_lookahead | t_primary '[' slices ']' !t_lookahead | del_t_atom
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (
            (a := self.t_primary())
            and (self.expect("."))
            and (b := self.name())
            and (self.negative_lookahead(self.t_lookahead))
        ):
            return ast.Attribute(value=a, attr=b.string, ctx=Del, **self.span(_lnum, _col))
        self._reset(mark)
        if (
            (a := self.t_primary())
            and (self.expect("["))
            and (b := self.slices())
            and (self.expect("]"))
            and (self.negative_lookahead(self.t_lookahead))
        ):
            return ast.Subscript(value=a, slice=b, ctx=Del, **self.span(_lnum, _col))
        self._reset(mark)
        if del_t_atom := self.del_t_atom():
            return del_t_atom
        self._reset(mark)
        return None

    @memoize
    def del_t_atom(self) -> ast.expr | None:
        # del_t_atom: NAME | '(' del_target ')' | '(' del_targets? ')' | '[' del_targets? ']'
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if a := self.name():
            return ast.Name(id=a.string, ctx=Del, **self.span(_lnum, _col))
        self._reset(mark)
        if (self.expect("(")) and (b := self.del_target()) and (self.expect(")")):
            return self.set_expr_context(b, Del)
        self._reset(mark)
        if (self.expect("(")) and (c := self.del_targets(),) and (self.expect(")")):
            return ast.Tuple(elts=c or [], ctx=Del, **self.span(_lnum, _col))
        self._reset(mark)
        if (self.expect("[")) and (c := self.del_targets(),) and (self.expect("]")):
            return ast.List(elts=c or [], ctx=Del, **self.span(_lnum, _col))
        self._reset(mark)
        return None

    @memoize
    def type_comment_str(self) -> str | None:
        # type_comment_str: TYPE_COMMENT
        mark = self._mark()
        if t := self.token("TYPE_COMMENT"):
            return t.string
        self._reset(mark)
        return None

    @memoize
    def func_type_comment(self) -> str | None:
        # func_type_comment: NEWLINE TYPE_COMMENT &(NEWLINE INDENT) | invalid_double_type_comments | type_comment_str
        mark = self._mark()
        if (
            (self.token("NEWLINE"))
            and (t := self.token("TYPE_COMMENT"))
            and (self.positive_lookahead(self._tmp_44))
        ):
            return t.string
        self._reset(mark)
        if self.call_invalid_rules and (self.invalid_double_type_comments()):
            return None
        self._reset(mark)
        if type_comment_str := self.type_comment_str():
            return type_comment_str
        self._reset(mark)
        return None

    @memoize
    def invalid_arguments(self) -> None:
        # invalid_arguments: args ',' '*' | expression for_if_clauses ',' [args | expression for_if_clauses] | NAME '=' expression for_if_clauses | [(args ',')] NAME '=' &(',' | ')') | args for_if_clauses | args ',' expression for_if_clauses | args ',' args
        mark = self._mark()
        if (a := self.args()) and (self.expect(",")) and (self.expect("*")):
            self.raise_syntax_error_known_location(
                "iterable argument unpacking follows keyword argument unpacking",
                a[1][-1] if a[1] else a[0][-1],
            )
        self._reset(mark)
        if (
            (a1 := self.expression())
            and (b := self.for_if_clauses())
            and (self.expect(","))
            and (self._tmp_45(),)
        ):
            self.raise_syntax_error_known_range(
                "Generator expression must be parenthesized", a1, b[-1].ifs[-1] if b[-1].ifs else b[-1].iter
            )
        self._reset(mark)
        if (
            (a2 := self.name())
            and (b2 := self.expect("="))
            and (self.expression())
            and (self.for_if_clauses())
        ):
            self.raise_syntax_error_known_range(
                "invalid syntax. Maybe you meant '==' or ':=' instead of '='?", a2, b2
            )
        self._reset(mark)
        if (
            (self._tmp_46(),)
            and (a3 := self.name())
            and (b3 := self.expect("="))
            and (self.positive_lookahead(self._tmp_47))
        ):
            self.raise_syntax_error_known_range("expected argument value expression", a3, b3)
        self._reset(mark)
        if (a4 := self.args()) and (b4 := self.for_if_clauses()):
            self.raise_syntax_error_known_range(
                "Generator expression must be parenthesized",
                a4[0][-1],
                b4[-1].ifs[-1] if b4[-1].ifs else b4[-1].iter,
            ) if len(a4[0]) > 1 else None
        self._reset(mark)
        if (
            (self.args())
            and (self.expect(","))
            and (a5 := self.expression())
            and (b5 := self.for_if_clauses())
        ):
            self.raise_syntax_error_known_range(
                "Generator expression must be parenthesized",
                a5,
                b5[-1].ifs[-1] if b5[-1].ifs else b5[-1].iter,
            )
        self._reset(mark)
        if (a6 := self.args()) and (self.expect(",")) and (self.args()):
            self.raise_syntax_error(
                "positional argument follows keyword argument unpacking"
                if a6[1][-1].arg is None
                else "positional argument follows keyword argument"
            )
        self._reset(mark)

    @memoize
    def invalid_kwarg(self) -> None:
        # invalid_kwarg: ('True' | 'False' | 'None') '=' | NAME '=' expression for_if_clauses | !(NAME '=') expression '=' | '**' expression '=' expression
        mark = self._mark()
        if (a := self._tmp_48()) and (b := self.expect("=")):
            self.raise_syntax_error_known_range(f"cannot assign to {a.string}", a, b)
        self._reset(mark)
        if (
            (a1 := self.name())
            and (b1 := self.expect("="))
            and (self.expression())
            and (self.for_if_clauses())
        ):
            self.raise_syntax_error_known_range(
                "invalid syntax. Maybe you meant '==' or ':=' instead of '='?", a1, b1
            )
        self._reset(mark)
        if (self.negative_lookahead(self._tmp_49)) and (a2 := self.expression()) and (b2 := self.expect("=")):
            self.raise_syntax_error_known_range(
                'expression cannot contain assignment, perhaps you meant "=="?', a2, b2
            )
        self._reset(mark)
        if (
            (a3 := self.expect("**"))
            and (self.expression())
            and (self.expect("="))
            and (b3 := self.expression())
        ):
            self.raise_syntax_error_known_range("cannot assign to keyword argument unpacking", a3, b3)
        self._reset(mark)

    @memoize
    def expression_without_invalid(self) -> Node | Any | None:
        # expression_without_invalid: disjunction 'if' disjunction 'else' expression | disjunction | lambdef
        _prev_call_invalid = self.call_invalid_rules
        self.call_invalid_rules = False
        mark = self._mark()
        _lnum, _col = self._tokenizer.peek().start
        if (
            (a := self.disjunction())
            and (self.expect("if"))
            and (b := self.disjunction())
            and (self.expect("else"))
            and (c := self.expression())
        ):
            self.call_invalid_rules = _prev_call_invalid
            return ast.IfExp(body=b, test=a, orelse=c, **self.span(_lnum, _col))
        self._reset(mark)
        if disjunction := self.disjunction():
            self.call_invalid_rules = _prev_call_invalid
            return disjunction
        self._reset(mark)
        if lambdef := self.lambdef():
            self.call_invalid_rules = _prev_call_invalid
            return lambdef
        self._reset(mark)
        self.call_invalid_rules = _prev_call_invalid
        return None

    @memoize
    def invalid_legacy_expression(self) -> Any | None:
        # invalid_legacy_expression: NAME !'(' star_expressions
        mark = self._mark()
        if (
            (a := self.name())
            and (self.negative_lookahead(self.expect, "("))
            and (b := self.star_expressions())
        ):
            self.raise_syntax_error_known_range(
                f"Missing parentheses in call to '{a.string}' . Did you mean {a.string}(...)?", a, b
            ) if a.string in ("exec", "print") else None
        self._reset(mark)
        return None

    @memoize
    def invalid_expression(self) -> None:
        # invalid_expression: !(NAME STRING | SOFT_KEYWORD) disjunction expression_without_invalid | disjunction 'if' disjunction !('else' | ':') | 'lambda' lambda_params? ':' &(FSTRING_MIDDLE | fstring_replacement_field)
        mark = self._mark()
        if (
            (self.negative_lookahead(self._tmp_50))
            and (a := self.disjunction())
            and (b := self.expression_without_invalid())
        ):
            self.raise_syntax_error_known_range(
                "invalid syntax. Perhaps you forgot a comma?", a, b
            ) if not isinstance(a, ast.Name) or a.id not in ("print", "exec") else None
        self._reset(mark)
        if (
            (a1 := self.disjunction())
            and (self.expect("if"))
            and (b1 := self.disjunction())
            and (self.negative_lookahead(self._tmp_51))
        ):
            self.raise_syntax_error_known_range("expected 'else' after 'if' expression", a1, b1)
        self._reset(mark)
        if (
            (a2 := self.expect("lambda"))
            and (self.lambda_params(),)
            and (b2 := self.expect(":"))
            and (self.positive_lookahead(self._tmp_52))
        ):
            self.raise_syntax_error_known_range(
                "f-string: lambda expressions are not allowed without parentheses", a2, b2
            )
        self._reset(mark)

    @memoize
    def invalid_named_expression(self) -> None:
        # invalid_named_expression: expression ':=' expression | NAME '=' bitwise_or !('=' | ':=') | !(plist | ptuple | genexp | 'True' | 'None' | 'False') bitwise_or '=' bitwise_or !('=' | ':=')
        mark = self._mark()
        if (a := self.expression()) and (self.expect(":=")) and (self.expression()):
            self.raise_syntax_error_known_location(
                f"cannot use assignment expressions with {self.get_expr_name(a)}", a
            )
        self._reset(mark)
        if (
            (a1 := self.name())
            and (self.expect("="))
            and (b1 := self.bitwise_or())
            and (self.negative_lookahead(self._tmp_53))
        ):
            return (
                None
                if self.in_recursive_rule
                else self.raise_syntax_error_known_range(
                    "invalid syntax. Maybe you meant '==' or ':=' instead of '='?", a1, b1
                )
            )
        self._reset(mark)
        if (
            (self.negative_lookahead(self._tmp_54))
            and (a2 := self.bitwise_or())
            and (self.expect("="))
            and (self.bitwise_or())
            and (self.negative_lookahead(self._tmp_53))
        ):
            return (
                None
                if self.in_recursive_rule
                else self.raise_syntax_error_known_location(
                    f"cannot assign to {self.get_expr_name(a)} here. Maybe you meant '==' instead of '='?", a2
                )
            )
        self._reset(mark)
        return None

    @memoize
    def invalid_assignment(self) -> None:
        # invalid_assignment: invalid_ann_assign_target ':' expression | star_named_expression ',' star_named_expressions* ':' expression | expression ':' expression | ((star_targets '='))* star_expressions '=' | ((star_targets '='))* yield_expr '=' | star_expressions augassign annotated_rhs
        mark = self._mark()
        if (
            self.call_invalid_rules
            and (a := self.invalid_ann_assign_target())
            and (self.expect(":"))
            and (self.expression())
        ):
            self.raise_syntax_error_known_location(
                f"only single target (not {self.get_expr_name(a)}) can be annotated", a
            )
        self._reset(mark)
        if (
            (a := self.star_named_expression())
            and (self.expect(","))
            and (self.repeated(self.star_named_expressions),)
            and (self.expect(":"))
            and (self.expression())
        ):
            self.raise_syntax_error_known_location("only single target (not tuple) can be annotated", a)
        self._reset(mark)
        if (a := self.expression()) and (self.expect(":")) and (self.expression()):
            self.raise_syntax_error_known_location("illegal target for annotation", a)
        self._reset(mark)
        if (self.repeated(self._tmp_56),) and (a := self.star_expressions()) and (self.expect("=")):
            self.raise_syntax_error_invalid_target(Target.STAR_TARGETS, a)
        self._reset(mark)
        if (self.repeated(self._tmp_56),) and (a := self.yield_expr()) and (self.expect("=")):
            self.raise_syntax_error_known_location("assignment to yield expression not possible", a)
        self._reset(mark)
        if (a := self.star_expressions()) and (self.augassign()) and (self.annotated_rhs()):
            self.raise_syntax_error_known_location(
                f"'{self.get_expr_name(a)}' is an illegal expression for augmented assignment", a
            )
        self._reset(mark)

    @memoize
    def invalid_ann_assign_target(self) -> Node | None:
        # invalid_ann_assign_target: plist | ptuple | '(' invalid_ann_assign_target ')'
        mark = self._mark()
        if a := self.plist():
            return a
        self._reset(mark)
        if a1 := self.ptuple():
            return a1
        self._reset(mark)
        if (
            self.call_invalid_rules
            and (self.expect("("))
            and (a2 := self.invalid_ann_assign_target())
            and (self.expect(")"))
        ):
            return a2
        self._reset(mark)
        return None

    @memoize
    def invalid_del_stmt(self) -> None:
        # invalid_del_stmt: 'del' star_expressions
        mark = self._mark()
        if (self.expect("del")) and (a := self.star_expressions()):
            self.raise_syntax_error_invalid_target(Target.DEL_TARGETS, a)
        self._reset(mark)

    @memoize
    def invalid_block(self) -> None:
        # invalid_block: NEWLINE !INDENT
        mark = self._mark()
        if (self.token("NEWLINE")) and (self.negative_lookahead(self.token, "INDENT")):
            self.raise_indentation_error("expected an indented block")
        self._reset(mark)

    @memoize
    def invalid_comprehension(self) -> None:
        # invalid_comprehension: ('[' | '(' | '{') starred_expression for_if_clauses | ('[' | '{') star_named_expression ',' star_named_expressions for_if_clauses | ('[' | '{') star_named_expression ',' for_if_clauses
        mark = self._mark()
        if (self._tmp_58()) and (a1 := self.starred_expression()) and (self.for_if_clauses()):
            self.raise_syntax_error_known_location("iterable unpacking cannot be used in comprehension", a1)
        self._reset(mark)
        if (
            (self._tmp_59())
            and (a := self.star_named_expression())
            and (self.expect(","))
            and (b := self.star_named_expressions())
            and (self.for_if_clauses())
        ):
            self.raise_syntax_error_known_range(
                "did you forget parentheses around the comprehension target?", a, b[-1]
            )
        self._reset(mark)
        if (
            (self._tmp_59())
            and (a := self.star_named_expression())
            and (b := self.expect(","))
            and (self.for_if_clauses())
        ):
            self.raise_syntax_error_known_range(
                "did you forget parentheses around the comprehension target?", a, b
            )
        self._reset(mark)

    @memoize
    def invalid_dict_comprehension(self) -> None:
        # invalid_dict_comprehension: '{' '**' bitwise_or for_if_clauses '}'
        mark = self._mark()
        if (
            (self.expect("{"))
            and (a := self.expect("**"))
            and (self.bitwise_or())
            and (self.for_if_clauses())
            and (self.expect("}"))
        ):
            self.raise_syntax_error_known_location("dict unpacking cannot be used in dict comprehension", a)
        self._reset(mark)

    @memoize
    def invalid_parameters(self) -> None:
        # invalid_parameters: "/" ',' | (slash_no_default | slash_with_default) param_maybe_default* '/' | slash_no_default? param_no_default* invalid_parameters_helper param_no_default | param_no_default* '(' param_no_default+ ','? ')' | [(slash_no_default | slash_with_default)] param_maybe_default* '*' (',' | param_no_default) param_maybe_default* '/' | param_maybe_default+ '/' '*'
        mark = self._mark()
        if (a := self.expect("/")) and (self.expect(",")):
            self.raise_syntax_error_known_location("at least one argument must precede /", a)
        self._reset(mark)
        if (self._tmp_61()) and (self.repeated(self.param_maybe_default),) and (a1 := self.expect("/")):
            self.raise_syntax_error_known_location("/ may appear only once", a1)
        self._reset(mark)
        if (
            self.call_invalid_rules
            and (self.slash_no_default(),)
            and (self.repeated(self.param_no_default),)
            and (self.invalid_parameters_helper())
            and (a2 := self.param_no_default())
        ):
            self.raise_syntax_error_known_location(
                "parameter without a default follows parameter with a default", a2
            )
        self._reset(mark)
        if (
            (self.repeated(self.param_no_default),)
            and (a3 := self.expect("("))
            and (self.repeated(self.param_no_default))
            and (self.expect(","),)
            and (b := self.expect(")"))
        ):
            self.raise_syntax_error_known_range("Function parameters cannot be parenthesized", a3, b)
        self._reset(mark)
        if (
            (self._tmp_61(),)
            and (self.repeated(self.param_maybe_default),)
            and (self.expect("*"))
            and (self._tmp_63())
            and (self.repeated(self.param_maybe_default),)
            and (a4 := self.expect("/"))
        ):
            self.raise_syntax_error_known_location("/ must be ahead of *", a4)
        self._reset(mark)
        if (self.repeated(self.param_maybe_default)) and (self.expect("/")) and (a5 := self.expect("*")):
            self.raise_syntax_error_known_location("expected comma between / and *", a5)
        self._reset(mark)

    @memoize
    def invalid_default(self) -> Any | None:
        # invalid_default: '=' &(')' | ',')
        mark = self._mark()
        if (a := self.expect("=")) and (self.positive_lookahead(self._tmp_64)):
            self.raise_syntax_error_known_location("expected default value expression", a)
        self._reset(mark)
        return None

    @memoize
    def invalid_star_etc(self) -> Any | None:
        # invalid_star_etc: '*' (')' | ',' (')' | '**')) | '*' ',' TYPE_COMMENT | '*' param '=' | '*' (param_no_default | ',') param_maybe_default* '*' (param_no_default | ',')
        mark = self._mark()
        if (a := self.expect("*")) and (self._tmp_65()):
            self.raise_syntax_error_known_location("named arguments must follow bare *", a)
        self._reset(mark)
        if (self.expect("*")) and (self.expect(",")) and (self.token("TYPE_COMMENT")):
            self.raise_syntax_error("bare * has associated type comment")
        self._reset(mark)
        if (self.expect("*")) and (self.param()) and (a := self.expect("=")):
            self.raise_syntax_error_known_location("var-positional argument cannot have default value", a)
        self._reset(mark)
        if (
            (self.expect("*"))
            and (self._tmp_66())
            and (self.repeated(self.param_maybe_default),)
            and (a := self.expect("*"))
            and (self._tmp_66())
        ):
            self.raise_syntax_error_known_location("* argument may appear only once", a)
        self._reset(mark)
        return None

    @memoize
    def invalid_kwds(self) -> Any | None:
        # invalid_kwds: '**' param '=' | '**' param ',' param | '**' param ',' ('*' | '**' | '/')
        mark = self._mark()
        if (self.expect("**")) and (self.param()) and (a := self.expect("=")):
            self.raise_syntax_error_known_location("var-keyword argument cannot have default value", a)
        self._reset(mark)
        if (self.expect("**")) and (self.param()) and (self.expect(",")) and (a1 := self.param()):
            self.raise_syntax_error_known_location("arguments cannot follow var-keyword argument", a1)
        self._reset(mark)
        if (self.expect("**")) and (self.param()) and (self.expect(",")) and (a := self._tmp_68()):
            self.raise_syntax_error_known_location("arguments cannot follow var-keyword argument", a)
        self._reset(mark)
        return None

    @memoize
    def invalid_parameters_helper(self) -> Any | None:
        # invalid_parameters_helper: slash_with_default | param_with_default+
        mark = self._mark()
        if a := self.slash_with_default():
            return [a]
        self._reset(mark)
        if a := self.repeated(self.param_with_default):
            return a
        self._reset(mark)
        return None

    @memoize
    def invalid_lambda_parameters(self) -> None:
        # invalid_lambda_parameters: "/" ',' | (lambda_slash_no_default | lambda_slash_with_default) lambda_param_maybe_default* '/' | lambda_slash_no_default? lambda_param_no_default* invalid_lambda_parameters_helper lambda_param_no_default | lambda_param_no_default* '(' ','.lambda_param+ ','? ')' | [(lambda_slash_no_default | lambda_slash_with_default)] lambda_param_maybe_default* '*' (',' | lambda_param_no_default) lambda_param_maybe_default* '/' | lambda_param_maybe_default+ '/' '*'
        mark = self._mark()
        if (a := self.expect("/")) and (self.expect(",")):
            self.raise_syntax_error_known_location("at least one argument must precede /", a)
        self._reset(mark)
        if (
            (self._tmp_69())
            and (self.repeated(self.lambda_param_maybe_default),)
            and (a1 := self.expect("/"))
        ):
            self.raise_syntax_error_known_location("/ may appear only once", a1)
        self._reset(mark)
        if (
            self.call_invalid_rules
            and (self.lambda_slash_no_default(),)
            and (self.repeated(self.lambda_param_no_default),)
            and (self.invalid_lambda_parameters_helper())
            and (a2 := self.lambda_param_no_default())
        ):
            self.raise_syntax_error_known_location(
                "parameter without a default follows parameter with a default", a2
            )
        self._reset(mark)
        if (
            (self.repeated(self.lambda_param_no_default),)
            and (a3 := self.expect("("))
            and (self.gathered(self.lambda_param, self.expect, ","))
            and (self.expect(","),)
            and (b := self.expect(")"))
        ):
            self.raise_syntax_error_known_range("Lambda expression parameters cannot be parenthesized", a3, b)
        self._reset(mark)
        if (
            (self._tmp_69(),)
            and (self.repeated(self.lambda_param_maybe_default),)
            and (self.expect("*"))
            and (self._tmp_71())
            and (self.repeated(self.lambda_param_maybe_default),)
            and (a4 := self.expect("/"))
        ):
            self.raise_syntax_error_known_location("/ must be ahead of *", a4)
        self._reset(mark)
        if (
            (self.repeated(self.lambda_param_maybe_default))
            and (self.expect("/"))
            and (a5 := self.expect("*"))
        ):
            self.raise_syntax_error_known_location("expected comma between / and *", a5)
        self._reset(mark)

    @memoize
    def invalid_lambda_parameters_helper(self) -> Any | None:
        # invalid_lambda_parameters_helper: lambda_slash_with_default | lambda_param_with_default+
        mark = self._mark()
        if a := self.lambda_slash_with_default():
            return [a]
        self._reset(mark)
        if a := self.repeated(self.lambda_param_with_default):
            return a
        self._reset(mark)
        return None

    @memoize
    def invalid_lambda_star_etc(self) -> None:
        # invalid_lambda_star_etc: '*' (':' | ',' (':' | '**')) | '*' lambda_param '=' | '*' (lambda_param_no_default | ',') lambda_param_maybe_default* '*' (lambda_param_no_default | ',')
        mark = self._mark()
        if (self.expect("*")) and (self._tmp_72()):
            self.raise_syntax_error("named arguments must follow bare *")
        self._reset(mark)
        if (self.expect("*")) and (self.lambda_param()) and (a := self.expect("=")):
            self.raise_syntax_error_known_location("var-positional argument cannot have default value", a)
        self._reset(mark)
        if (
            (self.expect("*"))
            and (self._tmp_73())
            and (self.repeated(self.lambda_param_maybe_default),)
            and (a := self.expect("*"))
            and (self._tmp_73())
        ):
            self.raise_syntax_error_known_location("* argument may appear only once", a)
        self._reset(mark)

    @memoize
    def invalid_lambda_kwds(self) -> Any | None:
        # invalid_lambda_kwds: '**' lambda_param '=' | '**' lambda_param ',' lambda_param | '**' lambda_param ',' ('*' | '**' | '/')
        mark = self._mark()
        if (self.expect("**")) and (self.lambda_param()) and (a := self.expect("=")):
            self.raise_syntax_error_known_location("var-keyword argument cannot have default value", a)
        self._reset(mark)
        if (
            (self.expect("**"))
            and (self.lambda_param())
            and (self.expect(","))
            and (a1 := self.lambda_param())
        ):
            self.raise_syntax_error_known_location("arguments cannot follow var-keyword argument", a1)
        self._reset(mark)
        if (self.expect("**")) and (self.lambda_param()) and (self.expect(",")) and (a2 := self._tmp_68()):
            self.raise_syntax_error_known_location("arguments cannot follow var-keyword argument", a2)
        self._reset(mark)
        return None

    @memoize
    def invalid_double_type_comments(self) -> None:
        # invalid_double_type_comments: TYPE_COMMENT NEWLINE TYPE_COMMENT NEWLINE INDENT
        mark = self._mark()
        if (
            (self.token("TYPE_COMMENT"))
            and (self.token("NEWLINE"))
            and (self.token("TYPE_COMMENT"))
            and (self.token("NEWLINE"))
            and (self.token("INDENT"))
        ):
            self.raise_syntax_error("Cannot have two type comments on def")
        self._reset(mark)

    @memoize
    def invalid_with_item(self) -> None:
        # invalid_with_item: expression 'as' expression &(',' | ')' | ':')
        mark = self._mark()
        if (
            (self.expression())
            and (self.expect("as"))
            and (a := self.expression())
            and (self.positive_lookahead(self._tmp_15))
        ):
            self.raise_syntax_error_invalid_target(Target.STAR_TARGETS, a)
        self._reset(mark)

    @memoize
    def invalid_for_target(self) -> None:
        # invalid_for_target: 'async'? 'for' star_expressions
        mark = self._mark()
        if (self.expect("async"),) and (self.expect("for")) and (a := self.star_expressions()):
            self.raise_syntax_error_invalid_target(Target.FOR_TARGETS, a)
        self._reset(mark)

    @memoize
    def invalid_group(self) -> None:
        # invalid_group: '(' starred_expression ')' | '(' '**' expression ')'
        mark = self._mark()
        if (self.expect("(")) and (a := self.starred_expression()) and (self.expect(")")):
            self.raise_syntax_error_known_location("cannot use starred expression here", a)
        self._reset(mark)
        if (self.expect("(")) and (b := self.expect("**")) and (self.expression()) and (self.expect(")")):
            self.raise_syntax_error_known_location("cannot use double starred expression here", b)
        self._reset(mark)

    @memoize
    def invalid_import(self) -> Any | None:
        # invalid_import: 'import' ','.dotted_name+ 'from' dotted_name
        mark = self._mark()
        if (
            (a := self.expect("import"))
            and (self.gathered(self.dotted_name, self.expect, ","))
            and (self.expect("from"))
            and (self.dotted_name())
        ):
            self.raise_syntax_error_starting_from("Did you mean to use 'from ... import ...' instead?", a)
        self._reset(mark)
        return None

    @memoize
    def invalid_import_from_targets(self) -> None:
        # invalid_import_from_targets: import_from_as_names ',' NEWLINE
        mark = self._mark()
        if (self.import_from_as_names()) and (self.expect(",")) and (self.token("NEWLINE")):
            self.raise_syntax_error("trailing comma not allowed without surrounding parentheses")
        self._reset(mark)

    @memoize
    def invalid_with_stmt(self) -> None:
        # invalid_with_stmt: 'async'? 'with' ','.(expression ['as' star_target])+ &&':' | 'async'? 'with' '(' ','.(expressions ['as' star_target])+ ','? ')' &&':'
        mark = self._mark()
        if (
            (self.expect("async"),)
            and (self.expect("with"))
            and (self.gathered(self._tmp_77, self.expect, ","))
            and (self.expect_forced(self.expect(":"), "':'"))
        ):
            return None
        self._reset(mark)
        if (
            (self.expect("async"),)
            and (self.expect("with"))
            and (self.expect("("))
            and (self.gathered(self._tmp_78, self.expect, ","))
            and (self.expect(","),)
            and (self.expect(")"))
            and (self.expect_forced(self.expect(":"), "':'"))
        ):
            return None
        self._reset(mark)
        return None

    @memoize
    def invalid_with_stmt_indent(self) -> None:
        # invalid_with_stmt_indent: 'async'? 'with' ','.(expression ['as' star_target])+ ':' NEWLINE !INDENT | 'async'? 'with' '(' ','.(expressions ['as' star_target])+ ','? ')' ':' NEWLINE !INDENT
        mark = self._mark()
        if (
            (self.expect("async"),)
            and (a := self.expect("with"))
            and (self.gathered(self._tmp_77, self.expect, ","))
            and (self.expect(":"))
            and (self.token("NEWLINE"))
            and (self.negative_lookahead(self.token, "INDENT"))
        ):
            self.raise_indentation_error(
                f"expected an indented block after 'with' statement on line {a.start[0]}"
            )
        self._reset(mark)
        if (
            (self.expect("async"),)
            and (a := self.expect("with"))
            and (self.expect("("))
            and (self.gathered(self._tmp_78, self.expect, ","))
            and (self.expect(","),)
            and (self.expect(")"))
            and (self.expect(":"))
            and (self.token("NEWLINE"))
            and (self.negative_lookahead(self.token, "INDENT"))
        ):
            self.raise_indentation_error(
                f"expected an indented block after 'with' statement on line {a.start[0]}"
            )
        self._reset(mark)

    @memoize
    def invalid_try_stmt(self) -> None:
        # invalid_try_stmt: 'try' ':' NEWLINE !INDENT | 'try' ':' block !('except' | 'finally') | 'try' ':' block* except_block+ 'except' '*' expression ['as' NAME] ':' | 'try' ':' block* except_star_block+ 'except' [expression ['as' NAME]] ':'
        mark = self._mark()
        if (
            (a := self.expect("try"))
            and (self.expect(":"))
            and (self.token("NEWLINE"))
            and (self.negative_lookahead(self.token, "INDENT"))
        ):
            self.raise_indentation_error(
                f"expected an indented block after 'try' statement on line {a.start[0]}"
            )
        self._reset(mark)
        if (
            (self.expect("try"))
            and (self.expect(":"))
            and (self.block())
            and (self.negative_lookahead(self._tmp_81))
        ):
            self.raise_syntax_error("expected 'except' or 'finally' block")
        self._reset(mark)
        if (
            (self.expect("try"))
            and (self.expect(":"))
            and (self.repeated(self.block),)
            and (self.repeated(self.except_block))
            and (a := self.expect("except"))
            and (b := self.expect("*"))
            and (self.expression())
            and (self._tmp_82(),)
            and (self.expect(":"))
        ):
            self.raise_syntax_error_known_range(
                "cannot have both 'except' and 'except*' on the same 'try'", a, b
            )
        self._reset(mark)
        if (
            (self.expect("try"))
            and (self.expect(":"))
            and (self.repeated(self.block),)
            and (self.repeated(self.except_star_block))
            and (a := self.expect("except"))
            and (self._tmp_83(),)
            and (self.expect(":"))
        ):
            self.raise_syntax_error_known_location(
                "cannot have both 'except' and 'except*' on the same 'try'", a
            )
        self._reset(mark)

    @memoize
    def invalid_except_stmt(self) -> None:
        # invalid_except_stmt: 'except' '*'? expression ',' expressions ['as' NAME] ':' | 'except' '*'? expression ['as' NAME] NEWLINE | 'except' '*'? NEWLINE | 'except' '*' (NEWLINE | ':')
        mark = self._mark()
        if (
            (self.expect("except"))
            and (self.expect("*"),)
            and (a := self.expression())
            and (self.expect(","))
            and (self.expressions())
            and (self._tmp_82(),)
            and (self.expect(":"))
        ):
            self.raise_syntax_error_starting_from("multiple exception types must be parenthesized", a)
        self._reset(mark)
        if (
            (self.expect("except"))
            and (self.expect("*"),)
            and (self.expression())
            and (self._tmp_82(),)
            and (self.token("NEWLINE"))
        ):
            self.raise_syntax_error("expected ':'")
        self._reset(mark)
        if (self.expect("except")) and (self.expect("*"),) and (self.token("NEWLINE")):
            self.raise_syntax_error("expected ':'")
        self._reset(mark)
        if (self.expect("except")) and (self.expect("*")) and (self._tmp_86()):
            self.raise_syntax_error("expected one or more exception types")
        self._reset(mark)

    @memoize
    def invalid_finally_stmt(self) -> None:
        # invalid_finally_stmt: 'finally' ':' NEWLINE !INDENT
        mark = self._mark()
        if (
            (a := self.expect("finally"))
            and (self.expect(":"))
            and (self.token("NEWLINE"))
            and (self.negative_lookahead(self.token, "INDENT"))
        ):
            self.raise_indentation_error(
                f"expected an indented block after 'finally' statement on line {a.start[0]}"
            )
        self._reset(mark)

    @memoize
    def invalid_except_stmt_indent(self) -> None:
        # invalid_except_stmt_indent: 'except' expression ['as' NAME] ':' NEWLINE !INDENT | 'except' ':' NEWLINE !INDENT
        mark = self._mark()
        if (
            (a := self.expect("except"))
            and (self.expression())
            and (self._tmp_82(),)
            and (self.expect(":"))
            and (self.token("NEWLINE"))
            and (self.negative_lookahead(self.token, "INDENT"))
        ):
            self.raise_indentation_error(
                f"expected an indented block after 'except' statement on line {a.start[0]}"
            )
        self._reset(mark)
        if (
            (a := self.expect("except"))
            and (self.expect(":"))
            and (self.token("NEWLINE"))
            and (self.negative_lookahead(self.token, "INDENT"))
        ):
            self.raise_indentation_error(
                f"expected an indented block after 'except' statement on line {a.start[0]}"
            )
        self._reset(mark)

    @memoize
    def invalid_except_star_stmt_indent(self) -> None:
        # invalid_except_star_stmt_indent: 'except' '*' expression ['as' NAME] ':' NEWLINE !INDENT
        mark = self._mark()
        if (
            (a := self.expect("except"))
            and (self.expect("*"))
            and (self.expression())
            and (self._tmp_82(),)
            and (self.expect(":"))
            and (self.token("NEWLINE"))
            and (self.negative_lookahead(self.token, "INDENT"))
        ):
            self.raise_indentation_error(
                f"expected an indented block after 'except*' statement on line {a.start[0]}"
            )
        self._reset(mark)

    @memoize
    def invalid_match_stmt(self) -> None:
        # invalid_match_stmt: "match" subject_expr !':' | "match" subject_expr ':' NEWLINE !INDENT
        mark = self._mark()
        if (self.expect("match")) and (self.subject_expr()) and (self.negative_lookahead(self.expect, ":")):
            self.raise_syntax_error("expected ':'")
        self._reset(mark)
        if (
            (a := self.expect("match"))
            and (self.subject_expr())
            and (self.expect(":"))
            and (self.token("NEWLINE"))
            and (self.negative_lookahead(self.token, "INDENT"))
        ):
            self.raise_indentation_error(
                f"expected an indented block after 'match' statement on line {a.start[0]}"
            )
        self._reset(mark)

    @memoize
    def invalid_case_block(self) -> None:
        # invalid_case_block: "case" patterns guard? !':' | "case" patterns guard? ':' NEWLINE !INDENT
        mark = self._mark()
        if (
            (self.expect("case"))
            and (self.patterns())
            and (self.guard(),)
            and (self.negative_lookahead(self.expect, ":"))
        ):
            self.raise_syntax_error("expected ':'")
        self._reset(mark)
        if (
            (a := self.expect("case"))
            and (self.patterns())
            and (self.guard(),)
            and (self.expect(":"))
            and (self.token("NEWLINE"))
            and (self.negative_lookahead(self.token, "INDENT"))
        ):
            self.raise_indentation_error(
                f"expected an indented block after 'case' statement on line {a.start[0]}"
            )
        self._reset(mark)

    @memoize
    def invalid_as_pattern(self) -> None:
        # invalid_as_pattern: or_pattern 'as' "_" | or_pattern 'as' !NAME expression
        mark = self._mark()
        if (self.or_pattern()) and (self.expect("as")) and (a := self.expect("_")):
            self.raise_syntax_error_known_location("cannot use '_' as a target", a)
        self._reset(mark)
        if (
            (self.or_pattern())
            and (self.expect("as"))
            and (self.negative_lookahead(self.name))
            and (a1 := self.expression())
        ):
            self.raise_syntax_error_known_location("invalid pattern target", a1)
        self._reset(mark)

    @memoize
    def invalid_class_pattern(self) -> None:
        # invalid_class_pattern: name_or_attr '(' invalid_class_argument_pattern
        mark = self._mark()
        if (
            self.call_invalid_rules
            and (self.name_or_attr())
            and (self.expect("("))
            and (a := self.invalid_class_argument_pattern())
        ):
            self.raise_syntax_error_known_range("positional patterns follow keyword patterns", a[0], a[-1])
        self._reset(mark)

    @memoize
    def invalid_class_argument_pattern(self) -> Any | None:
        # invalid_class_argument_pattern: [positional_patterns ','] keyword_patterns ',' positional_patterns
        mark = self._mark()
        if (
            (self._tmp_89(),)
            and (self.keyword_patterns())
            and (self.expect(","))
            and (a := self.positional_patterns())
        ):
            return a
        self._reset(mark)
        return None

    @memoize
    def invalid_if_stmt(self) -> None:
        # invalid_if_stmt: 'if' named_expression NEWLINE | 'if' named_expression ':' NEWLINE !INDENT
        mark = self._mark()
        if (self.expect("if")) and (self.named_expression()) and (self.token("NEWLINE")):
            self.raise_syntax_error("expected ':'")
        self._reset(mark)
        if (
            (a := self.expect("if"))
            and (a_1 := self.named_expression())
            and (self.expect(":"))
            and (self.token("NEWLINE"))
            and (self.negative_lookahead(self.token, "INDENT"))
        ):
            self.raise_indentation_error(
                f"expected an indented block after 'if' statement on line {a.start[0]}"
            )
        self._reset(mark)

    @memoize
    def invalid_elif_stmt(self) -> None:
        # invalid_elif_stmt: 'elif' named_expression NEWLINE | 'elif' named_expression ':' NEWLINE !INDENT
        mark = self._mark()
        if (self.expect("elif")) and (self.named_expression()) and (self.token("NEWLINE")):
            self.raise_syntax_error("expected ':'")
        self._reset(mark)
        if (
            (a := self.expect("elif"))
            and (self.named_expression())
            and (self.expect(":"))
            and (self.token("NEWLINE"))
            and (self.negative_lookahead(self.token, "INDENT"))
        ):
            self.raise_indentation_error(
                f"expected an indented block after 'elif' statement on line {a.start[0]}"
            )
        self._reset(mark)

    @memoize
    def invalid_else_stmt(self) -> None:
        # invalid_else_stmt: 'else' ':' NEWLINE !INDENT
        mark = self._mark()
        if (
            (a := self.expect("else"))
            and (self.expect(":"))
            and (self.token("NEWLINE"))
            and (self.negative_lookahead(self.token, "INDENT"))
        ):
            self.raise_indentation_error(
                f"expected an indented block after 'else' statement on line {a.start[0]}"
            )
        self._reset(mark)

    @memoize
    def invalid_while_stmt(self) -> None:
        # invalid_while_stmt: 'while' named_expression NEWLINE | 'while' named_expression ':' NEWLINE !INDENT
        mark = self._mark()
        if (self.expect("while")) and (self.named_expression()) and (self.token("NEWLINE")):
            self.raise_syntax_error("expected ':'")
        self._reset(mark)
        if (
            (a := self.expect("while"))
            and (self.named_expression())
            and (self.expect(":"))
            and (self.token("NEWLINE"))
            and (self.negative_lookahead(self.token, "INDENT"))
        ):
            self.raise_indentation_error(
                f"expected an indented block after 'while' statement on line {a.start[0]}"
            )
        self._reset(mark)

    @memoize
    def invalid_for_stmt(self) -> None:
        # invalid_for_stmt: ASYNC? 'for' star_targets 'in' star_expressions NEWLINE | 'async'? 'for' star_targets 'in' star_expressions ':' NEWLINE !INDENT
        mark = self._mark()
        if (
            (self.token("ASYNC"),)
            and (self.expect("for"))
            and (self.star_targets())
            and (self.expect("in"))
            and (self.star_expressions())
            and (self.token("NEWLINE"))
        ):
            self.raise_syntax_error("expected ':'")
        self._reset(mark)
        if (
            (self.expect("async"),)
            and (a := self.expect("for"))
            and (self.star_targets())
            and (self.expect("in"))
            and (self.star_expressions())
            and (self.expect(":"))
            and (self.token("NEWLINE"))
            and (self.negative_lookahead(self.token, "INDENT"))
        ):
            self.raise_indentation_error(
                f"expected an indented block after 'for' statement on line {a.start[0]}"
            )
        self._reset(mark)

    @memoize
    def invalid_def_raw(self) -> None:
        # invalid_def_raw: 'async'? 'def' NAME type_params? '(' params? ')' return_expr? ':' NEWLINE !INDENT
        mark = self._mark()
        if (
            (self.expect("async"),)
            and (a := self.expect("def"))
            and (self.name())
            and (self.type_params(),)
            and (self.expect("("))
            and (self.params(),)
            and (self.expect(")"))
            and (self.return_expr(),)
            and (self.expect(":"))
            and (self.token("NEWLINE"))
            and (self.negative_lookahead(self.token, "INDENT"))
        ):
            self.raise_indentation_error(
                f"expected an indented block after function definition on line {a.start[0]}"
            )
        self._reset(mark)

    @memoize
    def invalid_class_def_raw(self) -> None:
        # invalid_class_def_raw: 'class' NAME type_params? ['(' arguments? ')'] NEWLINE | 'class' NAME type_params? ['(' arguments? ')'] ':' NEWLINE !INDENT
        mark = self._mark()
        if (
            (self.expect("class"))
            and (self.name())
            and (self.type_params(),)
            and (self._tmp_90(),)
            and (self.token("NEWLINE"))
        ):
            self.raise_syntax_error("expected ':'")
        self._reset(mark)
        if (
            (a := self.expect("class"))
            and (self.name())
            and (self.type_params(),)
            and (self._tmp_90(),)
            and (self.expect(":"))
            and (self.token("NEWLINE"))
            and (self.negative_lookahead(self.token, "INDENT"))
        ):
            self.raise_indentation_error(
                f"expected an indented block after class definition on line {a.start[0]}"
            )
        self._reset(mark)

    @memoize
    def invalid_double_starred_kvpairs(self) -> None:
        # invalid_double_starred_kvpairs: ','.double_starred_kvpair+ ',' invalid_kvpair | expression ':' '*' bitwise_or | expression ':' &('}' | ',')
        mark = self._mark()
        if (
            self.call_invalid_rules
            and (self.gathered(self.double_starred_kvpair, self.expect, ","))
            and (self.expect(","))
            and (self.invalid_kvpair())
        ):
            return None
        self._reset(mark)
        if (self.expression()) and (self.expect(":")) and (a := self.expect("*")) and (self.bitwise_or()):
            self.raise_syntax_error_starting_from("cannot use a starred expression in a dictionary value", a)
        self._reset(mark)
        if (self.expression()) and (a := self.expect(":")) and (self.positive_lookahead(self._tmp_92)):
            self.raise_syntax_error_known_location("expression expected after dictionary key and ':'", a)
        self._reset(mark)
        return None

    @memoize
    def invalid_kvpair(self) -> None:
        # invalid_kvpair: expression !(':') | expression ':' '*' bitwise_or | expression ':' &('}' | ',') | expression ':'
        mark = self._mark()
        if (a := self.expression()) and (self.negative_lookahead(self.expect, ":")):
            self.raise_raw_syntax_error(
                "':' expected after dictionary key",
                (a.lineno, a.col_offset),
                (a.end_lineno, a.end_col_offset),
            )
        self._reset(mark)
        if (self.expression()) and (self.expect(":")) and (a1 := self.expect("*")) and (self.bitwise_or()):
            self.raise_syntax_error_starting_from("cannot use a starred expression in a dictionary value", a1)
        self._reset(mark)
        if (self.expression()) and (a2 := self.expect(":")) and (self.positive_lookahead(self._tmp_92)):
            self.raise_syntax_error_known_location("expression expected after dictionary key and ':'", a2)
        self._reset(mark)
        if (self.expression()) and (a3 := self.expect(":")):
            self.raise_syntax_error_known_location("expression expected after dictionary key and ':'", a3)
        self._reset(mark)

    @memoize
    def invalid_starred_expression(self) -> Any | None:
        # invalid_starred_expression: '*' expression '=' expression
        mark = self._mark()
        if (
            (a := self.expect("*"))
            and (self.expression())
            and (self.expect("="))
            and (b := self.expression())
        ):
            self.raise_syntax_error_known_range("cannot assign to iterable argument unpacking", a, b)
        self._reset(mark)
        return None

    @memoize
    def invalid_replacement_field(self) -> None:
        # invalid_replacement_field: '{' '=' | '{' '!' | '{' ':' | '{' '}' | '{' !annotated_rhs | '{' annotated_rhs !('=' | '!' | ':' | '}') | '{' annotated_rhs '=' !('!' | ':' | '}') | '{' annotated_rhs '='? invalid_conversion_character | '{' annotated_rhs '='? ['!' NAME] !(':' | '}') | '{' annotated_rhs '='? ['!' NAME] ':' fstring_format_spec* !'}' | '{' annotated_rhs '='? ['!' NAME] !'}'
        mark = self._mark()
        if (self.expect("{")) and (a := self.expect("=")):
            self.raise_syntax_error_known_location("f-string: valid expression required before '='", a)
        self._reset(mark)
        if (self.expect("{")) and (a := self.expect("!")):
            self.raise_syntax_error_known_location("f-string: valid expression required before '!'", a)
        self._reset(mark)
        if (self.expect("{")) and (a := self.expect(":")):
            self.raise_syntax_error_known_location("f-string: valid expression required before ':'", a)
        self._reset(mark)
        if (self.expect("{")) and (a := self.expect("}")):
            self.raise_syntax_error_known_location("f-string: valid expression required before '}'", a)
        self._reset(mark)
        if (self.expect("{")) and (self.negative_lookahead(self.annotated_rhs)):
            self.raise_syntax_error_on_next_token("f-string: expecting a valid expression after '{'")
        self._reset(mark)
        if (self.expect("{")) and (self.annotated_rhs()) and (self.negative_lookahead(self._tmp_94)):
            self.raise_syntax_error_on_next_token("f-string: expecting '=', or '!', or ':', or '}'")
        self._reset(mark)
        if (
            (self.expect("{"))
            and (self.annotated_rhs())
            and (self.expect("="))
            and (self.negative_lookahead(self._tmp_95))
        ):
            self.raise_syntax_error_on_next_token("f-string: expecting '!', or ':', or '}'")
        self._reset(mark)
        if (
            self.call_invalid_rules
            and (self.expect("{"))
            and (self.annotated_rhs())
            and (self.expect("="),)
            and (self.invalid_conversion_character())
        ):
            return None
        self._reset(mark)
        if (
            (self.expect("{"))
            and (self.annotated_rhs())
            and (self.expect("="),)
            and (self._tmp_96(),)
            and (self.negative_lookahead(self._tmp_97))
        ):
            self.raise_syntax_error_on_next_token("f-string: expecting ':' or '}'")
        self._reset(mark)
        if (
            (self.expect("{"))
            and (self.annotated_rhs())
            and (self.expect("="),)
            and (self._tmp_96(),)
            and (self.expect(":"))
            and (self.repeated(self.fstring_format_spec),)
            and (self.negative_lookahead(self.expect, "}"))
        ):
            self.raise_syntax_error_on_next_token("f-string: expecting '}', or format specs")
        self._reset(mark)
        if (
            (self.expect("{"))
            and (self.annotated_rhs())
            and (self.expect("="),)
            and (self._tmp_96(),)
            and (self.negative_lookahead(self.expect, "}"))
        ):
            self.raise_syntax_error_on_next_token("f-string: expecting '}'")
        self._reset(mark)
        return None

    @memoize
    def invalid_conversion_character(self) -> None:
        # invalid_conversion_character: '!' &(':' | '}') | '!' !NAME
        mark = self._mark()
        if (self.expect("!")) and (self.positive_lookahead(self._tmp_97)):
            self.raise_syntax_error_on_next_token("f-string: missing conversion character")
        self._reset(mark)
        if (self.expect("!")) and (self.negative_lookahead(self.name)):
            self.raise_syntax_error_on_next_token("f-string: invalid conversion character")
        self._reset(mark)

    @memoize
    def _tmp_1(self) -> Any | None:
        # _tmp_1: 'import' | 'from'
        return self.seq_alts(
            (self.expect, "import"),
            (self.expect, "from"),
        )

    @memoize
    def _tmp_2(self) -> Any | None:
        # _tmp_2: 'def' | '@' | 'async'
        return self.seq_alts(
            (self.expect, "def"),
            (self.expect, "@"),
            (self.expect, "async"),
        )

    @memoize
    def _tmp_3(self) -> Any | None:
        # _tmp_3: 'class' | '@'
        return self.seq_alts(
            (self.expect, "class"),
            (self.expect, "@"),
        )

    @memoize
    def _tmp_4(self) -> Any | None:
        # _tmp_4: 'with' | 'async'
        return self.seq_alts(
            (self.expect, "with"),
            (self.expect, "async"),
        )

    @memoize
    def _tmp_5(self) -> Any | None:
        # _tmp_5: 'for' | 'async'
        return self.seq_alts(
            (self.expect, "for"),
            (self.expect, "async"),
        )

    @memoize
    def _tmp_6(self) -> Any | None:
        # _tmp_6: '=' annotated_rhs
        mark = self._mark()
        if (self.expect("=")) and (d := self.annotated_rhs()):
            return d
        self._reset(mark)
        return None

    @memoize
    def _tmp_7(self) -> Any | None:
        # _tmp_7: '(' single_target ')' | single_subscript_attribute_target
        mark = self._mark()
        if (self.expect("(")) and (b := self.single_target()) and (self.expect(")")):
            return b
        self._reset(mark)
        if single_subscript_attribute_target := self.single_subscript_attribute_target():
            return single_subscript_attribute_target
        self._reset(mark)
        return None

    @memoize
    def _tmp_8(self) -> Any | None:
        # _tmp_8: '=' annotated_rhs
        mark = self._mark()
        if (self.expect("=")) and (d1 := self.annotated_rhs()):
            return d1
        self._reset(mark)
        return None

    @memoize
    def _tmp_9(self) -> Any | None:
        # _tmp_9: 'from' expression
        mark = self._mark()
        if (self.expect("from")) and (z := self.expression()):
            return z
        self._reset(mark)
        return None

    @memoize
    def _tmp_10(self) -> Any | None:
        # _tmp_10: ';' | NEWLINE
        return self.seq_alts(
            (self.expect, ";"),
            (self.token, "NEWLINE"),
        )

    @memoize
    def _tmp_11(self) -> Any | None:
        # _tmp_11: ',' expression
        mark = self._mark()
        if (self.expect(",")) and (z := self.expression()):
            return z
        self._reset(mark)
        return None

    @memoize
    def _tmp_12(self) -> Any | None:
        # _tmp_12: 'as' NAME
        mark = self._mark()
        if (self.expect("as")) and (z := self.name()):
            return z.string
        self._reset(mark)
        return None

    @memoize
    def _tmp_14(self) -> Any | None:
        # _tmp_14: '(' arguments? ')'
        mark = self._mark()
        if (self.expect("(")) and (z := self.arguments(),) and (self.expect(")")):
            return z
        self._reset(mark)
        return None

    @memoize
    def _tmp_15(self) -> Any | None:
        # _tmp_15: ',' | ')' | ':'
        return self.seq_alts(
            (self.expect, ","),
            (self.expect, ")"),
            (self.expect, ":"),
        )

    @memoize
    def _tmp_18(self) -> Any | None:
        # _tmp_18: '+' | '-'
        return self.seq_alts(
            (self.expect, "+"),
            (self.expect, "-"),
        )

    @memoize
    def _tmp_20(self) -> Any | None:
        # _tmp_20: '.' | '(' | '='
        return self.seq_alts(
            (self.expect, "."),
            (self.expect, "("),
            (self.expect, "="),
        )

    @memoize
    def _tmp_22(self) -> Any | None:
        # _tmp_22: literal_expr | attr
        return self.seq_alts(
            self.literal_expr,
            self.attr,
        )

    @memoize
    def _tmp_23(self) -> Any | None:
        # _tmp_23: 'or' | '||'
        return self.seq_alts(
            (self.expect, "or"),
            (self.expect, "||"),
        )

    @memoize
    def _tmp_24(self) -> Any | None:
        # _tmp_24: 'and' | '&&'
        return self.seq_alts(
            (self.expect, "and"),
            (self.expect, "&&"),
        )

    @memoize
    def _tmp_25(self) -> Any | None:
        # _tmp_25: '$(' | '$[' | '![' | '!('
        return self.seq_alts(
            (self.expect, "$("),
            (self.expect, "$["),
            (self.expect, "!["),
            (self.expect, "!("),
        )

    @memoize
    def _tmp_26(self) -> Any | None:
        # _tmp_26: '??' | '?'
        return self.seq_alts(
            (self.expect, "??"),
            (self.expect, "?"),
        )

    @memoize
    def _tmp_27(self) -> Any | None:
        # _tmp_27: bare_genexp | expressions
        return self.seq_alts(
            self.bare_genexp,
            self.expressions,
        )

    @memoize
    def _tmp_28(self) -> Any | None:
        # _tmp_28: cmd_group | any_cmd
        return self.seq_alts(
            self.cmd_group,
            self.any_cmd,
        )

    @memoize
    def _tmp_29(self) -> Any | None:
        # _tmp_29: '(' | '!(' | '$('
        return self.seq_alts(
            (self.expect, "("),
            (self.expect, "!("),
            (self.expect, "$("),
        )

    @memoize
    def _tmp_30(self) -> Any | None:
        # _tmp_30: '[' | '![' | '$['
        return self.seq_alts(
            (self.expect, "["),
            (self.expect, "!["),
            (self.expect, "$["),
        )

    @memoize
    def _tmp_31(self) -> Any | None:
        # _tmp_31: slice | starred_expression
        return self.seq_alts(
            self.slice,
            self.starred_expression,
        )

    @memoize
    def _tmp_32(self) -> Any | None:
        # _tmp_32: ':' expression?
        mark = self._mark()
        if (self.expect(":")) and (d := self.expression(),):
            return d
        self._reset(mark)
        return None

    @memoize
    def _tmp_33(self) -> Any | None:
        # _tmp_33: STRING | FSTRING_START
        return self.seq_alts(
            (self.token, "STRING"),
            (self.token, "FSTRING_START"),
        )

    @memoize
    def _tmp_34(self) -> Any | None:
        # _tmp_34: ptuple | group | genexp
        return self.seq_alts(
            self.ptuple,
            self.group,
            self.genexp,
        )

    @memoize
    def _tmp_35(self) -> Any | None:
        # _tmp_35: plist | listcomp
        return self.seq_alts(
            self.plist,
            self.listcomp,
        )

    @memoize
    def _tmp_36(self) -> Any | None:
        # _tmp_36: dict | set | dictcomp | setcomp
        return self.seq_alts(
            self.dict,
            self.set,
            self.dictcomp,
            self.setcomp,
        )

    @memoize
    def _tmp_37(self) -> Any | None:
        # _tmp_37: yield_expr | named_expression
        return self.seq_alts(
            self.yield_expr,
            self.named_expression,
        )

    @memoize
    def _tmp_38(self) -> Any | None:
        # _tmp_38: star_named_expression ',' star_named_expressions?
        mark = self._mark()
        if (
            (y := self.star_named_expression())
            and (self.expect(","))
            and (z := self.star_named_expressions(),)
        ):
            return [y] + (z or [])
        self._reset(mark)
        return None

    @memoize
    def _tmp_39(self) -> Any | None:
        # _tmp_39: assignment_expression | expression !':='
        mark = self._mark()
        if assignment_expression := self.assignment_expression():
            return assignment_expression
        self._reset(mark)
        if (expression := self.expression()) and (self.negative_lookahead(self.expect, ":=")):
            return expression
        self._reset(mark)
        return None

    @memoize
    def _tmp_41(self) -> Any | None:
        # _tmp_41: ',' kwargs
        mark = self._mark()
        if (self.expect(",")) and (k := self.kwargs()):
            return k
        self._reset(mark)
        return None

    @memoize
    def _tmp_43(self) -> Any | None:
        # _tmp_43: !'*' star_target
        mark = self._mark()
        if (self.negative_lookahead(self.expect, "*")) and (star_target := self.star_target()):
            return star_target
        self._reset(mark)
        return None

    @memoize
    def _tmp_44(self) -> Any | None:
        # _tmp_44: NEWLINE INDENT
        mark = self._mark()
        if (_newline := self.token("NEWLINE")) and (_indent := self.token("INDENT")):
            return [_newline, _indent]
        self._reset(mark)
        return None

    @memoize
    def _tmp_45(self) -> Any | None:
        # _tmp_45: args | expression for_if_clauses
        mark = self._mark()
        if args := self.args():
            return args
        self._reset(mark)
        if (expression := self.expression()) and (for_if_clauses := self.for_if_clauses()):
            return [expression, for_if_clauses]
        self._reset(mark)
        return None

    @memoize
    def _tmp_46(self) -> Any | None:
        # _tmp_46: args ','
        mark = self._mark()
        if (args := self.args()) and (literal := self.expect(",")):
            return [args, literal]
        self._reset(mark)
        return None

    @memoize
    def _tmp_47(self) -> Any | None:
        # _tmp_47: ',' | ')'
        return self.seq_alts(
            (self.expect, ","),
            (self.expect, ")"),
        )

    @memoize
    def _tmp_48(self) -> Any | None:
        # _tmp_48: 'True' | 'False' | 'None'
        return self.seq_alts(
            (self.expect, "True"),
            (self.expect, "False"),
            (self.expect, "None"),
        )

    @memoize
    def _tmp_49(self) -> Any | None:
        # _tmp_49: NAME '='
        mark = self._mark()
        if (name := self.name()) and (literal := self.expect("=")):
            return [name, literal]
        self._reset(mark)
        return None

    @memoize
    def _tmp_50(self) -> Any | None:
        # _tmp_50: NAME STRING | SOFT_KEYWORD
        mark = self._mark()
        if (name := self.name()) and (_string := self.token("STRING")):
            return [name, _string]
        self._reset(mark)
        if soft_keyword := self.soft_keyword():
            return soft_keyword
        self._reset(mark)
        return None

    @memoize
    def _tmp_51(self) -> Any | None:
        # _tmp_51: 'else' | ':'
        return self.seq_alts(
            (self.expect, "else"),
            (self.expect, ":"),
        )

    @memoize
    def _tmp_52(self) -> Any | None:
        # _tmp_52: FSTRING_MIDDLE | fstring_replacement_field
        return self.seq_alts(
            (self.token, "FSTRING_MIDDLE"),
            self.fstring_replacement_field,
        )

    @memoize
    def _tmp_53(self) -> Any | None:
        # _tmp_53: '=' | ':='
        return self.seq_alts(
            (self.expect, "="),
            (self.expect, ":="),
        )

    @memoize
    def _tmp_54(self) -> Any | None:
        # _tmp_54: plist | ptuple | genexp | 'True' | 'None' | 'False'
        return self.seq_alts(
            self.plist,
            self.ptuple,
            self.genexp,
            (self.expect, "True"),
            (self.expect, "None"),
            (self.expect, "False"),
        )

    @memoize
    def _tmp_56(self) -> Any | None:
        # _tmp_56: star_targets '='
        mark = self._mark()
        if (star_targets := self.star_targets()) and (literal := self.expect("=")):
            return [star_targets, literal]
        self._reset(mark)
        return None

    @memoize
    def _tmp_58(self) -> Any | None:
        # _tmp_58: '[' | '(' | '{'
        return self.seq_alts(
            (self.expect, "["),
            (self.expect, "("),
            (self.expect, "{"),
        )

    @memoize
    def _tmp_59(self) -> Any | None:
        # _tmp_59: '[' | '{'
        return self.seq_alts(
            (self.expect, "["),
            (self.expect, "{"),
        )

    @memoize
    def _tmp_61(self) -> Any | None:
        # _tmp_61: slash_no_default | slash_with_default
        return self.seq_alts(
            self.slash_no_default,
            self.slash_with_default,
        )

    @memoize
    def _tmp_63(self) -> Any | None:
        # _tmp_63: ',' | param_no_default
        return self.seq_alts(
            (self.expect, ","),
            self.param_no_default,
        )

    @memoize
    def _tmp_64(self) -> Any | None:
        # _tmp_64: ')' | ','
        return self.seq_alts(
            (self.expect, ")"),
            (self.expect, ","),
        )

    @memoize
    def _tmp_65(self) -> Any | None:
        # _tmp_65: ')' | ',' (')' | '**')
        mark = self._mark()
        if literal := self.expect(")"):
            return literal
        self._reset(mark)
        if (literal := self.expect(",")) and (_tmp_101 := self._tmp_101()):
            return [literal, _tmp_101]
        self._reset(mark)
        return None

    @memoize
    def _tmp_66(self) -> Any | None:
        # _tmp_66: param_no_default | ','
        return self.seq_alts(
            self.param_no_default,
            (self.expect, ","),
        )

    @memoize
    def _tmp_68(self) -> Any | None:
        # _tmp_68: '*' | '**' | '/'
        return self.seq_alts(
            (self.expect, "*"),
            (self.expect, "**"),
            (self.expect, "/"),
        )

    @memoize
    def _tmp_69(self) -> Any | None:
        # _tmp_69: lambda_slash_no_default | lambda_slash_with_default
        return self.seq_alts(
            self.lambda_slash_no_default,
            self.lambda_slash_with_default,
        )

    @memoize
    def _tmp_71(self) -> Any | None:
        # _tmp_71: ',' | lambda_param_no_default
        return self.seq_alts(
            (self.expect, ","),
            self.lambda_param_no_default,
        )

    @memoize
    def _tmp_72(self) -> Any | None:
        # _tmp_72: ':' | ',' (':' | '**')
        mark = self._mark()
        if literal := self.expect(":"):
            return literal
        self._reset(mark)
        if (literal := self.expect(",")) and (_tmp_102 := self._tmp_102()):
            return [literal, _tmp_102]
        self._reset(mark)
        return None

    @memoize
    def _tmp_73(self) -> Any | None:
        # _tmp_73: lambda_param_no_default | ','
        return self.seq_alts(
            self.lambda_param_no_default,
            (self.expect, ","),
        )

    @memoize
    def _tmp_77(self) -> Any | None:
        # _tmp_77: expression ['as' star_target]
        mark = self._mark()
        if (expression := self.expression()) and (opt := self._tmp_103(),):
            return [expression, opt]
        self._reset(mark)
        return None

    @memoize
    def _tmp_78(self) -> Any | None:
        # _tmp_78: expressions ['as' star_target]
        mark = self._mark()
        if (expressions := self.expressions()) and (opt := self._tmp_103(),):
            return [expressions, opt]
        self._reset(mark)
        return None

    @memoize
    def _tmp_81(self) -> Any | None:
        # _tmp_81: 'except' | 'finally'
        return self.seq_alts(
            (self.expect, "except"),
            (self.expect, "finally"),
        )

    @memoize
    def _tmp_82(self) -> Any | None:
        # _tmp_82: 'as' NAME
        mark = self._mark()
        if (literal := self.expect("as")) and (name := self.name()):
            return [literal, name]
        self._reset(mark)
        return None

    @memoize
    def _tmp_83(self) -> Any | None:
        # _tmp_83: expression ['as' NAME]
        mark = self._mark()
        if (expression := self.expression()) and (opt := self._tmp_82(),):
            return [expression, opt]
        self._reset(mark)
        return None

    @memoize
    def _tmp_86(self) -> Any | None:
        # _tmp_86: NEWLINE | ':'
        return self.seq_alts(
            (self.token, "NEWLINE"),
            (self.expect, ":"),
        )

    @memoize
    def _tmp_89(self) -> Any | None:
        # _tmp_89: positional_patterns ','
        mark = self._mark()
        if (positional_patterns := self.positional_patterns()) and (literal := self.expect(",")):
            return [positional_patterns, literal]
        self._reset(mark)
        return None

    @memoize
    def _tmp_90(self) -> Any | None:
        # _tmp_90: '(' arguments? ')'
        mark = self._mark()
        if (literal := self.expect("(")) and (opt := self.arguments(),) and (literal_1 := self.expect(")")):
            return [literal, opt, literal_1]
        self._reset(mark)
        return None

    @memoize
    def _tmp_92(self) -> Any | None:
        # _tmp_92: '}' | ','
        return self.seq_alts(
            (self.expect, "}"),
            (self.expect, ","),
        )

    @memoize
    def _tmp_94(self) -> Any | None:
        # _tmp_94: '=' | '!' | ':' | '}'
        return self.seq_alts(
            (self.expect, "="),
            (self.expect, "!"),
            (self.expect, ":"),
            (self.expect, "}"),
        )

    @memoize
    def _tmp_95(self) -> Any | None:
        # _tmp_95: '!' | ':' | '}'
        return self.seq_alts(
            (self.expect, "!"),
            (self.expect, ":"),
            (self.expect, "}"),
        )

    @memoize
    def _tmp_96(self) -> Any | None:
        # _tmp_96: '!' NAME
        mark = self._mark()
        if (literal := self.expect("!")) and (name := self.name()):
            return [literal, name]
        self._reset(mark)
        return None

    @memoize
    def _tmp_97(self) -> Any | None:
        # _tmp_97: ':' | '}'
        return self.seq_alts(
            (self.expect, ":"),
            (self.expect, "}"),
        )

    @memoize
    def _tmp_101(self) -> Any | None:
        # _tmp_101: ')' | '**'
        return self.seq_alts(
            (self.expect, ")"),
            (self.expect, "**"),
        )

    @memoize
    def _tmp_102(self) -> Any | None:
        # _tmp_102: ':' | '**'
        return self.seq_alts(
            (self.expect, ":"),
            (self.expect, "**"),
        )

    @memoize
    def _tmp_103(self) -> Any | None:
        # _tmp_103: 'as' star_target
        mark = self._mark()
        if (literal := self.expect("as")) and (star_target := self.star_target()):
            return [literal, star_target]
        self._reset(mark)
        return None

    KEYWORDS = ('False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except', 'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try', 'while', 'with', 'yield')  # fmt: skip
    SOFT_KEYWORDS = ('_', 'case', 'match', 'type')  # fmt: skip
