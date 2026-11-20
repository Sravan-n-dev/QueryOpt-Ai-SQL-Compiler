"""
QueryOpt AI — AST Node Definitions
====================================
Complete AST representation for the SQL subset supported by the QueryOpt AI
compiler.  Every node is a frozen-friendly dataclass that supports:

  • to_dict()        — recursive serialisation to plain dicts/lists
  • pretty_print()   — human-readable, indented string rendering
  • accept(visitor)  — double-dispatch for the Visitor pattern
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Protocol, Union


# ============================================================================
# Visitor protocol
# ============================================================================

class ASTVisitor(Protocol):
    """Protocol that any concrete visitor must satisfy."""

    def visit_select_statement(self, node: "SelectStatement") -> Any: ...
    def visit_column(self, node: "Column") -> Any: ...
    def visit_star_column(self, node: "StarColumn") -> Any: ...
    def visit_table_ref(self, node: "TableRef") -> Any: ...
    def visit_where_clause(self, node: "WhereClause") -> Any: ...
    def visit_binary_op(self, node: "BinaryOp") -> Any: ...
    def visit_comparison(self, node: "Comparison") -> Any: ...
    def visit_column_ref(self, node: "ColumnRef") -> Any: ...
    def visit_literal(self, node: "Literal") -> Any: ...
    def visit_join_clause(self, node: "JoinClause") -> Any: ...
    def visit_order_by_clause(self, node: "OrderByClause") -> Any: ...
    def visit_order_by_item(self, node: "OrderByItem") -> Any: ...
    def visit_limit_clause(self, node: "LimitClause") -> Any: ...


# ============================================================================
# Expression type alias  (used by WhereClause, BinaryOp, Comparison, etc.)
# ============================================================================

Expression = Union["BinaryOp", "Comparison", "ColumnRef", "Literal"]


# ============================================================================
# Base class
# ============================================================================

@dataclass
class ASTNode:
    """Abstract base for every AST node."""

    # -- serialisation -------------------------------------------------------

    def to_dict(self) -> dict:
        """Return a JSON-serialisable dict representation of this node."""
        raise NotImplementedError

    # -- pretty printing -----------------------------------------------------

    def pretty_print(self, indent: int = 0) -> str:
        """Return a human-readable, indented string for this node."""
        raise NotImplementedError

    # -- visitor pattern -----------------------------------------------------

    def accept(self, visitor: ASTVisitor) -> Any:
        """Double-dispatch to *visitor*."""
        raise NotImplementedError

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _indent(level: int) -> str:
        return "  " * level

    @staticmethod
    def _child_to_dict(value: Any) -> Any:
        """Recursively convert a child value for *to_dict*."""
        if isinstance(value, ASTNode):
            return value.to_dict()
        if isinstance(value, list):
            return [ASTNode._child_to_dict(v) for v in value]
        return value

    @staticmethod
    def _child_pretty(value: Any, indent: int) -> str:
        """Recursively pretty-print a child value."""
        if isinstance(value, ASTNode):
            return value.pretty_print(indent)
        if isinstance(value, list):
            if not value:
                return "[]"
            parts = [ASTNode._child_pretty(v, indent + 1) for v in value]
            inner = (",\n").join(parts)
            pad = ASTNode._indent(indent)
            return f"[\n{inner}\n{pad}]"
        return repr(value)


# ============================================================================
# Leaf / scalar nodes
# ============================================================================

@dataclass
class ColumnRef(ASTNode):
    """Reference to a column, optionally qualified by a table/alias name."""

    name: str
    table_alias: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "node": "ColumnRef",
            "name": self.name,
            "table_alias": self.table_alias,
        }

    def pretty_print(self, indent: int = 0) -> str:
        pad = self._indent(indent)
        qualified = f"{self.table_alias}.{self.name}" if self.table_alias else self.name
        return f"{pad}ColumnRef({qualified})"

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_column_ref(self)


@dataclass
class Literal(ASTNode):
    """A literal value: integer, float, or single-quoted string."""

    value: Any
    type: str  # 'integer' | 'float' | 'string'

    def to_dict(self) -> dict:
        return {
            "node": "Literal",
            "value": self.value,
            "type": self.type,
        }

    def pretty_print(self, indent: int = 0) -> str:
        pad = self._indent(indent)
        display = repr(self.value) if self.type == "string" else str(self.value)
        return f"{pad}Literal({display}, type={self.type})"

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_literal(self)


# ============================================================================
# Column list items  (SELECT clause)
# ============================================================================

@dataclass
class Column(ASTNode):
    """A named column in the SELECT list, with optional table qualifier and alias."""

    name: str
    table_alias: Optional[str] = None
    alias: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "node": "Column",
            "name": self.name,
            "table_alias": self.table_alias,
            "alias": self.alias,
        }

    def pretty_print(self, indent: int = 0) -> str:
        pad = self._indent(indent)
        qualified = f"{self.table_alias}.{self.name}" if self.table_alias else self.name
        alias_part = f" AS {self.alias}" if self.alias else ""
        return f"{pad}Column({qualified}{alias_part})"

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_column(self)


@dataclass
class StarColumn(ASTNode):
    """A wildcard ``*`` or ``table.*`` in the SELECT list."""

    table_alias: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "node": "StarColumn",
            "table_alias": self.table_alias,
        }

    def pretty_print(self, indent: int = 0) -> str:
        pad = self._indent(indent)
        qualified = f"{self.table_alias}.*" if self.table_alias else "*"
        return f"{pad}StarColumn({qualified})"

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_star_column(self)


# ============================================================================
# Table reference
# ============================================================================

@dataclass
class TableRef(ASTNode):
    """A table name with an optional alias."""

    name: str
    alias: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "node": "TableRef",
            "name": self.name,
            "alias": self.alias,
        }

    def pretty_print(self, indent: int = 0) -> str:
        pad = self._indent(indent)
        alias_part = f" AS {self.alias}" if self.alias else ""
        return f"{pad}TableRef({self.name}{alias_part})"

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_table_ref(self)


# ============================================================================
# Boolean / comparison expressions (WHERE, JOIN ON)
# ============================================================================

@dataclass
class BinaryOp(ASTNode):
    """A boolean binary operator (AND / OR) combining two sub-expressions."""

    left: Expression
    operator: str  # 'AND' | 'OR'
    right: Expression

    def to_dict(self) -> dict:
        return {
            "node": "BinaryOp",
            "operator": self.operator,
            "left": self._child_to_dict(self.left),
            "right": self._child_to_dict(self.right),
        }

    def pretty_print(self, indent: int = 0) -> str:
        pad = self._indent(indent)
        left_str = self._child_pretty(self.left, indent + 1)
        right_str = self._child_pretty(self.right, indent + 1)
        return (
            f"{pad}BinaryOp(\n"
            f"{left_str}\n"
            f"{pad}  {self.operator}\n"
            f"{right_str}\n"
            f"{pad})"
        )

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_binary_op(self)


@dataclass
class Comparison(ASTNode):
    """A comparison between two scalar expressions (=, !=, <>, <, >, <=, >=)."""

    left: Expression
    operator: str
    right: Expression

    def to_dict(self) -> dict:
        return {
            "node": "Comparison",
            "operator": self.operator,
            "left": self._child_to_dict(self.left),
            "right": self._child_to_dict(self.right),
        }

    def pretty_print(self, indent: int = 0) -> str:
        pad = self._indent(indent)
        left_str = self._child_pretty(self.left, indent + 1)
        right_str = self._child_pretty(self.right, indent + 1)
        return (
            f"{pad}Comparison(\n"
            f"{left_str}\n"
            f"{pad}  {self.operator}\n"
            f"{right_str}\n"
            f"{pad})"
        )

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_comparison(self)


# ============================================================================
# Clauses
# ============================================================================

@dataclass
class WhereClause(ASTNode):
    """The WHERE clause wrapping a boolean condition tree."""

    condition: Expression

    def to_dict(self) -> dict:
        return {
            "node": "WhereClause",
            "condition": self._child_to_dict(self.condition),
        }

    def pretty_print(self, indent: int = 0) -> str:
        pad = self._indent(indent)
        cond_str = self._child_pretty(self.condition, indent + 1)
        return f"{pad}WhereClause(\n{cond_str}\n{pad})"

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_where_clause(self)


@dataclass
class JoinClause(ASTNode):
    """A JOIN clause: join type, target table, and ON condition."""

    join_type: str  # 'INNER'
    table: TableRef
    condition: Expression

    def to_dict(self) -> dict:
        return {
            "node": "JoinClause",
            "join_type": self.join_type,
            "table": self._child_to_dict(self.table),
            "condition": self._child_to_dict(self.condition),
        }

    def pretty_print(self, indent: int = 0) -> str:
        pad = self._indent(indent)
        table_str = self._child_pretty(self.table, indent + 1)
        cond_str = self._child_pretty(self.condition, indent + 1)
        return (
            f"{pad}JoinClause({self.join_type},\n"
            f"{table_str},\n"
            f"{cond_str}\n"
            f"{pad})"
        )

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_join_clause(self)


@dataclass
class OrderByItem(ASTNode):
    """A single column + direction pair inside ORDER BY."""

    column: ColumnRef
    direction: str = "ASC"  # 'ASC' | 'DESC'

    def to_dict(self) -> dict:
        return {
            "node": "OrderByItem",
            "column": self._child_to_dict(self.column),
            "direction": self.direction,
        }

    def pretty_print(self, indent: int = 0) -> str:
        pad = self._indent(indent)
        col_str = self._child_pretty(self.column, 0).strip()
        return f"{pad}OrderByItem({col_str} {self.direction})"

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_order_by_item(self)


@dataclass
class OrderByClause(ASTNode):
    """The ORDER BY clause containing one or more ordering items."""

    items: List[OrderByItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "node": "OrderByClause",
            "items": self._child_to_dict(self.items),
        }

    def pretty_print(self, indent: int = 0) -> str:
        pad = self._indent(indent)
        items_str = self._child_pretty(self.items, indent + 1)
        return f"{pad}OrderByClause(\n{items_str}\n{pad})"

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_order_by_clause(self)


@dataclass
class LimitClause(ASTNode):
    """The LIMIT clause."""

    count: int

    def to_dict(self) -> dict:
        return {
            "node": "LimitClause",
            "count": self.count,
        }

    def pretty_print(self, indent: int = 0) -> str:
        pad = self._indent(indent)
        return f"{pad}LimitClause({self.count})"

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_limit_clause(self)


# ============================================================================
# Top-level statement
# ============================================================================

@dataclass
class SelectStatement(ASTNode):
    """Root AST node for a SELECT query."""

    columns: List[Union[Column, StarColumn]]
    from_clause: List[TableRef]
    where_clause: Optional[WhereClause] = None
    joins: List[JoinClause] = field(default_factory=list)
    order_by: Optional[OrderByClause] = None
    limit: Optional[LimitClause] = None
    distinct: bool = False

    def to_dict(self) -> dict:
        return {
            "node": "SelectStatement",
            "distinct": self.distinct,
            "columns": self._child_to_dict(self.columns),
            "from_clause": self._child_to_dict(self.from_clause),
            "joins": self._child_to_dict(self.joins),
            "where_clause": self._child_to_dict(self.where_clause) if self.where_clause else None,
            "order_by": self._child_to_dict(self.order_by) if self.order_by else None,
            "limit": self._child_to_dict(self.limit) if self.limit else None,
        }

    def pretty_print(self, indent: int = 0) -> str:
        pad = self._indent(indent)
        lines = [f"{pad}SelectStatement("]
        if self.distinct:
            lines.append(f"{pad}  DISTINCT")

        lines.append(f"{pad}  columns={self._child_pretty(self.columns, indent + 2)}")
        lines.append(f"{pad}  from={self._child_pretty(self.from_clause, indent + 2)}")

        if self.joins:
            lines.append(f"{pad}  joins={self._child_pretty(self.joins, indent + 2)}")
        if self.where_clause:
            lines.append(f"{pad}  where={self._child_pretty(self.where_clause, indent + 2)}")
        if self.order_by:
            lines.append(f"{pad}  order_by={self._child_pretty(self.order_by, indent + 2)}")
        if self.limit:
            lines.append(f"{pad}  limit={self._child_pretty(self.limit, indent + 2)}")

        lines.append(f"{pad})")
        return "\n".join(lines)

    def accept(self, visitor: ASTVisitor) -> Any:
        return visitor.visit_select_statement(self)
