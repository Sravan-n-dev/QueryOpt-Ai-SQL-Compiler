"""
QueryOpt AI — Physical Plan Nodes
=================================
Physical operator representation chosen by the cost-based optimizer,
annotated with estimated costs, estimated output cardinalities, and chosen access paths.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PlanChoice:
    """Rationale for selecting a particular physical operator over alternatives."""

    strategy: str
    estimated_cost: float
    estimated_rows: float
    reason: str
    alternatives: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy,
            "estimated_cost": self.estimated_cost,
            "estimated_rows": self.estimated_rows,
            "reason": self.reason,
            "alternatives": self.alternatives,
        }


@dataclass
class PhysicalNode:
    """Base class for all physical execution plan operators."""

    node_type: str = ""
    estimated_cost: float = 0.0
    estimated_rows: float = 0.0
    actual_rows: int = 0
    execution_time_ms: float = 0.0
    choice: Optional[PlanChoice] = None

    def children(self) -> List[PhysicalNode]:
        return []

    def to_dict(self) -> dict:
        raise NotImplementedError

    def pretty_print(self, indent: int = 0) -> str:
        pad = "  " * indent
        child_strs = [c.pretty_print(indent + 1) for c in self.children()]
        cost_info = f" [est_cost={self.estimated_cost:.2f}, est_rows={self.estimated_rows:.0f}]"
        res = f"{pad}{self.node_type}{cost_info}"
        if child_strs:
            res += "\n" + "\n".join(child_strs)
        return res


@dataclass
class TableScanNode(PhysicalNode):
    """Full sequential table scan."""
    table_name: str = ""
    alias: Optional[str] = None

    def __post_init__(self):
        self.node_type = f"TableScan({self.table_name})"

    def to_dict(self) -> dict:
        return {
            "operator": "TableScan",
            "table_name": self.table_name,
            "alias": self.alias,
            "estimated_cost": self.estimated_cost,
            "estimated_rows": self.estimated_rows,
            "choice": self.choice.to_dict() if self.choice else None,
            "children": [],
        }


@dataclass
class IndexScanNode(PhysicalNode):
    """B-Tree index lookup scan."""
    table_name: str = ""
    index_name: str = ""
    column: str = ""
    op: str = "="
    value: Any = None
    alias: Optional[str] = None

    def __post_init__(self):
        self.node_type = f"IndexScan({self.table_name} via {self.index_name} ON {self.column} {self.op} {self.value})"

    def to_dict(self) -> dict:
        return {
            "operator": "IndexScan",
            "table_name": self.table_name,
            "index_name": self.index_name,
            "column": self.column,
            "op": self.op,
            "value": str(self.value),
            "alias": self.alias,
            "estimated_cost": self.estimated_cost,
            "estimated_rows": self.estimated_rows,
            "choice": self.choice.to_dict() if self.choice else None,
            "children": [],
        }


@dataclass
class FilterNode(PhysicalNode):
    """Evaluates predicate conditions on input tuples."""
    condition: Any = None
    child: Optional[PhysicalNode] = None

    def __post_init__(self):
        self.node_type = f"Filter({self.condition})"

    def children(self) -> List[PhysicalNode]:
        return [self.child] if self.child else []

    def to_dict(self) -> dict:
        return {
            "operator": "Filter",
            "condition": str(self.condition),
            "estimated_cost": self.estimated_cost,
            "estimated_rows": self.estimated_rows,
            "children": [self.child.to_dict()] if self.child else [],
        }


@dataclass
class ProjectNode(PhysicalNode):
    """Selects and renames output attributes."""
    columns: List[str] = field(default_factory=list)
    child: Optional[PhysicalNode] = None

    def __post_init__(self):
        self.node_type = f"Project({', '.join(self.columns)})"

    def children(self) -> List[PhysicalNode]:
        return [self.child] if self.child else []

    def to_dict(self) -> dict:
        return {
            "operator": "Project",
            "columns": self.columns,
            "estimated_cost": self.estimated_cost,
            "estimated_rows": self.estimated_rows,
            "children": [self.child.to_dict()] if self.child else [],
        }


@dataclass
class HashJoinNode(PhysicalNode):
    """In-memory Hash Join with build side and probe side."""
    left_key: str = ""
    right_key: str = ""
    condition: Any = None
    left: Optional[PhysicalNode] = None
    right: Optional[PhysicalNode] = None
    build_side: str = "right"

    def __post_init__(self):
        self.node_type = f"HashJoin({self.left_key} = {self.right_key})"

    def children(self) -> List[PhysicalNode]:
        res = []
        if self.left:
            res.append(self.left)
        if self.right:
            res.append(self.right)
        return res

    def to_dict(self) -> dict:
        return {
            "operator": "HashJoin",
            "left_key": self.left_key,
            "right_key": self.right_key,
            "condition": str(self.condition),
            "build_side": self.build_side,
            "estimated_cost": self.estimated_cost,
            "estimated_rows": self.estimated_rows,
            "choice": self.choice.to_dict() if self.choice else None,
            "children": [c.to_dict() for c in self.children()],
        }


@dataclass
class NestedLoopJoinNode(PhysicalNode):
    """Tuple-by-tuple nested loop join."""
    condition: Any = None
    left: Optional[PhysicalNode] = None
    right: Optional[PhysicalNode] = None

    def __post_init__(self):
        self.node_type = f"NestedLoopJoin({self.condition})"

    def children(self) -> List[PhysicalNode]:
        res = []
        if self.left:
            res.append(self.left)
        if self.right:
            res.append(self.right)
        return res

    def to_dict(self) -> dict:
        return {
            "operator": "NestedLoopJoin",
            "condition": str(self.condition),
            "estimated_cost": self.estimated_cost,
            "estimated_rows": self.estimated_rows,
            "choice": self.choice.to_dict() if self.choice else None,
            "children": [c.to_dict() for c in self.children()],
        }


@dataclass
class SortNode(PhysicalNode):
    """Sorts incoming tuples by one or more keys."""
    order_items: List[tuple] = field(default_factory=list)
    child: Optional[PhysicalNode] = None

    def __post_init__(self):
        items_str = ", ".join(f"{c} {d}" for c, d in self.order_items)
        self.node_type = f"Sort({items_str})"

    def children(self) -> List[PhysicalNode]:
        return [self.child] if self.child else []

    def to_dict(self) -> dict:
        return {
            "operator": "Sort",
            "order_items": self.order_items,
            "estimated_cost": self.estimated_cost,
            "estimated_rows": self.estimated_rows,
            "children": [self.child.to_dict()] if self.child else [],
        }


@dataclass
class LimitNode(PhysicalNode):
    """Truncates result set to given count."""
    count: int = 0
    child: Optional[PhysicalNode] = None

    def __post_init__(self):
        self.node_type = f"Limit({self.count})"

    def children(self) -> List[PhysicalNode]:
        return [self.child] if self.child else []

    def to_dict(self) -> dict:
        return {
            "operator": "Limit",
            "count": self.count,
            "estimated_cost": self.estimated_cost,
            "estimated_rows": self.estimated_rows,
            "children": [self.child.to_dict()] if self.child else [],
        }


@dataclass
class DistinctNode(PhysicalNode):
    """Eliminates duplicate tuples using hash set."""
    child: Optional[PhysicalNode] = None

    def __post_init__(self):
        self.node_type = "Distinct"

    def children(self) -> List[PhysicalNode]:
        return [self.child] if self.child else []

    def to_dict(self) -> dict:
        return {
            "operator": "Distinct",
            "estimated_cost": self.estimated_cost,
            "estimated_rows": self.estimated_rows,
            "children": [self.child.to_dict()] if self.child else [],
        }
