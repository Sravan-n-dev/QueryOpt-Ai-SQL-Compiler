"""
Tests for the SQL Lexer.
"""

import pytest
from compiler.diagnostics import LexerError
from compiler.lexer import SQLLexer


def test_simple_select_tokens(lexer):
    tokens = lexer.tokenize("SELECT name, age FROM Student")
    types = [t.type for t in tokens]
    assert "SELECT" in types
    assert "FROM" in types
    assert len(tokens) >= 5


def test_where_clause_tokens(lexer):
    tokens = lexer.tokenize("SELECT * FROM Student WHERE age > 23 AND branch = 'ECE'")
    types = [t.type for t in tokens]
    assert "WHERE" in types
    assert "AND" in types
    assert "COMP_OP" in types
    assert "SQ_STRING" in types


def test_numeric_literals(lexer):
    tokens = lexer.tokenize("SELECT * FROM Student WHERE cgpa >= 8.5 AND age = 21")
    values = [t.value for t in tokens]
    assert "8.5" in values
    assert "21" in values


def test_invalid_character(lexer):
    with pytest.raises(LexerError):
        lexer.tokenize("SELECT # FROM Student")
