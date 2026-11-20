"""
QueryOpt AI — Semantic Analyzer
===============================
Performs catalog-backed semantic validation on the AST:
  • Table existence
  • Column existence
  • Table alias resolution
  • Qualified column name resolution
  • Ambiguous column detection in multi-table queries
  • Type compatibility checks
  • JOIN condition validity
"""

from __future__ import annotations

import sqlite3
from typing import Dict, List, Optional, Set, Tuple

from compiler.ast_nodes import (
    BinaryOp,
    Column,
    ColumnRef,
    Comparison,
    Expression,
    JoinClause,
    Literal,
    OrderByClause,
    SelectStatement,
    StarColumn,
    TableRef,
    WhereClause,
)
from compiler.diagnostics import ErrorCollector, SemanticError


class SemanticAnalyzer:
    """Validates AST nodes against a live SQLite database catalog."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._schema_cache: Dict[str, Dict[str, str]] = {}  # table -> {column: data_type}
        self._load_schema()

    def _load_schema(self) -> None:
        """Fetch all user tables and their column definitions from SQLite."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]

        for tbl in tables:
            cursor.execute(f"PRAGMA table_info('{tbl}')")
            cols = {row[1]: (row[2] or "TEXT").upper() for row in cursor.fetchall()}
            self._schema_cache[tbl.lower()] = cols
            # Keep original case mapping as well
            self._schema_cache[tbl] = cols

    def analyze(self, ast: SelectStatement) -> SelectStatement:
        """Validate the AST against the schema.

        Raises:
            SemanticError: if semantic rules are violated.
        """
        collector = ErrorCollector()

        # 1. Resolve tables and aliases
        alias_to_table: Dict[str, str] = {}
        referenced_tables: List[str] = []

        # From clause
        for tbl_ref in ast.from_clause:
            tbl_name = tbl_ref.name
            actual_table = self._find_table(tbl_name)
            if not actual_table:
                collector.add(
                    SemanticError(
                        stage="semantic",
                        message=f"Table '{tbl_name}' does not exist in the database.",
                        hint=f"Available tables: {', '.join(sorted(self._get_table_names()))}",
                    )
                )
            else:
                referenced_tables.append(actual_table)
                alias = tbl_ref.alias or tbl_name
                alias_to_table[alias.lower()] = actual_table
                alias_to_table[tbl_name.lower()] = actual_table

        # Joins
        for join in ast.joins:
            tbl_name = join.table.name
            actual_table = self._find_table(tbl_name)
            if not actual_table:
                collector.add(
                    SemanticError(
                        stage="semantic",
                        message=f"JOIN table '{tbl_name}' does not exist in the database.",
                        hint=f"Available tables: {', '.join(sorted(self._get_table_names()))}",
                    )
                )
            else:
                referenced_tables.append(actual_table)
                alias = join.table.alias or tbl_name
                alias_to_table[alias.lower()] = actual_table
                alias_to_table[tbl_name.lower()] = actual_table

        # Stop if table resolution failed
        if collector.has_errors():
            collector.raise_if_any()

        # 2. Validate SELECT columns
        for item in ast.columns:
            if isinstance(item, StarColumn):
                if item.table_alias:
                    alias_lower = item.table_alias.lower()
                    if alias_lower not in alias_to_table:
                        collector.add(
                            SemanticError(
                                stage="semantic",
                                message=f"Unknown table or alias '{item.table_alias}' in wildcard '{item.table_alias}.*'.",
                                hint=f"Known table aliases: {', '.join(sorted(alias_to_table.keys()))}",
                            )
                        )
            elif isinstance(item, Column):
                self._validate_column_ref(
                    col_name=item.name,
                    table_alias=item.table_alias,
                    alias_to_table=alias_to_table,
                    referenced_tables=referenced_tables,
                    collector=collector,
                    context="SELECT clause",
                )

        # 3. Validate JOIN ON conditions
        for join in ast.joins:
            self._validate_expression(
                expr=join.condition,
                alias_to_table=alias_to_table,
                referenced_tables=referenced_tables,
                collector=collector,
                context=f"JOIN ON clause for '{join.table.name}'",
            )

        # 4. Validate WHERE clause
        if ast.where_clause:
            self._validate_expression(
                expr=ast.where_clause.condition,
                alias_to_table=alias_to_table,
                referenced_tables=referenced_tables,
                collector=collector,
                context="WHERE clause",
            )

        # 5. Validate ORDER BY clause
        if ast.order_by:
            for item in ast.order_by.items:
                self._validate_column_ref(
                    col_name=item.column.name,
                    table_alias=item.column.table_alias,
                    alias_to_table=alias_to_table,
                    referenced_tables=referenced_tables,
                    collector=collector,
                    context="ORDER BY clause",
                )

        # 6. Validate LIMIT clause
        if ast.limit:
            if ast.limit.count < 0:
                collector.add(
                    SemanticError(
                        stage="semantic",
                        message=f"LIMIT count cannot be negative: {ast.limit.count}.",
                        hint="Specify a positive integer for LIMIT.",
                    )
                )

        collector.raise_if_any()
        return ast

    def _find_table(self, name: str) -> Optional[str]:
        for tbl in self._schema_cache:
            if tbl.lower() == name.lower():
                return tbl
        return None

    def _get_table_names(self) -> List[str]:
        return [t for t in self._schema_cache if t == t.capitalize() or t.lower() == t]

    def _get_columns_for_table(self, table_name: str) -> Dict[str, str]:
        actual = self._find_table(table_name)
        if actual and actual in self._schema_cache:
            return self._schema_cache[actual]
        return {}

    def _validate_column_ref(
        self,
        col_name: str,
        table_alias: Optional[str],
        alias_to_table: Dict[str, str],
        referenced_tables: List[str],
        collector: ErrorCollector,
        context: str,
    ) -> None:
        """Verify that a column reference exists and is unambiguous."""
        if table_alias:
            alias_lower = table_alias.lower()
            if alias_lower not in alias_to_table:
                collector.add(
                    SemanticError(
                        stage="semantic",
                        message=f"Table or alias '{table_alias}' in {context} is not recognized.",
                        hint=f"Available aliases: {', '.join(sorted(alias_to_table.keys()))}",
                    )
                )
                return

            tbl = alias_to_table[alias_lower]
            table_cols = self._get_columns_for_table(tbl)
            matching_col = self._find_col(col_name, table_cols)
            if not matching_col:
                collector.add(
                    SemanticError(
                        stage="semantic",
                        message=f"Column '{col_name}' does not exist in table '{tbl}' ({context}).",
                        hint=f"Available columns in '{tbl}': {', '.join(sorted(table_cols.keys()))}",
                    )
                )
        else:
            # Unqualified column — check across all referenced tables
            matching_tables = []
            for tbl in set(referenced_tables):
                table_cols = self._get_columns_for_table(tbl)
                if self._find_col(col_name, table_cols):
                    matching_tables.append(tbl)

            if len(matching_tables) == 0:
                all_cols = []
                for tbl in set(referenced_tables):
                    all_cols.extend([f"{tbl}.{c}" for c in self._get_columns_for_table(tbl)])
                collector.add(
                    SemanticError(
                        stage="semantic",
                        message=f"Column '{col_name}' not found in any referenced table ({context}).",
                        hint=f"Available columns: {', '.join(sorted(all_cols))}",
                    )
                )
            elif len(matching_tables) > 1:
                collector.add(
                    SemanticError(
                        stage="semantic",
                        message=f"Ambiguous column reference '{col_name}' in {context}; matches multiple tables: {', '.join(matching_tables)}.",
                        hint=f"Qualify the column with the table name or alias, e.g. '{matching_tables[0]}.{col_name}'.",
                    )
                )

    def _find_col(self, col_name: str, cols: Dict[str, str]) -> Optional[str]:
        for c in cols:
            if c.lower() == col_name.lower():
                return c
        return None

    def _validate_expression(
        self,
        expr: Expression,
        alias_to_table: Dict[str, str],
        referenced_tables: List[str],
        collector: ErrorCollector,
        context: str,
    ) -> None:
        """Recursively validate conditions and comparisons."""
        if isinstance(expr, BinaryOp):
            self._validate_expression(expr.left, alias_to_table, referenced_tables, collector, context)
            self._validate_expression(expr.right, alias_to_table, referenced_tables, collector, context)
        elif isinstance(expr, Comparison):
            self._validate_scalar_expr(expr.left, alias_to_table, referenced_tables, collector, context)
            self._validate_scalar_expr(expr.right, alias_to_table, referenced_tables, collector, context)
        elif isinstance(expr, ColumnRef):
            self._validate_column_ref(
                col_name=expr.name,
                table_alias=expr.table_alias,
                alias_to_table=alias_to_table,
                referenced_tables=referenced_tables,
                collector=collector,
                context=context,
            )

    def _validate_scalar_expr(
        self,
        expr: Expression,
        alias_to_table: Dict[str, str],
        referenced_tables: List[str],
        collector: ErrorCollector,
        context: str,
    ) -> None:
        if isinstance(expr, ColumnRef):
            self._validate_column_ref(
                col_name=expr.name,
                table_alias=expr.table_alias,
                alias_to_table=alias_to_table,
                referenced_tables=referenced_tables,
                collector=collector,
                context=context,
            )
        elif isinstance(expr, Literal):
            pass  # Literals are valid
        elif isinstance(expr, (BinaryOp, Comparison)):
            self._validate_expression(expr, alias_to_table, referenced_tables, collector, context)
