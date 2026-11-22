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

In addition, an **AI Natural Language to SQL module** (powered by Azure OpenAI (GPT-5 mini)) translates plain English user queries into schema-constrained SQL queries that enter the exact same compiler pipeline.

---

## 🏗️ Architecture & Pipeline Flow

```
[ User Input: SQL Query ]           [ User Input: English Query ]
           │                                      │
           │                               [ Azure OpenAI GPT-5 mini ]
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
- Node.js and npm (needed to rebuild the React interface)

### 2. Install Python dependencies
From the project root:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Azure OpenAI (for the Natural Language to SQL feature)
Copy `.env.example` to `.env`, then replace the endpoint and API-key placeholders. Keep the deployment name as `gpt-5-mini`, matching your Foundry deployment.
```bash
cp .env.example .env
```
Open `.env` and fill in the values from Azure Portal → your Azure OpenAI resource → **Keys and Endpoint**. The deployment name comes from Foundry → **Model deployments**.

See **[AZURE_SETUP.md](AZURE_SETUP.md)** for the exact location of every placeholder and the values to copy. Do not commit or share `.env`.

### 4. Build the React frontend and launch the application
The Python server serves the prebuilt files in `static/`. Rebuild once after extracting this project so the updated Azure OpenAI settings dialog from `frontend/src/` is included:
```bash
cd frontend
npm install
npm run build
cd ..
python app.py
```
Open **http://localhost:8000** in your browser. The app initializes and seeds the SQLite database automatically on first launch.

> The `ui/` directory contains earlier Streamlit UI modules. The current entry point is `python app.py`; do not run `streamlit run app.py`.

## 🧪 Automated Testing

Execute the test suite verifying all 7 stages and SQLite equivalence:
```bash
python -m pytest tests/ -v
```

All 24 unit and integration tests verify:
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


## GPT-5 mini empty-response troubleshooting

If Azure returns an empty response during Test & Connect, update to the latest project package. GPT-5 reasoning tokens share the `max_output_tokens` budget with visible text. The client now sets minimal reasoning effort, explicitly requests text for the connection test, and gives the model a larger token budget. See [AZURE_SETUP.md](AZURE_SETUP.md#6-troubleshooting-empty-response-from-gpt-5-mini).
