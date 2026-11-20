"""
Tests for Semantic Analysis.
"""

import pytest
from compiler.diagnostics import SemanticError
from compiler.parser import SQLParser
from compiler.semantic_analyzer import SemanticAnalyzer


def test_valid_semantic_query(db_connection):
    parser = SQLParser()
    analyzer = SemanticAnalyzer(db_connection)

    ast = parser.parse("SELECT s.name, s.age FROM Student s WHERE s.age > 20")
    validated = analyzer.analyze(ast)
    assert validated is not None


def test_invalid_table_error(db_connection):
    parser = SQLParser()
    analyzer = SemanticAnalyzer(db_connection)

    ast = parser.parse("SELECT * FROM NonExistentTable")
    with pytest.raises(SemanticError) as exc_info:
        analyzer.analyze(ast)
    assert "NonExistentTable" in str(exc_info.value)


def test_invalid_column_error(db_connection):
    parser = SQLParser()
    analyzer = SemanticAnalyzer(db_connection)

    ast = parser.parse("SELECT fake_column FROM Student")
    with pytest.raises(SemanticError) as exc_info:
        analyzer.analyze(ast)
    assert "fake_column" in str(exc_info.value)
