"""GME Options Mart — Public Analytics Dashboard.

Connects to MotherDuck gme_db for live public GME options analytics.
Queries ONLY public analytical tables. No operator positions or private data.
"""

import os
import sys

import duckdb
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="GME Options Mart — Public Analytics", layout="wide")

MOTHERDUCK_TOKEN = os.environ.get("MOTHERDUCK_TOKEN")
DATABASE = "md:gme_db"

PUBLIC_TABLES = ["gme_dws_daily_snapshot_1d", "gme_dws_strike_gex_1d"]
FORBIDDEN_TABLES = ["gme_dws_warrant_monitor_1d"]

PUBLIC_METRIC_CATALOG = [
    {"id": "M-01", "name": "Spot Price", "source_type": "native", "link_status": "exact", "verification": "pending_verification"},
    {"id": "M-02", "name": "Max Pain Strike", "source_type": "derived", "link_status": "proxy", "verification": "pending_verification"},
    {"id": "M-03", "name": "Max Pain Convergence %", "source_type": "derived", "link_status": "unsupported", "verification": "pending_verification"},
    {"id": "M-04", "name": "Put/Call Ratio", "source_type": "native", "link_status": "proxy", "verification": "pending_verification"},
    {"id": "M-05", "name": "Net GEX", "source_type": "derived", "link_status": "proxy", "verification": "pending_verification"},
    {"id": "M-06", "name": "Call GEX by Strike", "source_type": "derived", "link_status": "unsupported", "verification": "pending_verification"},
    {"id": "M-07", "name": "Put GEX by Strike", "source_type": "derived", "link_status": "unsupported", "verification": "pending_verification"},
    {"id": "M-08", "name": "IV (avg)", "source_type": "native", "link_status": "proxy", "verification": "pending_verification"},
    {"id": "M-09", "name": "IV Percentile", "source_type": "derived", "link_status": "proxy", "verification": "pending_verification"},
    {"id": "M-10", "name": "OI by Strike", "source_type": "native", "link_status": "proxy", "verification": "pending_verification"},
]


def get_connection():
    if not MOTHERDUCK_TOKEN:
        return None
    try:
        return duckdb.connect(f"{DATABASE}?motherduck_token={MOTHERDUCK_TOKEN}", read_only=True)
    except Exception:
        return None


def safe_query(con, sql: str) -> pd.DataFrame:
    for table in FORBIDDEN_TABLES:
        if table in sql.lower():
            raise ValueError(f"Query blocked: references forbidden table {table}")
    try:
        return con.execute(sql).fetchdf()
    except Exception:
        return pd.DataFrame()


def load_snapshot(con) -> pd.DataFrame:
    return safe_query(con, """
        SELECT *
        FROM gme_dws_daily_snapshot_1d
        ORDER BY pull_date DESC
        LIMIT 30
    """)


def load_gex_latest(con) -> pd.DataFrame:
    return safe_query(con, """
        SELECT *
        FROM gme_dws_strike_gex_1d
        WHERE pull_date = (SELECT MAX(pull_date) FROM gme_dws_strike_gex_1d)
        ORDER BY gex_rank
        LIMIT 20
    """)


def load_gex_top5(con) -> pd.DataFrame:
    return safe_query(con, """
        SELECT *
        FROM gme_dws_strike_gex_1d
        WHERE pull_date = (SELECT MAX(pull_date) FROM gme_dws_strike_gex_1d)
          AND gex_rank <= 5
        ORDER BY gex_rank
    """)


def load_iv_history(con) -> pd.DataFrame:
    return safe_query(con, """
        WITH daily_avg_iv AS (
            SELECT
                pull_date,
                AVG(avg_iv) AS mean_iv
            FROM gme_dws_strike_gex_1d
            WHERE series_type = 'MONTHLY'
            GROUP BY pull_date
        )
        SELECT
            pull_date,
            mean_iv,
            PERCENT_RANK() OVER (ORDER BY mean_iv) AS iv_percentile
        FROM daily_avg_iv
        ORDER BY pull_date DESC
        LIMIT 60
    """)


st.title("GME Options Mart — Public Analytics")

con = get_connection()

if con is None:
    st.error("**BLOCKED — No MotherDuck connection**")
    if not MOTHERDUCK_TOKEN:
        st.warning("Set `MOTHERDUCK_TOKEN` environment variable before running.")
    else:
        st.warning("Could not connect to MotherDuck database `gme_db`.")

    st.markdown("---")
    st.subheader("Coverage & Status")
    st.caption("Dashboard is in BLOCKED state — no live data available.")

    status_data = []
    for m in PUBLIC_METRIC_CATALOG:
        status_data.append({
            "Metric ID": m["id"],
            "Metric": m["name"],
            "Source Type": m["source_type"],
            "Link Status": m["link_status"],
            "Data": "BLOCKED",
            "DQC Verification": m["verification"],
        })
    st.dataframe(pd.DataFrame(status_data), hide_index=True, use_container_width=True)

    st.info(
        "This dashboard requires a live MotherDuck connection.\n\n"
        "```bash\nexport MOTHERDUCK_TOKEN=<your-token>\n"
        "streamlit run app.py\n```"
    )
    st.stop()

snapshot_df = load_snapshot(con)
gex_top5_df = load_gex_top5(con)
gex_all_df = load_gex_latest(con)
iv_df = load_iv_history(con)

has_snapshot = not snapshot_df.empty
has_gex = not gex_top5_df.empty
has_iv = not iv_df.empty

st.caption("Live data from MotherDuck `gme_db` — all values tagged [REAL_API]. "
           "DQC verification status: pending. See KNOWN_GAPS.md.")

if not has_snapshot:
    st.warning("**STALE** — `gme_dws_daily_snapshot_1d` returned no data.")

if has_snapshot:
    latest = snapshot_df.iloc[0]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Spot Price [REAL_API]", f"${latest['spot']:.2f}")
    with col2:
        mp = latest["max_pain_strike"]
        convergence = latest["max_pain_convergence_pct"]
        st.metric("Max Pain [REAL_API]", f"${mp:.2f}", delta=f"{convergence:.1f}% from spot")
    with col3:
        pc = latest["pc_ratio"]
        label = "Bearish" if pc > 1.0 else "Bullish"
        st.metric("P/C Ratio [REAL_API]", f"{pc:.3f}", delta=label)
    with col4:
        net_gex = latest["net_gex"]
        st.metric("Net GEX [REAL_API]", f"{net_gex:,.0f}")

st.markdown("---")

st.header("Spot vs Max Pain (30d)")

if has_snapshot:
    snap_sorted = snapshot_df.sort_values("pull_date")
    fig_spot = go.Figure()
    fig_spot.add_trace(go.Scatter(
        x=snap_sorted["pull_date"], y=snap_sorted["spot"],
        mode="lines+markers", name="Spot", line=dict(color="#42a5f5"),
    ))
    fig_spot.add_trace(go.Scatter(
        x=snap_sorted["pull_date"], y=snap_sorted["max_pain_strike"],
        mode="lines", name="Max Pain", line=dict(color="#ff7043", dash="dash"),
    ))
    fig_spot.update_layout(
        yaxis_title="Price ($)", xaxis_title="Date",
        height=350, margin=dict(t=10, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig_spot, use_container_width=True)
else:
    st.info("STALE — No snapshot data for price/max-pain trend.")

st.markdown("---")

chart_cols = st.columns(2)

with chart_cols[0]:
    st.header("GEX by Strike (Top 5)")

    if has_gex:
        fig_gex = go.Figure()
        fig_gex.add_trace(go.Bar(
            x=gex_top5_df["strike"].astype(str),
            y=gex_top5_df["call_gex"],
            name="Call GEX",
            marker_color="#26a69a",
        ))
        fig_gex.add_trace(go.Bar(
            x=gex_top5_df["strike"].astype(str),
            y=gex_top5_df["put_gex"],
            name="Put GEX",
            marker_color="#ef5350",
        ))
        fig_gex.update_layout(
            barmode="group",
            xaxis_title="Strike", yaxis_title="GEX Contribution",
            height=350, margin=dict(t=10, b=40),
        )
        st.plotly_chart(fig_gex, use_container_width=True)
    else:
        st.info("STALE — No GEX data available.")

with chart_cols[1]:
    st.header("P/C Ratio Trend (30d)")

    if has_snapshot:
        fig_pc = go.Figure()
        fig_pc.add_trace(go.Scatter(
            x=snap_sorted["pull_date"], y=snap_sorted["pc_ratio"],
            mode="lines+markers", name="P/C Ratio", line=dict(color="#ab47bc"),
        ))
        fig_pc.add_hline(y=1.0, line_dash="dash", line_color="gray",
                         annotation_text="Neutral (1.0)")
        fig_pc.update_layout(
            yaxis_title="P/C Ratio", xaxis_title="Date",
            height=350, margin=dict(t=10, b=40),
        )
        st.plotly_chart(fig_pc, use_container_width=True)
    else:
        st.info("STALE — No snapshot data for P/C trend.")

st.markdown("---")

st.header("IV Percentile (Monthly Series)")

if has_iv:
    iv_sorted = iv_df.sort_values("pull_date")
    fig_iv = go.Figure()
    fig_iv.add_trace(go.Scatter(
        x=iv_sorted["pull_date"],
        y=iv_sorted["iv_percentile"] * 100,
        mode="lines+markers",
        name="IV Percentile",
        line=dict(color="#7e57c2"),
    ))
    fig_iv.add_hline(y=50, line_dash="dash", line_color="gray",
                     annotation_text="Median (50%)")
    fig_iv.update_layout(
        yaxis_title="IV Percentile (%)", xaxis_title="Date",
        height=300, margin=dict(t=10, b=40),
    )
    st.plotly_chart(fig_iv, use_container_width=True)
else:
    st.info("Insufficient IV history for percentile calculation.")

st.markdown("---")

if has_gex and not gex_all_df.empty:
    st.header("Open Interest by Strike")
    fig_oi = go.Figure()
    gex_sorted = gex_all_df.sort_values("strike")
    fig_oi.add_trace(go.Bar(
        x=gex_sorted["strike"].astype(str),
        y=gex_sorted["total_oi"],
        name="Total OI",
        marker_color="#66bb6a",
    ))
    if has_snapshot:
        spot_val = snapshot_df.iloc[0]["spot"]
        fig_oi.add_vline(x=str(round(spot_val)), line_dash="dash",
                         line_color="red", annotation_text=f"Spot ${spot_val:.0f}")
    fig_oi.update_layout(
        xaxis_title="Strike", yaxis_title="Open Interest",
        height=350, margin=dict(t=10, b=40),
    )
    st.plotly_chart(fig_oi, use_container_width=True)

st.markdown("---")

st.header("Coverage & Verification Status")

metric_status = []
for m in PUBLIC_METRIC_CATALOG:
    data_status = "LOADED [REAL_API]" if has_snapshot else "BLOCKED"
    if m["id"] in ("M-06", "M-07", "M-10"):
        data_status = "LOADED [REAL_API]" if has_gex else "BLOCKED"
    if m["id"] == "M-09":
        data_status = "LOADED [REAL_API]" if has_iv else "BLOCKED"

    metric_status.append({
        "ID": m["id"],
        "Metric": m["name"],
        "Source Type": m["source_type"],
        "Link Status": m["link_status"],
        "Data Status": data_status,
        "DQC Verification": m["verification"],
    })

loaded_count = sum(1 for m in metric_status if m["Data Status"] == "LOADED [REAL_API]")
total_count = len(metric_status)
verified_count = sum(1 for m in metric_status if m["DQC Verification"] == "verified")

cov_cols = st.columns(3)
with cov_cols[0]:
    st.metric("Data Loaded", f"{loaded_count} / {total_count}")
with cov_cols[1]:
    st.metric("DQC Verified", f"{verified_count} / {total_count}")
with cov_cols[2]:
    pct = (verified_count / total_count * 100) if total_count > 0 else 0
    st.metric("Verified Coverage", f"{pct:.0f}%")

st.dataframe(pd.DataFrame(metric_status), hide_index=True, use_container_width=True)

st.caption(
    "**Data tag semantics:** `[REAL_API]` = loaded from MotherDuck warehouse pipeline. "
    "This does NOT mean externally fact-checked. DQC verification is tracked separately. "
    "See `KNOWN_GAPS.md` for pending items."
)

if has_snapshot:
    st.caption(
        f"Latest data: {latest['pull_date']} | "
        f"Pipeline refreshes daily at 16:45 ET (weekdays)"
    )
