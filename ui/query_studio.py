"""
QueryOpt AI — Query Studio
==========================
Interactive query execution workshop supporting both direct SQL input and
AI-assisted Natural Language to SQL translation.
"""

import time
import pandas as pd
import streamlit as st


def render_query_studio(pipeline):
    """Render the Query Studio page."""
    st.title("Query Studio")
    st.markdown("Compile, optimize, and execute SQL or Natural Language queries.")

    tab_sql, tab_nl = st.tabs(["✍️ SQL Query Editor", "🤖 Natural Language to SQL"])

    # ------------------------------------------------------------------------
    # TAB 1: SQL Query
    # ------------------------------------------------------------------------
    with tab_sql:
        st.markdown("Enter an SQL query directly to run it through the 7-stage compilation pipeline.")

        default_sql = st.session_state.get(
            "studio_sql",
            "SELECT s.name, d.dept_name, s.cgpa\nFROM Student s\nINNER JOIN Department d\nON s.dept_id = d.dept_id\nWHERE s.age > 23 AND s.cgpa >= 8.5\nORDER BY s.cgpa DESC\nLIMIT 10;",
        )

        sql_input = st.text_area(
            "SQL Statement",
            value=default_sql,
            height=140,
            key="sql_text_area",
            help="Enter any SELECT query supported by the compiler grammar.",
        )

        col1, col2 = st.columns([1, 4])
        with col1:
            run_btn = st.button("🚀 Compile & Run", type="primary", key="run_sql_btn")

        if run_btn:
            with st.spinner("Compiling and executing through custom pipeline..."):
                res = pipeline.process_sql(sql_input)
                st.session_state["latest_result"] = res

                # Record in history
                history = st.session_state.setdefault("query_history", [])
                history.append({
                    "timestamp": time.strftime("%H:%M:%S"),
                    "type": "sql",
                    "query": sql_input.strip().replace("\n", " "),
                    "success": res.success,
                    "duration": res.total_time_ms,
                    "rows": res.execution_result.row_count if res.execution_result else 0,
                    "result": res,
                })

            if res.success:
                st.success(
                    f"✅ Query successfully compiled and executed in **{res.total_time_ms:.2f} ms**! "
                    f"Retrieved **{res.execution_result.row_count} rows**."
                )
            else:
                st.error(f"❌ **{res.error_stage} Failed**:\n\n{res.error_message}")

    # ------------------------------------------------------------------------
    # TAB 2: Natural Language Query
    # ------------------------------------------------------------------------
    with tab_nl:
        st.markdown("Describe what data you want in plain English. The AI model will translate it into a schema-aware SQL query.")

        nl_input = st.text_input(
            "Natural Language Request",
            value="Show all students above age 23 in the ECE branch with CGPA above 8.0",
            key="nl_text_input",
            help="Describe your query in English.",
        )

        c1, c2 = st.columns([1, 4])
        with c1:
            translate_btn = st.button("✨ Translate to SQL", key="translate_btn")

        if translate_btn:
            with st.spinner("Translating via Azure OpenAI..."):
                trans_res = pipeline.nl_translator.translate(nl_input)
                st.session_state["generated_translation"] = trans_res

        trans_res = st.session_state.get("generated_translation")
        if trans_res:
            if trans_res.success:
                st.markdown("#### Generated SQL")
                st.code(trans_res.sql, language="sql")
                if trans_res.explanation:
                    st.caption(f"**Explanation**: {trans_res.explanation}")

                # Allow editing before execution
                edited_sql = st.text_area(
                    "Edit Generated SQL if needed:",
                    value=trans_res.sql,
                    height=100,
                    key="edited_nl_sql",
                )

                if st.button("🚀 Execute Generated SQL", type="primary", key="exec_nl_btn"):
                    with st.spinner("Processing through compiler pipeline..."):
                        res = pipeline.process_sql(edited_sql)
                        res.input_query = nl_input
                        res.input_type = "natural_language"
                        res.generated_sql = edited_sql
                        res.translation_info = trans_res
                        st.session_state["latest_result"] = res

                        history = st.session_state.setdefault("query_history", [])
                        history.append({
                            "timestamp": time.strftime("%H:%M:%S"),
                            "type": "natural_language",
                            "query": nl_input,
                            "generated_sql": edited_sql,
                            "success": res.success,
                            "duration": res.total_time_ms,
                            "rows": res.execution_result.row_count if res.execution_result else 0,
                            "result": res,
                        })

                    if res.success:
                        st.success(f"✅ Executed in **{res.total_time_ms:.2f} ms**! Retrieved **{res.execution_result.row_count} rows**.")
                    else:
                        st.error(f"❌ **{res.error_stage} Failed**:\n\n{res.error_message}")
            else:
                st.error(f"❌ Translation failed: {trans_res.error}")

    # ------------------------------------------------------------------------
    # FULL RESULTS DISPLAY ON QUERY STUDIO PAGE
    # ------------------------------------------------------------------------
    latest = st.session_state.get("latest_result")
    if latest:
        st.markdown("---")
        st.subheader("📋 Execution Results & Pipeline Summary")

        if latest.success and latest.execution_result:
            er = latest.execution_result
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Total Rows", er.row_count)
            with m2:
                st.metric("Volcano Engine Latency", f"{er.execution_time_ms:.2f} ms")
            with m3:
                st.metric("Storage Rows Scanned", er.rows_scanned)
            with m4:
                match_val = "✅ 100% Match" if latest.results_match is True else "⚠️ Match" if latest.results_match is False else "N/A"
                st.metric("SQLite Verification", match_val)

            if er.rows:
                df = pd.DataFrame(er.rows)
                df.columns = [c.split(".")[-1] for c in df.columns]
                st.dataframe(df, use_container_width=True)

                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Download Result as CSV", csv, "query_results.csv", "text/csv")
            else:
                st.info("Query returned 0 rows.")

            st.markdown("💡 *To see intermediate AST, tokens, and plan trees, open **Pipeline Inspector** in the sidebar.*")
        elif not latest.success:
            st.error(f"❌ **Error in [{latest.error_stage}]**:\n\n{latest.error_message}")
