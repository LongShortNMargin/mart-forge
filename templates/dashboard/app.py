"""Dashboard skeleton for a mart-forge mart.

Required by SPEC §8.5 (Dashboard Contract):
- Render real visualizations (not metric-cards-only).
- Display per-metric link-status badges.
- Distinguish fixture mode from live mode visually.
- Render a coverage badge: "Data Loaded N/M | DQC Verified N/M".
"""

import json
import os
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WAREHOUSE_PATH = os.environ.get("WAREHOUSE_PATH", "warehouse.duckdb")
MART_MODE = os.environ.get("MART_MODE", "fixture")  # fixture | live
COVERAGE_MANIFEST = Path("coverage_manifest.json")
DQC_SCORECARD = Path("dqc_scorecard.json")

STATUS_BADGE = {
    "verified": "[verified]",
    "proxy": "[proxy]",
    "stale": "[stale]",
    "unsupported": "[unsupported]",
    "pending": "[pending]",
    "error": "[error]",
}


# ---------------------------------------------------------------------------
# Connection (cached)
# ---------------------------------------------------------------------------

@st.cache_resource
def get_conn() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(WAREHOUSE_PATH, read_only=True)


@st.cache_data(ttl=300)
def load_dashboard_table(table_name: str) -> pd.DataFrame:
    return get_conn().execute(f"SELECT * FROM {table_name}").df()


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------

def metric_with_badge(label: str, value: str, status: str) -> None:
    """Render a single metric with its honest-label status badge."""
    badge = STATUS_BADGE.get(status, "[?]")
    st.metric(label=f"{label} {badge}", value=value)


def coverage_badge() -> str:
    if not COVERAGE_MANIFEST.exists():
        return "Coverage manifest missing"
    try:
        cov = json.loads(COVERAGE_MANIFEST.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        return f"Coverage manifest unreadable: {exc}"
    verified = cov.get("verified_count", 0)
    planned = cov.get("planned_count", 0)
    return f"Data Loaded {verified}/{planned} | DQC Verified {verified}/{planned}"


def render_mode_banner() -> None:
    if MART_MODE == "fixture":
        st.warning("FIXTURE / DEMO MODE — values are from static fixtures")
    else:
        st.success("LIVE MODE — values are from the live warehouse")


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------

st.set_page_config(page_title="mart-forge dashboard", layout="wide")
st.title("Mart Dashboard")
render_mode_banner()
st.caption(coverage_badge())

# Replace <ads_table> with the actual ADS-layer model name for this mart.
ads_table = "<prefix>_ads_<use_case>"

try:
    df = load_dashboard_table(ads_table)
except duckdb.CatalogException:
    st.error(f"ADS table `{ads_table}` not found. Run `dbt build` first.")
    st.stop()
except Exception as exc:
    st.error(f"Failed to load table `{ads_table}`: {type(exc).__name__}: {exc}")
    st.stop()

# ---------------------------------------------------------------------------
# Example panels (replace with metrics specified in TDD §T-17)
# ---------------------------------------------------------------------------

col_a, col_b, col_c = st.columns(3)

with col_a:
    metric_with_badge(
        label="Total rows",
        value=str(len(df)),
        status="verified",
    )

with col_b:
    metric_with_badge(
        label="Example native metric",
        value="--",
        status=str(df["<metric_1>_status"].iloc[0]) if "<metric_1>_status" in df.columns else "pending",
    )

with col_c:
    metric_with_badge(
        label="Example derived metric",
        value="--",
        status="pending",
    )

# Example chart — replace with real visualizations per T-17.
if "<grouping_key>" in df.columns and "<measure>" in df.columns:
    fig = px.bar(df, x="<grouping_key>", y="<measure>", title="Example by group")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Edit `dashboard/app.py` to add the visualizations specified in TDD §T-17.")
