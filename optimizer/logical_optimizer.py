"""
QueryOpt AI — Logical Optimizer
===============================
Applies relational algebra transformation rules iteratively until reaching a
fixed point, logging each applied rewrite rule with before and after state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from optimizer.rewrite_rules import (
    ConstantFoldingRule,
    PredicatePushdownRule,
    ProjectionPushdownRule,
    RewriteRule,
    SelectionSimplificationRule,
)
from relational_algebra.nodes import RANode


@dataclass
class AppliedRule:
    """Record of a single applied optimization transformation."""

    rule_name: str
    description: str
    before_snippet: str
    after_snippet: str

    def to_dict(self) -> dict:
        return {
            "rule_name": self.rule_name,
            "description": self.description,
            "before_snippet": self.before_snippet,
            "after_snippet": self.after_snippet,
        }


class LogicalOptimizer:
    """Rule-based relational algebra query optimizer."""

    def __init__(self, rules: List[RewriteRule] = None, max_iterations: int = 15):
        self.rules = rules or [
            ConstantFoldingRule(),
            SelectionSimplificationRule(),
            PredicatePushdownRule(),
            ProjectionPushdownRule(),
        ]
        self.max_iterations = max_iterations

    def optimize(self, plan: RANode) -> Tuple[RANode, List[AppliedRule]]:
        """Apply rewrite rules until fixed point or max iterations reached.

        Returns:
            (optimized_plan, list_of_applied_rules)
        """
        current_plan = plan.copy()
        applied_rules: List[AppliedRule] = []

        for _ in range(self.max_iterations):
            any_changed = False
            for rule in self.rules:
                before_str = str(current_plan)
                new_plan, changed = rule.apply(current_plan)
                if changed:
                    after_str = str(new_plan)
                    applied_rules.append(
                        AppliedRule(
                            rule_name=rule.name,
                            description=rule.description,
                            before_snippet=before_str,
                            after_snippet=after_str,
                        )
                    )
                    current_plan = new_plan
                    any_changed = True
                    break  # Restart loop with new tree

            if not any_changed:
                break

        return current_plan, applied_rules
