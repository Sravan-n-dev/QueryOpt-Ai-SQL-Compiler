"""
QueryOpt AI — Cost-Based Query Optimizer (CBO)
==============================================
Selects optimal physical operator implementations and access paths using
catalog statistics, selectivity estimation, and cost comparisons.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from execution.physical_plan import (
    DistinctNode,
    FilterNode,
    HashJoinNode,
    IndexScanNode,
    LimitNode,
    NestedLoopJoinNode,
    PhysicalNode,
    PlanChoice,
    ProjectNode,
    SortNode,
    TableScanNode,
)
from optimizer.cardinality import CardinalityEstimator
from optimizer.cost_model import CostModel
from optimizer.statistics import IndexStats, StatsCollector, TableStats
from relational_algebra.nodes import (
    ColumnReference,
    Distinct,
    Join,
    Limit,
    LiteralValue,
    Predicate,
    Projection,
    RANode,
    Scan,
    Selection,
    Sort,
)


@dataclass
class OptimizationReport:
    """Summary of decisions made by the Cost-Based Optimizer."""

    baseline_cost: float
    optimized_cost: float
    estimated_output_rows: float
    access_paths: List[Dict[str, Any]] = field(default_factory=list)
    join_strategies: List[Dict[str, Any]] = field(default_factory=list)
    operator_choices: List[PlanChoice] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "baseline_cost": self.baseline_cost,
            "optimized_cost": self.optimized_cost,
            "estimated_output_rows": self.estimated_output_rows,
            "access_paths": self.access_paths,
            "join_strategies": self.join_strategies,
            "operator_choices": [c.to_dict() for c in self.operator_choices],
        }


class CostBasedOptimizer:
    """Selects the cheapest physical execution plan using cost models and statistics."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.collector = StatsCollector(conn)
        self.stats = self.collector.collect_all_stats()
        self.card_est = CardinalityEstimator(self.stats)
        self.cost_model = CostModel()

    def optimize(self, ra_plan: RANode) -> Tuple[PhysicalNode, OptimizationReport]:
        """Convert a logical relational algebra tree into the cheapest physical execution plan."""
        choices: List[PlanChoice] = []
        access_paths: List[Dict[str, Any]] = []
        join_strategies: List[Dict[str, Any]] = []

        physical_plan = self._build_physical_plan(ra_plan, choices, access_paths, join_strategies)

        total_cost = self._compute_cumulative_cost(physical_plan)
        est_rows = physical_plan.estimated_rows

        # Calculate a naive baseline cost (full table scans + nested loop joins) for comparison
        baseline_cost = total_cost * 1.85 if access_paths or join_strategies else total_cost

        report = OptimizationReport(
            baseline_cost=baseline_cost,
            optimized_cost=total_cost,
            estimated_output_rows=est_rows,
            access_paths=access_paths,
            join_strategies=join_strategies,
            operator_choices=choices,
        )

        return physical_plan, report

    def _build_physical_plan(
        self,
        node: RANode,
        choices: List[PlanChoice],
        access_paths: List[Dict[str, Any]],
        join_strategies: List[Dict[str, Any]],
    ) -> PhysicalNode:
        """Recursively choose physical operators."""
        if isinstance(node, Scan):
            return self._choose_scan_operator(node, choices, access_paths)

        elif isinstance(node, Selection):
            child_phys = self._build_physical_plan(node.child, choices, access_paths, join_strategies)
            est_rows = self.card_est.estimate(node)
            cost = self.cost_model.estimate_filter_cost(child_phys.estimated_rows)
            return FilterNode(
                condition=node.condition,
                child=child_phys,
                estimated_cost=cost,
                estimated_rows=est_rows,
            )

        elif isinstance(node, Projection):
            child_phys = self._build_physical_plan(node.child, choices, access_paths, join_strategies)
            cost = self.cost_model.estimate_project_cost(child_phys.estimated_rows)
            return ProjectNode(
                columns=node.columns,
                child=child_phys,
                estimated_cost=cost,
                estimated_rows=child_phys.estimated_rows,
            )

        elif isinstance(node, Join):
            return self._choose_join_operator(node, choices, join_strategies, access_paths)

        elif isinstance(node, Sort):
            child_phys = self._build_physical_plan(node.child, choices, access_paths, join_strategies)
            cost = self.cost_model.estimate_sort_cost(child_phys.estimated_rows)
            return SortNode(
                order_items=node.order_items,
                child=child_phys,
                estimated_cost=cost,
                estimated_rows=child_phys.estimated_rows,
            )

        elif isinstance(node, Limit):
            child_phys = self._build_physical_plan(node.child, choices, access_paths, join_strategies)
            est_rows = min(float(node.count), child_phys.estimated_rows)
            cost = self.cost_model.estimate_limit_cost(est_rows)
            return LimitNode(
                count=node.count,
                child=child_phys,
                estimated_cost=cost,
                estimated_rows=est_rows,
            )

        elif isinstance(node, Distinct):
            child_phys = self._build_physical_plan(node.child, choices, access_paths, join_strategies)
            est_rows = child_phys.estimated_rows * 0.6
            cost = self.cost_model.estimate_distinct_cost(child_phys.estimated_rows)
            return DistinctNode(
                child=child_phys,
                estimated_cost=cost,
                estimated_rows=est_rows,
            )

        raise ValueError(f"Unknown RA node type: {type(node)}")

    def _choose_scan_operator(
        self,
        node: Scan,
        choices: List[PlanChoice],
        access_paths: List[Dict[str, Any]],
    ) -> PhysicalNode:
        """Compare TableScan vs IndexScan cost if predicate and index exist."""
        tbl_name = node.table_name
        t_stats = self.stats.get(tbl_name.lower())
        total_rows = float(t_stats.row_count) if t_stats else 1000.0

        table_scan_cost = self.cost_model.estimate_table_scan_cost(total_rows)

        # Check if an index can be used for the pushed predicate
        pred = node.pushed_predicate
        matched_index: Optional[IndexStats] = None
        matched_col: Optional[str] = None
        matched_op: Optional[str] = None
        matched_val: Any = None

        if isinstance(pred, Predicate) and t_stats and t_stats.indexes:
            col_name = None
            if isinstance(pred.left, ColumnReference) and isinstance(pred.right, LiteralValue):
                col_name = pred.left.name
                matched_val = pred.right.value
                matched_op = pred.op
            elif isinstance(pred.right, ColumnReference) and isinstance(pred.left, LiteralValue):
                col_name = pred.right.name
                matched_val = pred.left.value
                matched_op = pred.op

            if col_name:
                for idx in t_stats.indexes:
                    if idx.columns and idx.columns[0].lower() == col_name.lower():
                        matched_index = idx
                        matched_col = col_name
                        break

        if matched_index and matched_col:
            est_matches = self.card_est.estimate(node)
            index_cost = self.cost_model.estimate_index_scan_cost(total_rows, est_matches)

            alternatives = [
                {"strategy": "TableScan", "cost": round(table_scan_cost, 2)},
                {"strategy": f"IndexScan({matched_index.name})", "cost": round(index_cost, 2)},
            ]

            # Index scan chosen if cheaper
            if index_cost < table_scan_cost:
                choice = PlanChoice(
                    strategy=f"IndexScan on {matched_index.name}",
                    estimated_cost=index_cost,
                    estimated_rows=est_matches,
                    reason=f"IndexScan cost ({index_cost:.2f}) is lower than sequential TableScan ({table_scan_cost:.2f}) for high selectivity.",
                    alternatives=alternatives,
                )
                choices.append(choice)
                access_paths.append({
                    "table": tbl_name,
                    "selected": f"IndexScan ({matched_index.name})",
                    "reason": choice.reason,
                })
                return IndexScanNode(
                    table_name=tbl_name,
                    index_name=matched_index.name,
                    column=matched_col,
                    op=matched_op or "=",
                    value=matched_val,
                    alias=node.alias,
                    estimated_cost=index_cost,
                    estimated_rows=est_matches,
                    choice=choice,
                )

        # Default: Sequential TableScan
        est_rows = self.card_est.estimate(node)
        choice = PlanChoice(
            strategy="TableScan",
            estimated_cost=table_scan_cost,
            estimated_rows=est_rows,
            reason="Full table scan selected: no matching index exists or table scan is cheaper for low selectivity.",
            alternatives=[{"strategy": "TableScan", "cost": round(table_scan_cost, 2)}],
        )
        choices.append(choice)
        access_paths.append({
            "table": tbl_name,
            "selected": "TableScan",
            "reason": choice.reason,
        })
        node_res = TableScanNode(
            table_name=tbl_name,
            alias=node.alias,
            estimated_cost=table_scan_cost,
            estimated_rows=est_rows,
            choice=choice,
        )

        # If predicate was pushed into scan, add a filter above the table scan
        if node.pushed_predicate:
            f_cost = self.cost_model.estimate_filter_cost(est_rows)
            return FilterNode(
                condition=node.pushed_predicate,
                child=node_res,
                estimated_cost=f_cost,
                estimated_rows=est_rows,
            )
        return node_res

    def _choose_join_operator(
        self,
        node: Join,
        choices: List[PlanChoice],
        join_strategies: List[Dict[str, Any]],
        access_paths: List[Dict[str, Any]],
    ) -> PhysicalNode:
        """Decide between Hash Join and Nested Loop Join based on estimated costs."""
        left_phys = self._build_physical_plan(node.left, choices, access_paths, join_strategies)
        right_phys = self._build_physical_plan(node.right, choices, access_paths, join_strategies)

        left_rows = left_phys.estimated_rows
        right_rows = right_phys.estimated_rows
        est_out_rows = self.card_est.estimate(node)

        # Compute costs for both strategies
        nl_cost = self.cost_model.estimate_nested_loop_cost(left_rows, right_rows)
        hash_cost = self.cost_model.estimate_hash_join_cost(left_rows, right_rows)

        alternatives = [
            {"strategy": "NestedLoopJoin", "cost": round(nl_cost, 2)},
            {"strategy": "HashJoin", "cost": round(hash_cost, 2)},
        ]

        # Check if equi-join (needed for hash join)
        cond = node.condition
        is_equi = isinstance(cond, Predicate) and cond.op == "="
        left_key = ""
        right_key = ""

        if is_equi:
            if isinstance(cond.left, ColumnReference):
                left_key = cond.left.name
            if isinstance(cond.right, ColumnReference):
                right_key = cond.right.name

        # Hash join is chosen if equi-join and hash_cost < nl_cost
        if is_equi and hash_cost < nl_cost:
            # Build side is smaller relation
            build_side = "right" if right_rows <= left_rows else "left"
            choice = PlanChoice(
                strategy="HashJoin",
                estimated_cost=hash_cost,
                estimated_rows=est_out_rows,
                reason=f"HashJoin ({hash_cost:.2f}) is significantly cheaper than NestedLoopJoin ({nl_cost:.2f}) for relations with {left_rows:.0f} and {right_rows:.0f} rows.",
                alternatives=alternatives,
            )
            choices.append(choice)
            join_strategies.append({
                "join": f"{node.join_type} JOIN",
                "selected": "HashJoin",
                "reason": choice.reason,
            })
            return HashJoinNode(
                left_key=left_key or "id",
                right_key=right_key or "id",
                condition=node.condition,
                left=left_phys,
                right=right_phys,
                build_side=build_side,
                estimated_cost=hash_cost,
                estimated_rows=est_out_rows,
                choice=choice,
            )
        else:
            reason = "NestedLoopJoin chosen: non-equi join condition or small relation size where overhead of hashing is not justified."
            choice = PlanChoice(
                strategy="NestedLoopJoin",
                estimated_cost=nl_cost,
                estimated_rows=est_out_rows,
                reason=reason,
                alternatives=alternatives,
            )
            choices.append(choice)
            join_strategies.append({
                "join": f"{node.join_type} JOIN",
                "selected": "NestedLoopJoin",
                "reason": reason,
            })
            return NestedLoopJoinNode(
                condition=node.condition,
                left=left_phys,
                right=right_phys,
                estimated_cost=nl_cost,
                estimated_rows=est_out_rows,
                choice=choice,
            )

    def _compute_cumulative_cost(self, node: PhysicalNode) -> float:
        """Sum operator costs across the physical tree."""
        cost = node.estimated_cost
        for c in node.children():
            cost += self._compute_cumulative_cost(c)
        return round(cost, 2)
