"""
GME Options Mart Dashboard
===========================
Streamlit dashboard for GME options analytics.
Dual-mode: MOTHERDUCK_TOKEN env -> md:gme_db; absent -> local DuckDB.
"""
import os
import json
import streamlit as st
import duckdb
import plotly.graph_objects as go
import plotly.express as px


LINK_STATUS_CONFIG = {
    "exact": {"badge": "Verified", "color": "green"},
    "proxy": {"badge": "Advisory", "color": "orange"},
    "unsupported": {"badge": "No Comparator", "color": "red"},
    "unverified": {"badge": "Unverified", "color": "gray"},
}

METRICS_META = [
    {"name": "Spot Price", "link_status": "exact"},
    {"name": "OI by Strike", "link_status": "exact"},
    {"name": "IV per Strike", "link_status": "exact"},
    {"name": "IV30", "link_status": "proxy"},
    {"name": "HV20", "link_status": "proxy"},
    {"name": "Max Pain", "link_status": "unsupported"},
    {"name": "P/C Ratio", "link_status": "exact"},
    {"name": "Net GEX", "link_status": "unsupported"},
    {"name": "IV Rank", "link_status": "proxy"},
]


def get_connection():
    md_token = os.environ.get("MOTHERDUCK_TOKEN")
    if md_token:
        conn = duckdb.connect(f"md:gme_db?motherduck_token={md_token}")
        return conn, "cloud"
    db_path = os.environ.get("DUCKDB_PATH", "target/gme_options.duckdb")
    conn = duckdb.connect(db_path, read_only=True)
    return conn, "local"


def render_badge(status: str) -> str:
    cfg = LINK_STATUS_CONFIG.get(status, LINK_STATUS_CONFIG["unverified"])
    return f":{cfg['color']}[{cfg['badge']}]"


def load_coverage_manifest():
    manifest_path = os.path.join(os.path.dirname(__file__), "..", "coverage_manifest.json")
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            return json.load(f)
    return None


st.set_page_config(page_title="GME Options Dashboard", page_icon="📊", layout="wide")

try:
    conn, mode = get_connection()
except Exception as e:
    st.error(f"Cannot connect to database: {e}")
    st.info("Run `dbt seed && dbt run` first to build the local warehouse.")
    st.stop()

if mode == "cloud":
    st.success("Connected to **MotherDuck** (cloud mode)")
else:
    st.info("Connected to **local DuckDB** (fixture/dev mode)")

st.title("GME Options Analytics Dashboard")

try:
    dashboard_df = conn.execute("SELECT * FROM gme_ads_market_dashboard ORDER BY pull_date").fetchdf()
except Exception as e:
    st.error(f"Dashboard table not found: {e}")
    st.stop()

if dashboard_df.empty:
    st.warning("No data in gme_ads_market_dashboard. Run the pipeline first.")
    st.stop()

latest = dashboard_df.iloc[-1]

st.sidebar.header("Filters")
dates = dashboard_df["pull_date"].sort_values().unique()
if len(dates) > 1:
    date_range = st.sidebar.date_input("Date range", value=[dates[0], dates[-1]])
else:
    st.sidebar.write(f"Single date: {dates[0]}")

st.sidebar.markdown("---")
st.sidebar.subheader("Metric Coverage")
manifest = load_coverage_manifest()
if manifest:
    total = manifest.get("planned_count", 9)
    verified = manifest.get("verified_count", 0)
    pct = round(verified / total * 100) if total > 0 else 0
    st.sidebar.markdown(f"**{verified}/{total}** metrics verified ({pct}%)")

st.sidebar.markdown("---")
st.sidebar.subheader("Link Status")
for m in METRICS_META:
    st.sidebar.markdown(f"- **{m['name']}**: {render_badge(m['link_status'])}")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Spot", f"${latest['spot']:.2f}" if latest['spot'] else "N/A")
with col2:
    st.metric("IV30", f"{latest['iv30']:.2%}" if latest['iv30'] else "N/A")
with col3:
    st.metric("P/C Ratio", f"{latest['pc_ratio']:.2f}" if latest['pc_ratio'] else "N/A")
with col4:
    st.metric("Max Pain", f"${latest['max_pain_strike']:.2f}" if latest['max_pain_strike'] else "N/A")

col5, col6, col7, col8 = st.columns(4)
with col5:
    st.metric("HV20", f"{latest['hv20']:.2%}" if latest['hv20'] else "N/A")
with col6:
    st.metric("Net GEX", f"{latest['net_gex']:,.0f}" if latest['net_gex'] else "N/A")
with col7:
    st.metric("IV Rank", f"{latest['iv_rank']:.2%}" if latest['iv_rank'] else "N/A")
with col8:
    st.metric("Gamma Flip", f"${latest['gamma_flip_point']:.2f}" if latest['gamma_flip_point'] else "N/A")

st.markdown("---")

try:
    gex_df = conn.execute("""
        SELECT strike, call_gex, put_gex, net_gex
        FROM gme_dws_strike_gex_1d
        WHERE pull_date = (SELECT MAX(pull_date) FROM gme_dws_strike_gex_1d)
        ORDER BY strike
    """).fetchdf()

    if not gex_df.empty:
        st.subheader("GEX by Strike")
        fig_gex = go.Figure()
        fig_gex.add_trace(go.Bar(x=gex_df["strike"], y=gex_df["call_gex"], name="Call GEX", marker_color="green"))
        fig_gex.add_trace(go.Bar(x=gex_df["strike"], y=gex_df["put_gex"], name="Put GEX", marker_color="red"))
        fig_gex.add_trace(go.Scatter(x=gex_df["strike"], y=gex_df["net_gex"], name="Net GEX", mode="lines+markers"))
        fig_gex.update_layout(barmode="group", xaxis_title="Strike", yaxis_title="GEX ($)")
        st.plotly_chart(fig_gex, use_container_width=True)
except Exception:
    st.info("GEX chart unavailable — run pipeline to populate gme_dws_strike_gex_1d")

try:
    oi_df = conn.execute("""
        SELECT d.strike,
               SUM(CASE WHEN d.option_type = 'call' THEN d.open_interest ELSE 0 END) AS call_oi,
               SUM(CASE WHEN d.option_type = 'put' THEN d.open_interest ELSE 0 END) AS put_oi
        FROM gme_dwd_option_contract_di d
        WHERE d.pull_date = (SELECT MAX(pull_date) FROM gme_dwd_option_contract_di)
        GROUP BY d.strike ORDER BY d.strike
    """).fetchdf()

    if not oi_df.empty:
        st.subheader("OI Distribution by Strike")
        fig_oi = go.Figure()
        fig_oi.add_trace(go.Bar(x=oi_df["strike"], y=oi_df["call_oi"], name="Call OI", marker_color="green"))
        fig_oi.add_trace(go.Bar(x=oi_df["strike"], y=oi_df["put_oi"], name="Put OI", marker_color="red"))
        fig_oi.update_layout(barmode="stack", xaxis_title="Strike", yaxis_title="Open Interest")
        st.plotly_chart(fig_oi, use_container_width=True)
except Exception:
    st.info("OI chart unavailable — run pipeline first")

if len(dashboard_df) > 1:
    st.subheader("Max Pain vs Spot")
    fig_mp = go.Figure()
    fig_mp.add_trace(go.Scatter(x=dashboard_df["pull_date"], y=dashboard_df["spot"], name="Spot", mode="lines+markers"))
    fig_mp.add_trace(go.Scatter(x=dashboard_df["pull_date"], y=dashboard_df["max_pain_strike"], name="Max Pain", mode="lines+markers", line=dict(dash="dash")))
    fig_mp.update_layout(xaxis_title="Date", yaxis_title="Price ($)")
    st.plotly_chart(fig_mp, use_container_width=True)

    st.subheader("IV30 / HV20 Trend")
    fig_iv = go.Figure()
    fig_iv.add_trace(go.Scatter(x=dashboard_df["pull_date"], y=dashboard_df["iv30"], name="IV30", mode="lines"))
    fig_iv.add_trace(go.Scatter(x=dashboard_df["pull_date"], y=dashboard_df["hv20"], name="HV20", mode="lines"))
    fig_iv.update_layout(xaxis_title="Date", yaxis_title="Volatility")
    st.plotly_chart(fig_iv, use_container_width=True)

    st.subheader("P/C Ratio Trend")
    fig_pc = px.line(dashboard_df, x="pull_date", y="pc_ratio")
    fig_pc.update_layout(xaxis_title="Date", yaxis_title="Put/Call Ratio")
    st.plotly_chart(fig_pc, use_container_width=True)

st.markdown("---")
st.subheader("Link Status Reference")
ref_data = []
for s, cfg in LINK_STATUS_CONFIG.items():
    ref_data.append({"Status": s, "Badge": cfg["badge"]})
st.table(ref_data)

st.markdown("---")
st.caption("Built with mart-forge | Kimball DWH Framework")

conn.close()
