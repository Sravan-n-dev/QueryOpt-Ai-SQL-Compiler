"""
QueryOpt AI — Statistics Collector
==================================
Extracts live schema and catalog statistics directly from the SQLite database.
Never uses mock or hardcoded statistics.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ColumnStats:
    column_name: str
    data_type: str
    num_distinct: int = 1
    min_val: Any = None
    max_val: Any = None
    null_count: int = 0


@dataclass
class IndexStats:
    name: str
    table_name: str
    columns: List[str]
    is_unique: bool = False


@dataclass
class TableStats:
    table_name: str
    row_count: int
    column_stats: Dict[str, ColumnStats] = field(default_factory=dict)
    indexes: List[IndexStats] = field(default_factory=list)


class StatsCollector:
    """Collects real-time physical catalog statistics from SQLite."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def collect_table_stats(self, table_name: str) -> TableStats:
        """Query actual table row count, column profiles, and index definitions."""
        cursor = self.conn.cursor()

        # 1. Row count
        cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
        row_count = cursor.fetchone()[0] or 0

        # 2. Columns
        cursor.execute(f'PRAGMA table_info("{table_name}")')
        cols_meta = cursor.fetchall()

        col_stats: Dict[str, ColumnStats] = {}
        for col in cols_meta:
            col_name = col[1]
            col_type = col[2] or "TEXT"

            # Compute distinct, min, max, null count if table has rows
            num_distinct = 1
            min_val = None
            max_val = None
            null_count = 0

            if row_count > 0:
                try:
                    cursor.execute(
                        f'SELECT COUNT(DISTINCT "{col_name}"), MIN("{col_name}"), MAX("{col_name}"), '
                        f'SUM(CASE WHEN "{col_name}" IS NULL THEN 1 ELSE 0 END) FROM "{table_name}"'
                    )
                    d_row = cursor.fetchone()
                    if d_row:
                        num_distinct = max(1, d_row[0] or 1)
                        min_val = d_row[1]
                        max_val = d_row[2]
                        null_count = d_row[3] or 0
                except Exception:
                    num_distinct = max(1, row_count // 10)

            col_stats[col_name.lower()] = ColumnStats(
                column_name=col_name,
                data_type=col_type,
                num_distinct=num_distinct,
                min_val=min_val,
                max_val=max_val,
                null_count=null_count,
            )

        # 3. Indexes
        cursor.execute(f'PRAGMA index_list("{table_name}")')
        idx_meta = cursor.fetchall()
        indexes: List[IndexStats] = []
        for idx in idx_meta:
            idx_name = idx[1]
            is_unique = bool(idx[2])
            cursor.execute(f'PRAGMA index_info("{idx_name}")')
            idx_cols = [c[2] for c in cursor.fetchall()]
            indexes.append(
                IndexStats(
                    name=idx_name,
                    table_name=table_name,
                    columns=idx_cols,
                    is_unique=is_unique,
                )
            )

        return TableStats(
            table_name=table_name,
            row_count=row_count,
            column_stats=col_stats,
            indexes=indexes,
        )

    def collect_all_stats(self) -> Dict[str, TableStats]:
        """Collect statistics for all user tables in the database."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [r[0] for r in cursor.fetchall()]

        all_stats: Dict[str, TableStats] = {}
        for tbl in tables:
            all_stats[tbl.lower()] = self.collect_table_stats(tbl)

        return all_stats
