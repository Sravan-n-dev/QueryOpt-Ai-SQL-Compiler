"""
QueryOpt AI — Logical Optimizer Rewrite Rules
==============================================
Implementation of relational algebra transformation rules that guarantee
semantic equivalence while moving selections and projections closer to leaves.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, List, Optional, Set, Tuple

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


def extract_referenced_tables_and_columns(cond: Any) -> Tuple[Set[str], Set[str]]:
    """Extract table names/aliases and column names referenced in a condition."""
    tables: Set[str] = set()
    cols: Set[str] = set()

    if isinstance(cond, ColumnReference):
        cols.add(cond.name.lower())
        if cond.table:
            tables.add(cond.table.lower())
    elif isinstance(cond, Predicate):
        t1, c1 = extract_referenced_tables_and_columns(cond.left)
        t2, c2 = extract_referenced_tables_and_columns(cond.right)
        tables.update(t1)
        tables.update(t2)
        cols.update(c1)
        cols.update(c2)
    elif isinstance(cond, (AndCondition, OrCondition)):
        for c in cond.conditions:
            t, col = extract_referenced_tables_and_columns(c)
            tables.update(t)
            cols.update(col)

    return tables, cols


def get_subtree_tables(node: RANode) -> Set[str]:
    """Get all table names and aliases available in a subtree."""
    tables: Set[str] = set()
    if isinstance(node, Scan):
        tables.add(node.table_name.lower())
        if node.alias:
            tables.add(node.alias.lower())
    for child in node.children():
        tables.update(get_subtree_tables(child))
    return tables


class RewriteRule(ABC):
    """Abstract base class for all logical optimization rewrite rules."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the optimization rule."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of why and how the rule transforms the query."""

    @abstractmethod
    def apply(self, node: RANode) -> Tuple[RANode, bool]:
        """Apply rule to the node. Returns (new_node, changed_boolean)."""


class ConstantFoldingRule(RewriteRule):
    """Evaluates constant conditions at compile time (e.g. 1 = 1, 23 > 10)."""

    @property
    def name(self) -> str:
        return "Constant Folding"

    @property
    def description(self) -> str:
        return "Evaluates compile-time constant expressions and eliminates always-true conditions."

    def apply(self, node: RANode) -> Tuple[RANode, bool]:
        changed = False

        # Recursively apply to children first
        if isinstance(node, Selection):
            cond = node.condition
            if isinstance(cond, Predicate):
                if isinstance(cond.left, LiteralValue) and isinstance(cond.right, LiteralValue):
                    # Compile-time evaluation
                    lval = cond.left.value
                    rval = cond.right.value
                    op = cond.op
                    is_true = False
                    if op == "=":
                        is_true = (lval == rval)
                    elif op in ("!=", "<>"):
                        is_true = (lval != rval)
                    elif op == "<":
                        is_true = (lval < rval)
                    elif op == ">":
                        is_true = (lval > rval)
                    elif op == "<=":
                        is_true = (lval <= rval)
                    elif op == ">=":
                        is_true = (lval >= rval)

                    if is_true:
                        # Always true filter can be eliminated
                        return node.child, True

        # Process children
        new_children = []
        for child in node.children():
            new_child, ch = self.apply(child)
            new_children.append(new_child)
            if ch:
                changed = True

        if changed:
            if isinstance(node, Selection):
                node = Selection(condition=node.condition, child=new_children[0])
            elif isinstance(node, Projection):
                node = Projection(columns=node.columns, child=new_children[0])
            elif isinstance(node, Join):
                node = Join(join_type=node.join_type, condition=node.condition, left=new_children[0], right=new_children[1])
            elif isinstance(node, Sort):
                node = Sort(order_items=node.order_items, child=new_children[0])
            elif isinstance(node, Limit):
                node = Limit(count=node.count, child=new_children[0])
            elif isinstance(node, Distinct):
                node = Distinct(child=new_children[0])

        return node, changed


class SelectionSimplificationRule(RewriteRule):
    """Splits conjunctive (AND) selection into cascading individual selections:
    σ(A AND B) -> σ(A)(σ(B))
    """

    @property
    def name(self) -> str:
        return "Selection Simplification"

    @property
    def description(self) -> str:
        return "Splits complex AND conditions into independent selection filters for modular pushdown."

    def apply(self, node: RANode) -> Tuple[RANode, bool]:
        if isinstance(node, Selection) and isinstance(node.condition, AndCondition):
            conds = node.condition.conditions
            if len(conds) > 1:
                curr = node.child
                for c in reversed(conds):
                    curr = Selection(condition=c, child=curr)
                return curr, True

        # Recursively check children
        changed = False
        new_children = []
        for ch in node.children():
            new_ch, modified = self.apply(ch)
            new_children.append(new_ch)
            if modified:
                changed = True

        if changed:
            if isinstance(node, Selection):
                return Selection(condition=node.condition, child=new_children[0]), True
            elif isinstance(node, Projection):
                return Projection(columns=node.columns, child=new_children[0]), True
            elif isinstance(node, Join):
                return Join(join_type=node.join_type, condition=node.condition, left=new_children[0], right=new_children[1]), True
            elif isinstance(node, Sort):
                return Sort(order_items=node.order_items, child=new_children[0]), True
            elif isinstance(node, Limit):
                return Limit(count=node.count, child=new_children[0]), True
            elif isinstance(node, Distinct):
                return Distinct(child=new_children[0]), True

        return node, False


class PredicatePushdownRule(RewriteRule):
    """Pushes Selection (σ) operators down past Projections, Joins, and directly into Scans."""

    @property
    def name(self) -> str:
        return "Predicate Pushdown"

    @property
    def description(self) -> str:
        return "Moves filtering operations below joins and projections, reducing intermediate relation size as early as possible."

    def apply(self, node: RANode) -> Tuple[RANode, bool]:
        # Case 1: Selection over Projection: σ_p(π_c(R)) -> π_c(σ_p(R))
        if isinstance(node, Selection) and isinstance(node.child, Projection):
            proj = node.child
            # We can push selection below projection if the projection includes all columns needed by condition
            _, cond_cols = extract_referenced_tables_and_columns(node.condition)
            proj_cols_clean = {c.split(".")[-1].lower() for c in proj.columns if c != "*"}

            # If it's a wildcard * or all condition columns are projected:
            if "*" in proj.columns or cond_cols.issubset(proj_cols_clean):
                new_sel = Selection(condition=node.condition, child=proj.child)
                new_proj = Projection(columns=proj.columns, child=new_sel)
                return new_proj, True

        # Case 2: Selection over Join: σ_p(Left ⋈ Right)
        if isinstance(node, Selection) and isinstance(node.child, Join):
            join_node = node.child
            left_tables = get_subtree_tables(join_node.left)
            right_tables = get_subtree_tables(join_node.right)

            cond_tables, _ = extract_referenced_tables_and_columns(node.condition)

            # If condition refers ONLY to left subtree tables:
            if cond_tables and cond_tables.issubset(left_tables) and not cond_tables.intersection(right_tables):
                new_left = Selection(condition=node.condition, child=join_node.left)
                new_join = Join(
                    join_type=join_node.join_type,
                    condition=join_node.condition,
                    left=new_left,
                    right=join_node.right,
                )
                return new_join, True

            # If condition refers ONLY to right subtree tables:
            if cond_tables and cond_tables.issubset(right_tables) and not cond_tables.intersection(left_tables):
                new_right = Selection(condition=node.condition, child=join_node.right)
                new_join = Join(
                    join_type=join_node.join_type,
                    condition=join_node.condition,
                    left=join_node.left,
                    right=new_right,
                )
                return new_join, True

        # Case 3: Selection over Scan: σ_p(Scan(T)) -> Scan(T, predicate=p)
        if isinstance(node, Selection) and isinstance(node.child, Scan):
            scan_node = node.child
            if scan_node.pushed_predicate is None:
                new_scan = Scan(
                    table_name=scan_node.table_name,
                    alias=scan_node.alias,
                    pushed_predicate=node.condition,
                )
                return new_scan, True

        # Recursively apply to children
        changed = False
        new_children = []
        for ch in node.children():
            new_ch, modified = self.apply(ch)
            new_children.append(new_ch)
            if modified:
                changed = True

        if changed:
            if isinstance(node, Selection):
                return Selection(condition=node.condition, child=new_children[0]), True
            elif isinstance(node, Projection):
                return Projection(columns=node.columns, child=new_children[0]), True
            elif isinstance(node, Join):
                return Join(join_type=node.join_type, condition=node.condition, left=new_children[0], right=new_children[1]), True
            elif isinstance(node, Sort):
                return Sort(order_items=node.order_items, child=new_children[0]), True
            elif isinstance(node, Limit):
                return Limit(count=node.count, child=new_children[0]), True
            elif isinstance(node, Distinct):
                return Distinct(child=new_children[0]), True

        return node, False


class ProjectionPushdownRule(RewriteRule):
    """Pushes Projection (π) down past Joins so only necessary attributes are carried forward."""

    @property
    def name(self) -> str:
        return "Projection Pushdown"

    @property
    def description(self) -> str:
        return "Filters out unused columns before relational joins, preserving only columns required for joins and outputs."

    def apply(self, node: RANode) -> Tuple[RANode, bool]:
        # π_C(Left ⋈_cond Right) -> push relevant column projections to left and right
        if isinstance(node, Projection) and isinstance(node.child, Join):
            # If projection is not "*", we can prune
            if "*" not in node.columns:
                join_node = node.child
                left_tables = get_subtree_tables(join_node.left)
                right_tables = get_subtree_tables(join_node.right)

                # Find columns needed by join condition
                _, join_cols = extract_referenced_tables_and_columns(join_node.condition)

                # Columns for left side: projected columns from left + join condition columns from left
                left_cols: List[str] = []
                right_cols: List[str] = []

                for c in node.columns:
                    parts = c.split(".")
                    tbl = parts[0].lower() if len(parts) > 1 else None
                    if tbl and tbl in left_tables:
                        left_cols.append(c)
                    elif tbl and tbl in right_tables:
                        right_cols.append(c)
                    else:
                        left_cols.append(c)
                        right_cols.append(c)

                # Ensure join columns are preserved
                for jc in join_cols:
                    left_cols.append(jc)
                    right_cols.append(jc)

                # Only rewrite if not already projected
                if not isinstance(join_node.left, Projection) and not isinstance(join_node.right, Projection):
                    new_left = Projection(columns=list(set(left_cols)), child=join_node.left) if left_cols else join_node.left
                    new_right = Projection(columns=list(set(right_cols)), child=join_node.right) if right_cols else join_node.right
                    new_join = Join(
                        join_type=join_node.join_type,
                        condition=join_node.condition,
                        left=new_left,
                        right=new_right,
                    )
                    return Projection(columns=node.columns, child=new_join), True

        # Recursively apply to children
        changed = False
        new_children = []
        for ch in node.children():
            new_ch, modified = self.apply(ch)
            new_children.append(new_ch)
            if modified:
                changed = True

        if changed:
            if isinstance(node, Selection):
                return Selection(condition=node.condition, child=new_children[0]), True
            elif isinstance(node, Projection):
                return Projection(columns=node.columns, child=new_children[0]), True
            elif isinstance(node, Join):
                return Join(join_type=node.join_type, condition=node.condition, left=new_children[0], right=new_children[1]), True
            elif isinstance(node, Sort):
                return Sort(order_items=node.order_items, child=new_children[0]), True
            elif isinstance(node, Limit):
                return Limit(count=node.count, child=new_children[0]), True
            elif isinstance(node, Distinct):
                return Distinct(child=new_children[0]), True

        return node, False
