"""
QueryOpt AI — SQL Parser
========================
Parses SQL queries using Lark and converts the concrete syntax tree into
strongly typed AST nodes defined in compiler.ast_nodes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional, Union

from lark import Lark, Token as LarkToken, Transformer
from lark.exceptions import (
    LarkError,
    UnexpectedCharacters,
    UnexpectedEOF,
    UnexpectedToken,
)

from compiler.ast_nodes import (
    BinaryOp,
    Column,
    ColumnRef,
    Comparison,
    Expression,
    JoinClause,
    LimitClause,
    Literal,
    OrderByClause,
    OrderByItem,
    SelectStatement,
    StarColumn,
    TableRef,
    WhereClause,
)
from compiler.diagnostics import ParseError

GRAMMAR_PATH = Path(__file__).parent / "grammar.lark"


class ASTTransformer(Transformer):
    """Transforms the Lark parse tree into our custom AST nodes."""

    def start(self, children) -> SelectStatement:
        return children[0]

    def select_stmt(self, children) -> SelectStatement:
        distinct = False
        columns: List[Union[Column, StarColumn]] = []
        from_clause: List[TableRef] = []
        joins: List[JoinClause] = []
        where_clause: Optional[WhereClause] = None
        order_by: Optional[OrderByClause] = None
        limit: Optional[LimitClause] = None

        has_set_columns = False
        has_set_from = False

        for child in children:
            if isinstance(child, LarkToken):
                tok_str = str(child).upper()
                if tok_str == "DISTINCT":
                    distinct = True
                continue

            if child == "DISTINCT":
                distinct = True
            elif isinstance(child, list):
                if not has_set_columns:
                    columns = child
                    has_set_columns = True
                elif not has_set_from:
                    from_clause = child
                    has_set_from = True
            elif isinstance(child, JoinClause):
                joins.append(child)
            elif isinstance(child, WhereClause):
                where_clause = child
            elif isinstance(child, OrderByClause):
                order_by = child
            elif isinstance(child, LimitClause):
                limit = child

        return SelectStatement(
            columns=columns,
            from_clause=from_clause,
            where_clause=where_clause,
            joins=joins,
            order_by=order_by,
            limit=limit,
            distinct=distinct,
        )

    def distinct(self, children) -> str:
        return "DISTINCT"

    def select_list(self, children) -> List[Union[Column, StarColumn]]:
        return [c for c in children if not (isinstance(c, LarkToken) and str(c) == ",")]

    def star_column(self, children) -> StarColumn:
        tokens = [str(c) for c in children if str(c) not in (".",)]
        if len(tokens) >= 2 and tokens[-1] == "*":
            return StarColumn(table_alias=tokens[0])
        return StarColumn(table_alias=None)

    def aliased_column(self, children) -> Column:
        clean = [c for c in children if not (isinstance(c, LarkToken) and str(c).upper() == "AS")]
        expr = clean[0]
        alias = str(clean[1]) if len(clean) > 1 else None

        if isinstance(expr, ColumnRef):
            return Column(name=expr.name, table_alias=expr.table_alias, alias=alias)
        elif isinstance(expr, Literal):
            return Column(name=str(expr.value), table_alias=None, alias=alias)
        return Column(name=str(expr), alias=alias)

    def alias(self, children) -> str:
        clean = [str(c) for c in children if str(c).upper() != "AS"]
        return clean[0] if clean else ""

    def column_ref(self, children) -> ColumnRef:
        tokens = [str(c) for c in children if str(c) not in (".",)]
        if len(tokens) == 2:
            return ColumnRef(table_alias=tokens[0], name=tokens[1])
        return ColumnRef(name=tokens[0], table_alias=None)

    def int_literal(self, children) -> Literal:
        return Literal(value=int(children[0]), type="integer")

    def float_literal(self, children) -> Literal:
        return Literal(value=float(children[0]), type="float")

    def string_literal(self, children) -> Literal:
        raw = str(children[0])
        val = raw[1:-1].replace("''", "'")
        return Literal(value=val, type="string")

    def from_clause(self, children) -> List[TableRef]:
        return [c for c in children if isinstance(c, TableRef)]

    def table_ref(self, children) -> TableRef:
        clean = [str(c) for c in children if str(c).upper() != "AS"]
        name = clean[0]
        alias = clean[1] if len(clean) > 1 else None
        return TableRef(name=name, alias=alias)

    def join_clause(self, children) -> JoinClause:
        # join_type table_ref ON condition
        # Filter out "ON" token
        clean = [c for c in children if not (isinstance(c, LarkToken) and str(c).upper() == "ON")]
        join_type = "INNER"
        table = None
        condition = None

        for item in clean:
            if isinstance(item, str) and item in ("INNER", "CROSS"):
                join_type = item
            elif isinstance(item, TableRef):
                table = item
            elif isinstance(item, (BinaryOp, Comparison, ColumnRef, Literal)):
                condition = item

        # Fallback to positional if loop didn't catch condition
        if condition is None:
            condition = clean[-1]
        if table is None and len(clean) > 1:
            table = clean[1] if isinstance(clean[1], TableRef) else clean[0]

        return JoinClause(join_type=join_type, table=table, condition=condition)

    def join_type(self, children) -> str:
        return "INNER"

    def where_clause(self, children) -> WhereClause:
        # where_clause: WHERE condition
        return WhereClause(condition=children[-1])

    def or_expr(self, children) -> Expression:
        clean = [c for c in children if not (isinstance(c, LarkToken) and str(c).upper() == "OR")]
        if len(clean) == 1:
            return clean[0]
        node = clean[0]
        for right in clean[1:]:
            node = BinaryOp(left=node, operator="OR", right=right)
        return node

    def and_expr(self, children) -> Expression:
        clean = [c for c in children if not (isinstance(c, LarkToken) and str(c).upper() == "AND")]
        if len(clean) == 1:
            return clean[0]
        node = clean[0]
        for right in clean[1:]:
            node = BinaryOp(left=node, operator="AND", right=right)
        return node

    def paren_cond(self, children) -> Expression:
        clean = [c for c in children if not (isinstance(c, LarkToken) and str(c) in ("(", ")"))]
        return clean[0]

    def comparison(self, children) -> Comparison:
        left = children[0]
        op = str(children[1]).strip()
        right = children[2]
        return Comparison(left=left, operator=op, right=right)

    def order_by_clause(self, children) -> OrderByClause:
        items = [c for c in children if isinstance(c, OrderByItem)]
        return OrderByClause(items=items)

    def order_item(self, children) -> OrderByItem:
        col = children[0]
        direction = "ASC"
        if len(children) > 1 and children[1]:
            direction = str(children[1]).upper()
        return OrderByItem(column=col, direction=direction)

    def limit_clause(self, children) -> LimitClause:
        # limit_clause: LIMIT INT_NUMBER
        int_val = int(children[-1])
        return LimitClause(count=int_val)


class SQLParser:
    """Parses SQL queries into structured AST trees."""

    def __init__(self, grammar_path: Optional[Path] = None):
        path = grammar_path or GRAMMAR_PATH
        with open(path, "r", encoding="utf-8") as f:
            grammar_text = f.read()

        self._lark = Lark(
            grammar_text,
            start="start",
            parser="earley",
            propagate_positions=True,
        )
        self._transformer = ASTTransformer()

    def parse(self, sql: str) -> SelectStatement:
        if not sql or not sql.strip():
            raise ParseError(
                stage="parser",
                message="Cannot parse an empty SQL query.",
                position=(1, 1),
                hint="Provide a valid SELECT statement.",
            )

        clean_sql = sql.strip().rstrip(";")

        try:
            tree = self._lark.parse(clean_sql)
            ast = self._transformer.transform(tree)
            return ast
        except UnexpectedToken as exc:
            line = getattr(exc, "line", 1)
            column = getattr(exc, "column", 1)
            token = getattr(exc, "token", None)
            val = str(token.value) if token else "unknown token"
            expected = ", ".join(sorted(exc.expected)) if hasattr(exc, "expected") else "valid SQL clause"
            hint = f"Unexpected token '{val}'. Expected one of: {expected}."
            if "FROM" in str(expected).upper() and "FROM" not in clean_sql.upper():
                hint = "Missing FROM clause in SELECT query."
            elif val.upper() == "FROM":
                hint = "Missing column list or '*' before FROM keyword."
            raise ParseError(
                stage="parser",
                message=f"Syntax error at line {line}, column {column}: unexpected token '{val}'",
                position=(line, column),
                hint=hint,
            ) from exc
        except UnexpectedCharacters as exc:
            line = getattr(exc, "line", 1)
            column = getattr(exc, "column", 1)
            char = exc.char if hasattr(exc, "char") else "invalid character"
            raise ParseError(
                stage="parser",
                message=f"Syntax error at line {line}, column {column}: unexpected character '{char}'",
                position=(line, column),
                hint=f"Check syntax around character '{char}'. Ensure quotes and operators are valid.",
            ) from exc
        except UnexpectedEOF as exc:
            raise ParseError(
                stage="parser",
                message="Syntax error: Unexpected end of SQL input.",
                position=(1, len(clean_sql)),
                hint="Query terminated prematurely. Ensure all clauses and parentheses are properly closed.",
            ) from exc
        except LarkError as exc:
            raise ParseError(
                stage="parser",
                message=f"Parsing error: {str(exc)}",
                position=(1, 1),
                hint="Verify that the query conforms to supported SQL syntax.",
            ) from exc


_default_parser: Optional[SQLParser] = None


def parse(sql: str) -> SelectStatement:
    global _default_parser
    if _default_parser is None:
        _default_parser = SQLParser()
    return _default_parser.parse(sql)
