"""
Dashboard Template — Streamlit Presentation Layer

Rules:
- Every metric card traces to a TDD metric entry (bidirectional traceability)
- External comparison links displayed per link_status (exact/proxy/unsupported)
- Fixture mode shows explicit "FIXTURE/DEMO" banner
- Live mode shows "BLOCKED/STALE" if data unavailable
- Never silently substitute fixture for live data
- Consume DQC results and provenance — no manual reference value entry
"""

import json
import os
from pathlib import Path

import streamlit as st

# Configuration
MART_NAME = "{mart_name}"
DQC_SCORECARD_PATH = "dqc_scorecard.json"
IS_FIXTURE_MODE = os.getenv("MART_FIXTURE_MODE", "false").lower() == "true"


def load_scorecard(path: str) -> dict | None:
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text())
    return None


def render_link_status_badge(link_status: str, url: str | None = None) -> str:
    """Render link status per SPEC display rules."""
    if link_status == "exact" and url:
        return f"[Exact verification source]({url})"
    elif link_status == "proxy" and url:
        return f"Advisory comparator (proxy) — not ingestion provenance or DQC truth. [Link]({url})"
    elif link_status == "unsupported":
        return "No external comparator available — see DQC scorecard"
    else:
        return f"Status: {link_status}"


def main():
    st.set_page_config(page_title=f"{MART_NAME} Dashboard", layout="wide")
    st.title(f"{MART_NAME} Dashboard")

    if IS_FIXTURE_MODE:
        st.warning("FIXTURE/DEMO MODE — This dashboard is using static fixture data, not live data.")

    scorecard = load_scorecard(DQC_SCORECARD_PATH)

    st.header("Metrics Overview")
    st.info("Replace this section with metric cards from the signed TDD dashboard specification.")

    # Example metric card structure (replace with actual metrics from TDD)
    # col1, col2 = st.columns(2)
    # with col1:
    #     st.metric("Metric Name (M-1)", value="123", delta="+5%")
    #     st.caption(render_link_status_badge("exact", "https://example.com/verify"))
    # with col2:
    #     st.metric("Metric Name (M-2)", value="456")
    #     st.caption(render_link_status_badge("unsupported"))

    st.header("DQC Scorecard")
    if scorecard:
        controls = scorecard.get("controls", [])
        for control in controls:
            status = control.get("status", "unknown")
            icon = {"pass": "green", "fail": "red", "exhausted": "orange"}.get(status, "gray")
            st.markdown(
                f":{icon}_circle: **{control.get('class', 'N/A')}** — "
                f"{control.get('metric', 'N/A')}: {status}"
            )
    else:
        st.warning("DQC scorecard not found. Run `dbt test` and `dqc-update` to generate.")

    st.header("Data Provenance")
    st.info("Provenance information is populated from ODS pull_ts_utc and provider columns.")


if __name__ == "__main__":
    main()
