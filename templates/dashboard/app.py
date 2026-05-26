"""
mart-forge Dashboard Template
=============================
Streamlit skeleton for visualizing mart-forge DWH output.
Supports dual-mode connection: MotherDuck (cloud) or local DuckDB.

Usage:
    streamlit run app.py

Environment variables:
    MOTHERDUCK_TOKEN  - If set, connects to MotherDuck cloud. Otherwise uses local DuckDB.
    DUCKDB_PATH       - Path to local DuckDB file (default: ./mart.duckdb)
"""

import os
import json

import streamlit as st
import duckdb


# ---------------------------------------------------------------------------
# Connection setup: MotherDuck vs Local DuckDB
# ---------------------------------------------------------------------------

def get_connection():
    """
    Return a DuckDB connection.
    - If MOTHERDUCK_TOKEN is set, connect to MotherDuck.
    - Otherwise, connect to a local DuckDB file.
    """
    md_token = os.environ.get("MOTHERDUCK_TOKEN")
    if md_token:
        conn = duckdb.connect(f"md:?motherduck_token={md_token}")
        return conn, "cloud"
    else:
        db_path = os.environ.get("DUCKDB_PATH", "./mart.duckdb")
        conn = duckdb.connect(db_path)
        return conn, "local"


# ---------------------------------------------------------------------------
# Link-status display helpers
# ---------------------------------------------------------------------------

LINK_STATUS_CONFIG = {
    "exact": {
        "badge": "Verified",
        "color": "green",
        "description": "Verified link to authoritative source",
    },
    "proxy": {
        "badge": "Advisory",
        "color": "orange",
        "description": "Directional match via proxy metric",
    },
    "unsupported": {
        "badge": "No Comparator",
        "color": "red",
        "description": "No external comparator available",
    },
    "unverified": {
        "badge": "Unverified",
        "color": "gray",
        "description": "Verification not yet attempted",
    },
}


def render_link_status_badge(status: str) -> str:
    """Return a colored markdown badge for the given link_status value."""
    config = LINK_STATUS_CONFIG.get(status, LINK_STATUS_CONFIG["unverified"])
    return f":{config['color']}[{config['badge']}]"


def render_coverage_badge(total_metrics: int, verified_count: int) -> str:
    """Return a coverage ratio string for display."""
    pct = round(verified_count / total_metrics * 100) if total_metrics > 0 else 0
    return f"{verified_count}/{total_metrics} metrics verified ({pct}%)"


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="mart-forge Dashboard",
    page_icon="📊",
    layout="wide",
)

st.title("mart-forge Dashboard")

conn, mode = get_connection()

# ---------------------------------------------------------------------------
# Mode banner
# ---------------------------------------------------------------------------

if mode == "cloud":
    st.success("Connected to **MotherDuck** (cloud mode)")
else:
    st.info("Connected to **local DuckDB** (fixture/dev mode)")

# ---------------------------------------------------------------------------
# Sidebar: filters
# ---------------------------------------------------------------------------

st.sidebar.header("Filters")

# TODO: Replace with actual date range from your ADS table
date_range = st.sidebar.date_input(
    "Date range",
    value=[],
    help="Select start and end dates to filter the dashboard",
)

# TODO: Add entity-specific filters
# entity_filter = st.sidebar.multiselect(
#     "Select entities",
#     options=["all"],  # Populate from dim table
#     default=["all"],
# )

# ---------------------------------------------------------------------------
# Coverage badge
# ---------------------------------------------------------------------------

st.sidebar.markdown("---")
st.sidebar.subheader("Metric Coverage")

# TODO: Replace with actual metric metadata query
# Example: query a metadata table or hardcode from BRD
total_metrics = 0  # TODO
verified_count = 0  # TODO
st.sidebar.markdown(render_coverage_badge(total_metrics, verified_count))

# TODO: Render per-metric link status badges
# metrics_meta = [
#     {"name": "metric_1", "link_status": "exact"},
#     {"name": "metric_2", "link_status": "proxy"},
#     {"name": "metric_3", "link_status": "unsupported"},
# ]
# for m in metrics_meta:
#     badge = render_link_status_badge(m["link_status"])
#     st.sidebar.markdown(f"- **{m['name']}**: {badge}")

# ---------------------------------------------------------------------------
# Chart 1: Time-series trend
# ---------------------------------------------------------------------------

st.subheader("Trend Over Time")

# TODO: Replace with actual query against your ADS layer
# Example:
# df_trend = conn.execute("""
#     SELECT full_date, total_amount
#     FROM {prefix}_ads_{use_case}
#     ORDER BY full_date
# """).fetchdf()
# st.line_chart(df_trend.set_index("full_date"))

st.info("TODO: Connect this chart to your ADS table. Use `st.line_chart()` or `st.plotly_chart()`.")

# ---------------------------------------------------------------------------
# Chart 2: Category breakdown (bar chart)
# ---------------------------------------------------------------------------

st.subheader("Breakdown by Category")

# TODO: Replace with actual query
# Example:
# df_category = conn.execute("""
#     SELECT category_name, SUM(order_count) AS total_orders
#     FROM {prefix}_ads_{use_case}
#     GROUP BY category_name
#     ORDER BY total_orders DESC
#     LIMIT 20
# """).fetchdf()
# st.bar_chart(df_category.set_index("category_name"))

st.info("TODO: Connect this chart to your ADS table. Use `st.bar_chart()` or `st.plotly_chart()`.")

# ---------------------------------------------------------------------------
# Chart 3: KPI scorecards
# ---------------------------------------------------------------------------

st.subheader("Key Performance Indicators")

col1, col2, col3 = st.columns(3)

# TODO: Replace with actual metric queries
# Example:
# row = conn.execute("""
#     SELECT
#         SUM(total_amount) AS revenue,
#         SUM(order_count) AS orders,
#         SUM(unique_customers) AS customers
#     FROM {prefix}_ads_{use_case}
# """).fetchone()

with col1:
    st.metric(label="Total Revenue", value="$0", delta=None)
    # st.metric(label="Total Revenue", value=f"${row[0]:,.2f}", delta="+5%")

with col2:
    st.metric(label="Total Orders", value="0", delta=None)
    # st.metric(label="Total Orders", value=f"{row[1]:,}", delta="+12%")

with col3:
    st.metric(label="Unique Customers", value="0", delta=None)
    # st.metric(label="Unique Customers", value=f"{row[2]:,}", delta="+3%")

# ---------------------------------------------------------------------------
# Link-status reference table
# ---------------------------------------------------------------------------

st.markdown("---")
st.subheader("Metric Link Status Reference")

link_status_df_data = []
for status, cfg in LINK_STATUS_CONFIG.items():
    link_status_df_data.append({
        "Status": status,
        "Badge": cfg["badge"],
        "Description": cfg["description"],
    })

st.table(link_status_df_data)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown("---")
st.caption("Built with mart-forge | Kimball DWH Framework")

conn.close()
