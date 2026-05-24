# GME Options Mart — Technical Design Document (TDD)

Status: **MVP Checkpoint** (pending runtime column-level verification — Phase F iteration)

---

## T-1: Version History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 0.1 | 2026-05-24 | DROOK-OPUS | MVP checkpoint: document expected warehouse tables for dashboard |
| 0.2 | 2026-05-24 | DROOK-OPUS | Correction pass: pending_verification on all tables, disclose incomplete sections |

---

## T-2: Design Reasoning (Kimball 4-Step)

1. **Business Process:** Daily GME options-chain data capture and public analytics aggregation
2. **Grain:** One row per trading day (daily snapshot); one row per strike-expiry-date (GEX)
3. **Dimensions:** `dim_date` (calendar), `dim_strike` (option strike/expiry metadata — future)
4. **Facts:** Options chain metrics aggregated to daily and strike-level grains

---

## T-3: Table Summary

| Table | Layer | Grain | Materialization | Status |
|-------|-------|-------|-----------------|--------|
| `gme_ods_options_chain` | ODS | per-contract per-pull_date | incremental | `pending_verification` |
| `gme_dim_date` | DIM | per-calendar-date | table (seed) | `pending_verification` |
| `gme_dws_daily_snapshot_1d` | DWS | per-pull_date | table | `pending_verification` |
| `gme_dws_strike_gex_1d` | DWS | per-strike per-expiry per-pull_date | table | `pending_verification` |

All table statuses are `pending_verification` — actual MotherDuck schemas have not been reconciled against these specs at this checkpoint.

---

## T-4: Data Architecture Diagram

```
Public options data API (pending source confirmation)
        │
        ▼
┌──────────────────┐
│  gme_ods_options  │  ODS: raw chain, incremental by pull_date
│  _chain           │
└────────┬─────────┘
         │
    ┌────┴─────────────────┐
    ▼                      ▼
┌──────────────┐   ┌──────────────────┐
│ gme_dws_daily │   │ gme_dws_strike   │  DWS: aggregations
│ _snapshot_1d  │   │ _gex_1d          │
└──────┬───────┘   └────────┬─────────┘
       │                    │
       └────────┬───────────┘
                ▼
        ┌───────────────┐
        │  Streamlit     │  Presentation
        │  Dashboard     │
        └───────────────┘
```

---

## T-5: Column Specification

Column specs below reflect the **expected** schema based on pipeline design. Actual MotherDuck columns require runtime reconciliation in Phase F. All column-level claims are `pending_verification`.

### gme_dws_daily_snapshot_1d

All example values below are placeholders [THEORETICAL] — not sourced from live data.

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|-----------|---------------|-------------|-------------|
| pull_date | DATE | Trading day of data capture | 2026-05-23 [THEORETICAL] | native | Ingestion metadata |
| spot | DECIMAL(10,2) | GME last closing price | 27.15 [THEORETICAL] | native — last close from price endpoint | pending source confirmation |
| max_pain_strike | DECIMAL(10,2) | Strike minimizing total option holder P&L | 25.00 [THEORETICAL] | derived — `argmin(sum(call_pain + put_pain) over strikes)` | ODS options chain |
| max_pain_convergence_pct | DECIMAL(5,2) | Percentage distance from spot to max pain | -7.9 [THEORETICAL] | derived — `(max_pain_strike - spot) / spot * 100` | Computed |
| pc_ratio | DECIMAL(8,4) | Put/Call volume ratio | 0.8500 [THEORETICAL] | derived — `sum(put_volume) / nullif(sum(call_volume), 0)` | ODS options chain |
| net_gex | DECIMAL(18,2) | Net gamma exposure across all strikes | 1250000.00 [THEORETICAL] | derived — `sum(gamma * OI * 100 * spot^2 * 0.01 * sign)` | ODS options chain |
| provider | VARCHAR | Data source identifier | pending [THEORETICAL] | native | Ingestion metadata |
| pull_ts_utc | TIMESTAMP | UTC timestamp of data pull | 2026-05-23T20:45:00Z [THEORETICAL] | native | Ingestion metadata |

### gme_dws_strike_gex_1d

All example values below are placeholders [THEORETICAL] — not sourced from live data.

| column_name | data_type | definition | example_value | calculation | data_source |
|-------------|-----------|-----------|---------------|-------------|-------------|
| pull_date | DATE | Trading day | 2026-05-23 [THEORETICAL] | native | Ingestion metadata |
| strike | DECIMAL(10,2) | Option strike price | 25.00 [THEORETICAL] | native | pending source confirmation |
| expiry | DATE | Option expiration date | 2026-06-20 [THEORETICAL] | native | pending source confirmation |
| series_type | VARCHAR | Expiry classification | MONTHLY [THEORETICAL] | derived — monthly vs weekly detection | Computed |
| dte | INTEGER | Days to expiration | 28 [THEORETICAL] | derived — `expiry - pull_date` | Computed |
| call_gex | DECIMAL(18,2) | Call gamma exposure at strike | 85000.00 [THEORETICAL] | derived — `call_gamma * call_oi * 100 * spot^2 * 0.01` | ODS chain |
| put_gex | DECIMAL(18,2) | Put gamma exposure at strike | -42000.00 [THEORETICAL] | derived — `-1 * put_gamma * put_oi * 100 * spot^2 * 0.01` | ODS chain |
| net_gex | DECIMAL(18,2) | Net GEX at strike | 43000.00 [THEORETICAL] | derived — `call_gex + put_gex` | Computed |
| total_oi | INTEGER | Total open interest (calls + puts) | 15230 [THEORETICAL] | derived — `call_oi + put_oi` | ODS chain |
| avg_iv | DECIMAL(8,4) | Average implied volatility at strike | 0.8500 [THEORETICAL] | derived — `(call_iv + put_iv) / 2` | ODS chain |
| gex_rank | INTEGER | Rank by absolute net GEX | 1 [THEORETICAL] | derived — `row_number() over (partition by pull_date order by abs(net_gex) desc)` | Computed |

---

## T-6: ODS Table Design

### gme_ods_options_chain

| Property | Value |
|----------|-------|
| Source | Public options data API (pending source confirmation) |
| Grain | One row per option contract per pull_date |
| Logical Partition | `pull_date` |
| Incremental Strategy | `delete+insert` (dbt-duckdb) |
| Unique Key | `['pull_date', 'option_symbol']` |
| Backfill | Re-run with `--vars '{pull_date: "YYYY-MM-DD"}'` |
| Restatement | Overwrite partition; no prior-day correction |
| Provenance Columns | `provider`, `pull_ts_utc`, `quote_ts_utc`, `run_id` |

---

## T-7 through T-13: Incomplete Sections

The following TDD sections are not yet populated for this MVP checkpoint:

| Section | Title | Status |
|---------|-------|--------|
| T-7 | Dimension Table Design | `pending` — only `dim_date` exists, inline strike dimensions |
| T-8 | Fact Table Design | `pending` — DWS aggregates directly from ODS |
| T-9 | Count Aggregation Design | `pending` |
| T-10 | Performance Aggregation Design | `pending` |
| T-11 | Presentation Table Design | `pending` — no ADS/OBT layer yet |
| T-12 | Physical Design | `pending` — column-level specs in T-5 are expected, not reconciled |
| T-13 | Implementation Specification | `pending` — dbt project not in public repo |

These sections are required for full TDD sign-off and will be populated during Phase F iteration.

---

## T-14: DQC Plan

| Control Class | Applicable | Target | Severity | Notes |
|---------------|-----------|--------|----------|-------|
| PK Integrity | Yes | All tables | error | `pull_date` + entity key not null, unique |
| FK Integrity | Yes | DWS → DIM | error | `pull_date` resolves to `dim_date` |
| Freshness | Yes | ODS/DWS | error | Data within 2 trading days of current date |
| Completeness | Yes | DWS snapshot | warn | Expect 1 row per trading day |
| Accepted Ranges | Yes | spot, pc_ratio, avg_iv | warn | spot > 0, 0 < pc_ratio < 50, 0 < avg_iv < 10 |
| Duplicate Detection | Yes | ODS | error | No duplicate option_symbol per pull_date |
| Null-Rate | Yes | All tables | warn | Metric columns < 5% null |
| Business Reconciliation | Pending | spot, max_pain, pc_ratio | warn | External source comparison not yet implemented |

---

## T-15 through T-16: Incomplete Sections

| Section | Title | Status |
|---------|-------|--------|
| T-15 | Test Inventory | `pending` — tests exist in `tests/` but inventory not formalized |
| T-16 | Operations | `pending` — refresh schedule documented in BRD but SLA/alerting not specified |

---

## T-17: Known Limitations

- All tables and layers below are proposed checkpoint design pending live schema verification
- DWD layer is not present in the proposed design — DWS tables aggregate directly from ODS
- No DIM tables beyond `dim_date` — strike/expiry dimensions are inline
- IV percentile calculated from internal history only (no external IV rank comparison)
- GEX formula uses simplified gamma; commercial providers may use different models
- No 7d/30d trailing aggregation tables yet
- Column specs above reflect expected schema; actual warehouse columns require reconciliation in Phase F
- ODS ingestion script is not in the public repository
- Source binding (provider, endpoint) is pending discovery and confirmation
- TDD sections T-7 through T-13 and T-15/T-16 are incomplete at this checkpoint
