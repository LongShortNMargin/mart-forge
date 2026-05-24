# GME Options Mart — Public Analytics Example

A conformance trial of the mart-forge lifecycle against live GME options data.

## What This Is

This example demonstrates mart-forge Phases A through E using public GameStop options-chain data:

- **Phase A (BRD):** `business-requirements.md` — 10 public metrics scoped to public market data
- **Phase B (TDD):** `tech-design-doc.md` — Kimball design for ODS/DWS tables (pending schema reconciliation)
- **Phase E (Dashboard):** `dashboard/app.py` — Streamlit dashboard with live MotherDuck connection

## What This Is NOT

- Not a complete, fully-verified production mart (see `KNOWN_GAPS.md`)
- Not a source of trading signals or financial advice
- Data loaded from the pipeline is tagged `[REAL_API]` but is NOT externally fact-checked or DQC verified

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

- **Data loaded:** pending runtime verification (10 metrics intended when MotherDuck is available)
- **DQC verified:** 0/10 metrics (external reconciliation pending)
- **Phase F items:** documented iteration items remaining
- **TDD completeness:** sections T-7 through T-13, T-15, T-16 are pending

## Tables Used

| Table | Layer | Description |
|-------|-------|------------|
| `gme_dws_daily_snapshot_1d` | DWS | Daily aggregate: spot, max pain, P/C ratio, net GEX |
| `gme_dws_strike_gex_1d` | DWS | Per-strike GEX, OI, IV with ranking |

This mart queries only the public analytical tables listed above.
