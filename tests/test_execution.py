"""
Tests for Volcano Physical Execution Operators.
"""

from execution.operators import FilterIterator, LimitIterator, TableScanIterator


def test_volcano_table_scan_and_limit(db_connection):
    scan = TableScanIterator(db_connection, "Student")
    lim = LimitIterator(5, scan)

    lim.open()
    rows = []
    while True:
        row = lim.next()
        if row is None:
            break
        rows.append(row)
    lim.close()

    assert len(rows) == 5
    assert "student_id" in rows[0]
