"""
QueryOpt AI — Demonstration Showcase
====================================
Interactive preset demonstration gallery featuring all mandatory academic
SQL queries, natural language queries, and compiler error diagnostics.
"""

import time
import pandas as pd
import streamlit as st
from relational_algebra.visualizer import ra_to_dot, ra_to_text_tree

DEMO_SQL_QUERIES = [
    {
        "title": "Example 1: Simple Selection (Filter Pushdown)",
        "desc": "Single-table selection demonstrating predicate pushdown into the scan operator.",
        "sql": "SELECT *\nFROM Student\nWHERE age > 23\nLIMIT 10;",
    },
    {
        "title": "Example 2: Projection and Selection (Pruning)",
        "desc": "Projection combined with equality selection, demonstrating attribute reduction.",
        "sql": "SELECT name, cgpa\nFROM Student\nWHERE branch = 'ECE'\nLIMIT 10;",
    },
    {
        "title": "Example 3: Multiple Conjunctive Predicates",
        "desc": "Conjunctive condition split by selection simplification and pushed down.",
        "sql": "SELECT name, age\nFROM Student\nWHERE age > 23 AND branch = 'ECE'\nLIMIT 10;",
    },
    {
        "title": "Example 4: Two-Table INNER JOIN (Hash Join Selection)",
        "desc": "Student-Department join evaluated by CBO; Hash Join chosen over Nested Loop.",
        "sql": "SELECT s.name, d.dept_name\nFROM Student s\nINNER JOIN Department d\nON s.dept_id = d.dept_id\nLIMIT 10;",
    },
    {
        "title": "Example 5: JOIN with Multi-Table Filtering",
        "desc": "Predicate on Student pushed to left child; predicate on Department pushed to right child.",
        "sql": "SELECT s.name, d.dept_name\nFROM Student s\nINNER JOIN Department d\nON s.dept_id = d.dept_id\nWHERE s.age > 23 AND d.dept_name = 'Computer Science'\nLIMIT 10;",
    },
    {
        "title": "Example 6: Multi-Table 3-Way JOIN (Student + Enrollment + Course)",
        "desc": "3-relation join with marks filter. Hash join pipelines evaluated.",
        "sql": "SELECT s.name, c.course_name, e.marks\nFROM Student s\nINNER JOIN Enrollment e\nON s.student_id = e.student_id\nINNER JOIN Course c\nON e.course_id = c.course_id\nWHERE e.marks > 80\nLIMIT 10;",
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

    # ------------------------------------------------------------------------
    # LIVE OUTPUT VIEWER ON DEMO PAGE
    # ------------------------------------------------------------------------
    latest = st.session_state.get("latest_result")
    if latest:
        st.markdown("---")
        st.subheader("📋 Query Execution Output")
        st.markdown(f"**Executed Query**: `{latest.generated_sql or latest.input_query}`")

        if latest.success and latest.execution_result:
            er = latest.execution_result
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Rows Output", er.row_count)
            with c2:
                st.metric("Volcano Execution Time", f"{er.execution_time_ms:.2f} ms")
            with c3:
                st.metric("Rows Scanned", er.rows_scanned)
            with c4:
                match_icon = "✅ 100% Match" if latest.results_match is True else "⚠️ Order Diff" if latest.results_match is False else "N/A"
                st.metric("SQLite Equivalence", match_icon)

            if er.rows:
                df = pd.DataFrame(er.rows)
                df.columns = [c.split(".")[-1] for c in df.columns]
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Query executed successfully but returned 0 rows.")

            # Quick show optimization summary
            if latest.applied_rules:
                st.markdown(f"**Optimizations Applied ({len(latest.applied_rules)})**:")
                for r in latest.applied_rules:
                    st.markdown(f"- ⚡ **{r.rule_name}**: {r.description}")

            if latest.optimization_report and latest.optimization_report.operator_choices:
                st.markdown("**Physical Operator Decisions:**")
                for ch in latest.optimization_report.operator_choices:
                    st.markdown(f"- 🎯 **{ch.strategy}**: {ch.reason}")

        else:
            st.error(f"❌ **Compilation Error at [{latest.error_stage}]**:\n\n{latest.error_message}")


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
