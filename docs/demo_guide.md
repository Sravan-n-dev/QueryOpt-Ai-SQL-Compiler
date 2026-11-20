# Professor Demonstration Guide — QueryOpt AI

Follow this 10-15 minute walkthrough to demonstrate all required compiler, optimizer, and AI capabilities.

---

## Step 1: System Overview & Catalog Verification
1. Launch the application:
   ```bash
   streamlit run app.py
   ```
2. Open the **Dashboard**:
   - Highlight the live metrics: 4 tables, 3,000 students, 9,000+ enrollments, 6 B-tree indexes.
3. Open the **Schema Explorer**:
   - Show table `Student`. Point out column statistics dynamically gathered from SQLite (`num_distinct`, `min_val`, `max_val`).

---

## Step 2: Core SQL Compilation & Pipeline Inspection
1. Go to **Query Studio** -> **SQL Query Editor**.
2. Run this query:
   ```sql
   SELECT name, age FROM Student WHERE age > 23 ORDER BY student_id LIMIT 10;
   ```
3. Click **Compile & Run**.
4. Navigate to **Pipeline Inspector**:
   - **Stage 1 (Lexer)**: Show token stream with types and line/column positions.
   - **Stage 2 (Parser)**: Show the generated AST tree.
   - **Stage 3 (Semantic Analyzer)**: Show schema validation pass.
   - **Stage 4 (Relational Algebra)**: Show the unoptimized canonical RA tree.
   - **Stage 5 (Logical Optimizer)**: Show the rewritten tree with **Predicate Pushdown**!
   - **Stage 6 (CBO)**: Show cost estimation and access path selection.
   - **Stage 7 (Volcano Engine)**: Show execution time and rows scanned.
   - Show **Verification Check**: Volcano results match reference SQLite 100%.

---

## Step 3: Complex Join Optimization Comparison
1. Go to **Optimization Dashboard**.
2. Run or select **Example 5**:
   ```sql
   SELECT s.name, d.dept_name
   FROM Student s
   INNER JOIN Department d ON s.dept_id = d.dept_id
   WHERE s.age > 23 AND d.dept_name = 'Computer Science';
   ```
3. Observe the side-by-side comparison:
   - Left tree: unoptimized join with filter on top.
   - Right tree: filter on `s.age` pushed to Student; filter on `d.dept_name` pushed to Department!
   - Selected Physical Operator: **HashJoin** with cost explanation.

---

## Step 4: AI Natural Language Interface
1. Go to **Query Studio** -> **Natural Language to SQL**.
2. Enter:
   > *"Show all students above age 23 in the ECE branch with CGPA above 8.0"*
3. Click **Translate to SQL**:
   - Show that Gemini produced a clean, valid SELECT query without hallucinating columns.
4. Click **Execute Generated SQL**:
   - Point out that the AI-generated SQL flowed through the **exact same compiler pipeline** as raw SQL.

---

## Step 5: Error Handling & Diagnostics
1. Go to **Demo Showcase** -> **Error Diagnostic Scenarios**:
   - Run **Lexical Error** (`SELECT # FROM Student;`) -> Show lexer diagnostic.
   - Run **Syntax Error** (`SELECT FROM Student;`) -> Show parser diagnostic.
   - Run **Semantic Error** (`SELECT unknown_column FROM Student;`) -> Show semantic diagnostic.
   - Emphasize: compilation stopped immediately without executing invalid queries.
