"""
QueryOpt AI — Compiler Pipeline Inspector
=========================================
Deep-dive inspection tool for every stage of query compilation and optimization.
"""

import pandas as pd
import streamlit as st
from relational_algebra.visualizer import ra_to_dot, ra_to_text_tree


def render_pipeline_inspector(pipeline):
    """Render the detailed stage-by-stage compiler pipeline inspector."""
    st.title("Compiler Pipeline Inspector")
    st.markdown("Inspect intermediate representations across every stage of the custom SQL compilation pipeline.")

    res = st.session_state.get("latest_result")
    if not res:
        st.info("No query has been compiled yet. Run a query in **Query Studio** or select one from **Demo Queries**.")
        return

    st.markdown(f"**Target Query**: `{res.generated_sql or res.input_query}`")

    # Status ribbon across all stages
    st.subheader("Pipeline Stages Execution Status")
    cols = st.columns(len(res.stages))
    for idx, (col, stage) in enumerate(zip(cols, res.stages)):
        with col:
            icon = "✅" if stage.status == "success" else "❌" if stage.status == "error" else "⏳"
            st.markdown(f"**{icon} Stage {stage.stage_number}**")
            st.caption(f"{stage.stage_name}<br/>`{stage.duration_ms:.2f} ms`", unsafe_allow_html=True)

    st.markdown("---")

    # Expandable detail views for each stage
    # ------------------------------------------------------------------------
    # STAGE 1: Lexical Analysis
    # ------------------------------------------------------------------------
    with st.expander("🔍 Stage 1: Lexical Analysis (Tokens Stream)", expanded=True):
        st.markdown("Token stream produced by the Lark SQL lexer terminal specifications:")
        if res.tokens:
            tok_data = [
                {
                    "Index": i,
                    "Type": tok.type,
                    "Value": repr(tok.value),
                    "Line": tok.line,
                    "Column": tok.column,
                    "Span": f"[{tok.pos_start}:{tok.pos_end}]",
                }
                for i, tok in enumerate(res.tokens)
            ]
            st.dataframe(pd.DataFrame(tok_data), use_container_width=True, hide_index=True)
        else:
            st.caption("No tokens captured.")

    # ------------------------------------------------------------------------
    # STAGE 2: Syntax Analysis (AST)
    # ------------------------------------------------------------------------
    with st.expander("🌳 Stage 2: Syntax Analysis & Abstract Syntax Tree (AST)", expanded=False):
        st.markdown("Parsed concrete syntax transformed into strongly typed Abstract Syntax Tree (AST) nodes:")
        if res.ast:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**AST Pretty Print Representation**")
                st.code(res.ast.pretty_print(), language="python")
            with c2:
                st.markdown("**Structured AST JSON Schema**")
                st.json(res.ast.to_dict())
        else:
            st.caption("AST was not generated due to an earlier error.")

    # ------------------------------------------------------------------------
    # STAGE 3: Semantic Analysis
    # ------------------------------------------------------------------------
    with st.expander("🛡️ Stage 3: Semantic Analysis & Catalog Validation", expanded=False):
        if res.semantic_valid:
            st.success("✅ **Semantic Validation Passed**: All referenced tables, columns, aliases, and data types verified against live SQLite catalog.")
        else:
            st.error(f"❌ **Semantic Validation Failed**: {res.error_message}")

    # ------------------------------------------------------------------------
    # STAGE 4: Relational Algebra (Canonical)
    # ------------------------------------------------------------------------
    with st.expander("📐 Stage 4: Relational Algebra Tree (Before Optimization)", expanded=False):
        st.markdown("Canonical relational algebra operator tree ($\pi$, $\sigma$, $\\bowtie$, Scan) before rewrite rules:")
        if res.ra_tree:
            c1, c2 = st.columns([1, 1])
            with c1:
                st.markdown("**Textual Operator Tree**")
                st.code(ra_to_text_tree(res.ra_tree), language="text")
            with c2:
                st.markdown("**Graphviz Logical Plan Tree**")
                dot_str = ra_to_dot(res.ra_tree)
                st.graphviz_chart(dot_str)

    # ------------------------------------------------------------------------
    # STAGE 5: Logical Optimization
    # ------------------------------------------------------------------------
    with st.expander("⚡ Stage 5: Logical Query Optimizer (Rewrite Rules)", expanded=False):
        st.markdown("Transformed relational algebra tree after algebraic rewrites (Predicate Pushdown, Projection Pushdown, Constant Folding):")
        if res.ra_tree_optimized:
            c1, c2 = st.columns([1, 1])
            with c1:
                st.markdown("**Optimized Operator Tree**")
                st.code(ra_to_text_tree(res.ra_tree_optimized), language="text")
                if res.applied_rules:
                    st.markdown("**Applied Optimization Rules:**")
                    for rule in res.applied_rules:
                        st.markdown(f"- **{rule.rule_name}**: {rule.description}")
                else:
                    st.info("Plan was already in canonical optimal form; no rewrites needed.")
            with c2:
                st.markdown("**Optimized Graphviz Tree**")
                dot_str = ra_to_dot(res.ra_tree_optimized)
                st.graphviz_chart(dot_str)

    # ------------------------------------------------------------------------
    # STAGE 6: Cost-Based Optimizer & Physical Plan
    # ------------------------------------------------------------------------
    with st.expander("📊 Stage 6: Cost-Based Optimization & Physical Plan", expanded=False):
        st.markdown("Selected physical execution operators with estimated I/O + CPU cost annotations:")
        if res.physical_plan and res.optimization_report:
            rep = res.optimization_report
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Estimated Cost", f"{rep.optimized_cost:.2f} units")
            with m2:
                st.metric("Baseline Estimated Cost", f"{rep.baseline_cost:.2f} units")
            with m3:
                st.metric("Estimated Output Rows", f"{rep.estimated_output_rows:.0f}")

            st.markdown("**Physical Operator Tree:**")
            st.code(res.physical_plan.pretty_print(), language="text")

            if rep.operator_choices:
                st.markdown("**Optimizer Operator Decisions:**")
                for ch in rep.operator_choices:
                    st.markdown(f"- **{ch.strategy}** (est. cost {ch.estimated_cost:.2f}): {ch.reason}")

    # ------------------------------------------------------------------------
    # STAGE 7: Physical Execution Results
    # ------------------------------------------------------------------------
    with st.expander("⚙️ Stage 7: Volcano Physical Engine Execution", expanded=False):
        if res.execution_result:
            er = res.execution_result
            e1, e2, e3 = st.columns(3)
            with e1:
                st.metric("Volcano Execution Time", f"{er.execution_time_ms:.2f} ms")
            with e2:
                st.metric("Rows Output", er.row_count)
            with e3:
                st.metric("Storage Rows Scanned", er.rows_scanned)
