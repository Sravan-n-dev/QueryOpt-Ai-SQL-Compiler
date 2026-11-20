"""
QueryOpt AI — Schema Explorer
=============================
Inspects live SQLite catalog tables, data types, indexes, and sample records.
"""

import pandas as pd
import streamlit as st
from database.catalog import get_all_tables, get_table_stats


def render_schema_explorer(pipeline):
    """Render the interactive database schema catalog explorer."""
    st.title("Schema Explorer")
    st.markdown("Browse physical tables, schema profiles, cardinality statistics, and indexes in the College Database.")

    conn = pipeline.conn
    tables = get_all_tables(conn)

    selected_table = st.selectbox("Select a Relation:", tables, index=0 if tables else None)

    if selected_table:
        stats = get_table_stats(conn, selected_table)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Records", f"{stats.row_count:,}")
        with col2:
            st.metric("Columns", len(stats.columns))
        with col3:
            st.metric("Indexes", len(stats.indexes))

        st.markdown("---")

        # Column profile table
        st.subheader(f"Table Profile: `{selected_table}`")
        col_data = [
            {
                "Column": col.name,
                "Type": col.data_type,
                "Distinct Values": col.num_distinct,
                "Min Value": str(col.min_val) if col.min_val is not None else "NULL",
                "Max Value": str(col.max_val) if col.max_val is not None else "NULL",
                "Null Count": col.null_count,
            }
            for col in stats.columns
        ]
        st.dataframe(pd.DataFrame(col_data), use_container_width=True, hide_index=True)

        # Indexes
        if stats.indexes:
            st.subheader("B-Tree Indexes")
            idx_data = [
                {
                    "Index Name": idx.name,
                    "Indexed Columns": ", ".join(idx.columns),
                    "Unique": "Yes" if idx.is_unique else "No",
                }
                for idx in stats.indexes
            ]
            st.dataframe(pd.DataFrame(idx_data), use_container_width=True, hide_index=True)

        # Sample Records
        st.subheader("Sample Records (First 5 Rows)")
        cursor = conn.cursor()
        cursor.execute(f'SELECT * FROM "{selected_table}" LIMIT 5')
        sample_cols = [d[0] for d in cursor.description]
        sample_rows = cursor.fetchall()
        df_sample = pd.DataFrame([dict(zip(sample_cols, r)) for r in sample_rows])
        st.dataframe(df_sample, use_container_width=True, hide_index=True)
