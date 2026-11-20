"""
QueryOpt AI — Cardinality Estimator
===================================
Calculates estimated output tuple counts for relational algebra nodes
using selectivity formulas and catalog statistics.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from optimizer.statistics import TableStats
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


class CardinalityEstimator:
    """Estimates output cardinality for relational algebra trees."""

    def __init__(self, stats: Dict[str, TableStats]):
        self.stats = stats

    def estimate(self, node: RANode) -> float:
        """Estimate the number of rows produced by a given node."""
        if isinstance(node, Scan):
            tbl = node.table_name.lower()
            t_stats = self.stats.get(tbl)
            base_rows = float(t_stats.row_count) if t_stats else 1000.0

            if node.pushed_predicate:
                sel = self.estimate_selectivity(node.pushed_predicate, t_stats)
                return max(1.0, base_rows * sel)
            return max(1.0, base_rows)

        elif isinstance(node, Selection):
            child_rows = self.estimate(node.child)
            # Find primary table if available
            t_stats = self._find_underlying_table_stats(node.child)
            sel = self.estimate_selectivity(node.condition, t_stats)
            return max(1.0, child_rows * sel)

        elif isinstance(node, Projection):
            return self.estimate(node.child)

        elif isinstance(node, Join):
            left_rows = self.estimate(node.left)
            right_rows = self.estimate(node.right)

            left_stats = self._find_underlying_table_stats(node.left)
            right_stats = self._find_underlying_table_stats(node.right)

            # Check if condition is equality between join keys
            cond = node.condition
            if isinstance(cond, Predicate) and cond.op == "=":
                distinct_left = 10
                distinct_right = 10

                if isinstance(cond.left, ColumnReference) and left_stats:
                    c = left_stats.column_stats.get(cond.left.name.lower())
                    if c:
                        distinct_left = c.num_distinct
                if isinstance(cond.right, ColumnReference) and right_stats:
                    c = right_stats.column_stats.get(cond.right.name.lower())
                    if c:
                        distinct_right = c.num_distinct

                denom = max(1.0, float(max(distinct_left, distinct_right)))
                return max(1.0, (left_rows * right_rows) / denom)

            # Default cross product or non-equi join selectivity
            return max(1.0, left_rows * right_rows * 0.1)

        elif isinstance(node, Sort):
            return self.estimate(node.child)

        elif isinstance(node, Limit):
            child_rows = self.estimate(node.child)
            return min(float(node.count), child_rows)

        elif isinstance(node, Distinct):
            child_rows = self.estimate(node.child)
            return max(1.0, child_rows * 0.6)

        return 100.0

    def estimate_selectivity(self, condition: Any, t_stats: Optional[TableStats]) -> float:
        """Estimate the selectivity fraction [0.0, 1.0] of a condition."""
        if isinstance(condition, Predicate):
            op = condition.op
            col_name = None
            lit_val = None

            if isinstance(condition.left, ColumnReference) and isinstance(condition.right, LiteralValue):
                col_name = condition.left.name.lower()
                lit_val = condition.right.value
            elif isinstance(condition.right, ColumnReference) and isinstance(condition.left, LiteralValue):
                col_name = condition.right.name.lower()
                lit_val = condition.left.value

            if col_name and t_stats and col_name in t_stats.column_stats:
                col_stat = t_stats.column_stats[col_name]
                if op == "=":
                    return 1.0 / max(1, col_stat.num_distinct)
                elif op in ("!=", "<>"):
                    return 1.0 - (1.0 / max(1, col_stat.num_distinct))
                elif op in (">", ">=", "<", "<="):
                    # Range interpolation if min/max numeric values exist
                    if (
                        col_stat.min_val is not None
                        and col_stat.max_val is not None
                        and isinstance(lit_val, (int, float))
                        and isinstance(col_stat.min_val, (int, float))
                        and isinstance(col_stat.max_val, (int, float))
                        and col_stat.max_val > col_stat.min_val
                    ):
                        if op in (">", ">="):
                            frac = (col_stat.max_val - lit_val) / (col_stat.max_val - col_stat.min_val)
                            return max(0.01, min(0.99, frac))
                        else:
                            frac = (lit_val - col_stat.min_val) / (col_stat.max_val - col_stat.min_val)
                            return max(0.01, min(0.99, frac))
                    return 0.33

            # Default heuristic selectivities
            if op == "=":
                return 0.1
            elif op in ("!=", "<>"):
                return 0.9
            return 0.33

        elif isinstance(condition, AndCondition):
            sel = 1.0
            for c in condition.conditions:
                sel *= self.estimate_selectivity(c, t_stats)
            return max(0.001, sel)

        elif isinstance(condition, OrCondition):
            sel = 0.0
            for c in condition.conditions:
                s = self.estimate_selectivity(c, t_stats)
                sel = sel + s - (sel * s)
            return min(1.0, sel)

        return 0.5

    def _find_underlying_table_stats(self, node: RANode) -> Optional[TableStats]:
        if isinstance(node, Scan):
            return self.stats.get(node.table_name.lower())
        for c in node.children():
            res = self._find_underlying_table_stats(c)
            if res:
                return res
        return None
