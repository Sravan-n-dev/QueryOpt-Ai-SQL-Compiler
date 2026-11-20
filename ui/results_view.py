"""
QueryOpt AI — Results Viewer
============================
Interactive table view of query results with CSV export and column metrics.
"""

import pandas as pd
import streamlit as st


def render_results_view(pipeline):
    """Render the full query execution results table."""
    st.title("Query Results Viewer")

    res = st.session_state.get("latest_result")
    if not res:
        st.info("No query results to display. Please execute a query in **Query Studio** first.")
        return

    st.markdown(f"**Executed Statement**: `{res.generated_sql or res.input_query}`")

    if not res.success or not res.execution_result:
        st.error(f"Query execution was unsuccessful: {res.error_message}")
        return

    er = res.execution_result
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total Rows", er.row_count)
    with c2:
        st.metric("Execution Time", f"{er.execution_time_ms:.2f} ms")
    with c3:
        st.metric("Rows Scanned", er.rows_scanned)

    st.markdown("---")

    if er.rows:
        df = pd.DataFrame(er.rows)
        # Clean qualified column names for cleaner display
        df.columns = [c.split(".")[-1] for c in df.columns]

        st.dataframe(df, use_container_width=True)

        # CSV Download button
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Export Results to CSV",
            data=csv_data,
            file_name="query_results.csv",
            mime="text/csv",
        )
    else:
        st.info("Query returned 0 rows.")
