"""
Tests for the SQL Parser & AST construction.
"""

import pytest
from compiler.ast_nodes import SelectStatement
from compiler.diagnostics import ParseError
from compiler.parser import SQLParser


def test_parse_simple_select(parser):
    ast = parser.parse("SELECT * FROM Student")
    assert isinstance(ast, SelectStatement)
    assert len(ast.from_clause) == 1
    assert ast.from_clause[0].name.lower() == "student"


def test_parse_where_and_order_by_limit(parser):
    ast = parser.parse("SELECT name, age FROM Student WHERE age > 23 ORDER BY cgpa DESC LIMIT 5")
    assert isinstance(ast, SelectStatement)
    assert len(ast.columns) == 2
    assert ast.where_clause is not None
    assert ast.order_by is not None
    assert ast.limit is not None
    assert ast.limit.count == 5


def test_parse_join(parser):
    ast = parser.parse("SELECT s.name, d.dept_name FROM Student s INNER JOIN Department d ON s.dept_id = d.dept_id")
    assert isinstance(ast, SelectStatement)
    assert len(ast.joins) == 1
    assert ast.joins[0].table.name.lower() == "department"


def test_parse_syntax_error(parser):
    with pytest.raises(ParseError):
        parser.parse("SELECT FROM Student")
