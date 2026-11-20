"""
QueryOpt AI — Iterator Engine
=============================
Compiles physical execution plan nodes into a tree of executable
Volcano-style iterators and compiles relational predicates into Python functions.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Callable, Dict

from execution.operators import (
    DistinctIterator,
    FilterIterator,
    HashJoinIterator,
    IndexScanIterator,
    LimitIterator,
    NestedLoopJoinIterator,
    ProjectIterator,
    SortIterator,
    TableScanIterator,
    VolcanoIterator,
)
from execution.physical_plan import (
    DistinctNode,
    FilterNode,
    HashJoinNode,
    IndexScanNode,
    LimitNode,
    NestedLoopJoinNode,
    PhysicalNode,
    ProjectNode,
    SortNode,
    TableScanNode,
)
from relational_algebra.nodes import (
    AndCondition,
    ColumnReference,
    LiteralValue,
    OrCondition,
    Predicate,
)


class IteratorEngine:
    """Instantiates a live Volcano iterator tree from a PhysicalNode plan."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def build_iterator_tree(self, plan: PhysicalNode) -> VolcanoIterator:
        """Recursively assemble Volcano iterator operators from a physical plan."""
        if isinstance(plan, TableScanNode):
            return TableScanIterator(self.conn, plan.table_name, plan.alias)

        elif isinstance(plan, IndexScanNode):
            return IndexScanIterator(
                self.conn,
                plan.table_name,
                plan.index_name,
                plan.column,
                plan.op,
                plan.value,
                plan.alias,
            )

        elif isinstance(plan, FilterNode):
            child_it = self.build_iterator_tree(plan.child)
            cond_fn = self.compile_condition(plan.condition)
            return FilterIterator(condition_fn=cond_fn, child=child_it)

        elif isinstance(plan, ProjectNode):
            child_it = self.build_iterator_tree(plan.child)
            return ProjectIterator(columns=plan.columns, child=child_it)

        elif isinstance(plan, HashJoinNode):
            left_it = self.build_iterator_tree(plan.left)
            right_it = self.build_iterator_tree(plan.right)
            return HashJoinIterator(
                left=left_it,
                right=right_it,
                left_key=plan.left_key,
                right_key=plan.right_key,
                build_side=plan.build_side,
            )

        elif isinstance(plan, NestedLoopJoinNode):
            left_it = self.build_iterator_tree(plan.left)
            right_it = self.build_iterator_tree(plan.right)
            cond_fn = self.compile_condition(plan.condition)
            return NestedLoopJoinIterator(left=left_it, right=right_it, condition_fn=cond_fn)

        elif isinstance(plan, SortNode):
            child_it = self.build_iterator_tree(plan.child)
            return SortIterator(order_items=plan.order_items, child=child_it)

        elif isinstance(plan, LimitNode):
            child_it = self.build_iterator_tree(plan.child)
            return LimitIterator(count=plan.count, child=child_it)

        elif isinstance(plan, DistinctNode):
            child_it = self.build_iterator_tree(plan.child)
            return DistinctIterator(child=child_it)

        raise ValueError(f"Unsupported physical node type: {type(plan)}")

    def compile_condition(self, condition: Any) -> Callable[[Dict[str, Any]], bool]:
        """Compile a relational algebra condition into a fast Python boolean evaluator."""
        if isinstance(condition, Predicate):
            op = condition.op

            def eval_pred(row: Dict[str, Any]) -> bool:
                lval = self._eval_val(condition.left, row)
                rval = self._eval_val(condition.right, row)
                if lval is None or rval is None:
                    return False

                # Ensure type compatibility for comparison
                try:
                    if isinstance(lval, (int, float)) and isinstance(rval, (int, float)):
                        pass
                    elif isinstance(lval, str) or isinstance(rval, str):
                        lval = str(lval)
                        rval = str(rval)
                except Exception:
                    pass

                if op == "=":
                    return lval == rval
                elif op in ("!=", "<>"):
                    return lval != rval
                elif op == "<":
                    return lval < rval
                elif op == ">":
                    return lval > rval
                elif op == "<=":
                    return lval <= rval
                elif op == ">=":
                    return lval >= rval
                return False

            return eval_pred

        elif isinstance(condition, AndCondition):
            evals = [self.compile_condition(c) for c in condition.conditions]
            return lambda row: all(fn(row) for fn in evals)

        elif isinstance(condition, OrCondition):
            evals = [self.compile_condition(c) for c in condition.conditions]
            return lambda row: any(fn(row) for fn in evals)

        # Default always true
        return lambda row: True

    def _eval_val(self, val_expr: Any, row: Dict[str, Any]) -> Any:
        if isinstance(val_expr, LiteralValue):
            return val_expr.value
        elif isinstance(val_expr, ColumnReference):
            col_name = val_expr.name
            tbl = val_expr.table

            if tbl:
                q1 = f"{tbl}.{col_name}"
                q2 = f"{tbl.lower()}.{col_name.lower()}"
                if q1 in row:
                    return row[q1]
                if q2 in row:
                    return row[q2]

            # Try bare column
            if col_name in row:
                return row[col_name]
            col_lower = col_name.lower()
            if col_lower in row:
                return row[col_lower]

            for k, v in row.items():
                if k.lower() == col_lower or k.lower().endswith(f".{col_lower}"):
                    return v

            return None
        return val_expr
