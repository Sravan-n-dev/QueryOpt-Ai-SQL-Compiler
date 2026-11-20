"""Database catalog / statistics collector.

Every statistic is derived from live SQL queries against the database —
nothing is hardcoded.
"""

import sqlite3
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Data-classes
# ---------------------------------------------------------------------------

@dataclass
class ColumnInfo:
    """Per-column statistics."""

    name: str
    data_type: str
    num_distinct: int
    min_val: Any
    max_val: Any
    null_count: int


@dataclass
class IndexInfo:
    """Metadata for a single index."""

    name: str
    table_name: str
    columns: List[str]
    is_unique: bool


@dataclass
class CatalogStats:
    """Aggregated statistics for one table."""

    table_name: str
    row_count: int
    columns: List[ColumnInfo] = field(default_factory=list)
    indexes: List[IndexInfo] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_all_tables(conn: sqlite3.Connection) -> List[str]:
    """Return every user-created table name in the database."""
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    )
    return [row[0] for row in cur.fetchall()]


def get_column_stats(
    conn: sqlite3.Connection,
    table_name: str,
    column_name: str,
) -> ColumnInfo:
    """Collect statistics for a single column by querying the database."""
    # Data type from PRAGMA
    pragma = conn.execute(f"PRAGMA table_info([{table_name}])").fetchall()
    data_type = "TEXT"
    for col in pragma:
        if col[1] == column_name:
            data_type = col[2] if col[2] else "TEXT"
            break

    row = conn.execute(
        f"SELECT COUNT(DISTINCT [{column_name}]), "
        f"MIN([{column_name}]), "
        f"MAX([{column_name}]), "
        f"SUM(CASE WHEN [{column_name}] IS NULL THEN 1 ELSE 0 END) "
        f"FROM [{table_name}]"
    ).fetchone()

    return ColumnInfo(
        name=column_name,
        data_type=data_type,
        num_distinct=row[0],
        min_val=row[1],
        max_val=row[2],
        null_count=row[3],
    )


def get_indexes(conn: sqlite3.Connection, table_name: str) -> List[IndexInfo]:
    """Return every index on *table_name* (including auto-indexes)."""
    cur = conn.execute(
        "SELECT name, tbl_name FROM sqlite_master "
        "WHERE type = 'index' AND tbl_name = ?",
        (table_name,),
    )
    indexes: List[IndexInfo] = []
    for idx_name, tbl in cur.fetchall():
        if idx_name is None:
            continue
        # Determine columns in this index
        info = conn.execute(f"PRAGMA index_info([{idx_name}])").fetchall()
        columns = [row[2] for row in info]  # row[2] = column name

        # Determine uniqueness
        idx_list = conn.execute(f"PRAGMA index_list([{tbl}])").fetchall()
        is_unique = False
        for entry in idx_list:
            if entry[1] == idx_name:
                is_unique = bool(entry[2])
                break

        indexes.append(IndexInfo(
            name=idx_name,
            table_name=tbl,
            columns=columns,
            is_unique=is_unique,
        ))
    return indexes


# ---------------------------------------------------------------------------
# High-level API
# ---------------------------------------------------------------------------

def get_table_stats(conn: sqlite3.Connection, table_name: str) -> CatalogStats:
    """Collect full statistics for a single table."""
    row_count = conn.execute(
        f"SELECT COUNT(*) FROM [{table_name}]"
    ).fetchone()[0]

    # Column info from PRAGMA
    pragma = conn.execute(f"PRAGMA table_info([{table_name}])").fetchall()
    columns = [
        get_column_stats(conn, table_name, col[1])
        for col in pragma
    ]

    indexes = get_indexes(conn, table_name)

    return CatalogStats(
        table_name=table_name,
        row_count=row_count,
        columns=columns,
        indexes=indexes,
    )


def get_all_catalog_stats(
    conn: sqlite3.Connection,
) -> Dict[str, CatalogStats]:
    """Return catalog statistics for every table in the database."""
    tables = get_all_tables(conn)
    return {t: get_table_stats(conn, t) for t in tables}
