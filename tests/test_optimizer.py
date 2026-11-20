"""
Tests for Logical and Cost-Based Optimizers.
"""

from compiler.parser import SQLParser
from optimizer.cost_optimizer import CostBasedOptimizer
from optimizer.logical_optimizer import LogicalOptimizer
from relational_algebra.converter import ASTToRAConverter
from relational_algebra.nodes import Scan


def test_predicate_pushdown():
    parser = SQLParser()
    converter = ASTToRAConverter()
    optimizer = LogicalOptimizer()

    ast = parser.parse("SELECT name FROM Student WHERE age > 23")
    ra = converter.convert(ast)

    opt_ra, rules = optimizer.optimize(ra)
    rule_names = [r.rule_name for r in rules]

    assert "Predicate Pushdown" in rule_names


def test_cost_based_optimizer(db_connection):
    parser = SQLParser()
    converter = ASTToRAConverter()
    optimizer = LogicalOptimizer()
    cbo = CostBasedOptimizer(db_connection)

    ast = parser.parse("SELECT s.name, d.dept_name FROM Student s JOIN Department d ON s.dept_id = d.dept_id")
    ra = converter.convert(ast)
    opt_ra, _ = optimizer.optimize(ra)

    phys_plan, report = cbo.optimize(opt_ra)
    assert phys_plan is not None
    assert report.optimized_cost > 0
