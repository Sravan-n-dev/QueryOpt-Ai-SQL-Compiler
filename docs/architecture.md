# System Architecture — QueryOpt AI

## 1. End-to-End Pipeline Overview

QueryOpt AI implements an end-to-end database query compiler following traditional compiler design and database engine principles:

```
[SQL / NL Query]
       │
       ▼
1. Lexer (Lark EBNF) ──────► Token Stream [Token(TYPE, val, line, col)]
       │
       ▼
2. Parser (Earley Engine) ──► Abstract Syntax Tree (ASTNode dataclasses)
       │
       ▼
3. Semantic Analyzer ──────► Catalog Validation (sqlite3 PRAGMA metadata)
       │
       ▼
4. RA Converter ───────────► Canonical Relational Algebra Tree (σ, π, ⋈, Scan)
       │
       ▼
5. Logical Optimizer ──────► Rewritten Relational Algebra Tree (Pushed Filters)
       │
       ▼
6. Cost Optimizer (CBO) ───► Physical Plan Tree (TableScan / IndexScan / HashJoin)
       │
       ▼
7. Volcano Execution ──────► Demand-Driven Iterators (open/next/close)
       │
       ▼
8. Verification Engine ────► Equivalence Validation against Reference SQLite
```

## 2. Component Structure

- **`compiler/`**:
  - `grammar.lark`: Declarative EBNF syntax rules.
  - `lexer.py`: Wraps Lark token stream, extracts line/column offsets.
  - `parser.py`: Transforms Lark parse tree to typed dataclass ASTs.
  - `ast_nodes.py`: Strongly typed nodes (`SelectStatement`, `ColumnRef`, `Comparison`, etc.).
  - `semantic_analyzer.py`: Resolves identifiers against SQLite catalog.
  - `diagnostics.py`: Structured exceptions with line numbers and human hints.

- **`relational_algebra/`**:
  - `nodes.py`: Operator classes (`Scan`, `Selection`, `Projection`, `Join`, `Sort`, `Limit`, `Distinct`).
  - `converter.py`: Transforms AST to canonical relational algebra tree.
  - `visualizer.py`: Renders Graphviz DOT diagrams and ASCII text trees.

- **`optimizer/`**:
  - `rewrite_rules.py`: Relational transformation rules.
  - `logical_optimizer.py`: Fixed-point iteration engine.
  - `statistics.py`: Dynamic SQLite catalog profiling.
  - `cardinality.py`: Mathematical selectivity estimation.
  - `cost_model.py`: I/O page and CPU evaluation cost formulas.
  - `cost_optimizer.py`: Physical operator selection.

- **`execution/`**:
  - `physical_plan.py`: Physical operator definitions annotated with costs.
  - `operators.py`: Volcano iterator implementations (`open/next/close/reset`).
  - `iterator_engine.py`: Compiles physical tree into iterator tree.
  - `executor.py`: Pulls tuples, measures latency, compares with SQLite.

- **`ai/`**:
  - `prompts.py`: Schema-constrained system and user prompts.
  - `llm_client.py`: Google GenAI SDK wrapper.
  - `nl2sql.py`: Structured JSON extraction and SQL validation.

- **`ui/`**:
  - Streamlit dashboard, query studio, pipeline inspector, optimization dashboard, schema explorer, history, and demonstration gallery.
