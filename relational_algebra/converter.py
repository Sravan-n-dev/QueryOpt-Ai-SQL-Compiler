"""
QueryOpt AI — AST to Relational Algebra Converter
=================================================
Transforms a validated SelectStatement AST into a canonical Relational
Algebra operator tree:
  Limit -> Sort -> Distinct -> Projection -> Selection -> Join* -> Scan
"""

from __future__ import annotations

from typing import Any, List, Optional

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
    SelectStatement,
    StarColumn,
    TableRef,
    WhereClause,
)
from relational_algebra.nodes import (
    AndCondition,
    ColumnReference,
    Distinct,
    Join,
    Limit,
    LiteralValue,
    OrCondition,
    Predicate,
    Projection,
    RANode,
    Scan,
    Selection,
    Sort,
)


class ASTToRAConverter:
    """Converts a parsed and validated SelectStatement AST into a Relational Algebra tree."""

    def convert(self, ast: SelectStatement) -> RANode:
        """Construct the canonical initial Relational Algebra tree."""
        # 1. Base table scan(s) from FROM clause
        if not ast.from_clause:
            raise ValueError("SelectStatement has no FROM clause.")

        first_tbl = ast.from_clause[0]
        current_node: RANode = Scan(table_name=first_tbl.name, alias=first_tbl.alias)

        # Additional comma-separated tables in FROM treated as implicit Cross Joins
        for extra_tbl in ast.from_clause[1:]:
            right_scan = Scan(table_name=extra_tbl.name, alias=extra_tbl.alias)
            current_node = Join(
                join_type="CROSS",
                condition=Predicate(
                    left=LiteralValue(1, "integer"),
                    op="=",
                    right=LiteralValue(1, "integer"),
                ),
                left=current_node,
                right=right_scan,
            )

        # 2. Explicit JOIN clauses
        for join in ast.joins:
            right_scan = Scan(table_name=join.table.name, alias=join.table.alias)
            cond = self._convert_expression(join.condition)
            current_node = Join(
                join_type=join.join_type or "INNER",
                condition=cond,
                left=current_node,
                right=right_scan,
            )

        # 3. WHERE clause -> Selection (σ)
        if ast.where_clause:
            where_cond = self._convert_expression(ast.where_clause.condition)
            current_node = Selection(condition=where_cond, child=current_node)

        # 4. SELECT columns -> Projection (π)
        col_names: List[str] = []
        is_wildcard = False
        for c in ast.columns:
            if isinstance(c, StarColumn):
                is_wildcard = True
                col_names.append(f"{c.table_alias}.*" if c.table_alias else "*")
            elif isinstance(c, Column):
                q = f"{c.table_alias}.{c.name}" if c.table_alias else c.name
                col_names.append(q)

        # Projection is added (unless it's a bare "*", which can still be projected as "*")
        current_node = Projection(columns=col_names, child=current_node)

        # 5. DISTINCT (δ)
        if ast.distinct:
            current_node = Distinct(child=current_node)

        # 6. ORDER BY (τ)
        if ast.order_by and ast.order_by.items:
            order_items = [
                (
                    f"{item.column.table_alias}.{item.column.name}" if item.column.table_alias else item.column.name,
                    item.direction,
                )
                for item in ast.order_by.items
            ]
            current_node = Sort(order_items=order_items, child=current_node)

        # 7. LIMIT
        if ast.limit:
            current_node = Limit(count=ast.limit.count, child=current_node)

        return current_node

    def _convert_expression(self, expr: Expression) -> Any:
        """Convert AST boolean/comparison expression into RA condition."""
        if isinstance(expr, BinaryOp):
            left_cond = self._convert_expression(expr.left)
            right_cond = self._convert_expression(expr.right)
            if expr.operator.upper() == "AND":
                # Flatten nested ANDs if desirable
                conds = []
                if isinstance(left_cond, AndCondition):
                    conds.extend(left_cond.conditions)
                else:
                    conds.append(left_cond)
                if isinstance(right_cond, AndCondition):
                    conds.extend(right_cond.conditions)
                else:
                    conds.append(right_cond)
                return AndCondition(conditions=conds)
            elif expr.operator.upper() == "OR":
                conds = []
                if isinstance(left_cond, OrCondition):
                    conds.extend(left_cond.conditions)
                else:
                    conds.append(left_cond)
                if isinstance(right_cond, OrCondition):
                    conds.extend(right_cond.conditions)
                else:
                    conds.append(right_cond)
                return OrCondition(conditions=conds)
            return Predicate(left=left_cond, op=expr.operator, right=right_cond)

        elif isinstance(expr, Comparison):
            left_val = self._convert_scalar(expr.left)
            right_val = self._convert_scalar(expr.right)
            return Predicate(left=left_val, op=expr.operator, right=right_val)

        elif isinstance(expr, ColumnRef):
            return ColumnReference(name=expr.name, table=expr.table_alias)

        elif isinstance(expr, Literal):
            return LiteralValue(value=expr.value, data_type=expr.type)

        return str(expr)

    def _convert_scalar(self, expr: Expression) -> Any:
        if isinstance(expr, ColumnRef):
            return ColumnReference(name=expr.name, table=expr.table_alias)
        elif isinstance(expr, Literal):
            return LiteralValue(value=expr.value, data_type=expr.type)
        return expr
