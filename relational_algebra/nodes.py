"""
QueryOpt AI — Relational Algebra Representation
===============================================
Defines strongly typed relational algebra operator nodes and condition
expressions used for logical query planning and algebraic rewriting.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


# ============================================================================
# Condition Expressions
# ============================================================================

@dataclass
class ColumnReference:
    """Represents a column reference inside a relational algebra condition."""
    name: str
    table: Optional[str] = None

    def __str__(self) -> str:
        return f"{self.table}.{self.name}" if self.table else self.name

    def to_dict(self) -> dict:
        return {"type": "ColumnReference", "name": self.name, "table": self.table}


@dataclass
class LiteralValue:
    """Represents a literal constant in a condition."""
    value: Any
    data_type: str  # 'integer', 'float', 'string'

    def __str__(self) -> str:
        return repr(self.value) if self.data_type == "string" else str(self.value)

    def to_dict(self) -> dict:
        return {"type": "LiteralValue", "value": self.value, "data_type": self.data_type}


@dataclass
class Predicate:
    """Single binary comparison condition (e.g. age > 23)."""
    left: Any
    op: str
    right: Any

    def __str__(self) -> str:
        return f"{self.left} {self.op} {self.right}"

    def to_dict(self) -> dict:
        left_dict = self.left.to_dict() if hasattr(self.left, "to_dict") else str(self.left)
        right_dict = self.right.to_dict() if hasattr(self.right, "to_dict") else str(self.right)
        return {"type": "Predicate", "left": left_dict, "op": self.op, "right": right_dict}


@dataclass
class AndCondition:
    """Conjunction of two or more conditions."""
    conditions: List[Any]

    def __str__(self) -> str:
        return " AND ".join(f"({c})" for c in self.conditions)

    def to_dict(self) -> dict:
        return {
            "type": "AndCondition",
            "conditions": [c.to_dict() if hasattr(c, "to_dict") else str(c) for c in self.conditions],
        }


@dataclass
class OrCondition:
    """Disjunction of two or more conditions."""
    conditions: List[Any]

    def __str__(self) -> str:
        return " OR ".join(f"({c})" for c in self.conditions)

    def to_dict(self) -> dict:
        return {
            "type": "OrCondition",
            "conditions": [c.to_dict() if hasattr(c, "to_dict") else str(c) for c in self.conditions],
        }


# ============================================================================
# Relational Algebra Operator Nodes
# ============================================================================

@dataclass
class RANode:
    """Base class for all Relational Algebra tree nodes."""

    def children(self) -> List[RANode]:
        return []

    def copy(self) -> RANode:
        return deepcopy(self)

    def to_dict(self) -> dict:
        raise NotImplementedError

    def pretty_print(self, indent: int = 0) -> str:
        pad = "  " * indent
        child_strs = [c.pretty_print(indent + 1) for c in self.children()]
        res = f"{pad}{self}"
        if child_strs:
            res += "\n" + "\n".join(child_strs)
        return res


@dataclass
class Scan(RANode):
    """Table Scan operator: Scan(TableName, [alias])"""
    table_name: str
    alias: Optional[str] = None
    pushed_predicate: Optional[Any] = None  # Populated if predicate pushed directly into scan

    def __str__(self) -> str:
        al = f" AS {self.alias}" if self.alias and self.alias.lower() != self.table_name.lower() else ""
        pred = f", predicate={self.pushed_predicate}" if self.pushed_predicate else ""
        return f"Scan({self.table_name}{al}{pred})"

    def to_dict(self) -> dict:
        return {
            "operator": "Scan",
            "symbol": "Scan",
            "table_name": self.table_name,
            "alias": self.alias,
            "pushed_predicate": str(self.pushed_predicate) if self.pushed_predicate else None,
            "children": [],
        }


@dataclass
class Selection(RANode):
    """Selection operator: σ_condition(Child)"""
    condition: Any
    child: RANode

    def children(self) -> List[RANode]:
        return [self.child]

    def __str__(self) -> str:
        return f"σ[{self.condition}]"

    def to_dict(self) -> dict:
        return {
            "operator": "Selection",
            "symbol": "σ",
            "condition": str(self.condition),
            "children": [self.child.to_dict()],
        }


@dataclass
class Projection(RANode):
    """Projection operator: π_columns(Child)"""
    columns: List[str]  # e.g. ["name", "age"] or ["s.name", "d.dept_name"]
    child: RANode

    def children(self) -> List[RANode]:
        return [self.child]

    def __str__(self) -> str:
        cols = ", ".join(self.columns)
        return f"π[{cols}]"

    def to_dict(self) -> dict:
        return {
            "operator": "Projection",
            "symbol": "π",
            "columns": self.columns,
            "children": [self.child.to_dict()],
        }


@dataclass
class Join(RANode):
    """Join operator: Left ⋈_condition Right"""
    join_type: str  # 'INNER'
    condition: Any
    left: RANode
    right: RANode

    def children(self) -> List[RANode]:
        return [self.left, self.right]

    def __str__(self) -> str:
        return f"⋈[{self.join_type} ON {self.condition}]"

    def to_dict(self) -> dict:
        return {
            "operator": "Join",
            "symbol": "⋈",
            "join_type": self.join_type,
            "condition": str(self.condition),
            "children": [self.left.to_dict(), self.right.to_dict()],
        }


@dataclass
class Sort(RANode):
    """Sort operator: τ_items(Child)"""
    order_items: List[tuple]  # list of (column_name, 'ASC'|'DESC')
    child: RANode

    def children(self) -> List[RANode]:
        return [self.child]

    def __str__(self) -> str:
        items = ", ".join(f"{col} {dir}" for col, dir in self.order_items)
        return f"τ[{items}]"

    def to_dict(self) -> dict:
        return {
            "operator": "Sort",
            "symbol": "τ",
            "order_items": self.order_items,
            "children": [self.child.to_dict()],
        }


@dataclass
class Limit(RANode):
    """Limit operator: Limit_count(Child)"""
    count: int
    child: RANode

    def children(self) -> List[RANode]:
        return [self.child]

    def __str__(self) -> str:
        return f"Limit[{self.count}]"

    def to_dict(self) -> dict:
        return {
            "operator": "Limit",
            "symbol": "LIMIT",
            "count": self.count,
            "children": [self.child.to_dict()],
        }


@dataclass
class Distinct(RANode):
    """Distinct operator: δ(Child)"""
    child: RANode

    def children(self) -> List[RANode]:
        return [self.child]

    def __str__(self) -> str:
        return "δ[DISTINCT]"

    def to_dict(self) -> dict:
        return {
            "operator": "Distinct",
            "symbol": "δ",
            "children": [self.child.to_dict()],
        }
