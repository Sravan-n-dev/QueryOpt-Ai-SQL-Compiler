"""
QueryOpt AI — System Dashboard
==============================
High-level observability overview: catalog metrics, compiler health,
database status, and AI integration availability.
"""

import streamlit as st
from config.database_config import get_connection
from database.catalog import get_all_tables, get_table_stats


def render_dashboard(pipeline):
    """Render the main system overview dashboard."""
    st.markdown("""
    <div style="padding: 1.5rem 0; margin-bottom: 1rem;">
        <h1 style="font-size: 2.3rem; font-weight: 700; color: #1E88E5; margin-bottom: 0.2rem;">
            QueryOpt AI
        </h1>
        <p style="font-size: 1.15rem; color: #555; margin-top: 0;">
            Intelligent SQL Query Compiler, Cost-Based Optimizer & Natural Language Interface
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 1. Status metrics
    conn = pipeline.conn
    tables = get_all_tables(conn)

    total_records = 0
    total_indexes = 0
    for tbl in tables:
        stats = get_table_stats(conn, tbl)
        total_records += stats.row_count
        total_indexes += len(stats.indexes)

    ai_available = pipeline.nl_translator.is_available()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Database Tables", len(tables), help="Total user relations in SQLite storage")
    with col2:
        st.metric("Total Records", f"{total_records:,}", help="Total seeded records across all tables")
    with col3:
        st.metric("B-Tree Indexes", total_indexes, help="Active secondary and primary key indexes")
    with col4:
        st.metric(
            "AI NL2SQL Engine",
            "Active" if ai_available else "Not Configured",
            delta="Ready" if ai_available else "Requires API Key",
            delta_color="normal" if ai_available else "inverse",
        )

    st.markdown("---")

    # 2. Architecture cards
    st.subheader("Compiler & Optimization Pipeline Architecture")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        **Stage 1-3: Frontend**
        - **Lexer**: Lark EBNF tokenization stream
        - **Parser**: AST construction with typed dataclasses
        - **Semantic Analyzer**: Schema catalog validation, type checks & alias resolution
        """)
    with c2:
        st.markdown("""
        **Stage 4-5: Logical Planning**
        - **Relational Algebra**: $\\sigma$, $\\pi$, $\\bowtie$, $\\tau$, $\\delta$ operator tree
        - **Rewrite Rules**: Predicate pushdown, projection pruning, constant folding
        - **Fixed-Point Engine**: Iterative algebraic transformations
        """)
    with c3:
        st.markdown("""
        **Stage 6-7: Physical Engine**
        - **Cost-Based Optimizer**: Catalog statistics & selectivity estimation
        - **Operator Selection**: TableScan vs IndexScan, HashJoin vs NestedLoop
        - **Volcano Engine**: Pure demand-driven iterator pipeline (`open/next/close`)
        """)

    st.markdown("---")

    # 3. Recent activity
    st.subheader("Recent Execution Activity")
    history = st.session_state.get("query_history", [])
    if history:
        for idx, item in enumerate(reversed(history[-5:])):
            status_icon = "✅" if item.get("success") else "❌"
            st.markdown(
                f"- **{status_icon} [{item.get('type').upper()}]** `{item.get('query')}` — "
                f"*{item.get('duration', 0):.2f} ms* ({item.get('rows', 0)} rows)"
            )
    else:
        st.info("No queries executed in this session yet. Navigate to **Query Studio** or **Demo Queries** to start compiling!")
