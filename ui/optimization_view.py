"""
QueryOpt AI — Optimization Dashboard
====================================
Side-by-side comparison of plans before and after optimization,
detailing algebraic rewrites, cost model comparisons, and execution metrics.
"""

import streamlit as st
from relational_algebra.visualizer import ra_to_dot, ra_to_text_tree


def render_optimization_dashboard(pipeline):
    """Render the side-by-side optimization comparison dashboard."""
    st.title("Query Optimization Dashboard")
    st.markdown("Compare logical relational algebra trees and physical execution strategies before and after optimization.")

    res = st.session_state.get("latest_result")
    if not res:
        st.info("No query has been compiled yet. Please run a query in **Query Studio** or select a **Demo Query**.")
        return

    st.markdown(f"**Query**: `{res.generated_sql or res.input_query}`")

    # 1. High-level metric highlights
    if res.optimization_report:
        rep = res.optimization_report
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("Baseline Estimated Cost", f"{rep.baseline_cost:.2f}")
        with c2:
            st.metric("Optimized Estimated Cost", f"{rep.optimized_cost:.2f}")
        with c3:
            reduction = max(0.0, (1.0 - (rep.optimized_cost / max(1.0, rep.baseline_cost))) * 100.0)
            st.metric("Estimated Cost Reduction", f"{reduction:.1f}%")
        with c4:
            st.metric("Volcano Execution Time", f"{res.execution_result.execution_time_ms:.2f} ms" if res.execution_result else "N/A")

    st.markdown("---")

    # 2. Side-by-side tree visualizer
    st.subheader("Logical Plan Comparison (Before vs. After)")
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("### 📋 Before Optimization (Canonical RA)")
        if res.ra_tree:
            st.caption("Canonical unoptimized relational algebra tree:")
            st.graphviz_chart(ra_to_dot(res.ra_tree))
            with st.expander("Show Text Tree"):
                st.code(ra_to_text_tree(res.ra_tree), language="text")

    with col_right:
        st.markdown("### ⚡ After Optimization (Rewritten RA)")
        if res.ra_tree_optimized:
            st.caption("Optimized plan with pushed selections and pruned projections:")
            st.graphviz_chart(ra_to_dot(res.ra_tree_optimized))
            with st.expander("Show Text Tree"):
                st.code(ra_to_text_tree(res.ra_tree_optimized), language="text")

    st.markdown("---")

    # 3. Applied transformation rules
    st.subheader("Applied Logical Transformation Rules")
    if res.applied_rules:
        for idx, rule in enumerate(res.applied_rules, 1):
            with st.expander(f"Transformation {idx}: {rule.rule_name}", expanded=True):
                st.markdown(f"**Description**: {rule.description}")
                r_col1, r_col2 = st.columns(2)
                with r_col1:
                    st.markdown("**Subtree Before:**")
                    st.code(rule.before_snippet, language="text")
                with r_col2:
                    st.markdown("**Subtree After:**")
                    st.code(rule.after_snippet, language="text")
    else:
        st.info("No algebraic rewrites applied; the original plan was already canonical.")

    st.markdown("---")

    # 4. Cost-Based Decisions & Operator Alternatives
    st.subheader("Cost-Based Operator Decisions & Alternative Evaluations")
    if res.optimization_report and res.optimization_report.operator_choices:
        for choice in res.optimization_report.operator_choices:
            st.markdown(f"#### 🎯 Selected: `{choice.strategy}` (Est. Cost: {choice.estimated_cost:.2f})")
            st.markdown(f"**Optimizer Rationale**: {choice.reason}")
            if choice.alternatives:
                st.markdown("**Evaluated Alternatives:**")
                import pandas as pd
                df_alts = pd.DataFrame(choice.alternatives)
                st.dataframe(df_alts, hide_index=True)
    else:
        st.caption("No multi-path operator decisions were required for this query.")

    st.markdown("---")

    # 5. Correctness & Reference Equivalence
    st.subheader("Correctness Verification (Volcano Engine vs. SQLite Reference)")
    if res.results_match is True:
        st.success(
            "🎯 **Result Equivalence Verified**: The custom Volcano iterator engine produced "
            "results 100% equivalent to the SQLite reference standard."
        )
    elif res.results_match is False:
        st.warning(
            "⚠️ Results differed from SQLite reference. Note: without explicit ORDER BY, row ordering may naturally vary."
        )
    else:
        st.info("Equivalence comparison skipped or not applicable.")
