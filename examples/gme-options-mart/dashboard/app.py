"""Streamlit dashboard for gme-options-mart canonical example.

Reads gme_ads_market_dashboard either from MotherDuck `md:gme_db` (live mode, when
MOTHERDUCK_TOKEN is present) or from a local DuckDB fixture at
`data/fixtures/gme.duckdb` (fallback mode). Renders the nine T-17 tiles plus
header banner + sidebar link-status legend with clickable comparator badges
(closes predecessor bae4af2's non-clickable badges defect, TEST PLAN T4.3 / T7.4).
"""
from __future__ import annotations

import os
from pathlib import Path

import duckdb
import streamlit as st

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[3] / ".env")
except Exception:
    pass

ADS_TABLE = "gme_ads_market_dashboard"
DASHBOARD_ROOT = Path(__file__).resolve().parent
EXAMPLE_ROOT = DASHBOARD_ROOT.parent
FIXTURE_PATH = EXAMPLE_ROOT / "data" / "fixtures" / "gme.duckdb"

LINK_STATUS_URLS = {
    "spot": ("exact", "https://finance.yahoo.com/quote/GME/history"),
    "max_pain_strike_front": ("exact", "https://max-pain.com/stocks/GME"),
    "pc_ratio_oi": ("exact", "https://barchart.com/stocks/quotes/GME/put-call-ratios"),
    "iv30": ("proxy", "https://marketchameleon.com/Overview/GME/"),
    "hv20": ("exact", "https://barchart.com/stocks/quotes/GME/price-history/historical"),
    "net_gex": ("unsupported", None),
    "gex_zero_cross_strike": ("unsupported", None),
    "dealer_net_gamma": ("unsupported", None),
    "iv_rank": ("phase-gated", "https://marketchameleon.com/Overview/GME/IV/"),
}


@st.cache_resource
def get_conn() -> tuple[duckdb.DuckDBPyConnection, str]:
    token = os.environ.get("MOTHERDUCK_TOKEN")
    if token:
        try:
            conn = duckdb.connect(f"md:gme_db?motherduck_token={token}", read_only=True)
            return conn, "live"
        except Exception as exc:  # noqa: BLE001
            st.warning(f"MotherDuck connect failed ({exc}); falling back to local fixture.")
    if FIXTURE_PATH.exists():
        conn = duckdb.connect(str(FIXTURE_PATH), read_only=True)
        return conn, "fixture"
    raise RuntimeError(f"No MOTHERDUCK_TOKEN and no local fixture at {FIXTURE_PATH}.")


def render_badge(label: str, url: str | None, status: str) -> str:
    if status in {"exact", "proxy"} and url:
        return f"[`{label} [{status}]`]({url})"
    if status == "phase-gated":
        # Caller passes the resolved status; rendered as either link or grey.
        return f"`{label} [phase-gated]`"
    return f"`{label} [unsupported]`"


def render_tile(col, label: str, value, metric_key: str, lookback_days: int | None = None) -> None:
    status, url = LINK_STATUS_URLS.get(metric_key, ("unsupported", None))
    if metric_key == "iv_rank":
        if lookback_days is not None and lookback_days >= 252:
            status_resolved = "proxy"
        else:
            status_resolved = "unsupported"
    else:
        status_resolved = status
    badge_url = url if status_resolved in {"exact", "proxy"} else None
    if status_resolved in {"exact", "proxy"} and badge_url:
        col.metric(label, value)
        col.markdown(f"[{label} [{status_resolved}]]({badge_url})")
    else:
        col.metric(label, value)
        col.markdown(f"`{label} [{status_resolved}]`")


def main() -> None:
    st.set_page_config(page_title="GME options mart", layout="wide")
    st.title("GME Options Mart — Dashboard")

    conn, mode = get_conn()

    if mode == "live":
        st.success("Connected to MotherDuck (`md:gme_db`).")
    else:
        st.warning(f"local DuckDB fixture mode (`{FIXTURE_PATH}`).")

    df = conn.execute(f"SELECT * FROM {ADS_TABLE}").df()
    if df.empty:
        st.error(f"`{ADS_TABLE}` is empty — run `dbt seed && dbt run` first.")
        return
    row = df.iloc[0]

    pull_lag = float(row.get("pull_lag_hours") or 0)
    if bool(row.get("is_stale")):
        st.error(
            f"STALE — last pull {pull_lag:+.1f}h relative to most recent session close "
            f"({row.get('most_recent_session_close_ts_utc')})."
        )
    else:
        st.caption(
            f"trading_date={row['trading_date']} · last pull {pull_lag:+.1f}h "
            f"after most recent close ({row.get('most_recent_session_close_ts_utc')})."
        )

    c1, c2, c3 = st.columns(3)
    render_tile(c1, "Spot", f"${row['spot']:.2f}", "spot")
    render_tile(c2, "Max pain (front)", f"${row['max_pain_strike_front']:.2f}", "max_pain_strike_front")
    render_tile(c3, "P/C OI", f"{row['pc_ratio_oi']:.3f}", "pc_ratio_oi")

    c4, c5, c6 = st.columns(3)
    iv30 = row.get("iv30")
    hv20 = row.get("hv20")
    render_tile(c4, "IV30", f"{iv30:.3f}" if iv30 is not None else "n/a", "iv30")
    render_tile(c5, "HV20", f"{hv20:.3f}" if hv20 is not None else "n/a", "hv20")
    net_gex_m = (row.get("net_gex") or 0) / 1e6
    render_tile(c6, "Net GEX ($M / 1%)", f"{net_gex_m:,.1f}", "net_gex")

    c7, c8, c9 = st.columns(3)
    zc = row.get("gex_zero_cross_strike")
    render_tile(c7, "Strike-axis GEX zero cross", f"${zc:.2f}" if zc is not None else "n/a", "gex_zero_cross_strike")
    dng = row.get("dealer_net_gamma")
    render_tile(c8, "Dealer net γ (front, shares/1%)", f"{dng:,.0f}" if dng is not None else "n/a", "dealer_net_gamma")
    iv_rank = row.get("iv_rank")
    lookback = int(row.get("iv_rank_lookback_days") or 0)
    iv_label = row.get("iv_rank_label", "provisional")
    iv_text = f"{iv_rank:.1f} ({iv_label} · {lookback}/252)" if iv_rank is not None else f"provisional ({lookback}/252)"
    render_tile(c9, "IV Rank", iv_text, "iv_rank", lookback_days=lookback)

    with st.sidebar:
        st.subheader("Link-status legend")
        for metric_key, (status, url) in LINK_STATUS_URLS.items():
            if metric_key == "iv_rank":
                status_now = "proxy" if lookback >= 252 else "unsupported"
                url_now = url if status_now == "proxy" else None
            else:
                status_now = status
                url_now = url
            if status_now in {"exact", "proxy"} and url_now:
                st.markdown(f"- [{metric_key} [{status_now}]]({url_now})")
            else:
                st.markdown(f"- `{metric_key} [{status_now}]`")
        if st.button("Refresh"):
            st.cache_resource.clear()
            st.experimental_rerun()


if __name__ == "__main__":
    main()
