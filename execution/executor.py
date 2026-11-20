"""
QueryOpt AI — Query Executor
============================
Executes the physical operator tree using the Volcano iterator engine,
records runtime execution statistics, and verifies results against reference SQLite.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from execution.iterator_engine import IteratorEngine
from execution.physical_plan import PhysicalNode


@dataclass
class ExecutionResult:
    """Execution output and performance metrics."""

    rows: List[Dict[str, Any]]
    row_count: int
    execution_time_ms: float
    rows_scanned: int
    success: bool
    error: Optional[str] = None
    column_names: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "row_count": self.row_count,
            "execution_time_ms": self.execution_time_ms,
            "rows_scanned": self.rows_scanned,
            "success": self.success,
            "error": self.error,
            "column_names": self.column_names,
        }


class QueryExecutor:
    """Executes physical execution plans using the Volcano-style iterator engine."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.engine = IteratorEngine(conn)

    def execute(self, physical_plan: PhysicalNode) -> ExecutionResult:
        """Run the query by pulling tuples through the Volcano iterator tree."""
        root_iterator = self.engine.build_iterator_tree(physical_plan)
        rows: List[Dict[str, Any]] = []

        start_time = time.perf_counter()
        try:
            root_iterator.open()
            while True:
                row = root_iterator.next()
                if row is None:
                    break
                rows.append(row)
            root_iterator.close()
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            col_names = list(rows[0].keys()) if rows else []

            return ExecutionResult(
                rows=rows,
                row_count=len(rows),
                execution_time_ms=round(elapsed_ms, 3),
                rows_scanned=root_iterator.rows_scanned,
                success=True,
                column_names=col_names,
            )
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            try:
                root_iterator.close()
            except Exception:
                pass
            return ExecutionResult(
                rows=[],
                row_count=0,
                execution_time_ms=round(elapsed_ms, 3),
                rows_scanned=root_iterator.rows_scanned if root_iterator else 0,
                success=False,
                error=str(exc),
            )

    def execute_reference(self, sql: str) -> List[Dict[str, Any]]:
        """Execute the SQL directly in SQLite as reference standard for equivalence testing."""
        cursor = self.conn.cursor()
        cursor.execute(sql)
        cols = [d[0] for d in cursor.description] if cursor.description else []
        raw_rows = cursor.fetchall()
        return [dict(zip(cols, r)) for r in raw_rows]

    @staticmethod
    def compare_results(custom_rows: List[Dict[str, Any]], reference_rows: List[Dict[str, Any]]) -> bool:
        """Verify that the custom compiler engine returned results identical to reference SQLite."""
        if len(custom_rows) != len(reference_rows):
            return False
        if not custom_rows and not reference_rows:
            return True

        # Helper to normalize values (float rounding, string strip)
        def norm_val(v: Any) -> Any:
            if isinstance(v, float):
                return round(v, 4)
            return v

        # Compare row-by-row if sorted, or sort by hash of values
        def row_tuple(r: Dict[str, Any]) -> Tuple:
            # Only compare bare column names or values in sorted order of lowercase keys
            clean = {k.split(".")[-1].lower(): norm_val(v) for k, v in r.items() if "." not in k or len(r) == 1}
            if not clean:
                clean = {k.split(".")[-1].lower(): norm_val(v) for k, v in r.items()}
            return tuple(sorted(clean.items()))

        custom_tuples = sorted([row_tuple(r) for r in custom_rows], key=lambda x: str(x))
        ref_tuples = sorted([row_tuple(r) for r in reference_rows], key=lambda x: str(x))

        return custom_tuples == ref_tuples
