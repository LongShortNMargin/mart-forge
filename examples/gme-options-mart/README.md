# GME Options Mart — Public Analytics Example

A conformance trial of the mart-forge lifecycle against live GME options data.

## What This Is

This example demonstrates mart-forge Phases A through E using public GameStop options-chain data:

- **Phase A (BRD):** `business-requirements.md` — 10 public metrics, no operator data
- **Phase B (TDD):** `tech-design-doc.md` — Kimball design for ODS/DWS tables
- **Phase E (Dashboard):** `dashboard/app.py` — Streamlit dashboard with live MotherDuck connection

## What This Is NOT

- Not a complete, fully-verified production mart (see `KNOWN_GAPS.md`)
- Not a source of trading signals or financial advice
- Does not contain any operator positions, warrant data, account details, or private trading decisions

## Running the Dashboard

```bash
# Install dependencies
pip install -r dashboard/requirements.txt

# Set MotherDuck token (never commit this)
export MOTHERDUCK_TOKEN=<your-token>

# Run
cd dashboard
streamlit run app.py
```

Without `MOTHERDUCK_TOKEN`, the dashboard renders in BLOCKED mode showing the coverage panel and metric catalog.

## Coverage Status

See `KNOWN_GAPS.md` for the current gap inventory. At MVP checkpoint:

- **Data loaded:** 10/10 metrics (when MotherDuck is available)
- **DQC verified:** 0/10 metrics (external reconciliation pending)
- **Phase F items:** 6 documented iteration items remaining

## Tables Used

| Table | Layer | Description |
|-------|-------|------------|
| `gme_dws_daily_snapshot_1d` | DWS | Daily aggregate: spot, max pain, P/C ratio, net GEX |
| `gme_dws_strike_gex_1d` | DWS | Per-strike GEX, OI, IV with ranking |

**Excluded:** `gme_dws_warrant_monitor_1d` (private operator data — not part of public mart).
