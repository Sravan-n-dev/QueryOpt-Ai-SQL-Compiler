"""
QueryOpt AI — Query History
===========================
Maintains an interactive local audit log of all queries compiled during the session.
"""

import pandas as pd
import streamlit as st


def render_query_history(pipeline):
    """Render the query history log."""
    st.title("Query Execution History")

    history = st.session_state.get("query_history", [])

    if not history:
        st.info("No query activity recorded in this session yet.")
        return

    c1, c2 = st.columns([6, 1])
    with c2:
        if st.button("🗑️ Clear History"):
            st.session_state["query_history"] = []
            st.rerun()

    table_data = []
    for idx, item in enumerate(reversed(history)):
        table_data.append({
            "Time": item.get("timestamp"),
            "Mode": item.get("type").upper(),
            "Query": item.get("query"),
            "Status": "✅ Success" if item.get("success") else "❌ Failed",
            "Duration (ms)": f"{item.get('duration', 0):.2f}",
            "Rows": item.get("rows", 0),
        })

    st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)
