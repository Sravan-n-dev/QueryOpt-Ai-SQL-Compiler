# Limitations & Future Scope — QueryOpt AI

## 1. Supported SQL Subset
- `SELECT`, `SELECT *`, `SELECT DISTINCT`
- Column aliases (`AS alias` or implicit)
- Table aliases (`FROM Student s`)
- `FROM` (single or multiple comma-separated relations)
- `WHERE` with `AND`, `OR`, parenthesized conditions
- Comparison operators: `=`, `!=`, `<>`, `<`, `>`, `<=`, `>=`
- String literals (`'ECE'`), integer literals (`23`), float literals (`8.5`)
- `INNER JOIN`, `JOIN ... ON ...`
- `ORDER BY` with `ASC` and `DESC`
- `LIMIT <int>`

## 2. Current Limitations & Unsupported Features
1. **Aggregations & Grouping**: `GROUP BY`, `HAVING`, and aggregate functions (`COUNT`, `SUM`, `AVG`, `MIN`, `MAX`) are currently not parsed in user queries (though catalog profiling queries use them internally).
2. **Subqueries**: Correlated and non-correlated subqueries (`WHERE x IN (SELECT ...)`) are not supported in the initial grammar.
3. **Set Operations**: `UNION`, `INTERSECT`, and `EXCEPT` are not implemented.
4. **Outer Joins**: `LEFT JOIN`, `RIGHT JOIN`, and `FULL OUTER JOIN` are not supported (only `INNER JOIN` and `CROSS JOIN`).
5. **Memory Management**: The Volcano iterator engine materializes the build side of HashJoins and Sort in RAM without spilling to secondary disk partitions.

## 3. Future Scope
- Implementation of Volcano query execution memory spilling (grace hash joins).
- Aggregation physical operators (`HashAggregate`, `StreamAggregate`).
- Subquery unnesting into semi-joins.
- Dynamic Programming join enumeration for multi-table joins (> 5 tables).
