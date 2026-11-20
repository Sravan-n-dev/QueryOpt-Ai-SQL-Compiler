"""
QueryOpt AI — Demonstration Showcase
====================================
Interactive preset demonstration gallery featuring all mandatory academic
SQL queries, natural language queries, and compiler error diagnostics.
"""

import time
import streamlit as st

DEMO_SQL_QUERIES = [
    {
        "title": "Example 1: Simple Selection (Filter Pushdown)",
        "desc": "Single-table selection demonstrating predicate pushdown into the scan operator.",
        "sql": "SELECT *\nFROM Student\nWHERE age > 23;",
    },
    {
        "title": "Example 2: Projection and Selection (Pruning)",
        "desc": "Projection combined with equality selection, demonstrating attribute reduction.",
        "sql": "SELECT name, cgpa\nFROM Student\nWHERE branch = 'ECE';",
    },
    {
        "title": "Example 3: Multiple Conjunctive Predicates",
        "desc": "Conjunctive condition split by selection simplification and pushed down.",
        "sql": "SELECT name, age\nFROM Student\nWHERE age > 23 AND branch = 'ECE';",
    },
    {
        "title": "Example 4: Two-Table INNER JOIN (Hash Join Selection)",
        "desc": "Student-Department join evaluated by CBO; Hash Join chosen over Nested Loop.",
        "sql": "SELECT s.name, d.dept_name\nFROM Student s\nINNER JOIN Department d\nON s.dept_id = d.dept_id;",
    },
    {
        "title": "Example 5: JOIN with Multi-Table Filtering",
        "desc": "Predicate on Student pushed to left child; predicate on Department pushed to right child.",
        "sql": "SELECT s.name, d.dept_name\nFROM Student s\nINNER JOIN Department d\nON s.dept_id = d.dept_id\nWHERE s.age > 23 AND d.dept_name = 'Computer Science';",
    },
    {
        "title": "Example 6: Multi-Table 3-Way JOIN (Student + Enrollment + Course)",
        "desc": "3-relation join with marks filter. Hash join pipelines evaluated.",
        "sql": "SELECT s.name, c.course_name, e.marks\nFROM Student s\nINNER JOIN Enrollment e\nON s.student_id = e.student_id\nINNER JOIN Course c\nON e.course_id = c.course_id\nWHERE e.marks > 80;",
    },
    {
        "title": "Example 7: Sorting and Limiting (Top-K)",
        "desc": "Sort operator τ evaluated in Volcano engine with Limit operator truncation.",
        "sql": "SELECT name, cgpa\nFROM Student\nORDER BY cgpa DESC\nLIMIT 10;",
    },
]

DEMO_NL_QUERIES = [
    {
        "title": "Natural Language Query 1: Age & Branch Filter",
        "prompt": "List out all the students above age 23 whose branch is ECE.",
    },
    {
        "title": "Natural Language Query 2: CSE Department Query",
        "prompt": "Show the names and CGPA of all CSE students.",
    },
    {
        "title": "Natural Language Query 3: Multi-Table High Scorers",
        "prompt": "Find students who scored more than 80 marks in their courses.",
    },
    {
        "title": "Natural Language Query 4: Top Rankers by CGPA",
        "prompt": "List the top 10 students based on CGPA.",
    },
]

DEMO_ERRORS = [
    {
        "title": "Lexical Error (Invalid Character)",
        "desc": "Demonstrates scanner rejecting illegal character '#'.",
        "sql": "SELECT name # age FROM Student;",
        "expected_stage": "Lexical Analysis",
    },
    {
        "title": "Syntax Error (Missing Columns before FROM)",
        "desc": "Demonstrates parser rejecting malformed grammar.",
        "sql": "SELECT FROM Student;",
        "expected_stage": "Syntax Analysis",
    },
    {
        "title": "Semantic Error (Non-Existent Column)",
        "desc": "Catalog analyzer detects unknown column 'unknown_column'.",
        "sql": "SELECT unknown_column FROM Student;",
        "expected_stage": "Semantic Analysis",
    },
    {
        "title": "Semantic Error (Non-Existent Table)",
        "desc": "Catalog analyzer detects unknown table 'UnknownTable'.",
        "sql": "SELECT name FROM UnknownTable;",
        "expected_stage": "Semantic Analysis",
    },
]


def render_demo_gallery(pipeline):
    """Render the academic demonstration showcase."""
    st.title("Academic Demonstration Showcase")
    st.markdown("Run curated textbook examples demonstrating compiler stages, algebraic rewrites, cost decisions, and error diagnostics.")

    tab1, tab2, tab3 = st.tabs(["📚 Core SQL Scenarios", "🤖 Natural Language Scenarios", "🛡️ Error Diagnostic Scenarios"])

    # ------------------------------------------------------------------------
    # TAB 1: SQL Scenarios
    # ------------------------------------------------------------------------
    with tab1:
        for idx, demo in enumerate(DEMO_SQL_QUERIES, 1):
            with st.expander(f"**{demo['title']}**", expanded=False):
                st.caption(demo["desc"])
                st.code(demo["sql"], language="sql")
                if st.button(f"▶️ Run Query {idx}", key=f"run_demo_sql_{idx}"):
                    _run_and_set(pipeline, demo["sql"], "sql")

    # ------------------------------------------------------------------------
    # TAB 2: NL Scenarios
    # ------------------------------------------------------------------------
    with tab2:
        for idx, demo in enumerate(DEMO_NL_QUERIES, 1):
            with st.expander(f"**{demo['title']}**", expanded=False):
                st.markdown(f"**English Prompt**: *\"{demo['prompt']}\"*")
                if st.button(f"🤖 Translate & Run NL {idx}", key=f"run_demo_nl_{idx}"):
                    _run_and_set(pipeline, demo["prompt"], "natural_language")

    # ------------------------------------------------------------------------
    # TAB 3: Error Scenarios
    # ------------------------------------------------------------------------
    with tab3:
        for idx, demo in enumerate(DEMO_ERRORS, 1):
            with st.expander(f"**{demo['title']}**", expanded=False):
                st.caption(demo["desc"])
                st.code(demo["sql"], language="sql")
                if st.button(f"⚠️ Trigger Diagnostic {idx}", key=f"run_demo_err_{idx}"):
                    _run_and_set(pipeline, demo["sql"], "sql")


def _run_and_set(pipeline, query_str: str, mode: str):
    with st.spinner("Processing through compiler pipeline..."):
        if mode == "sql":
            res = pipeline.process_sql(query_str)
        else:
            res = pipeline.process_natural_language(query_str)

        st.session_state["latest_result"] = res

        history = st.session_state.setdefault("query_history", [])
        history.append({
            "timestamp": time.strftime("%H:%M:%S"),
            "type": mode,
            "query": query_str,
            "success": res.success,
            "duration": res.total_time_ms,
            "rows": res.execution_result.row_count if res.execution_result else 0,
            "result": res,
        })

    if res.success:
        st.success(
            f"✅ **Success!** Compiled and executed in **{res.total_time_ms:.2f} ms** "
            f"({res.execution_result.row_count} rows). Open **Pipeline Inspector** or **Optimization Dashboard** to explore."
        )
    else:
        st.error(f"🛡️ **Caught at [{res.error_stage}]**:\n\n{res.error_message}")
