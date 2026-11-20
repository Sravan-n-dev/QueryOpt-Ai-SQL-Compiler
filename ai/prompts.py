"""
QueryOpt AI — LLM Prompt Templates
==================================
Schema-grounded prompts for translating natural language queries to valid SQL.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict


def get_schema_description(conn: sqlite3.Connection) -> str:
    """Generate a clean schema representation for prompt injection."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [r[0] for r in cursor.fetchall()]

    lines = []
    for tbl in tables:
        cursor.execute(f"PRAGMA table_info('{tbl}')")
        cols = cursor.fetchall()
        col_strs = [f"{c[1]} ({c[2]})" for c in cols]

        # Foreign keys
        cursor.execute(f"PRAGMA foreign_key_list('{tbl}')")
        fks = cursor.fetchall()
        fk_strs = [f"FOREIGN KEY ({f[3]}) REFERENCES {f[2]}({f[4]})" for f in fks]

        tbl_desc = f"Table: {tbl}\n  Columns: {', '.join(col_strs)}"
        if fk_strs:
            tbl_desc += f"\n  Relationships: {'; '.join(fk_strs)}"
        lines.append(tbl_desc)

    return "\n\n".join(lines)


SYSTEM_PROMPT_TEMPLATE = """You are an expert SQL Compiler assistant for QueryOpt AI.
Your task is to translate an English question into a syntactically and semantically valid SQL SELECT query based STRICTLY on the College Database schema below.

DATABASE SCHEMA:
{schema_description}

SUPPORTED SQL GRAMMAR & CONSTRAINTS:
1. ONLY generate read-only SELECT statements. Never generate INSERT, UPDATE, DELETE, DROP, or ALTER.
2. Supported features: SELECT, SELECT *, FROM, WHERE, AND, OR, parentheses, INNER JOIN, JOIN ON, ORDER BY (ASC/DESC), LIMIT, DISTINCT.
3. Use exact table names and column names from the schema above. Do NOT invent columns or tables.
4. If the user asks for information not present in the schema (e.g. attendance, fees), do NOT hallucinate columns; state the limitation in assumptions.
5. Return your answer ONLY as a JSON object with this exact structure:
{{
  "sql": "SELECT ...",
  "explanation": "Short 1-2 sentence explanation of how the query answers the question",
  "assumptions": ["List of assumptions or empty list"]
}}
"""


def build_system_prompt(conn: sqlite3.Connection) -> str:
    schema_desc = get_schema_description(conn)
    return SYSTEM_PROMPT_TEMPLATE.format(schema_description=schema_desc)


def build_user_prompt(natural_language_query: str) -> str:
    return f"Translate this request into a valid SQL query:\n\"{natural_language_query}\""
