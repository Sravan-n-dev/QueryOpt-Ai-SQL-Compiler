"""
QueryOpt AI — Cost Model
========================
Accurate, textbook-grounded cost model evaluating physical operator costs
using I/O page costs and CPU evaluation costs.
"""

from __future__ import annotations

import math
from typing import Optional

from optimizer.statistics import TableStats


class CostModel:
    """Computes standard database engine cost units for alternative physical plans."""

    # Standard System R / PostgreSQL cost constants
    SEQ_PAGE_COST = 1.0          # Cost of a sequential 4KB page fetch
    RANDOM_PAGE_COST = 4.0       # Cost of a non-sequential (random) page fetch
    CPU_TUPLE_COST = 0.01        # Cost of processing a single tuple in memory
    CPU_OPERATOR_COST = 0.0025   # Cost of evaluating an operator or filter condition
    CPU_INDEX_TUPLE_COST = 0.005 # Cost of checking an index tree entry
    HASH_BUILD_COST = 0.02       # Cost of hashing and inserting a tuple into a hash table
    PAGE_SIZE = 4096             # 4KB disk page
    AVG_ROW_BYTES = 80           # Estimated average bytes per row

    def estimate_table_scan_cost(self, total_rows: float) -> float:
        """Sequential I/O cost + CPU tuple processing cost."""
        total_pages = max(1.0, math.ceil((total_rows * self.AVG_ROW_BYTES) / self.PAGE_SIZE))
        io_cost = total_pages * self.SEQ_PAGE_COST
        cpu_cost = total_rows * self.CPU_TUPLE_COST
        return io_cost + cpu_cost

    def estimate_index_scan_cost(self, total_rows: float, estimated_matches: float) -> float:
        """B-tree traversal random I/O + matching table page fetches."""
        # B-tree depth log2(total_rows) random I/Os
        tree_depth = max(2.0, math.log2(max(2.0, total_rows)) / 4.0)
        index_io_cost = tree_depth * self.RANDOM_PAGE_COST

        # Random table I/Os for matched tuples
        matching_pages = min(estimated_matches, max(1.0, (estimated_matches * self.AVG_ROW_BYTES) / self.PAGE_SIZE))
        table_io_cost = matching_pages * self.RANDOM_PAGE_COST

        cpu_cost = (estimated_matches * self.CPU_INDEX_TUPLE_COST) + (estimated_matches * self.CPU_TUPLE_COST)
        return index_io_cost + table_io_cost + cpu_cost

    def estimate_filter_cost(self, input_rows: float) -> float:
        """CPU condition evaluation cost."""
        return input_rows * self.CPU_OPERATOR_COST

    def estimate_project_cost(self, input_rows: float) -> float:
        """CPU column extraction cost."""
        return input_rows * (self.CPU_OPERATOR_COST * 0.5)

    def estimate_nested_loop_cost(self, outer_rows: float, inner_rows: float) -> float:
        """Cost of nested loop join: outer tuples * inner scan and condition checks."""
        return (outer_rows * self.CPU_TUPLE_COST) + (outer_rows * inner_rows * self.CPU_OPERATOR_COST)

    def estimate_hash_join_cost(self, outer_rows: float, inner_rows: float) -> float:
        """Cost of building hash table from inner relation + probing with outer relation."""
        build_cost = inner_rows * (self.CPU_TUPLE_COST + self.HASH_BUILD_COST)
        probe_cost = outer_rows * (self.CPU_TUPLE_COST + self.CPU_OPERATOR_COST)
        return build_cost + probe_cost

    def estimate_sort_cost(self, rows: float) -> float:
        """In-memory quicksort cost: O(N log N)."""
        if rows <= 1.0:
            return 0.0
        return rows * math.log2(rows) * self.CPU_OPERATOR_COST

    def estimate_limit_cost(self, rows: float) -> float:
        return rows * 0.001

    def estimate_distinct_cost(self, rows: float) -> float:
        """Hash table deduplication cost."""
        return rows * (self.CPU_TUPLE_COST + self.HASH_BUILD_COST)
