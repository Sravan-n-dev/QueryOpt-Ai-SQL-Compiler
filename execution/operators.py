"""
QueryOpt AI — Volcano-Style Iterator Operators
==============================================
Pure Volcano iterator implementation (open, next, close, reset).
Pulls tuples demand-driven through the physical plan operator tree.
"""

from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class VolcanoIterator(ABC):
    """Abstract base class for all Volcano-style physical execution operators."""

    def __init__(self):
        self.rows_scanned: int = 0
        self.rows_produced: int = 0
        self.is_open: bool = False

    @abstractmethod
    def open(self) -> None:
        """Initialize operator state and open child iterators."""
        self.is_open = True
        self.rows_scanned = 0
        self.rows_produced = 0

    @abstractmethod
    def next(self) -> Optional[Dict[str, Any]]:
        """Pull the next output tuple, or None if stream is exhausted."""

    @abstractmethod
    def close(self) -> None:
        """Release resources and close child iterators."""
        self.is_open = False

    def reset(self) -> None:
        """Reset iterator state to the beginning for nested-loop re-scans."""
        self.close()
        self.open()


class TableScanIterator(VolcanoIterator):
    """Scans all rows of a physical table from the database storage."""

    def __init__(self, conn: sqlite3.Connection, table_name: str, alias: Optional[str] = None):
        super().__init__()
        self.conn = conn
        self.table_name = table_name
        self.alias = alias or table_name
        self.cursor: Optional[sqlite3.Cursor] = None
        self.col_names: List[str] = []

    def open(self) -> None:
        super().open()
        self.cursor = self.conn.cursor()
        self.cursor.execute(f'SELECT * FROM "{self.table_name}"')
        self.col_names = [d[0] for d in self.cursor.description]

    def next(self) -> Optional[Dict[str, Any]]:
        if not self.cursor:
            return None
        row = self.cursor.fetchone()
        if row is None:
            return None

        self.rows_scanned += 1
        self.rows_produced += 1

        # Populate row dictionary with both bare column names and qualified names
        row_dict: Dict[str, Any] = {}
        for col_name, val in zip(self.col_names, row):
            row_dict[col_name] = val
            row_dict[col_name.lower()] = val
            row_dict[f"{self.table_name}.{col_name}"] = val
            row_dict[f"{self.table_name.lower()}.{col_name.lower()}"] = val
            if self.alias:
                row_dict[f"{self.alias}.{col_name}"] = val
                row_dict[f"{self.alias.lower()}.{col_name.lower()}"] = val

        return row_dict

    def close(self) -> None:
        if self.cursor:
            try:
                self.cursor.close()
            except Exception:
                pass
            self.cursor = None
        super().close()


class IndexScanIterator(VolcanoIterator):
    """Performs an index-accelerated scan on a table for a specific predicate."""

    def __init__(
        self,
        conn: sqlite3.Connection,
        table_name: str,
        index_name: str,
        column: str,
        op: str,
        value: Any,
        alias: Optional[str] = None,
    ):
        super().__init__()
        self.conn = conn
        self.table_name = table_name
        self.index_name = index_name
        self.column = column
        self.op = op
        self.value = value
        self.alias = alias or table_name
        self.cursor: Optional[sqlite3.Cursor] = None
        self.col_names: List[str] = []

    def open(self) -> None:
        super().open()
        self.cursor = self.conn.cursor()
        # Query utilizing SQLite index
        query = f'SELECT * FROM "{self.table_name}" WHERE "{self.column}" {self.op} ?'
        self.cursor.execute(query, (self.value,))
        self.col_names = [d[0] for d in self.cursor.description]

    def next(self) -> Optional[Dict[str, Any]]:
        if not self.cursor:
            return None
        row = self.cursor.fetchone()
        if row is None:
            return None

        self.rows_scanned += 1
        self.rows_produced += 1

        row_dict: Dict[str, Any] = {}
        for col_name, val in zip(self.col_names, row):
            row_dict[col_name] = val
            row_dict[col_name.lower()] = val
            row_dict[f"{self.table_name}.{col_name}"] = val
            row_dict[f"{self.table_name.lower()}.{col_name.lower()}"] = val
            if self.alias:
                row_dict[f"{self.alias}.{col_name}"] = val
                row_dict[f"{self.alias.lower()}.{col_name.lower()}"] = val

        return row_dict

    def close(self) -> None:
        if self.cursor:
            try:
                self.cursor.close()
            except Exception:
                pass
            self.cursor = None
        super().close()


class FilterIterator(VolcanoIterator):
    """Filters child tuples against a boolean condition predicate."""

    def __init__(self, condition_fn: Callable[[Dict[str, Any]], bool], child: VolcanoIterator):
        super().__init__()
        self.condition_fn = condition_fn
        self.child = child

    def open(self) -> None:
        super().open()
        self.child.open()

    def next(self) -> Optional[Dict[str, Any]]:
        while True:
            row = self.child.next()
            if row is None:
                return None
            self.rows_scanned += 1
            if self.condition_fn(row):
                self.rows_produced += 1
                return row

    def close(self) -> None:
        self.child.close()
        super().close()

    def reset(self) -> None:
        self.child.reset()
        super().open()


class ProjectIterator(VolcanoIterator):
    """Projects specified columns and aliases from child tuples."""

    def __init__(self, columns: List[str], child: VolcanoIterator):
        super().__init__()
        self.columns = columns
        self.child = child
        self._is_star = "*" in columns or any(c.endswith(".*") for c in columns)

    def open(self) -> None:
        super().open()
        self.child.open()

    def next(self) -> Optional[Dict[str, Any]]:
        row = self.child.next()
        if row is None:
            return None

        self.rows_scanned += 1
        self.rows_produced += 1

        if self._is_star:
            # Clean up internally duplicated qualified names for user-facing output
            out: Dict[str, Any] = {}
            for k, v in row.items():
                if "." not in k:
                    out[k] = v
            return out if out else row

        out_row: Dict[str, Any] = {}
        for col in self.columns:
            # Handle qualified or bare name lookup
            val = self._lookup(row, col)
            display_name = col.split(".")[-1]
            out_row[display_name] = val

        return out_row

    def _lookup(self, row: Dict[str, Any], col: str) -> Any:
        if col in row:
            return row[col]
        col_lower = col.lower()
        if col_lower in row:
            return row[col_lower]
        bare = col.split(".")[-1].lower()
        if bare in row:
            return row[bare]
        return None

    def close(self) -> None:
        self.child.close()
        super().close()

    def reset(self) -> None:
        self.child.reset()
        super().open()


class HashJoinIterator(VolcanoIterator):
    """Performs an equi-join by building a hash table in memory from the build side."""

    def __init__(
        self,
        left: VolcanoIterator,
        right: VolcanoIterator,
        left_key: str,
        right_key: str,
        build_side: str = "right",
    ):
        super().__init__()
        self.left = left
        self.right = right
        self.left_key = left_key.lower()
        self.right_key = right_key.lower()
        self.build_side = build_side

        self.hash_table: Dict[Any, List[Dict[str, Any]]] = {}
        self.current_probe_row: Optional[Dict[str, Any]] = None
        self.current_matches: List[Dict[str, Any]] = []
        self.match_idx: int = 0

    def open(self) -> None:
        super().open()
        self.left.open()
        self.right.open()

        # Build phase: consume all tuples from build side (default: right relation)
        self.hash_table.clear()
        build_iter = self.right if self.build_side == "right" else self.left
        key = self.right_key if self.build_side == "right" else self.left_key

        while True:
            row = build_iter.next()
            if row is None:
                break
            val = self._get_key_val(row, key)
            if val is not None:
                self.hash_table.setdefault(val, []).append(row)

        self.current_probe_row = None
        self.current_matches = []
        self.match_idx = 0

    def next(self) -> Optional[Dict[str, Any]]:
        probe_iter = self.left if self.build_side == "right" else self.right
        probe_key = self.left_key if self.build_side == "right" else self.right_key

        while True:
            # Yield next match from current probe tuple
            if self.current_matches and self.match_idx < len(self.current_matches):
                build_row = self.current_matches[self.match_idx]
                self.match_idx += 1
                self.rows_produced += 1

                # Combine probe row and build row
                merged = dict(self.current_probe_row)
                merged.update(build_row)
                return merged

            # Pull next probe tuple
            self.current_probe_row = probe_iter.next()
            if self.current_probe_row is None:
                return None

            self.rows_scanned += 1
            pval = self._get_key_val(self.current_probe_row, probe_key)
            self.current_matches = self.hash_table.get(pval, [])
            self.match_idx = 0

    def _get_key_val(self, row: Dict[str, Any], key: str) -> Any:
        if key in row:
            return row[key]
        for k, v in row.items():
            if k.lower() == key or k.lower().endswith(f".{key}"):
                return v
        return None

    def close(self) -> None:
        self.left.close()
        self.right.close()
        self.hash_table.clear()
        super().close()


class NestedLoopJoinIterator(VolcanoIterator):
    """Executes a nested loop join across left and right child streams."""

    def __init__(
        self,
        left: VolcanoIterator,
        right: VolcanoIterator,
        condition_fn: Callable[[Dict[str, Any]], bool],
    ):
        super().__init__()
        self.left = left
        self.right = right
        self.condition_fn = condition_fn
        self.current_left_row: Optional[Dict[str, Any]] = None

    def open(self) -> None:
        super().open()
        self.left.open()
        self.right.open()
        self.current_left_row = self.left.next()

    def next(self) -> Optional[Dict[str, Any]]:
        while self.current_left_row is not None:
            right_row = self.right.next()
            if right_row is not None:
                self.rows_scanned += 1
                combined = dict(self.current_left_row)
                combined.update(right_row)
                if self.condition_fn(combined):
                    self.rows_produced += 1
                    return combined
            else:
                # Right stream exhausted; advance outer left tuple and reset inner
                self.current_left_row = self.left.next()
                if self.current_left_row is not None:
                    self.right.reset()

        return None

    def close(self) -> None:
        self.left.close()
        self.right.close()
        super().close()


class SortIterator(VolcanoIterator):
    """Sorts incoming tuples in-memory before yielding them in order."""

    def __init__(self, order_items: List[Tuple[str, str]], child: VolcanoIterator):
        super().__init__()
        self.order_items = order_items
        self.child = child
        self.sorted_rows: List[Dict[str, Any]] = []
        self.cursor_idx: int = 0

    def open(self) -> None:
        super().open()
        self.child.open()

        # Materialize all child tuples
        rows: List[Dict[str, Any]] = []
        while True:
            row = self.child.next()
            if row is None:
                break
            rows.append(row)
            self.rows_scanned += 1

        # Multi-key sorting
        def sort_key(row: Dict[str, Any]):
            keys = []
            for col, _ in self.order_items:
                val = self._lookup(row, col)
                # None handling in sort keys
                keys.append(val if val is not None else -float("inf"))
            return tuple(keys)

        # Primary sort
        if self.order_items:
            first_col, first_dir = self.order_items[0]
            reverse = (first_dir.upper() == "DESC")
            rows.sort(key=sort_key, reverse=reverse)

        self.sorted_rows = rows
        self.cursor_idx = 0

    def _lookup(self, row: Dict[str, Any], col: str) -> Any:
        col_clean = col.split(".")[-1].lower()
        if col in row:
            return row[col]
        for k, v in row.items():
            if k.lower() == col.lower() or k.lower().endswith(f".{col_clean}") or k.lower() == col_clean:
                return v
        return None

    def next(self) -> Optional[Dict[str, Any]]:
        if self.cursor_idx < len(self.sorted_rows):
            row = self.sorted_rows[self.cursor_idx]
            self.cursor_idx += 1
            self.rows_produced += 1
            return row
        return None

    def close(self) -> None:
        self.child.close()
        self.sorted_rows.clear()
        super().close()


class LimitIterator(VolcanoIterator):
    """Yields at most count tuples from child."""

    def __init__(self, count: int, child: VolcanoIterator):
        super().__init__()
        self.count = count
        self.child = child
        self.produced: int = 0

    def open(self) -> None:
        super().open()
        self.child.open()
        self.produced = 0

    def next(self) -> Optional[Dict[str, Any]]:
        if self.produced >= self.count:
            return None
        row = self.child.next()
        if row is None:
            return None
        self.rows_scanned += 1
        self.produced += 1
        self.rows_produced += 1
        return row

    def close(self) -> None:
        self.child.close()
        super().close()


class DistinctIterator(VolcanoIterator):
    """Deduplicates tuples using a hash set of tuple values."""

    def __init__(self, child: VolcanoIterator):
        super().__init__()
        self.child = child
        self.seen: Set[Tuple[Any, ...]] = set()

    def open(self) -> None:
        super().open()
        self.child.open()
        self.seen.clear()

    def next(self) -> Optional[Dict[str, Any]]:
        while True:
            row = self.child.next()
            if row is None:
                return None
            self.rows_scanned += 1
            # Build hashable key from non-qualified row values
            key = tuple(sorted((k, v) for k, v in row.items() if "." not in k))
            if key not in self.seen:
                self.seen.add(key)
                self.rows_produced += 1
                return row

    def close(self) -> None:
        self.child.close()
        self.seen.clear()
        super().close()
