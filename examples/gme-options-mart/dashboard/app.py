"""Streamlit dashboard for gme-options-mart canonical example.

Reads gme_ads_market_dashboard either from MotherDuck `md:gme_db` (live mode, when
MOTHERDUCK_TOKEN is present) or from a local DuckDB fixture at
`data/fixtures/gme.duckdb` (fallback mode). Renders the nine T-17 tiles plus
header banner + sidebar link-status legend with clickable comparator badges
(closes predecessor bae4af2's non-clickable badges defect, TEST PLAN T4.3 / T7.4).

iv_rank link status is sourced from the ADS view's `iv_rank_link_status_active`
column — the single source of truth for the phase-gated `unsupported → proxy`
flip at the 252-trading-day boundary (closes Phase C.5 advisory M5).
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

# Static link-status contract for the eight non-phase-gated metrics. iv_rank's
# active status is resolved at runtime from `iv_rank_link_status_active` on the
# ADS view (see render_tile).
LINK_STATUS_URLS = {
    "spot": ("exact", "https://finance.yahoo.com/quote/GME/history"),
    "max_pain_strike_front": ("exact", "https://max-pain.com/stocks/GME"),
    "pc_ratio_oi": ("exact", "https://barchart.com/stocks/quotes/GME/put-call-ratios"),
    "iv30": ("proxy", "https://marketchameleon.com/Overview/GME/"),
    "hv20": ("exact", "https://barchart.com/stocks/quotes/GME/price-history/historical"),
    "net_gex": ("unsupported", None),
    "gex_zero_cross_strike": ("unsupported", None),
    "dealer_net_gamma": ("unsupported", None),
}

IV_RANK_URL = "https://marketchameleon.com/Overview/GME/IV/"


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


def render_tile(col, label: str, value, status: str, url: str | None) -> None:
    col.metric(label, value)
    if status in {"exact", "proxy"} and url:
        col.markdown(f"[{label} [{status}]]({url})")
    else:
        col.markdown(f"`{label} [{status}]`")


def resolve_status(metric_key: str, iv_rank_status_active: str | None) -> tuple[str, str | None]:
    """Single source of truth for link-status badge resolution at render time."""
    if metric_key == "iv_rank":
        status = iv_rank_status_active or "unsupported"
        return status, IV_RANK_URL if status in {"exact", "proxy"} else None
    return LINK_STATUS_URLS.get(metric_key, ("unsupported", None))


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

    iv_rank_status_active = row.get("iv_rank_link_status_active")

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

    def tile(col, label, value, metric_key):
        status, url = resolve_status(metric_key, iv_rank_status_active)
        render_tile(col, label, value, status, url)

    c1, c2, c3 = st.columns(3)
    tile(c1, "Spot", f"${row['spot']:.2f}", "spot")
    tile(c2, "Max pain (front)", f"${row['max_pain_strike_front']:.2f}", "max_pain_strike_front")
    tile(c3, "P/C OI", f"{row['pc_ratio_oi']:.3f}", "pc_ratio_oi")

    c4, c5, c6 = st.columns(3)
    iv30 = row.get("iv30")
    hv20 = row.get("hv20")
    tile(c4, "IV30", f"{iv30:.3f}" if iv30 is not None else "n/a", "iv30")
    tile(c5, "HV20", f"{hv20:.3f}" if hv20 is not None else "n/a", "hv20")
    net_gex_m = (row.get("net_gex") or 0) / 1e6
    tile(c6, "Net GEX ($M / 1%)", f"{net_gex_m:,.1f}", "net_gex")

    c7, c8, c9 = st.columns(3)
    zc = row.get("gex_zero_cross_strike")
    tile(c7, "Strike-axis GEX zero cross", f"${zc:.2f}" if zc is not None else "n/a", "gex_zero_cross_strike")
    dng = row.get("dealer_net_gamma")
    tile(c8, "Dealer net γ (front, shares/1%)", f"{dng:,.0f}" if dng is not None else "n/a", "dealer_net_gamma")
    iv_rank = row.get("iv_rank")
    lookback = int(row.get("iv_rank_lookback_days") or 0)
    iv_label = row.get("iv_rank_label", "provisional")
    iv_text = f"{iv_rank:.1f} ({iv_label} · {lookback}/252)" if iv_rank is not None else f"provisional ({lookback}/252)"
    tile(c9, "IV Rank", iv_text, "iv_rank")

    with st.sidebar:
        st.subheader("Link-status legend")
        legend_keys = list(LINK_STATUS_URLS.keys()) + ["iv_rank"]
        for metric_key in legend_keys:
            status, url = resolve_status(metric_key, iv_rank_status_active)
            if status in {"exact", "proxy"} and url:
                st.markdown(f"- [{metric_key} [{status}]]({url})")
            else:
                st.markdown(f"- `{metric_key} [{status}]`")
        if st.button("Refresh"):
            st.cache_resource.clear()
            st.experimental_rerun()


if __name__ == "__main__":
    main()
