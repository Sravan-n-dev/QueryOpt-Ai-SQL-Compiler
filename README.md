# QueryOpt AI: Intelligent SQL Compiler & Cost-Based Optimizer

> **Academic Project**: 3rd Year B.Tech Computer Science & Engineering — Compiler Design & Database Systems  
> **Topic**: End-to-End SQL Compilation, Logical Relational Algebra Rewrites, Cost-Based Physical Plan Optimization, Volcano-Style Execution Engine, and AI-Driven Natural Language Interface.

---

## 🌟 Executive Summary

**QueryOpt AI** is a fully custom SQL query compiler and cost-based database query optimizer built from first principles in Python. Rather than acting as a simple wrapper or forwarding raw SQL queries to an existing database engine, QueryOpt AI implements its own complete 7-stage compilation and execution pipeline:

1. **Lexical Analysis (Lexer)**: Lark EBNF-driven token stream generation with lexical error localization.
2. **Syntax Analysis (Parser)**: EBNF grammar parsing constructing a strongly typed Abstract Syntax Tree (AST).
3. **Semantic Analysis**: Catalog-driven schema validation, identifier resolution, type checking, and ambiguity detection.
4. **Relational Algebra Generation**: Conversion of AST into an algebraic operator tree ($\sigma$, $\pi$, $\bowtie$, $\tau$, $\delta$).
5. **Logical Query Optimizer**: Rule-based algebraic transformations including Predicate Pushdown, Projection Pushdown, Selection Simplification, and Constant Folding.
6. **Cost-Based Query Optimizer (CBO)**: Selectivity estimation, catalog statistics profiling, TableScan vs. IndexScan evaluation, and HashJoin vs. NestedLoopJoin selection.
7. **Physical Execution Engine**: Pure Volcano-style demand-driven iterator pipeline (`open()`, `next()`, `close()`, `reset()`) executing physical operators against persistent SQLite storage.

In addition, an **AI Natural Language to SQL module** (powered by Google Gemini) translates plain English user queries into schema-constrained SQL queries that enter the exact same compiler pipeline.

---

## 🏗️ Architecture & Pipeline Flow

```
[ User Input: SQL Query ]           [ User Input: English Query ]
           │                                      │
           │                               [ Google Gemini ]
           │                               (Schema-Aware LLM)
           │                                      │
           └──────────────────┬───────────────────┘
                              ▼
                Stage 1: Lexical Analysis
                (Tokens Stream & Positions)
                              ▼
                Stage 2: Syntax Analysis
                (Abstract Syntax Tree - AST)
                              ▼
                Stage 3: Semantic Analysis
                (Catalog Schema Validation)
                              ▼
                Stage 4: Relational Algebra
                (Canonical Logical Tree)
                              ▼
                Stage 5: Logical Optimizer
                (Rewrite Rules / Fixed-Point)
                              ▼
                Stage 6: Cost-Based Optimizer
                (Cardinality & Cost Models)
                              ▼
                Stage 7: Volcano Physical Engine
                (Iterators: open / next / close)
                              ▼
           [ Results Viewer & SQLite Verification ]
```

---

## 📊 Database Schema (College Database)

The persistent storage layer uses SQLite with deterministic sample data (3,000 students, 9,000+ enrollments, 21 courses, 5 departments):

- **Student** (`student_id` PK, `name`, `age`, `branch`, `cgpa`, `dept_id` FK)
- **Department** (`dept_id` PK, `dept_name`, `hod`)
- **Course** (`course_id` PK, `course_name`, `dept_id` FK, `credits`)
- **Enrollment** (`enrollment_id` PK, `student_id` FK, `course_id` FK, `marks`)

### Physical Indexes
- `idx_student_age` on `Student(age)`
- `idx_student_branch` on `Student(branch)`
- `idx_student_dept_id` on `Student(dept_id)`
- `idx_enrollment_student_id` on `Enrollment(student_id)`
- `idx_enrollment_course_id` on `Enrollment(course_id)`
- `idx_course_dept_id` on `Course(dept_id)`

---

## 🚀 Quick Start & Installation

### 1. Prerequisites
- Python 3.11 or newer
- Git

### 2. Clone the Repository
```bash
git clone https://github.com/Sravan-n-dev/QueryOpt-Ai-SQL-Compiler.git
cd QueryOpt-Ai-SQL-Compiler
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. (Optional) Configure AI Natural Language Model
Copy `.env.example` to `.env` and set your Google Gemini API key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash
```
*(Note: If no API key is configured, all core compiler and optimizer features function normally for SQL queries.)*

### 5. Launch the Developer Studio & Web IDE
```bash
python app.py
```
Open **`http://localhost:8000`** in your browser. The application will automatically initialize and seed the SQLite database with 3,000 students and 9,000+ records on first launch!

---

## 🧪 Automated Testing

Execute the test suite verifying all 7 stages and SQLite equivalence:
```bash
python -m pytest tests/ -v
```

All 19 unit and integration tests verify:
- Lexer tokenization & position tagging
- Parser syntax checking & AST generation
- Semantic error detection (invalid tables, missing columns)
- Relational algebra canonical plan construction
- Predicate pushdown and algebraic rewrites
- Cost-based operator selection
- Volcano iterator operator execution
- 100% result equivalence with reference SQLite

---

## 📚 Documentation Links
- [System Architecture](docs/architecture.md)
- [Algorithms & Cost Model](docs/algorithms.md)
- [Professor Demonstration Guide](docs/demo_guide.md)
- [Limitations & Future Scope](docs/limitations.md)
- [Project Status & Roadmap](PROJECT_STATUS.txt)
