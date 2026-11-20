"""
QueryOpt AI — LLM Prompt Templates
==================================
Schema-grounded prompts for translating natural language queries to valid SQL.
"""

from __future__ import annotations

import sqlite3


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

DATA DOMAIN RULES:
- Student.branch uses short codes: 'CSE', 'ECE', 'ME', 'CE', 'MATH'.
  * Electronics / ECE -> 'ECE'
  * Computer Science / CS / CSE -> 'CSE'
  * Mechanical / Mech -> 'ME'
  * Civil -> 'CE'
  * Mathematics / Math -> 'MATH'

COMPILER GRAMMAR CONSTRAINTS (VERY IMPORTANT):
1. ONLY generate standard read-only SELECT statements. Never generate INSERT, UPDATE, DELETE, DROP, or ALTER.
2. Supported syntax:
   - SELECT [DISTINCT] col1, col2, ... (or SELECT *)
   - FROM table [t1]
   - INNER JOIN table2 [t2] ON t1.col = t2.col
   - WHERE condition [AND/OR condition]
   - ORDER BY col [ASC|DESC]
   - LIMIT n
3. DO NOT use aggregations or clauses not supported by the custom compiler:
   - NO GROUP BY, NO HAVING
   - NO COUNT, SUM, AVG, MIN, MAX
   - NO Subqueries or UNION
4. When selecting columns across joins, always qualify with table alias or table name (e.g. s.name, d.dept_name).
5. If the user asks for non-existent attributes (e.g. attendance, fees), do NOT invent them; return an empty sql string and describe the limitation in the explanation.
6. Return your answer ONLY as a raw JSON object with this exact structure (no markdown fences, just JSON):
{{
  "sql": "SELECT ... FROM ... WHERE ... LIMIT ...;",
  "explanation": "Short 1-2 sentence explanation of how the query answers the question",
  "assumptions": ["List of assumptions made"]
}}
"""


def build_system_prompt(conn: sqlite3.Connection) -> str:
    schema_desc = get_schema_description(conn)
    return SYSTEM_PROMPT_TEMPLATE.format(schema_description=schema_desc)


def build_user_prompt(natural_language_query: str) -> str:
    return f"Translate this request into a valid SQL query:\n\"{natural_language_query}\""
