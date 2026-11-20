"""
QueryOpt AI — Test Configuration and Fixtures
=============================================
Provides clean in-memory database fixtures, lexer, parser, and pipeline fixtures.
"""

import sqlite3
import pytest
from pathlib import Path

from compiler.lexer import SQLLexer
from compiler.parser import SQLParser
from compiler.semantic_analyzer import SemanticAnalyzer
from database.seed import seed_database
from pipeline import QueryPipeline


@pytest.fixture
def db_connection():
    """In-memory SQLite database initialized with schema and seed data."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    # Load schema.sql
    schema_path = Path(__file__).resolve().parent.parent / "database" / "schema.sql"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    conn.executescript(schema_sql)
    seed_database(conn)
    conn.commit()

    yield conn
    conn.close()


@pytest.fixture
def lexer():
    return SQLLexer()


@pytest.fixture
def parser():
    return SQLParser()


@pytest.fixture
def semantic_analyzer(db_connection):
    return SemanticAnalyzer(db_connection)


@pytest.fixture
def test_pipeline(db_connection):
    return QueryPipeline(conn=db_connection)
