"""
QueryOpt AI — Streamlit Main Application Router
===============================================
Orchestrates page routing, UI theme styling, and session state persistence.
"""

import streamlit as st
from pipeline import QueryPipeline
from ui.dashboard import render_dashboard
from ui.demo import render_demo_gallery
from ui.history import render_query_history
from ui.optimization_view import render_optimization_dashboard
from ui.pipeline_view import render_pipeline_inspector
from ui.query_studio import render_query_studio
from ui.results_view import render_results_view
from ui.schema_view import render_schema_explorer


def init_session():
    """Ensure pipeline and session state objects are initialized."""
    if "pipeline" not in st.session_state:
        st.session_state["pipeline"] = QueryPipeline()
    if "query_history" not in st.session_state:
        st.session_state["query_history"] = []


def apply_custom_css():
    """Inject clean modern database IDE aesthetics."""
    st.markdown("""
    <style>
        /* Card containers */
        .metric-card {
            background-color: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        /* Tab formatting */
        .stTabs [data-baseweb="tab-list"] {
            gap: 1.5rem;
        }
        .stTabs [data-baseweb="tab"] {
            font-size: 1.05rem;
            font-weight: 600;
        }
        /* Sidebar branding */
        .sidebar-brand {
            font-size: 1.3rem;
            font-weight: 700;
            color: #1E88E5;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #e0e0e0;
            margin-bottom: 1rem;
        }
    </style>
    """, unsafe_allow_html=True)


def main():
    st.set_page_config(
        page_title="QueryOpt AI — SQL Compiler & Optimizer",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_session()
    apply_custom_css()

    pipeline = st.session_state["pipeline"]

    # Sidebar Navigation
    with st.sidebar:
        st.markdown('<div class="sidebar-brand">🔍 QueryOpt AI</div>', unsafe_allow_html=True)
        st.caption("Compiler Design & Query Optimization")

        page = st.radio(
            "Navigation",
            [
                "🏠 Dashboard",
                "✍️ Query Studio",
                "🔬 Pipeline Inspector",
                "📊 Optimization Dashboard",
                "📋 Results Viewer",
                "🗄️ Schema Explorer",
                "📜 Query History",
                "🎯 Demo Showcase",
            ],
            index=0,
        )

        st.markdown("---")
        ai_status = "🟢 Active" if pipeline.nl_translator.is_available() else "⚪ Not Configured"
        st.markdown(f"**Gemini AI Engine**: {ai_status}")
        st.caption("B.Tech Compiler Design Project")

    # Routing
    if page == "🏠 Dashboard":
        render_dashboard(pipeline)
    elif page == "✍️ Query Studio":
        render_query_studio(pipeline)
    elif page == "🔬 Pipeline Inspector":
        render_pipeline_inspector(pipeline)
    elif page == "📊 Optimization Dashboard":
        render_optimization_dashboard(pipeline)
    elif page == "📋 Results Viewer":
        render_results_view(pipeline)
    elif page == "🗄️ Schema Explorer":
        render_schema_explorer(pipeline)
    elif page == "📜 Query History":
        render_query_history(pipeline)
    elif page == "🎯 Demo Showcase":
        render_demo_gallery(pipeline)


if __name__ == "__main__":
    main()
